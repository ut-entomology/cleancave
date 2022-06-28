from __future__ import annotations
from typing import Callable, Optional, TYPE_CHECKING, Union
from functools import partial

if TYPE_CHECKING:
    from src.reporter.specimen_record import SpecimenRecord
from src.util.states import States

TaxonDelta = tuple[str, Optional[str]]
TaxonGroup = tuple[list[TaxonDelta], list["SpecimenRecord"]]
RestrictionFunc = Callable[["SpecimenRecord"], bool]

NO_TAXON_STR = "--"


class TaxaIterator:

    _UNRECOGNIZED = "!"

    def __init__(self, records: list["SpecimenRecord"]):
        self._records = records
        self._record_index: int = 0

        for record in records:
            record.sort_key = to_taxon_sort_key(record)
        records.sort(key=lambda r: r.sort_key)

        self._last_phylum: Optional[str] = self._UNRECOGNIZED
        self._last_class: Optional[str] = self._UNRECOGNIZED
        self._last_subclass: Optional[str] = self._UNRECOGNIZED
        self._last_order: Optional[str] = self._UNRECOGNIZED
        self._last_suborder: Optional[str] = self._UNRECOGNIZED
        self._last_infraorder: Optional[str] = self._UNRECOGNIZED
        self._last_family: Optional[str] = self._UNRECOGNIZED
        self._last_subfamily: Optional[str] = self._UNRECOGNIZED
        self._last_genus_species: Optional[str] = self._UNRECOGNIZED

        if self._record_index < len(records):
            record = records[self._record_index]
            self._next_deltas = self._compute_deltas(record)

    def __iter__(self) -> TaxaIterator:
        return self

    def __next__(self) -> TaxonGroup:
        if self._record_index == len(self._records):
            raise StopIteration

        record = self._records[self._record_index]
        record_group: list["SpecimenRecord"] = []
        current_deltas = self._next_deltas
        self._next_deltas = []

        while self._next_deltas == []:
            record_group.append(record)
            self._record_index += 1
            if self._record_index == len(self._records):
                break
            record = self._records[self._record_index]
            self._next_deltas = self._compute_deltas(record)

        record_group.sort(
            key=lambda r: 0 if r.catalog_number is None else r.catalog_number
        )
        return (current_deltas, record_group)

    def _clear_class(self) -> None:
        self._last_class = self._UNRECOGNIZED
        self._clear_subclass()

    def _clear_subclass(self) -> None:
        self._last_subclass = self._UNRECOGNIZED
        self._clear_order()

    def _clear_order(self) -> None:
        self._last_order = self._UNRECOGNIZED
        self._clear_suborder()

    def _clear_suborder(self) -> None:
        self._last_suborder = self._UNRECOGNIZED
        self._clear_infraorder()

    def _clear_infraorder(self) -> None:
        self._last_infraorder = self._UNRECOGNIZED
        self._clear_family()

    def _clear_family(self) -> None:
        self._last_family = self._UNRECOGNIZED
        self._clear_subfamily()

    def _clear_subfamily(self) -> None:
        self._last_subfamily = self._UNRECOGNIZED
        self._clear_genus_species()

    def _clear_genus_species(self) -> None:
        self._last_genus_species = self._UNRECOGNIZED

    def _compute_deltas(self, record: "SpecimenRecord") -> list[TaxonDelta]:
        deltas: list[TaxonDelta] = []
        taxon = clean_taxon(record.phylum)
        if taxon != self._last_phylum:
            deltas.append(("phylum", taxon))
            self._last_phylum = taxon
            self._clear_class()
        taxon = clean_taxon(record.class_)
        if taxon != self._last_class:
            deltas.append(("class", taxon))
            self._last_class = taxon
            self._clear_subclass()
        taxon = clean_taxon(record.subclass)
        if taxon != self._last_subclass:
            deltas.append(("subclass", taxon))
            self._last_subclass = taxon
            self._clear_order()
        taxon = clean_taxon(record.order)
        if taxon != self._last_order:
            deltas.append(("order", taxon))
            self._last_order = taxon
            self._clear_suborder()
        taxon = clean_taxon(record.suborder)
        if taxon != self._last_suborder:
            deltas.append(("suborder", taxon))
            self._last_suborder = taxon
            self._clear_infraorder()
        taxon = clean_taxon(record.infraorder)
        if taxon != self._last_infraorder:
            deltas.append(("infraorder", taxon))
            self._last_infraorder = taxon
            self._clear_family()
        taxon = clean_taxon(record.family)
        if taxon != self._last_family:
            deltas.append(("family", taxon))
            self._last_family = taxon
            self._clear_subfamily()
        taxon = clean_taxon(record.subfamily)
        if taxon != self._last_subfamily:
            deltas.append(("subfamily", taxon))
            self._last_subfamily = taxon
            self._clear_genus_species()
        taxon = to_clean_genus_species(record.genus, record.species, record.subspecies)
        if taxon != self._last_genus_species:
            deltas.append(("species", taxon))
            self._last_genus_species = taxon
        return deltas


def clean_or_empty_taxon(name: Optional[str]) -> str:
    clean = clean_taxon(name)
    return "" if clean is None else clean


def clean_species(name: str | None, subspecies: str | None) -> Optional[str]:
    if name is None:
        return None
    if name.lower() == "new species":
        name = "n. sp."
    if name == "sp.":
        return None
    if subspecies is not None:
        name += " " + subspecies
    return clean_taxon(name)


def clean_taxon(name: Optional[str]) -> Optional[str]:
    if name is None or name in [".", "0"]:
        return None
    name = name.replace("(?)", "").replace("?", "").replace("  ", " ").strip()
    if "(" in name and ")" not in name:
        name += ")"
    else:
        lower_name = name.lower()
        if lower_name == "new genus":
            name = "new genus"
        elif lower_name.startswith("undescribed"):
            name = "undescribed"
    return name


def to_clean_genus_species(
    genus: str | None, species: str | None, subspecies: str | None
) -> str:
    genus = clean_taxon(genus)
    species = clean_species(species, subspecies)
    if species is not None:
        species = _strip_species_qualifier(species)

    if genus is None:
        if species is None:
            genus_species = NO_TAXON_STR
        else:
            # Sometimes happens outside cleaned-up Texas data.
            genus_species = "(no genus) %s" % species
    else:
        if species is None:
            genus_species = "%s sp." % genus
        else:
            genus_species = "%s %s" % (genus, species)

    return genus_species


def to_taxon_sort_key(record: SpecimenRecord) -> str:

    # Must sort genus & species separately to put no-species designations
    # first, otherwise the 'sp.' gets sorted as if it were a species epithet.

    component_taxa = _to_high_level_component_taxa(record)
    component_taxa.append(clean_or_empty_taxon(record.genus))
    species = clean_species(record.species, record.subspecies)
    component_taxa.append("" if species is None else _strip_species_qualifier(species))

    # Delimit by a character that precedes all other characters, including space,
    # so that empty (None) taxa list before non-empty taxa. Tab precedes all
    # expected characters, while '|' follows all expected characters.

    return "\t".join(component_taxa)


def to_taxon_spec(record: SpecimenRecord) -> str:
    # Not a sortable key because it combines genus and species.
    return " | ".join(_to_component_taxa(record)).replace("|  ", "| - ")


def to_taxon_unique(
    taxon_spec: Union[str, SpecimenRecord]
) -> tuple[str, RestrictionFunc, str]:
    restriction_func = _include_all
    restriction_abbr = ""
    if isinstance(taxon_spec, str):
        assert "|" in taxon_spec, "Not a taxon spec [%s]" % taxon_spec
        bracket_offset = taxon_spec.find("[")
        if bracket_offset > 0:
            assert taxon_spec[-1] == "]", (
                "taxa line missing ending ']' [%s]" % taxon_spec
            )
            restriction_str = taxon_spec[bracket_offset + 1 : -1].strip()
            restriction_func, restriction_abbr = _parse_restriction(restriction_str)
            taxon_spec = taxon_spec[0:bracket_offset].strip()
        component_taxa = taxon_spec.split("|")
    else:
        component_taxa = _to_component_taxa(taxon_spec)
    i = len(component_taxa) - 1
    taxon = component_taxa[i].strip()
    while i > 0 and (taxon == "" or taxon[0] == "-"):
        i -= 1
        taxon = component_taxa[i].strip()

    return (taxon, restriction_func, restriction_abbr)


def _exclude_countries(countries: list[str], record: SpecimenRecord) -> bool:
    if record.country is None:
        return "none" not in countries
    return record.country.lower() not in countries


def _exclude_states(states: list[str], record: SpecimenRecord) -> bool:
    if record.state is None:
        return "none" not in states
    return record.state.lower() not in states


def _include_all(record: SpecimenRecord) -> bool:
    return True


def _include_countries(countries: list[str], record: SpecimenRecord) -> bool:
    if record.country is None:
        return "none" in countries
    return record.country.lower() in countries


def _include_states(states: list[str], record: SpecimenRecord) -> bool:
    if record.state is None:
        return "none" in states
    return record.state.lower() in states


def _parse_restriction(restriction_str: str) -> tuple[RestrictionFunc, str]:
    error_message = "taxa [restriction] must start with 'country:' or 'state:'"
    restriction_str = restriction_str.lower()
    colon_offset = restriction_str.find(":")
    if colon_offset <= 0:
        raise Exception(error_message)
    geo_unit = restriction_str[0:colon_offset].strip()
    remainder_str = restriction_str[colon_offset + 1 :].strip()
    excluded = False
    if remainder_str.startswith("not"):
        excluded = True
        remainder_str = remainder_str[4:]
    raw_geo_names = remainder_str.split(",")
    geo_names: list[str] = []
    for geo_name in raw_geo_names:
        geo_names.append(geo_name.strip().lower())

    if geo_unit == "country" or geo_unit == "countries":
        func = _include_countries
        abbr = ",".join([("none" if n == "none" else n.upper()) for n in geo_names])
        if excluded:
            func = _exclude_countries
            abbr = "NOT " + abbr
        return (partial(func, geo_names), abbr)
    elif geo_unit == "state" or geo_unit == "states":
        func = _include_states
        abbr = ",".join(
            [("none" if s == "none" else States.TO_ABBREV[s]) for s in geo_names]
        )
        if excluded:
            func = _exclude_states
            abbr = "NOT " + abbr
        return (partial(func, geo_names), abbr)
    raise Exception("geographic restriction '%s:' not recognized" % geo_unit)


def _strip_species_qualifier(species: str) -> str:
    if "manuscript name" in species:
        return "n. sp."
    i = 1
    while i < len(species):
        if species[i].isupper():
            if species[i - 1] == "(":
                i -= 1
            species = species[0:i].strip()
            break
        i += 1
    return species


def _to_component_taxa(record: SpecimenRecord) -> list[str]:
    component_taxa = _to_high_level_component_taxa(record)
    component_taxa.append(
        to_clean_genus_species(record.genus, record.species, record.subspecies)
    )
    return component_taxa


def _to_high_level_component_taxa(record: SpecimenRecord) -> list[str]:
    return [
        clean_or_empty_taxon(record.phylum),
        clean_or_empty_taxon(record.class_),
        clean_or_empty_taxon(record.subclass),
        clean_or_empty_taxon(record.order),
        clean_or_empty_taxon(record.suborder),
        clean_or_empty_taxon(record.infraorder),
        clean_or_empty_taxon(record.family),
        clean_or_empty_taxon(record.subfamily),
    ]
