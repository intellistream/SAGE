#!/usr/bin/env python3
"""Build a private-title EuroSys review PDF outside the public paper tree."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require_untracked(repo_root: Path, path: Path, label: str) -> None:
    result = subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(path)],
        cwd=repo_root,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if result.returncode == 0:
        raise ValueError(f"{label} must not be Git-tracked: {path}")


def build(
    repo_root: Path,
    title_file: Path,
    system_name_file: Path,
    output_pdf: Path,
) -> dict[str, object]:
    paper_dir = repo_root / "docs" / "papers" / "semantic_mapreduce"
    main_tex = paper_dir / "main.tex"
    if not main_tex.is_file() or not title_file.is_file() or not system_name_file.is_file():
        raise FileNotFoundError("paper source, private title, or private system name is absent")
    _require_untracked(repo_root, title_file, "private title file")
    _require_untracked(repo_root, system_name_file, "private system-name file")
    _require_untracked(repo_root, output_pdf, "submission PDF")

    title = title_file.read_text(encoding="utf-8").strip()
    system_name = system_name_file.read_text(encoding="utf-8").strip()
    if any(not value or "\n" in value or "\r" in value for value in (title, system_name)):
        raise ValueError("private title and system-name files must each contain one line")

    with tempfile.TemporaryDirectory(prefix="semantic-mr-submission-") as tmp:
        stage = Path(tmp)
        shutil.copy2(main_tex, stage / "main.tex")
        shutil.copy2(paper_dir / "references.bib", stage / "references.bib")
        shutil.copytree(paper_dir / "figures", stage / "figures")
        (stage / "anonymous-submission-title.tex").write_text(
            f"\\renewcommand{{\\papertitle}}{{{title}}}\n"
            f"\\renewcommand{{\\systemname}}{{{system_name}}}\n",
            encoding="utf-8",
        )
        build_dir = stage / "build"
        build_dir.mkdir()
        build_result = subprocess.run(
            ["tectonic", "--outdir", str(build_dir), "main.tex"],
            cwd=stage,
            check=True,
            capture_output=True,
            text=True,
        )
        built_pdf = build_dir / "main.pdf"
        if not built_pdf.is_file():
            raise RuntimeError(
                "Tectonic reported success without a PDF: "
                + build_result.stderr[-1000:]
            )
        output_pdf.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(built_pdf, output_pdf)

    page_output = subprocess.run(
        ["pdfinfo", str(output_pdf)],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    pages = next(
        int(line.split(":", 1)[1].strip())
        for line in page_output.splitlines()
        if line.startswith("Pages:")
    )
    return {
        "status": "PASS",
        "publication_anonymized": True,
        "output": str(output_pdf),
        "pages": pages,
        "sha256": _sha256(output_pdf),
        "title_source_tracked": False,
        "system_name_source_tracked": False,
        "output_tracked": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a private-title Semantic MapReduce review PDF."
    )
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--title-file", required=True, type=Path)
    parser.add_argument("--system-name-file", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = build(
        args.repo_root.resolve(),
        args.title_file.resolve(),
        args.system_name_file.resolve(),
        args.output.resolve(),
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
