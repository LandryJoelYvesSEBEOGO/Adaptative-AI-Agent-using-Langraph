"""Évaluation de la qualité du RAG sur un jeu de référence (FinanceBench).

    python -m evaluation run     --dataset financebench.jsonl --out results/new.json
    python -m evaluation compare --baseline results/baseline.json --candidate results/new.json

Le jeu FinanceBench (150 questions annotées) se télécharge depuis
https://huggingface.co/datasets/PatronusAI/financebench (fichier JSONL).
"""
