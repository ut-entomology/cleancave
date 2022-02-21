from __future__ import annotations
import os
import sys

from james_names import JamesNamesTable


class MergeJamesNames:
    """Read an existing file of declared names and mark as 'known' each name in
    that file that also occurs in James' name file by appending an exclamation
    point to the name and printing out the new declared names file. Appends two
    exclamation marks if the declared name is only the start of a known name."""

    def __init__(self, james_names_file: str, declared_names_file: str):
        self._known_names = JamesNamesTable(james_names_file).known_names
        self._process_file(declared_names_file)

    def _process_file(self, filename: str) -> None:
        with open(filename, "r") as file:
            for line in file:
                self._process_line(line)

    def _process_line(self, line: str):
        line = line.rstrip()
        clean_line = line.lstrip()
        if clean_line == "" or clean_line[0] == "#" or clean_line[1] == "/":
            print(line)
            return
        if line[0] == "-":
            clean_line = line[1:].strip()
        if clean_line in self._known_names:
            print("%s!" % line)
        else:
            declared_name = False
            for known_name in self._known_names:
                if clean_line.startswith(known_name):
                    print("%s!!" % line)
                    declared_name = True
            if not declared_name:
                print(line)


def _expand_filename(filename: str) -> str:
    if filename[0] == ".":
        return os.path.join(os.path.dirname(__file__), filename)
    return filename


if __name__ == "__main__":
    james_names_file: str = "data/james-names.txt"
    declared_names_file: str = "data/declared-names.txt"
    if len(sys.argv) > 1:
        james_names_file = sys.argv[1]
    if len(sys.argv) > 2:
        declared_names_file = sys.argv[2]
    james_names_file = _expand_filename(james_names_file)
    declared_names_file = _expand_filename(declared_names_file)

    MergeJamesNames(james_names_file, declared_names_file)
