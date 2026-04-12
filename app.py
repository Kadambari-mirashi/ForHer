"""
PCOSense — default Shiny entrypoint
===================================
Multi-Agent System for Polycystic Ovary Syndrome Detection (full UI in ``src/app/pcosense_app.py``).

Run:
  shiny run app.py

Legacy course app (Zena — preventive care / MyHealthfinder):
  shiny run src/app/zena_app.py
"""

from src.app.pcosense_app import app

__all__ = ["app"]
