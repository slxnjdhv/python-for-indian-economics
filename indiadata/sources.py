"""Download functions for official data sources.

Sources
-------
* MoSPI eSankhyiki API  (https://api.mospi.gov.in) - Consumer Price Index.
* World Bank Indicators API (https://api.worldbank.org/v2) - long-run
  macro series for India and other countries.

Design rules (kept deliberately simple, because students will read this file):
1. One function per data set.
2. Every download is saved to ``data/raw/<name>.csv`` with the date it was
   fetched; later calls read the saved file unless ``refresh=True``.
3. Columns come back in lower case with sensible types (dates as datetime,
   numbers as float).
"""

from __future__ import annotations

import datetime as _dt
from pathlib import Path

import pandas as pd
import requests

# Downloads are cached in data/raw/ under the folder you run Python from
# (the book folder, or /content on Colab).
RAW_DIR = Path.cwd() / "data" / "raw"
_HEADERS = {"User-Agent": "python-for-indian-economics (teaching use)"}

_MONTHS = {m: i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July",
     "August", "September", "October", "November", "December"], start=1)}

# Codes used by the MoSPI CPI API (base 2012 series).
CPI_SECTORS = {"rural": 1, "urban": 2, "combined": 3}
ALL_INDIA = 99


def _cache_path(name: str) -> Path:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    return RAW_DIR / f"{name}.csv"


def _save(df: pd.DataFrame, path: Path) -> None:
    out = df.copy()
    out["fetched_on"] = _dt.date.today().isoformat()
    out.to_csv(path, index=False)


# ---------------------------------------------------------------------------
# MoSPI: Consumer Price Index (CPI), base 2012 = 100
# ---------------------------------------------------------------------------
def mospi_cpi(sector: str = "combined", state_code: int = ALL_INDIA,
              group_code: int = 0, refresh: bool = False) -> pd.DataFrame:
    """Monthly CPI (base 2012=100) from MoSPI's eSankhyiki API.

    Parameters
    ----------
    sector : "rural", "urban" or "combined" (the RBI targets *combined*).
    state_code : 99 means All India.
    group_code : 0 means the General (headline) index.
    refresh : download again even if a saved copy exists.

    Returns
    -------
    DataFrame with columns: date, index, inflation (year-on-year %, as
    published by MoSPI), sector, state, group, subgroup, status
    (P = provisional, F = final).
    """
    name = f"mospi_cpi_{sector}_{state_code}_{group_code}"
    path = _cache_path(name)
    if path.exists() and not refresh:
        return pd.read_csv(path, parse_dates=["date"])

    url = "https://api.mospi.gov.in/api/cpi/getCPIIndex"
    params = {"base_year": 2012, "series": "Current", "state_code": state_code,
              "sector_code": CPI_SECTORS[sector], "group_code": group_code,
              "Format": "JSON", "limit": 200}
    rows, page = [], 1
    while True:                      # the API sends at most 200 rows per page
        reply = requests.get(url, params={**params, "page": page},
                             headers=_HEADERS, timeout=60)
        reply.raise_for_status()
        body = reply.json()
        rows.extend(body.get("data") or [])
        if page >= body.get("meta_data", {}).get("totalPages", 1):
            break
        page += 1

    if not rows:
        raise ValueError("MoSPI returned no data for these settings.")

    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(dict(year=df["year"],
                                     month=df["month"].map(_MONTHS), day=1))
    df["index"] = pd.to_numeric(df["index"], errors="coerce")
    df["inflation"] = pd.to_numeric(df["inflation"], errors="coerce")
    df = (df[["date", "index", "inflation", "sector", "state", "group",
              "subgroup", "status"]]
          .sort_values("date").reset_index(drop=True))
    _save(df, path)
    return df


# ---------------------------------------------------------------------------
# World Bank Indicators API
# ---------------------------------------------------------------------------
def worldbank(indicator: str, country: str = "IND",
              refresh: bool = False) -> pd.DataFrame:
    """Annual series from the World Bank Indicators API.

    Useful codes
    ------------
    NY.GDP.MKTP.KD.ZG   GDP growth (annual %)
    NY.GDP.PCAP.KD      GDP per capita (constant 2015 US$)
    FP.CPI.TOTL.ZG      Inflation, consumer prices (annual %)
    NE.TRD.GNFS.ZS      Trade (% of GDP)
    SP.POP.TOTL         Population

    ``country`` takes ISO-3 codes; join several with ';' e.g. "IND;CHN;BGD".

    Returns a DataFrame with columns: country, iso3, year, value.
    """
    safe = country.replace(";", "-")
    path = _cache_path(f"wb_{indicator}_{safe}")
    if path.exists() and not refresh:
        return pd.read_csv(path)

    url = (f"https://api.worldbank.org/v2/country/{country}/indicator/"
           f"{indicator}")
    records, page = [], 1
    while True:                      # small pages are faster and more reliable
        reply = requests.get(url, params={"format": "json", "per_page": 100,
                                          "page": page},
                             headers=_HEADERS, timeout=60)
        reply.raise_for_status()
        body = reply.json()
        if len(body) < 2 or not body[1]:
            break
        records.extend(body[1])
        if page >= body[0].get("pages", 1):
            break
        page += 1

    if not records:
        raise ValueError(f"World Bank returned no data for {indicator}.")

    df = pd.DataFrame({
        "country": [r["country"]["value"] for r in records],
        "iso3": [r["countryiso3code"] for r in records],
        "year": [int(r["date"]) for r in records],
        "value": [r["value"] for r in records],
    })
    df = (df.dropna(subset=["value"])
          .sort_values(["iso3", "year"]).reset_index(drop=True))
    _save(df, path)
    return df
