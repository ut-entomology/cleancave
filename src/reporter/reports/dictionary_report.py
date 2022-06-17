from __future__ import annotations
from typing import TYPE_CHECKING, Union

if TYPE_CHECKING:
    from src.reporter.james_table import *
from src.reporter.record_filter import RecordFilter

from src.reporter.reports.report import Report


class DictionaryReport(Report):
    def __init__(
        self,
        table: JamesTable,
        record_filter: RecordFilter,
    ):
        super().__init__(table, record_filter)

    def show(self) -> None:
        self._print_filter_title()
        self._show_dictionary("phyla", self.table.phyla)
        self._show_dictionary("classes", self.table.classes)
        self._show_dictionary("subclasses", self.table.subclasses)
        self._show_dictionary("orders", self.table.orders)
        self._show_dictionary("suborders", self.table.suborders)
        self._show_dictionary("infraorders", self.table.infraorders)
        self._show_dictionary("families", self.table.families)
        self._show_dictionary("subfamilies", self.table.subfamilies)
        self._show_dictionary("genera", self.table.genera)
        self._show_dictionary("species", self.table.species)
        self._show_dictionary("genus-species", self.table.genus_species)
        self._show_dictionary("species-subspecies", self.table.species_subspecies)
        self._show_dictionary("authors", self.table.authors)
        self._show_dictionary("continents", self.table.continents)
        self._show_dictionary("countries", self.table.countries)
        self._show_dictionary("states", self.table.states)
        self._show_dictionary("counties", self.table.counties)
        self._show_dictionary("type statuses", self.table.type_statuses)
        self._show_dictionary("collections", self.table.collections)
        self._show_dictionary("owners", self.table.owners)

    def _show_dictionary(
        self, name: str, dictionary: Union[StrCountDict, IdentityDict]
    ):
        print("\n---- %s dictionary ----\n" % name)
        if dictionary:
            self._print_columns(
                sorted(dictionary.keys(), key=lambda x: "" if x is None else x.lower())
            )
        else:
            print("[empty]")
