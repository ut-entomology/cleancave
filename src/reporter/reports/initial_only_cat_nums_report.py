from __future__ import annotations
from typing import TYPE_CHECKING
import re

if TYPE_CHECKING:
    from src.reporter.james_table import *
from src.reporter.record_filter import RecordFilter

from src.reporter.reports.name_cat_nums_report import NameCatNumsReport


class InitialOnlyCatNumsReport(NameCatNumsReport):
    def __init__(
        self,
        table: JamesTable,
        record_filter: RecordFilter,
    ):
        super().__init__(table, record_filter)
        table.revise_names(unify_names_by_sound=True, merge_with_reference_names=True)

    def show(self) -> None:

        self._print_filter_title()
        print("\n==== Catalog numbers for primary names only having initials ====\n")

        INITIALS_ONLY_REGEX = re.compile(
            r"^(?:[A-Z][.] ?)+(?:, ?(?:Jr.|II|III|2nd|3rd))?$"
        )

        names_to_find: list[str] = []
        synonyms = self.table.identity_catalog.get_synonyms()
        for primary in synonyms:
            identity = self.table.identity_catalog.get_identity_by_name(primary)
            label_name = identity.get_fnf_correction().replace(" ", "")
            if self._is_filtered_identity(identity):
                if (
                    label_name.isalpha()
                    and label_name.isupper()
                    or INITIALS_ONLY_REGEX.match(label_name) is not None
                ):
                    names_to_find.append(primary)

        self._print_cat_nums_for_names(names_to_find)
