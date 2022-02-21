from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.reporter.james_table import *
from src.reporter.record_filter import RecordFilter

from src.reporter.reports.by_taxa_report import ByTaxaReport


class DupsByTaxaReport(ByTaxaReport):
    def __init__(
        self,
        table: JamesTable,
        record_filter: RecordFilter,
    ):
        super().__init__(table, record_filter)

    def show(self) -> None:

        # Collect all the records with duplicate catalog numbers.

        dups: list[SpecimenRecord] = []

        for record_set in self.table.catalog_numbers_to_records.values():
            if len(record_set) > 1:
                for record in record_set:
                    if self._record_filter.test(record):
                        dups += record_set
                        break

        # Print the report header.

        self._print_filter_title()
        print("\n==== Duplicate Catalog Numbers, Taxonomically Ordered ====\n")
        if not dups:
            print("No duplicates found.\n")
            return
        self._print_taxon_groups(dups)
