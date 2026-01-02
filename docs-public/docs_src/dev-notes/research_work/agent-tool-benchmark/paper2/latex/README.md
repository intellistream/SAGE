# Paper 2 LaTeX Package

## Structure

- `main.tex`: ICML-style shell referencing modular section files.
- `references.bib`: Placeholder bibliography entries.
- `sections/`: Add `introduction.tex`, `method.tex`, etc. (not included by default).

## Compile

```bash
cd docs/dev-notes/research_work/agent-tool-benchmark/paper2/latex
pdflatex main.tex
bibtex main
pdflatex main.tex
pdflatex main.tex
```

Ensure `icml2025.sty` is on the TEXINPUTS path (download from ICML website).
