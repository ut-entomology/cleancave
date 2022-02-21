from __future__ import annotations
from typing import TYPE_CHECKING
import re

if TYPE_CHECKING:
    from src.reporter.james_table import *
from src.reporter.record_filter import RecordFilter
from src.reporter.name_column_parser import NameColumnParser

from src.reporter.reports.report import Report


class NameCheckReport(Report):

    INITIAL_REGEX = re.compile(r"[a-z][.]")
    JR_SR_REGEX = re.compile(r"[js]r[. ]")
    CHAR_REGEX = re.compile(r"[`.,;&/()?]")
    NUMBER_REGEX = re.compile(r"[0-9]+")
    SPACE_REGEX = re.compile(r"  +")

    PRECONFIRMED_NAMES_MAP: dict[str, str] = {
        "B., J": "Brooks",
    }

    def __init__(
        self,
        table: JamesTable,
        record_filter: RecordFilter,
        more_first_names_file: str,
    ):
        super().__init__(table, record_filter)
        self.declared_names_table = table.declared_names_table
        table.revise_names(unify_names_by_sound=True, merge_with_reference_names=True)

        # Build a consolidated list of preconfirmed names.

        self._preconfirmed_names_map: dict[str, str] = {}
        self._preconfirmed_names_map.update(
            table.declared_names_table.raw_correction_last_names
        )
        self._preconfirmed_names_map.update(self.PRECONFIRMED_NAMES_MAP)

        # Construct a list of first names and misspellings of first names that need
        # to be excluded from the check of last names.

        self._more_first_names: dict[str, bool] = {}
        with open(more_first_names_file, "r") as file:
            for first_name in file:
                self._more_first_names[first_name.strip()] = True

        # Construct a map of all raw last names to their various deduced corrections.
        # One raw name may have different corrections for different initial names.
        # Both raw name key and deduced last names are in lowercase, but the raw name
        # is processed to turn it into the last names expected for comparison. The map
        # is constructed from the deduced result of the parse and consolidation.

        self._last_name_corrections: dict[str, list[str]] = {}
        synonym_map = table.identity_catalog.get_synonyms()
        last_name_issues = False
        for variants in synonym_map.values():
            corrected_last_name = variants[0].last_name.lower()
            for variant in variants:
                if not self._is_filtered_identity(variant):
                    continue  # spare us an indendation
                raw_names = variant.get_raw_names()
                if raw_names is not None:
                    for raw_name in raw_names:
                        raw_name = raw_name.replace("?", "").strip()
                        try:
                            raw_last_names = [
                                self._preconfirmed_names_map[raw_name].lower()
                            ]
                        except KeyError:
                            raw_last_names = self._to_lower_last_names(raw_name)
                        if len(raw_last_names) == 0:
                            print(
                                "* no raw last names in [%s] for [%s]"
                                % (raw_name, str(variant))
                            )
                            last_name_issues = True
                        else:
                            if len(raw_last_names) > 1:
                                # The first name could also be a last name; we'll
                                # confirm the first name on generating the report.
                                raw_last_name = variant.last_name.lower()
                            else:
                                raw_last_name = raw_last_names[0]
                            try:
                                self._last_name_corrections[raw_last_name].append(
                                    corrected_last_name
                                )
                            except KeyError:
                                self._last_name_corrections[raw_last_name] = [
                                    corrected_last_name
                                ]
        if last_name_issues:
            raise Exception("please eliminate the last name issues")

    def show(self) -> None:

        self._print_filter_title()
        print("\n==== Name Check Report ====\n")
        count: int = 0

        for record in self._filtered_records():
            collector_diffs = self._check_names(
                record.raw_collectors, record.collectors
            )
            determiner_diffs = self._check_names(
                record.raw_identifier_year,
                record.identifier_year.determiners,
            )
            if collector_diffs or determiner_diffs:
                print("ID/Cat No. %d/%s:" % (record.id, str(record.catalog_number)))
                if collector_diffs:
                    self._print_diffs(
                        "collectors", record.raw_collectors, collector_diffs
                    )
                if determiner_diffs:
                    self._print_diffs(
                        "determiners", record.raw_identifier_year, determiner_diffs
                    )
                print()
                count += 1

        if count == 0:
            print("Confirmed all names.\n")

    def _check_names(
        self, raw_names: str, identities: Optional[list[Identity]]
    ) -> list[str]:

        # Normalize the raw column string and replace name substrings, where
        # possible, with the last names to which they are definitively mapped.
        # This provides last names for strings that otherwise don't have them.

        # original_raw_names = raw_names
        raw_names = NameColumnParser.preprocess_raw_column(raw_names)
        raw_names = NameColumnParser.preprocess_raw_name(raw_names)
        for (confirmed_raw, confirmed_last) in self._preconfirmed_names_map.items():
            start_offset = raw_names.find(confirmed_raw)
            if start_offset >= 0:
                end_offset = start_offset + len(confirmed_raw)
                start_offset -= 1
                while start_offset >= 0 and raw_names[start_offset] == " ":
                    start_offset -= 1
                if start_offset >= 0 and raw_names[start_offset] not in ",;":
                    continue
                end_offset += 1
                while end_offset < len(raw_names) and raw_names[end_offset] == " ":
                    end_offset += 1
                if end_offset < len(raw_names) and raw_names[end_offset] not in ",;":
                    continue
                raw_names = raw_names.replace(confirmed_raw, confirmed_last, 1)

        # Collect the possible last names from the prepared raw column string.

        raw_last_names: list[str] = []
        pared_names = self._to_lower_last_names(raw_names)
        for name in pared_names:
            if self._is_possible_last_name(name) and name not in raw_last_names:
                raw_last_names.append(name)

        # Construct a list of the deduced last names, in lowercase, against which
        # we'll check the raw last names in the raw column string.

        deduced_last_names: list[str] = []
        if identities is not None:
            for identity in identities:
                deduced_last_name = identity.get_master_copy().last_name.lower()
                if deduced_last_name not in deduced_last_names:
                    deduced_last_names.append(deduced_last_name)

        # For each raw name, look for one of the accepted corrections to the
        # raw name among the deduced names. If present, remove that deduced
        # name from the list of deduced names that need to be matched; if not
        # present, see if the name is actually an initial name, and if not,
        # report that the raw name has no corresponding deduced name.

        diffs: list[str] = []
        for raw_last_name in raw_last_names:
            error: Optional[str] = None

            try:
                corrections = self._last_name_corrections[raw_last_name]
                found_deduced_last_name = False
                for correction in corrections:
                    if correction in deduced_last_names:
                        deduced_last_names.remove(correction)
                        found_deduced_last_name = True
                        break
                if not found_deduced_last_name:
                    error = "raw name [%s] not matched to variant" % raw_last_name
            except KeyError:
                # if (
                #     original_raw_names == "Tucek, Heather; Shaw, Justin"
                #     and raw_last_name == "pursley"
                # ):
                #     raise Exception(
                #         "found it \n%s\n%s\n%s\n%s"
                #         % (
                #             original_raw_names,
                #             raw_names,
                #             raw_last_names,
                #             deduced_last_names,
                #         )
                #     )
                error = "raw name [%s] has no variants" % raw_last_name

            if error is not None and identities is not None and len(raw_last_name) > 1:
                found_first_name = False
                for identity in identities:
                    initial_names = identity.initial_names
                    if initial_names is not None:
                        initial_names = initial_names.lower()
                        if initial_names.startswith(raw_last_name):
                            found_first_name = True
                        elif (" " + raw_last_name) in initial_names:
                            found_first_name = True
                if not found_first_name:
                    diffs.append(error)

        # Report names deduced for the column value that were not matched to
        # raw names in the column value.

        for deduced_last_name in deduced_last_names:
            diffs.append("raw name not found for variant [%s]" % deduced_last_name)

        # if len(raw_last_names) != len(deduced_last_names):
        #     diffs.append(
        #         "%d name(s) in source [%s], %d in results [%s]"
        #         % (
        #             len(raw_last_names),
        #             ", ".join(raw_last_names),
        #             len(deduced_last_names),
        #             ", ".join(deduced_last_names),
        #         )
        #     )

        return diffs

    def _is_known_first_name(self, name: str) -> bool:
        return (
            self.declared_names_table.is_declared_first_name(name)
            or name in self._more_first_names
        )

    def _is_possible_last_name(self, name: str) -> bool:
        return len(name) > 1 and (
            self.declared_names_table.is_declared_last_name(name)
            or not self._is_known_first_name(name)
        )

    def _print_diffs(self, name_set: str, raw_names: str, diffs: list[str]) -> None:
        print("* %s [%s]" % (name_set, raw_names))
        for diff in diffs:
            print("  - %s" % diff)

    def _to_lower_last_names(self, raw_text: str) -> list[str]:
        pared_str = self.INITIAL_REGEX.sub(" ", raw_text.lower())
        pared_str = self.JR_SR_REGEX.sub(" ", pared_str)
        pared_str = self.CHAR_REGEX.sub(" ", pared_str)
        pared_str = pared_str.replace("iii", " ").replace("van ", " ")
        pared_str = self.NUMBER_REGEX.sub(" ", pared_str)  # det year
        pared_str = self.SPACE_REGEX.sub(" ", pared_str)

        last_names: list[str] = []
        for name in pared_str.strip().split(" "):
            if self._is_possible_last_name(name):
                last_names.append(name)
        return last_names
