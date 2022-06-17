from __future__ import annotations
from decimal import Decimal
from enum import Enum
import sys
import csv

from src.reporter.james_table import *
from src.reporter.record_filter import StrictlyTexasCaveRecordFilter
from src.reporter.reports.report import Report

# TODO: designate non-wet specimens, when James gets me the info
# TODO: should I store the property owner somewhere?

MAX_COLLECTORS = 8  # max collectors that workbench allows
MAX_DETERMINERS = 1  # max determiners that workbench allows


class MiscNotesType(Enum):
    IGNORED = 0
    ATTRIBUTE = 1
    HABITAT = 2
    DETERMINATION = 3
    STAGE = 4
    PREP_TYPE = 5


class SpecifyWorkbenchReport(Report):
    def __init__(self, table: JamesTable):
        super().__init__(table, StrictlyTexasCaveRecordFilter())
        self._misc_notes_type = MiscNotesType.IGNORED
        table.revise_names(unify_names_by_sound=True, merge_with_reference_names=True)

    def show(self) -> None:
        headers = [
            "Cataloger First Name",
            "Cataloger Last Name",
            "Cataloged Date",
            "Accession Accession Number",
            "Catalog Number",
            "Phylum1",
            "Class1",
            # "Subclass", -- not in Specify
            "Order1",  # valued
            # "Suborder", -- not in Specify
            # "Infraorder", -- not in Specify
            "Family1",  # valued
            "Subfamily1",
            "Genus1",
            "Species1",  # in specify as Species
            "Subspecies1",
            "Author1",
            "Country",
            "State",
            "County",
            "Locality Name",
            "Latitude",
            "Longitude",
            "CI Locality and Habitat Notes",
            "Start Date",
            "End Date",
            "CI Verbatim Date",
            "Prep Type",  # "Wet" if not already in Specify and no "pinned" in misc notes
            "Count 1",
            "Determined Date",
            "Determination Remarks",
            "Type Status",
            "CoA Sex",
            "CoA Stage",
            "CoA Remarks",
            "Storage Location",  # "Biospeleology"
        ]
        i = 1
        while i <= MAX_COLLECTORS:
            headers.append("Collector First Name %d" % i)
            headers.append("Collector Last Name %d" % i)
            i += 1
        i = 1
        while i <= MAX_DETERMINERS:
            headers.append("Determiner First Name %d" % i)
            headers.append("Determiner Last Name %d" % i)
            i += 1
        writer = csv.DictWriter(
            sys.stdout, fieldnames=headers, dialect="excel", lineterminator="\n"
        )
        writer.writeheader()

        for record in self._filtered_records():
            if "Biospeleology" not in record.collections:
                raise Exception(
                    "Can't upload non-Biospeleology record %d" % record.catalog_number
                )

            self._parse_misc_notes(record)
            row: dict[str, str] = {
                "Cataloger First Name": "James R.",
                "Cataloger Last Name": "Reddell",
                "Cataloged Date": "00/00/2022",
                "Accession Accession Number": "002022c",
                "Catalog Number": _to_column(self._pull_catalog_number(record)),
                "Phylum1": _to_column(record.phylum),
                "Class1": _to_column(record.class_),
                "Order1": _to_column(record.order),
                "Family1": _to_column(record.family),
                "Subfamily1": _to_column(record.subfamily),
                "Genus1": _to_column(JamesTable.drop_parens(record.genus)),
                "Species1": _to_column(self._pull_species(record.species)),
                "Author1": _to_column(record.authors),
                "Subspecies1": _to_column(JamesTable.drop_parens(record.subspecies)),
                "Country": _to_column(self._pull_country(record)),
                "State": _to_column(record.state),
                "County": _to_column(self._pull_county(record)),
                "Locality Name": _to_column(self._get_safe_locality_name(record)),
                "Latitude": _to_column(
                    self._get_safe_coordinate(record, record.latitude)
                ),
                "Longitude": _to_column(
                    self._get_safe_coordinate(record, record.longitude)
                ),
                "CI Locality and Habitat Notes": _to_column(
                    self._pull_locality_notes(record)
                ),
                # "Owner": _to_column(record.owner), -- TODO: need a decision
                "Start Date": _to_column(self._pull_start_date(record)),
                "End Date": _to_column(self._pull_end_date(record)),
                "CI Verbatim Date": record.raw_date_time,
                "Prep Type": self._pull_prep_type(record),
                "Count 1": _to_column(record.specimen_count),
                "Determined Date": _to_column(self._pull_determined_date(record)),
                "Determination Remarks": _to_column(
                    self._pull_determination_remarks(record)
                ),
                "Type Status": _to_column(self._pull_type_status(record.type_status)),
                "CoA Sex": _to_column(self._pull_sex(record)),
                "CoA Stage": _to_column(self._pull_stage(record)),
                "CoA Remarks": _to_column(
                    self._pull_collection_object_attribute_remarks(record)
                ),
                "Storage Location": "Biospeleology",
            }

            collectorNumber = 1
            if record.collectors is not None:
                for collector in record.collectors:
                    primary = collector.get_master_copy().primary
                    assert primary is not None
                    if collectorNumber > MAX_COLLECTORS:
                        raise Exception(
                            "More than 8 collectors in Cat. #%d" % record.catalog_number
                        )
                    _add_agent(
                        "Collector",
                        row,
                        collectorNumber,
                        primary.initial_names,
                        primary.last_name,
                        primary.name_suffix,
                    )
                    collectorNumber += 1
            while collectorNumber <= MAX_COLLECTORS:
                _add_agent("Collector", row, collectorNumber, "", "", "")
                collectorNumber += 1

            determinerNumber = 1
            if (
                record.identifier_year is not None
                and record.identifier_year.determiners is not None
            ):
                determiners = record.identifier_year.determiners
                while (
                    determinerNumber <= len(determiners)
                    and determinerNumber <= MAX_DETERMINERS
                ):
                    primary = (
                        determiners[determinerNumber - 1].get_master_copy().primary
                    )
                    assert primary is not None
                    _add_agent(
                        "Determiner",
                        row,
                        determinerNumber,
                        primary.initial_names,
                        primary.last_name,
                        primary.name_suffix,
                    )
                    determinerNumber += 1
            while determinerNumber <= MAX_DETERMINERS:
                _add_agent("Determiner", row, determinerNumber, "", "", "")
                determinerNumber += 1

            if len(row) != len(headers):
                raise Exception(
                    "Incorrect columnn count: HEADER ROWS %s\nRECORD ROWS %s"
                    % (headers, list(row.keys()))
                )
            writer.writerow(row)

    def _parse_misc_notes(self, record: SpecimenRecord):
        self._misc_notes_type = MiscNotesType.IGNORED
        if record.misc_notes is None or "collector" in record.misc_notes:
            return
        record.misc_notes = record.misc_notes.replace("Speciemen", "specimen")

        lowercase_notes = record.misc_notes.lower().strip()
        if lowercase_notes in [
            "head only",
            "specimen too fragmented for id",
            "specimen discarded",
        ]:
            self._misc_notes_type = MiscNotesType.ATTRIBUTE
        elif lowercase_notes.startswith("pinned"):
            self._misc_notes_type = MiscNotesType.PREP_TYPE
        elif lowercase_notes.startswith("zone"):
            self._misc_notes_type = MiscNotesType.HABITAT
        elif lowercase_notes == "larva":
            self._misc_notes_type = MiscNotesType.STAGE
        else:
            self._misc_notes_type = MiscNotesType.DETERMINATION

    def _pull_catalog_number(self, record: SpecimenRecord) -> Optional[str]:
        if record.catalog_number is None:
            return None
        if record.catalog_number < 200000:
            return "TMM" + str(record.catalog_number)
        return str(record.catalog_number)

    def _pull_collection_object_attribute_remarks(
        self, record: SpecimenRecord
    ) -> Optional[str]:
        total = record.specimen_count
        females = record.females if record.females is not None else 0
        males = record.males if record.males is not None else 0
        immatures = record.immatures if record.immatures is not None else 0
        stage_notes: list[str] = []
        if females > 0 and females < total:
            stage_notes.append("%d female%s" % (females, "s" if females > 1 else ""))
        if males > 0 and males < total:
            stage_notes.append("%d male%s" % (males, "s" if males > 1 else ""))
        if immatures > 0 and immatures < total:
            stage_notes.append(
                "%d immature%s" % (immatures, "s" if immatures > 1 else "")
            )
        remarks: Optional[str] = ", ".join(stage_notes)
        if self._misc_notes_type == MiscNotesType.ATTRIBUTE:
            remarks = self._append_notes(remarks, record.misc_notes)
        return remarks if remarks != "" else None

    def _pull_country(self, record: SpecimenRecord) -> Optional[str]:
        if record.country == "USA":
            return "United States"
        return record.country

    def _pull_county(self, record: SpecimenRecord) -> Optional[str]:
        if record.country == "USA" and record.county is not None:
            if not record.county.endswith("County"):
                return record.county + " County"
        return record.county

    def _pull_start_date(self, record: SpecimenRecord) -> str | None:
        if record.date_time is None:
            return None
        return self._pull_date(record.date_time.start_date)

    def _pull_end_date(self, record: SpecimenRecord) -> str | None:
        start_date = self._pull_start_date(record)
        if record.date_time is None:
            return None
        if record.date_time.end_date is None:
            return start_date
        return self._pull_date(record.date_time.end_date)

    def _pull_date(self, partial_date: Optional[PartialDate]) -> Optional[str]:
        return partial_date.to_MMDDYYYY() if partial_date is not None else None

    def _pull_determination_remarks(self, record: SpecimenRecord) -> Optional[str]:
        remarks = ""
        if record.species is not None and record.species.startswith("sp. prob."):
            remarks = record.species
        if self._misc_notes_type == MiscNotesType.DETERMINATION:
            remarks = self._append_notes(remarks, record.misc_notes)
        if record.identifier_year is not None and record.identifier_year.determiners:
            determiners = record.identifier_year.determiners
            i = MAX_DETERMINERS
            while i < len(determiners):
                determiner = determiners[i].get_master_copy().primary
                assert determiner is not None
                remarks = self._append_notes(
                    remarks, "det. also by %s" % determiner.get_full_name()
                )
                i += 1
        return remarks if remarks != "" else None

    def _pull_determined_date(self, record: SpecimenRecord) -> Optional[str]:
        if record.identifier_year is None or record.identifier_year.year is None:
            return None
        return "00/00/" + str(record.identifier_year.year)

    def _pull_locality_notes(self, record: SpecimenRecord) -> Optional[str]:
        notes: Optional[str] = record.microhabitat
        if self._misc_notes_type == MiscNotesType.HABITAT:
            notes = self._append_notes(notes, record.misc_notes)
        if record.is_sensitive:
            notes = self._append_notes(notes, "sensitive coordinates withheld")
        end_date = self._pull_end_date(record)
        if end_date is not None and end_date != self._pull_start_date(record):
            notes = self._append_notes(
                notes,
                "*end date " + record.date_time.end_date.to_YYYYMMDD(),  # type: ignore
            )
        return notes

    def _pull_prep_type(self, record: SpecimenRecord) -> str:
        if self._misc_notes_type == MiscNotesType.PREP_TYPE:
            if record.misc_notes.lower().startswith("pinned"):  # type: ignore
                return "Pinned"
        return "Wet"

    def _pull_sex(self, record: SpecimenRecord) -> Optional[str]:
        females = record.females if record.females is not None else 0
        males = record.males if record.males is not None else 0
        if record.order is not None and record.order.startswith("Araneae"):
            if record.genus is not None and record.genus.startswith("Cicurina"):
                if females > 0:
                    return "female"
            if males > 0:
                return "male"
        if males + females > 0:
            if females >= males:
                return "female"
            return "male"
        return None

    def _pull_species(self, james_species: Optional[str]) -> Optional[str]:
        if james_species is None:
            return None
        species = JamesTable.drop_parens(james_species)
        if (
            species is None
            or species == "sp."
            or species is not None
            and species.startswith("sp. prob.")
        ):
            return None
        return species

    def _pull_stage(self, record: SpecimenRecord) -> Optional[str]:
        females = record.females if record.females is not None else 0
        males = record.males if record.males is not None else 0
        immatures = record.immatures if record.immatures is not None else 0
        if self._misc_notes_type == MiscNotesType.STAGE:
            return record.misc_notes
        if males + females > 0:
            return "adult"
        if immatures > 0:
            return "immature"
        return None

    def _pull_type_status(self, type_status: Optional[str]) -> Optional[str]:
        if type_status is None:
            return None
        tmmOffset = type_status.find("TMM")
        if tmmOffset > 0:
            startOffset = type_status.rfind(")", 0, tmmOffset)
            if startOffset < 0:
                startOffset = 0
            else:
                startOffset += 1
            endOffset = type_status.find("(", startOffset, tmmOffset)
            if endOffset < 0:
                raise Exception("Invalid type status format '%s'" % type_status)
            type_status = type_status[startOffset:endOffset].strip()
        if type_status[-1] == "S":
            type_status = type_status[0:-1]
        return type_status.lower()


def _add_agent(
    agent_type: str,
    row: dict[str, str],
    field_number: int,
    initial_names: Optional[str],
    last_name: str,
    suffix: Optional[str],
):
    row["%s First Name %d" % (agent_type, field_number)] = _to_column(initial_names)
    if suffix == "":
        suffix = None
    row["%s Last Name %d" % (agent_type, field_number)] = last_name + (
        ", " + suffix if suffix is not None else ""
    )


def _to_column(s: Optional[str | int | Decimal]) -> str:
    return "" if s is None else str(s)
