#!/usr/bin/env python3
"""Point d'entrée du service (unité systemd) : lance la boucle de polling du package photo_devis."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from photo_devis.main import run  # noqa: E402

if __name__ == "__main__":
    run()
