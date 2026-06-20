# NASA battery data

Expected source: NASA Prognostics Center of Excellence Battery Data Set.

Place downloaded files in this directory. They are intentionally ignored by Git. Record the
download date, source URL, archive checksum, and extraction notes in a local data manifest
when the dataset is introduced.

Official repository:
https://www.nasa.gov/intelligent-systems-division/discovery-and-systems-health/pcoe/pcoe-data-set-repository/

## Phase 7 canonical experiment

- Archive: `5. Battery Data Set.zip` (raw archive is Git-ignored)
- SHA-256: `82302a7db4fc1b34e0b6676326610438d43b816bdf11a69d1d012a464ef2f92e`
- Experiment group: `1. BatteryAgingARC-FY08Q4.zip`
- Cells: B0005, B0006, B0007, B0018
- NASA EOL criterion: capacity fade from 2.0 Ah to 1.4 Ah
- Citation: B. Saha and K. Goebel (2007), “Battery Data Set,” NASA Prognostics
  Data Repository, NASA Ames Research Center, Moffett Field, CA.

Download and extraction:

```bash
curl -L 'https://phm-datasets.s3.amazonaws.com/NASA/5.+Battery+Data+Set.zip' \
  -o data/raw/nasa/nasa-battery-data-set.zip
unzip data/raw/nasa/nasa-battery-data-set.zip \
  '5. Battery Data Set/1. BatteryAgingARC-FY08Q4.zip' -d data/raw/nasa
unzip 'data/raw/nasa/5. Battery Data Set/1. BatteryAgingARC-FY08Q4.zip' \
  -d data/raw/nasa/battery-aging-fy08q4
```
