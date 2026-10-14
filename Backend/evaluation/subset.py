"""Prépare un sous-ensemble d'évaluation : N questions et uniquement les PDF qu'elles utilisent.

    python -m evaluation.subset --dataset financebench.jsonl --pdfs financebench/pdfs \
        --limit 20 --out-dir /tmp/eval

Écrit `<out-dir>/questions.jsonl` et copie les PDF nécessaires dans `<out-dir>/pdfs/`.
"""

import argparse
import json
import shutil
import sys
from pathlib import Path

from evaluation.dataset import load_dataset, normalize_doc_name


def build_subset(dataset: Path, pdf_dir: Path, limit: int, out_dir: Path, seed: int = 0) -> dict:
    examples = load_dataset(dataset, limit=limit, seed=seed)
    wanted = {doc for example in examples for doc in example.evidence_docs}
    available = {normalize_doc_name(p.name): p for p in pdf_dir.glob("*.pdf")}

    out_pdfs = out_dir / "pdfs"
    out_pdfs.mkdir(parents=True, exist_ok=True)
    copied, missing = [], []
    for key in sorted(wanted):
        if key in available:
            shutil.copy2(available[key], out_pdfs / available[key].name)
            copied.append(available[key].name)
        else:
            missing.append(key)

    ids = {example.id for example in examples}
    with (
        open(dataset, encoding="utf-8") as src,
        open(out_dir / "questions.jsonl", "w", encoding="utf-8") as dst,
    ):
        for line in src:
            if line.strip() and str(json.loads(line).get("financebench_id")) in ids:
                dst.write(line)
    return {"questions": len(examples), "pdfs": copied, "missing_pdfs": missing}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--pdfs", required=True, type=Path)
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args()
    report = build_subset(args.dataset, args.pdfs, args.limit, args.out_dir, args.seed)
    print(json.dumps(report, indent=2))
    return 1 if report["missing_pdfs"] else 0


if __name__ == "__main__":
    sys.exit(main())
