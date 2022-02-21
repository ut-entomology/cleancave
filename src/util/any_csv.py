from typing import Callable
import csv

RowReceiver = Callable[[dict[str, str]], bool]


def load_csv(filename: str, receive_row: RowReceiver) -> None:
    with open(filename) as raw_file:
        first_line = raw_file.readline()
    with open(filename, newline="", encoding="utf-8-sig") as csv_file:
        if first_line[0] == "'":
            reader = csv.DictReader(csv_file, delimiter=",", quotechar="'")
        elif first_line[0] == '"':
            reader = csv.DictReader(csv_file, delimiter=",", quotechar='"')
        else:
            reader = csv.DictReader(csv_file, dialect="excel")
        for row in reader:
            if not receive_row(row):
                break  # reached end of valid records
