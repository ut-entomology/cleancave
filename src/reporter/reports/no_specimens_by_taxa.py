from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.reporter.james_table import *
from src.reporter.record_filter import RecordFilter

from src.reporter.reports.by_taxa_report import ByTaxaReport


class NoSpecimensByTaxaReport(ByTaxaReport):
    def __init__(
        self,
        table: JamesTable,
        record_filter: RecordFilter,
    ):
        super().__init__(table, record_filter)

    def show(self) -> None:

        # Collect all the records with zero specimen counts.

        zeros: list[SpecimenRecord] = []

        for record in self._filtered_records():
            if record.specimen_count == 0:
                zeros.append(record)

        # Print the report header.

        self._print_filter_title()
        print("\n==== Zero Specimen Counts, Taxonomically Ordered ====\n")
        if not zeros:
            print("No vials with 0 specimens found.\n")
            return
        self._print_taxon_groups(zeros)
