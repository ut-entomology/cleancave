from __future__ import annotations
import re

from src.reporter.james_table import *
from src.reporter.record_filter import RecordFilter
from src.reporter.reports.report import Report


class OdditiesReport(Report):
    REGEX_NORMAL_TAXON = re.compile(r"^[a-zA-Z ]+$")

    def __init__(
        self,
        table: JamesTable,
        record_filter: RecordFilter,
    ):
        super().__init__(table, record_filter)

    def show(self) -> None:
        self._print_filter_title()
        self._show_oddities("phyla", self.table.phyla)
        self._show_oddities("classes", self.table.classes)
        self._show_oddities("subclasses", self.table.subclasses)
        self._show_oddities("orders", self.table.orders)
        self._show_oddities("suborders", self.table.suborders)
        self._show_oddities("infraorders", self.table.infraorders)
        self._show_oddities("families", self.table.families)
        self._show_oddities("subfamilies", self.table.subfamilies)
        self._show_oddities("genera", self.table.genera)
        self._show_oddities("species", self.table.species)
        self._show_oddities("subspecies", self.table.subspecies)
        # self._show_oddities("continents", self.table.continents)
        # self._show_oddities("countries", self.table.countries)
        # self._show_oddities("states", self.table.states)
        # self._show_oddities("counties", self.table.counties)
        self._show_oddities("type statuses", self.table.type_statuses)
        # self._show_oddities("collections", self.table.collections)
        # self._show_oddities("owners", self.table.owners)

    def _show_oddities(self, name: str, dictionary: StrCountDict):
        print("\n---- %s oddities ----\n" % name)
        if dictionary:
            self._print_columns(
                sorted(
                    self._get_odd_taxa(list(dictionary.keys())),
                    key=lambda x: "" if x is None else x.lower(),
                )
            )
        else:
            print("[empty]")

    def _get_odd_taxa(self, taxa: list[str]):
        oddities: list[str] = []
        for name in taxa:
            match = self.REGEX_NORMAL_TAXON.search(name)
            if match is None or name.find(" ") >= 0:
                if name != EMPTY_TERM:
                    oddities.append(name)

        return oddities

    # def _get_odd_species(self, dictionary: Union[StrCountDict, IdentityDict]):
    #     oddities: list[str] = []
    #     for name in dictionary.keys():
