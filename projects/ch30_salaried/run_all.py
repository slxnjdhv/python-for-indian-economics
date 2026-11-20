"""Rebuild every table and figure from the raw data.

Usage, from the project folder:  python code/run_all.py
Set the environment variable PLFS_DIR if the PLFS files are not in data/plfs.
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code"))
import salaried as s                                        # noqa: E402

PLFS_DIR = Path(os.environ.get("PLFS_DIR", ROOT / "data" / "plfs"))
RAW, CLEAN = ROOT / "data" / "raw", ROOT / "data" / "clean"
TABLES, FIGS = ROOT / "output" / "tables", ROOT / "output" / "figures"
for folder in (CLEAN, TABLES, FIGS):
    folder.mkdir(parents=True, exist_ok=True)

# 1. Clean. Public aggregates are saved; PLFS records stay in memory.
income = s.state_income(RAW / "mospi_nas_pc_nsdp_code25.csv")
income.to_csv(CLEAN / "state_income_2023_24.csv", index=False)
d = s.add_state(s.load_workers(PLFS_DIR), s.state_names(PLFS_DIR), income)

# 2. Analyse and write every output.
tab = s.state_table(d)
tab.round(2).to_csv(TABLES / "table1_state_shares.csv")
table = s.regression_table(s.fit_models(d))
table.tables[0].to_csv(TABLES / "table2_regressions.csv")
(TABLES / "table2_regressions.tex").write_text(table.as_latex(), encoding="utf-8")
(TABLES / "table2_regressions.md").write_text(s.to_markdown(table.tables[0]),
                                              encoding="utf-8")
s.save(s.figure_states(tab), FIGS / "figure1_states")
print(f"done: {len(d):,} workers, {d['state'].nunique()} states")
