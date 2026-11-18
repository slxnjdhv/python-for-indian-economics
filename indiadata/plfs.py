"""Read Periodic Labour Force Survey (PLFS) unit-level files.

PLFS microdata are free but **not** redistributable: each user must register
at https://microdata.gov.in, accept MoSPI's terms and download the files
themselves. This module therefore ships no data. It only reads the CSV files
and the official data-layout workbook that you downloaded.

Expected folder (default ``data/plfs``)::

    data/plfs/
        perv1.csv   hhv1.csv   perrv.csv   hhrv.csv
        Data_LayoutPLFS_2023-24.xlsx

The raw CSV headers are long and inconsistent (``b5pt1q3_perv1``,
``NSS_perv1``, ``b4q1_pervv`` ...). The layout workbook has one sheet per file
with a short, documented ``Field_Name`` for every column (``sex``, ``age``,
``pas`` for principal activity status ...). ``read_plfs`` renames the columns
by position using that sheet and adds the survey weight.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

PLFS_DIR = Path.cwd() / "data" / "plfs"

# Activity status codes used in PLFS.
WORKER_CODES = range(11, 52)        # usual status: 11-51 self-employed, regular, casual
CWS_WORKER_CODES = range(11, 73)    # weekly status adds 61-72: had work but did
                                    # not work that week (sickness, holiday ...)
UNEMPLOYED_CODES = (81, 82)         # 81 sought work; 82 (CWS) available only
SECTORS = {1: "Rural", 2: "Urban"}
SEXES = {1: "Male", 2: "Female", 3: "Transgender"}


def _find_layout(folder: Path) -> Path:
    found = sorted(folder.glob("Data_Layout*.xlsx"))
    if not found:
        raise FileNotFoundError(
            f"No Data_Layout*.xlsx in {folder}. Download it from the PLFS "
            "'Related materials' page on microdata.gov.in.")
    return found[0]


def layout_names(file: str = "perv1", folder: str | Path = PLFS_DIR) -> list[str]:
    """Short field names for one PLFS file, from the official layout workbook."""
    folder = Path(folder)
    sheet = pd.read_excel(_find_layout(folder), sheet_name=file.lower())
    names = sheet["Field_Name"].dropna().astype(str).str.strip().tolist()
    return names


def read_plfs(file: str = "perv1", folder: str | Path = PLFS_DIR,
              columns: list[str] | None = None) -> pd.DataFrame:
    """Read one PLFS CSV file with short column names and a survey weight.

    Parameters
    ----------
    file : "perv1" (persons, first visit), "hhv1" (households, first visit),
           "perrv" / "hhrv" (urban revisits).
    folder : where the CSV files and the layout workbook are.
    columns : short names to keep (e.g. ["sex", "age", "pas"]); the design
              and weight columns are always kept. ``None`` keeps everything.

    Returns
    -------
    DataFrame with layout names as columns plus ``weight``: the number of
    people (or households) in the population that each record stands for, for
    estimates over the whole survey year.

    The weight follows MoSPI's documented rule for annual estimates:
    ``mult / 100`` when ``nss == nsc`` (only one of the two sub-samples has
    households in that stratum, so it carries the full weight) and
    ``mult / 200`` otherwise (two sub-samples, so each carries half), divided
    by ``no_qtr``, the number of quarters in which the stratum was surveyed.
    """
    folder = Path(folder)
    path = folder / f"{file.lower()}.csv"
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Register at https://microdata.gov.in, download "
            "the PLFS CSV zip and unzip it into this folder.")

    names = layout_names(file, folder)
    header = pd.read_csv(path, nrows=0).columns
    if len(header) != len(names):
        raise ValueError(f"{path.name} has {len(header)} columns but the layout "
                         f"lists {len(names)}; check you have the same year.")
    rename = dict(zip(header, names))

    design = ["qtr", "visit", "sec", "st", "strm", "sstrm", "ss", "mfsu",
              "nss", "nsc", "mult", "no_qtr"]
    keep = None
    if columns is not None:
        wanted = list(dict.fromkeys(design + list(columns)))
        missing = set(wanted) - set(names)
        if missing:
            raise KeyError(f"Not in the {file} layout: {sorted(missing)}")
        keep = [h for h, n in rename.items() if n in wanted]

    # Read in chunks and shrink each one, so that the full person file fits in
    # the memory of an ordinary laptop or a free Colab session.
    text_cols = [h for h, n in rename.items() if n in ("file_id", "qtr", "visit")]
    chunks = []
    for chunk in pd.read_csv(path, usecols=keep, chunksize=100_000,
                             dtype={h: "string" for h in text_cols
                                    if keep is None or h in keep}):
        chunk = chunk.rename(columns=rename)
        for col in chunk.columns:
            if col in ("mult",):
                continue                     # keep the multiplier exact
            if pd.api.types.is_numeric_dtype(chunk[col]):
                chunk[col] = chunk[col].astype("float32")
            else:
                chunk[col] = chunk[col].astype("category")
        chunks.append(chunk)
    df = pd.concat(chunks, ignore_index=True)
    del chunks
    for col in df.columns:
        if isinstance(df[col].dtype, pd.CategoricalDtype) or df[col].dtype == object:
            df[col] = df[col].astype("category")  # categories may differ by chunk
        elif df[col].dtype == "float32":
            x = df[col]
            if (x.dropna() % 1 == 0).all():       # codes, ages, rupees: whole numbers
                df[col] = x.astype("Int32")       # nullable integer keeps blanks

    weight = (np.where(df["nss"] == df["nsc"], df["mult"] / 100,
                       df["mult"] / 200) / df["no_qtr"])
    return df.assign(weight=weight)


def labour_status(code: pd.Series, subsidiary: pd.Series | None = None,
                  weekly: bool = False) -> pd.Series:
    """Classify activity status codes as 'employed', 'unemployed' or 'out of LF'.

    * Usual status (ps+ss), the headline PLFS measure: pass the principal
      status ``pas`` and the subsidiary status ``sas``. Anyone working in
      either capacity counts as employed.
    * Current weekly status: pass ``acws`` with ``weekly=True``.
    """
    workers = CWS_WORKER_CODES if weekly else WORKER_CODES
    employed = code.isin(workers)
    if subsidiary is not None:
        employed = employed | subsidiary.isin(workers)
    unemployed = code.isin(UNEMPLOYED_CODES) & ~employed
    return pd.Series(np.select([employed, unemployed],
                               ["employed", "unemployed"], "out of LF"),
                     index=code.index)


def labour_rates(df: pd.DataFrame, status: str = "status",
                 weight: str = "weight") -> pd.Series:
    """Weighted LFPR, WPR and UR (in %) for the rows of ``df``.

    LFPR = labour force / population; WPR = employed / population;
    UR = unemployed / labour force.
    """
    w = df[weight]
    total = w.sum()
    emp = w[df[status] == "employed"].sum()
    unemp = w[df[status] == "unemployed"].sum()
    return pd.Series({"LFPR": 100 * (emp + unemp) / total,
                      "WPR": 100 * emp / total,
                      "UR": 100 * unemp / (emp + unemp)})
