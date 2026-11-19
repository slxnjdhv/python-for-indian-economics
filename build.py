"""Build the book: execute every chapter and produce public lab notebooks.

Usage
-----
    python build.py            # build all chapters
    python build.py ch01       # build chapters whose file name starts with ch01

For each chapters/chNN_*.py (jupytext percent format) this writes

* notebooks/chNN_*.ipynb : the full chapter, executed, with outputs
                           (manuscript; PRIVATE, not pushed to GitHub)
* labs/chNN_*.ipynb      : code cells and section headings only, no outputs,
                           with an "Open in Colab" badge and a setup cell
                           (PUBLIC, companion code for readers)

The build fails loudly if any cell raises an error, so a chapter that builds
is a chapter whose code works.
"""

import os
import sys
from pathlib import Path

# Keep each kernel small: one maths thread is plenty for teaching data sets,
# and it stops NumPy's BLAS reserving memory for every CPU core.
for _var in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_var, "1")

import jupytext
import nbformat
from nbclient import NotebookClient

# ---- Public repository settings (edit once the GitHub repo exists) --------
GITHUB_USER = "slxnjdhv"
GITHUB_REPO = "python-for-indian-economics"
BOOK_TITLE = "Python for Indian Economics Students"
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent
SRC, OUT, LABS = ROOT / "chapters", ROOT / "notebooks", ROOT / "labs"


def make_lab(nb: nbformat.NotebookNode, stem: str) -> nbformat.NotebookNode:
    """Keep code and headings; drop prose and outputs."""
    colab = (f"https://colab.research.google.com/github/{GITHUB_USER}/"
             f"{GITHUB_REPO}/blob/main/labs/{stem}.ipynb")
    title = next((line.lstrip("# ").strip()
                  for c in nb.cells if c.cell_type == "markdown"
                  for line in c.source.splitlines() if line.startswith("# ")),
                 stem)
    cells = [
        nbformat.v4.new_markdown_cell(
            f"# {title}\n\n"
            f"Companion code for *{BOOK_TITLE}*. The explanations, "
            f"exercises and discussion are in the book.\n\n"
            f"[![Open In Colab](https://colab.research.google.com/assets/"
            f"colab-badge.svg)]({colab})"),
        nbformat.v4.new_code_cell(
            "# Run this cell first on Google Colab (not needed on your own "
            "computer\n# if you installed requirements.txt).\n"
            "import sys\n"
            "if 'google.colab' in sys.modules:\n"
            f"    !pip install -q git+https://github.com/{GITHUB_USER}/"
            f"{GITHUB_REPO}.git"),
    ]
    for c in nb.cells:
        if c.cell_type == "code":
            cells.append(nbformat.v4.new_code_cell(c.source))
        else:
            heads = [l for l in c.source.splitlines()
                     if l.startswith("## ") or l.startswith("### ")]
            if heads:
                cells.append(nbformat.v4.new_markdown_cell("\n\n".join(heads)))
    lab = nbformat.v4.new_notebook(cells=cells, metadata=nb.metadata)
    return lab


def build(path: Path) -> None:
    nb = jupytext.read(path)
    # Run from the book root so `import indiadata` and data/raw/ resolve.
    NotebookClient(nb, timeout=600, kernel_name="python3",
                   resources={"metadata": {"path": str(ROOT)}}).execute()
    OUT.mkdir(exist_ok=True)
    LABS.mkdir(exist_ok=True)
    nbformat.write(nb, OUT / f"{path.stem}.ipynb")
    nbformat.write(make_lab(nb, path.stem), LABS / f"{path.stem}.ipynb")
    print(f"built  notebooks/{path.stem}.ipynb  +  labs/{path.stem}.ipynb")


if __name__ == "__main__":
    prefix = sys.argv[1] if len(sys.argv) > 1 else ""
    chapters = sorted(SRC.glob(f"{prefix}*.py"))
    if not chapters:
        sys.exit(f"No chapter matches '{prefix}'.")
    for ch in chapters:
        build(ch)
