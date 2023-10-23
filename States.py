#!/usr/bin/python3
import dataclasses
import logging

log = logging.getLogger(__name__)


@dataclasses.dataclass
class States:
    alt_baro: float = None
    alt_geom: float = None
    gs: float = None
    ias: float = None
    mach: float = None
    roll: float = None
    baro_rate: float = None
    geom_rate: float = None
    rssi: float = None
    ws: float = None
    oat: float = None
    r_dst: float = None

    def __init__(self) -> None:
        self.key_list = [
            a
            for a in dir(self)
            if not callable(getattr(self, a)) and not a.startswith("__")
        ]

    def import_data(self, data):
        assert type(self) == type(
            data
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
