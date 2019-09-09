# n2kparser
Python3.x CLI to parser incoming JSON data from `actisense-serial` and `analyzer` binaries from [CANBOAT](https://github.com/canboat/canboat) and store
values into InfluxDB using UDP

## Installation and Dependencies
### Installation

Install the `CANBOAT` repository binaries in order to use `actisense-serial` and `analyzer` binaries.

Clone the repository and then install the code:

    pip install .

### Development

develop using `venv`:

    python -m venv venv

activate the virtual environment and then

    pip install -e .


## Usage
Path to the `conf.json` (see File in repository for Structure) can be set via argument `--path`

### Configuration File

    $ n2kparser --path ./conf.json

The PGNs are configurable via the `conf.json` file in the repository. Follow the structure mentioned in the file.

A snippet of the PGN is as follows:

```
"pgnConfigs": {
      "130311": {
        "for": "Environmental Parameters",
        "fieldLabels": [
          "Temperature",
          "Atmospheric Pressure"
        ]
      },
      "127245": {
        "for": "Rudder",
        "fieldLabels": [
          "Direction Order",
          "Position"
        ]
      },
      "127501": {
        "for": "Binary Switch Bank",
        "fromSource": 1,
        "fieldLabels": [
          "Indicator1",
          "Indicator2"
        ]
      }
}
```
__NOTE__: A single PGN can measure a different values
* `for` key is for Human-Readable Description for the PGN. (Optional)
* `fieldLabels` key is an array of all the relevant keys for which the values should be saved
  to InfluxDB. Example, for Rudder (same PGN) one can choose to store only `Position` value or
  both `Direction Order` and `Position` (Required)
* `fromSource` keys is a filter key to store information from only distinct source (e.g. Engine, Rudder).
  If there are two Engines/Rudders and the value of Engine/Rudder 1 is to be stored then use `fromSource: 1`.
  (Optional)

## Maintainer

* Shantanoo Desai (des@biba.uni-bremen.de)