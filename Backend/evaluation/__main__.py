import argparse
import json
import os
import sys
from pathlib import Path

from evaluation.compare import compare, load
from evaluation.dataset import load_dataset
from evaluation.runner import run_evaluation


def _run(args: argparse.Namespace) -> int:
    judge = None
    if not args.no_judge:
        from evaluation.judge import GroqJudge

        judge = GroqJudge(args.judge_model)
    examples = load_dataset(args.dataset, limit=args.limit, seed=args.seed)
    report = run_evaluation(
        examples,
        base_url=args.api,
        email=args.email,
        password=args.password or os.environ.get("EVAL_PASSWORD", ""),
        judge=judge,
    )
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report["summary"], indent=2))
    return 0


def _compare(args: argparse.Namespace) -> int:
    table, regressions = compare(load(args.baseline), load(args.candidate), args.tolerance)
    print(table)
    if regressions:
        print("\nRégressions :\n- " + "\n- ".join(regressions))
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="evaluation")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="exécuter le jeu de questions contre l'API")
    run.add_argument("--dataset", required=True, help="fichier JSONL FinanceBench")
    run.add_argument("--out", required=True)
    run.add_argument("--api", default="http://127.0.0.1:8000/api/v1")
    run.add_argument("--email", default=os.environ.get("EVAL_EMAIL", "admin@example.com"))
    run.add_argument("--password", default=None, help="sinon variable EVAL_PASSWORD")
    run.add_argument("--limit", type=int, default=None, help="sous-ensemble reproductible")
    run.add_argument("--seed", type=int, default=0)
    run.add_argument("--judge-model", default=None)
    run.add_argument("--no-judge", action="store_true", help="métriques de retrieval seulement")
    run.set_defaults(func=_run)

    cmp_ = sub.add_parser("compare", help="comparer deux rapports (code 1 si régression)")
    cmp_.add_argument("--baseline", required=True)
    cmp_.add_argument("--candidate", required=True)
    cmp_.add_argument("--tolerance", type=float, default=0.02)
    cmp_.set_defaults(func=_compare)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
