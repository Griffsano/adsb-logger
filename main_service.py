import signal
import time

import sdnotify  # type: ignore

from ADSBLogger import ADSBLogger
from settings import config

terminate = False


def terminate_handler(signal_number, stack_frame):
    global terminate
    terminate = True


signal.signal(signal.SIGINT, terminate_handler)
signal.signal(signal.SIGTERM, terminate_handler)

n = sdnotify.SystemdNotifier()
adsb = ADSBLogger(config)

n.notify("READY=1")
while not terminate:
    adsb.loop()
    time.sleep(config["TIMEOUTS"].getfloat("main_loop"))

n.notify("STOPPING=1")
del adsb
time.sleep(1)
