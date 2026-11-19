"""indiadata - small helpers that fetch official Indian economic data.

Written for the book *Python for Indian Economics Students*.
Every function returns a tidy pandas DataFrame and caches the raw download
in ``data/raw/`` so that your notebooks still run when you are offline.

Chapter 4 opens this box and shows how each function works, line by line.
"""

from .sources import (mospi_cpi, worldbank, mospi, mospi_nas, mospi_iip,
                      mospi_cpi_groups, mospi_cpi_items, mospi_wpi, bis,
                      oecd_rates, pwt, NAS_INDICATORS, NAS_REVISIONS)
from .plfs import read_plfs, layout_names, labour_status, labour_rates

__all__ = ["mospi_cpi", "worldbank", "mospi", "mospi_nas", "mospi_iip",
           "mospi_cpi_groups", "mospi_cpi_items", "mospi_wpi", "bis",
           "oecd_rates", "pwt", "NAS_INDICATORS", "NAS_REVISIONS",
           "read_plfs", "layout_names", "labour_status", "labour_rates"]
