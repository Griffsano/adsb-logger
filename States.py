#!/usr/bin/python3
import dataclasses
import logging
from typing import Optional

log = logging.getLogger(__name__)


@dataclasses.dataclass
class States:
    alt_baro: Optional[float] = None
    alt_geom: Optional[float] = None
    gs: Optional[float] = None
    ias: Optional[float] = None
    mach: Optional[float] = None
    roll: Optional[float] = None
    baro_rate: Optional[float] = None
    geom_rate: Optional[float] = None
    rssi: Optional[float] = None
    ws: Optional[float] = None
    oat: Optional[float] = None
    r_dst: Optional[float] = None

    def __init__(self) -> None:
        self.key_list = [
            a
            for a in dir(self)
            if not callable(getattr(self, a)) and not a.startswith("__")
        ]

    def import_data(self, data):
        assert isinstance(
            self, type(data)
        ), f"Cannot compare {type(self)} with {type(self)}"

        # Overwrite remaining variables
        if isinstance(self.key_list, list):
            vars = self.key_list
        else:
            vars = [self.key_list]
        for var in vars:
            if not getattr(data, var) is None:
                setattr(self, var, getattr(data, var))

        return self
