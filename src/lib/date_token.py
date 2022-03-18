from typing import Any, Optional

import re

from src.lib.parse_error import ParseError


class DateToken:
    """Class Representing a date/time token"""

    DELIM_CHARS = "-/,= "
    COLON_TIME = re.compile(r"^\d\d?:\d\d$")

    DAY_OR_YEAR = 1
    MONTH = 2
    SEASON = 3
    TIME = 4
    PART_OF_MONTH = 5
    PART_OF_DAY = 6

    FROM_ROMAN_MONTHS = {
        "I": 1,
        "II": 2,
        "III": 3,
        "IV": 4,
        "V": 5,
        "VI": 6,
        "VII": 7,
        "VIII": 8,
        "IX": 9,
        "X": 10,
        "XI": 11,
        "XII": 12,
    }

    TO_ROMAN_MONTHS = {
        1: "I",
        2: "II",
        3: "III",
        4: "IV",
        5: "V",
        6: "VI",
        7: "VII",
        8: "VIII",
        9: "IX",
        10: "X",
        11: "XI",
        12: "XII",
    }

    SEASONS = ["spring", "summer", "winter", "fall", "easter", "christmas"]

    MONTHS = [
        "january",
        "february",
        "march",
        "april",
        "may",
        "june",
        "july",
        "august",
        "september",
        "october",
        "november",
        "december",
    ]

    PARTS_OF_MONTH = ["early", "middle", "mid", "late"]

    PARTS_OF_DAY = [
        "morning",
        "afternoon",
        "evening",
        "night",
        "dusk",
        "daylight",
        "a.m.",
        "p.m.",
        "day",
    ]

    def __init__(self, token: str):
        self.type: Optional[int] = None
        self.value: Any = token
        self.raw: str = token

        if token.isdigit():
            if len(token) <= 2:
                self.type = self.DAY_OR_YEAR
            elif len(token) == 4:
                self.type = self.TIME
            else:
                raise ParseError("unexpected integer '%s'" % token)
            self.value = int(token)
            return
        roman_value = self.from_roman(token)
        if roman_value is not None:
            self.type = self.MONTH
            self.value = roman_value
            return
        if self.COLON_TIME.match(token) is not None:
            self.type = self.TIME
            colon_offset = token.find(":")
            self.value = int(token[0:colon_offset] + token[colon_offset + 1 :])
            return
        for month in self.MONTHS:
            if month == token.lower():
                self.type = self.MONTH
                self.value = self.MONTHS.index(month) + 1
                return
        for season in self.SEASONS:
            if season in token.lower():
                self.type = self.SEASON
                self.value = token.lower()
                return
        for part_of_day in self.PARTS_OF_DAY:
            if part_of_day in token.lower():
                self.type = self.PART_OF_DAY
                self.value = token.lower()
                return
        # Do this test last to give precedence to prior possibilities.
        for part_of_month in self.PARTS_OF_MONTH:
            if part_of_month in token.lower():
                self.type = self.PART_OF_MONTH
                if part_of_month == "mid":
                    self.value = "middle"
                else:
                    self.value = token.lower()
                return
        raise ParseError("unrecognized token '%s'" % token)

    @classmethod
    def from_roman(cls, roman: str) -> Optional[int]:
        roman = roman.upper()
        if roman in cls.FROM_ROMAN_MONTHS:
            return cls.FROM_ROMAN_MONTHS[roman]
        return None

    @classmethod
    def is_delimeter(cls, token: str) -> bool:
        return token[0] in cls.DELIM_CHARS

    @classmethod
    def to_roman(cls, value: int) -> Optional[str]:
        for r, v in cls.FROM_ROMAN_MONTHS.items():
            if v == value:
                return r
        return None
