from __future__ import annotations
from typing import Optional
from decimal import Decimal, InvalidOperation
import re


class LatLongRecord:

    MULTI_ID_LABEL = "ID/Cat No."

    def __init__(
        self,
        raw_id: str,
        raw_catalog_number: str,
        raw_latitude: str,
        raw_longitude: str,
    ):
        # Issues lists must come first to allow for logging issues.

        self._problems: Optional[list[str]] = None
        self._warnings: Optional[list[str]] = None
        self.remarks: list[str] = []

        # Load from raw data.

        self.id: int = int(raw_id)
        self.catalog_number = self._parse_catalog_number(raw_catalog_number)
        self.trust_latitude_precision = False
        self.latitude = self._parse_latitude(raw_latitude)
        self.trust_longitude_precision = False
        self.longitude = self._parse_longitude(raw_longitude)

    def add_problem(self, description: str) -> None:
        if self._problems is None:
            self._problems = [description]
        else:
            self._problems.append(description)

    def add_warning(self, description: str) -> None:
        if self._warnings is None:
            self._warnings = [description]
        else:
            self._warnings.append(description)

    def get_multi_id(self) -> str:
        cat_num = self.catalog_number
        cat_num_str = str(cat_num) if cat_num is not None else "NONE"
        return "%d/%s" % (self.id, cat_num_str)

    def print_all_problems(self) -> bool:
        if self._problems is None:
            return False
        self._print_issues(self._problems)
        return True

    def print_all_warnings(self) -> bool:
        if self._warnings is not None:
            self._print_issues(self._warnings)
            return True
        return False

    def _parse_catalog_number(self, s: str) -> Optional[int]:
        cat_num = self._parse_int("catalog number", s)
        if cat_num is None or cat_num < 1 or cat_num > 300000:
            self.add_problem("invalid catalog number '%s'" % s)
        return cat_num

    def _parse_int(self, field_name: str, s: str) -> Optional[int]:
        try:
            return int(s)
        except ValueError:
            self.add_problem("%s '%s' is not an integer" % (field_name, s))
            return None

    def _parse_int_or_0(self, field_name: str, s: str) -> Optional[int]:
        return self._parse_int(field_name, s if s != "" else "0")

    def _parse_latitude(self, s: str) -> Optional[Decimal]:
        if s == "":
            return None
        if (
            s[0] == "-"
            and s[-1].upper() == "S"
            or s[0] != "-"
            and s[-1].upper() == "N"
            or s[-1].upper() == "X"
            or s[-1] == "°"
        ):
            s = s[0:-1].strip()
            self.trust_latitude_precision = True
        latitude = self._parse_lat_long("latitude", s)
        if latitude is None:
            return None
        if latitude < -90 or latitude > 90:
            self.add_problem("latitude '%s' out of range" % s)
        return latitude

    def _parse_longitude(self, s: str) -> Optional[Decimal]:
        if s == "":
            if self.latitude is not None:
                self.add_problem("latitude specified but not also longitude")
            return None
        if (
            s[0] == "-"
            and s[-1].upper() == "W"
            or s[0] != "-"
            and s[-1].upper() == "E"
            or s[-1].upper() == "X"
            or s[-1] == "°"
        ):
            s = s[0:-1].strip()
            self.trust_longitude_precision = True
        longitude = self._parse_lat_long("longitude", s)
        if longitude is None:
            return None
        if longitude < -180 or longitude > 180:
            self.add_problem("longitude '%s' out of range" % s)
        if self.latitude is None:
            self.add_problem("longitude specified but not also latitude")
        return longitude

    def _parse_lat_long(self, field_name: str, s: str) -> Optional[Decimal]:
        original_s = s
        if s.startswith(", -"):
            s = s[2:]
        s = (
            s.replace(", ", ".")
            .replace(",", ".")
            .replace("):", "")
            .replace("'", "")
            .replace("--", "-")
        )
        if s.endswith("."):
            s = s[0:-1]
        offset = s.find("\n")
        if offset > 0 and "." in s[0:offset]:
            s = s[0:offset]
        offset = s.find(" ")
        if offset > 0 and "." in s[offset:]:
            s = s[offset + 1 :]
        try:
            # Sometimes the float repeated back-to-back.
            offset = s.find(".")
            assert offset >= 0
            dec = s[0 : offset + 1]
            offset = s[offset + 1 :].find(dec)
            if offset > 0:
                s = s[0 : offset + len(dec)]
            assert s.find(".") == s.rfind(".")
            if s != original_s:
                self.remarks.append("lat/long: [%s]" % original_s)
            return Decimal(s)
        except (AssertionError, InvalidOperation):
            self.add_problem("%s '%s' is not a valid decimal" % (field_name, s))
            return None

    def _parse_non_empty(self, field_name: str, s: str) -> Optional[str]:
        if s == "":
            self.add_problem("%s is empty" % field_name)
            return None
        return s

    @staticmethod
    def _parse_str_or_none(s: str) -> Optional[str]:
        if s == "":
            return None
        offset = s.find("\n")
        if offset >= 0:
            s = s[0:offset]
        return re.sub(r"[\t ]+", " ", s)

    def _print_issues(self, issues: list[str]) -> None:
        multi_id = self.get_multi_id()
        print("* %s %s: %s" % (self.MULTI_ID_LABEL, multi_id, "; ".join(issues)))
