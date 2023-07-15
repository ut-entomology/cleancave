from __future__ import annotations
from typing import Optional
import re

from src.lib.declared_names_table import DeclaredNamesTable
from src.lib.partial_date import PartialDate
from src.lib.identity import Identity
from src.util.any_csv import load_csv
from src.reporter.lat_long_table import LatLongTable
from src.reporter.record_filter import RecordFilter
from src.reporter.specimen_record import SpecimenRecord
from src.reporter.identity_catalog import IdentityCatalog

StrCountDict = dict[str, int]
IdentityDict = dict[str, Identity]

END_CAT_NUM = "_END_"
EMPTY_TERM = "(blank)"


class JamesTable:
    """Representation of James' spreadsheet table."""

    def __init__(
        self,
        lat_longs_filename: Optional[str],
        records_filename: str,
        declared_names_table: DeclaredNamesTable,
    ):
        self._lat_longs_filename = lat_longs_filename
        self._records_filename = records_filename
        self._summarized = False
        self._revised_names = False
        self._lat_longs: Optional[LatLongTable] = None

        # Records and automatically-computed stats.

        self.records: list[SpecimenRecord] = []
        self.empty_record_ids: list[int] = []
        self.catalog_numbers_to_records: dict[int, list[SpecimenRecord]] = {}
        self.max_catalog_number = 0
        self.declared_names_table = declared_names_table  # required to parse names

        # Initialize summary data.

        self.catalog_numbers: dict[Optional[int], bool] = {}
        self.james_ids: dict[int, bool] = {}
        self.phyla: StrCountDict = {}
        self.classes: StrCountDict = {}
        self.subclasses: StrCountDict = {}
        self.orders: StrCountDict = {}
        self.suborders: StrCountDict = {}
        self.infraorders: StrCountDict = {}
        self.families: StrCountDict = {}
        self.subfamilies: StrCountDict = {}
        self.genera: StrCountDict = {}
        self.species: StrCountDict = {}
        self.subspecies: StrCountDict = {}
        self.genus_species: StrCountDict = {}
        self.species_subspecies: StrCountDict = {}
        self.authors: StrCountDict = {}
        self.continents: StrCountDict = {}
        self.countries: StrCountDict = {}
        self.states: StrCountDict = {}
        self.counties: StrCountDict = {}
        self.localities: StrCountDict = {}
        self.lowercaseLocalities: dict[str, list[str]] = {}
        self.localityCounties: dict[str, list[str | None]] = {}
        self.countyLocalities: dict[str | None, list[str]] = {}
        self.owners: StrCountDict = {}
        self.localityOwners: dict[str, list[str | None]] = {}
        self.microhabitats: StrCountDict = {}
        self.type_statuses: StrCountDict = {}
        self.collections: StrCountDict = {}
        self.seasons: StrCountDict = {}
        self.parts_of_month: StrCountDict = {}
        self.parts_of_day: StrCountDict = {}
        self.total_specimen_count: int = 0

        self.raw_names_by_collection: dict[Optional[str], dict[str, bool]] = {}
        self.identity_catalog = IdentityCatalog(declared_names_table)

    @classmethod
    def drop_parens(cls, s: Optional[str]) -> Optional[str]:
        if s is None:
            return None
        return re.sub(r"\([^)]*\)", "", s).strip()

    def load(self) -> None:
        if self._lat_longs_filename is not None:
            self._lat_longs = LatLongTable(self._lat_longs_filename)
            self._lat_longs.load()
        load_csv(self._records_filename, self._receive_row)

    def revise_names(
        self, unify_names_by_sound: bool, merge_with_reference_names: bool
    ) -> None:
        if self._revised_names:
            return
        assert self._summarized, "Must call summarize() before revising names."
        self.identity_catalog.correct_and_consolidate(
            unify_names_by_sound, merge_with_reference_names
        )
        self._revised_names = True

    def summarize(self, record_filter: RecordFilter) -> None:
        if self._summarized:
            return
        for record in self.records:
            if record is not None:
                if record_filter.test(record):
                    self.catalog_numbers[record.catalog_number] = True
                    self._collect_record(record)
                self._collect_agents(record)
        self._summarized = True

    def _collect_record(self, record: SpecimenRecord) -> None:

        self._collect_value(record.phylum, self.phyla)
        self._collect_value(record.class_, self.classes)
        self._collect_value(record.subclass, self.subclasses)
        self._collect_value(record.order, self.orders)
        self._collect_value(record.suborder, self.suborders)
        self._collect_value(record.infraorder, self.infraorders)
        self._collect_value(record.family, self.families)
        self._collect_value(record.subfamily, self.subfamilies)
        self._collect_value(record.genus, self.genera)
        self._collect_value(record.species, self.species)
        self._collect_value(record.subspecies, self.subspecies)
        self._collect_value(_combine(record.genus, record.species), self.genus_species)
        self._collect_value(
            _combine(record.species, record.subspecies), self.species_subspecies
        )
        self._collect_value(JamesTable.drop_parens(record.authors), self.authors)
        self._collect_value(record.continent, self.continents)
        self._collect_value(record.country, self.countries)
        self._collect_value(record.state, self.states)
        self._collect_value(record.county, self.counties)
        self._collect_value(record.locality_correct, self.localities)
        self._collect_value(record.owner, self.owners)
        self._collect_value(record.microhabitat, self.microhabitats)
        self._collect_value(record.type_status, self.type_statuses)
        for collection in record.collections:
            self._collect_value(collection, self.collections)

        if self.total_specimen_count is not None and record.specimen_count is not None:
            self.total_specimen_count += record.specimen_count

        date_time = record.date_time
        if date_time is not None:
            if date_time.start_date is not None:
                self._collect_partial_date(date_time.start_date)
            if date_time.end_date is not None:
                self._collect_partial_date(date_time.end_date)
            if date_time.season is not None:
                self._collect_value(date_time.season, self.seasons)
            if date_time.part_of_day is not None:
                self._collect_value(date_time.part_of_day, self.parts_of_day)

        if record.locality_correct is not None:

            if record.county in self.countyLocalities:
                countyLocalities = self.countyLocalities[record.county]
                if record.locality_correct not in countyLocalities:
                    countyLocalities.append(record.locality_correct)
            else:
                self.countyLocalities[record.county] = [record.locality_correct]

            lowercase_locality = record.locality_correct.lower()

            if lowercase_locality in self.lowercaseLocalities:
                original_localities = self.lowercaseLocalities[lowercase_locality]
                if record.locality_correct not in original_localities:
                    original_localities.append(record.locality_correct)
            else:
                self.lowercaseLocalities[lowercase_locality] = [record.locality_correct]

            if lowercase_locality in self.localityCounties:
                locality_counties = self.localityCounties[lowercase_locality]
                if record.county not in locality_counties:
                    locality_counties.append(record.county)
            else:
                self.localityCounties[lowercase_locality] = [record.county]

            if lowercase_locality in self.localityOwners:
                locality_owners = self.localityOwners[lowercase_locality]
                if record.owner not in locality_owners:
                    locality_owners.append(record.owner)
            else:
                self.localityOwners[lowercase_locality] = [record.owner]

    def _collect_agents(self, record: SpecimenRecord) -> None:
        self._collect_identities(record.collectors)
        if record.identifier_year is not None:
            self._collect_identities(record.identifier_year.determiners)

    def _collect_identities(self, source_identities: Optional[list[Identity]]):
        if source_identities is not None:
            for identity in source_identities:
                self.identity_catalog.add(identity)

    def _collect_partial_date(self, partial_date: PartialDate) -> None:
        if partial_date.part_of_month is not None:
            self._collect_value(partial_date.part_of_month, self.parts_of_month)

    @classmethod
    def _collect_value(cls, s: Optional[str], dictionary: StrCountDict) -> None:
        if s == "" or s is None:
            s = EMPTY_TERM
        # Catching an exception is faster than checking dictionary first.
        try:
            dictionary[s] += 1
        except KeyError:
            dictionary[s] = 1

    def _receive_row(self, row: dict[str, str]) -> bool:

        # Quit prematurely if there are no more records.

        raw_catalog_number = row["Catalog Number"].strip()
        if raw_catalog_number == END_CAT_NUM:
            return False

        # Create a record for the line and log its data.

        record = SpecimenRecord(
            self._lat_longs,
            self.declared_names_table,
            row["ID"].strip(),
            row["Proofed-JR"].strip(),
            raw_catalog_number,
            row["Phylum"].strip(),
            row["Class"].strip(),
            row["Subclass"].strip(),
            row["Order"].strip(),
            row["Suborder"].strip(),
            row["Infraorder"].strip(),
            row["Family"].strip(),
            row["Subfamily"].strip(),
            row["Genus"].strip(),
            row["Species/Author"].strip(),
            row["Subspecies"].strip(),
            row["Species Name on Label"].strip(),
            row["Continent"].strip(),
            row["Country"].strip(),
            row["State"].strip(),
            row["County"].strip(),
            row["Locality-Correct Name"].strip(),
            row["Locality as on label"].strip(),
            row["Datum"].strip(),
            row["Latitude"].strip(),
            row["Longitude"].strip(),
            row["coordinateUncertaintyInMeters"].strip(),
            row["Owner"].strip(),
            row["Microhabitat"].strip(),
            row["Date/Time"].strip(),
            row["Collector"].strip(),
            row["Females"].strip(),
            row["Males"].strip(),
            row["Immatures"].strip(),
            row["Type Status"].strip(),
            row["Collection"].strip(),
            row["Identifier/Year"].strip(),
            row["Number of Specimens"].strip(),
            row["Collection Year"].strip(),
            row["Collection Month"].strip(),
            row["Collection Day"].strip(),
            row["startDate"].strip(),
            row["endDate"].strip(),
            row["verbatimEventDate"].strip(),
            row["misc_comments_notes"].strip(),
            row["area"].strip(),
        )

        if record.catalog_number is not None or record.has_specimen():
            self.records.append(record)
        else:
            self.empty_record_ids.append(record.id)

        # Collect catalog number statistics.

        cat_num = record.catalog_number
        if cat_num is not None and cat_num > 0:
            if cat_num in self.catalog_numbers_to_records:
                self.catalog_numbers_to_records[cat_num].append(record)
            else:
                self.catalog_numbers_to_records[cat_num] = [record]
            if self.max_catalog_number < cat_num:
                self.max_catalog_number = cat_num
        return True


def _combine(term1: str | None, term2: str | None) -> str | None:
    if term2 is None:
        return None
    if term1 is None:
        return "[missing] " + term2
    return term1 + " " + term2
