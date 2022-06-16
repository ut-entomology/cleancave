from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.reporter.james_table import *
from src.reporter.record_filter import RecordFilter
from src.reporter.taxa import *

from src.reporter.reports.report import Report


class TaxaByDupsReport(Report):
    def __init__(
        self,
        table: JamesTable,
        record_filter: RecordFilter,
    ):
        super().__init__(table, record_filter)

    def show(self) -> None:

        # Collect all the records with duplicate catalog numbers.

        dups: list[SpecimenRecord] = []
        dup_cat_num_count = 0

        for record_set in self.table.catalog_numbers_to_records.values():
            if len(record_set) > 1:
                for record in record_set:
                    if self._record_filter.test(record):
                        dup_cat_num_count += 1
                        dups += record_set
                        break

        dups.sort(key=lambda r: r.catalog_number)  # type: ignore

        # Print the report header.

        self._print_filter_title()
        print("\n==== Duplicate Catalog Numbers with Taxa ====\n")
        if not dups:
            print("No duplicates found.\n")
            return
        print(
            "Found %d duplicated catalog numbers spanning %d records."
            % (dup_cat_num_count, len(dups))
        )
        print(
            "\n(The first four letters of collection names are shown after the slash.)"
        )

        # List taxa_line for each catalog number.

        NONE = "—"  # em dash
        SEP = ", "
        last_cat_num: int = -1
        for record in dups:
            assert record.catalog_number is not None
            if record.catalog_number != last_cat_num:
                print("\nCat no. %d:" % record.catalog_number)

            taxa_line = "  ID %d/%s: " % (
                record.id,
                self._to_collection_list(record.collections),
            )

            if record.phylum is None:
                taxa_line += NONE
            else:
                taxa_line += "'%s'" % record.phylum
            taxa_line += SEP

            if record.class_ is None:
                taxa_line += NONE
            else:
                taxa_line += "'%s'" % record.class_
            taxa_line += SEP

            if record.subclass is None:
                taxa_line += NONE
            else:
                taxa_line += "'%s'" % record.subclass
            taxa_line += SEP

            if record.order is None:
                taxa_line += NONE
            else:
                taxa_line += "'%s'" % record.order
            taxa_line += SEP

            if record.suborder is None:
                taxa_line += NONE
            else:
                taxa_line += "'%s'" % record.suborder
            taxa_line += SEP

            if record.infraorder is None:
                taxa_line += NONE
            else:
                taxa_line += "'%s'" % record.infraorder
            taxa_line += SEP

            if record.family is None:
                taxa_line += NONE
            else:
                taxa_line += "'%s'" % record.family
            taxa_line += SEP

            if record.subfamily is None:
                taxa_line += NONE
            else:
                taxa_line += "'%s'" % record.subfamily
            taxa_line += SEP

            genus_species = to_clean_genus_species(
                record.genus, record.species, record.subspecies
            )
            if genus_species == NO_TAXON_STR:
                genus_species = NONE
            elif genus_species.endswith("sp."):
                genus_species = "'%s' sp." % genus_species[0:-4]
            else:
                genus_species = "'%s'" % genus_species
            taxa_line += genus_species

            print(taxa_line)
            last_cat_num = record.catalog_number
