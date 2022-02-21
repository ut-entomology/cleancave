from __future__ import annotations
from typing import Callable, TYPE_CHECKING

from src.lib.identity import Identity

if TYPE_CHECKING:
    from src.reporter.james_table import *
from src.reporter.record_filter import RecordFilter

from src.reporter.reports.report import Report


class ForeignWordReport(Report):
    def __init__(
        self,
        table: JamesTable,
        record_filter: RecordFilter,
    ):
        super().__init__(table, record_filter)
        table.revise_names(unify_names_by_sound=True, merge_with_reference_names=True)

    def show(self) -> None:

        self._print_filter_title()
        print("\n==== Words containing foreign characters ====\n")

        words: dict[str, list[str]] = {}
        for record in self._filtered_records():
            country_or_state = record.country
            if country_or_state == "USA":
                country_or_state = record.state

            self._add_findings(words, country_or_state, "state", record.state)
            self._add_findings(words, country_or_state, "county", record.county)
            self._add_findings(
                words, country_or_state, "locality(c)", record.locality_correct
            )
            self._add_findings(
                words, country_or_state, "locality(l)", record.locality_on_label
            )
            self._add_findings(
                words, country_or_state, "microhabitat", record.microhabitat
            )
            self._add_findings(
                words,
                country_or_state,
                "collector",
                Identity.get_corrected_primary_names(record.collectors),
            )
            self._add_findings(
                words,
                country_or_state,
                "determiner",
                Identity.get_corrected_primary_names(
                    record.identifier_year.determiners
                ),
            )

        if words:
            longest_word = ""
            for word in words:
                if len(word) > len(longest_word):
                    longest_word = word
            space_buffer = len(longest_word)
            for word, findings in words.items():
                print(
                    "%s%s: %s"
                    % (word, " " * (space_buffer - len(word)), ", ".join(findings))
                )
        else:
            print("No foreign words found.")
        print()

    def _add_findings(
        self,
        words: dict[str, list[str]],
        country_or_state: Optional[str],
        column_name: str,
        value: Optional[str],
    ) -> None:
        is_letter: Callable[[int], bool] = (
            lambda o: o >= 65 and o <= 90 or o >= 97 and o <= 122 or o >= 128
        )
        if value is None:
            return

        # Extract the word surrounding each foreign character.

        for i, c in enumerate(value):
            o = ord(c)
            if o > 127:
                # Determine the word's starting offset.
                start = i
                while start > 0 and is_letter(o):
                    start -= 1
                    o = ord(value[start])
                if not is_letter(o):
                    start += 1
                # Determine the word's ending offset.
                end = i
                o = ord(value[end])
                while end < len(value) and is_letter(o):
                    end += 1
                    if end < len(value):
                        o = ord(value[end])
                # Add the word to the list of words.
                word = value[start:end]
                finding = "%s/%s" % (str(country_or_state), column_name)
                if word in words:
                    findings = words[word]
                    if finding not in findings:
                        findings.append(finding)
                else:
                    words[word] = [finding]
