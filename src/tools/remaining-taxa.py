from __future__ import annotations
import os
from os import path
import sys


class ListRemainingTaxa:
    """Outputs a list of the taxa for which James has not yet requested a problem
    report. It takes a list of all taxa and a directory of files listing jars for
    which problem reports have been requested, and it returns the taxa that remain
    after removing all taxa listed in the directory."""

    def __init__(self, all_taxa_file: str, subtracted_taxa_dir: str):
        self._all_taxa: dict[str, str | None] = self._load_taxa(all_taxa_file)
        self._subtracted_taxa_dir = subtracted_taxa_dir

    def run(self):
        for file in os.listdir(self._subtracted_taxa_dir):
            file_path = path.join(self._subtracted_taxa_dir, file)
            if file.endswith(".txt"):
                taxa = self._load_taxa(file_path)
                for taxon in taxa:
                    self._all_taxa[taxon] = None

        remaining_lines: list[str] = []
        for taxon in self._all_taxa:
            line = self._all_taxa[taxon]
            if line is not None:
                remaining_lines.append(line)

        remaining_lines.sort()
        for line in remaining_lines:
            print(line)

    def _load_taxa(self, filename: str) -> dict[str, str | None]:
        linesByTaxon: dict[str, str | None] = {}
        with open(filename, "r") as file:
            for line in file:
                self._process_line(linesByTaxon, line)
        return linesByTaxon

    def _process_line(self, linesByTaxon: dict[str, str | None], line: str):
        line = line.rstrip()
        clean_line = line.lstrip()
        if clean_line == "" or clean_line[0] in ["#", "-", "+"]:
            return
        taxa = clean_line.split("|")
        taxa_index = len(taxa) - 1
        while taxa_index >= 0:
            taxon = taxa[taxa_index].strip()
            if taxon != "" and taxon[0] != "-" and taxon[0] != "[":
                left_bracket_index = taxon.find("[")
                if left_bracket_index > 0:
                    taxon = taxon[0:left_bracket_index].strip()
                # left_paren_index = taxon.find("(")
                # if left_paren_index >= 0:
                #     right_paren_index = taxon.find(")")
                #     if right_paren_index < 0:
                #         raise Exception("No ')' in %s" % clean_line)
                #     taxon = (
                #         "%s %s"
                #         % (
                #             taxon[0:left_paren_index].strip(),
                #             taxon[right_paren_index + 1].strip()
                #             if right_paren_index + 1 < len(taxon)
                #             else "",
                #         )
                #     ).strip()
                if taxon != "":
                    # if taxon in linesByTaxon:
                    #     raise Exception("Taxon '%s' already listed" % taxon)
                    linesByTaxon[taxon] = clean_line
                    return
            taxa_index -= 1
        raise Exception("Unable to find taxon in line: %s" % clean_line)


def _expand_filename(filename: str) -> str:
    if filename[0] == ".":
        return path.join(path.dirname(__file__), filename)
    return filename


if __name__ == "__main__":
    all_taxa_file: str = "output/taxa-c.txt"
    subtracted_taxa_dir: str = "jars"
    if len(sys.argv) > 1:
        all_taxa_file = sys.argv[1]
    if len(sys.argv) > 2:
        subtracted_taxa_dir = sys.argv[2]
    all_taxa_file = _expand_filename(all_taxa_file)
    subtracted_taxa_dir = _expand_filename(subtracted_taxa_dir)

    ListRemainingTaxa(all_taxa_file, subtracted_taxa_dir).run()
