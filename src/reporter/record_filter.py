from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.reporter.specimen_record import SpecimenRecord
from abc import ABC, abstractmethod

from src.reporter.taxa import *


class RecordFilter(ABC):
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def test(self, record: "SpecimenRecord") -> bool:
        pass


class AllRecordsFilter(RecordFilter):
    def __init__(self):
        super().__init__("Both Cave and Non-Cave Records")

    def test(self, record: "SpecimenRecord") -> bool:
        return True


class CaveRecordFilter(RecordFilter):
    def __init__(self):
        super().__init__("Cave Records")

    def test(self, record: "SpecimenRecord") -> bool:
        return "Biospeleology" in record.collections


class CaveFamilyRecordFilter(RecordFilter):
    def __init__(self, family_name: str):
        super().__init__("Cave Records in Family %s" % family_name)
        self._lower_family_name = family_name.lower()

    def test(self, record: "SpecimenRecord") -> bool:
        return (
            "Biospeleology" in record.collections
            and record.family is not None
            and record.family.lower() == self._lower_family_name
        )


class CompoundRecordFilter(RecordFilter):
    def __init__(self, record_filters: list[RecordFilter]):
        super().__init__(" & ".join([f.name for f in record_filters]))
        self._filters = record_filters

    def test(self, record: "SpecimenRecord") -> bool:
        for filter in self._filters:
            if not filter.test(record):
                return False
        return True


class ProofedFilter(RecordFilter):
    def __init__(self, value: str):
        super().__init__("Designated Proofed Records")
        self._value: str = value

    def test(self, record: "SpecimenRecord") -> bool:
        return record.proofed == self._value


class StrictlyTexasCaveRecordFilter(RecordFilter):
    def __init__(self):
        super().__init__("Strictly Texas Cave Records")

    def test(self, record: "SpecimenRecord") -> bool:
        return (
            record.state is not None
            and record.state.startswith("Texas")
            and "Biospeleology" in record.collections
        )


class TaxaFilter(RecordFilter):
    def __init__(self, lines: list[str]):
        super().__init__("Selected Taxa")
        self._restriction_funcs: dict[str, list[RestrictionFunc]] = {}
        self._excluded_numbers: list[int] = []
        self._included_numbers: list[int] = []

        for line in lines:
            line = line.strip()
            if line != "":
                first_char = line[0]
                if first_char == "#":
                    pass  # ignore comment lines
                elif first_char == "-":
                    self._excluded_numbers += self._to_numbers(line)
                elif first_char == "+":
                    self._included_numbers += self._to_numbers(line)
                else:
                    taxon_unique, restriction_func, _ = to_taxon_unique(line)
                    if taxon_unique in self._restriction_funcs:
                        self._restriction_funcs[taxon_unique].append(restriction_func)
                    else:
                        self._restriction_funcs[taxon_unique] = [restriction_func]

    def test(self, record: "SpecimenRecord") -> bool:
        if record.catalog_number in self._included_numbers:
            return True
        if -1 * record.id in self._included_numbers:
            return True
        if (
            record.catalog_number not in self._excluded_numbers
            and -1 * record.id not in self._excluded_numbers
        ):
            try:
                for restriction_func in self._restriction_funcs[record.taxon_unique]:
                    if restriction_func(record):
                        return True
            except KeyError:
                pass
        return False

    def _to_numbers(self, line: str) -> list[int]:
        numbers: list[int] = []
        number_strings = line[1:].split(",")
        for number_str in number_strings:
            number_str = number_str.strip()
            assert number_str != "", "missing number in taxa filter file"
            if number_str[0] == "(":
                assert number_str[-1] == ")", "missing ')' in taxa filter file"
                numbers.append(-1 * int(number_str[1:-1]))
            else:
                numbers.append(int(number_str))
        return numbers


class TexasCaveRecordFilter(RecordFilter):
    def __init__(self):
        super().__init__("Jars Containing Texas Cave Records")

    def test(self, record: "SpecimenRecord") -> bool:
        if "Biospeleology" not in record.collections:
            return False
        if record.state is None:
            return False
        if record.state.startswith("Texas"):
            return True
        if record.phylum is not None and record.phylum.startswith("Nemata"):
            return True
        if record.order is not None and (
            record.order.startswith("Tricladida")
            or record.order.startswith("Symphypleona")
            or record.order.startswith("Odonata ")
            and (
                record.family is None
                or record.family.startswith("Aeschnidae")
                or record.family.startswith("Coenagrionidae")
                or record.family.startswith("Corduleragasteridae")
                or record.family.startswith("Libellulidae")
                or record.family.startswith("Megapagrionidae")
            )
        ):
            return True
        if record.class_ is not None and record.class_.startswith("Hirudinea"):
            return True
        if record.family is not None and record.family.startswith("Parajulidae"):
            return True
        return False


class NonCaveRecordsFilter(RecordFilter):
    def __init__(self):
        super().__init__("Non-Cave Records")

    def test(self, record: "SpecimenRecord") -> bool:
        return "Biospeleology" not in record.collections or len(record.collections) > 1
