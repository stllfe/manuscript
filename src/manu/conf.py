"""Manu's forward port of a subset of tyro config system.

---
The tyro.conf submodule contains helpers for attaching parsing-specific
configuration metadata to types via PEP 593 <https://peps.python.org/pep-0593/> runtime annotations.

---
Read more:
https://brentyi.github.io/tyro/examples/basics/#configuration-via-typing-annotated
"""

from tyro.conf import EnumChoicesFromValues as EnumChoicesFromValues
from tyro.conf import Fixed as Fixed
from tyro.conf import FlagCreatePairsOff as FlagCreatePairsOff
from tyro.conf import HelptextFromCommentsOff as HelptextFromCommentsOff
from tyro.conf import PositionalRequiredArgs as PositionalRequiredArgs
from tyro.conf import Suppress as Suppress
from tyro.conf import SuppressFixed as SuppressFixed
from tyro.conf import UseAppendAction as UseAppendAction
from tyro.conf import UseCounterAction as UseCounterAction
from tyro.conf import arg as arg
