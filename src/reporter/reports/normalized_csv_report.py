from __future__ import annotations
from typing import TYPE_CHECKING
from decimal import Decimal
import sys
import csv

from src.lib.identity import Identity

if TYPE_CHECKING:
    from src.reporter.james_table import *
from src.reporter.record_filter import RecordFilter
from src.reporter.reports.report import Report


class NormalizedCsvReport(Report):
    def __init__(
        self,
        table: JamesTable,
        record_filter: RecordFilter,
    ):
        super().__init__(table, record_filter)
        table.revise_names(unify_names_by_sound=True, merge_with_reference_names=True)

    def show(self) -> None:
        headers = [
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
            "Species",
            "Subspecies",
            "Country",
            "State",
            "County",
            "Locality",
            "Locality on Label",
            "Latitude",
            "Longitude",
            "Owner",
            "Start Date",
            "End Date",
            "Date on Label",
            "Collectors",
            "Collections",
            "Type Status",
            "Determiners",
            "Determination Date",
            "Number of Specimens",
            "Notes",
        ]
        writer = csv.DictWriter(
            sys.stdout,
            fieldnames=headers,
            delimiter=",",
            quotechar='"',
            lineterminator="\n",
        )
        writer.writeheader()

        for record in self._filtered_records():
            if record.date_time is None:
                start_date = None
                end_date = None
            else:
                start_date = record.date_time.start_date
                end_date = record.date_time.end_date

            row = {
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
                "Species": _to_column(record.species),
                "Subspecies": _to_column(record.subspecies),
                "Taxon Author": _to_column(record.authors),
                "Country": _to_column(record.country),
                "State": _to_column(record.state),
                "County": _to_column(record.county),
                "Locality": _to_column(record.locality_correct),
                "Locality on Label": _to_column(record.locality_on_label),
                "Latitude": _to_column(record.latitude),
                "Longitude": _to_column(record.longitude),
                "Owner": _to_column(record.owner),
                "Start Date": _to_column(
                    None if start_date is None else start_date.normalize()
                ),
                "End Date": _to_column(
                    None if end_date is None else end_date.normalize()
                ),
                "Date on Label": _to_column(record.raw_date_time),
                "Collectors": _to_names_column(record.collectors),
                "Type Status": _to_column(record.type_status),
                "Determiners": _to_names_column(record.identifier_year.determiners),
                "Determination Date": _to_column(record.identifier_year.year),
                "Collections": (
                    "" if record.collections is None else ", ".join(record.collections)
                ),
                "Number of Specimens": _to_column(record.specimen_count),
                "Notes": _to_column(record.misc_notes),
            }
            assert len(row) == len(headers)
            writer.writerow(row)


def _to_column(s: Optional[str | int | Decimal]) -> str:
    return "" if s is None else str(s)


def _to_names_column(identities: Optional[list[Identity]]) -> str:
    if identities is None:
        return ""
    names: list[str] = []
    for identity in identities:
        names.append(identity.get_lnf_primary())
    return "; ".join(names)
