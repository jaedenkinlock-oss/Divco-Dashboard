import logging
import sys
from pathlib import Path
from config import LOG_DIR

_LOG_FILE = Path(LOG_DIR) / "fetch_errors.log"
_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

_fmt_console = logging.Formatter(
    fmt="%(asctime)s [%(levelname)-8s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
_fmt_file = logging.Formatter(
    fmt='{"time": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "msg": %(message)s}',
    datefmt="%Y-%m-%dT%H:%M:%S",
)

_root_configured = False


def _configure_root() -> None:
    global _root_configured
    if _root_configured:
        return

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console.setFormatter(_fmt_console)

    file_handler = logging.FileHandler(_LOG_FILE, encoding="utf-8")
    file_handler.setLevel(logging.WARNING)
    file_handler.setFormatter(_fmt_file)

    root.addHandler(console)
    root.addHandler(file_handler)

    _root_configured = True


def get_logger(name: str) -> logging.Logger:
    _configure_root()
    return logging.getLogger(name)
