"""Entry point: `python -m hmd_editor` or the `hmd-save-editor` console script."""

from __future__ import annotations

import sys

from .app import main

if __name__ == "__main__":
    sys.exit(main())
