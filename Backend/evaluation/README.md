# Évaluation du RAG

Mesure la qualité des réponses sur **FinanceBench** (150 questions annotées sur des 10-K / 10-Q) :

| Métrique | Sens |
|---|---|
| `accuracy` | réponse jugée équivalente à la référence (juge LLM) |
| `faithfulness` | affirmations appuyées par les extraits cités (juge LLM) |
| `retrieval_doc_hit` / `retrieval_page_hit` | le document / la page de preuve annotés sont parmi les citations (sans LLM) |
| `error_rate`, `latency_mean`, `latency_p95` | robustesse et performance |

## Procédure

```bash
# 1. Télécharger le jeu (JSONL) : https://huggingface.co/datasets/PatronusAI/financebench
# 2. Lancer l'API avec le corpus indexé, puis :
uv run python -m evaluation run --dataset financebench.jsonl --out results/new.json \
    --email admin@example.com --password '...'          # EVAL_PASSWORD possible
#    --limit 20 : sous-ensemble reproductible ; --no-judge : retrieval seulement (sans LLM)
# 3. Comparer à la référence :
uv run python -m evaluation compare --baseline results/baseline.json --candidate results/new.json
```

`compare` retourne le code 1 si l'exactitude, la fidélité, le retrieval ou le taux d'erreur
régressent de plus de 2 points (`--tolerance`) ; la latence est rapportée sans bloquer.

## Mesure de référence (L3.1)

La référence doit être mesurée **avant** les modifications du lot 3, avec l'ancien pipeline
(commit `091ac7c`, tête de la branche `lot-2-fondations-backend`) :

```bash
git checkout 091ac7c          # ancien pipeline (graphe LangGraph à 8-20 appels, Chroma + BM25)
# indexer le corpus, lancer l'API, puis :
uv run python -m evaluation run --dataset financebench.jsonl --out results/baseline.json
```

Les rapports de `results/` ne sont pas versionnés (sorties locales).
