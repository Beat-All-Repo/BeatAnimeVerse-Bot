"""
BeatAniVerse modules package.
Auto-discovers all .py files in this directory.
"""
import glob
import os
import logging

LOGGER = logging.getLogger(__name__)

_NO_LOAD = set(os.getenv("NO_LOAD", "").split())

def _list_modules():
    mod_paths = glob.glob(os.path.dirname(__file__) + "/*.py")
    all_mods = [
        os.path.basename(f)[:-3]
        for f in mod_paths
        if f.endswith(".py") and not f.endswith("__init__.py")
    ]
    return [m for m in all_mods if m not in _NO_LOAD]

ALL_MODULES = _list_modules()
__all__ = ALL_MODULES + ["ALL_MODULES"]
