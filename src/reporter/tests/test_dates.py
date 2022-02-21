import pytest

from typing import Callable, Type

from src.lib.partial_date import PartialDate
from src.lib.parse_error import ParseError
from src.reporter.james_date_time import JamesDateTime


class TestDates:
    def test_simple_year(self):

        dt = parse_dt("79")
        assert dt == JamesDateTime(PartialDate(1979))
        dt = parse_dt("00")
        assert dt == JamesDateTime(PartialDate(2000))
        dt = parse_dt("01")
        assert dt == JamesDateTime(PartialDate(2001))
        dt = parse_dt("20")
        assert dt == JamesDateTime(PartialDate(2020))
        dt = parse_dt("21")
        assert dt == JamesDateTime(PartialDate(2021))

    def test_year_month(self):

        dt = parse_dt("79-I")
        assert dt == JamesDateTime(PartialDate(1979, 1))
        dt = parse_dt("79-V")
        assert dt == JamesDateTime(PartialDate(1979, 5))
        dt = parse_dt("01-XII")
        assert dt == JamesDateTime(PartialDate(2001, 12))

    def test_year_month_day(self):

        dt = parse_dt("79-IX-1")
        assert dt == JamesDateTime(PartialDate(1979, 9, 1))
        dt = parse_dt("79-IX-01")
        assert dt == JamesDateTime(PartialDate(1979, 9, 1))
        dt = parse_dt("79-IX-31")
        assert dt == JamesDateTime(PartialDate(1979, 9, 31))
        assert_raises(ParseError, lambda: parse_dt("79-II-0"))
        assert_raises(ParseError, lambda: parse_dt("79-II-32"))

    def test_year_year(self):

        dt = parse_dt("79-80")
        assert dt == JamesDateTime(
            PartialDate(1979),
            PartialDate(1980),
        )

        assert_raises(ParseError, lambda: parse_dt("80-79"))
        assert_raises(ParseError, lambda: parse_dt("20-80"))

    def test_year_month_month(self):

        dt = parse_dt("79-V-V")
        assert dt == JamesDateTime(
            PartialDate(1979, 5),
            PartialDate(1979, 5),
        )

        dt = parse_dt("79-I-II")
        assert dt == JamesDateTime(
            PartialDate(1979, 1),
            PartialDate(1979, 2),
        )

        dt = parse_dt("79-I,II")
        assert dt == JamesDateTime(
            PartialDate(1979, 1),
            PartialDate(1979, 2),
        )

        dt = parse_dt("79-I, II")
        assert dt == JamesDateTime(
            PartialDate(1979, 1),
            PartialDate(1979, 2),
        )

        dt = parse_dt("79-II-I")
        assert dt == JamesDateTime(
            PartialDate(1979, 2),
            PartialDate(1980, 1),
        )

    def test_year_month_day_day(self):

        dt = parse_dt("79-V-1-2")
        assert dt == JamesDateTime(
            PartialDate(1979, 5, 1),
            PartialDate(1979, 5, 2),
        )

        dt = parse_dt("79-V-12-22")
        assert dt == JamesDateTime(
            PartialDate(1979, 5, 12),
            PartialDate(1979, 5, 22),
        )

        assert_raises(ParseError, lambda: parse_dt("79-II-2-1"))
        assert_raises(ParseError, lambda: parse_dt("79-II-0-1"))
        assert_raises(ParseError, lambda: parse_dt("79-II-28-32"))

    def test_year_month_day_month_day(self):

        dt = parse_dt("18-XI-12-XI-12")
        assert dt == JamesDateTime(
            PartialDate(2018, 11, 12),
            PartialDate(2018, 11, 12),
        )

        dt = parse_dt("18-XI-12-XI-20")
        assert dt == JamesDateTime(
            PartialDate(2018, 11, 12),
            PartialDate(2018, 11, 20),
        )

        dt = parse_dt("18-XI-2-XII-20")
        assert dt == JamesDateTime(
            PartialDate(2018, 11, 2),
            PartialDate(2018, 12, 20),
        )

        dt = parse_dt("18-III-20-IV-2")
        assert dt == JamesDateTime(
            PartialDate(2018, 3, 20),
            PartialDate(2018, 4, 2),
        )

        dt = parse_dt("18-II-2-I-2")
        assert dt == JamesDateTime(
            PartialDate(2018, 2, 2),
            PartialDate(2019, 1, 2),
        )

        dt = parse_dt("18-II-2-I-1")
        assert dt == JamesDateTime(
            PartialDate(2018, 2, 2),
            PartialDate(2019, 1, 1),
        )

        assert_raises(ParseError, lambda: parse_dt("18-I-2-I-1"))

    def test_year_month_day_year_month_day(self):

        dt = parse_dt("18-XI-12,18-XI-12")
        assert dt == JamesDateTime(
            PartialDate(2018, 11, 12),
            PartialDate(2018, 11, 12),
        )

        dt = parse_dt("18-XI-12,18-XI-16")
        assert dt == JamesDateTime(
            PartialDate(2018, 11, 12),
            PartialDate(2018, 11, 16),
        )

        dt = parse_dt("18-XI-12,18-XII-1")
        assert dt == JamesDateTime(
            PartialDate(2018, 11, 12),
            PartialDate(2018, 12, 1),
        )

        dt = parse_dt("18-XII-31,19-I-1")
        assert dt == JamesDateTime(
            PartialDate(2018, 12, 31),
            PartialDate(2019, 1, 1),
        )

        assert_raises(ParseError, lambda: parse_dt("18-XI-12,17-XI-12"))
        assert_raises(ParseError, lambda: parse_dt("17-II-12,17-I-13"))
        assert_raises(ParseError, lambda: parse_dt("17-II-12,17-II-11"))

    def test_year_month_day_month_day_month_day(self):

        dt = parse_dt("07-VI-20, VI-28, VII-07")
        assert dt == JamesDateTime(
            PartialDate(2007, 6, 20),
            PartialDate(2007, 7, 7),
        )

        dt = parse_dt("18-I-2-II-3-III-4")
        assert dt == JamesDateTime(
            PartialDate(2018, 1, 2),
            PartialDate(2018, 3, 4),
        )

    def test_us_dates(self):

        dt = parse_dt("10/11/2018")
        assert dt == JamesDateTime(PartialDate(2018, 10, 11))

        dt = parse_dt("2/1/2018")
        assert dt == JamesDateTime(PartialDate(2018, 2, 1))

        dt = parse_dt("10/11/201810/11/2018")
        assert dt == JamesDateTime(PartialDate(2018, 10, 11))

        dt = parse_dt("2/1/20182/1/2018")
        assert dt == JamesDateTime(PartialDate(2018, 2, 1))

    def test_time(self):

        dt = parse_dt("80/0000")
        assert dt == JamesDateTime(PartialDate(1980, None, None, 0, 0))
        dt = parse_dt("80/0000-0100")
        assert dt == JamesDateTime(
            PartialDate(1980, None, None, 0, 0), PartialDate(1980, None, None, 1, 0)
        )

        dt = parse_dt("80/0800")
        assert dt == JamesDateTime(PartialDate(1980, None, None, 8, 0))
        dt = parse_dt("80/08:00")
        assert dt == JamesDateTime(PartialDate(1980, None, None, 8, 0))
        dt = parse_dt("80/0800-1200")
        assert dt == JamesDateTime(
            PartialDate(1980, None, None, 8, 0),
            PartialDate(1980, None, None, 12, 0),
        )

        dt = parse_dt("80/0800-12:00")
        assert dt == JamesDateTime(
            PartialDate(1980, None, None, 8, 0),
            PartialDate(1980, None, None, 12, 0),
        )

        dt = parse_dt("80/00:00-01:00")
        assert dt == JamesDateTime(
            PartialDate(1980, None, None, 0, 0), PartialDate(1980, None, None, 1, 0)
        )

        dt = parse_dt("80/1:00-2:30")
        assert dt == JamesDateTime(
            PartialDate(1980, None, None, 1, 0),
            PartialDate(1980, None, None, 2, 30),
        )

        dt = parse_dt("80/1800")
        assert dt == JamesDateTime(PartialDate(1980, None, None, 18, 0))
        dt = parse_dt("80/1800-2359")
        assert dt == JamesDateTime(
            PartialDate(1980, None, None, 18, 0),
            PartialDate(1980, None, None, 23, 59),
        )

        dt = parse_dt("80-X/1800")
        assert dt == JamesDateTime(PartialDate(1980, 10, None, 18, 0))
        dt = parse_dt("80-X/1800-1801")
        assert dt == JamesDateTime(
            PartialDate(1980, 10, None, 18, 0), PartialDate(1980, 10, None, 18, 1)
        )

        dt = parse_dt("80-X-5/1800")
        assert dt == JamesDateTime(PartialDate(1980, 10, 5, 18, 0))
        dt = parse_dt("80-X-5/1800-1900")
        assert dt == JamesDateTime(
            PartialDate(1980, 10, 5, 18, 0), PartialDate(1980, 10, 5, 19, 0)
        )

        dt = parse_dt("80-X-5/1800-1800")
        assert dt == JamesDateTime(
            PartialDate(1980, 10, 5, 18, 0), PartialDate(1980, 10, 5, 18, 0)
        )

        dt = parse_dt("80-X-5/1800-2400")
        assert dt == JamesDateTime(
            PartialDate(1980, 10, 5, 18, 0), PartialDate(1980, 10, 6, 0, 0)
        )

        dt = parse_dt("80-X-XI/1800")
        assert dt == JamesDateTime(
            PartialDate(1980, 10, None, 18, 0), PartialDate(1980, 11)
        )

        dt = parse_dt("80-X-XI/1800-2230")
        assert dt == JamesDateTime(
            PartialDate(1980, 10, None, 18, 0), PartialDate(1980, 11, None, 22, 30)
        )

        dt = parse_dt("80-X-5-XI-1/1800")
        assert dt == JamesDateTime(
            PartialDate(1980, 10, 5, 18, 0), PartialDate(1980, 11, 1)
        )

        dt = parse_dt("80-X-5-XI-1/1800-2230")
        assert dt == JamesDateTime(
            PartialDate(1980, 10, 5, 18, 0), PartialDate(1980, 11, 1, 22, 30)
        )

        dt = parse_dt("79-80/1800")
        assert dt == JamesDateTime(
            PartialDate(1979, None, None, 18, 0),
            PartialDate(1980),
        )

        dt = parse_dt("79-80/1800-2025")
        assert dt == JamesDateTime(
            PartialDate(1979, None, None, 18, 0),
            PartialDate(1980, None, None, 20, 25),
        )

        assert_raises(ParseError, lambda: parse_dt("79-80/1800-2400"))
        assert_raises(ParseError, lambda: parse_dt("18-I-1/2400"))
        assert_raises(ParseError, lambda: parse_dt("18-I-1/0060"))
        assert_raises(ParseError, lambda: parse_dt("18-I-1/1000-0959"))
        assert_raises(ParseError, lambda: parse_dt("18-I-1/1000-2260"))
        assert_raises(ParseError, lambda: parse_dt("18-I-1/1000-2265"))
        assert_raises(ParseError, lambda: parse_dt("18-I-1/1000-2500"))

    def test_excess_values(self):

        assert_raises(ParseError, lambda: parse_dt("18-19-20"))
        assert_raises(ParseError, lambda: parse_dt("18-I-2-2-2"))
        assert_raises(ParseError, lambda: parse_dt("18-I-I-II"))
        assert_raises(ParseError, lambda: parse_dt("18-I-II-III"))
        assert_raises(ParseError, lambda: parse_dt("18-I-2-II-3-4"))
        assert_raises(ParseError, lambda: parse_dt("18-I-2-II-3-4"))
        assert_raises(ParseError, lambda: parse_dt("18-I-1/1000-1100-1200"))

    def test_seasons(self):

        dt = parse_dt("69-spring")
        assert dt == JamesDateTime(PartialDate(1969), None, "spring")
        dt = parse_dt("69-summer")
        assert dt == JamesDateTime(PartialDate(1969), None, "summer")
        dt = parse_dt("69-fall")
        assert dt == JamesDateTime(PartialDate(1969), None, "fall")
        dt = parse_dt("69-winter")
        assert dt == JamesDateTime(PartialDate(1969), None, "winter")
        dt = parse_dt("69/Summer")
        assert dt == JamesDateTime(PartialDate(1969), None, "summer")
        dt = parse_dt("69/early summer")
        assert dt == JamesDateTime(PartialDate(1969), None, "early summer")
        dt = parse_dt("69/springtime")
        assert dt == JamesDateTime(PartialDate(1969), None, "springtime")
        dt = parse_dt("69-II/spring")
        assert dt == JamesDateTime(PartialDate(1969, 2), None, "spring")
        dt = parse_dt("69-II-5/spring")
        assert dt == JamesDateTime(PartialDate(1969, 2, 5), None, "spring")
        dt = parse_dt("79-80/spring")
        assert dt == JamesDateTime(PartialDate(1979), PartialDate(1980), "spring")

        dt = parse_dt("69-II-III/spring")
        assert dt == JamesDateTime(PartialDate(1969, 2), PartialDate(1969, 3), "spring")

        dt = parse_dt("69-II-28-III-2/spring")
        assert dt == JamesDateTime(
            PartialDate(1969, 2, 28), PartialDate(1969, 3, 2), "spring"
        )

        dt = parse_dt("69-II-28,69-III-2/spring")
        assert dt == JamesDateTime(
            PartialDate(1969, 2, 28), PartialDate(1969, 3, 2), "spring"
        )

        dt = parse_dt("69-II-5/1000/spring")
        assert dt == JamesDateTime(PartialDate(1969, 2, 5, 10, 0), None, "spring")

        dt = parse_dt("69-II-5/1000-1100/spring")
        assert dt == JamesDateTime(
            PartialDate(1969, 2, 5, 10, 0), PartialDate(1969, 2, 5, 11, 0), "spring"
        )

        dt = parse_dt("69-II-5/spring/1000-1100")
        assert dt == JamesDateTime(
            PartialDate(1969, 2, 5, 10, 0), PartialDate(1969, 2, 5, 11, 0), "spring"
        )

        assert_raises(ParseError, lambda: parse_dt("89/spring/spring"))
        assert_raises(ParseError, lambda: parse_dt("89/spring-spring"))

    def test_part_of_day(self):

        dt = parse_dt("69-morning")
        assert dt == JamesDateTime(PartialDate(1969), None, None, "morning")
        dt = parse_dt("69-Morning")
        assert dt == JamesDateTime(PartialDate(1969), None, None, "morning")
        dt = parse_dt("69-afternoon")
        assert dt == JamesDateTime(PartialDate(1969), None, None, "afternoon")
        dt = parse_dt("69-evening")
        assert dt == JamesDateTime(PartialDate(1969), None, None, "evening")
        dt = parse_dt("69-night")
        assert dt == JamesDateTime(PartialDate(1969), None, None, "night")
        dt = parse_dt("69-early morning")
        assert dt == JamesDateTime(PartialDate(1969), None, None, "early morning")

        dt = parse_dt("69-summer-afternoon")
        assert dt == JamesDateTime(PartialDate(1969), None, "summer", "afternoon")

        dt = parse_dt("69/morning-spring")
        assert dt == JamesDateTime(PartialDate(1969), None, "spring", "morning")

        dt = parse_dt("69-II/night")
        assert dt == JamesDateTime(PartialDate(1969, 2), None, None, "night")
        dt = parse_dt("69-II-5/night")
        assert dt == JamesDateTime(PartialDate(1969, 2, 5), None, None, "night")

        dt = parse_dt("79-80/night")
        assert dt == JamesDateTime(PartialDate(1979), PartialDate(1980), None, "night")

        dt = parse_dt("69-II-III/night")
        assert dt == JamesDateTime(
            PartialDate(1969, 2), PartialDate(1969, 3), None, "night"
        )

        dt = parse_dt("69-II-28-III-2/night")
        assert dt == JamesDateTime(
            PartialDate(1969, 2, 28), PartialDate(1969, 3, 2), None, "night"
        )

        dt = parse_dt("69-II-28,69-III-2/night")
        assert dt == JamesDateTime(
            PartialDate(1969, 2, 28), PartialDate(1969, 3, 2), None, "night"
        )

        dt = parse_dt("69-II-5/1000/night")
        assert dt == JamesDateTime(PartialDate(1969, 2, 5, 10, 0), None, None, "night")

        dt = parse_dt("69-II-5/1000/summer-night")
        assert dt == JamesDateTime(
            PartialDate(1969, 2, 5, 10, 0), None, "summer", "night"
        )

        dt = parse_dt("69-II-5/1000-1100/night")
        assert dt == JamesDateTime(
            PartialDate(1969, 2, 5, 10, 0),
            PartialDate(1969, 2, 5, 11, 0),
            None,
            "night",
        )

        dt = parse_dt("69-II-5/night/1000-1100")
        assert dt == JamesDateTime(
            PartialDate(1969, 2, 5, 10, 0),
            PartialDate(1969, 2, 5, 11, 0),
            None,
            "night",
        )

        dt = parse_dt("69-II-5/summer-night/1000-1100")
        assert dt == JamesDateTime(
            PartialDate(1969, 2, 5, 10, 0),
            PartialDate(1969, 2, 5, 11, 0),
            "summer",
            "night",
        )

        assert_raises(ParseError, lambda: parse_dt("89/night/night"))
        assert_raises(ParseError, lambda: parse_dt("89/night-night"))
        assert_raises(ParseError, lambda: parse_dt("89/night/summer/night"))

    def test_delimiters(self):

        dt = parse_dt("80-X-5,XI-1/1800")
        assert dt == JamesDateTime(
            PartialDate(1980, 10, 5, 18, 0), PartialDate(1980, 11, 1)
        )

        dt = parse_dt("80-X-5, XI-1/1800")
        assert dt == JamesDateTime(
            PartialDate(1980, 10, 5, 18, 0), PartialDate(1980, 11, 1)
        )

        dt = parse_dt("80-X-5,XI-1/1800-2230")
        assert dt == JamesDateTime(
            PartialDate(1980, 10, 5, 18, 0), PartialDate(1980, 11, 1, 22, 30)
        )

        dt = parse_dt("80-X-5, XI-1/1800-2230")
        assert dt == JamesDateTime(
            PartialDate(1980, 10, 5, 18, 0), PartialDate(1980, 11, 1, 22, 30)
        )

        dt = parse_dt("80-X-5, XI-1 / 1800-2230")
        assert dt == JamesDateTime(
            PartialDate(1980, 10, 5, 18, 0), PartialDate(1980, 11, 1, 22, 30)
        )

        dt = parse_dt("69-II-28, 69-III-2")
        assert dt == JamesDateTime(PartialDate(1969, 2, 28), PartialDate(1969, 3, 2))

        dt = parse_dt("69-II-28/69-III-2")
        assert dt == JamesDateTime(PartialDate(1969, 2, 28), PartialDate(1969, 3, 2))

        dt = parse_dt("69-II-28/69-III-2,night")
        assert dt == JamesDateTime(
            PartialDate(1969, 2, 28), PartialDate(1969, 3, 2), None, "night"
        )

    def test_month_first(self):

        dt = parse_dt("X")
        assert dt == JamesDateTime(PartialDate(None, 10))
        dt = parse_dt("I-2")
        assert dt == JamesDateTime(PartialDate(None, 1, 2))
        dt = parse_dt("V-10-12")
        assert dt == JamesDateTime(PartialDate(None, 5, 10), PartialDate(None, 5, 12))

        dt = parse_dt("V-10-VI-3")
        assert dt == JamesDateTime(PartialDate(None, 5, 10), PartialDate(None, 6, 3))

    def test_month_as_word(self):

        dt = parse_dt("02-january")
        assert dt == JamesDateTime(PartialDate(2002, 1))
        dt = parse_dt("69-january")
        assert dt == JamesDateTime(PartialDate(1969, 1))
        dt = parse_dt("69-January")
        assert dt == JamesDateTime(PartialDate(1969, 1))
        dt = parse_dt("69-december-11")
        assert dt == JamesDateTime(PartialDate(1969, 12, 11))

    def test_part_of_month(self):

        dt = parse_dt("69-II-early")
        assert dt == JamesDateTime(PartialDate(1969, 2, None, None, None, "early"))

        dt = parse_dt("69-II-Early")
        assert dt == JamesDateTime(PartialDate(1969, 2, None, None, None, "early"))

        dt = parse_dt("69-II-middle")
        assert dt == JamesDateTime(PartialDate(1969, 2, None, None, None, "middle"))

        dt = parse_dt("69-II-mid")
        assert dt == JamesDateTime(PartialDate(1969, 2, None, None, None, "middle"))

        dt = parse_dt("69-II-late")
        assert dt == JamesDateTime(PartialDate(1969, 2, None, None, None, "late"))

        dt = parse_dt("69-early-january")
        assert dt == JamesDateTime(PartialDate(1969, 1, None, None, None, "early"))

        dt = parse_dt("69-mid-december")
        assert dt == JamesDateTime(PartialDate(1969, 12, None, None, None, "middle"))

        dt = parse_dt("69/mid-december")
        assert dt == JamesDateTime(PartialDate(1969, 12, None, None, None, "middle"))

        dt = parse_dt("69-late-november")
        assert dt == JamesDateTime(PartialDate(1969, 11, None, None, None, "late"))

        assert_raises(ParseError, lambda: parse_dt("69-late"))
        assert_raises(ParseError, lambda: parse_dt("69-II-12-early"))
        assert_raises(ParseError, lambda: parse_dt("69-early-late"))

    def test_all_digit_dates(self):

        dt = parse_dt("32-01-13")
        print(dt)
        assert dt == JamesDateTime(PartialDate(1932, 1, 13))
        dt = parse_dt("01-13-32")
        assert dt == JamesDateTime(PartialDate(1932, 1, 13))
        dt = parse_dt("13-01-32")
        assert dt == JamesDateTime(PartialDate(1932, 1, 13))
        dt = parse_dt("99-12-31")
        assert dt == JamesDateTime(PartialDate(1999, 12, 31))
        dt = parse_dt("12-31-99")
        assert dt == JamesDateTime(PartialDate(1999, 12, 31))
        dt = parse_dt("31-12-99")
        assert dt == JamesDateTime(PartialDate(1999, 12, 31))
        dt = parse_dt("00-12-31")
        assert dt == JamesDateTime(PartialDate(2000, 12, 31))
        dt = parse_dt("12-31-00")
        assert dt == JamesDateTime(PartialDate(2000, 12, 31))
        dt = parse_dt("31-12-00")
        assert dt == JamesDateTime(PartialDate(2000, 12, 31))
        assert_raises(ParseError, lambda: parse_dt("32-13-01"))
        assert_raises(ParseError, lambda: parse_dt("01-01-01"))
        assert_raises(ParseError, lambda: parse_dt("12-12-12"))
        assert_raises(ParseError, lambda: parse_dt("12-12-89"))
        assert_raises(ParseError, lambda: parse_dt("89-12-12"))
        assert_raises(ParseError, lambda: parse_dt("12-89-12"))
        assert_raises(ParseError, lambda: parse_dt("31-12-31"))
        assert_raises(ParseError, lambda: parse_dt("31-31-12"))
        assert_raises(ParseError, lambda: parse_dt("12-31-31"))
        assert_raises(ParseError, lambda: parse_dt("31-31-31"))
        assert_raises(ParseError, lambda: parse_dt("89-89-89"))
        assert_raises(ParseError, lambda: parse_dt("00-00-00"))

    def test_no_year(self):
        assert_raises(ParseError, lambda: parse_dt("spring"))
        assert_raises(ParseError, lambda: parse_dt("1000"))
        assert_raises(ParseError, lambda: parse_dt("1000-1100"))

    def test_undelimited_date(self):

        dt = parse_dt("69II28")
        assert dt == JamesDateTime(PartialDate(1969, 2, 28))
        dt = parse_dt("69-II28")
        assert dt == JamesDateTime(PartialDate(1969, 2, 28))
        dt = parse_dt("69II-28")
        assert dt == JamesDateTime(PartialDate(1969, 2, 28))
        dt = parse_dt("80X1/0800")
        assert dt == JamesDateTime(PartialDate(1980, 10, 1, 8, 0))
        dt = parse_dt("80-X1/0800")
        assert dt == JamesDateTime(PartialDate(1980, 10, 1, 8, 0))
        dt = parse_dt("80X-1/0800")
        assert dt == JamesDateTime(PartialDate(1980, 10, 1, 8, 0))
        dt = parse_dt("69II5/spring")
        assert dt == JamesDateTime(PartialDate(1969, 2, 5), None, "spring")
        dt = parse_dt("69II5/night")
        assert dt == JamesDateTime(PartialDate(1969, 2, 5), None, None, "night")

    def test_consecutive_delimiters(self):
        assert_raises(ParseError, lambda: parse_dt("1,,"))
        assert_raises(ParseError, lambda: parse_dt("1,-"))
        assert_raises(ParseError, lambda: parse_dt("1-,"))
        assert_raises(ParseError, lambda: parse_dt("1-, "))
        assert_raises(ParseError, lambda: parse_dt("1- , "))
        assert_raises(ParseError, lambda: parse_dt("1 - , "))
        assert_raises(ParseError, lambda: parse_dt("1,,1"))
        assert_raises(ParseError, lambda: parse_dt("1, ,1"))
        assert_raises(ParseError, lambda: parse_dt("1,  ,1"))


def parse_dt(s: str) -> JamesDateTime:
    return JamesDateTime().load(s)


def assert_raises(
    exception_type: Type[Exception], test_func: Callable[[], JamesDateTime]
) -> None:
    with pytest.raises(exception_type):  # type: ignore
        test_func()
