import csv

import src.util.args as args


class GbifTaxaErrors:

    UNRECOGNIZED_RANK = "*"
    TO_GBIF_RANK = {
        "(phyla)": "PHYLUM",
        "(classes)": "CLASS",
        "(subclasses)": UNRECOGNIZED_RANK,
        "(orders)": "ORDER",
        "(suborders)": UNRECOGNIZED_RANK,
        "(infraorders)": UNRECOGNIZED_RANK,
        "(families)": "FAMILY",
        "(subfamilies)": UNRECOGNIZED_RANK,
        "(genera)": "GENUS",
    }
    TO_RANK_NAME = {
        "(phyla)": "a phylum",
        "(classes)": "a class",
        "(subclasses)": "a subclass",
        "(orders)": "an order",
        "(suborders)": "a suborder",
        "(infraorders)": "an infraorder",
        "(families)": "a family",
        "(subfamilies)": "a subfamily",
        "(genera)": "a genus",
    }

    def __init__(self):
        self._csv_filename: str
        self._taxa_errors: list[TaxonError] = []

        options: args.OptionsDict = {
            0: self._parse_csv_filename,
            None: self._parse_no_arguments,
        }
        try:
            args.parse_args(options)
        except args.ArgException as e:
            if e.message:
                print(e.message)
            print("Please provide the filename of the GBIF CSV file.")

    def run(self) -> None:
        print("\n==== Problems with and corrections to taxa ====")

        with open(self._csv_filename, newline="", encoding="utf-8-sig") as csv_file:
            reader = csv.DictReader(csv_file)
            expected_rank: str = ""

            for row in reader:
                verbatimName = row["verbatimScientificName"]
                if verbatimName in self.TO_GBIF_RANK:
                    expected_rank = verbatimName
                elif (
                    row["matchType"] != "EXACT"
                    or row["rank"] != self.TO_GBIF_RANK[expected_rank]
                ):
                    self._taxa_errors.append(TaxonError(row, expected_rank))

        print("\n---- Taxa GBIF Did Not Recognize ----")

        current_rank: str = ""
        recognized_rank = True
        for error in self._taxa_errors:
            if current_rank != error.expected_rank:
                current_rank = error.expected_rank
                self._print_rank_header("Unrecognized", current_rank)
                recognized_rank = (
                    self.TO_GBIF_RANK[current_rank] != self.UNRECOGNIZED_RANK
                )
                if not recognized_rank:
                    print("  (GBIF does not seem to recognize this rank)\n")
            if not recognized_rank:
                if not error.exact:
                    print("  %s" % error.incorrect_name)
            elif not error.matched:
                print("  %s" % error.incorrect_name)

        print("\n---- GBIF-Suggested Taxa Corrections ----")
        print("\nTypos are indented and follow a slash ('/').")

        for rank in self.TO_GBIF_RANK:
            self._print_corrections(rank)

    def _parse_csv_filename(self, arg: str) -> None:
        self._csv_filename = args.expand_filename(arg)

    def _parse_no_arguments(self, arg: str) -> None:
        raise args.ArgException()

    def _print_corrections(self, for_rank: str) -> None:
        valid_names: dict[str, list[TaxonError]] = {}
        self._print_rank_header("Corrected", for_rank)
        recognized_rank = self.TO_GBIF_RANK[for_rank] != self.UNRECOGNIZED_RANK
        count = 0

        current_rank = ""
        for error in self._taxa_errors:
            if current_rank != error.expected_rank:
                current_rank = error.expected_rank
            if current_rank == for_rank and error.matched:
                if error.suggested_name in valid_names:
                    valid_names[error.suggested_name].append(error)
                else:
                    valid_names[error.suggested_name] = [error]

        for valid_name in sorted(list(valid_names)):
            printed_valid_name = False
            errors = valid_names[valid_name]
            for error in errors:
                notes: list[str] = []
                if error.actual_rank != self.TO_GBIF_RANK[for_rank]:
                    notes.append(
                        "%s not %s" % (error.actual_rank, self.TO_RANK_NAME[for_rank])
                    )
                if error.suggested_name_status != "ACCEPTED":
                    if error.suggested_name_status == "SYNONYM":
                        notes.append("SYNONYM for %s" % error.accepted_name)
                if (not recognized_rank and error.exact) or (
                    recognized_rank and error.incorrect_name != valid_name
                ):
                    if not printed_valid_name:
                        print(
                            "%s%s"
                            % (
                                valid_name,
                                "" if not notes else " (%s)" % "; ".join(notes),
                            )
                        )
                        printed_valid_name = True
                    if error.incorrect_name != valid_name:
                        print("  /%s" % error.incorrect_name)
                    count += 1

        if count == 0:
            print("(none)")

    def _print_rank_header(self, context: str, my_rank: str) -> None:
        print("\n** %s %s **\n" % (context, my_rank[1:-1].capitalize()))


class TaxonError:
    def __init__(self, row: dict[str, str], expected_rank: str):
        self.incorrect_name = row["verbatimScientificName"]
        self.exact = row["matchType"] == "EXACT"
        self.matched = row["matchType"] != "HIGHERRANK"
        self.suggested_name = row["scientificName"]
        space_offset = self.suggested_name.find(" ")
        if space_offset > 0:
            self.suggested_name = self.suggested_name[0:space_offset]
        self.suggested_name_status = row["status"]
        self.expected_rank = expected_rank
        self.actual_rank = row["rank"]

        if row["species"] != "":
            self.accepted_name = row["species"]
        elif row["genus"] != "":
            self.accepted_name = row["genus"]
        elif row["family"] != "":
            self.accepted_name = row["family"]
        elif row["order"] != "":
            self.accepted_name = row["order"]
        elif row["class"] != "":
            self.accepted_name = row["class"]
        elif row["phylum"] != "":
            self.accepted_name = row["phylum"]


if __name__ == "__main__":
    GbifTaxaErrors().run()
