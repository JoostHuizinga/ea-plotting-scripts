__author__ = 'Joost Huizinga'
__version__ = '1.8 (Jun. 27 2019)'

import sys
import shlex
from typing import List, Any, Dict, Union, Callable, Optional
import argparse as ap
import warnings
from createPlotUtils import debug_enabled, debug_print, InputError

###################
#  GLOBAL OPTIONS #
###################
global_options: Dict[str, Union[List[Any], Callable]] = {}
global_alias = {}
global_parser = ap.ArgumentParser()

RETURN_NONE = 1
RETURN_FIRST = 2
RETURN_DEFAULT = 3
RETURN_INDEX = 4
RAISE_EXCEPTION = 5


class NotProvided:
    pass


def custom_cast_to_bool(value):
    if (value == "False" or
            value == "false" or
            value == "0"):
        return False
    elif (value == "True" or
          value == "true" or
          value == "1"):
        return True
    else:
        return bool(value)


def safe_cast(cast, value):
    if value is None:
        return None
    else:
        return cast(value)


def safe_cast_list(cast, value):
    if value is None:
        return None
    else:
        return list(map(cast, value))


def init_options(description, usage, version):
    global_parser.version = version + "\ncreatePlotUtils.py: " + __version__
    global_parser.add_argument('-v', '--version', action='version',
                               version='%(prog)s ' + global_parser.version)
    global_parser.add_argument('-c', '--config_file', nargs='?', type=str,
                               help='Gets all options from the provided config file.')
    global_parser.add_argument("--debug", type=str, nargs='+',
                               help='Enables debug statements.')
    global_parser.add_argument("--warn_err", action='store_true',
                               help='Turns warnings into errors, so you get a stack trace.')
    global_parser.description = description
    global_parser.usage = sys.argv[0] + " " + usage


def add_option(name, value=NotProvided, nargs='+', aliases=None, help_str=""):
    if value == NotProvided:
        value = []
    if not isinstance(value, list) and not hasattr(value, '__call__'):
        value = [value]
    global_parser.add_argument("--" + name, type=str, nargs=nargs, help=help_str)
    global_options[name] = value
    if aliases is not None:
        for alias in aliases:
            global_alias[alias] = name


def add_positional_option(name, value=NotProvided, nargs='+', help_str=""):
    if value == NotProvided:
        value = []
    if not isinstance(value, list) and not hasattr(value, '__call__'):
        value = [value]
    global_parser.add_argument(name, type=str, nargs=nargs, help=help_str)
    global_options[name] = value


def set_glb(name: str, value: Union[List[Any], Callable]):
    """
    Sets the value of the provided option to the provided value without any
    further checks.

    :param name: Name of the option.
    :param value: Value for the option
    """
    global_options[name] = value


def get_glb(name: str) -> Union[List[Any], Callable]:
    """
    Returns the value of the provided option without any further processing.

    :param name: Name of the option.
    :return: Value of the option with the provided "name".
    """
    return global_options[name]


def get_any(name: str, index: int = 0, default: Any = None, when_not_exist: int = RETURN_DEFAULT) -> Any:
    """
    Returns the value of the provided option at the provided index. Does not
    attempt to cast the value to anything.

    :param name: Name of the option.
    :param index: Index for the option.
    :param default: Value to return when the index is out of range and
      "when_not_exist" is set to "RETURN_DEFAULT".
    :param when_not_exist: Strategy on how to behave when the provided index is
      out of range for the option.
    :return: Value of the option with the provided name at the provided index.
    """
    if not get_exists(name, index):
        if when_not_exist == RETURN_DEFAULT:
            return default
        elif when_not_exist == RETURN_FIRST:
            return get_any(name, 0, default)
        elif when_not_exist == RETURN_NONE:
            return None
        elif when_not_exist == RETURN_INDEX:
            return index
        elif when_not_exist == RAISE_EXCEPTION:
            raise IndexError(f"Index {index} out of range for option {name} "
                             f"with {len(global_options[name])} values.")
        else:
            raise ValueError(f"{when_not_exist} is not a valid strategy.")
    return global_options[name][index]


def get_str(
        name: str,
        index: int = 0,
        default: Optional[str] = None,
        when_not_exist: int = RETURN_DEFAULT
) -> Optional[str]:
    value = safe_cast(str, get_any(name, index, default, when_not_exist))
    if not get_exists(name, index) and when_not_exist == RETURN_INDEX:
        value = "undefined-" + value
    return value


def get_bool(
        name: str,
        index: int = 0,
        default: Optional[bool] = False,
        when_not_exist: int = RETURN_DEFAULT
) -> Optional[bool]:
    return safe_cast(custom_cast_to_bool, get_any(name, index, default, when_not_exist))


def get_int(
        name: str,
        index: int = 0,
        default: Optional[int] = 0,
        when_not_exist: int = RETURN_DEFAULT
) -> Optional[int]:
    return safe_cast(int, get_any(name, index, default, when_not_exist))


def get_float(
        name: str,
        index: int = 0,
        default: Optional[float] = 0,
        when_not_exist: int = RETURN_DEFAULT
) -> Optional[float]:
    return safe_cast(float, get_any(name, index, default, when_not_exist))


def get_list(
        name: str,
        index: int = 0,
        default: Optional[List] = None,
        when_not_exist: int = RETURN_DEFAULT
) -> Optional[List]:
    value = get_any(name, index, default, when_not_exist)
    if not isinstance(value, list) and value is not None:
        value = [value]
    return value


def get_float_list(
        name: str,
        index: int = 0,
        default: Optional[List[float]] = None,
        when_not_exist: int = RETURN_DEFAULT
) -> Optional[List[float]]:
    return safe_cast_list(float, get_list(name, index, default, when_not_exist))


def get_int_list(
        name: str,
        index: int = 0,
        default: Optional[List[int]] = None,
        when_not_exist: int = RETURN_DEFAULT
) -> Optional[List[int]]:
    return safe_cast_list(int, get_list(name, index, default, when_not_exist))


def get_bool_list(
        name: str,
        index: int = 0,
        default: Optional[List[bool]] = None,
        when_not_exist: int = RETURN_DEFAULT
) -> Optional[List[bool]]:
    return safe_cast_list(custom_cast_to_bool, get_list(name, index, default, when_not_exist))


def get_str_list(
        name: str,
        index: int = 0,
        default: Optional[List[str]] = None,
        when_not_exist: int = RETURN_DEFAULT
) -> Optional[List[str]]:
    return safe_cast_list(str, get_list(name, index, default, when_not_exist))


def get_exists(name, index=0):
    return index < len(global_options[name])


def get_indices(name):
    return list(range(len(global_options[name])))


def read_config(config_file_name):
    global global_options
    default_overwritten = {}
    with open(config_file_name, 'r') as config_file:
        for line in config_file:
            debug_print("options", "Reading line:", line)
            if line[0] == "#":
                continue
            words = shlex.split(line)
            if len(words) == 0:
                continue
            elif len(words) == 1:
                # print "Error: word \"" + str(words[0]) + "\" has no parameters"
                raise InputError("word \"" + str(words[0]) + "\" has no parameters")
            if words[0] in global_alias:
                key = global_alias[words[0]]
            else:
                key = words[0]

            if len(words[1:]) == 1:
                # If we get one value, we assume it is supposed to be a single value
                value = words[1]
            else:
                # Otherwise we assume the value for this argument is a list
                value = words[1:]

            if key not in default_overwritten:
                debug_print("options", "key:", key, "default:", global_options[key], "overwriting with:", words[1:])
                global_options[key] = [value]
                default_overwritten[key] = True
            else:
                debug_print("options", "key:", key, "current options:", global_options[key], "adding:", words[1:])
                global_options[key].append(value)


def parse_global_options(command_line_args):
    args = global_parser.parse_args(command_line_args)

    if args.warn_err:
        warnings.simplefilter("error")

    if args.debug:
        for arg in args.debug:
            debug_enabled[arg] = True

    # Retrieve values from the config file
    set_glb("config_file", [])
    if args.config_file:
        read_config(args.config_file)
        set_glb("config_file", [args.config_file])

    # Retrieve values from the provided options, overwriting defaults and config settings
    arg_dict = vars(args)
    for option in arg_dict.items():
        key, _ = option
        if arg_dict[key]:
            value = arg_dict[key]
            if not isinstance(value, list):
                value = [value]
            set_glb(key, value)

    # If an option has a derived default, and the default was not overwritten, use the derived default
    for option in global_options.items():
        key, value = option
        if hasattr(value, '__call__'):
            while hasattr(value, '__call__'):
                function = value
                value = function()
            if not isinstance(value, list):
                value = [value]
            set_glb(key, value)
