"""Starter-compatible command flags; original implementation, no starter code."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from signalpost.cli import main

if __name__ == "__main__":
    raise SystemExit(main(["batch", *sys.argv[1:]]))
