"""Startup, logging, crash handling, backup/restore."""
import logging
import shutil
import sys
import traceback
import zipfile
from logging.handlers import RotatingFileHandler
from storage.paths import data_dir, sub


def setup_logging():
    log = sub("logs") / "jarvis.log"
    handler = RotatingFileHandler(log, maxBytes=2_000_000, backupCount=3, encoding="utf-8")
    logging.basicConfig(level=logging.INFO, handlers=[handler, logging.StreamHandler()],
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    def excepthook(t, v, tb):
        logging.critical("Unhandled error:\n%s", "".join(traceback.format_exception(t, v, tb)))
        (sub("logs") / "last_crash.txt").write_text("".join(traceback.format_exception(t, v, tb)), encoding="utf-8")
    sys.excepthook = excepthook
    return log


def backup(zip_path):
    d = data_dir()
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for f in d.rglob("*"):
            if f.is_file() and "browser_profile" not in f.parts and "logs" not in f.parts:
                z.write(f, f.relative_to(d))


def restore(zip_path):
    d = data_dir()
    safety = d.parent / (d.name + "_before_restore")
    if safety.exists():
        shutil.rmtree(safety)
    shutil.copytree(d, safety, ignore=shutil.ignore_patterns("browser_profile"))
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(d)
