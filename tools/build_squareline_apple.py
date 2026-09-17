#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Build the AIWatchApple SquareLine Studio project (240x240 CIRCLE).

This file is now just the entry point.  The interesting parts live in:

    tools/engine/squareline_engine.py   serialisation engine (project-agnostic)
    tools/screens/aiwatch_apple.py      palette + fonts + build_screens()

Run
---
    python tools/build_squareline_apple.py
    python tools/build_squareline_apple.py --assets examples/AIWatchApple/assets
    python tools/build_squareline_apple.py --out /tmp/AIWatchApple
    SQUARELINE_NODE_BIN=/usr/local/bin/node python tools/build_squareline_apple.py

Then verify:
    python tools/validate_squareline_project.py <out dir>
    python tools/preview_from_project.py <out dir>
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from screens.aiwatch_apple import PROJECT          # noqa: E402
from engine import squareline_engine as engine     # noqa: E402


def main():
    return engine.build(PROJECT)


if __name__ == "__main__":
    sys.exit(main())
