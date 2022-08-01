from __future__ import annotations
from typing import Any, Optional

from src.lib.date_token import DateToken
from src.lib.parse_error import ParseError


class PartialDate:
    """Represents a date with possible unknown values."""

    def __init__(
        self,
        year: Optional[int] = None,
        month: Optional[int] = None,
        day: Optional[int] = None,
        hour: Optional[int] = None,
        minute: Optional[int] = None,
        part_of_month: Optional[str] = None,
    ):

        self.assumed_year: bool = False  # whether assumed second year of a range
        self.year: Optional[int] = year
        self.month: Optional[int] = month
        self.day: Optional[int] = day
        self.hour: Optional[int] = hour
        self.minute: Optional[int] = minute
        self.part_of_month: Optional[str] = part_of_month

    def __str__(self) -> str:
        if self.year is None:
            s = "????"
        else:
            s = "%02d" % self.year
        if self.month is not None:
            s += "-%s" % DateToken.to_roman(self.month)
        if self.day is not None:
            s += "-%d" % self.day
        if self.part_of_month is not None:
            s += "-%s" % self.part_of_month
        if self.hour is not None and self.minute is not None:
            s += "/%02d:%02d" % (self.hour, self.minute)
        return s

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, PartialDate):
            return NotImplemented
        return (
            self.year == other.year
            and self.month == other.month
            and self.day == other.day
            and self.hour == other.hour
            and self.minute == other.minute
            and self.part_of_month == other.part_of_month
        )

    def clone_date(self) -> PartialDate:
        clone = PartialDate(self.year, self.month, self.day)
        clone.assumed_year = True
        return clone

    def normalize(self) -> Optional[str]:
        if self.year is None:
            return None
        day = "??" if self.day is None else str(self.day)
        month = "??"
        if self.month is not None:
            month = DateToken.to_roman(self.month)
            assert month is not None
        return "%s-%s-%d" % (day, month, self.year)

    def set_time(self, time_int: int) -> None:
        if time_int == 2400:
            time_int = 0
        self.hour = time_int // 100
        self.minute = time_int % 100

    def to_MMDDYYYY(self) -> Optional[str]:
        if self.year is None:
            return None
        m = (
            "00"
            if self.month is None
            else ("0" if self.month < 10 else "") + str(self.month)
        )
        d = (
            "00"
            if self.month is None or self.day is None
            else ("0" if self.day < 10 else "") + str(self.day)
        )
        return "%s/%s/%d" % (m, d, self.year)

    def to_YYYYMMDD(self) -> Optional[str]:
        if self.year is None:
            return None
        m = (
            "??"
            if self.month is None
            else ("0" if self.month < 10 else "") + str(self.month)
        )
        d = (
            "??"
            if self.month is None or self.day is None
            else ("0" if self.day < 10 else "") + str(self.day)
        )
        return "%d-%s-%s" % (self.year, m, d)

    def validate(self, context: str) -> None:
        if self.month is not None and (self.month < 1 or self.month > 12):
            raise ParseError("%s month not in valid range" % context)

        if self.day is not None and (self.day < 1 or self.day > 31):
            raise ParseError("%s day not in valid range" % context)

        if self.hour is not None and (self.hour < 0 or self.hour > 23):
            raise ParseError("%s hour not in valid range" % context)

        if self.minute is not None and (self.minute < 0 or self.minute > 59):
            raise ParseError("%s minute not in valid range" % context)

        if self.part_of_month is not None and self.day is not None:
            raise ParseError("specified both day of month and part of month")
