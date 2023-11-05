import logging
import os
import sqlite3
from configparser import ConfigParser
from datetime import datetime, time
from typing import List

from Aircraft import Aircraft
from Record import Record
from States import States

log = logging.getLogger(__name__)


class Database:
    db_connection: sqlite3.Connection = None  # type: ignore
    db_cursor: sqlite3.Cursor = None  # type: ignore

    def __init__(self, config: ConfigParser, read_only: bool = False) -> None:
        self.config = config

        # Setup and create database
        path_database = self.config["PATHS"]["database"].strip()
        log.debug(f"Database path: {path_database}")
        if read_only:
            self.db_connection = sqlite3.connect(
                os.path.abspath(path_database), uri=True
            )
        else:
            self.db_connection = sqlite3.connect(os.path.abspath(path_database))
        self.db_cursor = self.db_connection.cursor()
        if not read_only:
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

    def read_recent_flights(self, timestamp_min: int) -> List[Aircraft]:
        db_command = f"SELECT * FROM aircraft WHERE time >= {timestamp_min}"
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

    def write_flights(self, aircraft: List[Aircraft]) -> int:
        db_counter = 0
        for t in aircraft:
            if not self.write_flight(t, False):
                db_counter += 1
        self.db_connection.commit()
        log.info(f"Stored {db_counter} recent flights in database")
        return db_counter

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

        except sqlite3.IntegrityError as e:
            log.error(
                f"Error when storing flight {aircraft.flight} "
                f"({aircraft.registration}/{aircraft.hex}) in database"
            )
            log.error(e)
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
                    record.is_stored = True
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
                if r.is_stored:
                    continue
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
                    f"Stored {id} record with value "
                    f"{getattr(r.aircraft.states, r.record_key)} in database"
                )

            except sqlite3.IntegrityError as e:
                if r.aircraft is None:  # mypy fix
                    r.aircraft = Aircraft()
                log.error(
                    f"Error when storing record {id} "
                    f"({getattr(r.aircraft.states, r.record_key)}) in database"
                )
                log.error(e)
                return True

        if commit_db:
            self.db_connection.commit()
        log.info(f"Stored {db_counter} record flights in database")
        return False

    def evaluate_counts(
        self, timestamp_min: float = 0, timestamp_max: float = 0
    ) -> List[List[str]]:
        if timestamp_max <= timestamp_min:
            timestamp_max = datetime.timestamp(datetime.now())
        statistics = [["Database Keys", "Count"]]
        commands = {
            "Entries": "COUNT(id)",
            "Addresses": "COUNT(DISTINCT hex)",
            "Flights": "COUNT(DISTINCT flight)",
            "Types": "COUNT(DISTINCT type)",
        }

        for name, cmd in commands.items():
            db_command = (
                f"SELECT {cmd} FROM aircraft "
                f"WHERE time >= {timestamp_min} AND time < {timestamp_max}"
            )
            db_response = self.db_cursor.execute(db_command).fetchone()
            statistics.append([name, db_response[0]])

        return statistics

    def evaluate_days(self, day_count: int = 5) -> List[List[str]]:
        statistics = [["Day (local time)", "Entries", "Addresses", "Flights", "Types"]]
        now = datetime.now()

        # Total entries in database
        result = self.evaluate_counts(0, datetime.timestamp(now))
        day_counts = ["Database total"]
        for count_type in range(1, len(statistics[0])):
            # Ensure the type of count (e.g., entries or flights) is correct
            assert result[count_type][0] == statistics[0][count_type]
            day_counts.append(result[count_type][1])
        statistics.append(day_counts)

        # Database entries for each day
        timestamp_min = datetime.timestamp(datetime.combine(now, time.min))
        timestamp_max = datetime.timestamp(datetime.combine(now, time.max))
        for day in range(day_count):
            if day == 0:
                day_name = "Today until now"
            elif day == 1:
                day_name = "Yesterday"
            else:
                day_name = f"{day} days ago"
            result = self.evaluate_counts(timestamp_min, timestamp_max)
            day_counts = [day_name]
            day_counts.extend(result[c][1] for c in range(1, len(statistics[0])))
            statistics.append(day_counts)
            timestamp_min -= 24 * 3600
            timestamp_max -= 24 * 3600

        return statistics

    def evaluate_flights(self, key: str, max_count: int = 5) -> List[List[str]]:
        if key == "flight":
            db_command = (
                "SELECT flight, COUNT(flight) FROM aircraft "
                "GROUP BY flight "
                "ORDER BY COUNT(flight) DESC"
            )
        elif key == "registration":
            db_command = (
                "SELECT registration, COUNT(registration) FROM aircraft "
                "GROUP BY registration "
                "ORDER BY COUNT(registration) DESC"
            )
        elif key == "type":
            db_command = (
                "SELECT type, COUNT(type) FROM aircraft "
                "GROUP BY type "
                "ORDER BY COUNT(type) DESC"
            )
        elif key == "airline":
            db_command = (
                "SELECT substr(flight, 1, 3) as airline, COUNT(flight) as count, "
                "REPLACE(registration,'-','') as registration_short, "
                "REPLACE(flight,' ','') as flight_short FROM aircraft "
                "WHERE registration_short is not NULL "
                "AND registration_short is not flight_short "
                "GROUP BY airline "
                "ORDER BY count DESC"
            )
        else:
            raise KeyError(f"Unknown database entry key {key}")
        statistics = [[key.capitalize(), "Count"]]
        db_response = self.db_cursor.execute(db_command).fetchmany(max_count)
        statistics.extend([r[0], r[1]] for r in db_response)
        return statistics

    def evaluate_records(self) -> List[List[str]]:
        statistics = [["Record", "Value", "Registration", "Type", "Flight", "Time"]]
        db_command = (
            "SELECT id as record, value, registration, type, flight, time FROM records"
        )
        db_response = self.db_cursor.execute(db_command).fetchall()
        for r in db_response:
            timestamp = datetime.fromtimestamp(r[-1])
            statistics.append(list(r[0:-1]) + [timestamp])
        return sorted(statistics, key=lambda x: x[0])
