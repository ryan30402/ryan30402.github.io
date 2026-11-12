#!/usr/bin/env python3
"""Compatibility entry point: validate the currently published project."""
from pathlib import Path
import runpy
if __name__ == "__main__":
    runpy.run_path(str(Path(__file__).with_name("check_prefix_cache.py")), run_name="__main__")
