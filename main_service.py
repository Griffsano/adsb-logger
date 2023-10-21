#!/usr/bin/python3
import signal
import time
import logging

import sdnotify

from ADSBLogger import ADSBLogger

log = logging.getLogger(None)
log.setLevel(logging.INFO)

sh = logging.StreamHandler()
sh.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
log.addHandler(sh)

path_database = "/var/adsb-logger/adsb-logger.db"
path_json = "http://localhost/tar1090/data/aircraft.json"

terminate = False


def terminate_handler(signal_number, stack_frame):
    global terminate
    terminate = True


signal.signal(signal.SIGINT, terminate_handler)
signal.signal(signal.SIGTERM, terminate_handler)

n = sdnotify.SystemdNotifier()
adsb = ADSBLogger(path_database, path_json)

n.notify("READY=1")
while not terminate:
    adsb.loop()
    time.sleep(0.5)

n.notify("STOPPING=1")
del adsb
time.sleep(1)
