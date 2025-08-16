"""Helpers for parsing docstrings. Used for helptext generation."""
# NOTE: mostly based on tyro._docstring module, but I think we have to simplify it further a lot for flat simple scripts

import ast
import functools
import io
import tokenize

from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeVar

import docstring_parser

from tyro import _strings
from tyro import _unsafe_cache
from tyro.conf import _markers


T = TypeVar("T", bound=Callable)


@dataclass(frozen=True)
class _Token:
  token_type: int
  content: str
  logical_line: int
  actual_line: int


@dataclass(frozen=True)
class _VarData:
  index: int
  logical_line: int
  actual_line: int
  prev_field_logical_line: int


@dataclass(frozen=True)
class _ScriptTokenization:
  tokens: list[_Token]
  tokens_from_logical_line: dict[int, list[_Token]]
  tokens_from_actual_line: dict[int, list[_Token]]
  var_data_from_name: dict[str, _VarData]

  @staticmethod
  @_unsafe_cache.unsafe_cache(64)
  def make(source: str) -> "_ScriptTokenization":
    """Parse the source code of a script, and cache some tokenization information."""

    readline = io.BytesIO(source.encode("utf-8")).readline

    tokens: list[_Token] = []
    tokens_from_logical_line: dict[int, list[_Token]] = {1: []}
    tokens_from_actual_line: dict[int, list[_Token]] = {1: []}
    var_data_from_name: dict[str, _VarData] = {}

    logical_line: int = 1
    actual_line: int = 1
    for toktype, tok, start, end, line in tokenize.tokenize(readline):
      # Note: we only track logical line numbers, which are delimited by
      # `tokenize.NEWLINE`. `tokenize.NL` tokens appear when logical lines are
      # broken into multiple lines of code; these are ignored.
      if toktype == tokenize.NEWLINE:
        logical_line += 1
        actual_line += 1
        tokens_from_logical_line[logical_line] = []
        tokens_from_actual_line[actual_line] = []
      elif toktype == tokenize.NL:
        actual_line += 1
        tokens_from_actual_line[actual_line] = []
      elif toktype is not tokenize.INDENT:
        token = _Token(
          token_type=toktype,
          content=tok,
          logical_line=logical_line,
          actual_line=actual_line,
        )
        tokens.append(token)
        tokens_from_logical_line[logical_line].append(token)
        tokens_from_actual_line[actual_line].append(token)

    prev_var_logical_line: int = 1
    for i, token in enumerate(tokens[:-1]):
      if token.token_type == tokenize.NAME:
        # Naive heuristic for field names.
        is_first_token = True
        for t in tokens_from_logical_line[token.logical_line]:
          if t == token:
            break
          if t.token_type is not tokenize.COMMENT:
            is_first_token = False
            break

        if not is_first_token:
          continue

        if token.content not in var_data_from_name:
          var_data_from_name[token.content] = _VarData(
            index=i,
            logical_line=token.logical_line,
            actual_line=token.actual_line,
            prev_field_logical_line=prev_var_logical_line,
          )
          prev_var_logical_line = token.logical_line

    return _ScriptTokenization(
      tokens=tokens,
      tokens_from_logical_line=tokens_from_logical_line,
      tokens_from_actual_line=tokens_from_actual_line,
      var_data_from_name=var_data_from_name,
    )


@_unsafe_cache.unsafe_cache(1024)
def get_script_tokenization_with_var(source: str, var_name: str) -> _ScriptTokenization | None:
  # Search for token in this class + all parents.
  try:
    tokenization = _ScriptTokenization.make(source)  # type: ignore
  except ValueError:
    # OSError is raised when we can't read the source code. This is
    # fine, we just assume there's no docstring. We can uncomment the
    # assert below for debugging.
    #
    # assert (
    #     # Dynamic dataclasses.
    #     "could not find class definition" in e.args[0]
    #     # Pydantic.
    #     or "source code not available" in e.args[0]
    #     # Third error that can be raised by inspect.py.
    #     or "could not get source code" in e.args[0]
    # )
    return None
  except TypeError as e:  # pragma: no cover
    # Notebooks cause “___ is a built-in class” TypeError.
    assert "built-in class" in e.args[0]
    return None

  # Grab field-specific tokenization data.
  if var_name in tokenization.var_data_from_name:
    return tokenization


@functools.lru_cache(maxsize=1024)
def parse_docstring_from_object(obj: object) -> dict[str, str]:
  return {
    doc.arg_name: doc.description
    for doc in docstring_parser.parse_from_object(obj).params
    if doc.description is not None
  }


@_unsafe_cache.unsafe_cache(1024)
def get_var_docstring(source: str, var_name: str, markers: tuple[_markers.Marker, ...]) -> str | None:
  """Get docstring for a variable in a script."""

  # NoneType will break docstring_parser.
  # if cls is type(None):
  #   return None

  # # Try to parse using docstring_parser.
  # for cls_search in cls.__mro__:
  #   if cls_search.__module__ == "builtins":
  #     continue  # Skip `object`, `Callable`, `tuple`, etc.
  #   docstring = parse_docstring_from_object(cls_search).get(field_name, None)
  #   if docstring is not None:
  #     return _strings.dedent(_strings.remove_single_line_breaks(docstring)).strip()

  if _markers.HelptextFromCommentsOff in markers:
    return None

  # If docstring_parser failed, let's try looking for comments.
  tokenization = get_script_tokenization_with_var(source, var_name)
  if tokenization is None:  # Currently only happens for dynamic dataclasses.
    return None

  var_data = tokenization.var_data_from_name[var_name]

  # Check for comment on the same line as the field.
  final_token_on_line = tokenization.tokens_from_logical_line[var_data.logical_line][-1]
  if final_token_on_line.token_type == tokenize.COMMENT:
    comment: str = final_token_on_line.content
    assert comment.startswith("#")
    if comment.startswith("#!"):
      return
    if comment.startswith("#:"):  # Sphinx autodoc-style comment.
      # https://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html#directive-autoattribute
      return _strings.remove_single_line_breaks(comment[2:].strip())
    else:
      return _strings.remove_single_line_breaks(comment[1:].strip())

  # Check for a single string literal on the next logical line, which we
  # interpret as a docstring for the preceding variable.
  next_logical_line = var_data.logical_line + 1
  if next_logical_line in tokenization.tokens_from_logical_line:
    next_line_tokens = tokenization.tokens_from_logical_line[next_logical_line]
    if len(next_line_tokens) == 1 and next_line_tokens[0].token_type == tokenize.STRING:
      string_token = next_line_tokens[0]
      try:
        string_value = ast.literal_eval(string_token.content)
      except Exception:
        # Fallback: strip quotes crudely if literal_eval fails.
        string_value = string_token.content.strip().strip('"').strip("'")
      return _strings.remove_single_line_breaks(str(string_value).strip())

  # Check for comments that come before the field. This is intentionally written to
  # support comments covering multiple (grouped) fields, for example:
  #
  #     # Optimizer hyperparameters.
  #     learning_rate: float
  #     beta1: float
  #     beta2: float
  #
  # In this case, 'Optimizer hyperparameters' will be treated as the docstring for all
  # 3 fields. There are tradeoffs we are making here.
  #
  # The exception this is Sphinx-style comments:
  #
  #     #: The learning rate.
  #     learning_rate: float
  #     beta1: float
  #     beta2: float
  #
  # Where, by convention the comment only applies to the field that directly follows it.

  # Get first line of the class definition, excluding decorators. This logic is only
  # needed for Python >= 3.9; in 3.8, we can simply use
  # `tokenization.tokens[0].logical_line`.
  # classdef_logical_line = -1
  # for token in tokenization.tokens:
  #   if token.content == "class":
  #     classdef_logical_line = token.logical_line
  #     break
  # assert classdef_logical_line != -1

  comments: list[str] = []
  current_actual_line = var_data.actual_line - 1
  directly_above_field = True
  is_sphinx_doc_comment = False
  while current_actual_line in tokenization.tokens_from_actual_line:
    actual_line_tokens = tokenization.tokens_from_actual_line[current_actual_line]

    # We stop looking if we find an empty line.
    if len(actual_line_tokens) == 0:
      break

    # We don't look in the first logical line. This includes all comments that come
    # before the end parentheses in the class definition (eg comments in the
    # subclass list).
    # if actual_line_tokens[0].logical_line <= classdef_logical_line:
    #   break

    # Record single comments!
    if len(actual_line_tokens) == 1 and actual_line_tokens[0].token_type is tokenize.COMMENT:
      (comment_token,) = actual_line_tokens
      assert comment_token.content.startswith("#")
      if comment_token.content.startswith("#:"):  # Sphinx autodoc-style comment.
        # https://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html#directive-autoattribute
        comments.append(comment_token.content[2:].strip())
        is_sphinx_doc_comment = True
      else:
        comments.append(comment_token.content[1:].strip())
    elif len(comments) > 0:
      # Comments should be contiguous.
      break
    else:
      # This comment is not directly above the current field.
      directly_above_field = False

    current_actual_line -= 1

  if len(comments) > 0 and not (is_sphinx_doc_comment and not directly_above_field):
    return _strings.remove_single_line_breaks("\n".join(reversed(comments)))

  return
