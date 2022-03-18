from __future__ import annotations
from typing import Iterator, Optional

from src.lib.identity import Identity
from src.lib.identity_parser import IdentityParser
from src.lib.parse_error import ParseError

# Indexed by last name, then prefix, then initial name sequence.
_Subrevision = dict[Optional[str], dict[Optional[str], Identity]]
_Revision = dict[str, _Subrevision]


class DeclaredProperty(Identity.Property):
    pass


DECLARED_PRIMARY = DeclaredProperty("declared primary")
DECLARED_VARIANT = DeclaredProperty("declared variant")
REFERENCE_NAME = DeclaredProperty("in Specify")
REFERENCE_LAST_NAME = Identity.Property("last name in Specify")
KNOWN_PROPERTY = Identity.Property("in James' list")
PARTIALLY_KNOWN_PROPERTY = Identity.Property("in James' list except M.I.")
SEPARATED_REFERENCE_PROPERTY = Identity.Property("overrode inferred variant")


class DeclaredNamesTable:
    """Constructs a table of declared names, optionally doing so from a file of
    declared names. This file lists one name per line, variant names on lines
    following their primary name. Precede each accepted variant with "- ". The
    file may also indicate misspellings that are to be corrected to the nearest
    preceding primary name or variant by prefixing the name with a forward slash,
    optionally indented by two spaces. The form of each name is "Last, First,
    Suffix". Use the asterisk as a wildcard in a misspelling to indicate that
    portion of the name need not match in order to apply the correction. Use the
    asterisk as a wildcard in primary name to indicate portions of the name that
    are not to be corrected upon matching a misspelling. If not wildcard is given
    for the suffix, a misspelling only matches names without suffixes. In short,
    misspellings designate what to match and primary names designate what to
    change the match to. Primary names with wildcards cannot have variants
    (preceeded with "- ") under them. Follow either a primary name or a variant
    with an exclamation mark to indicate that the name is known to be valid; it's
    possible to declare found-but-possibly-invalid names to organize the catalog.
    Follow with two exclamations if the first and last names match a known name
    but the remainder of the name does not."""

    WILDCARD: str = "*"
    NO_NAME: str = "-"

    def __init__(
        self,
        declared_names_file: Optional[str] = None,
        reference_names_file: Optional[str] = None,
    ):
        self._source_identities_by_name: dict[str, Identity] = {}
        self._references_by_last_name: dict[str, list[Identity]] = {}
        self._name_maps: list[_Primary] = []
        self._primaries_by_name: dict[str, _Primary] = {}
        self._identity_name_to_primary: dict[str, Identity] = {}
        self._revisions: _Revision = {}
        self._lowercase_first_names: dict[str, bool] = {}
        self._lowercase_last_names: dict[str, bool] = {}
        self._prev_primary_had_wildcards = False
        self._bad_reference_names: list[str] = []
        self._group_names: list[str] = []
        self.raw_correction_last_names: dict[str, str] = {}

        self._line_number: int = 0
        if declared_names_file is not None:
            with open(declared_names_file, "r") as file:
                for line in file:
                    self.add_correct_name_line(line)

        self._line_number = 0
        if reference_names_file is not None:
            with open(reference_names_file, "r") as file:
                for line in file:
                    self.add_reference_name_line(line)

    def add_correct_name_line(self, line: str) -> None:
        self._line_number += 1
        if line == "" or line.isspace():
            return

        # Determine what kind of line it is.

        line = line.strip()
        if line.startswith("#"):  # comment line
            return
        is_variant = line.startswith("-")
        is_correction = line.startswith("/")
        if is_variant or is_correction:
            line = line[1:].strip()
            if line == "":
                self._error("No variant or correction")
        exclamations = 0
        if line[-1] == "!":
            if line[-2] == "!":
                exclamations = 2
                line = line[0:-2].strip()
            else:
                exclamations = 1
                line = line[0:-1].strip()

        # Parse out the name and construct a Identity.

        comma_splits = line.split(",")
        if len(comma_splits) > 3:
            self._error("Too many commas")
        last_name = comma_splits[0].strip().replace("  ", " ")
        initial_names: Optional[str] = None
        name_suffix: Optional[str] = None
        if len(comma_splits) > 1:
            initial_names = comma_splits[1].strip().replace("  ", " ")
            if initial_names == "":
                self._error("Missing first name(s)")
            if initial_names == self.NO_NAME:
                initial_names = None
        if len(comma_splits) > 2:
            name_suffix = comma_splits[2].strip()
            if name_suffix == "":
                self._error("Missing name suffix")

        properties: list[Identity.Property] = []
        if is_variant:
            properties.append(DECLARED_VARIANT)
        else:
            properties.append(DECLARED_PRIMARY)
        if exclamations == 1:
            properties.append(KNOWN_PROPERTY)
        elif exclamations == 2:
            properties.append(PARTIALLY_KNOWN_PROPERTY)

        identity = Identity(
            last_name,
            initial_names,
            name_suffix,
            properties,
        )

        # Add the name map to the appropriate location.

        parent: Optional[_Variant] = None
        if is_variant:
            if len(self._name_maps) == 0:
                self._error("Variant name does not follow a primary name")
            parent = self._name_maps[-1]
            parent.variants.append(_Variant(identity))
            self._identity_name_to_primary[str(identity)] = parent.identity
        elif is_correction:
            if len(self._name_maps) == 0:
                self._error("Incorrect name does not follow a correct name")
            parent = self._name_maps[-1]
            if parent.variants:
                parent = parent.variants[-1]
            if parent.corrections is None:
                parent.corrections = []
            parent.corrections.append(identity)
        else:  # if primary

            # Make sure a preceding wildcard primary was given corrections.

            if self._prev_primary_had_wildcards:
                prev_primary = self._name_maps[-1]
                if not prev_primary.corrections:
                    self._error("No corrections for previous wildcard name")
                self._prev_primary_had_wildcards = False
            if (
                last_name == DeclaredNamesTable.WILDCARD
                or initial_names == DeclaredNamesTable.WILDCARD
            ):
                if name_suffix is None:
                    self._error("Missing name suffix correction")
                self._prev_primary_had_wildcards = True

            # Check for required name suffix.ArithmeticError()

            if name_suffix == DeclaredNamesTable.WILDCARD:
                self._prev_primary_had_wildcards = True
            elif name_suffix == self.NO_NAME:
                name_suffix = None
                identity.name_suffix = None

            # Store the primary name away.

            primary = _Primary(identity)
            self._name_maps.append(primary)
            identity_name = str(identity)
            self._primaries_by_name[identity_name] = primary
            self._identity_name_to_primary[identity_name] = identity

            # If the last name contains spaces, index for correcting parser.

            index_identity = self._get_indexed_identity(identity)
            if index_identity is not identity:
                self._put_identity_at_index(index_identity, identity)

            # Collect group names.

            if (
                identity.initial_names is None
                and identity.name_suffix is None
                and " " in identity.last_name
            ):
                self._group_names.append(identity.last_name)

        # Index the names for efficient processing.

        if is_correction:
            # Add this correction to the dictionary of revisions, which ultimately
            # references the primary (parent) name indicating the correction to make.

            assert parent is not None
            index_identity = self._get_indexed_identity(identity)
            self._put_identity_at_index(index_identity, parent.identity)
            self.raw_correction_last_names[line] = parent.identity.last_name

        else:
            # Collect all declared names.

            self._add_source_name(identity)

    def add_properties(self, identity: Identity) -> None:

        try:
            lower_name = str(identity).lower()
            source_identity = self._source_identities_by_name[lower_name]
            identity.add_properties_from(source_identity)
        except KeyError:
            pass

        if self.is_reference_last_name(identity.last_name):
            reference_identity = self._get_reference_identity(identity)
            if reference_identity is not None:
                identity.add_properties_from(reference_identity)
            else:
                identity.add_property(REFERENCE_LAST_NAME)

    def add_reference_name_line(self, line: str) -> None:
        self._line_number += 1
        if line == "" or line.isspace():
            return

        line = line.replace('"', "")
        splits = line.split(",")
        last_name = splits[0].strip()
        first_name = splits[1].strip()
        middle_initial = splits[2].strip()

        if self._line_number == 1:
            assert "lastName" in last_name
            assert "firstName" in first_name
            assert "middleInitial" in middle_initial
            return

        if first_name != "":
            first_names = (
                first_name.lower().replace(".", ". ").replace(",", " ").split(" ")
            )
            for name in first_names:
                if (
                    len(name) > 2
                    and name[-1] != "."
                    and name not in ["jr", "sr", "ii", "iii", "iv"]
                ):
                    self._lowercase_first_names[name] = True

        if len(last_name) > 1 and not last_name.isupper():
            name = first_name
            if middle_initial:
                if name != "":
                    name += " "
                name += middle_initial
            if name != "":
                name += " "
            # Allow parse of Spanish names like "Burgos S.".
            if last_name[-1] == ".":
                last_name = last_name[0:-1]
            # Preserve last names containing spaces.
            name += last_name.replace("   ", " ").replace("  ", " ").replace(" ", "_")
            try:
                identities = IdentityParser(name, True, None, REFERENCE_NAME).parse()
            except ParseError:
                self._bad_reference_names.append(name.replace("_", " "))
                return
            assert identities is not None
            assert len(identities) == 1
            identity = identities[0]
            identity.clear_raw_names()  # Prevent confusing with data.
            identity.last_name = identity.last_name.replace("_", " ")
            last_name_key = last_name.lower()
            try:
                self._references_by_last_name[last_name_key].append(identity)
            except KeyError:
                self._references_by_last_name[last_name_key] = [identity]
            self._add_source_name(identity)

    def correct_identity_name(self, identity: Identity) -> None:
        revision = self._get_revision(identity)
        if revision is not None:
            if revision.last_name != self.WILDCARD:
                identity.last_name = revision.last_name
            if revision.name_suffix != self.WILDCARD:
                identity.name_suffix = revision.name_suffix
            if revision.initial_names != self.WILDCARD:
                identity.initial_names = revision.initial_names

    def get_group_names(self) -> list[str]:
        return self._group_names

    def get_primary(
        self, variant_name: str, references_are_primary: bool = False
    ) -> Optional[Identity]:
        try:
            return self._identity_name_to_primary[variant_name]
        except KeyError:
            if references_are_primary:
                try:
                    primary = self._source_identities_by_name[variant_name]
                    assert primary.has_property(REFERENCE_NAME)
                    return primary
                except KeyError:
                    return None
            return None

    def get_known_identity_iterator(self) -> Iterator[Identity]:
        return iter(self._source_identities_by_name.values())

    def get_bad_reference_names(self) -> list[str]:
        return self._bad_reference_names

    def get_variant_identities(self, primary_name: str) -> Optional[list[Identity]]:
        try:
            primary = self._primaries_by_name[primary_name]
            return [v.identity for v in primary.variants]
        except KeyError:
            return None

    def is_declared_first_name(self, first_name: str) -> bool:
        return first_name.lower() in self._lowercase_first_names

    def is_declared_last_name(self, last_name: str) -> bool:
        return last_name.lower() in self._lowercase_last_names

    def is_reference_last_name(self, last_name: str) -> bool:
        return last_name.lower() in self._references_by_last_name

    def _add_source_name(self, identity: Identity) -> None:

        # Add a fully specified name to master list of source names.

        lower_name = str(identity).lower()
        if "*" not in lower_name:
            try:
                source_identity = self._source_identities_by_name[lower_name]
                source_identity.add_properties_from(identity)
            except KeyError:
                self._source_identities_by_name[lower_name] = identity

        # Collect first and last names for separate lookup.

        if identity.initial_names is not None:
            initial_names_splits = identity.initial_names.split(" ")
            for initial_names_split in initial_names_splits:
                if len(initial_names_split) > 1 and initial_names_split[-1] != ".":
                    self._lowercase_first_names[initial_names_split.lower()] = True
        self._lowercase_last_names[identity.last_name.lower()] = True

    def _error(self, message: str) -> None:
        raise ParseError("%s (line %d)" % (message, self._line_number))

    def _get_indexed_identity(self, identity: Identity) -> Identity:
        if " " not in identity.last_name:
            return identity
        if identity.initial_names is not None or identity.name_suffix is not None:
            return identity
        identities = IdentityParser(identity.last_name).parse()
        assert identities is not None
        return identities[0]

    def _get_reference_identity(self, identity: Identity) -> Optional[Identity]:
        try:
            found_identities = self._references_by_last_name[identity.last_name.lower()]
            for found_identity in found_identities:
                if identity == found_identity:
                    return identity
            return None
        except KeyError:
            return None

    def _get_revision(self, key_identity: Identity) -> Optional[Identity]:
        try:
            last_name_dict = self._revisions[key_identity.last_name]
            return self._get_from_revision(last_name_dict, key_identity)
        except KeyError:
            try:
                last_name_dict = self._revisions[self.WILDCARD]
                return self._get_from_revision(last_name_dict, key_identity)
            except KeyError:
                return None

    def _get_from_revision(
        self, last_name_dict: _Subrevision, key_identity: Identity
    ) -> Optional[Identity]:
        try:
            name_suffixes_dict = last_name_dict[key_identity.name_suffix]
        except KeyError:
            name_suffixes_dict = last_name_dict[self.WILDCARD]
        try:
            return name_suffixes_dict[key_identity.initial_names]
        except KeyError:
            return name_suffixes_dict[self.WILDCARD]

    def _put_identity_at_index(self, index: Identity, identity: Identity) -> None:
        try:
            last_name_revision = self._revisions[index.last_name]
            try:
                name_suffix_revision = last_name_revision[index.name_suffix]
                if index.initial_names in name_suffix_revision:
                    self._error("Correction already exists elsewhere")
                name_suffix_revision[index.initial_names] = identity
            except KeyError:
                last_name_revision[index.name_suffix] = {index.initial_names: identity}
        except KeyError:
            self._revisions[index.last_name] = {
                index.name_suffix: {index.initial_names: identity}
            }


class _Variant:
    def __init__(self, identity: Identity):
        self.identity = identity
        self.corrections: Optional[list[Identity]] = None  # TODO: Not used?


class _Primary(_Variant):
    def __init__(self, identity: Identity):
        super().__init__(identity)
        self.variants: list[_Variant] = []
