#!/usr/bin/python3
import dataclasses
import logging
import numbers

from Aircraft import Aircraft

log = logging.getLogger(__name__)


@dataclasses.dataclass
class Record:
    aircraft: Aircraft = None
    record_key: str = ""
    is_max: str = None
    timestamp: int = None

    def __init__(self) -> None:
        self.aircraft = Aircraft()
        self.aircraft.time_start = 0
        self.timestamp = 0

    def compare_aircraft(self, ac: Aircraft) -> bool:
        if not isinstance(getattr(ac.states, self.record_key), numbers.Number):
            return False
        if not getattr(self.aircraft.states, self.record_key):
            return True

        if self.is_max is True:
            if getattr(ac.states, self.record_key) > getattr(
                self.aircraft.states, self.record_key
            ):
                return True
        elif self.is_max is False:
            if getattr(ac.states, self.record_key) < getattr(
                self.aircraft.states, self.record_key
            ):
                return True
        else:
            return False

    def assign_aircraft(self, ac: Aircraft):
        self.aircraft = Aircraft()
        self.aircraft.merge(ac)
        self.aircraft.states.import_data(ac.states)
