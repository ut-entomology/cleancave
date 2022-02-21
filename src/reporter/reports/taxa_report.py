from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.reporter.james_table import *
from src.reporter.record_filter import RecordFilter
from src.reporter.taxa import *

from src.reporter.reports.report import Report


class TaxaReport(Report):
    def __init__(
        self,
        table: JamesTable,
        record_filter: RecordFilter,
    ):
        super().__init__(table, record_filter)

    def show(self) -> None:

        # Print taxa in order of first occurrence in the spreadsheet.

        prior_taxon_uniques: dict[str, bool] = {}
        taxa_iterator = TaxaIterator(list(self._filtered_records()))
        for _, records in taxa_iterator:
            taxon_unique = to_taxon_spec(records[0])
            if taxon_unique not in prior_taxon_uniques:
                print(taxon_unique)
                prior_taxon_uniques[taxon_unique] = True

        # Contruct a list of uniques to the left of each rank.

        left_of_rank_uniques: dict[str, list[str]] = {}
        for unique in prior_taxon_uniques:
            taxa = unique.split(" | ")
            i = 1
            while i < len(taxa):
                right_taxon = taxa[i].lower()
                if right_taxon not in [
                    "-",
                    "--",
                    "sp.",
                    "n. sp.",
                    "new genus sp.",
                    "undescribed",
                    "undescribed n. sp.",
                ]:
                    left_taxa = " | ".join(taxa[0:i]).lower()
                    try:
                        left_uniques = left_of_rank_uniques[right_taxon]
                    except KeyError:
                        left_uniques = []
                        left_of_rank_uniques[right_taxon] = left_uniques
                    if left_taxa not in left_uniques:
                        left_uniques.append(left_taxa)
                i += 1

        # Report taxa for which there is more than one left set of taxa.

        for right_taxon, left_taxa in left_of_rank_uniques.items():
            if len(left_taxa) > 1:
                print("\n%s:" % right_taxon)
                for left_unique in left_taxa:
                    print("- %s | %s" % (left_unique, right_taxon))
