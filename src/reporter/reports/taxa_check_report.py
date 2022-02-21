from __future__ import annotations
from typing import TYPE_CHECKING, Union
import re

if TYPE_CHECKING:
    from src.reporter.james_table import *
from src.reporter.record_filter import RecordFilter
from src.reporter.reports.report import Report


class TaxaCheckReport(Report):
    def __init__(
        self,
        table: JamesTable,
        record_filter: RecordFilter,
    ):
        super().__init__(table, record_filter)

    NAME_REGEX = re.compile(r"^[a-zA-Z]+")

    def show(self) -> None:
        print("kingdom,scientificName")
        self._put_line("(phyla)")
        self._put_dictionary(self.table.phyla)
        self._put_line("(classes)")
        self._put_dictionary(self.table.classes)
        self._put_line("(subclasses)")
        self._put_dictionary(self.table.subclasses)
        self._put_line("(orders)")
        self._put_dictionary(self.table.orders)
        self._put_line("(suborders)")
        self._put_dictionary(self.table.suborders)
        self._put_line("(infraorders)")
        self._put_dictionary(self.table.infraorders)
        self._put_line("(families)")
        self._put_dictionary(self.table.families)
        self._put_line("(subfamilies)")
        self._put_dictionary(self.table.subfamilies)
        self._put_line("(genera)")
        self._put_dictionary(self.table.genera)

    def _put_dictionary(self, dictionary: Union[StrCountDict, IdentityDict]):

        # Collect the first word of each name, without duplication.

        dictionary_names: dict[str, bool] = {}
        for raw_name in dictionary:
            matches = self.NAME_REGEX.match(raw_name)
            if matches is not None:
                name = matches.group(0)
                if name not in dictionary_names and name not in [
                    "sp",
                    "undescribed",
                    "Undescribed",
                ]:
                    dictionary_names[name] = True

        # Add the names to the list of taxa in sort order for this group.

        for name in sorted(dictionary_names):
            self._put_line(name)

    def _put_line(self, taxon: str) -> None:
        print("Animalia,%s" % taxon)
