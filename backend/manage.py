#!/usr/bin/env python
import os
from pathlib import Path


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "irv_backend.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError("Could not import Django. Install backend dependencies.") from exc
    execute_from_command_line()


if __name__ == "__main__":
    main()
