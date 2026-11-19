# Python for Indian Economics Students: companion code

Code, lab notebooks and data helpers for the forthcoming book
*Python for Indian Economics Students*. The labs teach Python for economics
using **official Indian data** from MoSPI, the RBI and the NSSO.

## What's here

```
labs/        one notebook per chapter: runnable code with section headings
indiadata/   a small package that downloads official Indian data as pandas tables
data/        created when you run the labs: downloads are cached in data/raw/
             (not part of the repository; PLFS files go in data/plfs/)
```

| Chapter / Appendix | Topic | Open |
|---|---|---|
| 1 | Your First Look at Indian Inflation | [ch01_first_look_at_inflation.ipynb](labs/ch01_first_look_at_inflation.ipynb) |
| 2 | Python as an Economist's Calculator | [ch02_economists_calculator.ipynb](labs/ch02_economists_calculator.ipynb) |
| 3 | Lists, Loops and Decisions | [ch03_lists_loops_decisions.ipynb](labs/ch03_lists_loops_decisions.ipynb) |
| 4 | Getting Indian Data into Python | [ch04_getting_indian_data.ipynb](labs/ch04_getting_indian_data.ipynb) |
| 5 | NumPy and Index Numbers | [ch05_numpy_index_numbers.ipynb](labs/ch05_numpy_index_numbers.ipynb) |
| 6 | pandas I: Tables of the Indian Economy | [ch06_pandas_state_economies.ipynb](labs/ch06_pandas_state_economies.ipynb) |
| 7 | pandas II: Cleaning Messy Indian Data | [ch07_cleaning_messy_data.ipynb](labs/ch07_cleaning_messy_data.ipynb) |
| 8 | Charts and Maps that Tell the Story | [ch08_charts_that_tell_the_story.ipynb](labs/ch08_charts_that_tell_the_story.ipynb) |
| 9 | National Accounts and Growth | [ch09_national_accounts_growth.ipynb](labs/ch09_national_accounts_growth.ipynb) |
| 10 | Prices and Inflation | [ch10_prices_and_inflation.ipynb](labs/ch10_prices_and_inflation.ipynb) |
| 11 | Money, Banking and Monetary Policy | [ch11_money_and_monetary_policy.ipynb](labs/ch11_money_and_monetary_policy.ipynb) |
| 12 | Public Finance | [ch12_public_finance.ipynb](labs/ch12_public_finance.ipynb) |
| 13 | The External Sector | [ch13_external_sector.ipynb](labs/ch13_external_sector.ipynb) |
| 14 | Working with PLFS Unit-Level Data | [ch14_plfs_unit_level_data.ipynb](labs/ch14_plfs_unit_level_data.ipynb) |
| 15 | Poverty and Inequality | [ch15_poverty_inequality.ipynb](labs/ch15_poverty_inequality.ipynb) |
| 16 | Agriculture and Rural India | [ch16_agriculture_rural_india.ipynb](labs/ch16_agriculture_rural_india.ipynb) |
| 17 | Probability and Statistics by Simulation | [ch17_statistics_by_simulation.ipynb](labs/ch17_statistics_by_simulation.ipynb) |
| 18 | Simple and Multiple Regression | [ch18_regression_mincer.ipynb](labs/ch18_regression_mincer.ipynb) |
| 19 | When OLS Goes Wrong | [ch19_when_ols_goes_wrong.ipynb](labs/ch19_when_ols_goes_wrong.ipynb) |
| 20 | Binary Outcomes | [ch20_binary_outcomes.ipynb](labs/ch20_binary_outcomes.ipynb) |
| 21 | Panel Data across Indian States | [ch21_panel_data_states.ipynb](labs/ch21_panel_data_states.ipynb) |
| 22 | Time Series I: Forecasting Inflation | [ch22_forecasting_inflation.ipynb](labs/ch22_forecasting_inflation.ipynb) |
| 23 | Time Series II: Monetary Transmission | [ch23_monetary_transmission_var.ipynb](labs/ch23_monetary_transmission_var.ipynb) |
| 24 | Causal Inference | [ch24_causal_inference.ipynb](labs/ch24_causal_inference.ipynb) |
| 25 | Numerical Methods for Economists | [ch25_numerical_methods.ipynb](labs/ch25_numerical_methods.ipynb) |
| 26 | Optimisation | [ch26_optimisation.ipynb](labs/ch26_optimisation.ipynb) |
| 27 | Difference Equations and Markov Chains | [ch27_markov_chains.ipynb](labs/ch27_markov_chains.ipynb) |
| 28 | Growth Models and Simulation | [ch28_growth_models.ipynb](labs/ch28_growth_models.ipynb) |
| 29 | Machine Learning and Text for Economists | [ch29_ml_and_text.ipynb](labs/ch29_ml_and_text.ipynb) |
| 30 | Your Dissertation in Python | [ch30_dissertation_in_python.ipynb](labs/ch30_dissertation_in_python.ipynb) |
| A | Field Guide to Indian Data Sources | [appA_indian_data_sources.ipynb](labs/appA_indian_data_sources.ipynb) |
| B | Python Cheat-Sheet for Economists | [appB_python_cheatsheet.ipynb](labs/appB_python_cheatsheet.ipynb) |
| C | Installing Python and Using Colab | [appC_installing_python.ipynb](labs/appC_installing_python.ipynb) |
| D | Stata, SPSS, R, EViews and Excel → Python Translation Table | [appD_stata_r_translation.ipynb](labs/appD_stata_r_translation.ipynb) |

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
