from __future__ import annotations
from datetime import date
from typing import Any, Callable, Optional

from src.lib.partial_date import PartialDate
from src.lib.date_token import DateToken
from src.lib.parse_error import ParseError

import re

_StateFunc = Callable[[DateToken], Any]


class JamesDateTime:
    """Represents the date/time(s) at which a specimen was collected."""

    US_DATE_REGEX = re.compile(r"^(\d\d?)/(\d\d?)/(\d\d(?:\d\d)?)")
    BAD_US_DATE_REGEX = re.compile(r"^(\d\d?/\d\d?)[-.](\d\d\d\d)$")
    SIMPLE_JAMES_DATE = re.compile(r"^\d\d[-/][IVXivx]+[-/]\d\d?(?:/([^\d/]+))?$")

    DATE_TOKEN_REGEX = re.compile(
        r"\d+(?::\d+)?|"
        r"[ivxIVX]+|"
        r"[a-zA-Z][^-/,=]*[^-/,= ]|"
        r"[a-zA-Z]|"
        r" *(?:--?|[,=/]) *"
    )

    def __init__(
        self,
        start_date: Optional[PartialDate] = None,
        end_date: Optional[PartialDate] = None,
        season: Optional[str] = None,
        part_of_day: Optional[str] = None,
    ):
        self.start_date: Optional[PartialDate] = start_date
        self.end_date: Optional[PartialDate] = end_date
        self.season: Optional[str] = season
        self.part_of_day: Optional[str] = part_of_day

        self._token_index: int = 0
        self._tokens: Optional[list[DateToken]] = None
        self._state: _StateFunc = self._state_year_or_month

    def __str__(self) -> str:
        # This prints year first in comformance with James' convention
        # but in violation of standard convention.
        # TODO: Can I make this standard year last?
        s = ""
        if self.start_date is not None:
            s += str(self.start_date)
        if self.end_date is not None:
            s += ", %s" % str(self.end_date)
        if self.season is not None:
            s += "/%s" % self.season
        if self.part_of_day is not None:
            s += "/%s" % self.part_of_day
        return s

    @classmethod
    def correct_raw_date_time(cls, s: str) -> str:
        match = cls.BAD_US_DATE_REGEX.match(s)
        if match is not None:
            s = "%s/%s" % (match.group(1), match.group(2))
        return s

    def load(self, s: str) -> JamesDateTime:

        if s == "":
            raise ParseError("missing date")

        # Apply lexical modifications necessary to properly parse.

        match = self.US_DATE_REGEX.match(s)
        if match is not None:
            # U.S. date format mm/dd/yyyy
            full_match = match.group(0)
            if len(s) <= len(full_match) or s[len(full_match) :] == full_match:
                month = int(match.group(1))
                day = int(match.group(2))
                year = int(match.group(3))
                s = "%d-%s-%d" % (year % 100, DateToken.TO_ROMAN_MONTHS[month], day)
                if year > 100:
                    assert year == self._expand_james_year(year % 100)
        elif s == "05-VIII-18, IX-12, 15":
            # Not equivalent, but expresses range, which is all I'm capturing.
            s = "05-VIII-18, 15-IX-18"

        elif s == "0 I-V-29, 02-II-17":
            # Not equivalent, but expresses range, which is all I'm capturing.
            s = "00-I-29, 02-II-17"

        else:
            s = s.replace(" or ", ", ")

        # Parse James' date/time as a stream of tokens.

        raw_tokens = self.DATE_TOKEN_REGEX.findall(s)
        if len(raw_tokens) == 0:
            raise ParseError("invalid date")
        try:
            # Collect the non-delimeter tokens.

            self._tokens = []
            delimiter_count = 0
            for raw_token in raw_tokens:
                if DateToken.is_delimeter(raw_token):
                    delimiter_count += 1
                    if delimiter_count >= 2:
                        raise ParseError("extra delimiter '%s'" % raw_token)
                else:
                    self._tokens.append(DateToken(raw_token))
                    delimiter_count = 0

            # Iterate state machine over the non-delimeter tokens. Track the
            # token index in the object to support lookaheads and to allow the
            # state methods to advance the token after lookahead.

            while self._token_index < len(self._tokens):
                # I can't figure out why the following type check stopped working.
                self._state = self._state(self._tokens[self._token_index])  # type: ignore
                self._token_index += 1

        finally:
            # Free up a little memory, since there are a lot of these.
            self._tokens = None

        # Make sure the two dates are consistent with each other.

        self.validate()

        return self

    def normalize(self, raw_date_time: str) -> str:

        assert self.start_date is not None
        suffix: Optional[str] = None
        is_simple = raw_date_time == "" and (
            self.end_date is None or self.end_date == self.start_date
        )

        if not is_simple:
            match = self.SIMPLE_JAMES_DATE.match(raw_date_time)
            if match is not None:
                is_simple = True
                suffix = match.group(1)
            else:
                match = self.US_DATE_REGEX.match(raw_date_time)
                if match is not None:
                    is_simple = True

        if is_simple:
            assert self.start_date.month is not None
            assert self.start_date.day is not None
            return "%s%s" % (
                self._to_simple_date(self.start_date),
                "" if suffix is None else "/" + suffix,
            )

        if raw_date_time == "":
            assert self.end_date is not None
            if self.start_date.year == self.end_date.year:
                assert self.start_date.day is not None
                assert self.start_date.month is not None
                assert self.start_date.year is not None
                if self.start_date.month == self.end_date.month:
                    return "%d-%s" % (
                        self.start_date.day,
                        self._to_simple_date(self.end_date),
                    )
                else:
                    assert self.end_date.day is not None
                    assert self.end_date.month is not None
                    return "%d-%s-%d-%s-%d" % (
                        self.start_date.day,
                        DateToken.TO_ROMAN_MONTHS[self.start_date.month],
                        self.end_date.day,
                        DateToken.TO_ROMAN_MONTHS[self.end_date.month],
                        self.start_date.year,
                    )
            else:
                return "%s-%s" % (
                    self._to_simple_date(self.start_date),
                    self._to_simple_date(self.end_date),
                )

        assert self.start_date.year is not None
        return "%s (%d)" % (raw_date_time, self.start_date.year)

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, JamesDateTime):
            return NotImplemented
        return (
            other is not None
            and (
                self.start_date is other.start_date
                or self.start_date == other.start_date
            )
            and (self.end_date is other.end_date or self.end_date == other.end_date)
            and self.season == other.season
            and self.part_of_day == other.part_of_day
        )

    def _check_for_trailer(self, token: DateToken, context: str) -> _StateFunc:
        if token.type == DateToken.SEASON:
            if self.season is not None:
                raise ParseError("season multiply specified")
            self.season = token.value
            return self._state_end_of_date
        if token.type == DateToken.PART_OF_DAY:
            if self.part_of_day is not None:
                raise ParseError("part of day multiply specified")
            self.part_of_day = token.value
            return self._state_end_of_date
        if token.type == DateToken.TIME:
            if token.value > 2400:
                raise ParseError("start times > 24:00")
            if self.start_date is None:
                self.start_date = PartialDate()
            if self.start_date.hour is None:
                if token.value == 2400:
                    raise ParseError("start times >= 24:00")
                self.start_date.set_time(token.value)
                return self._state_end_of_date
            if self.end_date is None:
                self.end_date = self.start_date.clone_date()
            if self.end_date.hour is None:
                if token.value < 2400:
                    self.end_date.set_time(token.value)
                elif self.end_date.day is None:
                    raise ParseError("no day given to advance after midnight")
                else:
                    self.end_date.set_time(token.value - 2400)
                    self.end_date.day += 1
                return self._state_end_of_date
            raise ParseError("extra time specified")
        raise ParseError("invalid token '%s' %s" % (token.raw, context))

    def _state_year_or_month(self, token: DateToken) -> _StateFunc:
        if token.type == DateToken.DAY_OR_YEAR:
            next_token = self._lookahead(1)
            next_next_token = self._lookahead(2)
            if (
                next_token is None
                or next_token.type != DateToken.DAY_OR_YEAR
                or next_next_token is None
                or next_next_token.type != DateToken.DAY_OR_YEAR
            ):
                year = self._expand_james_year(token.value)
                self.start_date = PartialDate(year)
                return self._state_after_1st_year

            # Handle date of format dd-dd-dd, all digits.
            dd1 = token.value
            dd2 = next_token.value
            dd3 = next_next_token.value
            if dd1 == 0 or dd1 > 31:  # YY-**-**
                if 1 <= dd2 <= 12:  # YY-(MM|DD)-**
                    if 1 <= dd3 <= 12:  # YY-(MM|DD)-(MM|DD)
                        raise ParseError("ambiguous date")
                    elif 1 <= dd3 <= 31:  # YY-MM-DD
                        year = self._expand_james_year(dd1)
                        self.start_date = PartialDate(year, dd2, dd3)
                        self._token_index += 2
                    else:  # YY-(MM|DD)-YY
                        raise ParseError("cannot parse date")
                else:  # YY-DD-**
                    raise ParseError("apparent YY-DD-MM month format")
            elif dd1 > 12:  # (DD|YY)-**-**
                if 1 <= dd2 <= 12:  # (DD|YY)-(MM|DD)-**
                    if dd3 == 0 or dd3 > 31:  # if DD-MM-YY
                        year = self._expand_james_year(dd3)
                        self.start_date = PartialDate(year, dd2, dd1)
                        self._token_index += 2
                    else:  # (DD|YY)-(MM|DD)-(MM|DD)
                        raise ParseError("ambiguous date")
                elif 1 <= dd2 <= 31:  # (DD|YY)-(DD|YY)-**
                    raise ParseError("ambiguous date")
                else:  # DD-YY-**
                    raise ParseError("cannot parse date")
            else:  # (DD|YY|MM)-**-**
                if 12 < dd2 <= 31:  # (DD|YY|MM)-(YY|DD)-**
                    if dd3 == 0 or dd3 > 31:  # MM-DD-YY
                        year = self._expand_james_year(dd3)
                        self.start_date = PartialDate(year, dd1, dd2)
                        self._token_index += 2
                    else:
                        raise ParseError("ambiguous date")
                else:
                    raise ParseError("ambiguous date")
            return self._state_after_1st_day
        elif token.type == DateToken.MONTH:
            self.start_date = PartialDate(None, token.value)
            return self._state_after_1st_month
        raise ParseError("missing year")

    def _state_after_1st_year(self, token: DateToken) -> _StateFunc:
        assert self.start_date is not None  # make typechecker happy
        if token.type == DateToken.DAY_OR_YEAR:
            year = self._expand_james_year(token.value)
            self.end_date = PartialDate(year)
            return self._state_after_2nd_year
        if token.type == DateToken.PART_OF_MONTH:
            next_token = self._lookahead(1)
            if next_token is None:
                raise ParseError("Oops. Do I need to support parts of year?")
            if next_token.type == DateToken.MONTH:
                if self.start_date.part_of_month is not None:
                    raise ParseError("part of month multiply specified")
                self.start_date.part_of_month = token.value
                return self._state_after_1st_year
            raise ParseError("unexpected part of month '%s'" % token.value)
        if token.type == DateToken.MONTH:
            self.start_date.month = token.value
            return self._state_after_1st_month
        return self._check_for_trailer(token, "after year")

    def _state_after_1st_month(self, token: DateToken) -> _StateFunc:
        assert self.start_date is not None  # make typechecker happy
        if token.type == DateToken.PART_OF_MONTH:
            if self.start_date.part_of_month is not None:
                raise ParseError("part of month multiply specified")
            self.start_date.part_of_month = token.value
            return self._state_after_1st_month
        if token.type == DateToken.DAY_OR_YEAR:
            self.start_date.day = token.value
            return self._state_after_1st_day
        if token.type == DateToken.MONTH:
            self.end_date = self.start_date.clone_date()
            self.end_date.month = token.value
            return self._state_after_2nd_month
        return self._check_for_trailer(token, "after month")

    def _state_after_1st_day(self, token: DateToken) -> _StateFunc:
        assert self.start_date is not None  # make typechecker happy
        if token.type == DateToken.DAY_OR_YEAR:
            next_token = self._lookahead(1)
            if (
                next_token is not None and next_token.type == DateToken.MONTH
            ):  # 2nd month
                year = self._expand_james_year(token.value)
                self.end_date = PartialDate(year)  # 2nd year
                return self._state_after_2nd_year
            self.end_date = self.start_date.clone_date()
            self.end_date.day = token.value
            return self._state_end_of_date
        if token.type == DateToken.MONTH:
            self.end_date = self.start_date.clone_date()
            self.end_date.month = token.value  # 2nd month
            return self._state_after_2nd_month
        return self._check_for_trailer(token, "after day")

    def _state_after_2nd_year(self, token: DateToken) -> _StateFunc:
        assert self.end_date is not None  # make typechecker happy
        if token.type == DateToken.MONTH:
            self.end_date.month = token.value
            return self._state_after_2nd_month
        return self._check_for_trailer(token, "after 2nd year")

    def _state_after_2nd_month(self, token: DateToken) -> _StateFunc:
        assert self.end_date is not None  # make typechecker happy
        if token.type == DateToken.DAY_OR_YEAR:
            self.end_date.day = token.value
            return self._state_end_of_date
        return self._check_for_trailer(token, "after 2nd month")

    def _state_end_of_date(self, token: DateToken) -> _StateFunc:
        if token.type == DateToken.MONTH:
            assert self.end_date is not None  # make typechecker happy
            self.end_date.month = token.value
            self.end_date.day = None
            return self._state_after_2nd_month
        return self._check_for_trailer(token, "after date")

    def validate(self) -> None:

        start = self.start_date
        assert start is not None  # make typechecker happy
        start.validate("start")

        end = self.end_date
        if end is None:
            return
        end.validate("end")

        if start.year is not None:
            assert end.year is not None  # make typechecker happy
            if end.year < start.year:
                raise ParseError(
                    "ending %d year precedes starting year %d" % (end.year, start.year)
                )
            if end.year > start.year:
                return

        if end.month is not None:
            assert start.month is not None  # make typechecker happy
            if end.month < start.month:
                if end.year is None or not end.assumed_year:
                    raise ParseError(
                        "ending month %d precedes starting month %d "
                        % (end.month, start.month)
                    )
                end.year += 1
                return
            if end.month > start.month:
                return

        if end.day is not None:
            assert start.day is not None  # make typechecker happy
            if end.day < start.day:
                raise ParseError(
                    "ending day %d precedes starting day %d" % (end.day, start.day)
                )
            if end.day > start.day:
                return

        if end.hour is not None:
            assert start.hour is not None  # make typechecker happy
            assert start.minute is not None  # make typechecker happy
            assert end.minute is not None  # make typechecker happy
            if end.hour < start.hour:
                raise ParseError("ending hour precedes starting hour")
            if end.hour > start.hour:
                return
            if end.minute < start.minute:
                raise ParseError("ending minute precedes starting minute")

    def _lookahead(self, offset: int) -> Optional[DateToken]:
        assert self._tokens is not None  # make typechecker happy
        prospective_index = self._token_index + offset
        if prospective_index < len(self._tokens):
            return self._tokens[prospective_index]
        return None

    @staticmethod
    def _expand_james_year(year: int) -> int:
        return year + (2000 if year <= date.today().year % 100 else 1900)

    @staticmethod
    def _to_simple_date(date: PartialDate) -> str:
        assert date.month is not None
        assert date.day is not None
        return "%d-%s-%d" % (
            date.day,
            DateToken.TO_ROMAN_MONTHS[date.month],
            date.year,
        )
