# Visa Automatic synthetic regression fixtures

The CSV header row is copied from the **uploaded 235-column Google Forms export**. Each response is new, fictitious test data; none of the original applicant rows are present. Fixtures with deliberately invalid headers/row widths are named `csv-unsupported-header.csv` and `csv-malformed-row.csv`.

To use, copy contents into the repo `bugfix-fixtures/` directory. Preserve your existing `expected-results.md` if it already contains your full acceptance specification; use this package's `expected-results.md` as an additional fixture expectations reference or merge its test table manually.

Every CSV is UTF-8 with BOM and uses standard CSV quoting for multiline Portuguese headings. Do not open and re-save through spreadsheet apps unless you confirm the headers are identical afterwards.
