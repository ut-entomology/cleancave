from __future__ import annotations
from typing import TYPE_CHECKING

from src.lib.declared_names_table import DeclaredNamesTable

if TYPE_CHECKING:
    from src.reporter.james_table import *
from src.reporter.record_filter import RecordFilter
from src.reporter.name_column_parser import FOUND_PROPERTY

from src.reporter.reports.report import Report


class AgentsReport(Report):
    def __init__(
        self,
        table: JamesTable,
        record_filter: RecordFilter,
        declared_names_table: DeclaredNamesTable,
    ):
        super().__init__(table, record_filter)
        self._declared_names_table = declared_names_table
        table.revise_names(unify_names_by_sound=True, merge_with_reference_names=True)

    def show(self) -> None:
        self._print_filter_title()
        print("\n---- collectors & determiners ----\n")

        print("(based on an analysis of all names in the spreadsheet)\n")

        includes_synonym = False
        includes_raw_name = False

        # Print the variants and corrections for each primary name.

        synonym_map = self.table.identity_catalog.get_synonyms()
        primary_names = sorted(synonym_map.keys(), key=lambda k: k.lower())
        for primary_name in primary_names:

            # Get the primary identity.

            variant_identities = synonym_map[primary_name]
            primary = variant_identities[0]
            show_this_primary = self._is_filtered_identity(primary)

            # Print the variants and corrections for the primary name.

            variant_identities.sort(key=lambda p: str(p))
            variant_lines: list[tuple[str, list[str]]] = []
            for identity in variant_identities:

                # Determine whether to show this variant.

                if self._is_filtered_identity(identity):
                    show_this_primary = True
                else:
                    continue  # spare us an indentation

                # Collect the variant corrections.

                identity_name = str(identity)
                raw_names = identity.get_raw_names()
                raw_names_to_display: list[str] = []
                if raw_names is None:
                    if identity_name != primary_name:
                        raise Exception("no raw text for '%s'" % identity_name)
                else:
                    for raw_name in raw_names:
                        if raw_name != identity_name:
                            raw_names_to_display.append(raw_name)
                if len(variant_identities) > 1:  # TODO: redundant conditions?
                    if identity_name != primary_name:
                        includes_synonym = True
                        variant_lines.append(
                            ("- %s" % identity_name, self._get_name_notes(identity))
                        )

                # Collect the corrections.

                for raw_name in sorted(raw_names_to_display):

                    # Determine whether to include this raw name in the report.

                    if not self._is_filtered_raw_name(raw_name):
                        continue  # spare us an indentation

                    # Append a note for this raw name.

                    raw_name_line = "  [%s]" % raw_name
                    if self.table.identity_catalog.is_autocorrected_name(raw_name):
                        note = "phonetically autocorrected last name"
                    elif self.table.identity_catalog.is_lexically_modified_name(
                        raw_name
                    ):
                        note = "lexically altered name"
                    else:
                        note = "declared name correction"

                    # Collect the line for this raw name.

                    variant_line = (raw_name_line, [note])
                    if identity_name == primary_name:
                        variant_lines.insert(0, variant_line)
                    else:
                        variant_lines.append(variant_line)
                    includes_raw_name = True
                    show_this_primary = True

            # Print the collected variants for the filter-selected primaries.

            if show_this_primary:
                _print_name(primary_name, self._get_name_notes(primary))
                for variant_line in variant_lines:
                    _print_name(variant_line[0], variant_line[1])

        # Print the legend.

        print()
        if includes_synonym:
            print("- indictates a synonymous variant of the primary name")
        if includes_raw_name:
            print("[name] indicates raw source text, though shown space-normalized")

        # List names from data that failed to parse.

        print("\n==== Errors Parsing Names in Cave Collection ====\n")

        problem_record_count = 0
        for record in self._filtered_records():
            if record.print_name_problems():
                problem_record_count += 1
        if problem_record_count == 0:
            print("No name parsing errors found.\n")
        else:
            print("\n  Found name parsing errors in %d records" % problem_record_count)

        print("\n==== Warnings Parsing Names in Cave Collection ====\n")

        problem_record_count = 0
        for record in self._filtered_records():
            if record.print_name_warnings():
                problem_record_count += 1
        if problem_record_count == 0:
            print("No name parsing warnings found.\n")
        else:
            print(
                "\n  Found name parsing warnings in %d records" % problem_record_count
            )

        # List reference names that failed to parse.

        bad_names = self._declared_names_table.get_bad_reference_names()
        if bad_names:
            print("\n---- Names from Specify that failed to parse ----\n")
            self._print_columns(bad_names)

    def _get_name_notes(self, identity: Identity) -> list[str]:

        notes: list[str] = []

        is_found_data = False
        for property in identity.get_properties():
            if property is FOUND_PROPERTY:
                is_found_data = True
            else:
                notes.append(property.name)

        raw_names = identity.get_raw_names()
        if is_found_data:
            assert raw_names is not None
        else:
            assert raw_names is None, "Unexpected raw names %s" % raw_names
            notes.append("not in data")

        return notes


def _print_name(name_text: str, notes: list[str]) -> None:
    if notes:
        print(name_text.ljust(24, " "), "(%s)" % "; ".join(notes))
    else:
        print(name_text)
