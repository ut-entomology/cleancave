from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.reporter.james_table import *
from src.reporter.record_filter import RecordFilter

from src.reporter.reports.report import Report


class ProblemReport(Report):
    def __init__(
        self,
        table: JamesTable,
        record_filter: RecordFilter,
        jar_group_uniques: Optional[list[str]],
    ):
        super().__init__(table, record_filter)
        self._jar_group_uniques = jar_group_uniques
        table.revise_names(unify_names_by_sound=True, merge_with_reference_names=True)

    def show(self) -> None:

        self._print_filter_title()

        print("\n==== IDs of Empty Records ====\n")
        messages: list[str] = []

        for line_num in self.table.empty_record_ids:
            messages.append(str(line_num))
        if messages:
            self._print_columns(messages)
        else:
            print("No empty records found.\n")

        print("\n==== Missing Catalog Numbers (across all records) ====\n")

        messages = []
        last_found_cat_num = 0
        in_missing_range = False
        for cat_num in range(1, self.table.max_catalog_number + 1):
            if cat_num in self.table.catalog_numbers_to_records:
                if in_missing_range:
                    if cat_num == last_found_cat_num + 2:
                        messages.append(str(last_found_cat_num + 1))
                    else:
                        messages.append("%d-%d" % (last_found_cat_num + 1, cat_num - 1))
                    in_missing_range = False
                last_found_cat_num = cat_num
            else:
                in_missing_range = True

        if messages:
            self._print_columns(messages)
        else:
            print("No missing catalog numbers.\n")

        print("\n==== Duplicate Catalog Numbers ====\n")
        print("(Lists show catalog numbers with record IDs in parentheses.)\n")

        messages = []
        all_catalog_numbers = sorted(self.table.catalog_numbers_to_records.keys())
        includes_records_not_in_set = False
        includes_dups_both_in_set = False
        for cat_num in all_catalog_numbers:
            if cat_num in self.table.catalog_numbers:
                records = self.table.catalog_numbers_to_records[cat_num]
                if len(records) > 1:  # if there are duplicates
                    records_in_set_count = 0
                    for record in records:
                        if self._record_filter.test(record):
                            records_in_set_count += 1
                    for record in records:
                        suffix = ""
                        if not self._record_filter.test(record):
                            suffix = "^"
                            includes_records_not_in_set = True
                        if records_in_set_count > 1:
                            suffix += "*"
                            includes_dups_both_in_set = True
                        messages.append("%d(%d)%s" % (cat_num, record.id, suffix))
        if messages:
            self._print_columns(messages)
            if includes_dups_both_in_set or includes_records_not_in_set:
                print()
            if includes_dups_both_in_set:
                print("  * both duplicates are in the selected set")
            if includes_records_not_in_set:
                print("  ^ vial is not in the selected set")
        else:
            print("No duplicates found.\n")

        # Report problems found with individual records.

        print("\n==== Problems with Individual Records ====\n")

        problem_record_count = 0
        for record in self._filtered_records():
            if record is not None and record.print_all_problems():
                problem_record_count += 1
        if problem_record_count == 0:
            print("No problems found.\n")
        else:
            print("\n  Found problems in %d records" % problem_record_count)

        # Show warnings associated with each record.

        print("\n==== Warnings for Individual Records ====\n")

        found_warning = False
        for record in self._filtered_records():
            found_warning = record.print_all_warnings() or found_warning

        if not found_warning:
            print("No warnings generated.")

        # Collect the records associated with each warning.

        records_by_name_change: dict[str, list[SpecimenRecord]] = {}
        for record in self._filtered_records():
            if record.name_changes is not None:
                for name_change in record.name_changes:
                    try:
                        records_by_name_change[name_change].append(record)
                    except KeyError:
                        records_by_name_change[name_change] = [record]

        # Print the selected set of jars.

        if self._jar_group_uniques is not None:
            print("\n==== Selected Set of Jars and Vials ====\n")

            for taxon_unique in self._jar_group_uniques:
                print(taxon_unique.strip())
