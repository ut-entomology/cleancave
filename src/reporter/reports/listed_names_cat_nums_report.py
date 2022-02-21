from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.reporter.james_table import *
from src.reporter.record_filter import RecordFilter

from src.reporter.reports.name_cat_nums_report import NameCatNumsReport


class ListedNamesCatNumsReport(NameCatNumsReport):
    def __init__(
        self,
        table: JamesTable,
        record_filter: RecordFilter,
    ):
        super().__init__(table, record_filter)

    def show(self) -> None:
        names_to_find = [
            "Allen, D. L.",
            "B., B.",
            "B., J.",
            "B., J. R.",
            "Balgemann, W.",
            "Barrones, O.",
            "Barth, N.",
            "Bauer, K.",
            "Bauman",
            "Benavides, Alex",
            "Blakley, J.",
            "Boice, N.",
            "Bolando, D.",
            "Bolano, D.",
            "Boyd, R.",
            "Brinkley, M.",
            "Brown",
            "Brown, J. C.",
            "Bryant, B.",
            "Buchanan, J.",
            "Buck, M.",
            "C., M.",
            "Childa, R.",
            "Childs, R.",
            "Clarfield, C.",
            "Clarfield, L.",
            "CM, MS",
            "Collins, R.",
            "Cooper",
            "DMW",
            "Drukker",
            "Gibson, G.",
            "Gray, M.",
            "H., J. R.",
            "Hays County",
            "Herrina, J. L.",
            "Justin",
            "Justin, Hernandez",
            "Lee, C.",
            "McNeilus, V.",
            "McNeilus, V. E.",
            "Mead, J. G.",
            "Prasil",
            "R., W.",
            "Roth",
            "Sanders",
            "Scott",
            "Sherrod",
            "Steve",
            "Szergs, C. R.",
            "Tamiera",
            "Thomas",
            "W., L.",
            "White, R. E.",
            "William",
            "William, L. H.",
            "Williams, J.",
            "Yode",
            "Zimmerman, R.",
        ]

        self._print_filter_title()
        print("\n==== Catalog Numbers for Select Names ====\n")
        self._print_cat_nums_for_names(names_to_find)
