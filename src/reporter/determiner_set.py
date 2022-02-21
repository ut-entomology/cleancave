from __future__ import annotations
from typing import Optional, TYPE_CHECKING
from datetime import date
import re

if TYPE_CHECKING:
    from src.reporter.specimen_record import SpecimenRecord
from src.lib.declared_names_table import DeclaredNamesTable
from src.lib.identity import Identity
from src.reporter.name_column_parser import NameColumnParser


class DeterminerSet:

    NUMBER_REGEX = re.compile(r"\d+")

    MONTH_TERMS = [
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
        "jan",
        "feb",
        "mar",
        "apr",
        "jun",
        "jul",
        "aug",
        "sep",
        "oct",
        "nov",
        "dec",
        "jan.",
        "feb.",
        "mar.",
        "apr.",
        "may.",
        "jun.",
        "jul.",
        "aug.",
        "sep.",
        "oct.",
        "nov.",
        "dec.",
    ]

    checked_record_ids = [
        2567,
        7637,
        9149,
        13706,
        13707,
        15689,
        17718,
        29644,
        42229,
        44724,
    ]

    def __init__(
        self,
        determiners: Optional[list[Identity]] = None,
        year: Optional[int] = None,
    ):
        self.determiners = determiners
        self.year = year

    def __str__(self) -> str:
        s = ""
        if self.determiners is not None:
            s += "; ".join([str(p) for p in self.determiners])
        if self.year is not None:
            s += "/%d" % self.year
        return s

    def load(
        self,
        declared_names_table: DeclaredNamesTable,
        record: SpecimenRecord,
        raw_text: str,
    ) -> DeterminerSet:

        raw_text = raw_text.strip()
        if raw_text == "":
            return self

        # Apply corrections that allow for parsing the year and don't require warnings.

        if raw_text[-1] == "/":
            if len(raw_text) == 1:
                return self
            raw_text = raw_text[0:-1]

        corrections = {
            "1j982": "1982",
            "/07/77": "/1977",
            "/;": "/",
            "; :": ";",
            "29008": "2008",
            "1006": "2006",
            "2986": "1986",
            "2989": "1989",
            "Shell1y": "Shelley",
        }
        for mistake, correction in corrections.items():
            raw_text = raw_text.replace(mistake, correction)

        # Extract the year, ignoring any indication of month.

        if raw_text[-1].isdigit():
            offset = len(raw_text) - 1
            while offset >= 0 and raw_text[offset].isdigit():
                offset -= 1
            digits = raw_text[offset + 1 :]
            year = int(digits)
            if year >= 1900 and year <= date.today().year:
                self.year = digits
                raw_text = raw_text[0 : offset + 1].strip().replace("/", ";")
                last_semicolon_offset = raw_text.rfind(";")
                if last_semicolon_offset != -1:
                    drop_last_term = False
                    if last_semicolon_offset == len(raw_text) - 1:
                        drop_last_term = True
                    else:
                        last_term = raw_text[last_semicolon_offset + 1 :].strip()
                        if last_term.lower() in self.MONTH_TERMS:
                            drop_last_term = True
                        else:
                            drop_last_term = True
                            for c in last_term.upper():
                                if not c.isdigit() and c not in "IVX- ":
                                    drop_last_term = False
                                    break
                    if drop_last_term:
                        raw_text = raw_text[0:last_semicolon_offset]

        numbers = self.NUMBER_REGEX.findall(raw_text)
        if numbers:
            record.add_problem(
                "unexpected number(s) %s in determiner" % str(numbers)[1:-1]
            )
        else:
            parser = NameColumnParser(raw_text, declared_names_table)
            self.determiners = parser.parse()
            record.save_problems(parser, "determiner")
        return self
