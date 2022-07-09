from __future__ import annotations
import os

import src.util.args as args
from src.lib.declared_names_table import DeclaredNamesTable
from james_table import JamesTable
from record_filter import *
from reports.report import *
from reports.agents_report import *
from reports.county_localities import *
from reports.dictionary_report import *
from reports.dups_by_taxa_report import *
from reports.foreign_word_report import *
from reports.initial_only_cat_nums_report import *
from reports.label_report import *
from reports.lat_long_report import *
from reports.listed_names_cat_nums_report import *
from reports.name_cat_nums_report import *
from reports.name_check_report import *
from reports.no_specimens_by_taxa import *
from reports.oddities_report import *
from reports.problem_report import *
from reports.remarks_report import *
from reports.specify_workbench_report import *
from reports.taxa_by_dups_report import *
from reports.taxa_check_report import *
from reports.taxa_report import *
from reports.tss_csv_report import *
from reports.normalized_csv_report import *


class Norm:
    """Main program for normalizing James' spreadsheet data."""

    def __init__(self):
        self._specimen_csv_file = "unspecified"
        self._lat_longs_csv_file: str
        self._declared_names_file = args.expand_filename("data/declared-names.txt")
        self._reference_names_file = args.expand_filename("data/reference-names.csv")
        self._more_first_names_file = args.expand_filename("data/more-first-names.txt")
        self._report_code: str = ""
        self._record_filters: list[RecordFilter] = []
        self._jar_group_uniques: Optional[list[str]] = None
        self._make_printable = False
        self._restricted_to_texas = False

    def main(self) -> None:
        # fmt: off
        info = (
            "Normalizes James' cave data spreadsheet.\n"
            "  args: [-c|-f|-n|-t|-x] [-r<report-letters>] [-p] <specimen_csv>\n"
            "\n"
            "-c restrict report to just cave data\n"
            "-f=<family-name> restrict report to just cave records in this family\n"
            "-n restrict report to just non-cave data\n"
            "-p create a printable report (of labels)\n"
            "-r reports to print: A=agents, F=foreign characters, C=lat/long coords,\n"
                "D=dictionaries, L=labels, M=mashed labels, N=normalized CSV, O=oddities,\n"
                "P=problems, QN=name check, QT=taxa check, R=remarks, T=TSS CSV,\n"
                "U=cat nums for names, V=cat nums for initials,\n"
                "W=CSV for Specify Workbench, X=taxa, Y=taxa by dups, Z=dups by taxon,\n"
                "0=0 specimen counts by taxa, AC=collectors, DC=localities per county\n"
            "-t restrict report to just Texas cave data\n"
            "-x=<taxa-file> restrict report to just the taxa in this file\n"
            "<specimen_csv> is the path to a CSV file of specimens. 'reference-lat-longs.csv'\n"
            "  is expected to be in the same directory, providing lat/long accuracy info.\n"
            "\n"
            "<min-max> = <min-required-label-lines>-<max-usable-label-lines>\n"
            "Use cat num. '_END_' to end table before the end of the CSV file.\n"
        )
        # fmt: on

        options: args.OptionsDict = {
            "-c": self._parse_cave_report,
            "-f": self._parse_cave_family_report,
            "-n": self._parse_noncave_report,
            "-p": self._parse_make_printable,
            "-r": self._parse_report_type,
            "-t": self._parse_texas_cave_report,
            "-x": self._parse_taxa_filter,
            0: self._parse_specimen_csv,
            None: self._parse_no_arguments,
        }
        try:
            # Parse the input data and generate the table.

            args.parse_args(options)
            decls = DeclaredNamesTable(
                self._declared_names_file, self._reference_names_file
            )
            table = JamesTable(self._lat_longs_csv_file, self._specimen_csv_file, decls)
            table.load()

            # Construct the report filter.

            filter = AllRecordsFilter()
            if len(self._record_filters) == 1:
                filter = self._record_filters[0]
            elif len(self._record_filters) > 1:
                filter = CompoundRecordFilter(self._record_filters)
            if self._jar_group_uniques and self._restricted_to_texas:
                raise args.ArgException("Can't combine -t with -x")

            # Construct and show the report. Done after reading all arguments so
            # that the filters are available.

            if self._report_code == "":
                raise args.ArgException("No report specified")
            elif self._report_code == "A":
                report = AgentsReport(table, filter, decls, False)
            elif self._report_code == "AC":
                report = AgentsReport(table, filter, decls, True)
            elif self._report_code == "C":
                report = LatLongReport(table, filter, True)
            elif self._report_code == "D":
                report = DictionaryReport(table, filter)
            elif self._report_code == "DC":
                report = CountyLocalitiesReport(table, filter)
            elif self._report_code == "F":
                report = ForeignWordReport(table, filter)
            elif self._report_code == "L":
                report = LabelReport(
                    table,
                    filter,
                    self._jar_group_uniques,
                    decls,
                    LabelReport.Type.ALL,
                    self._make_printable,
                )
            elif self._report_code == "M":
                report = LabelReport(
                    table,
                    filter,
                    self._jar_group_uniques,
                    decls,
                    LabelReport.Type.MASHED,
                    self._make_printable,
                )
            elif self._report_code == "N":
                report = NormalizedCsvReport(table, filter)
            elif self._report_code == "O":
                report = OdditiesReport(table, filter)
            elif self._report_code == "P":
                report = ProblemReport(
                    table,
                    filter,
                    self._jar_group_uniques,
                )
            elif self._report_code == "QN":
                report = NameCheckReport(table, filter, self._more_first_names_file)
            elif self._report_code == "QT":
                report = TaxaCheckReport(table, filter)
            elif self._report_code == "R":
                report = RemarksReport(table, filter)
            elif self._report_code == "T":
                report = TssCsvReport(table, filter)
            elif self._report_code == "U":
                report = ListedNamesCatNumsReport(table, filter)
            elif self._report_code == "V":
                report = InitialOnlyCatNumsReport(table, filter)
            elif self._report_code == "W":
                report = SpecifyWorkbenchReport(table)
            elif self._report_code == "X":
                report = TaxaReport(table, filter)
            elif self._report_code == "Y":
                report = TaxaByDupsReport(table, filter)
            elif self._report_code == "Z":
                report = DupsByTaxaReport(table, filter)
            elif self._report_code == "0":
                report = NoSpecimensByTaxaReport(table, filter)
            else:
                raise args.ArgException(
                    "Urecognized report type '%s'" % self._report_code
                )

            report.show()

        except args.ArgException as e:
            if e.message:
                print(e.message)
            print()
            print(info)

    def _parse_make_printable(self, arg: str) -> None:
        self._make_printable = True

    def _parse_specimen_csv(self, arg: str) -> None:
        self._specimen_csv_file = args.expand_filename(arg)
        self._lat_longs_csv_file = os.path.join(
            os.path.dirname(self._specimen_csv_file), "reference-lat-longs.csv"
        )

    def _parse_cave_report(self, _arg: str) -> None:
        self._record_filters.append(CaveRecordFilter())

    def _parse_cave_family_report(self, arg: str) -> None:
        self._record_filters.append(CaveFamilyRecordFilter(arg))

    def _parse_texas_cave_report(self, _arg: str) -> None:
        self._record_filters.append(TexasCaveRecordFilter())
        self._restricted_to_texas = True

    def _parse_noncave_report(self, _arg: str) -> None:
        self._record_filters.append(NonCaveRecordsFilter())

    def _parse_report_type(self, arg: str) -> None:
        self._report_code = arg.upper()

    def _parse_taxa_filter(self, arg: str) -> None:
        self._jar_group_uniques = _load_file(args.expand_filename(arg))
        self._record_filters.append(TaxaFilter(self._jar_group_uniques))

    def _parse_no_arguments(self, _arg: str) -> None:
        raise args.ArgException()


def _load_file(file_path: str) -> list[str]:
    lines: list[str] = []
    with open(file_path, "r") as file:
        for line in file:
            lines.append(line)
    return lines


if __name__ == "__main__":
    Norm().main()
