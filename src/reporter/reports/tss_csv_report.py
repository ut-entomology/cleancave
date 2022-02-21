from __future__ import annotations
from typing import TYPE_CHECKING
from decimal import Decimal
import sys
import csv

from src.lib.identity import Identity

if TYPE_CHECKING:
    from src.reporter.james_table import *
from src.reporter.record_filter import RecordFilter, StrictlyTexasCaveRecordFilter
from src.reporter.reports.report import Report

MAX_RECORDS_PER_COUNTY = 3


class TssCsvReport(Report):
    def __init__(
        self,
        table: JamesTable,
        _: RecordFilter,
    ):
        super().__init__(table, StrictlyTexasCaveRecordFilter())
        table.revise_names(unify_names_by_sound=True, merge_with_reference_names=True)
        self._record_count_by_county: dict[str, int] = {}

    def show(self) -> None:
        headers = [
            "ID",
            "Catalog Number",
            "Phylum",
            "Class",
            "Subclass",
            "Order",
            "Suborder",
            "Infraorder",
            "Family",
            "Subfamily",
            "Genus",
            "Species/Author",
            "Subspecies",
            "Country",
            "State",
            "County",
            "Locality Name",
            "Latitude",
            "Longitude",
            "Owner",
            "Date/Time",
            "Collector",
            "Type Status",
            "Collection",
            "Specimen Count",
            "Notes",
        ]
        writer = csv.DictWriter(
            sys.stdout, fieldnames=headers, dialect="excel", lineterminator="\n"
        )
        writer.writeheader()

        for record in self._filtered_records():
            row = {
                "ID": _to_column(record.id),
                "Catalog Number": _to_column(record.catalog_number),
                "Phylum": _to_column(record.phylum),
                "Class": _to_column(record.class_),
                "Subclass": _to_column(record.subclass),
                "Order": _to_column(record.order),
                "Suborder": _to_column(record.suborder),
                "Infraorder": _to_column(record.infraorder),
                "Family": _to_column(record.family),
                "Subfamily": _to_column(record.subfamily),
                "Genus": _to_column(record.genus),
                "Species/Author": _to_column(record.species_author),
                "Subspecies": _to_column(record.subspecies),
                "Country": _to_column(record.country),
                "State": _to_column(record.state),
                "County": _to_column(record.county),
                "Locality Name": _to_column(self._get_safe_locality_name(record)),
                "Latitude": _to_column(
                    self._get_safe_coordinate(record, record.latitude)
                ),
                "Longitude": _to_column(
                    self._get_safe_coordinate(record, record.longitude)
                ),
                "Owner": _to_column(record.owner),
                "Date/Time": record.normalized_date_time,
                "Collector": _to_column(
                    Identity.get_corrected_primary_names(record.collectors)
                ),
                "Type Status": _to_column(record.type_status),
                "Collection": (
                    "" if record.collections is None else ", ".join(record.collections)
                ),
                "Specimen Count": _to_column(record.specimen_count),
                "Notes": _to_column(self._get_notes(record)),
            }
            assert len(row) == len(headers)

            county = record.county if record.county is not None else "(unspecified)"
            if county in self._record_count_by_county:
                count = self._record_count_by_county[county]
            else:
                count = 0
            if count < MAX_RECORDS_PER_COUNTY:
                writer.writerow(row)
                count += 1
                self._record_count_by_county[county] = count

    def _get_notes(self, record: SpecimenRecord) -> Optional[str]:
        notes = record.misc_notes
        if record.is_sensitive:
            notes = self._append_notes(notes, "sensitive coordinates withheld")
        return notes


def _to_column(s: Optional[str | int | Decimal]) -> str:
    return "" if s is None else str(s)
