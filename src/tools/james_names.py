from __future__ import annotations
import re

from src.lib.identity_parser import IdentityParser


class JamesNamesTable:
    """Constructs a table of known names from a file in the format that James has
    been using to track names. Each line of the file indicates a name, up until a
    line beginning with '---'. Lines beginning with '*', '!', or '^' are ignored.
    Names ending with ("aka Another Name") designate an alternate name that is not
    the identity primary name. Everything after '/' on a line is ignored."""

    SKIP_DESIGNATORS = "*^!"
    AKA_SELECTOR = re.compile(r"([^(]+)(?:\(aka ([^)]+)\))?")

    def __init__(self, james_names_file: str):
        self.known_names: list[str] = []
        self._name_variants: dict[str, list[str]] = {}
        self._ignore_remainder: bool = False
        self._line_number: int = 1
        self._load_file(james_names_file)

    def print_names(self) -> None:
        official_names = sorted(self._name_variants.keys())
        for official_name in official_names:
            print(official_name)
            variants = self._name_variants[official_name]
            for variant in variants:
                print("- %s" % variant)

    def _load_file(self, filename: str) -> None:
        with open(filename, "r") as file:
            for line in file:
                if not self._ignore_remainder:
                    self._load_line(line)

    def _load_line(self, line: str):
        slash_offset = line.find("/")
        if slash_offset >= 0:
            line = line[0:slash_offset]

        line = line.strip()
        if line.startswith("---"):
            self._ignore_remainder = True
        elif line != "" and line[0] not in self.SKIP_DESIGNATORS:

            matches = self.AKA_SELECTOR.findall(line)[0]
            line_identity = IdentityParser(matches[0]).parse()
            assert line_identity is not None

            # First name in line is the primary name.

            official_name = str(line_identity[0])
            self.known_names.append(official_name)

            # "aka" name in the line designates a secondary name.

            if matches[1] == "":
                self._name_variants[official_name] = []
            else:
                line_identity = IdentityParser(matches[1]).parse()
                assert line_identity is not None
                aka_name = str(line_identity[0])
                self._name_variants[official_name] = [aka_name]
                self.known_names.append(aka_name)

        self._line_number += 1
