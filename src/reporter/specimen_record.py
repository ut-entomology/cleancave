from __future__ import annotations
from typing import Optional, Tuple
from decimal import Decimal
import re

# NOTE: All Texas cave coordinates are rounded to the 2nd decimal place in
# reports that generate publicly-available data, except for coordinates
# on military bases, which are not provided either publicly or privately.

from src.lib.identity import Identity
from src.lib.declared_names_table import DeclaredNamesTable
from src.lib.parse_error import ParseError
from src.reporter.taxa import *
from src.reporter.lat_long_table import LatLongTable
from src.reporter.lat_long_record import LatLongRecord
from src.reporter.james_date_time import JamesDateTime
from src.reporter.name_column_parser import NameColumnParser
from src.reporter.determiner_set import DeterminerSet

OWNER_CORRECTIONS = {
    "camp bullis": "Camp Bullis",
    "camp bulls": "Camp Bullis",
    "camp bulils": "Camp Bullis",
    "fort hood": "Fort Hood",
    "tpwd": "TPW",
}
SENSITIVE_OWNERS = ["Camp Bullis", "Fort Hood"]
UNCERTAIN_DET_TEXT = "uncertain det."

REGEX_SUBGENUS = re.compile(r"\([A-Z][a-z]+")
REGEX_PARENED = re.compile(r"\([^)]+\)")
REGEX_AUTHOR_START = re.compile(r"[A-Z][A-Za-z.]")
REGEX_LOWER_LETTERS = re.compile(r"^[a-z]+$")
REGEX_SPACES = re.compile(r" {2,}")  # 2nd dash is not short!
NEW_SUBSPECIES = "n. subsp."


class SpecimenRecord(LatLongRecord):
    """Representation of a record in James' spreadsheet."""

    REGEX_DIGITS = re.compile(r"[^\d]*(\d+).*")
    REGEX_ACCURACY = re.compile(r"(\d+) m(?:eters?)? accuracy")
    MISSING_LABEL_TEXT = "(?)"
    MISSING_LABEL_YEAR = " (year?)"

    def __init__(
        self,
        lat_longs: Optional[LatLongTable],
        declared_names_table: DeclaredNamesTable,
        raw_id: str,
        raw_catalog_number: str,
        raw_phylum: str,
        raw_class: str,
        raw_subclass: str,
        raw_order: str,
        raw_suborder: str,
        raw_infraorder: str,
        raw_family: str,
        raw_subfamily: str,
        raw_genus: str,
        raw_species_author: str,
        raw_subspecies: str,
        raw_species_on_label: str,
        raw_continent: str,
        raw_country: str,
        raw_state: str,
        raw_county: str,
        raw_correct_locality: str,
        raw_label_locality: str,
        raw_datum: str,
        raw_latitude: str,
        raw_longitude: str,
        raw_accuracy_meters: str,
        raw_owner: str,
        raw_microhabitat: str,
        raw_date_time: str,
        raw_collectors: str,
        raw_females: str,
        raw_males: str,
        raw_immatures: str,
        raw_type_status: str,
        raw_collections: str,
        raw_determiners: str,
        raw_specimen_count: str,
        raw_year: str,
        raw_month: str,
        raw_day: str,
        raw_start_date: str,
        raw_end_date: str,
        raw_verbatim_date: str,
        raw_notes: str,
        raw_area: str,
    ):
        super().__init__(raw_id, raw_catalog_number, raw_latitude, raw_longitude)

        # Initialize state variables.

        self.name_changes: Optional[list[str]] = None
        self.sort_key: str = ""

        # Perform checks on assumptions.

        if raw_subspecies != "":
            self.add_problem("Expected empty subspecies")

        # Load from raw data.

        self.det_descriptors: list[str] = []
        self.phylum = self._parse_non_empty("phylum", raw_phylum)
        self.class_ = self._parse_taxon(raw_class)
        self.subclass = self._parse_taxon(raw_subclass)
        self.order = self._parse_taxon(raw_order)
        self.suborder = self._parse_str_or_none(raw_suborder)
        self.infraorder = self._parse_str_or_none(raw_infraorder)
        self.family = self._parse_taxon(raw_family)
        self.subfamily = self._parse_str_or_none(raw_subfamily)
        [self.genus, self.subgenus] = self._parse_genus(raw_genus)
        [self.species, self.subspecies, self.authors] = parse_species_author(
            self._parse_str_or_none(raw_species_author), self.det_descriptors
        )
        self.species_on_label = self._parse_str_or_none(raw_species_on_label)
        self.continent = self._parse_str_or_none(raw_continent)
        self.country = self._parse_str_or_none(raw_country)
        self.state = self._parse_state(raw_state)
        self.county = self._parse_county(raw_county)
        self.locality_correct = self._parse_locality_correct(raw_correct_locality)
        self.locality_on_label = self._parse_locality_on_label(raw_label_locality)
        self.datum = self._parse_str_or_none(raw_datum)
        self.owner = self._parse_owner(raw_owner)
        self.is_sensitive = self._parse_sensitivity()
        self.microhabitat = self._parse_microhabitat(raw_microhabitat)
        self.accuracy_meters = self._parse_accuracy(
            raw_microhabitat, raw_accuracy_meters
        )
        # Appends "[US]" if was originally in U.S. month/day/year format.
        self.raw_date_time = JamesDateTime.correct_raw_date_time(raw_date_time)
        self.date_time = self._parse_date_time(
            self.raw_date_time, raw_start_date, raw_end_date
        )
        self.normalized_date_time = self._normalize_date_time()
        self.raw_collectors: str = raw_collectors
        self.collectors = self._parse_collectors(
            declared_names_table, self.raw_collectors
        )
        self.females = self._parse_int_or_0("females", raw_females)
        self.males = self._parse_int_or_0("males", raw_males)
        self.immatures = self._parse_int_or_0("immatures", raw_immatures)
        self.type_status = self._parse_type_status(raw_type_status)
        self.collections = self._parse_collections(raw_collections)
        self.raw_identifier_year = raw_determiners
        self.identifier_year = DeterminerSet().load(
            declared_names_table, self, self.raw_identifier_year
        )
        self.specimen_count = self._parse_specimen_count(raw_specimen_count)
        self.misc_notes = self._parse_str_or_none(raw_notes)
        self.new_verbatim_date = raw_verbatim_date
        self.new_area = raw_area

        # Process after loading.

        if self.phylum is None:
            self.taxon_unique = NO_TAXON_STR
        else:
            self.taxon_unique = to_taxon_unique(self)[0]

        if self.genus is not None:
            if self.genus == "Cicurina (Cicurella)":
                if self.species is not None:
                    self.species = self.species.replace("(blind)", "(eyeless)")
                    if self.subspecies is not None:
                        self.subspecies = self.subspecies.replace(
                            "(blind)", "(eyeless)"
                        )

        if lat_longs is not None:
            self._revise_lat_long(lat_longs)

        # Validate.

        self._validate(raw_day, raw_month, raw_year)

    def has_specimen(self) -> bool:
        # only deleted from table if there's a non-empty duplicate
        return (
            self.phylum is not None
            or self.class_ is not None
            or self.order is not None
            or self.family is not None
            or self.genus is not None
            or self.species is not None
            or self.species_on_label is not None
        )

    def log_name_change(self, from_text: str, to_text: str) -> None:
        log = "changed name '%s' to '%s'" % (from_text, to_text)
        if self.name_changes is None:
            self.name_changes = [log]
        else:
            self.name_changes.append(log)

    def print_name_problems(self) -> bool:
        if self._problems is None:
            return False
        name_problems: list[str] = []
        for problem in self._problems:
            if problem.endswith(" in collector") or problem.endswith(" in determiner"):
                name_problems.append(problem)
        if name_problems:
            self._print_issues(name_problems)
            return True
        return False

    def print_name_warnings(self) -> bool:
        if self._warnings is None:
            return False
        name_warnings: list[str] = []
        for problem in self._warnings:
            if problem.endswith(" in collector") or problem.endswith(" in determiner"):
                name_warnings.append(problem)
        if name_warnings:
            self._print_issues(name_warnings)
            return True
        return False

    def save_problems(self, parser: NameColumnParser, column_name: str) -> None:
        for error in parser.get_errors():
            self.add_problem("%s in %s" % (error, column_name))
        for warning in parser.get_warnings():
            self.add_warning("%s in %s" % (warning, column_name))

    def _correct_foreign_chars(self, s: Optional[str]) -> Optional[str]:
        if s is None:
            return None
        return s.replace("Ò", "ñ").replace("√í", "ñ").replace("í", "'")

    def _normalize_date_time(self) -> str:
        if self.date_time is None:
            if self.raw_date_time == "":
                return "(no date)"
            return self.raw_date_time + self.MISSING_LABEL_YEAR
        assert self.date_time.start_date is not None
        if self.date_time.start_date.year is None:
            return self.raw_date_time + self.MISSING_LABEL_YEAR
        return self.date_time.normalize(self.raw_date_time)

    def _parse_accuracy(self, raw_microhabitat: str, raw_accuracy: str):
        accuracy1 = 0
        match = self.REGEX_ACCURACY.search(raw_microhabitat)
        if match is not None:
            accuracy1 = self._parse_int("microhabitat accuracy", match.group(1))
            if accuracy1 is None:
                accuracy1 = 0

        accuracy2 = self._parse_int_or_0("coordinateUncertaintyInMeters", raw_accuracy)
        if accuracy2 is None:
            accuracy2 = 0

        if accuracy1 != accuracy2:
            if accuracy1 == 0 or accuracy2 == 0:
                accuracy1 += accuracy2
            else:
                self.add_problem(
                    "coordinateUncertaintyInMeters disagrees with accuracy in microhabitat"
                )
                accuracy1 = 0
        return accuracy1 if accuracy1 != 0 else None

    def _parse_date_time(
        self, combo_str: str, start_str: str, end_str: str
    ) -> Optional[JamesDateTime]:
        if combo_str != "" or (combo_str == start_str):
            return self._parse_date_time_column("Date/Time", combo_str)
        date_time = self._parse_date_time_column("startDate", start_str)
        if date_time is not None:
            end_date_time = self._parse_date_time_column("endDate", end_str)
            if end_date_time is not None:
                if date_time.start_date != end_date_time.start_date:
                    date_time.end_date = end_date_time.start_date
        return date_time

    def _parse_date_time_column(
        self, column_name: str, date_time_str: str
    ) -> Optional[JamesDateTime]:
        try:
            if date_time_str == ".":
                raise ParseError("missing date")
            date_time = JamesDateTime()
            date_time.load(date_time_str)
            return date_time
        except ParseError as e:
            if e.message.startswith("missing date"):
                self.add_warning(e.message)
            else:
                self.add_problem(
                    "%s (%s '%s')" % (e.message, column_name, date_time_str)
                )
            return None

    def _parse_collectors(
        self, declared_names_table: DeclaredNamesTable, s: str
    ) -> Optional[list[Identity]]:
        parser = NameColumnParser(s, declared_names_table)
        identities = parser.parse()
        self.save_problems(parser, "collector")
        if identities is None:
            self.add_warning("no collectors")
            return None
        return identities

    def _parse_collections(self, raw_collections: str) -> list[str]:
        collections: list[str] = []
        for collection in raw_collections.split(","):
            collections.append(collection.strip())
        return collections

    def _parse_county(self, s: str) -> Optional[str]:
        corrections = {
            "AcuÒa": "Acuña",
            "Ascencion": "Ascension",
            "Asencion": "Ascension",
            "Ciudad de Maiz": "Ciudad del Maiz",
            "Dekalb": "DeKalb",
            "Zaragosa": "Zaragoza",
            "Millls": "Mills",
            "Muzquis": "Muzquiz",
            "Musquiz": "Muzquiz",
            "Talcotalpa": "Tacotalpa",
            "Tepetlasco": "Tepatlaxco",
        }
        for mistake, correction in corrections.items():
            if s == mistake:
                s = correction
                break
        return self._parse_str_or_none(s)

    def _parse_genus(self, s: str | None) -> Tuple[str | None, str | None]:
        if s is None:
            return (None, None)
        s = self._parse_str_or_none(s)
        if s is None or s == ".":
            return (None, None)
        if "undescribed" in s.lower():
            self.det_descriptors.append(s)
            return (None, None)
        if s[-1] == ".":
            s = s[0:-1]
        s = s.replace("=", "")
        if s[0] == '"' and s[-1] == '"':
            s = s[1:-1]
        if " or " in s or " and " in s or "+" in s or "/" in s:
            self.det_descriptors.append(s)
            return (None, None)

        # Extract subgenus, which begins with a capital letter.
        genus = s
        subgenus: str | None = None
        match = REGEX_SUBGENUS.search(s)
        if match is not None:
            subgenus = s[match.start(0) + 1 :]
            if subgenus[-1] == ")":
                subgenus = subgenus[0:-1]
            genus = s[0 : match.start(0)].strip()

        # Extract descriptors, which begin with a non-letter or a lowercase letter.
        genus = self._parse_taxon(genus)

        return (genus, subgenus)

    def _parse_locality_correct(self, s: str) -> Optional[str]:
        correct_locality = self._correct_foreign_chars(self._parse_str_or_none(s))
        if (
            self.state is not None
            and self.state.lower() == "texas"
            and correct_locality is None
        ):
            self.add_problem("Texas specimen missing a correct locality")
        return correct_locality

    def _parse_locality_on_label(self, s: str) -> Optional[str]:
        locality_on_label = self._correct_foreign_chars(self._parse_str_or_none(s))
        if locality_on_label is not None:
            locality_on_label = locality_on_label.replace("^&", "&")
            assert "^" not in locality_on_label
            assert "|" not in locality_on_label
        return locality_on_label

    def _parse_microhabitat(self, s: str):
        if s == "":
            return None
        match = self.REGEX_ACCURACY.search(s)
        if match is not None:
            s = (
                s.replace(match.group(0), "")
                .replace(", ,", ", ")
                .replace("; ;", "; ")
                .replace("  ", " ")
                .strip()
            )
            if s != "":
                if s[0] in [".", ",", ";"]:
                    s = s[1:].strip()
                elif s[-1] in [".", ",", ";"]:
                    s = s[0:-1].strip()
        return s if s != "" else None

    def _parse_owner(self, s: str) -> Optional[str]:
        owner = self._parse_str_or_none(s)
        if owner is not None and owner.lower() in OWNER_CORRECTIONS:
            owner = OWNER_CORRECTIONS[owner.lower()]
        return owner

    def _parse_sensitivity(self) -> bool:
        return self.owner in SENSITIVE_OWNERS

    def _parse_specimen_count(self, s: str) -> int:
        count = 0 if s == "" else self._parse_int("specimen count", s)
        if count == 0:
            self.add_problem("specimen count is 0")
        if count is None:
            self.add_problem("invalid specimen count")
            count = 0
        return count

    def _parse_state(self, s: str) -> Optional[str]:
        corrections = {
            "Califonria": "California",
        }
        for mistake, correction in corrections.items():
            if s == mistake:
                s = correction
                break
        return self._parse_str_or_none(s)

    def _parse_taxon(self, raw: str) -> str | None:
        # cannot be used to parse species
        s = self._parse_str_or_none(raw)
        if s is None or s == ".":
            return None
        if s[0] == '"' and s[-1] == '"':
            s = s[1:-1]
        if " or " in s or " and " in s or "+" in s or "/" in s:
            self.det_descriptors.append(s)
            return None
        match = REGEX_PARENED.search(s)
        if match is not None:
            descriptor = s[match.start(0) + 1 : match.end(0) - 1].strip()
            if descriptor == "?":
                descriptor = UNCERTAIN_DET_TEXT
            if descriptor not in self.det_descriptors:
                self.det_descriptors.append(descriptor)
            s = s[0 : match.start(0)].strip()
        if "-" in s:
            dashIndex = s.index("-")
            s = s[0:dashIndex]
        if " " in s:
            self.add_problem("Taxon '%s' contains spaces" % s)
        return s

    def _parse_type_status(self, s: str) -> Optional[str]:
        if s == "":
            return None
        return (
            s.upper().replace("HOLOTYE", "HOLOTYPE").replace("PARAYPTES", "PARATYPES")
        )

    def _revise_lat_long(self, lat_longs: LatLongTable) -> None:
        # Alex's MDB exports were preserving coordinate precision, mine weren't,
        # and we needed to work based on my exports. So I stored Alex's coordinates
        # off in a file that gets loaded into LatLongTable and I use the precision
        # found in that file if James hasn't since changed the coordinates or the
        # coordinates aren't given in a way that preserves precision (such as by
        # appending N, S, E, W, or x, making the coordinate a string.)

        lat_long = lat_longs.get_by_id(self.id)
        if self.latitude is not None and not self.trust_latitude_precision:
            if lat_long is not None and self.latitude == lat_long.latitude:
                self.latitude = lat_long.latitude  # may change the precision
            else:
                self.latitude, precision = self._to_min_precision(self.latitude)
                if precision < 5:
                    self.add_problem(
                        "unknown latitude precision %s (< 5 digits)" % self.latitude
                    )

        if self.longitude is not None and not self.trust_longitude_precision:
            if lat_long is not None and self.longitude == lat_long.longitude:
                self.longitude = lat_long.longitude  # may change the precision
            else:
                self.longitude, precision = self._to_min_precision(self.longitude)
                if precision < 5:
                    self.add_problem(
                        "unknown longitude precision %s (< 5 digits)" % self.longitude
                    )

    def _to_min_precision(self, dec: Decimal) -> tuple[Decimal, int]:
        s = str(dec)
        i = len(s)
        while i > 0 and s[i - 1] == "0":
            i -= 1
        s = s[0:i]
        dot_offset = s.find(".")
        return (Decimal(s), 0 if dot_offset < 0 else len(s) - dot_offset - 1)

    def _validate(self, raw_day: str, raw_month: str, raw_year: str) -> None:

        if not self.has_specimen():
            self.add_problem("names no specimen")

        if self.country is None:
            self.add_problem("missing country")
        if (
            self.country in ["USA", "Belize", "Guatemala", "Mexico"]
            and self.state is None
        ):
            self.add_problem("missing state in %s" % self.country)

        if (
            self.locality_correct is None
            and self.locality_on_label is None
            and self.county is None
        ):
            self.add_problem("missing locality information")

        if self.date_time is not None:
            start_date = self.date_time.start_date
            year_column = self._parse_int_or_0("Collection Year", raw_year)
            month_column = self._parse_int_or_0("Collection Month", raw_month)
            day_column = self._parse_int_or_0("Collection Day", raw_day)

            if start_date is not None:
                if (
                    year_column != 0
                    and start_date.year is not None
                    and year_column != start_date.year
                ):
                    self.add_problem(
                        "Year column %d disagrees with parsed year %d"
                        % (year_column, start_date.year)
                    )
                elif (
                    month_column != 0
                    and start_date.month is not None
                    and month_column != start_date.month
                ):
                    self.add_problem(
                        "Month column %d disagrees with parsed month %d"
                        % (month_column, start_date.month)
                    )
                elif (
                    day_column != 0
                    and start_date.day is not None
                    and day_column != start_date.day
                ):
                    self.add_problem(
                        "Day column %d disagrees with parsed day %d"
                        % (day_column, start_date.day)
                    )

        if self.species is None:
            if self.subspecies is not None:
                self.add_problem("Supspecies given without species")
            elif self.authors is not None:
                self.add_problem("Authors given without species")


def parse_species_author(
    species_author: str | None, descriptors: list[str]
) -> Tuple[str | None, str | None, str | None]:
    if species_author is None or species_author == ".":
        return (None, None, None)

    if "manuscript name" in species_author:
        species_author = "n. sp."
    else:
        species_author = (
            species_author.replace(". ", ".")
            .replace(".", ". ")
            .replace(". ,", ".,")  ## for properly tracking oddities
            .strip()
        )
    species_author = re.sub(REGEX_SPACES, " ", species_author)

    species = species_author
    subspecies: str | None = None
    author: str | None = None

    match = REGEX_AUTHOR_START.search(species_author)
    if match is not None:
        author_start_offset = match.start(0)
        if author_start_offset == 0:
            return (None, None, species_author)
        author_end_offset = len(species_author)
        prev_paren_offset = species_author.rfind("(", 0, author_start_offset)
        if prev_paren_offset >= 0:
            author_start_offset = prev_paren_offset
            author_end_offset = species_author.find(")", author_start_offset)
            if author_end_offset >= 0:
                author_end_offset += 1
        else:
            author_end_offset = species_author.find("(")
        if author_end_offset < 0:
            author_end_offset = len(species_author)

        author = species_author[author_start_offset:author_end_offset].strip()
        if author[0] == "(" and author[len(author) - 1] != ")":
            author += ")"
        author = author.replace(". ", ".")

        species = species_author[0:author_start_offset].strip()
        if author_end_offset < len(species_author):
            species += " " + species_author[author_end_offset:].strip()
        species = species.strip()

    if " and " in species or "+" in species or "/" in species or " or " in species:
        descriptors.append(species)
        return (None, None, None)

    words = species.split()
    match = REGEX_LOWER_LETTERS.match(words[0])
    if match is not None:
        if len(words) > 1 and words[1][0].isalpha():
            subspecies = species[len(words[0]) :].strip()
            species = words[0]

    if species in ["sp.", "so.", "sp,", "so,", "sp", "so"] and subspecies is None:
        return (None, None, None)
    if subspecies is not None and subspecies.startswith("n."):
        if not subspecies.startswith(NEW_SUBSPECIES):
            species += " " + subspecies
            subspecies = None
        else:
            descriptors.append(subspecies)

    species = species.replace(" near ", " nr. ")
    if species.startswith("sp. ("):
        descriptors.append(species[len("sp. (") : -1].strip())
        return (None, None, None)
    if species.startswith("sp.,"):
        descriptors.append(species[len("sp.,") :].strip())
        return (None, None, None)
    if species.startswith("sp. prob."):
        species = species[len("sp. prob.") :].strip()
        descriptors.append("probable det.")

    if "?" in species:
        descriptor = species
        species = species.replace("(?)", "").replace("?", "").replace("  ", " ").strip()
        if "n." in species or " " in species:
            if not "n." in species:
                descriptors.append(descriptor)
            return (None, None, None)
        else:
            descriptors.append(UNCERTAIN_DET_TEXT)

    if "n." in species:
        if not species.startswith("n."):
            species = "n. sp."
        elif "," in species:
            descriptors.append(species)
            species = "n. sp."
    elif "cf." in species:
        descriptors.append(species)
        return (None, None, None)

    return (species, subspecies, author)
