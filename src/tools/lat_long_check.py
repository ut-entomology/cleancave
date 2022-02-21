from typing import Optional
from decimal import Decimal
import os
import csv

COL_ID = 0
COL_CAT = 1
COL_LAT = 15
COL_LONG = 16
# COL_ID = 0
# COL_CAT = 2
# COL_LAT = 22
# COL_LONG = 23


class LatLongRecord:
    def __init__(self, row: list[str]):
        self.id = int(row[0])
        self.cat_num = None if row[1] == "None" else int(row[1])
        self.lat = None if row[2] == "None" else Decimal(row[2])
        self.long = None if row[3] == "None" else Decimal(row[3])


def _expand_filename(filename: str) -> str:
    if filename[0] == ".":
        return os.path.join(os.path.dirname(__file__), filename)
    return filename


class LatLongCheck:
    def __init__(self):
        self.lat_long_by_id: dict[int, LatLongRecord] = {}
        self.lat_long_by_cat_num: dict[Optional[int], LatLongRecord] = {}

        lat_long_filename = _expand_filename("lat_long.csv")
        specimens_filename = _expand_filename("data/Invertebrata_2020_09_05.csv")
        # specimens_filename = _expand_filename("data/Invertebrata_2021_07_30.csv")

        with open(lat_long_filename, newline="", encoding="utf-8-sig") as csv_file:
            reader = csv.reader(csv_file)
            for row in reader:
                record = LatLongRecord(row)
                self.lat_long_by_id[record.id] = record
                self.lat_long_by_cat_num[record.cat_num] = record

        with open(specimens_filename, newline="", encoding="utf-8-sig") as csv_file:
            reader = csv.reader(csv_file)
            for row in reader:
                if row[COL_ID] == "ID":
                    continue
                id = int(row[COL_ID])

                cat_num = None if row[COL_CAT] == "" else int(row[COL_CAT])
                if cat_num is None:
                    continue

                lat = row[COL_LAT].strip()
                lat = "None" if lat == "" else lat
                long = row[COL_LONG].strip()
                long = "None" if long == "" else long

                lat_long = self.lat_long_by_id[id]
                if cat_num != lat_long.cat_num:
                    self.error(
                        id,
                        cat_num,
                        "does not have expected cat num %s" % str(lat_long.cat_num),
                    )
                if str(lat_long.lat) not in lat:
                    self.error(
                        id,
                        cat_num,
                        "lat '%s' does not contain '%s'" % (lat, str(lat_long.lat)),
                    )
                if str(lat_long.long) not in long:
                    self.error(
                        id,
                        cat_num,
                        "long '%s' does not contain '%s'" % (long, str(lat_long.long)),
                    )

    def error(self, id: int, cat_num: Optional[int], message: str) -> None:
        print("* ID/Cat. No. %d/%s: %s" % (id, str(cat_num), message))


if __name__ == "__main__":
    LatLongCheck()
