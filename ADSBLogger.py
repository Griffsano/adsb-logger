import json
import logging
import time
from configparser import ConfigParser
from contextlib import closing
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from Aircraft import Aircraft
from Database import Database

log = logging.getLogger(__name__)


class ADSBLogger:
    config: ConfigParser
    database: Database = None  # type: ignore

    # Timestamps
    time_json: int = 0
    time_print_info: int = 0
    time_db_write: int = 0

    # Aircraft lists
    current: list = []
    tracked: list = []

    # Observed record values
    records: list = []

    def __init__(self, config: ConfigParser) -> None:
        log.info("Starting ADS-B Logger")
        self.config = config

        # Set up JSON path
        log.debug(f"JSON path: {self.config['PATHS']['json'].strip()}")
        self.fetch_adsb_info()

        # Set up database
        self.database = Database(self.config)

        # Read recent flights from database
        timestamp_min = int(
            self.time_json - self.config["TIMEOUTS"].getfloat("unique_flight")
        )
        for t in self.database.read_recent_flights(timestamp_min):
            self.tracked.append(t)
        for r in self.database.read_records():
            self.records.append(r)

    def loop(self):
        if self.time_print_info < self.time_json - self.config["TIMEOUTS"].getfloat(
            "print_info"
        ):
            log.info(
                f"{len(self.current)} currently seen flights, "
                f"{len(self.tracked)} tracked recent flights"
            )
            self.time_print_info = self.time_json

        if self.time_db_write < self.time_json - self.config["TIMEOUTS"].getfloat(
            "db_write"
        ):
            self.database.write_records(self.records, False)
            self.clean_tracked_flights()
            self.time_db_write = self.time_json

        if self.fetch_adsb_info():
            return

        self.check_records()
        self.merge_flights()

    def __del__(self) -> None:
        log.info("Stopping ADS-B Logger")

        self.database.write_records(self.records, False)

        # Write tracked (cached) flights to database
        self.database.write_flights(self.tracked)
        del self.database

    def clean_tracked_flights(self) -> None:
        outdated = []
        for t in self.tracked:
            if t.time_start < self.time_json - self.config["TIMEOUTS"].getfloat(
                "unique_flight"
            ):
                outdated.append(t)
                self.tracked.remove(t)
        self.database.write_flights(outdated)

    def fetch_adsb_info(self) -> bool:
        # Fetch newest JSON with ADS-B data
        try:
            with closing(
                urlopen(
                    self.config["PATHS"]["json"].strip(),
                    None,
                    self.config["TIMEOUTS"].getfloat("http_read"),
                )
            ) as aircraft_file:
                aircraft_data = json.load(aircraft_file)
        except TimeoutError as e:
            log.error(e)
            return True
        except (HTTPError, URLError, json.JSONDecodeError) as e:
            log.error(e)
            time.sleep(self.config["TIMEOUTS"].getfloat("http_read"))
            return True

        # Check if data is new
        now = aircraft_data["now"]
        if self.time_json >= now:
            return True
        self.time_json = now

        # Parse all aircraft data
        self.current = []
        for a in aircraft_data["aircraft"]:
            aircraft = Aircraft()
            aircraft.parse_data_dict(a)

            aircraft.time_start = self.time_json
            aircraft.time_end = self.time_json

            self.current.append(aircraft)
        return False

    def check_records(self) -> None:
        for c in self.current:
            for r in self.records:
                if r.compare_aircraft(c):
                    r.timestamp = self.time_json
                    r.aircraft = c
                    r.is_stored = False
                    m = "max" if r.is_max else "min"
                    log.info(
                        f"Registration {r.aircraft.registration} "
                        f"set new record for {m} {r.record_key}: "
                        f"{getattr(r.aircraft.states, r.record_key)}"
                    )
                    self.print_flight_info(c, "Record")

    def merge_flights(self) -> None:
        # Merge current flights with tracked (cached) flights
        for c in self.current:
            for t in reversed(self.tracked):
                if t.time_start > self.time_json - self.config["TIMEOUTS"].getfloat(
                    "unique_flight"
                ) and t.is_identical(c):
                    t.merge(c)
                    break
            else:
                self.tracked.append(c)
                self.print_flight_info(c, "New")

    def print_flight_info(
        self, aircraft: Aircraft, header: str, log_type: str = ""
    ) -> None:
        log_str = (
            f"{header}: "
            # f"Time: {int(self.time_json)}, "
            f"Hex: {aircraft.hex}, "
            f"Reg: {aircraft.registration}, "
            f"Type: {aircraft.ac_type}, "
            f"Flight: {aircraft.flight}"
        )
        if log_type == "INFO":
            log.info(log_str)
        else:
            log.debug(log_str)
