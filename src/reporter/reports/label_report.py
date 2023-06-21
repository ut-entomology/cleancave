from __future__ import annotations
from typing import TYPE_CHECKING
from datetime import date
from decimal import Decimal
from enum import Enum
import os
import re

from matplotlib.afm import AFM
from pathlib import Path

from src.lib.declared_names_table import DeclaredNamesTable
from src.lib.identity import Identity
from src.lib.identity_parser import IdentityParser
from src.util.states import States
from src.lib.parse_error import ParseError

if TYPE_CHECKING:
    from src.reporter.james_table import *
from src.reporter.record_filter import RecordFilter
from src.reporter.specimen_record import SpecimenRecord
from src.reporter.taxa import *

from src.reporter.reports.report import Report


class _Rule(Enum):
    LOCALITY_LINE_BREAK = 1  # line break at start of locality
    COORDS_LINE_BREAK = 2  # line break at start of lat/long coordinates
    NAMES_LINE_BREAK = 3  # line break at start of collector names
    MID_COORD_BREAK = 4  # line break between latitude and longitude
    BREAK_NAMES_AT_SPACES = 5
    NO_SPACES_AFTER_INITIALS = 6
    NO_SPACES_AFTER_COMMAS = 7
    ABBREVIATE_FIRST_NAMES = 8  # fewest possible, trailing names first


class _JarGroup:
    def __init__(self):
        self.taxa_uniques: list[str] = []
        self.records: list[SpecimenRecord] = []
        self.sort_key = ""
        self.restriction_func: RestrictionFunc
        self.restriction_abbr = ""


class LabelReport(Report):
    class Type(Enum):
        ALL = 1
        MASHED = 2

    MAX_LABEL_PT_WIDTH = 1.41 * 19300.0 / 1.36
    PREFERRED_MAX_LINES_PER_LABEL = 5
    MAX_LINES_PER_PAGE = 130
    MAX_COLUMNS_PER_PAGE = 5
    DIVIDER_CHAR = "-"

    DOES_NOT_FIT_LABEL = "label does not fit"
    MASHED_COUNTRY_REGEX = re.compile(r": *[^ ]")
    LAT_LONG_REGEX = re.compile(r"^\d+[.]\d+°[NSEW]")
    NO_DATE_TEXT = "(no date)"
    NO_CAT_NUM_TEXT = "(no cat. #)"
    MIN_UTIC_NUMBER = 200000
    COUNTRIES_WITH_STATES = ["USA", "Mexico", "Ecuador", "Canada"]

    COMPRESSION_RULES = [
        # Line breaks must be in order the in which they would occur in the label.
        [_Rule.LOCALITY_LINE_BREAK, _Rule.COORDS_LINE_BREAK, _Rule.NAMES_LINE_BREAK],
        [_Rule.LOCALITY_LINE_BREAK, _Rule.NAMES_LINE_BREAK],
        [_Rule.LOCALITY_LINE_BREAK, _Rule.COORDS_LINE_BREAK],
        [_Rule.LOCALITY_LINE_BREAK, _Rule.MID_COORD_BREAK],
        [_Rule.LOCALITY_LINE_BREAK],
        [_Rule.COORDS_LINE_BREAK, _Rule.NAMES_LINE_BREAK],
        [_Rule.NAMES_LINE_BREAK],
        [_Rule.COORDS_LINE_BREAK],
        [_Rule.MID_COORD_BREAK],
        [_Rule.BREAK_NAMES_AT_SPACES],
        [_Rule.BREAK_NAMES_AT_SPACES, _Rule.NO_SPACES_AFTER_INITIALS],
        [
            _Rule.BREAK_NAMES_AT_SPACES,
            _Rule.NO_SPACES_AFTER_INITIALS,
            _Rule.ABBREVIATE_FIRST_NAMES,
        ],
        [],  # must be last
    ]

    def __init__(
        self,
        table: JamesTable,
        record_filter: RecordFilter,
        jar_group_uniques: Optional[list[str]],
        declared_names_table: DeclaredNamesTable,
        report_type: LabelReport.Type,
        make_printable: bool,
    ):
        super().__init__(table, record_filter)
        self._report_type = report_type
        self._make_printable = make_printable
        table.revise_names(unify_names_by_sound=True, merge_with_reference_names=True)

        self._group_corrections: dict[str, Identity] = {}
        for group_name in declared_names_table.get_group_names():
            group_identities = IdentityParser(group_name, False).parse()
            assert group_identities is not None
            self._group_corrections[str(group_identities[0])] = Identity(group_name)

        self._jar_groups: list[_JarGroup] = []
        self._jar_group_map: dict[str, list[_JarGroup]] = {}
        if jar_group_uniques is not None:
            current_jar_group = _JarGroup()
            for taxon_spec in jar_group_uniques:
                taxon_spec = taxon_spec.strip()
                if taxon_spec == "":
                    if len(current_jar_group.taxa_uniques) > 0:
                        self._jar_groups.append(current_jar_group)
                    current_jar_group = _JarGroup()
                elif taxon_spec[0] not in "-+#":
                    taxon_unique, restriction_func, restriction_abbr = to_taxon_unique(
                        taxon_spec
                    )
                    current_jar_group.taxa_uniques.append(taxon_unique)
                    current_jar_group.restriction_func = restriction_func
                    current_jar_group.restriction_abbr = restriction_abbr
                    if taxon_unique in self._jar_group_map:
                        self._jar_group_map[taxon_unique].append(current_jar_group)
                    else:
                        self._jar_group_map[taxon_unique] = [current_jar_group]
            if len(current_jar_group.taxa_uniques) > 0:
                self._jar_groups.append(current_jar_group)
        self._taxa_sample_records: dict[str, SpecimenRecord] = {}

        afm_path = Path("./data/AGaramondPro-Regular.afm")
        with afm_path.open("rb") as fh:
            self._font_afm = AFM(fh)
        assert self._font_afm is not None

        self._columns_on_page = 0
        self._lines_in_column = 0
        self._label_count = 0
        self._max_label_lines = self.PREFERRED_MAX_LINES_PER_LABEL

    def show(self) -> None:

        # How to generate strikethrough: "0̶1̶2̶3̶4̶5̶6̶7̶8̶9̶". The strikethrough is a
        # separate character that follows the digit. Copied into word, they are
        # all offset to the right about by one character, so I might not want
        # to include the final strikethrough character.

        if not self._make_printable:
            self._print_filter_title()

        if self._report_type == self.Type.ALL:
            title = "All"
        elif self._report_type == self.Type.MASHED:
            title = "Mashed"
        else:
            raise Exception("Unrecognized label report")
        title = "%s Specimen Labels" % title

        filtered_records = list(self._filtered_records())
        filtered_records = self._print_records(title, filtered_records)
        while len(filtered_records) > 0:
            self._max_label_lines += 1
            for jar_group in self._jar_groups:
                jar_group.records = []
            while (
                self._lines_in_column != self.MAX_LINES_PER_PAGE
                and self._columns_on_page != self.MAX_COLUMNS_PER_PAGE
            ):
                self._print_line()  # start a new page
            filtered_records = self._print_records(title, filtered_records)

        if not self._make_printable:
            print("\nThere are %d labels in this list.\n" % self._label_count)

    def _print_records(
        self, title: str, filtered_records: list[SpecimenRecord]
    ) -> list[SpecimenRecord]:

        # Print the title of this group of records.

        if self._make_printable:
            self._print_line("Generated on %s" % date.today().strftime("%B %d, %Y"))
            self._print_line()
            self._print_line("%d lines per label" % self._max_label_lines)
            self._space_to_next_label()
        else:
            print("\n---- %s ----\n" % title)
        left_over_records: list[SpecimenRecord] = []

        # Print only the records in the indicated jars.

        if self._jar_groups:
            for record in filtered_records:
                if record.taxon_unique in self._jar_group_map:
                    for jar_group in self._jar_group_map[record.taxon_unique]:
                        if jar_group.restriction_func(record):
                            jar_group.records.append(record)
                            if jar_group.sort_key == "":
                                jar_group.sort_key = to_taxon_sort_key(record)
                            self._taxa_sample_records[record.taxon_unique] = record
            self._jar_groups.sort(key=lambda g: g.sort_key)
            for jar_group in self._jar_groups:
                if jar_group.records:
                    jar_group.records.sort(
                        key=lambda r: 0
                        if r.catalog_number is None
                        else r.catalog_number
                    )
                    printed_header = False
                    for record in jar_group.records:
                        lines, notes = self._make_label_and_notes(record)
                        if self._suits_report_type(lines):
                            if len(lines) <= self._max_label_lines:
                                if not printed_header:
                                    for taxon_unique in jar_group.taxa_uniques:
                                        # Records excluded by cat # or ID don't have
                                        # sample records; avoid causing errors.
                                        if taxon_unique in self._taxa_sample_records:
                                            self._print_delta_taxa_label(
                                                None,
                                                self._taxa_sample_records[taxon_unique],
                                                taxon_unique,
                                                jar_group.restriction_abbr,
                                            )
                                        self._print_carryover_lines()
                                    if not self._make_printable:
                                        print()
                                    printed_header = True
                                self._print_record_label(lines, notes)
                                self._print_carryover_lines()
                            else:
                                left_over_records.append(record)

        # Print records irrespective of their jars.

        else:
            if self._report_type == self.Type.ALL and self._make_printable:
                for deltas, group in TaxaIterator(filtered_records):
                    printed_header = False
                    for record in group:
                        lines, notes = self._make_label_and_notes(record)
                        if self._suits_report_type(lines):
                            if len(lines) <= self._max_label_lines:
                                if not printed_header:
                                    self._print_delta_taxa_label(deltas, group[0])
                                    self._print_carryover_lines()
                                    printed_header = True
                                self._print_record_label(lines, notes)
                                self._print_carryover_lines()
                            else:
                                left_over_records.append(record)
            else:
                for record in filtered_records:
                    lines, notes = self._make_label_and_notes(record)
                    if self._suits_report_type(lines):
                        if len(lines) <= self._max_label_lines:
                            self._print_record_label(lines, notes)
                            self._print_carryover_lines()
                        else:
                            left_over_records.append(record)

        return left_over_records

    def _abbreviate_one_name(self, label: str) -> str:
        end_name = label.rfind("}")
        assert end_name > 0
        start_name = end_name
        if label[start_name - 1] == ".":  # abbreviated, non-initial name
            start_name -= 1
        while True:
            start_name -= 1
            if label[start_name] in " .,}|":
                break
        if label[start_name] == "|":
            start_name += 1  # skip over following line break designation char
        return "%s.%s" % (label[0 : start_name + 2], label[end_name + 1 :])

    def _exceeds_label_width(self, line: str) -> bool:
        return self._to_pt_width(line) > self.MAX_LABEL_PT_WIDTH

    def _find_end_of_label_line(self, line: str) -> int:
        end_offset = len(line)
        while self._exceeds_label_width(line[0:end_offset]):
            end_offset -= 1
        if end_offset == len(line):
            return len(line)
        while (line[end_offset].isalnum() or line[end_offset] in ".,:;)°") and (
            line[end_offset - 1].isalnum() or line[end_offset - 1] in ".(°"
        ):
            end_offset -= 1
        return end_offset

    def _suits_report_type(self, lines: list[str]) -> bool:
        is_mashed = False
        for line in lines:
            if "|" in line:
                is_mashed = True

        if not is_mashed:
            colon_line = lines[0] if ":" in lines[0] else lines[1]
            if self.MASHED_COUNTRY_REGEX.search(colon_line) is not None:
                is_mashed = True

        return (
            self._report_type == self.Type.ALL
            or self._report_type == self.Type.MASHED
            and is_mashed
        )

    def _make_label_and_notes(
        self, record: SpecimenRecord
    ) -> tuple[list[str], list[str]]:
        label: str = ""
        notes: list[str] = []

        # Construct the geographic location line.

        if record.country is None:
            notes.append("missing country")
        if (
            record.state is None
            and record.county is None
            and record.country not in self.COUNTRIES_WITH_STATES
        ):
            label = "%s:" % self._to_label_value(record.country)
        else:
            if record.state is None:
                notes.append("missing state")
            if record.county is None and (
                record.country != "USA"
                or (
                    record.state is not None
                    and record.state.lower() in States.TERRITORIES
                )
            ):
                label = "%s, %s:" % (
                    self._to_label_value(record.country),
                    self._to_label_value(record.state),
                )
            else:
                state = record.state
                if state is not None and record.country == "USA":
                    if state.lower() in States.TO_ABBREV:
                        state = States.TO_ABBREV[state.lower()]
                county = self._to_label_value(record.county)
                if record.country == "USA":
                    county = "%s Co." % county
                elif (
                    record.country == "Ecuador" and record.state == "Galapagos Islands"
                ):
                    if not county.startswith("Isla "):
                        county = "Isla %s" % county
                else:
                    if not county.startswith("Mun. "):
                        county = "Mun. %s" % county
                label = "%s, %s, %s:" % (
                    self._to_label_value(record.country),
                    self._to_label_value(state),
                    county,
                )
                if record.county is None and record.country == "USA":
                    notes.append("missing county")

        try:
            if self._exceeds_label_width(label):
                label = label.replace("Galapagos Islands", "Galapagos")
                # label = label.replace("Mun.", "M.")
            label += " "  # space after the country line colon
        except:
            raise Exception("Error with record ID %d, cat no. %d" % (record.id, record.catalog_number));

        # Add the locality, if there is any.

        locality = record.locality_on_label
        if record.locality_correct is not None:
            locality = record.locality_correct
        if locality is None:
            notes.append("missing locality")
        else:
            label += locality

        # Add the lat/long coordinates, if there are any.

        if record.latitude is not None and record.longitude is not None:
            if record.latitude >= 0:
                latitude = "%s°N" % record.latitude
            else:
                latitude = "%s°S" % (record.latitude * -1)
            if record.longitude >= 0:
                longitude = "%s°E" % record.longitude
            else:
                longitude = "%s°W" % (record.longitude * -1)
            label += " |C%s^%s" % (latitude, longitude)

        # Add the collector names.

        if record.collectors is None:
            notes.append("missing collectors")
        else:
            primary_names = Identity.get_corrected_primary_names(
                record.collectors, True
            )
            assert primary_names is not None
            label += " |N" + primary_names

        # Compact the label as so far constructed.

        abbreviated_names = False
        long_first_names_count = label.count("}")
        rule_index = 0
        # Apply this once regardless, to expand too-compact labels.
        label_lines, max_line_pt_width = self._split_label_lines(
            record.id, label.replace("}", " "), self.COMPRESSION_RULES[rule_index]
        )
        while rule_index + 1 < len(self.COMPRESSION_RULES) and (
            max_line_pt_width > self.MAX_LABEL_PT_WIDTH
            or len(label_lines) > self._max_label_lines - 1
        ):
            compression_rule = self.COMPRESSION_RULES[rule_index]
            if (
                _Rule.ABBREVIATE_FIRST_NAMES in compression_rule
                and long_first_names_count > 0
            ):
                label = self._abbreviate_one_name(label)
                long_first_names_count -= 1
                abbreviated_names = True
            else:
                rule_index += 1
                abbreviated_names = False
            label_lines, max_line_pt_width = self._split_label_lines(
                record.id, label.replace("}", " "), compression_rule
            )
        if abbreviated_names:
            notes.append("abbreviated names")

        # Construct the catalog number and date line.

        collection_date = record.normalized_date_time
        if record.date_time is None:
            if record.raw_date_time == "":
                notes.append("missing date")
            else:
                notes.append("unclear date")
        else:
            assert record.date_time.start_date is not None
            if record.date_time.start_date.year is None:
                notes.append("unclear year")

        if record.catalog_number is None:
            cat_num = self.NO_CAT_NUM_TEXT
            notes.append("missing catalog number")
        else:
            cat_num = "{:,}".format(record.catalog_number)
            if record.catalog_number < self.MIN_UTIC_NUMBER:
                cat_num = "TMM#%s" % cat_num
            else:
                cat_num = "UTIC#%s" % cat_num

        date_catnum_line = "%s\t%s" % (collection_date, cat_num)
        label_lines.append(date_catnum_line)

        # Mark labels that don't fit.

        if (
            max_line_pt_width > self.MAX_LABEL_PT_WIDTH
            or len(label_lines) > self._max_label_lines
        ):
            notes.append(self.DOES_NOT_FIT_LABEL)

        self._verify_label(record, label_lines)
        return (label_lines, notes)

    def _print_carryover_lines(self) -> None:
        if self._make_printable:
            if self._lines_in_column + self._max_label_lines > self.MAX_LINES_PER_PAGE:
                while self._lines_in_column % self.MAX_LINES_PER_PAGE > 0:
                    self._print_line()

    def _print_delta_taxa_label(
        self,
        deltas: Optional[list[TaxonDelta]],
        sample: SpecimenRecord,
        taxon_unique: str = "",
        restriction_abbr: str = "",
    ) -> None:
        changed = self._print_delta_taxa_label_line(
            deltas,
            ["phylum"],
            [clean_taxon(sample.phylum)],
            taxon_unique,
            restriction_abbr,
            False,
        )
        changed = self._print_delta_taxa_label_line(
            deltas,
            ["class", "subclass"],
            [clean_taxon(sample.class_), clean_taxon(sample.subclass)],
            taxon_unique,
            restriction_abbr,
            changed,
        )
        changed = self._print_delta_taxa_label_line(
            deltas,
            ["order", "suborder", "infraorder"],
            [
                clean_taxon(sample.order),
                clean_taxon(sample.suborder),
                clean_taxon(sample.infraorder),
            ],
            taxon_unique,
            restriction_abbr,
            changed,
        )
        changed = self._print_delta_taxa_label_line(
            deltas,
            ["family", "subfamily"],
            [clean_taxon(sample.family), clean_taxon(sample.subfamily)],
            taxon_unique,
            restriction_abbr,
            changed,
        )
        self._print_delta_taxa_label_line(
            deltas,
            ["species"],
            [to_clean_genus_species(sample.genus, sample.species, sample.subspecies)],
            taxon_unique,
            restriction_abbr,
            changed,
        )
        self._space_to_next_label()

    def _print_delta_taxa_label_line(
        self,
        deltas: Optional[list[TaxonDelta]],
        ranks_in_line: list[str],
        taxa: list[Optional[str]],
        taxon_unique: str,
        restriction_abbr: str,
        already_noted_change: bool,
    ) -> bool:

        rendered_taxa: list[str] = []
        for taxon in taxa:
            if taxon is None:
                rendered_taxa.append(NO_TAXON_STR)  # AFM won't measure em-dash '—'
            else:
                if restriction_abbr != "" and taxon == taxon_unique:
                    taxon = "%s %s" % (restriction_abbr, taxon)
                rendered_taxa.append(taxon)

        suffix = ""
        if deltas and not already_noted_change:
            for delta in deltas:
                if delta[0] in ranks_in_line:
                    suffix = "  «««"
                    already_noted_change = True
                    break

        line = "@  %s%s" % (" | ".join(rendered_taxa), suffix)
        if self._exceeds_label_width(line):
            while self._exceeds_label_width(line + "..."):
                line = line[0:-1]
            line += "..."
        elif ranks_in_line == ["phylum"]:
            if not self._exceeds_label_width(line + "  " + self.DIVIDER_CHAR):
                line += "  " + self.DIVIDER_CHAR
                while not self._exceeds_label_width(line + self.DIVIDER_CHAR):
                    line += self.DIVIDER_CHAR

        self._print_line(line)
        return already_noted_change

    def _print_record_label(self, lines: list[str], notes: list[str]) -> None:
        if self._make_printable:
            for line in lines:
                self._print_line(line)
            self._space_to_next_label()
        else:
            for line in lines:
                self._print_line(line)
            self._print_line()
            if notes:
                self._print_line("^ %s" % ", ".join(notes))
                self._print_line()
        self._label_count += 1
        if self._label_count % 5000 == 0:
            os.system("say %d" % self._label_count)

    def _print_line(self, line: str = "") -> None:
        self._lines_in_column += 1
        if self._lines_in_column > self.MAX_LINES_PER_PAGE:
            self._lines_in_column = 1
            self._columns_on_page += 1
            if self._columns_on_page > self.MAX_COLUMNS_PER_PAGE:
                self._columns_on_page = 0
        print(line)

    def _space_to_next_label(self) -> None:
        if self._make_printable:
            while self._lines_in_column % self._max_label_lines > 0:
                self._print_line()

    def _split_label_lines(
        self, record_id: int, label: str, compression_rule: list[_Rule]
    ) -> tuple[list[str], float]:

        lines: list[str] = []

        # First split a country line that is too long.

        colon_offset = label.find(":")
        assert colon_offset > 0
        test_line = label[0:colon_offset]
        if self._exceeds_label_width(test_line):
            end_offset = self._find_end_of_label_line(test_line)
            lines.append(label[0:end_offset].rstrip())
            label = label[end_offset:].lstrip()
            colon_offset = label.find(":")
            assert colon_offset > 0

        # Put a line break before the locality line, if required.

        if _Rule.LOCALITY_LINE_BREAK in compression_rule:
            lines.append(label[0 : colon_offset + 1])
            label = label[colon_offset + 2 :].lstrip()

        if label != "":

            # Handle case where there is no locality.

            if label[0] == "|":
                label = label[2:]

            # Split up a locality that is too long.

            else:
                vertical_offset = label.find(" |")
                if vertical_offset < 0:
                    end_locality: int = len(label)
                else:
                    end_locality = min(vertical_offset, len(label))
                test_line = label[0:end_locality]
                while self._exceeds_label_width(test_line):
                    end_offset = self._find_end_of_label_line(test_line)
                    lines.append(label[0:end_offset].rstrip())
                    label = label[end_offset:]
                    end_locality -= end_offset
                    for c in label:
                        if c != " ":
                            break
                        end_locality -= 1
                    label = label.lstrip()
                    test_line = label[0:end_locality]

            # Insert line breaks at the start of the coordinates and names lines
            # as required. Also split latitude and longitude, if required.

            names_offset = label.find("|N")
            if names_offset >= 0:
                names_offset += 2

            for line_break in compression_rule:
                if (
                    line_break == _Rule.COORDS_LINE_BREAK
                    or line_break == _Rule.NAMES_LINE_BREAK
                ):
                    c = "C" if line_break == _Rule.COORDS_LINE_BREAK else "N"
                    break_offset = label.find(" |" + c)
                    if break_offset >= 0:
                        lines.append(label[0:break_offset])
                        left_shift = break_offset + 3
                        label = label[left_shift:]
                        names_offset -= left_shift
                elif line_break == _Rule.MID_COORD_BREAK:
                    break_offset = label.find("^")
                    if break_offset >= 0:
                        lines.append(label[0:break_offset])
                        left_shift = break_offset + 1
                        label = label[left_shift:]
                        names_offset -= left_shift

            # Split up too-long line containing lat/long coordinates.
            # (This line may also contain leftover locality.)

            vertical_offset = label.find(" |C")
            if vertical_offset >= 0:
                vertical_offset = label.find(" |", vertical_offset + 2)
                end_coords = min(vertical_offset, len(label))
                test_line = label[0:end_coords]
                if self._exceeds_label_width(test_line):
                    end_offset = self._find_end_of_label_line(test_line)
                    if end_offset <= end_coords:
                        if label[end_offset + 1] == "|":
                            lines.append(label[0:end_offset])
                            label = label[end_offset + 3 :]  # skip " |N"
                        elif label[end_offset] == "|":
                            lines.append(label[0 : end_offset - 1])
                            label = label[end_offset + 2 :]  # skip " |N"
                        elif label[end_offset - 1] == "|":
                            lines.append(label[0 : end_offset - 2])
                            label = label[end_offset + 1 :]  # skip " |N"
                        elif label[end_offset - 1] == "^":
                            lines.append(label[0 : end_offset - 1])
                            label = label[end_offset:]
                        elif label[end_offset] == "^":
                            lines.append(label[0:end_offset])
                            label = label[end_offset + 1 :]
                        else:
                            raise Exception(
                                "Tried to break id %d label [%s] (w/ lat-long) at [%s]"
                                % (record_id, label, label[end_offset:])
                            )

            # Split name lines that are too long.

            if self._exceeds_label_width(label):
                break_at_spaces = _Rule.BREAK_NAMES_AT_SPACES in compression_rule
                squeeze_periods = _Rule.NO_SPACES_AFTER_INITIALS in compression_rule
                squeeze_commas = _Rule.NO_SPACES_AFTER_COMMAS in compression_rule

                if names_offset >= 0:  # if we know there are names
                    names_offset = label.find("|N")
                    if names_offset < 0:
                        names_offset = 0
                    else:
                        names_offset += 2
                if names_offset < 0:
                    raise Exception(
                        "Label too wide but no names: id %d, label [%s]"
                        % (record_id, label)
                    )

                line = label[0:names_offset]
                if break_at_spaces:
                    names = label[names_offset:].split(" ")
                else:
                    names = label[names_offset:].split(", ")
                    for i in range(len(names)):
                        if i + 1 < len(names):
                            names[i] += ","
                for i in range(len(names)):
                    name = names[i]
                    if squeeze_periods:
                        name = name.replace(". ", ".")
                    if i == 0 or squeeze_commas:
                        candidate = name
                    else:
                        candidate = " " + name
                    if self._exceeds_label_width(line + candidate):
                        lines.append(line)
                        line = name
                    else:
                        line += candidate
                lines.append(line)
            else:
                lines.append(label)

        # Remove signal characters from the label before returning it.

        clean_lines: list[str] = []
        max_line_pt_width = 0
        for line in lines:
            line = (
                line.replace("^", " ")
                .replace("|L", "| ")
                .replace("|C", "| ")
                .replace("|N", "| ")
            )
            if line.endswith(" | "):
                line = line[0:-3]
            clean_lines.append(line)
            line_pt_length = self._to_pt_width(line)
            if line_pt_length > max_line_pt_width:
                max_line_pt_width = line_pt_length

        return (clean_lines, max_line_pt_width)

    @classmethod
    def _to_label_value(cls, value: Optional[str]):
        if value is None:
            return SpecimenRecord.MISSING_LABEL_TEXT
        return value

    def _to_pt_width(self, line: str) -> float:
        try:
            return self._font_afm.string_width_height(line)[0]
        except KeyError:
            raise Exception("AFM could not measure line [%s]" % line)

    def _verify_label(self, record: SpecimenRecord, lines: list[str]) -> None:

        # Validate simple character constraints.

        for line in lines:
            if "^" in line:
                _invalid_label(record.id, lines, "Found '^' in line.")
            if line.strip() != line:
                _invalid_label(record.id, lines, "Line not trimmed of whitespace.")
        label = "^".join(lines)
        if label.count("|") != label.count(" | "):
            _invalid_label(record.id, lines, "Vertical bars not all space-delimited")
        if ":" not in label:
            _invalid_label(record.id, lines, "No colon following country/state/county")

        # Extract and validate the country/state/county line.

        colon_offset = label.find(":")
        country_line = label[0:colon_offset].replace("^", " ")
        if record.county is not None:
            if not record.county.endswith(" Co."):
                country_line = country_line.replace(" Co.", "")
            if not record.county.startswith("Isla "):
                country_line = country_line.replace("Isla ", "")
            if not record.county.startswith("Mun. "):
                country_line = country_line.replace("Mun. ", "")

        label = label[colon_offset + 2 :]
        divisions = country_line.split(", ")

        if record.country is None:
            if divisions[0] != SpecimenRecord.MISSING_LABEL_TEXT:
                _invalid_label(record.id, lines, "Country should be unknown")
        else:
            if divisions[0] != record.country:
                _invalid_label(record.id, lines, "Invalid country")
        if record.country == "USA":
            state = record.state
            if state is None:
                if (
                    len(divisions) < 2
                    or divisions[1] != SpecimenRecord.MISSING_LABEL_TEXT
                ):
                    _invalid_label(record.id, lines, "State should be unknown")
            else:
                if state.lower() in States.TO_ABBREV and (
                    state.lower() not in States.TERRITORIES or record.county is not None
                ):
                    state = States.TO_ABBREV[state.lower()]
                if len(divisions) < 2 or divisions[1] != state:
                    _invalid_label(record.id, lines, "Invalid state")
        elif record.state is None:
            if record.country in self.COUNTRIES_WITH_STATES:
                if (
                    len(divisions) < 2
                    or divisions[1] != SpecimenRecord.MISSING_LABEL_TEXT
                ):
                    _invalid_label(record.id, lines, "State/province should be unknown")
            else:
                if len(divisions) > 1:
                    _invalid_label(record.id, lines, "Not expecting state/province")
        else:
            if (
                len(divisions) < 2
                or divisions[1] != record.state
                and not (
                    record.state == "Galapagos Islands" and divisions[1] == "Galapagos"
                )
            ):
                _invalid_label(record.id, lines, "Invalid state/province")

        if record.county is None:
            if record.country == "USA":
                if (
                    record.state is None
                    or record.state.lower() not in States.TERRITORIES
                ) and (
                    len(divisions) < 3
                    or SpecimenRecord.MISSING_LABEL_TEXT not in divisions[2]
                ):
                    _invalid_label(record.id, lines, "County should be unknown")
            else:
                if len(divisions) > 2:
                    _invalid_label(record.id, lines, "Not expecting county")
        else:
            if len(divisions) <= 2:
                _invalid_label(record.id, lines, "Missing county")
            elif len(divisions) == 3:
                if divisions[2] != record.county:
                    _invalid_label(
                        record.id,
                        lines,
                        "Invalid county (["
                        + divisions[2]
                        + "] should be ["
                        + record.county
                        + "])",
                    )
            else:
                _invalid_label(record.id, lines, "Too many divisions in country line")

        # Extract and validate the locality.

        expected_locality = record.locality_on_label
        if record.locality_correct is not None:
            expected_locality = record.locality_correct
        if expected_locality is not None:
            assert expected_locality != "", "locality problem with ID %d" % record.id
            actual_locality = ""
            while not _compare_localities(expected_locality, actual_locality):
                eol_offset = label.find("^", 1)
                if eol_offset < 0:  # cat no. line should follow
                    _invalid_label(record.id, lines, "Locality not found")
                vbar_offset = label.find(" |")
                if vbar_offset < 0:
                    vbar_offset = 1000000
                end_offset = min(eol_offset, vbar_offset)
                actual_locality += label[0:end_offset]
                label = label[end_offset:]  # keep the "^""
        label = _advance_label_line(label)

        # Extract and validate latitude and longitude.

        if record.latitude is not None and record.longitude is not None:

            match = self.LAT_LONG_REGEX.match(label)
            if match is None:
                _invalid_label(record.id, lines, "Missing latitude")
            else:
                latitude_str = match.group(0)
                latitude = Decimal(latitude_str[0:-2])
                if latitude_str[-1] == "S":
                    latitude *= -1
                elif latitude_str[-1] != "N":
                    _invalid_label(record.id, lines, "Latitude neither N nor S")
                if latitude != record.latitude:
                    _invalid_label(record.id, lines, "Incorrect latitude")
                if label[len(latitude_str)] != " " and label[len(latitude_str)] != "^":
                    _invalid_label(record.id, lines, "Invalid lat/long separator")
                label = label[len(latitude_str) + 1 :]

            match = self.LAT_LONG_REGEX.match(label)
            if match is None:
                _invalid_label(record.id, lines, "Missing longitude")
            else:
                longitude_str = match.group(0)
                longitude = Decimal(longitude_str[0:-2])
                if longitude_str[-1] == "W":
                    longitude *= -1
                elif longitude_str[-1] != "E":
                    _invalid_label(record.id, lines, "Longitude neither E nor W")
                if longitude != record.longitude:
                    _invalid_label(record.id, lines, "Incorrect longitude")
                label = label[len(longitude_str) + 1 :]
                label = _advance_label_line(label)

        # Extract and validate collector names.

        if record.collectors is not None:

            last_line_offset = label.rfind("^")
            if last_line_offset < 0:
                _invalid_label(
                    record.id, lines, "Missing collectors or date/cat.# line"
                )
            actual_name_sets = (
                label[0:last_line_offset]
                .replace("^", " ")
                .replace(". ", ".")
                .replace(".", ". ")
                .split("; ")
            )
            label = label[last_line_offset + 1 :]
            try:
                actual_collectors: list[Identity] = []
                for actual_name_set in actual_name_sets:
                    actual_subset = IdentityParser(actual_name_set, False).parse()
                    if actual_subset is not None:
                        actual_collectors += actual_subset

                if not actual_collectors:
                    _invalid_label(record.id, lines, "Missing collector names")
                elif len(actual_collectors) != len(record.collectors):
                    _invalid_label(
                        record.id,
                        lines,
                        "Expected %d collectors but found %d"
                        % (len(record.collectors), len(actual_collectors)),
                    )
                else:
                    for i in range(len(actual_collectors)):
                        actual = actual_collectors[i]
                        try:
                            actual = self._group_corrections[str(actual)]
                        except KeyError:
                            pass  # ignore, keeping original value of `actual`
                        expected = record.collectors[i].get_master_copy().primary
                        assert expected is not None
                        if not _compare_identities(expected, actual):
                            _invalid_label(
                                record.id,
                                lines,
                                "Actual collector '%s' does not match expected '%s'"
                                % (actual, expected),
                            )

            except ParseError as e:
                _invalid_label(record.id, lines, "ParseError '%s'" % e.message)

        # Extract and validate the collection date/time.

        tab_offset = label.find("\t")
        if tab_offset < 0:
            _invalid_label(record.id, lines, "Missing cat. # tab")
        date_time_str = label[0:tab_offset]
        label = label[tab_offset + 1 :]

        if date_time_str != record.normalized_date_time:
            _invalid_label(
                record.id, lines, "Expected date '%s'" % record.normalized_date_time
            )

        # Extract and validate the catalog number.

        if record.catalog_number is None:
            if label != self.NO_CAT_NUM_TEXT:
                _invalid_label(record.id, lines, "Expected '%s'" % self.NO_CAT_NUM_TEXT)
        else:
            if record.catalog_number < self.MIN_UTIC_NUMBER:
                if not label.startswith("TMM#"):
                    _invalid_label(record.id, lines, "Invalid TMM cat. # prefix")
                label = label[4:]
            else:
                if not label.startswith("UTIC#"):
                    _invalid_label(record.id, lines, "Invalid UTIC cat. # prefix")
                label = label[5:]
            label = label.replace(",", "")
            if not label.isdigit():
                _invalid_label(record.id, lines, "Invalid catalog number")
            if int(label) != record.catalog_number:
                _invalid_label(record.id, lines, "Incorrect catalog number")


def _advance_label_line(label: str) -> str:
    c = label[0]
    if c == "^":
        label = label[1:]
    elif c == " ":
        label = label[3:]  # skip " | "
    elif c == "|":
        label = label[2:]  # skip "| "
    return label


def _compare_identities(expected: Identity, actual: Identity) -> bool:
    if actual.last_name != expected.last_name:
        return False
    if actual.name_suffix != expected.name_suffix:
        return False
    if actual.initial_names != expected.initial_names:
        if actual.initial_names is None or expected.initial_names is None:
            return False
        actual_initial_names = actual.initial_names.split(" ")
        expected_initial_names = expected.initial_names.split(" ")
        if len(actual_initial_names) != len(expected_initial_names):
            return False
        for i in range(len(actual_initial_names)):
            actual_name = actual_initial_names[i]
            if actual_name[0] != expected_initial_names[i][0]:
                return False
            if len(actual_name) != 2 or actual_name[1] != ".":
                return False
    return True


def _compare_localities(expected: str, actual: str) -> bool:
    div_offset = actual.find("^")
    if div_offset < 0:
        return expected == actual
    if _compare_localities(expected, actual.replace("^", " ", 1)):
        return True
    return _compare_localities(expected, actual.replace("^", "", 1))


def _invalid_label(record_id: int, lines: list[str], message: str) -> None:
    raise Exception(
        "Invalid label ID %d: %s\n[%s]" % (record_id, message, "↵\n".join(lines))
    )
