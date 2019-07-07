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

You can change the path using the `CONF_PATH` variable in `n2kparser.py` to use the configuration JSON file.

### Configuration File

    $ n2kparser

Many things are currently hardcoded in the script like serial port and udp port for InfluxDB.

The PGNs are configuration via the `conf.json` file in the repository.

A snippet of the PGN is as follows:

```
"pgnConfigs": {
          "127250": [
            {
              "code": "vessel-heading",
              "label": "Vessel Heading",
              "fieldLabel": "Heading",
              "samplingrate": 500
            },
            {
              "code": "vessel-hdg-dev",
              "label": "Vessel Heading Deviation",
              "fieldLabel": "Deviation",
              "samplingrate": 500
            },
            {
             "code": "vessel-hdg-var",
             "label": "Vessel Heading Variation",
             "fieldLabel": "Variation",
             "samplingrate": 500
            }
          ]
}
```
* A single PGN can measure a different values
* `code`: here is the name of the measurement in InfluxDB where the data will be stored
* `label`: is a human-readable name of the measurement. It does not get used in the code but only for understanding
* `fieldLabel`: is the key in the sub-JSON of the incoming data whose value needs to be stored in InfluxDB
* `samplingrate`: is also for understanding only and is not used within the code

## Maintainer

* Shantanoo Desai (des@biba.uni-bremen.de)