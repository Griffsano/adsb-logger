import logging
import os
import sqlite3
from configparser import ConfigParser
from datetime import datetime
from typing import List

from Aircraft import Aircraft
from Record import Record
from States import States

log = logging.getLogger(__name__)


class Database:
    db_connection: sqlite3.Connection = None  # type: ignore
    db_cursor: sqlite3.Cursor = None  # type: ignore

    def __init__(self, config: ConfigParser) -> None:
        self.config = config

        # Setup and create database
        path_database = self.config["PATHS"]["database"].strip()
        log.debug(f"Database path: {path_database}")
        self.db_connection = sqlite3.connect(os.path.abspath(path_database))
        self.db_cursor = self.db_connection.cursor()
        self.create_database()

    def __del__(self) -> None:
        # Close database
        self.db_cursor.close()
        self.db_connection.close()

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

    def read_recent_flights(self, timestamp_min) -> List[Aircraft]:
        db_command = f"SELECT * FROM aircraft WHERE time > {timestamp_min}"
        db_response = self.db_cursor.execute(db_command).fetchall()
        ac_list = []

        for r in db_response:
            aircraft = Aircraft()

            aircraft.time_start = r[1]
            aircraft.time_end = aircraft.time_start
            aircraft.hex = r[3]
            aircraft.registration = r[4]
            aircraft.ac_type = r[5]
            aircraft.flight = r[6]

            ac_list.append(aircraft)

        log.info(f"Read {len(ac_list)} recent flights from database")
        return ac_list

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

        except sqlite3.IntegrityError:
            return True

        if commit_db:
            self.db_connection.commit()
        return False

    def read_records(self) -> List[Record]:
        db_counter = 0
        rec_list = []
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

                rec_list.append(record)
        log.info(f"Read {db_counter} record flights from database")
        return rec_list

    def write_records(self, records: List[Record], commit_db: bool = True) -> bool:
        db_counter = 0
        for r in records:
            try:
                if r.aircraft is None:  # mypy fix
                    r.aircraft = Aircraft()
                db_command = (
                    "REPLACE INTO records ( "
                    "'id', 'value', 'id_aircraft', 'time', 'date', "
                    "'hex', 'registration', 'type', 'flight' ) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);"
                )
                m = "max" if r.is_max else "min"
                id = f"{r.record_key}_{m}"
                if r.aircraft.time_start is None:  # mypy fix
                    time_start_short_int = 0
                else:
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
                log.debug(
                    f"Wrote {id} record with value "
                    f"{getattr(r.aircraft.states, r.record_key)} to database"
                )

            except sqlite3.IntegrityError:
                return True

        if commit_db:
            self.db_connection.commit()
        log.info(f"Stored {db_counter} record flights in database")
        return False
