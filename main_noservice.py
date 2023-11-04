import signal
import time

from ADSBLogger import ADSBLogger
from settings import config, log

terminate = False


def terminate_handler(signal_number, stack_frame):
    global terminate
    terminate = True


signal.signal(signal.SIGINT, terminate_handler)
signal.signal(signal.SIGTERM, terminate_handler)

adsb = ADSBLogger(config)
log.warning("Not running as service. Press CTRL + C once to shutdown ADS-B Logger.")

while not terminate:
    adsb.loop()
    time.sleep(config["TIMEOUTS"].getfloat("main_loop"))

del adsb
time.sleep(1)
