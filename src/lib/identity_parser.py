from __future__ import annotations
from typing import Optional, TYPE_CHECKING
import re

if TYPE_CHECKING:
    from src.lib.declared_names_table import DeclaredNamesTable
from src.lib.lookahead_parser import LookaheadParser, OptStateFunc
from src.lib.parse_error import ParseError
from src.lib.identity import Identity

UNCERTAIN_PROPERTY = Identity.Property("UNCERTAIN")


class _NameToken:
    """Class Representing a name token"""

    COMMA = 0  # ","
    NAME = 1  # name without any periods
    ABBREV = 2  # one or more letters of a name followed by period
    SUFFIX = 3  # name suffix

    ABBREVIATED_SUFFIXES = ["Jr", "Sr"]
    ROMAN_SUFFIXES = ["II", "III", "IV"]

    def __init__(self, raw_text_offset: int, raw_text: str):
        self.type: Optional[int] = None
        self.value: str = raw_text
        self.raw_text_offset = raw_text_offset
        potential_suffix = raw_text.capitalize()
        if potential_suffix[-1] == ".":
            potential_suffix = raw_text[0:-1]

        if raw_text == ",":
            self.type = self.COMMA
        elif potential_suffix in self.ABBREVIATED_SUFFIXES:
            self.type = self.SUFFIX
            self.value = "%s." % potential_suffix
        elif raw_text in self.ROMAN_SUFFIXES:
            self.type = self.SUFFIX
            self.value = raw_text
        elif raw_text[-1] == ".":
            self.type = self.ABBREV
        else:
            self.type = self.NAME


class _NameTokenizer:

    REGEX = re.compile(r"[^-–., ]+[.]?|[.,]|[-–]| +")  # 2nd dash is not short!
    HYPHENS = "-–"  # 2nd dash is not short!

    def __init__(self, raw_text: str):
        self._raw_tokens: list[str] = self.REGEX.findall(raw_text)
        self._raw_token_index: int = 0
        self._token_start_offset: int = 0
        self._token_next_start_offset: int = 0
        self._token_str: str = ""

    def __iter__(self):  # designate class as an Iterable
        return self

    def __next__(self) -> _NameToken:
        while self._raw_token_index < len(self._raw_tokens):
            raw_token = self._raw_tokens[self._raw_token_index]
            if raw_token.islower() and raw_token != "et_al!":
                raw_token = raw_token.capitalize()
            self._raw_token_index += 1
            if raw_token == ".":
                raise ParseError("extraneous period")
            elif raw_token[0] in self.HYPHENS:
                if self._token_str == "":
                    raise ParseError("name begins with a hyphen")
                if self._token_str[-1] == "-":
                    raise ParseError("repeated hyphens")
                self._token_str += "-"
            elif raw_token[0] != " ":
                if self._token_str == "":
                    self._token_str = raw_token
                elif self._token_str[-1] == "-":
                    self._token_str += raw_token
                else:
                    start_offset = self._token_start_offset
                    next_token_str = self._token_str
                    self._token_start_offset = self._token_next_start_offset
                    self._token_next_start_offset += len(raw_token)
                    self._token_str = raw_token
                    return _NameToken(start_offset, next_token_str)
            self._token_next_start_offset += len(raw_token)
        if self._token_str != "":
            start_offset = self._token_start_offset
            token_str = self._token_str
            self._token_start_offset = self._token_next_start_offset
            self._token_str = ""
            return _NameToken(start_offset, token_str)
        raise StopIteration


_OptStateFunc = OptStateFunc[_NameToken]


class IdentityParser(LookaheadParser[_NameToken]):

    # Making this a lookahead-parser prevents us from having to track the
    # most name for a subsequent state to decide what to do with. It also
    # reduces the number of states needed.
    #
    # Assumes a suffix always ends the name; first name can't follow suffix.

    def __init__(
        self,
        raw_text: str,
        handle_syntax_errors: bool = True,
        declared_names_table: Optional[DeclaredNamesTable] = None,
        identity_property: Optional[Identity.Property] = None,
        raw_ranges: list[tuple[int, int]] = [],
    ):
        super().__init__()
        self._identity_properties = (
            [identity_property] if identity_property is not None else None
        )
        self._raw_text = raw_text
        self._handle_syntax_errors = handle_syntax_errors
        self._raw_ranges = raw_ranges
        self._name_start_offset: int = 0
        self._name_end_offset: int = 0
        self._tokenizer = _NameTokenizer(self._preprocess_text(raw_text))
        self._declared_names_table = declared_names_table

        self._identities: list[Identity] = []
        self._state: _OptStateFunc = self._state_start

        self._initial_names: Optional[str] = None
        self._last_name: Optional[str] = None
        self._name_suffix: Optional[str] = None

        self._warnings: Optional[list[str]] = None

    def parse(self) -> Optional[list[Identity]]:
        for token in self._tokenizer:
            self._tokens.append(token)
        super()._parse()
        return self._identities if self._identities else None

    def get_warnings(self) -> list[str]:
        return self._warnings if self._warnings else []

    def _preprocess_text(self, text: str) -> str:
        # Preprocess valid names. Don't make corrections here.
        # Must preserve the original number of characters.

        text = text.replace("de la Rosa Reyna", "de_la_Rosa_Reyna")
        mods = {
            "de la ": "de_la_",
            "De ": "De_",
            "Le ": "Le_",
            "St. ": "St!_",
            "van ": "van_",
            "Van ": "Van_",
            "et al.": "et_al!",
        }
        for from_substring, to_substring in mods.items():
            text = text.replace(from_substring, to_substring)

        mods = {
            " de ": " de_",
            ",de ": ",de_",
        }
        for from_substring, to_substring in mods.items():
            text = text.replace(from_substring, to_substring)
        if text.startswith("de "):
            text = "de_" + text[3:]

        return text

    def _undo_preprocessing(self, text: str) -> str:
        return text.replace("_", " ").replace("!", ".")

    def _state_start(self, token: Optional[_NameToken]) -> _OptStateFunc:
        """Initial state for parsing one or more comma-delimited names"""
        if token is None:
            raise ParseError("empty name")
        elif token.type is _NameToken.COMMA:
            self._add_warning("extraneous comma")
            return self._state_start
        elif token.type is _NameToken.SUFFIX:
            raise ParseError("name starts with a name suffix '%s'" % token.value)
        else:
            self._name_start_offset = token.raw_text_offset
            if self._parses_as_last_name(token):
                value = token.value
                self._last_name = value
                # Handle an acronym that entirely designates an entity.
                if len(value) >= 3 and value.isalpha() and value.isupper():
                    return self._state_end_of_name
                return self._state_last_name_first
            else:
                self._append_initial_name(token)
                return self._state_initial_names_first

    def _state_last_name_first(self, token: Optional[_NameToken]) -> _OptStateFunc:
        """State in which have last name but no first name and no trailing comma"""
        if token is None:
            self._name_end_offset = len(self._raw_text)
            self._add_new_identity()
            return None
        elif token.type is _NameToken.COMMA:
            self._name_end_offset = token.raw_text_offset
            return self._state_initial_names_second
        elif token.type is _NameToken.SUFFIX:
            self._assign_suffix(token.value)
            return self._state_end_of_name
        else:
            raise ParseError("could not parse '%s'" % token.value)

    def _state_initial_names_first(self, token: Optional[_NameToken]) -> _OptStateFunc:
        """State in which have first name but no last name and no trailing comma"""
        if token is None or token.type is _NameToken.COMMA:
            assert self._initial_names is not None
            name_splits = self._initial_names.split(" ")
            if len(name_splits) == 1:
                self._last_name = self._initial_names
                self._initial_names = None
            elif name_splits[0][1] == "." or not self._handle_syntax_errors:
                self._last_name = name_splits[-1]
                self._initial_names = " ".join(name_splits[0:-1])
            else:
                self._last_name = name_splits[0]
                self._initial_names = " ".join(name_splits[1:])
            if token is None:
                self._name_end_offset = len(self._raw_text)
                self._add_new_identity()
                return None
            self._name_end_offset = token.raw_text_offset
            if len(name_splits) == 1:
                return self._state_initial_names_second
            return self._state_started_another_name
        elif token.type is _NameToken.SUFFIX:
            raise ParseError("name suffix '%s' precedes last name" % token.value)
        elif self._parses_as_last_name(token):
            self._last_name = token.value
            return self._state_end_of_name
        else:
            self._append_initial_name(token)
            return self._state_initial_names_first

    def _state_initial_names_second(self, token: Optional[_NameToken]) -> _OptStateFunc:
        """State in which we have a last name that was followed by a comma, either
        none of the first name or part of first name, and no subsequent comma"""
        if token is None:
            if self._initial_names is None:
                self._add_warning("extraneous comma")  # preceding this state
            else:
                self._name_end_offset = len(self._raw_text)
            self._add_new_identity()
            return None
        elif token.type is _NameToken.COMMA:
            if self._initial_names is None:
                self._add_warning("extraneous comma")
            else:
                self._name_end_offset = token.raw_text_offset
            return self._state_started_another_name
        elif token.type is _NameToken.SUFFIX:
            self._assign_suffix(token.value)
            return self._state_end_of_name
        else:
            if self._initial_names is None and self._parses_as_last_name(token):
                if not self._is_declared_first_name(token):
                    if self._is_declared_last_name(token):
                        self._add_new_identity()
                        self._name_start_offset = token.raw_text_offset
                        self._last_name = token.value
                        return self._state_last_name_first
            self._append_initial_name(token)
            return self._state_initial_names_second

    def _state_end_of_name(self, token: Optional[_NameToken]) -> _OptStateFunc:
        """State in which have first name and last name and no trailing comma"""
        if token is None:
            self._name_end_offset = len(self._raw_text)
            self._add_new_identity()
            return None
        elif token.type is _NameToken.COMMA:
            self._name_end_offset = token.raw_text_offset
            return self._state_started_another_name  # suffix may still follow
        elif token.type is _NameToken.SUFFIX:
            self._assign_suffix(token.value)
            return self._state_end_of_name
        else:
            raise ParseError("unexpected continuation of name at '%s'" % token.value)

    def _state_started_another_name(self, token: Optional[_NameToken]) -> _OptStateFunc:
        """State in which received first name and last name and trailing comma"""
        if token is None:
            self._add_warning("extraneous comma")
            return None
        elif token.type is _NameToken.SUFFIX:
            self._assign_suffix(token.value)
            return self._state_end_of_name
        else:
            self._add_new_identity()
            return self._state_start(token)

    def _add_new_identity(self) -> None:
        assert self._last_name is not None
        self._identities.append(
            Identity(
                self._undo_preprocessing(self._last_name),
                self._initial_names,
                self._name_suffix,
                self._identity_properties,
                self._raw_text[self._name_start_offset : self._name_end_offset],
            )
        )
        self._raw_ranges.append((self._name_start_offset, self._name_end_offset))
        self._last_name = None
        self._initial_names = None
        self._name_suffix = None

    def _append_initial_name(self, token: _NameToken) -> None:
        name = token.value
        if not name[0].isalpha():
            raise ParseError("name '%s' does not begin with a letter" % name)
        if len(name) == 1:
            name += "."
        elif token.type is _NameToken.ABBREV and len(name) == 3 and name.isupper():
            name = "%s. %s" % (name[0], name[1:])
        if self._initial_names is None:
            self._initial_names = name
        else:
            self._initial_names += " %s" % name

    def _assign_suffix(self, suffix: str) -> None:
        if self._name_suffix is not None:
            raise ParseError("multiple suffixes in one name at '%s'" % suffix)
        self._name_suffix = suffix

    def _is_declared_first_name(self, token: _NameToken) -> bool:
        if self._declared_names_table is None:
            return False
        return self._declared_names_table.is_declared_first_name(token.value)

    def _is_declared_last_name(self, token: _NameToken) -> bool:
        if self._declared_names_table is None:
            return False
        return self._declared_names_table.is_declared_last_name(token.value)

    def _parses_as_last_name(self, token: _NameToken) -> bool:
        next_token = self._lookahead(1)
        return token.type is _NameToken.NAME and (
            next_token is None
            or next_token.type is _NameToken.COMMA
            or next_token.type is _NameToken.SUFFIX
        )

    def _add_warning(self, warning: str) -> None:
        if self._warnings is None:
            self._warnings = [warning]
        else:
            self._warnings.append(warning)
