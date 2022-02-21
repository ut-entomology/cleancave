from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.reporter.james_table import *
from src.reporter.record_filter import RecordFilter

from src.reporter.reports.report import Report


class RemarksReport(Report):
    def __init__(
        self,
        table: JamesTable,
        record_filter: RecordFilter,
    ):
        super().__init__(table, record_filter)
        table.revise_names(unify_names_by_sound=True, merge_with_reference_names=True)

    def show(self) -> None:

        self._print_filter_title()
        print("\n==== Remarks on Individual Records ====\n")

        for record in self._filtered_records():
            if record.remarks:
                record._print_issues(record.remarks)  # type: ignore
