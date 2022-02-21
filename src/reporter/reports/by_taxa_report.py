from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.reporter.james_table import *
from src.reporter.record_filter import RecordFilter
from src.reporter.taxa import *

from src.reporter.reports.report import Report


class ByTaxaReport(Report):

    INDENT_SPACES = "    "
    INDENT_LEVELS = [
        "phylum",
        "class",
        "subclass",
        "order",
        "suborder",
        "infraorder",
        "family",
        "subfamily",
        # genus is rolled into species
        "species",
    ]

    def __init__(
        self,
        table: JamesTable,
        record_filter: RecordFilter,
    ):
        super().__init__(table, record_filter)

    def _print_taxon_group(self, taxon_group: TaxonGroup) -> None:

        deltas, record_group = taxon_group

        for rank, taxon in deltas:
            indent_level = self.INDENT_LEVELS.index(rank)
            if taxon is None:
                taxon = NO_TAXON_STR
            elif rank == "species":
                if taxon == NO_TAXON_STR:
                    taxon = "(no genus or species)"
                elif taxon.endswith(" sp."):
                    taxon = "'%s' sp." % taxon[0:-4]
                else:
                    taxon = "'%s'" % taxon
            else:
                taxon = "'%s'" % taxon
            print(
                "%s* %s%s"
                % (
                    indent_level * self.INDENT_SPACES,
                    "" if rank == "species" else rank.capitalize() + " ",
                    taxon,
                )
            )
        print()

        entries: list[str] = []
        for record in record_group:
            entries.append(
                "%d(%d)/%s"
                % (
                    record.catalog_number,
                    record.id,
                    self._to_collection_list(record.collections),
                )
            )
        self._print_columns(entries)

    def _print_taxon_groups(self, records: list[SpecimenRecord]) -> None:

        print("(Lists show catalog numbers with record IDs in parentheses and")
        print(" the first four letters of collection names after the slash.)")

        iterator = TaxaIterator(records)
        first_group = False
        for taxon_group in iterator:
            if first_group:
                first_group = False
            else:
                print("\n--------")
            self._print_taxon_group(taxon_group)
