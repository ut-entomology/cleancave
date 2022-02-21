from __future__ import annotations
from typing import Optional

from src.util.any_csv import load_csv
from src.reporter.lat_long_record import LatLongRecord


class LatLongTable:
    def __init__(self, csv_filename: str):
        self._csv_filename = csv_filename
        self._records: dict[int, LatLongRecord] = {}

    def load(self) -> None:
        load_csv(self._csv_filename, self._receive_row)

    def get_by_id(self, record_id: int) -> Optional[LatLongRecord]:
        try:
            return self._records[record_id]
        except KeyError:
            return None

    def _receive_row(self, row: dict[str, str]) -> bool:
        record = LatLongRecord(
            row["id"], row["cat_num"], row["latitude"], row["longitude"]
        )
        if record.latitude is not None or record.longitude is not None:
            self._records[record.id] = record
        return True
