import tyro.conf

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


__doc__ = f"Manu's forward port of a subset of tyro config system:\n{tyro.conf.__doc__}"
