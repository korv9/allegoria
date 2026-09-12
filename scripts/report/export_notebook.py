"""Export a `# %%` percent-format script to .ipynb.

    python scripts/report/export_notebook.py notebooks/01_pipeline_walkthrough.py
    python scripts/report/export_notebook.py notebooks/01_pipeline_walkthrough.py --execute

The `.py` stays the source of truth. It is what git diffs as text, what ruff
lints, and what gets edited; the `.ipynb` is a build artifact regenerated from
it. Editing the `.ipynb` and expecting the change to survive is a mistake --
the next export overwrites it.

Outputs are excluded unless `--execute` is passed. A notebook that stores its
outputs diffs badly and starts carrying stale numbers that look authoritative,
which is exactly the failure mode the walkthrough exists to prevent.

Uses `nbformat` and, for `--execute`, `nbclient` -- both already present via
ipykernel, so this adds no dependency.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import nbformat

CELL_MARKER = "# %%"
MARKDOWN_MARKER = "# %% [markdown]"


def split_cells(source: str) -> list[tuple[str, str]]:
    """Split percent-format source into (kind, body) pairs, kind in {code, markdown}."""
    cells: list[tuple[str, str]] = []
    kind = "code"
    body: list[str] = []

    for line in source.splitlines():
        if line.startswith(CELL_MARKER):
            if body:
                cells.append((kind, "\n".join(body)))
            kind = "markdown" if line.startswith(MARKDOWN_MARKER) else "code"
            body = []
        else:
            body.append(line)
    if body:
        cells.append((kind, "\n".join(body)))

    return [(kind, text) for kind, text in cells if text.strip()]


def strip_comment_prefix(text: str) -> str:
    """Turn a commented markdown block back into markdown."""
    lines = []
    for line in text.splitlines():
        if line.startswith("# "):
            lines.append(line[2:])
        elif line.strip() == "#":
            lines.append("")
        else:
            lines.append(line)
    return "\n".join(lines).strip("\n")


def to_notebook(source: str) -> nbformat.NotebookNode:
    notebook = nbformat.v4.new_notebook()
    for kind, body in split_cells(source):
        if kind == "markdown":
            notebook.cells.append(nbformat.v4.new_markdown_cell(strip_comment_prefix(body)))
        else:
            notebook.cells.append(nbformat.v4.new_code_cell(body.strip("\n")))

    notebook.metadata["kernelspec"] = {
        "display_name": "Python 3",
        "language": "python",
        "name": "python3",
    }
    notebook.metadata["language_info"] = {"name": "python", "pygments_lexer": "ipython3"}
    return notebook


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="the .py percent-format script")
    parser.add_argument("--out", type=Path, help="defaults to the source with .ipynb")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="run the notebook and store outputs; slow, and the result diffs badly",
    )
    args = parser.parse_args()

    destination = args.out or args.source.with_suffix(".ipynb")
    notebook = to_notebook(args.source.read_text(encoding="utf-8"))

    if args.execute:
        from nbclient import NotebookClient

        NotebookClient(
            notebook,
            timeout=1200,
            kernel_name="python3",
            resources={"metadata": {"path": str(args.source.parent.resolve())}},
        ).execute()

    nbformat.write(notebook, destination)

    code = sum(cell.cell_type == "code" for cell in notebook.cells)
    markdown = sum(cell.cell_type == "markdown" for cell in notebook.cells)
    outputs = "with outputs" if args.execute else "no outputs"
    print(f"NOTEBOOK | {code} code + {markdown} markdown cells | {outputs} | {destination}")


if __name__ == "__main__":
    main()
