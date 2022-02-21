from __future__ import annotations
from typing import Optional, TYPE_CHECKING
import re

if TYPE_CHECKING:
    from src.lib.declared_names_table import DeclaredNamesTable
from src.lib.parse_error import ParseError
from src.lib.identity import Identity
from src.lib.identity_parser import IdentityParser

FOUND_PROPERTY = Identity.Property("found in data")


class NameColumnParser:

    # The second initial requires a period to avoid other occurrences of '&'.
    NAME_PAIR = re.compile(r"(([^&,;]+), *([a-zA-Z][.]?) *& *([a-zA-Z][.]))")
    SHUFFLED_INITIAL = re.compile(r"^([-a-zA-Z'. ]+), *([a-zA-Z][.]?)$")

    def __init__(self, text: str, declared_names_table: DeclaredNamesTable):
        assert "^" not in text
        assert "|" not in text
        self._text = text.strip()
        self._declared_names_table = declared_names_table
        self._errors: Optional[list[str]] = None
        self._warnings: Optional[list[str]] = None

    def parse(self) -> Optional[list[Identity]]:
        if self._text == "":
            return None

        if ",," in self._text or ", ," in self._text:
            self._add_warning("extraneous comma")
        if self._declared_names_table is not None:
            self._text = self.preprocess_raw_column(self._text)
        column_identities: list[Identity] = []

        semi_splits = self._text.split(";")  # semicolons can divide sets of names
        for semi_split in semi_splits:
            semi_split = semi_split.strip()
            try:
                raw_split = ""
                if semi_split == "":
                    self._add_warning("extraneous name delimiter")
                    continue
                if semi_split.endswith("]]"):
                    raw_name_offset = semi_split.find("[[")
                    raw_split = (
                        semi_split[raw_name_offset + 2 : -2]
                        .replace("&", " & ")
                        .replace("  ", " ")
                        .strip()
                    )
                    semi_split = semi_split[0:raw_name_offset]
                if semi_split.isnumeric():
                    raise ParseError("completely numeric name '%s'" % semi_split)
                # James says there's nothing more he can do.
                # if "?" in semi_split:
                #     self._add_warning("'%s' contains a question mark" % semi_split)
                for i, c in enumerate(semi_split):
                    if ord(c) < 32 or ord(c) > 122 and not c.isalpha():
                        raise ParseError(
                            "Unexpected character #%d found at offset %d of '%s'"
                            % (ord(c), i, semi_split)
                        )
                raw_ranges: list[tuple[int, int]] = []
                parser = IdentityParser(
                    self.preprocess_raw_name(semi_split),
                    True,
                    self._declared_names_table,
                    FOUND_PROPERTY,
                    raw_ranges,
                )
                split_identities = parser.parse()
                for warning in parser.get_warnings():
                    self._add_warning(warning)

                if split_identities is not None:
                    for i, identity in enumerate(split_identities):
                        name = str(identity)
                        if len(name) == 2 and name[1] == ".":
                            self._add_error(
                                "Name '%s' consists only of an initial" % name
                            )
                        else:
                            self._undo_preprocessing(identity)
                            column_identities.append(identity)
                            if raw_split == "":
                                raw_name = semi_split[
                                    raw_ranges[i][0] : raw_ranges[i][1]
                                ]
                            else:
                                raw_name = raw_split
                            identity.set_raw_name(Identity.normalize_raw_name(raw_name))
            except ParseError as e:
                self._add_error(e.message)
        return column_identities if column_identities else None

    def get_errors(self) -> list[str]:
        return self._errors if self._errors else []

    def get_warnings(self) -> list[str]:
        return self._warnings if self._warnings else []

    @classmethod
    def preprocess_raw_column(cls, text: str) -> str:
        # Return sooner for efficiency, when possible.

        if text == "":
            return text

        # Remove "det" indication.

        lower_text = text.lower()
        if lower_text.startswith("det"):
            if lower_text.startswith("det "):
                text = text[4:]
            elif lower_text.startswith("det. "):
                text = text[5:]

        # Modify text in ways not requiring reporting.

        if text[0] == ".":
            text = text[1:]

        corrections = {
            "Barr, Mitchell, Andrews": "Barr, T.C.; Mitchell, R.W.; Andrews",
            "Bell, W.Reddell": "Bell, W., Reddell",
            "Brown, J. De Leon": "Brown, J., De Leon",
            "Bryce, Smith": "Smith, Bryce",
            "Calvert, W. Warton": "Calvert, W., Warton",
            "CM, MS": "McCann, Cait; Schramm, Matt",
            "Collins, C. Weissling": "Collins, C., Weissling",
            "Cowell, B. Ivy": "Cowell, B., Ivy",
            "Elliott, W.. Alexander": "Elliott, W.., Alexander",
            "Gamboa, A. McKenzie": "Gamboa, A., McKenzie",
            "Garza, E.Cavanaugh": "Garza, E., Cavanaugh",
            "Gluesenkamp, A. Rutherford": "Gluesenkamp, A., Rutherford",
            "Graves, L.J. McKenzie": "Graves, L.J., McKenzie",
            "Grubbs, .A.G.": "Grubbs, A.G.",
            "Hernandez Justin": "Hernandez, Justin",
            "Ibar., Carmen": "Ibar, Carmen",
            "Krejca, J. Sprouse": "Krejca, J., Sprouse",
            "Lieberz, J. Balsdon": "Lieberz, J., Balsdon",
            "Loftin, :Lacey": "Loftin, Lacey",
            "McDermid, Stock, Greg": "McDermid; Stock, Greg",
            "McKenzie, M.Buttwrwick": "McKenzie, M., Buttwrwick",
            "McKenzie, Suzanne Wiley": "David McKenzie, Suzanne Wiley",
            "McKenzie, Wiley, S.": "McKenzie, S. Wiley",
            "Mitchell, R.W.Abernethy": "Mitchell, R.W., Abernethy",
            "MullinexTibbetts": "Mullinex Tibbetts",
            "Murray;  C.;": "Murray, C.;",
            "Myers,. Rob": "Myers, Rob",
            "Randy.": "Randy",
            "Reddell, ,J.": "Reddell, J.",
            "Reddell, J. Reyes": "Reddell, J., Reyes",
            "Reyes, M. Stanford": "Reyes, M., Stanford",
            "Reyes,.": "Reyes,",
            "Robertson; Steve": "Robertson, Steve",
            "Saususs; Francois": "Saususs, Francois",
            "Scott, Travis, Scott": "Scott, Travis",
            "Snow, J. Fryer": "Snow, J., Fryer",
            "Sprouse, P. Savvas": "Sprouse, P., Savvas",
            "Treacy Sprouse, Terri": "Sprouse, Terri Treacy",
            "Treacey Sprouse, Terri": "Sprouse, Terri Treacey",
            "Van Helsdingen P. J.": "Van Helsdingen, P. J.",
            "Warton (M.)": "Warton, M.",
            "Winterath, Elliott, W.R.": "Winterath; Elliott, W.R.",
        }
        for from_substring, to_substring in corrections.items():
            text = text.replace(from_substring, to_substring)

        # if "Rosa Reyna" not in text:
        #     text = text.replace("de la Rosa", "de la Rosa Reyna")

        # Replace names of the form "Lat, A. & B."
        matches = cls.NAME_PAIR.findall(text)
        if matches:
            for match in matches:
                name1 = "%s, %s" % (match[1], match[2])
                name2 = "%s, %s" % (match[1], match[3])
                # Embeds the raw name in brackets.
                sub = "%s[[%s]];%s[[%s]]" % (name1, match[0], name2, match[0])
                sub = sub.replace("&", "@")
                text = text.replace(match[0], sub)

        text = text.replace("  ", " ")
        corrections = {
            ",&": ";",
            ", &": ";",
            ";&": ";",
            "; &": ";",
            ",and ": ";",
            ", and ": ";",
            ";and ": ";",
            "; and ": ";",
        }
        for from_substring, to_substring in corrections.items():
            text = text.replace(from_substring, to_substring)
        corrections = {
            "/": ";",
            "&": ";",
            " and ": ";",
            ":": ";",
            ";'": "'",
        }
        for from_substring, to_substring in corrections.items():
            text = text.replace(from_substring, to_substring)

        text = text.replace("e t al.", "et al.").replace("et. al.", "et al.")
        if "et al" in text:  # only do this sequence when necessary
            # "et al." does occur before end of text
            text = (
                text.replace(",et al.", ";et al.")
                .replace(", et al.", ";et al.")
                .replace(",  et al.", ";et al.")
                .replace("et al.", ";et al.")
                .replace(" et al", ";et al.")
                .replace(", et al", ";et al.")
                .replace(";;et al.", ";et al.")
                .replace("; ;et al.", ";et al.")
            )

        text = text.replace("@", "&")  # restore embedded raw name
        return text

    @classmethod
    def preprocess_raw_name(cls, text: str, is_duplicate: bool = False) -> str:
        # Must preserve the number of characters so that the offsets
        # into the original raw data remain the same.

        matches = cls.SHUFFLED_INITIAL.match(text)
        if matches is not None:
            # Insert number of spaces needed to preserve original length.
            space_count = len(text) - len(matches.group(1)) - len(matches.group(2))
            text = "%s%s%s" % (matches.group(2), " " * space_count, matches.group(1))

        corrections = {
            "Gert sch": "Gert|sch",
            "Richt er": "Richt|er",
            "West brook": "West|brook",
            ",.": ". ",
            ",,": ", ",
            "..": ". ",
            "(?)": "   ",
            "’": "'",  # not presently in the data; James must have fixed
        }
        for from_substring, to_substring in corrections.items():
            text = text.replace(from_substring, to_substring)
        text = text.replace("?", " ")  # must follow above "(?)" replacement

        return text

    def _add_error(self, error: str) -> None:
        if self._errors is None:
            self._errors = [error]
        else:
            self._errors.append(error)

    def _add_warning(self, warning: str) -> None:
        if self._warnings is None:
            self._warnings = [warning]
        else:
            self._warnings.append(warning)

    @classmethod
    def _undo_preprocessing(cls, identity: Identity) -> None:
        corrections = {"|": "", "!": ".", "_": " "}
        for code, correction in corrections.items():
            identity.last_name = identity.last_name.replace(code, correction)
        if identity.initial_names is not None:
            for code, correction in corrections.items():
                identity.initial_names = identity.initial_names.replace(
                    code, correction
                )
