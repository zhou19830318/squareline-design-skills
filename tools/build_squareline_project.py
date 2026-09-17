#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Build the AIWatch SquareLine Studio project (410x502 RECTANGLE).

This file is now just the entry point.  The interesting parts live in:

    tools/engine/squareline_engine.py   serialisation engine (project-agnostic)
    tools/screens/aiwatch.py            palette + fonts + build_screens()

Run
---
    python tools/build_squareline_project.py
    python tools/build_squareline_project.py --assets examples/AIWatch/assets
    python tools/build_squareline_project.py --out /tmp/AIWatch
    SQUARELINE_NODE_BIN=/usr/local/bin/node python tools/build_squareline_project.py

Then verify:
    python tools/validate_squareline_project.py <out dir>
    python tools/preview_from_project.py <out dir>
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from screens.aiwatch import PROJECT                # noqa: E402
from engine import squareline_engine as engine     # noqa: E402


def main():
    return engine.build(PROJECT)


if __name__ == "__main__":
    sys.exit(main())
