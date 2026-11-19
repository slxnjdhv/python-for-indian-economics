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
from io import StringIO
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


# ---------------------------------------------------------------------------
# MoSPI eSankhyiki API: a general fetcher and one wrapper per data set
# ---------------------------------------------------------------------------
_MOSPI = "https://api.mospi.gov.in/api/"


def mospi(endpoint: str, refresh: bool = False, **params) -> pd.DataFrame:
    """Download every page of any MoSPI eSankhyiki API endpoint.

    ``endpoint`` is the part after /api/, e.g. "iip/getIIPMonthly";
    ``params`` are the API's own filters (base_year=..., year=...).
    The raw table comes back with the API's column names, all as text,
    and is cached in data/raw/.
    """
    tag = "_".join(f"{k}-{v}" for k, v in sorted(params.items()))
    name = ("mospi_" + endpoint.replace("/", "_") + ("_" + tag if tag else "")
            ).replace(" ", "")
    path = _cache_path(name)
    if path.exists() and not refresh:
        return pd.read_csv(path, dtype=str).drop(columns="fetched_on")

    def one_pass() -> tuple[list, int]:
        rows, page, total = [], 1, 0
        while True:
            reply = requests.get(_MOSPI + endpoint,
                                 params={**params, "limit": 200, "page": page,
                                         "Format": "JSON"},
                                 headers=_HEADERS, timeout=90)
            reply.raise_for_status()
            body = reply.json()
            rows.extend(body.get("data") or [])
            meta = body.get("meta_data") or {}
            total = meta.get("totalRecords", len(rows))
            if page >= meta.get("totalPages", 1):
                break
            page += 1
        return rows, total

    # Keep only distinct rows. If a pass returns fewer distinct rows than the
    # API reports, try again in case pages shifted while we read them; stop
    # as soon as a new pass adds nothing (then the API itself repeats rows).
    seen: dict[tuple, dict] = {}
    total = 0
    for _ in range(3):
        before = len(seen)
        rows, total = one_pass()
        for r in rows:
            seen.setdefault(tuple(sorted((k, str(v)) for k, v in r.items())), r)
        if len(seen) >= total or (before and len(seen) == before):
            break
    if not seen:
        raise ValueError(f"MoSPI returned no data for {endpoint} {params}.")
    if len(seen) < total:
        import warnings
        warnings.warn(f"MoSPI {endpoint}: the API reports {total} rows but only "
                      f"{len(seen)} are distinct; it repeats "
                      f"{total - len(seen)} row(s). Duplicates were dropped.")
    df = pd.DataFrame(list(seen.values())).astype("string")
    df = df.replace({"None": pd.NA, "nan": pd.NA, "": pd.NA})
    _save(df, path)
    return df


def _add_month(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["date"] = pd.to_datetime(dict(year=df["year"].astype(int),
                                     month=df["month"].map(_MONTHS), day=1))
    return df


# Order in which a year's national-accounts estimate is revised.
NAS_REVISIONS = ["First Advance Estimates", "Second Advance Estimates",
                 "Provisional Estimates", "First Revised Estimates",
                 "Second Revised Estimates", "Third Revised Estimates",
                 "Final Estimates", "Additional Revision"]

NAS_INDICATORS = {
    "GVA": 1, "net taxes": 2, "GDP": 5, "CFC": 6, "NDP": 7,
    "GCF by industry": 8, "GFCF": 9, "PFCE": 10, "GFCE": 11,
    "change in stocks": 12, "valuables": 13, "exports": 14, "imports": 15,
    "GNI": 17, "GNDI": 19, "gross saving": 20, "GVA growth": 21,
    "GDP growth": 22, "GSDP": 23, "NSDP": 24,
    "per capita NSDP": 25, "per capita NSDP growth": 28,
    "GSVA by industry": 29, "NSVA by industry": 30,
    "per capita GSDP": 31,
    # Code 32 (per capita NSDP, wider state coverage) exists but its Karnataka
    # constant-price values duplicate code 31's current-price values (an error
    # at source, Nov 2026); use 25 unless you need the extra states.
}


def mospi_nas(indicator="GDP", frequency: str = "annual",
              base_year: str = "2011-12", latest: bool = True,
              refresh: bool = False) -> pd.DataFrame:
    """National Accounts Statistics from MoSPI.

    Units are in the ``unit`` column: Rs crore for most indicators, but
    rupees for the per-capita codes (25, 31, 32) and Rs lakh for state GSVA
    by industry (29). Always check ``unit`` before adding or comparing.

    ``indicator`` is a key of ``NAS_INDICATORS`` (e.g. "GDP", "PFCE", "GSDP")
    or a numeric indicator code. ``frequency`` is "annual" or "quarterly".
    With ``latest=True`` only the most recent estimate of each period is
    kept; with ``latest=False`` every vintage (advance, provisional,
    revised ...) is returned, which is how you study data revisions.

    Columns: year (fiscal year, e.g. "2023-24"), fy (its first calendar
    year, as a number), quarter, revision, current_price, constant_price,
    plus state / industry / institutional_sector where the indicator has them.
    """
    code = NAS_INDICATORS.get(indicator, indicator)
    freq = {"annual": 1, "quarterly": 2}[frequency]
    df = mospi("nas/getNASData", refresh=refresh, indicator_code=code,
               base_year=base_year, series="Current", frequency_code=freq)
    for col in ("current_price", "constant_price"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["fy"] = df["year"].str[:4].astype(int)
    if "revision" in df.columns and latest:
        rank = {r: i for i, r in enumerate(NAS_REVISIONS)}
        df["_rank"] = df["revision"].map(rank).fillna(-1)
        keys = [c for c in ("year", "quarter", "state", "industry",
                            "subindustry", "institutional_sector")
                if c in df.columns]
        df = (df.sort_values("_rank", kind="stable")
                .groupby(keys, dropna=False, sort=False).tail(1)
                .drop(columns="_rank"))
    drop = [c for c in ("base_year", "series") if c in df.columns]
    sort = [c for c in ("state", "industry", "fy", "quarter") if c in df.columns]
    return df.drop(columns=drop).sort_values(sort).reset_index(drop=True)


def mospi_iip(frequency: str = "monthly", base_year: str = "2011-12",
              refresh: bool = False) -> pd.DataFrame:
    """Index of Industrial Production (general, sectoral and use-based).

    Columns: date (monthly) or year (annual), type, category, sub_category,
    index, growth_rate (% year-on-year, as published).
    """
    ep = {"monthly": "iip/getIIPMonthly", "annual": "iip/getIIPAnnual"}[frequency]
    df = mospi(ep, refresh=refresh, base_year=base_year)
    for col in ("index", "growth_rate"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    if frequency == "monthly":
        df = _add_month(df).sort_values("date")
    return df.reset_index(drop=True)


def mospi_cpi_groups(sector: str = "combined", refresh: bool = False
                     ) -> pd.DataFrame:
    """CPI (base 2012) for all groups and sub-groups, All India, monthly.

    Columns: date, group, subgroup, index, inflation, status.
    """
    df = mospi("cpi/getCPIIndex", refresh=refresh, base_year=2012,
               series="Current", state_code=ALL_INDIA,
               sector_code=CPI_SECTORS[sector])
    df = _add_month(df)
    for col in ("index", "inflation"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return (df[["date", "group", "subgroup", "index", "inflation", "status"]]
            .sort_values(["group", "subgroup", "date"]).reset_index(drop=True))


def mospi_cpi_items(years=range(2013, 2026), base_year: str = "2012",
                    refresh: bool = False) -> pd.DataFrame:
    """CPI item-level indices, All India combined, monthly.

    The API mixes bases: 2013 comes only on the old base 2010, and 2014 on
    both 2010 and 2012. Rows are kept only for ``base_year`` (default 2012),
    so each item has at most one value per month.
    """
    parts = [mospi("cpi/getItemIndex", refresh=refresh, year=y) for y in years]
    df = pd.concat(parts, ignore_index=True)
    df = df[df["baseyear"] == str(base_year)]
    df = _add_month(df)
    for col in ("index", "inflation"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return (df[["date", "item", "index", "inflation", "status"]]
            .sort_values(["item", "date"]).reset_index(drop=True))


def mospi_wpi(years=range(2013, 2027), refresh: bool = False) -> pd.DataFrame:
    """Wholesale Price Index (base 2011-12), every level down to items."""
    parts = [mospi("wpi/getWpiRecords", refresh=refresh, year=y) for y in years]
    df = _add_month(pd.concat(parts, ignore_index=True))
    df["index_value"] = pd.to_numeric(df["index_value"], errors="coerce")
    return df.rename(columns={"index_value": "index"}).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Bank for International Settlements (BIS) and OECD statistics (SDMX APIs)
# ---------------------------------------------------------------------------
def bis(dataset: str, key: str, refresh: bool = False) -> pd.DataFrame:
    """A series from the BIS data portal (https://data.bis.org).

    Useful India series
    -------------------
    bis("WS_CBPOL", "M.IN")             RBI policy (repo) rate, monthly, %
    bis("WS_EER", "M.R.B.IN")           real effective exchange rate, broad
    bis("WS_EER", "M.N.B.IN")           nominal effective exchange rate
    bis("WS_XRU", "M.IN.INR.A")         rupees per US dollar, monthly average
    bis("WS_CREDIT_GAP", "Q.IN.P.A.C")  credit-to-GDP gap

    Returns columns: date, value.
    """
    path = _cache_path(f"bis_{dataset}_{key}")
    if path.exists() and not refresh:
        return pd.read_csv(path, parse_dates=["date"]).drop(columns="fetched_on")
    url = f"https://stats.bis.org/api/v1/data/{dataset}/{key}"
    reply = requests.get(url, params={"format": "csv"}, headers=_HEADERS,
                         timeout=90)
    reply.raise_for_status()
    raw = pd.read_csv(StringIO(reply.text))
    periods = raw["TIME_PERIOD"].astype(str).str.replace("-Q", "Q")
    df = pd.DataFrame({
        "date": pd.PeriodIndex(periods, freq=key[0]).to_timestamp(),
        "value": pd.to_numeric(raw["OBS_VALUE"], errors="coerce")})
    df = df.dropna().sort_values("date").reset_index(drop=True)
    _save(df, path)
    return df


def oecd_rates(refresh: bool = False) -> pd.DataFrame:
    """India's market interest rates from the OECD (monthly, % per year).

    Columns: date, short_rate (3-month interbank rate), long_rate (10-year
    government bond yield).
    """
    path = _cache_path("oecd_rates_IND")
    if path.exists() and not refresh:
        return pd.read_csv(path, parse_dates=["date"]).drop(columns="fetched_on")
    url = ("https://sdmx.oecd.org/public/rest/data/OECD.SDD.STES,"
           "DSD_STES@DF_FINMARK,4.0/IND.M.IR3TIB+IRLT.PA.....")
    reply = requests.get(url, params={"format": "csvfilewithlabels"},
                         headers=_HEADERS, timeout=90)
    reply.raise_for_status()
    raw = pd.read_csv(StringIO(reply.text))
    raw["date"] = pd.to_datetime(raw["TIME_PERIOD"])
    df = (raw.pivot_table(index="date", columns="MEASURE", values="OBS_VALUE")
             .rename(columns={"IR3TIB": "short_rate", "IRLT": "long_rate"})
             .reset_index())
    df.columns.name = None
    _save(df, path)
    return df


# ---------------------------------------------------------------------------
# Penn World Table 10.01 (Feenstra, Inklaar and Timmer 2015)
# ---------------------------------------------------------------------------
def pwt(country: str | None = "IND", refresh: bool = False) -> pd.DataFrame:
    """Penn World Table 10.01: output, capital, labour, human capital, TFP.

    ``country`` is an ISO-3 code; ``None`` returns all 183 countries.
    Key columns: rgdpna (real GDP, mn 2017 US$), rnna (capital stock),
    emp (persons engaged, mn), hc (human capital index), labsh (labour
    share), rtfpna (TFP index, 2017 = 1), pop (mn), avh (annual hours).
    """
    path = RAW_DIR / "pwt1001.dta"
    if not path.exists() or refresh:
        RAW_DIR.mkdir(parents=True, exist_ok=True)
        reply = requests.get("https://dataverse.nl/api/access/datafile/354098",
                             headers=_HEADERS, timeout=180)
        reply.raise_for_status()
        path.write_bytes(reply.content)
    df = pd.read_stata(path)
    if country:
        df = df[df["countrycode"] == country]
    return df.reset_index(drop=True)
