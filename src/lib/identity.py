from __future__ import annotations
from typing import Any, Optional, Union


class Identity:
    class Property:
        def __init__(self, name: str):
            self.name = name

        def __str__(self) -> str:
            return self.name

    def __init__(
        self,
        last_name: str,
        initial_names: Optional[str] = None,  # space-separated non-last names
        name_suffix: Optional[str] = None,  # e.g. Jr., Sr., II, III
        properties: Optional[list[Identity.Property]] = None,
        raw_name: Optional[str] = None,  # text that sourced this identity
    ):
        self.initial_names = initial_names
        self.last_name = last_name
        self.name_suffix = name_suffix
        self.raw_name = raw_name
        self.uncertain = False
        self._properties: Optional[list[Identity.Property]] = None
        if properties:
            for property in properties:
                self.add_property(property)  # centrally check all properties
        self._raw_names: Optional[Union[str, list[str]]] = (
            self.normalize_raw_name(raw_name) if raw_name is not None else None
        )

        # `primary` is the instance representing the variant of the name that
        # should be used in reports for data that use one of the variants.
        self.primary: Optional[Identity] = None

        # `occurrence_count` is the number of occurrences of this exact name
        # in the data.
        self.occurrence_count: int = 1

        # `_master_copy` is the copy with correct primary and all raw names
        self._master_copy: Optional[Identity] = None

    def __str__(self) -> str:
        s = self.last_name
        if self.initial_names is not None:
            s += ", " + self.initial_names
        if self.name_suffix is not None:
            s += ", " + self.name_suffix
        return s

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Identity):
            return False
        return (
            self.last_name == other.last_name
            and self.initial_names == other.initial_names
            and self.name_suffix == other.name_suffix
        )

    def add_property(self, property: Identity.Property) -> None:
        if self._properties is None:
            self._properties = [property]
        elif property not in self._properties:
            self._properties.append(property)

    def add_properties_from(self, identity: Identity) -> None:
        for property in identity.get_properties():
            self.add_property(property)

    def add_raw_name(self, raw_name: str) -> None:
        raw_name = self.normalize_raw_name(raw_name)
        if self._raw_names is None:
            self._raw_names = raw_name
        else:
            if not isinstance(self._raw_names, list):
                self._raw_names = [self._raw_names]
            if raw_name not in self._raw_names:
                self._raw_names.append(raw_name)

    def clear_raw_names(self):
        self._raw_names = None

    def get_first_name(self) -> Optional[str]:
        if self.initial_names is None:
            return None
        first_space = self.initial_names.find(" ")
        if first_space == -1:
            return self.initial_names
        return self.initial_names[0:first_space]

    def get_fnf_correction(self, coded_for_shortening: bool = False) -> str:
        # first name first correction
        master_copy = self.get_master_copy()
        last_name = master_copy.last_name
        if master_copy.name_suffix is None:
            name = last_name
        else:
            name = "%s, %s" % (last_name, master_copy.name_suffix)
        if master_copy.initial_names is not None:
            initial_names = master_copy.initial_names
            if coded_for_shortening:
                splits = initial_names.split(" ")
                initial_names = ""
                for split in splits:
                    if split[1] == "." and len(split) == 2:
                        initial_names += split
                    else:
                        initial_names += split + "}"
            if initial_names[-1] == "}":
                name = initial_names + name
            else:
                name = "%s %s" % (initial_names, name)
        return name

    def get_full_name(self) -> str:
        primary = self.get_master_copy().primary
        assert primary is not None
        s = primary.last_name
        if primary.initial_names is not None:
            s = primary.initial_names + " " + s
        if primary.name_suffix is not None:
            s = s + ", " + primary.name_suffix
        return s

    def get_lnf_primary(self) -> str:
        # last name first correction
        master_copy = self.get_master_copy().primary
        assert master_copy is not None
        name = master_copy.last_name
        if master_copy.initial_names is not None:
            name = "%s, %s" % (name, master_copy.initial_names)
        if master_copy.name_suffix is not None:
            name = "%s, %s" % (name, master_copy.name_suffix)
        return name

    @staticmethod
    def get_corrected_primary_names(
        identities: Optional[list[Identity]], coded_for_shortening: bool = False
    ) -> Optional[str]:
        if identities is None:
            return None
        corrections: list[str] = []
        delimiter = ", "
        for identity in identities:
            primary = identity.get_master_copy().primary
            assert primary is not None, "No primary for '%s'" % str(identity)
            corrected_name = primary.get_fnf_correction(coded_for_shortening)
            corrections.append(corrected_name)
            if primary.initial_names is None and primary.last_name != "et al.":
                delimiter = "; "
        return delimiter.join(corrections)

    def get_master_copy(self) -> Identity:
        master_copy = self._master_copy
        if master_copy is None:
            return self
        while master_copy._master_copy is not None:
            master_copy = master_copy._master_copy
        return master_copy

    def get_properties(self) -> list[Identity.Property]:
        return self._properties if self._properties is not None else []

    def get_raw_name(self) -> str:
        assert isinstance(self._raw_names, str)
        return self._raw_names

    def get_raw_names(self):
        if self._raw_names is None:
            return None
        if isinstance(self._raw_names, str):
            return [self._raw_names]
        return self._raw_names

    def has_property(self, property: Union[Identity.Property, type]) -> bool:
        if self._properties is None:
            return False
        if isinstance(property, Identity.Property):
            return property in self._properties
        for p in self._properties:
            if isinstance(p, property):
                return True
        return False

    def merge_with(self, identity: Identity) -> None:

        assert identity is not self, "Attempted to merge '%s' with itself" % str(self)

        other_raw_name = identity._raw_names
        if other_raw_name is not None:
            if isinstance(other_raw_name, str):
                self.add_raw_name(other_raw_name)
            else:
                for raw_name in other_raw_name:
                    self.add_raw_name(raw_name)

        identity._master_copy = self

    @staticmethod
    def normalize_raw_name(raw_name: str) -> str:
        # Might compare performance with regex.sub(), which
        # still has to test each match to select a replacement.
        return (
            raw_name.replace("  ", " ")
            .replace("..", ".|.")
            .replace(".", ". ")
            .replace(",", ", ")
            .replace("  ", " ")
            .replace(". ,", ".,")
            .replace(", .", ",.")
            .replace(", ,", ",,")
            .replace(" |", "")
            .rstrip()
        )

    def set_raw_name(self, new_raw_name: str) -> None:
        self.raw_name = new_raw_name
        self._raw_names = new_raw_name
