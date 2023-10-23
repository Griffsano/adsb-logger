#!/usr/bin/python3
import json
import logging
import os
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from Aircraft import Aircraft
from Record import Record
from States import States

log = logging.getLogger(__name__)


class ADSBLogger:
    # Settings
    timeout_print_info: float = 3 * 60
    timeout_unique_flight: float = 60 * 60
    timeout_db_write: float = 15 * 60

    # Paths
    path_database: os.PathLike = None  # type: ignore
    path_json: Path = None  # type: ignore

    # Timestamps
    time_json: int = 0
    time_print_info: int = 0
    time_db_write: int = 0

    # Aircraft lists
    current: list = []
    tracked: list = []

    # Observed record values
    records: list = []

    # Database
    db_connection: sqlite3.Connection = None  # type: ignore
    db_cursor: sqlite3.Cursor = None  # type: ignore

    def __init__(self, path_database: str, path_json: str) -> None:
        log.info("Starting ADS-B Logger")

        # Set up JSON path
        self.path_json = Path(path_json)
        log.debug(f"JSON path: {self.path_json}")
        self.fetch_adsb_info()

        # Set up database
        self.path_database = os.path.abspath(path_database)  # type: ignore
        log.debug(f"Database: {self.path_database}")

        self.db_connection = sqlite3.connect(self.path_database)
        self.db_cursor = self.db_connection.cursor()

        # Create and read recent flights from database
        self.create_database()
        self.read_recent_flights()
        self.read_records()

    def loop(self):
        if self.time_print_info < self.time_json - self.timeout_print_info:
            log.info(
                f"{len(self.current)} currently seen flights, "
                f"{len(self.tracked)} tracked recent flights"
            )
            self.time_print_info = self.time_json

        if self.time_db_write < self.time_json - self.timeout_db_write:
            self.write_records(False)
            self.clean_tracked_flights()
            self.time_db_write = self.time_json

        if self.fetch_adsb_info():
            return

        self.check_records()
        self.merge_flights()

    def __del__(self) -> None:
        log.info("Stopping ADS-B Logger")

        self.write_records(False)

        # Write tracked (cached) flights to database
        db_counter = 0
        for t in self.tracked:
            self.write_flight(t, False)
            db_counter += 1
        self.db_connection.commit()

        # Close database
        self.db_cursor.close()
        self.db_connection.close()
        log.info(f"Stored {db_counter} tracked flights in database")

    def clean_tracked_flights(self) -> None:
        db_counter = 0
        for t in self.tracked:
            if t.time_start < self.time_json - self.timeout_unique_flight:
                self.write_flight(t, False)
                self.tracked.remove(t)
                db_counter += 1
        self.db_connection.commit()
        log.info(f"Stored {db_counter} outdated recent flights in database")

    def create_database(self) -> None:
        # table for seen aircraft
        try:
            self.db_cursor.execute(
                "CREATE TABLE aircraft ( "
                "id TEXT PRIMARY KEY, "
                "time INTEGER, "
                "date TEXT, "
                "hex TEXT, "
                "registration TEXT, "
                "type TEXT, "
                "flight TEXT )"
            )
            log.debug("Created aircraft table in database")
        except sqlite3.OperationalError:
            log.debug("Aircraft table already exists in database")

        # table for record values
        try:
            self.db_cursor.execute(
                "CREATE TABLE records ( "
                "id TEXT PRIMARY KEY, "
                "value REAL, "
                "id_aircraft TEXT, "
                "time INTEGER, "
                "date TEXT, "
                "hex TEXT, "
                "registration TEXT, "
                "type TEXT, "
                "flight TEXT )"
            )
            log.debug("Created records table in database")
        except sqlite3.OperationalError:
            log.debug("Records table already exists in database")
        return

    def read_recent_flights(self) -> None:
        timestamp_min = int(self.time_json - self.timeout_unique_flight)
        db_command = f"SELECT * FROM aircraft WHERE time > {timestamp_min}"
        db_response = self.db_cursor.execute(db_command).fetchall()

        for r in db_response:
            aircraft = Aircraft()

            aircraft.time_start = r[1]
            aircraft.time_end = aircraft.time_start
            aircraft.hex = r[3]
            aircraft.registration = r[4]
            aircraft.ac_type = r[5]
            aircraft.flight = r[6]

            self.tracked.append(aircraft)
            # self.print_flight_info(aircraft, "Read")

        log.info(f"Read {len(db_response)} recent flights from database")

    def write_flight(self, aircraft: Aircraft, commit_db: bool = True) -> bool:
        try:
            db_command = (
                "REPLACE INTO aircraft ( "
                "'id', 'time', 'date', 'hex', 'registration', 'type', 'flight'"
                " ) VALUES (?, ?, ?, ?, ?, ?, ?);"
            )
            if aircraft.time_start is None:  # mypy fix
                time_start_short_int = 0
            else:
                time_start_short_int = int(aircraft.time_start)
            id = f"{time_start_short_int}_{aircraft.hex}"
            self.db_cursor.execute(
                db_command,
                (
                    id,
                    time_start_short_int,
                    datetime.utcfromtimestamp(time_start_short_int).strftime(
                        "%Y-%m-%d"
                    ),
                    aircraft.hex,
                    aircraft.registration,
                    aircraft.ac_type,
                    aircraft.flight,
                ),
            )

            # Continues if no integrity error is thrown
            self.print_flight_info(aircraft, "Stored")

        except sqlite3.IntegrityError:
            # self.print_flight_info(aircraft, "Skipped")
            return True

        if commit_db:
            self.db_connection.commit()
        return False

    def read_records(self) -> None:
        db_counter = 0
        temp_ac = Aircraft()
        if temp_ac.states is None:  # mypy fix
            temp_ac.states = States()
        for s in temp_ac.states.key_list:
            for m in ["min", "max"]:
                record = Record()
                if record.aircraft is None:  # mypy fix
                    record.aircraft = Aircraft()
                record.record_key = s
                record.is_max = True if m == "max" else False

                db_command = f"SELECT * FROM records WHERE id='{s}_{m}'"
                db_response = self.db_cursor.execute(db_command).fetchone()
                if db_response:
                    setattr(record.aircraft.states, s, db_response[1])
                    record.aircraft.time_start = db_response[2].split("_")[0]
                    record.timestamp = db_response[3]
                    record.aircraft.hex = db_response[5]
                    record.aircraft.registration = db_response[6]
                    record.aircraft.ac_type = db_response[7]
                    record.aircraft.flight = db_response[8]
                    log.debug(
                        f"Read {s}_{m} record with value "
                        f"{getattr(record.aircraft.states, s)} from database"
                    )
                    db_counter += 1
                else:
                    log.debug(f"Record for {s}_{m} not available in database")

                self.records.append(record)
        log.info(f"Read {db_counter} record flights from database")

    def write_records(self, commit_db: bool = True) -> bool:
        db_counter = 0
        for r in self.records:
            try:
                db_command = (
                    "REPLACE INTO records ( "
                    "'id', 'value', 'id_aircraft', 'time', 'date', "
                    "'hex', 'registration', 'type', 'flight' ) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);"
                )
                m = "max" if r.is_max else "min"
                id = f"{r.record_key}_{m}"
                time_start_short_int = int(r.aircraft.time_start)
                aircraft_id = f"{time_start_short_int}_{r.aircraft.hex}"
                self.db_cursor.execute(
                    db_command,
                    (
                        id,
                        getattr(r.aircraft.states, r.record_key),
                        aircraft_id,
                        int(r.timestamp),
                        datetime.utcfromtimestamp(int(r.timestamp)).strftime(
                            "%Y-%m-%d"
                        ),
                        r.aircraft.hex,
                        r.aircraft.registration,
                        r.aircraft.ac_type,
                        r.aircraft.flight,
                    ),
                )

                # Continues if no integrity error is thrown
                db_counter += 1
                self.print_flight_info(r.aircraft, "Stored Record")

            except sqlite3.IntegrityError:
                # self.print_flight_info(aircraft, "Skipped Record")
                return True

        if commit_db:
            self.db_connection.commit()
        log.info(f"Stored {db_counter} record flights in database")
        return False

    def fetch_adsb_info(self) -> bool:
        # Fetch newest JSON with ADS-B data
        try:
            with closing(
                urlopen(str(self.path_json), None, 3.0)
            ) as aircraft_file:
                aircraft_data = json.load(aircraft_file)
        except (HTTPError, URLError) as e:
            log.error(e)
            return True

        # Check if data is new
        now = aircraft_data["now"]
        if self.time_json >= now:
            # log.debug("Skipping outdated ADS-B info")
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
                if (
                    t.time_start > self.time_json - self.timeout_unique_flight
                    and t.is_identical(c)
                ):
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
