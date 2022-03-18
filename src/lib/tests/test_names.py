import pytest
from typing import Optional

from src.lib.identity import Identity
from src.lib.identity_parser import IdentityParser
from src.lib.parse_error import ParseError
from src.lib.declared_names_table import DeclaredNamesTable


class TestNames:
    declared_names = [
        "Smith, George",
        "Porter, Ralph",
        "Bigly-Boo, John-Paul",
        "Lessig, Lessig",
    ]
    declared_names_table = DeclaredNamesTable()

    @classmethod
    def setup_class(cls):
        for name in cls.declared_names:
            cls.declared_names_table.add_correct_name_line(name)

    def test_first_name_first(self):
        # Test undeclared first and last names, first name first.

        _test("James Reddell", [_identity("Reddell", "James")])
        _test("J Reddell", [_identity("Reddell", "J.")])
        _test("J. Reddell", [_identity("Reddell", "J.")])
        _test("J.   Reddell", [_identity("Reddell", "J.")])
        _test("J.Reddell", [_identity("Reddell", "J.")])
        _test("J.R. Reddell", [_identity("Reddell", "J. R.")])
        _test("J.R.Reddell", [_identity("Reddell", "J. R.")])
        _test("James R. Reddell", [_identity("Reddell", "James R.")])
        _test("Jessy Joe Jack", [_identity("Jack", "Jessy Joe")])
        _test("Fred Horner Jr", [_identity("Horner", "Fred", "Jr.")])
        _test("Fred Horner Jr.", [_identity("Horner", "Fred", "Jr.")])
        _test("Fred Horner, Jr", [_identity("Horner", "Fred", "Jr.")])
        _test("Fred Horner, Jr.", [_identity("Horner", "Fred", "Jr.")])
        _test("Fred Horner,Jr", [_identity("Horner", "Fred", "Jr.")])
        _test("Fred Horner ,Jr", [_identity("Horner", "Fred", "Jr.")])
        _test("Fred Horner,Jr.", [_identity("Horner", "Fred", "Jr.")])
        _test("F. Horner, Jr.", [_identity("Horner", "F.", "Jr.")])
        _test("F.  Horner,  Jr.", [_identity("Horner", "F.", "Jr.")])
        _test("F. Horner II", [_identity("Horner", "F.", "II")])
        _test("F. Horner, II", [_identity("Horner", "F.", "II")])
        _test("F. Horner III", [_identity("Horner", "F.", "III")])
        _test("F. Horner, III", [_identity("Horner", "F.", "III")])
        _test("John Sibley-Harley", [_identity("Sibley-Harley", "John")])
        _test("J Sibley-Harley", [_identity("Sibley-Harley", "J.")])
        _test("J Sibley-Harley, Jr.", [_identity("Sibley-Harley", "J.", "Jr.")])
        _test("Mary-Sue Wang", [_identity("Wang", "Mary-Sue")])
        _test("Mary- Sue Wang", [_identity("Wang", "Mary-Sue")])
        _test("Mary -Sue Wang", [_identity("Wang", "Mary-Sue")])
        _test("Mary - Sue Wang", [_identity("Wang", "Mary-Sue")])
        _test("Mary-Sue X. Wang", [_identity("Wang", "Mary-Sue X.")])

        # Test declared first names first in unambiguous circumstances.

        _test("George Reddell", [_identity("Reddell", "George")])
        _test("Ralph R. Reddell", [_identity("Reddell", "Ralph R.")])
        _test("George Joe Jack", [_identity("Jack", "George Joe")])
        _test("John-Paul Sibley-Harley", [_identity("Sibley-Harley", "John-Paul")])
        _test("Ralph Sibley-Harley", [_identity("Sibley-Harley", "Ralph")])
        _test("Ralph Sibley-Harley, Jr.", [_identity("Sibley-Harley", "Ralph", "Jr.")])
        _test("John-Paul Wang", [_identity("Wang", "John-Paul")])
        _test("John-Paul X. Wang", [_identity("Wang", "John-Paul X.")])

        # Test ill-specified first names.

        with pytest.raises(ParseError):  # type: ignore
            _parse("Fred Horner, Jr, Jr.")
        with pytest.raises(ParseError):  # type: ignore
            _parse("Fred Horner Jr, Jr.")
        with pytest.raises(ParseError):  # type: ignore
            _parse("Fred Horner Jr. Jr")
        with pytest.raises(ParseError):  # type: ignore
            _parse("Fred Horner Jr, Jr. Jr")
        with pytest.raises(ParseError):  # type: ignore
            _parse("Fred Horner Jr, Jr., Jr")

    def test_last_name_first(self):
        # Test undeclared first and last names, last name first, without suffix.

        _test("Reddell", [_identity("Reddell")])
        _test("Reddell, James", [_identity("Reddell", "James")])
        _test("Reddell,  James", [_identity("Reddell", "James")])
        _test("Reddell,James", [_identity("Reddell", "James")])
        _test("Reddell ,James", [_identity("Reddell", "James")])
        _test("Reddell, J.", [_identity("Reddell", "J.")])
        _test("Reddell, J", [_identity("Reddell", "J.")])
        _test("Reddell,  J", [_identity("Reddell", "J.")])
        _test("Reddell, J. R.", [_identity("Reddell", "J. R.")])
        _test("Reddell, J R", [_identity("Reddell", "J. R.")])
        _test("Reddell, J.R.", [_identity("Reddell", "J. R.")])
        _test("Reddell, James R.", [_identity("Reddell", "James R.")])
        _test("Reddell, James Robby", [_identity("Reddell", "James Robby")])
        _test("Reddell, J. Robby", [_identity("Reddell", "J. Robby")])
        _test("Reddell, Wm.Robby", [_identity("Reddell", "Wm. Robby")])
        _test("Reddell, J. R. R.", [_identity("Reddell", "J. R. R.")])
        _test("Reddell, J.R.R.", [_identity("Reddell", "J. R. R.")])
        _test("Sibley-Harley", [_identity("Sibley-Harley")])
        _test("Sibley - Harley", [_identity("Sibley-Harley")])
        _test("Sibley -Harley", [_identity("Sibley-Harley")])
        _test("Sibley- Harley", [_identity("Sibley-Harley")])
        _test("Sibley-Harley, John", [_identity("Sibley-Harley", "John")])

        # Test undeclared first and/or last names, last name first, with suffix.

        _test("Horner Jr", [_identity("Horner", None, "Jr.")])
        _test("Horner jr", [_identity("Horner", None, "Jr.")])
        _test("Horner JR", [_identity("Horner", None, "Jr.")])
        _test("Horner Jr.", [_identity("Horner", None, "Jr.")])
        _test("Horner, Jr", [_identity("Horner", None, "Jr.")])
        _test("Horner, Jr.", [_identity("Horner", None, "Jr.")])
        _test("Horner, Fred Jr.", [_identity("Horner", "Fred", "Jr.")])
        _test("Horner, Fred Jr", [_identity("Horner", "Fred", "Jr.")])
        _test("Horner, Fred, Jr", [_identity("Horner", "Fred", "Jr.")])
        _test("Horner, Fred, Jr.", [_identity("Horner", "Fred", "Jr.")])
        _test("Horner Sr", [_identity("Horner", None, "Sr.")])
        _test("Horner sr", [_identity("Horner", None, "Sr.")])
        _test("Horner SR", [_identity("Horner", None, "Sr.")])
        _test("Horner Sr.", [_identity("Horner", None, "Sr.")])

        # Test undeclared first and declared last names, last name first.

        _test("Porter", [_identity("Porter")])
        _test("Porter, James", [_identity("Porter", "James")])
        _test("Bigly-Boo", [_identity("Bigly-Boo")])
        _test("Bigly-Boo, John", [_identity("Bigly-Boo", "John")])

        # Test ill-specified suffixes.

        with pytest.raises(ParseError):  # type: ignore
            _parse("Horner, Jr., Jr")
        with pytest.raises(ParseError):  # type: ignore
            _parse("Horner Jr., Jr.")
        with pytest.raises(ParseError):  # type: ignore
            _parse("Horner Jr. Jr")
        with pytest.raises(ParseError):  # type: ignore
            _parse("Horner, F., Jr Jr.")
        with pytest.raises(ParseError):  # type: ignore
            _parse("Horner, F. Jr Jr.")
        with pytest.raises(ParseError):  # type: ignore
            _parse("Horner, F., Jr, Jr.")
        with pytest.raises(ParseError):  # type: ignore
            _parse("Horner, F. Jr, Jr.")

    def test_unambiguous_name_lists(self):
        # Test lists of entirely undeclared, unambiguous names.

        _test(
            "J. Reddell, F. Johnson",
            [_identity("Reddell", "J."), _identity("Johnson", "F.")],
        )
        _test(
            "J. R. Reddell, Fred Johnson",
            [_identity("Reddell", "J. R."), _identity("Johnson", "Fred")],
        )
        _test(
            "J. R. Reddell, Jr., Fred Johnson",
            [_identity("Reddell", "J. R.", "Jr."), _identity("Johnson", "Fred")],
        )
        _test(
            "J. R. Reddell, Jr., Johnson, F.",
            [_identity("Reddell", "J. R.", "Jr."), _identity("Johnson", "F.")],
        )
        _test(
            "Reddell, J., Johnson, F.",
            [_identity("Reddell", "J."), _identity("Johnson", "F.")],
        )
        _test(
            "Reddell, J.R., Johnson, F. X.",
            [_identity("Reddell", "J. R."), _identity("Johnson", "F. X.")],
        )
        _test(
            "Reddell, J.R., Johnson, F. X., Jr",
            [_identity("Reddell", "J. R."), _identity("Johnson", "F. X.", "Jr.")],
        )
        _test(
            "Johnson, Jr., Susan Hancock",
            [_identity("Johnson", None, "Jr."), _identity("Hancock", "Susan")],
        )
        _test(
            "Johnson Jr, Hancock, S.",
            [_identity("Johnson", None, "Jr."), _identity("Hancock", "S.")],
        )
        _test(
            "J. R. Reddell, Fred Johnson, Susan X. Hancock",
            [
                _identity("Reddell", "J. R."),
                _identity("Johnson", "Fred"),
                _identity("Hancock", "Susan X."),
            ],
        )
        _test(
            "J. R. Reddell, Johnson, F., Susan X. Hancock",
            [
                _identity("Reddell", "J. R."),
                _identity("Johnson", "F."),
                _identity("Hancock", "Susan X."),
            ],
        )
        _test(
            "Reddell, J.R., Johnson, F., Hancock, S. X.",
            [
                _identity("Reddell", "J. R."),
                _identity("Johnson", "F."),
                _identity("Hancock", "S. X."),
            ],
        )
        _test(
            "Reddell, J.R., Fred Johnson, Jr., Hancock, S. X.",
            [
                _identity("Reddell", "J. R."),
                _identity("Johnson", "Fred", "Jr."),
                _identity("Hancock", "S. X."),
            ],
        )

        # Test lists of declared last names in unambiguous names.

        _test("Smith, Porter", [_identity("Smith"), _identity("Porter")])
        _test(
            "J. Smith, F. Johnson",
            [_identity("Smith", "J."), _identity("Johnson", "F.")],
        )
        _test(
            "J. R. Reddell, Fred Smith",
            [_identity("Reddell", "J. R."), _identity("Smith", "Fred")],
        )
        _test(
            "Porter, J., Porter, F.",
            [_identity("Porter", "J."), _identity("Porter", "F.")],
        )
        _test(
            "Smith, Jr., Susan Porter",
            [_identity("Smith", None, "Jr."), _identity("Porter", "Susan")],
        )
        _test(
            "J. R. Smith, Fred Porter, Susan X. Bigly-Boo",
            [
                _identity("Smith", "J. R."),
                _identity("Porter", "Fred"),
                _identity("Bigly-Boo", "Susan X."),
            ],
        )
        _test(
            "J. R. Smith, Porter, F., Susan X. Bigly-Boo",
            [
                _identity("Smith", "J. R."),
                _identity("Porter", "F."),
                _identity("Bigly-Boo", "Susan X."),
            ],
        )
        _test(
            "Smith, J.R., Porter, F., Bigly-Boo, S. X.",
            [
                _identity("Smith", "J. R."),
                _identity("Porter", "F."),
                _identity("Bigly-Boo", "S. X."),
            ],
        )
        _test(
            "Smith, J.R., Fred Porter, Jr., Bigly-Boo, S. X.",
            [
                _identity("Smith", "J. R."),
                _identity("Porter", "Fred", "Jr."),
                _identity("Bigly-Boo", "S. X."),
            ],
        )

        # Test lists of declared first names in unambiguous names.

        _test(
            "George Reddell, Ralph Johnson",
            [_identity("Reddell", "George"), _identity("Johnson", "Ralph")],
        )
        _test(
            "George R. Reddell, Jr., Johnson, F.",
            [_identity("Reddell", "George R.", "Jr."), _identity("Johnson", "F.")],
        )
        _test(
            "Reddell, George, Johnson, Ralph",
            [_identity("Reddell", "George"), _identity("Johnson", "Ralph")],
        )
        _test(
            "Johnson, Jr., John-Paul Hancock",
            [_identity("Johnson", None, "Jr."), _identity("Hancock", "John-Paul")],
        )
        _test(
            "J. R. Reddell, Ralph Johnson, John-Paul X. Hancock",
            [
                _identity("Reddell", "J. R."),
                _identity("Johnson", "Ralph"),
                _identity("Hancock", "John-Paul X."),
            ],
        )
        _test(
            "George R. Reddell, Johnson, F., John-Paul X. Hancock",
            [
                _identity("Reddell", "George R."),
                _identity("Johnson", "F."),
                _identity("Hancock", "John-Paul X."),
            ],
        )
        _test(
            "Reddell, George, Johnson, Ralph, Hancock, John-Paul X.",
            [
                _identity("Reddell", "George"),
                _identity("Johnson", "Ralph"),
                _identity("Hancock", "John-Paul X."),
            ],
        )
        _test(
            "Reddell, J.R., Ralph Johnson, Jr., Hancock, John-Paul X.",
            [
                _identity("Reddell", "J. R."),
                _identity("Johnson", "Ralph", "Jr."),
                _identity("Hancock", "John-Paul X."),
            ],
        )

    def test_ambiguous_name_lists(self):
        # Relies on the declared first and last names given at the top of the class.

        _test("Jack, Jimmy", [_identity("Jack", "Jimmy")])
        _test("Jack, George", [_identity("Jack", "George")])
        _test("Jack, Smith", [_identity("Jack"), _identity("Smith")])
        _test("Porter, Jimmy", [_identity("Porter", "Jimmy")])
        _test("Porter, George", [_identity("Porter", "George")])
        _test("Porter, Smith", [_identity("Porter"), _identity("Smith")])
        _test("Jack, Jimmy, Jr.", [_identity("Jack", "Jimmy", "Jr.")])
        _test("Jack, George, Jr.", [_identity("Jack", "George", "Jr.")])
        _test("Jack, Smith, Jr.", [_identity("Jack"), _identity("Smith", None, "Jr.")])
        _test("Jack, Jr., Jimmy", [_identity("Jack", None, "Jr."), _identity("Jimmy")])
        _test("Black, Porter, S.", [_identity("Black"), _identity("Porter", "S.")])
        _test(
            "Black, Porter, Smith",
            [_identity("Black"), _identity("Porter"), _identity("Smith")],
        )
        _test("Black, Stan, Smith", [_identity("Black", "Stan"), _identity("Smith")])
        _test(
            "Black, Lessig, Smith", [_identity("Black", "Lessig"), _identity("Smith")]
        )
        _test(
            "Black, Porter, Lessig", [_identity("Black"), _identity("Porter", "Lessig")]
        )
        _test("Lessig, Stan, Smith", [_identity("Lessig", "Stan"), _identity("Smith")])
        _test(
            "Lessig, Porter, Smith",
            [_identity("Lessig"), _identity("Porter"), _identity("Smith")],
        )
        _test("Lessig, Jack, Smith", [_identity("Lessig", "Jack"), _identity("Smith")])
        _test("Smith, Stan, Black", [_identity("Smith", "Stan"), _identity("Black")])
        _test(
            "Smith, Lessig, Black", [_identity("Smith", "Lessig"), _identity("Black")]
        )
        _test(
            "Black, Porter X., Smith",
            [_identity("Black", "Porter X."), _identity("Smith")],
        )
        _test(
            "Black, Porter Jr., Smith",
            [_identity("Black"), _identity("Porter", None, "Jr."), _identity("Smith")],
        )
        _test(
            "Black, Porter X. Jr., Smith",
            [_identity("Black", "Porter X.", "Jr."), _identity("Smith")],
        )
        _test("Lessig Black", [_identity("Black", "Lessig")])
        _test(
            "Jimmy John, Lessig Black",
            [_identity("John", "Jimmy"), _identity("Black", "Lessig")],
        )

    def test_case_normalization(self):
        _test("joe lapp", [_identity("Lapp", "Joe")])
        _test("j. t. Lapp", [_identity("Lapp", "J. T.")])
        _test("deSantis, mary-sue", [_identity("deSantis", "Mary-Sue")])
        _test("DeSantis, mary-Sue", [_identity("DeSantis", "Mary-Sue")])
        _test("desantis, Mary-Sue j", [_identity("Desantis", "Mary-Sue J.")])
        _test("porter-smith, fred", [_identity("Porter-Smith", "Fred")])
        _test("smith-deSantis, fred", [_identity("Smith-deSantis", "Fred")])
        _test("Black, jr", [_identity("Black", None, "Jr.")])
        _test("black, jimmy, jr.", [_identity("Black", "Jimmy", "Jr.")])

    def test_compact_initials(self):
        _test("JD. Powers", [_identity("Powers", "J. D.")])
        _test("Powers, JD.", [_identity("Powers", "J. D.")])
        _test("Powers, JD", [_identity("Powers", "JD")])

    def test_acronyms(self):
        _test("ABC", [_identity("ABC")])
        _test("ABC, Fred", [_identity("ABC"), _identity("Fred")])
        _test("ABCD, Fred", [_identity("ABCD"), _identity("Fred")])
        _test("ABC, XY", [_identity("ABC"), _identity("XY")])
        _test(
            "F. Toad, ABC, Fred",
            [_identity("Toad", "F."), _identity("ABC"), _identity("Fred")],
        )
        _test("ABC, DEF", [_identity("ABC"), _identity("DEF")])
        _test("F. ABC", [_identity("ABC", "F.")])

    def test_ill_formed_names(self):

        with pytest.raises(ParseError):  # type: ignore
            _parse("")
        with pytest.raises(ParseError):  # type: ignore
            _parse(",")
        with pytest.raises(ParseError):  # type: ignore
            _parse("Jack--Black")
        with pytest.raises(ParseError):  # type: ignore
            _parse("-Jack")
        with pytest.raises(ParseError):  # type: ignore
            _parse(".")
        with pytest.raises(ParseError):  # type: ignore
            _parse("S.. Black")
        with pytest.raises(ParseError):  # type: ignore
            _parse("S . Black")
        with pytest.raises(ParseError):  # type: ignore
            _parse("George, Ralph, Jr..")
        with pytest.raises(ParseError):  # type: ignore
            _parse("Jr. Jack")

    def test_exact_raw_text(self):

        _test_raw("Johnson", ["Johnson"])
        _test_raw("Fred Johnson", ["Fred Johnson"])
        _test_raw("F. Johnson", ["F. Johnson"])
        _test_raw("F. G. Johnson", ["F. G. Johnson"])
        _test_raw("F. G. Johnson Jr.", ["F. G. Johnson Jr."])
        _test_raw("F. G. Johnson, Jr.", ["F. G. Johnson, Jr."])

        _test_raw("Johnson, Fred", ["Johnson, Fred"])
        _test_raw("Johnson, F.", ["Johnson, F."])
        _test_raw("Johnson, F. G.", ["Johnson, F. G."])
        _test_raw("Johnson, F. G., Jr.", ["Johnson, F. G., Jr."])

        _test_raw("Fred Johnson, Jack Black", ["Fred Johnson", "Jack Black"])
        _test_raw("F. Johnson, J. Black", ["F. Johnson", "J. Black"])
        _test_raw("F. Johnson, Jr, J. Black", ["F. Johnson, Jr", "J. Black"])
        _test_raw("F. Johnson, Black, Jack", ["F. Johnson", "Black, Jack"])
        _test_raw("Johnson, F., Black, Jack", ["Johnson, F.", "Black, Jack"])

        _test_raw("Smith, Porter", ["Smith", "Porter"])
        _test_raw("Smith, L., Porter", ["Smith, L.", "Porter"])
        _test_raw("Smith, Johnson", ["Smith, Johnson"])
        _test_raw("Smith, L., Johnson", ["Smith, L.", "Johnson"])

    def test_normalized_raw_text(self):

        _test_raw("F.  Johnson", ["F. Johnson"])
        _test_raw("F.  G. Johnson", ["F. G. Johnson"])
        _test_raw("Johnson,  F.G.", ["Johnson, F. G."])
        _test_raw("Johnson, F. G.,  Jr.", ["Johnson, F. G., Jr."])

        _test_raw("F.Johnson", ["F. Johnson"])
        _test_raw("F.G. Johnson", ["F. G. Johnson"])
        _test_raw("F.G.Johnson Jr.", ["F. G. Johnson Jr."])
        _test_raw("F. G. Johnson,Jr.", ["F. G. Johnson, Jr."])

        _test_raw("Johnson,Fred", ["Johnson, Fred"])
        _test_raw("Johnson,F.", ["Johnson, F."])
        _test_raw("Johnson, F.G.", ["Johnson, F. G."])
        _test_raw("Johnson, F. G.,Jr.", ["Johnson, F. G., Jr."])

        _test_raw("Fred Johnson,Jack Black", ["Fred Johnson", "Jack Black"])
        _test_raw("F. Johnson,J. Black", ["F. Johnson", "J. Black"])
        _test_raw("F. Johnson, Jr,J. Black", ["F. Johnson, Jr", "J. Black"])
        _test_raw("F. Johnson, Black,Jack", ["F. Johnson", "Black, Jack"])
        _test_raw("Johnson,F., Black,Jack", ["Johnson, F.", "Black, Jack"])


def _parse(text: str):
    return IdentityParser(text, True, TestNames.declared_names_table).parse()


def _identity(
    last_name: str,
    initial_names: Optional[str] = None,
    name_suffix: Optional[str] = None,
) -> Identity:
    return Identity(last_name, initial_names, name_suffix)


def _test(text: str, expected_identities: list[Identity]) -> None:
    actual_identities = _parse(text)
    assert actual_identities is not None
    assert len(actual_identities) == len(expected_identities)
    for i in range(len(actual_identities)):
        assert actual_identities[i] == expected_identities[i]


def _test_raw(text: str, expected_raw_names: list[str]) -> None:
    actual_identities = _parse(text)
    assert actual_identities is not None
    assert len(actual_identities) == len(expected_raw_names)
    for i in range(len(actual_identities)):
        assert actual_identities[i]._raw_names == expected_raw_names[i]  # type: ignore
