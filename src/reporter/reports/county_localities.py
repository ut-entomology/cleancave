from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.reporter.james_table import *
from src.reporter.record_filter import RecordFilter

from src.reporter.reports.report import Report


class CountyLocalitiesReport(Report):
    def __init__(
        self,
        table: JamesTable,
        record_filter: RecordFilter,
    ):
        super().__init__(table, record_filter)

    def show(self) -> None:
        self._print_filter_title()

        counties = list(self.table.countyLocalities.keys())
        counties.sort(key=lambda county: "" if county is None else county)
        for county in counties:
            if county is None:
                print("(no county):")
            else:
                print(county + " County:")
            localities = self.table.countyLocalities[county]
            localities.sort(key=lambda county: county)
            for locality in localities:
                print("+ " + locality)
            print()
