from __future__ import annotations
from typing import Iterator, TYPE_CHECKING
from abc import ABC, abstractmethod
import math
from decimal import Decimal

if TYPE_CHECKING:
    from src.reporter.james_table import *
from src.reporter.record_filter import RecordFilter
from src.reporter.specimen_record import SpecimenRecord


class Report(ABC):

    LINE_WIDTH: int = 88  # print to lines of this maximum width

    class FilteredRecordsIterator:
        def __init__(self, records: list[SpecimenRecord], record_filter: RecordFilter):
            self._records_iterator = iter(records)
            self._record_filter = record_filter

        def __iter__(self):
            return self

        def __next__(self) -> SpecimenRecord:
            next_record = next(self._records_iterator)
            while not self._record_filter.test(next_record):
                next_record = next(self._records_iterator)
            return next_record

    def __init__(
        self,
        table: JamesTable,
        record_filter: RecordFilter,
    ):
        self.table: JamesTable = table
        self._record_filter: RecordFilter = record_filter
        self._filtered_identities: Optional[dict[str, bool]] = None
        self._filtered_raw_names: Optional[dict[str, bool]] = None
        self._filtered_collectors: Optional[dict[str, bool]] = None

        table.summarize(record_filter)

    @abstractmethod
    def show(self) -> None:
        pass

    def _append_notes(self, old_notes: Optional[str], new_notes: Optional[str]) -> str:
        if new_notes is None:
            raise Exception("New notes unexpectedly None")
        if old_notes is not None and old_notes != "":
            new_notes = "%s; %s" % (old_notes, new_notes)
        return new_notes

    def _get_safe_coordinate(
        self, record: SpecimenRecord, coord: Optional[Decimal]
    ) -> Optional[Decimal]:
        if coord is None or record.is_sensitive:
            return None
        if record.state == "Texas":
            return Decimal("{:.2f}".format(coord))  # this rounds Decimals (not floats)
        return coord

    def _get_safe_locality_name(self, record: SpecimenRecord) -> Optional[str]:
        if record.is_sensitive:
            if record.owner is None:
                raise Exception("No owner despite being sensitive")
            if record.locality_correct is None:
                return "TBD, " + record.owner
            return "%s, %s" % (record.locality_correct, record.owner)
        return (
            record.locality_correct
            if record.locality_correct is not None
            else record.locality_on_label
        )

    def _filtered_records(self) -> Iterator[SpecimenRecord]:
        return self.FilteredRecordsIterator(self.table.records, self._record_filter)

    def _is_filtered_identity(self, identity: Identity) -> bool:
        if self._filtered_identities is None:
            self.__filter_identities()
            assert self._filtered_identities is not None
        return str(identity.get_master_copy()) in self._filtered_identities

    def _is_filtered_raw_name(self, raw_name: str) -> bool:
        if self._filtered_raw_names is None:
            self.__filter_identities()
            assert self._filtered_raw_names is not None
        return raw_name in self._filtered_raw_names

    def _print_columns(self, messages: list[str]):

        max_width = 0
        for message in messages:
            if message is None:
                message = EMPTY_TERM
            if len(message) > max_width:
                max_width = len(message)

        column_count = (self.LINE_WIDTH + 3) // (max_width + 3)

        if column_count == 0:
            for message in messages:
                print("%s", message)
        else:
            line_count = math.ceil(len(messages) / column_count)
            for i in range(line_count):
                j = i
                while j < len(messages):
                    if j == i:
                        print("", end="")  # start of line
                    else:
                        print(" | ", end="")
                    message = messages[j]
                    if message is None or message == "":
                        message = EMPTY_TERM
                    print(message.ljust(max_width, " "), end="")
                    j += line_count
                print()

    def _print_filter_title(self) -> None:
        print("\n**** Report of %s ****" % self._record_filter.name)

    def _print_segments(
        self,
        segments: list[str],
        first_line: str = "",
        start_of_line: str = "  ",
        delimiter: str = ", ",
    ):
        line = first_line
        just_starting = True
        for segment in segments:
            if not just_starting:
                line += delimiter
            if len(line) + len(segment) > self.LINE_WIDTH:
                print(line)
                line = start_of_line
            line += segment
            just_starting = False
        print(line)

    def _to_collection_list(self, collections: list[str]) -> str:
        abbrevs: list[str] = []
        for collection in collections:
            if collection == "":
                abbrevs.append("none")
            else:
                abbrevs.append(collection[0:4].strip())
        return ",".join(abbrevs)

    def _to_species_author(self, record: SpecimenRecord) -> str | None:
        if record.species is None:
            return None
        species_author = record.species
        if record.subspecies is not None:
            species_author += " " + record.subspecies
        if record.authors is not None:
            species_author += " " + record.authors
        return species_author

    def __filter_identities(self) -> None:
        self._filtered_identities = {}
        self._filtered_raw_names = {}
        self._filtered_collectors = {}

        for record in self._filtered_records():
            # had_hebard = "Hebard" in self._filtered_raw_names
            if record.collectors is not None:
                self.__load_filtered_identities(record.collectors, True)
            if record.identifier_year.determiners is not None:
                self.__load_filtered_identities(
                    record.identifier_year.determiners, False
                )
            # if not had_hebard and "Hebard" in self._filtered_raw_names:
            #     raise Exception("Hebard add for ID %d" % record.id)

    def __load_filtered_identities(
        self, identities: list[Identity], isCollector: bool
    ) -> None:
        assert self._filtered_identities is not None
        assert self._filtered_raw_names is not None
        assert self._filtered_collectors is not None

        for identity in identities:
            master_identity = identity.get_master_copy()
            self._filtered_identities[str(master_identity)] = True
            if identity.raw_name is not None:
                self._filtered_raw_names[identity.raw_name] = True
            if isCollector:
                self._filtered_collectors[identity.get_lnf_primary()] = True
