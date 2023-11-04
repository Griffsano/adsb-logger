import logging
from configparser import ConfigParser
from os import path

log = logging.getLogger(None)
sh = logging.StreamHandler()
sh.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
log.addHandler(sh)

config = ConfigParser()
if not config.read(path.join(path.dirname(__file__), "settings.ini")):
    log.error("Could not read settings file")
    raise RuntimeError("Could not read settings file")

log.setLevel(eval(f"logging.{config['LOGGING']['LEVEL'].strip()}"))
