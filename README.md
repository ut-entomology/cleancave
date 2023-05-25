# cleancave

Python tools for cleaning, normalizing, and reporting on James Reddell's cave data. Does not include James' source data. It provides the following reports:

- A list of all agents (collectors and determiners) mentioned, organized by variants under the longest matching name. It also guesses at matching typos by phonetic similarity.
- A list of all latitude/longitude coordinates.
- Dictionary lists of the various distinct terms used by the different columns.
- Labels suitable for printing and depositing with the specimens in vials. The labels maximize the available space by tracking letter point widths, combining lines while keeping them distinguishable, and abbreviating names when necessary.
- Problem reports listing problems and warning found in the data.
- A CSV file output providing sample data for TSS.
- A CSV file output suitable for uploading to Specify.
- A list of all taxa.
- A list of duplicate catalog numbers by taxa.
- A list of records for each duplicate catalog number.
- A list of specimen counts by taxa.
- A list of all localities organized by county.

Reports can be restricted to just cave data (marked Biospeleology), to Texas cave data, and to records for particular taxa. In the latter case, the taxa can be restricted by locality and is used for printing labels just for particular jars of specimens.

All reports require that you name a source CSV file, which is a CSV export of James Reddell's Microsoft Access MDB. The reports are based on this data.

Reports may require the presence of a file called `declared-names.txt`, which maps ambiguous or incomplete agent names to the names that are to appear in reports.

The tool is not expected to have value once all of James' data has been imported into the DB and printed to specimen labels.

## Installation

```
python3 -m venv cleancave
cd cleancave
# set PYTHONPATH to the current directory (e.g. source ./exec/setpath)
source ./bin/activate
./exec/install-pips
export PYTHONPATH="${PYTHONPATH}:/path/to/project"
```

## Usage

Run the following to see command line options:

```
python3 src/reporter/main.py
```

### Generating a Problem Report

The following command generates a problem report for the provided CSV file, restricting the report to just the Biospeleological collection. This is the report I run for James when he wants all problems with the collection:

```
python3 src/reporter/main.py path/to/csv-file.csv -c -rP > problem-report.txt
```

When James wants just a report of problems with specimens in particular jars, I add the `-x` switch to point to a file containing a list of taxa found in those jars. You'll find examples of these lists in the `jars` directory. Here is an example:

```
python3 src/reporter/main.py path/to/csv-file.csv -c -rP -xjars/jars-2022-05-07.txt > problem-report.txt
```

The problem reports do not show how the program maps any new agent names it finds. I usually also check them for problems before sending James each next problem report.

### Generating Agent Names

Whenever James asks for a problem report, I also check for the effects of any new names he's added. To do this, first run the following command to get a list of all agent names:

```
python3 src/reporter/main.py path/to/csv-file.csv -c -rA > agents.txt
```

Then compare this list with `data/agents.txt`. I use the diffing facility of BBedit. Examine every change.

If the change is clearly a new variant of an existing name that the program was unable to automatically assign to the fuller name, edit the `data/declared-names.txt` file to declare the full name.

If the change is clearly a newly introduced typo, edit the `data/declared-names.txt` file to assert how the typo should be corrected.

If the change is ambiguusly a typo, ask James whether the name is correct, also showing him the similar reported names.

If the change is clearly a newly introduced name, nothing needs to be done.

### Generating Labels

Labels can be generated for all of the data at once, but they're usually generated for each set of jars that James has completed verifying. This command generates them for a particular set of jars:

```
python3 src/reporter/main.py path/to/csv-file.csv -rL -p -c -xjars/jars-2022-05-07.txt > labels.txt
```

The `-p` says to produce a printable version other labels. You can leave that out if you want a more readable version that also reports problems.

After printing the labels, I open an existing labels Word document, highlight everything, press delete, and then insert the new set of labels. I've found that, on my Mac at least, than any other procedure can change the layout.

I then go through the document making sure that labels properly line up with page boundaries. On rare occassions, a label may end up with too many lines. The generator does its best to separately group 4-line label, 5-line labels, and 6-line labels, but on rare occassions it doesn't work. You'll need to manually edit or move these few labels.
