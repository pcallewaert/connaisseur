import os
import datetime as dt

times = {}
debug = os.environ.get("LOG_LEVEL", "INFO") == "DEBUG"


def start(timer: str):
    if debug:
        times[f"_{timer}"] = dt.datetime.now()


def stop(timer: str):
    if debug:
        try:
            times[timer] = (dt.datetime.now() - times[f"_{timer}"]).total_seconds()
            del times[f"_{timer}"]
        except KeyError:
            pass
