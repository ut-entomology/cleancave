import pytest
import textwrap
from typing import Any, Callable, Optional, Type

from src.lib.parse_error import ParseError
from src.lib.identity import Identity
from src.lib.declared_names_table import DeclaredNamesTable


class TestKnownNamesTable:
    def test_declared_first_and_last_names(self):

        table = _create_table(
            """
            Parson, Jimmy
            Johnson, Fred, Jr.
            - Johnson, Freddie, Jr.
            - Johnson, Frederick Q., Jr.
            Lollipop, S. T.
            Lollipop, Susie T.
            Lollipop, S. Terry
            """
        )
        for name in ["Jimmy", "Fred", "Susie", "Terry", "Freddie", "Frederick"]:
            assert table.is_declared_first_name(name)
        for name in ["Parson", "Johnson", "Lollipop"]:
            assert table.is_declared_last_name(name)
        for name in ["Parson", "Johnson", "Lollipop", "S.", "T.", "Q.", "Jr."]:
            assert not table.is_declared_first_name(name)
        for name in [
            "Jimmy",
            "Fred",
            "Susie",
            "Terry",
            "Freddie",
            "Frederick",
            "S.",
            "T.",
            "Q.",
            "Jr.",
        ]:
            assert not table.is_declared_last_name(name)

    def test_revise_last_name(self):

        table = _create_table(
            """
            Johnson, Fred
            Smith, Sammy
            Smith, *, *
                /Smitth, *
                /Smitty, *, *
            Porter, Jim
            """
        )

        p1 = _identity("Smitth", "John")
        table.correct_identity_name(p1)
        assert p1 == _identity("Smith", "John")

        p1 = _identity("Smitty", "John")
        table.correct_identity_name(p1)
        assert p1 == _identity("Smith", "John")

        p1 = _identity("Smitth", "J. J.")
        table.correct_identity_name(p1)
        assert p1 == _identity("Smith", "J. J.")

        p1 = _identity("Smitty", "John", "Jr.")
        table.correct_identity_name(p1)
        assert p1 == _identity("Smith", "John", "Jr.")

        p1 = _identity("Smitth", "John", "Jr.")
        table.correct_identity_name(p1)  # not changed because is Jr.
        assert p1 == _identity("Smitth", "John", "Jr.")

    def test_revise_exact_matches(self):

        table = _create_table(
            """
            Smith, *, *
                /Smitth, John
                /Smitty, *, Jr.
            """
        )

        p1 = _identity("Smitth", "John")
        table.correct_identity_name(p1)
        assert p1 == _identity("Smith", "John")

        p1 = _identity("Smitth", "Johnny")
        table.correct_identity_name(p1)
        assert p1 == _identity("Smitth", "Johnny")

        p1 = _identity("Smitty", "Johnny", "Jr.")
        table.correct_identity_name(p1)
        assert p1 == _identity("Smith", "Johnny", "Jr.")

        p1 = _identity("Smitth", "John", "Jr.")
        table.correct_identity_name(p1)
        assert p1 == _identity("Smitth", "John", "Jr.")

        table = _create_table(
            """
            Smith, *, -
                /Smith, John, Jr.
                /Smitth, John
                /Smitty, *, Jr.
            """
        )

        p1 = _identity("Smith", "John", "Jr.")
        table.correct_identity_name(p1)
        assert p1 == _identity("Smith", "John")

        p1 = _identity("Smitth", "John", "Jr.")
        table.correct_identity_name(p1)
        assert p1 == _identity("Smitth", "John", "Jr.")

        p1 = _identity("Smitth", "John")
        table.correct_identity_name(p1)
        assert p1 == _identity("Smith", "John")

        p1 = _identity("Smitty", "John", "Jr.")
        table.correct_identity_name(p1)
        assert p1 == _identity("Smith", "John")

    def test_revise_first_name(self):

        table = _create_table(
            """
            Smith, Suzie, *
                /Smith, Susie
                /Smith, Susan
            *, Fred, *
                /*, Freddie
            """
        )

        p1 = _identity("Smith", "Suzie")
        table.correct_identity_name(p1)
        assert p1 == _identity("Smith", "Suzie")

        p1 = _identity("Smith", "Susie")
        table.correct_identity_name(p1)
        assert p1 == _identity("Smith", "Suzie")

        p1 = _identity("Smith", "Susan")
        table.correct_identity_name(p1)
        assert p1 == _identity("Smith", "Suzie")

        p1 = _identity("Porter", "Fred")
        table.correct_identity_name(p1)
        assert p1 == _identity("Porter", "Fred")

        p1 = _identity("Porter", "Freddie")
        table.correct_identity_name(p1)
        assert p1 == _identity("Porter", "Fred")

        p1 = _identity("Porter", "Freddie", "Jr.")
        table.correct_identity_name(p1)
        assert p1 == _identity("Porter", "Freddie", "Jr.")

    def test_revise_with_no_first_name(self):

        table = _create_table(
            """
            Smith, -, -
                /Smitth
                /Smith, Susan
            """
        )

        p1 = _identity("Smith", "Suzie")
        table.correct_identity_name(p1)
        assert p1 == _identity("Smith", "Suzie")

        p1 = _identity("Smitth", "Suzie")
        table.correct_identity_name(p1)
        assert p1 == _identity("Smitth", "Suzie")

        p1 = _identity("Smitth")
        table.correct_identity_name(p1)
        assert p1 == _identity("Smith")

        p1 = _identity("Smith", "Susan")
        table.correct_identity_name(p1)
        assert p1 == _identity("Smith")

    def test_multi_word_last_names(self):

        table = _create_table(
            """
            The Cave Club
                /The Cave Cub
            """
        )

        p1 = _identity("Club", "The Cave")
        table.correct_identity_name(p1)
        assert p1 == _identity("The Cave Club")

        p1 = _identity("Cub", "The Cave")
        table.correct_identity_name(p1)
        assert p1 == _identity("The Cave Club")

    def test_bad_syntax(self):

        _assert_raises(
            ParseError,
            lambda: _create_table(
                """
                Johnson, *
                  /johhnson
                """
            ),
        )
        _assert_raises(
            ParseError,
            lambda: _create_table(
                """
                - Johnson
                """
            ),
        )
        _assert_raises(
            ParseError,
            lambda: _create_table(
                """
                /Johnson
                """
            ),
        )
        _assert_raises(
            ParseError,
            lambda: _create_table(
                """
                Johnson, Fred
                - 
                """
            ),
        )
        _assert_raises(
            ParseError,
            lambda: _create_table(
                """
                Johnson, Fred
                / 
                """
            ),
        )
        _assert_raises(
            ParseError,
            lambda: _create_table(
                """
                Johnson, Fred
                  / 
                """
            ),
        )
        _assert_raises(
            ParseError,
            lambda: _create_table(
                """
                *
                  /johhnson, Fred 
                """
            ),
        )
        _assert_raises(
            ParseError,
            lambda: _create_table(
                """
                *, -
                  /johhnson, Fred 
                """
            ),
        )
        _assert_raises(
            ParseError,
            lambda: _create_table(
                """
                *, *
                  /johhnson, Fred 
                """
            ),
        )
        _assert_raises(
            ParseError,
            lambda: _create_table(
                """
                *, *
                  /johhnson, 
                """
            ),
        )
        _assert_raises(
            ParseError,
            lambda: _create_table(
                """
                *, *
                  /johhnson, , Jr.
                """
            ),
        )
        _assert_raises(
            ParseError,
            lambda: _create_table(
                """
                *,
                  /johhnson, , Jr.
                """
            ),
        )
        _assert_raises(
            ParseError,
            lambda: _create_table(
                """
                ,
                  /johhnson, , Jr.
                """
            ),
        )
        _assert_raises(
            ParseError,
            lambda: _create_table(
                """
                ,,
                  /johhnson, , Jr.
                """
            ),
        )
        _assert_raises(
            ParseError,
            lambda: _create_table(
                """
                ,,
                  /,,
                """
            ),
        )
        _assert_raises(
            ParseError,
            lambda: _create_table(
                """
                Johnson, Fred
                  /johhnson, Fred
                  /johhnson, Fred
                """
            ),
        )
        _assert_raises(
            ParseError,
            lambda: _create_table(
                """
                Johnson, Fred
                  /johhnson, Fred
                Johnson, Fred
                  /johhnson, Fred
                """
            ),
        )
        _assert_raises(
            ParseError,
            lambda: _create_table(
                """
                Johnson, *, *
                Blau, Jeff
                """
            ),
        )


def _create_table(name_list_str: str) -> DeclaredNamesTable:

    table = DeclaredNamesTable()
    lines = textwrap.dedent(name_list_str).splitlines()
    for line in lines:
        table.add_correct_name_line(line)
    return table


def _assert_raises(
    exception_type: Type[Exception], test_func: Callable[[], Any]
) -> None:
    with pytest.raises(exception_type):  # type: ignore
        test_func()


def _identity(
    last_name: str,
    initial_names: Optional[str] = None,
    name_suffix: Optional[str] = None,
) -> Identity:
    return Identity(last_name, initial_names, name_suffix)
