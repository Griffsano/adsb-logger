#!/usr/bin/python3
import dataclasses
import logging
import numbers

from States import States

log = logging.getLogger(__name__)


@dataclasses.dataclass
class Aircraft:
    unique_var = ["hex", "flight", "registration", "ac_type"]
    overwrite_var = []

    hex: str = None
    flight: str = None
    registration: str = None
    ac_type: str = None

    states: States = None

    time_start: int = None
    time_end: int = None

    def __init__(self) -> None:
        self.states = States()

    def parse_data_dict(self, data: dict) -> None:
        self.hex = data.get("hex")
        self.flight = data.get("flight")
        self.registration = data.get("r")
        self.ac_type = data.get("t")

        for s in self.states.key_list:
            if isinstance(data.get(s), numbers.Number):
                setattr(self.states, s, data.get(s))

    def is_identical(self, data) -> bool:
        """Returns true if the unique identifiers are identical"""
        assert type(self) == type(
            data
        ), f"Cannot compare {type(self)} with {type(self)}"

        # Compare unique identifiers
        if isinstance(self.unique_var, list):
            identifiers = self.unique_var
        else:
            identifiers = [self.unique_var]
        for identifier in identifiers:
            if not (
                getattr(self, identifier) == None
                or getattr(data, identifier) == None
                or getattr(self, identifier) == getattr(data, identifier)
            ):
                return False
        else:
            return True

    def merge(self, data):
        assert type(self) == type(
            data
        ), f"Cannot compare {type(self)} with {type(self)}"

        # Merge variables two-way
        if isinstance(self.unique_var, list):
            vars = self.unique_var
        else:
            vars = [self.unique_var]
        for var in vars:
            if getattr(self, var) is None:
                setattr(self, var, getattr(data, var))
            elif getattr(data, var) is None:
                setattr(data, var, getattr(self, var))

        # Overwrite remaining variables
        if isinstance(self.overwrite_var, list):
            vars = self.overwrite_var
        else:
            vars = [self.overwrite_var]
        for var in vars:
            if not getattr(data, var) is None:
                setattr(self, var, getattr(data, var))

        self.time_start = min(self.time_start, data.time_start)
        self.time_end = max(self.time_end, data.time_end)

        return self
