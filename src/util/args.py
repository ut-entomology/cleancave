from typing import Callable, Optional, Union
import os
import sys

ParseFunc = Callable[[str], None]
OptionsDict = dict[Union[str, int, None], ParseFunc]


class ArgException(Exception):
    def __init__(self, message: Optional[str] = None):
        self.message: Optional[str] = message


def expand_filename(filename: str) -> str:
    if filename[0] == ".":
        return os.path.join(os.getcwd(), filename)
    return filename


def parse_args(options: OptionsDict) -> None:

    # Handle the case where there are no command line arguments.

    if len(sys.argv) == 1:
        if None in options:
            options[None]("")
        return  # not necessary, but makes code clearer

    # Parse option arguments and collect filename arguments.

    nonswitch_args: list[str] = []
    for i, arg in enumerate(sys.argv):
        if i == 0:
            continue  # skip name of executing file
        if arg[0] == "-":
            if len(arg) == 1:
                raise ArgException("Argument '-' not recognized")
            option = arg[0:2]
            if option in options:
                option_parser = options[option]
            else:
                raise ArgException("Argument '%s' not recognized" % arg)
            option_arg = arg[2:]
            if len(option_arg) > 0 and option_arg[0] == "=":
                option_arg = option_arg[1:]
            option_parser(option_arg)
        else:
            nonswitch_args.append(arg)

    # Parse arguments not options (not beginning with '-').

    for i in range(len(nonswitch_args)):
        if i in options:
            arg_parser = options[i]
            arg_parser(nonswitch_args[i])
        else:
            raise ArgException("Too many non-option arguments.")
