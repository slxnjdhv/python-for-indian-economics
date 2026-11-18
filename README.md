# Python for Indian Economics Students: companion code

Code, lab notebooks and data helpers for the forthcoming book
*Python for Indian Economics Students*. The labs teach Python for economics
using **official Indian data** from MoSPI, the RBI and the NSSO.

## What's here

```
labs/        one notebook per chapter: runnable code with section headings
indiadata/   a small package that downloads official Indian data as pandas tables
data/raw/    dated snapshots of the data used in the book
```

| Chapter | Topic | Open |
|---|---|---|
| 1 | Your First Look at Indian Inflation | [labs/ch01_first_look_at_inflation.ipynb](labs/ch01_first_look_at_inflation.ipynb) |
| 14 | Working with PLFS Unit-Level Data | [labs/ch14_plfs_unit_level_data.ipynb](labs/ch14_plfs_unit_level_data.ipynb) |

## Run in Google Colab (no installation)

Open a lab notebook and click **Open in Colab**. The first cell installs `indiadata`.

## Run on your own computer

```
python -m venv .venv
.venv\Scripts\activate          # Windows   (Mac/Linux: source .venv/bin/activate)
pip install -r requirements.txt
pip install -e .
jupyter lab                     # or open the labs/ folder in VS Code
```

## Using `indiadata`

```python
from indiadata import mospi_cpi, worldbank

cpi = mospi_cpi(sector="combined")      # monthly CPI, base 2012=100, MoSPI eSankhyiki API
gdp = worldbank("NY.GDP.MKTP.KD.ZG")    # India's real GDP growth, World Bank
```

Every download is cached in `data/raw/` with the date it was fetched.

### PLFS unit-level data (Chapter 14)

MoSPI does not allow PLFS microdata to be redistributed, so this repository
contains **no PLFS data**. Register free at <https://microdata.gov.in>, open
*Periodic Labour Force Survey (PLFS), July 2023–June 2024*, download the CSV zip
and the data layout workbook, and unzip them into `data/plfs/`. Then:

```python
from indiadata import read_plfs, labour_status, labour_rates

p = read_plfs("perv1", columns=["sex", "age", "pas", "sas"])  # readable names + survey weight
p["status"] = labour_status(p["pas"], p["sas"])               # usual status (ps+ss)
labour_rates(p[p["age"] >= 15])                                # LFPR 60.1, WPR 58.2, UR 3.2
```

| Source | Data | Access |
|---|---|---|
| MoSPI eSankhyiki API | Consumer Price Index (base 2012) | `mospi_cpi()` |
| World Bank Indicators API | Annual macro series | `worldbank()` |
| RBI DBIE | Rates, money, credit | Manual download (site blocks scripted access) |
| MoSPI Microdata Portal | PLFS, HCES unit-level data | Free registration at microdata.gov.in |

## Licence

Code: MIT (see `LICENSE`). Data belong to their original publishers.
The book text is not part of this repository.
