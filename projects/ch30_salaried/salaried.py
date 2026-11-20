"""Do richer states have more salaried jobs?  Project functions.

All cleaning lives here; the notebook and run_all.py only call these
functions. PLFS unit records are read into memory, never written to disk.
"""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from statsmodels.iolib.summary2 import summary_col

from indiadata import read_plfs

# gedu_lvl codes (PLFS Schedule 10.4, see Chapter 18) in five levels
EDU = {1: "None", 2: "None", 3: "None", 4: "None", 5: "Primary",
       6: "Primary", 7: "Middle/secondary", 8: "Middle/secondary",
       10: "Higher sec./diploma", 11: "Higher sec./diploma",
       12: "Graduate+", 13: "Graduate+"}
EDU_ORDER = ["None", "Primary", "Middle/secondary", "Higher sec./diploma",
             "Graduate+"]
CROSSWALK = {"Tamilnadu": "Tamil Nadu", "Puduchery": "Puducherry",
             "Andaman & N. Island": "Andaman & Nicobar Islands"}  # Chapter 7
UNION_TERRITORIES = ["Andaman & Nicobar Islands", "Chandigarh", "Delhi",
                     "Jammu & Kashmir", "Puducherry"]


def state_names(plfs_dir):
    """PLFS state codes with NAS-style names, from the layout workbook."""
    layout = next(Path(plfs_dir).glob("Data_Layout*.xlsx"))
    st = pd.read_excel(layout, sheet_name="State code", header=1)
    st.columns = ["st", "plfs_name"]
    st = st.dropna().astype({"st": int})
    st["state"] = st["plfs_name"].str.strip().replace(CROSSWALK)
    assert st["st"].is_unique
    return st[["st", "state"]]


def state_income(raw_csv, year="2023-24"):
    """Per capita NSDP at current prices (Rs) in one fiscal year."""
    raw = pd.read_csv(raw_csv, dtype=str)
    inc = raw[raw["year"] == year].copy()
    inc["pc_nsdp"] = pd.to_numeric(inc["current_price"], errors="raise")
    assert inc["unit"].eq("₹").all() and inc["state"].is_unique
    inc["log_pc"] = np.log(inc["pc_nsdp"] / 1e5)          # log of Rs lakh
    return inc[["state", "pc_nsdp", "log_pc"]].reset_index(drop=True)


def load_workers(plfs_dir):
    """Workers aged 15-59 by usual principal status: one row per person."""
    p = read_plfs("perv1", folder=plfs_dir,
                  columns=["sex", "age", "gedu_lvl", "pas"])
    w = p[p["pas"].between(11, 51) & p["age"].between(15, 59)
          & p["sex"].isin([1, 2])]
    d = pd.DataFrame({
        "salaried": (w["pas"] == 31).astype(float),
        "female": (w["sex"] == 2).astype(float),
        "urban": (w["sec"] == 2).astype(float),
        "age": w["age"].astype(float),
        "edu": pd.Categorical(w["gedu_lvl"].map(EDU), categories=EDU_ORDER),
        "st": w["st"].astype(int),
        "weight": w["weight"].astype(float)})
    assert d["edu"].notna().all(), "unmapped education code"
    return d.reset_index(drop=True)


def add_state(workers, names, income):
    """Attach state names and income; keep states with an income figure."""
    d = workers.merge(names, on="st", how="left", validate="many_to_one")
    d = d.merge(income, on="state", how="inner", validate="many_to_one")
    d["w_norm"] = d["weight"] / d["weight"].mean()       # weights averaging 1
    return d


def state_table(d):
    """Weighted state shares (%) and sample sizes: aggregates only."""
    def one(g):
        w = g["weight"]
        return pd.Series({
            "salaried_pct": 100 * np.average(g["salaried"], weights=w),
            "graduate_pct": 100 * np.average(g["edu"] == "Graduate+", weights=w),
            "urban_pct": 100 * np.average(g["urban"], weights=w),
            "workers_mn": w.sum() / 1e6, "sample": len(g),
            "pc_nsdp": g["pc_nsdp"].iloc[0]})
    cols = ["salaried", "edu", "urban", "weight", "pc_nsdp"]
    return d.groupby("state")[cols].apply(one).sort_values("pc_nsdp")


CONTROLS = "female + urban + age + I(age**2 / 100)"
FORMULAS = {"(1)": "salaried ~ log_pc",
            "(2)": "salaried ~ log_pc + " + CONTROLS,
            "(3)": "salaried ~ log_pc + " + CONTROLS + " + C(edu)",
            "(4)": "salaried ~ log_pc + " + CONTROLS + " + C(edu)"}


def fit_models(d):
    """Weighted linear probability models, SEs clustered by state.
    Model (4) repeats (3) without the union territories."""
    out = {}
    for name, formula in FORMULAS.items():
        data = d[~d["state"].isin(UNION_TERRITORIES)] if name == "(4)" else d
        res = smf.wls(formula, data=data, weights=data["w_norm"]).fit(
            cov_type="cluster", cov_kwds={"groups": data["st"]})
        res.n_clusters = data["st"].nunique()
        out[name] = res
    return out


LABELS = {"log_pc": "Log per capita NSDP", "female": "Female",
          "urban": "Urban", "age": "Age", "I(age ** 2 / 100)": "Age squared / 100",
          **{f"C(edu)[T.{e}]": f"Education: {e}" for e in EDU_ORDER[1:]},
          "Intercept": "Constant"}


def regression_table(models):
    """Side-by-side table of all models, built with summary_col."""
    table = summary_col(
        list(models.values()), model_names=list(models), stars=True,
        float_format="%.3f", regressor_order=list(LABELS), drop_omitted=True,
        info_dict={"Observations": lambda r: f"{int(r.nobs):,}",
                   "States (clusters)": lambda r: str(r.n_clusters)})
    t = table.tables[0]
    t.index = [LABELS.get(i, i) for i in t.index]
    return table


def to_markdown(df):
    """A Markdown table without extra packages."""
    head = "| | " + " | ".join(map(str, df.columns)) + " |"
    rule = "|---" * (len(df.columns) + 1) + "|"
    rows = ["| " + str(i) + " | " + " | ".join(map(str, r)) + " |"
            for i, r in zip(df.index, df.to_numpy())]
    return "\n".join([head, rule, *rows])


STYLE = {"font.size": 9, "axes.titlesize": 9.5, "axes.labelsize": 9,
         "xtick.labelsize": 8, "ytick.labelsize": 8,
         "axes.spines.top": False, "axes.spines.right": False,
         "pdf.fonttype": 42, "figure.dpi": 100, "figure.facecolor": "white"}
OFFSETS = {"Bihar": (5, 3), "Uttar Pradesh": (6, 4), "Kerala": (4, 3),
           "Maharashtra": (6, -10), "Delhi": (-26, 4), "Goa": (4, -9),
           "Sikkim": (-14, 6)}


def figure_states(tab):
    """Figure 1: salaried and graduate shares against state income."""
    from matplotlib.ticker import NullFormatter
    with plt.rc_context(STYLE):
        fig, axes = plt.subplots(1, 2, figsize=(6.3, 2.9), sharex=True,
                                 layout="constrained")
        x = tab["pc_nsdp"] / 1e3
        for ax, col, title in zip(axes, ["salaried_pct", "graduate_pct"],
                                  ["(a) Salaried, % of workers",
                                   "(b) Graduates, % of workers"]):
            ax.scatter(x, tab[col], s=8 + 2.5 * tab["workers_mn"],
                       color="#1f4e79", alpha=0.6, edgecolor="white", lw=0.5)
            b = np.polyfit(np.log(x), tab[col], 1, w=np.sqrt(tab["workers_mn"]))
            grid = np.linspace(np.log(x.min()), np.log(x.max()), 50)
            ax.plot(np.exp(grid), np.polyval(b, grid), color="#c55a11", lw=1)
            for st, off in OFFSETS.items():
                ax.annotate(st, (x[st], tab.loc[st, col]), xytext=off,
                            textcoords="offset points", fontsize=7)
            ax.set_xscale("log")
            ax.set_xticks([60, 100, 200, 400], labels=["60", "100", "200", "400"])
            ax.xaxis.set_minor_formatter(NullFormatter())
            ax.set_title(title, loc="left")
        fig.supxlabel("Per capita NSDP 2023-24, Rs thousand (log scale)",
                      fontsize=9)
    return fig


def save(fig, stem):
    """Save as vector PDF and 300-dpi PNG; no timestamps, so reruns match."""
    fig.savefig(Path(stem).with_suffix(".pdf"), bbox_inches="tight",
                metadata={"CreationDate": None})
    fig.savefig(Path(stem).with_suffix(".png"), bbox_inches="tight", dpi=300)
