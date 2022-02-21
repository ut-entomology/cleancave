from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.reporter.james_table import *
from src.reporter.record_filter import RecordFilter

from src.reporter.reports.report import Report


class NameCatNumsReport(Report):
    def __init__(
        self,
        table: JamesTable,
        record_filter: RecordFilter,
    ):
        super().__init__(table, record_filter)
        table.revise_names(unify_names_by_sound=True, merge_with_reference_names=True)

    def _print_cat_nums_for_names(self, names_to_find: list[str]) -> None:

        # + cat num means collector; - cat num means determiner
        cat_nums_by_name: dict[str, list[Optional[int]]] = {}

        print("A suffix of 'c' means that the name is a collector.")
        print("A suffix of 'd' means that the name is a determiner/identifier.")
        print("A suffix of 'cd' means the determiner is the collector.")
        print()

        for record in self._filtered_records():
            if record.collectors is not None:
                for identity in record.collectors:
                    try:
                        cat_nums_by_name[str(identity)].append(record.catalog_number)
                    except KeyError:
                        cat_nums_by_name[str(identity)] = [record.catalog_number]
            if record.identifier_year.determiners is not None:
                for identity in record.identifier_year.determiners:
                    cat_num = record.catalog_number
                    if cat_num is not None:
                        cat_num *= -1
                    try:
                        cat_nums_by_name[str(identity)].append(cat_num)
                    except KeyError:
                        cat_nums_by_name[str(identity)] = [cat_num]

        for name in names_to_find:
            found_cat_nums: list[str] = []
            if name in cat_nums_by_name:
                abs_cat_nums: list[Optional[int]] = []
                suffixes: list[str] = []
                for cat_num in cat_nums_by_name[name]:
                    if cat_num is None:
                        abs_cat_nums.append(None)
                    elif cat_num > 0:
                        abs_cat_nums.append(cat_num)
                        suffixes.append("c")
                    else:
                        cat_num = abs(cat_num)
                        if not abs_cat_nums or abs_cat_nums[-1] != cat_num:
                            suffixes.append("d")
                            abs_cat_nums.append(cat_num)
                        else:
                            suffixes[-1] = "cd"
                for i in range(len(abs_cat_nums)):
                    found_cat_nums.append("%d/%s" % (abs_cat_nums[i], suffixes[i]))
            else:
                found_cat_nums.append("NAME NOT FOUND")
            print('"%s": %s' % (name, ", ".join(found_cat_nums)))
