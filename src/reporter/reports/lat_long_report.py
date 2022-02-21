from __future__ import annotations
from typing import TYPE_CHECKING
from decimal import Decimal

if TYPE_CHECKING:
    from src.reporter.james_table import *
from src.reporter.record_filter import RecordFilter

from src.reporter.reports.report import Report


class LatLongReport(Report):
    def __init__(
        self,
        table: JamesTable,
        record_filter: RecordFilter,
        low_precision_only: bool,
    ):
        super().__init__(table, record_filter)
        self.low_precision_only = low_precision_only

    def show(self) -> None:
        for record in self._filtered_records():
            if self.low_precision_only:
                if (
                    self._to_precision(record.latitude) < 4
                    or self._to_precision(record.longitude) < 4
                ):
                    locality = (
                        record.locality_correct
                        if record.locality_correct is not None
                        else record.locality_correct
                    )
                    print(
                        "%d,%s,%s,%s,%s,%s,%s"
                        % (
                            record.id,
                            str(record.catalog_number),
                            str(record.latitude),
                            str(record.longitude),
                            record.country,
                            record.state,
                            locality,
                        )
                    )
            else:
                print(
                    "%d,%s,%s,%s"
                    % (
                        record.id,
                        str(record.catalog_number),
                        str(record.latitude),
                        str(record.longitude),
                    )
                )

    def _to_precision(self, coord: Decimal | None):
        if coord is None:
            return 100
        coordStr = str(coord)
        return len(coordStr) - coordStr.rfind(".") - 1
