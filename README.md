# cleancave

Python tools for cleaning, normalizing, and reporting on James Reddell's cave data. Does not include James' source data. Not likely to be of value after importing James' data into Specify.

## Installation

```
python3 -m venv cleancave
cd cleancave
# set PYTHONPATH to the current directory (e.g. source ./exec/setpath)
source ./bin/activate
./exec/install-pips
```

## Usage

Run the following to see command line options:

```
python3 src/reporter/main.py
```

Here is an example usage, pulling the raw cave data from outside the repo:

```
python3 src/reporter/main.py ../ut-cave-data/data/Invertebrata.csv -c -rP > out.txt
```
