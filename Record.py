#!/usr/bin/python3
import dataclasses
import logging
import numbers
from typing import Optional

from Aircraft import Aircraft
from States import States

log = logging.getLogger(__name__)


@dataclasses.dataclass
class Record:
    aircraft: Optional[Aircraft] = None
    record_key: str = ""
    is_max: Optional[bool] = None
    timestamp: Optional[int] = None

    def __init__(self) -> None:
        self.aircraft = Aircraft()
        self.aircraft.time_start = 0
        self.timestamp = 0

    def compare_aircraft(self, ac: Aircraft) -> bool:
        if self.aircraft is None:  # mypy fix
            self.aircraft = Aircraft()

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
        return False

    def assign_aircraft(self, ac: Aircraft):
        self.aircraft = Aircraft()
        self.aircraft.merge(ac)
        if self.aircraft.states is None:  # mypy fix
            self.aircraft.states = States()
        self.aircraft.states.import_data(ac.states)
