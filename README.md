# ADS-B Logger

This is a logger for ADS-B receivers that stores all received flights and other data.

## Key Features

- Logging of all flights detected by your ADS-B receiver, including flight number, registration, aircraft type, and timestamp of first contact
- Logging of record values such as highest altitude, highest speed, longest distance from receiver
- Storage in a [SQLite](https://www.sqlite.org/index.html) database that can be further processed, e.g., by [Grafana](https://grafana.com) for visualization
- Can be run as Linux systemd service

## More Details

### Working Principle

- As prerequisite for the ADS-B Logger, an ADS-B receiver is necessary that processes and broadcasts received flight information on the local network via JSON format (`aircraft.json` file).
The ADS-B Logger has been developed for [readsb](https://github.com/wiedehopf/readsb), but may work with other decoders as well.
- The `aircraft.json` file is continuously parsed for aircraft data provided by the ADS-B receiver.
- Distinctive aircraft (ICAO HEX code) and flights (airline flight numbers) are stored in a database, along with the first time of contact, aircraft registration (if available) and aicraft type (if available).
- As default setting, a flight is considered unique for one hour from initial contact, allowing the detection of multiple flights by the same aircraft within one day.
This is especially relevant for general aviation flights without specific flight number.
The threshold of one hour can be configured in the [settings.ini file](settings.ini) as required.
- Information regarding currently seen flights and tracked recent flights are written to the service logs or screen in certain time intervals.

### Database

- The ADS-B Logger uses a lightweight [SQLite](https://www.sqlite.org/index.html) database, and no database server is necessary.
- Other tools, such as [Grafana](https://grafana.com), may be used to read the database and visualize received flight information.
- Flights are added to the database in certain time intervals to reduce the number of database writes.
- When the ADS-B Logger service terminates, all tracked flights in the cache are written to the database.
- When the ADS-B Logger service starts, recent flights (i.e., within the last hour per default) are read for tracking from the database, allowing the logger to continue when it is restarted.

### Record Values

- The ADS-B Logger stores record values for lowest/highest barometric/geometric altitude, ground speed, indicated airspeed, mach number, vertical speed, distance to the receiver, and other information.
- The record values are stored together with a timestamp and information about the flight/aircraft that set the respective record.

### Further Information

- readsb ADS-B decoder:
https://github.com/wiedehopf/readsb
- Wiedehopf's very helpful wiki on ADS-B receivers:
https://github.com/wiedehopf/adsb-wiki/wiki
- Information on `aircraft.json` data fields:
https://github.com/wiedehopf/readsb/blob/dev/README-json.md#aircraftjson-and---json-port

## Settings

All settings, such as the database path and the timeout for treating a flight as unique, are stored in the [settings.ini file](settings.ini).
The file can be adjusted by the user as necessary.

## Setup / Installation

### Optional: Additional Information in aircraft.json

ADS-B data does not contain the aircraft registration and aircraft type.
An additional database is necessary to provide this data based on the unique 24-bit ICAO identifier assigned to the aicraft.
The following adds the registration and aircraft type to `aircraft.json`.
The folder paths may have to be modified as required.

1. Download the aircraft database:
    ```
    wget -O /usr/local/share/tar1090/aircraft.csv.gz https://github.com/wiedehopf/tar1090-db/raw/csv/aircraft.csv.gz
    ```

2. Update the `readsb` configuration:
    ```
    sudo nano /etc/default/readsb
    ```

    Add the following setting to, e.g., `JSON_OPTIONS`:
    ```
    --db-file=/usr/local/share/tar1090/aircraft.csv.gz
    ```

    Optionally you can also add `--db-file-lt` for adding the long aircraft type name in addition to the short ICAO aircraft type.

3. Restart `readsb`:
    ```
    sudo systemctl restart readsb.service
    ```

4. Sources / further reading:
    - https://github.com/wiedehopf/readsb#configuration
    - https://github.com/wiedehopf/tar1090#0800-destroy-sd-card

### Clone adsb-logger Repository

1. Clone this repo to a local folder, e.g., `/var/adsb-logger/`
2. Configure the [settings.ini file](settings.ini) as required, e.g.,
    ```
    cd /var/adsb-logger/
    sudo nano settings.ini
    ```

### Variant 1: Run ADS-B Logger in Terminal

It is suggested to try variant 1 before setting up the service ([variant 2](#variant-2-set-up-ads-b-logger-as-service)) to ensure that the logger is working as intended.

1. To simply run the ADS-B Logger in your terminal, run the main file:
    ```
    python main_noservice.py
    ```
2. The ADS-B Logger can be stopped by pressing CTRL + C.

### Variant 2: Set up ADS-B Logger as Service

1. Create a new user for the service:
    ```
    sudo useradd -r -s /bin/false adsb_logger
    ```

2. Ensure the new user has write access to this folder:
    ```
    sudo chown adsb_logger:adsb_logger adsb-logger --recursive
    ```

3. Create new serviced file:
    ```
    sudo nano /etc/systemd/system/adsb-logger.service
    ```

4. Copy the content of the [adsb-logger.service](adsb-logger.service) file,and modify the service settings as required (e.g., paths).
    The `python3 -u` is for the unbuffered Python mode to immediately show printouts in the journal log.
    The environment `PYTHONUNBUFFERED=1` is redundant to the `-u` argument.

5. Enable and start the new service:
    ```
    sudo systemctl daemon-reload
    sudo systemctl enable --now adsb-logger.service
    sudo systemctl start --now adsb-logger.service
    ```

## Log Files

For the systemd service version ([variant 2](#variant-2-set-up-ads-b-logger-as-service)), access the log files via
```
sudo journalctl -u adsb-logger.service -f
```

## Credits

The ADS-B Logger was inspired by:
1. wesmorgan1's reddit post:
https://www.reddit.com/r/ADSB/comments/rutot0/python3_script_to_profile_dump1090_output_and
2. wiedehopf2342's comments for performance optimization
3. nfacha's adsb-stats-logger, a similar project:
https://github.com/nfacha/adsb-stats-logger

Thank you for your inspiration!
