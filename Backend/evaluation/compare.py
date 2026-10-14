"""Compare deux rapports d'évaluation et signale les régressions."""

import json
from pathlib import Path
from typing import Any

# (clé, libellé, plus grand = mieux)
METRICS = [
    ("accuracy", "Exactitude", True),
    ("faithfulness", "Fidélité", True),
    ("retrieval_doc_hit", "Document trouvé", True),
    ("retrieval_page_hit", "Page trouvée", True),
    ("error_rate", "Taux d'erreur", False),
    ("latency_mean", "Latence moyenne (s)", False),
    ("latency_p95", "Latence p95 (s)", False),
]


def load(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))["summary"]


def compare(
    baseline: dict[str, Any], candidate: dict[str, Any], tolerance: float = 0.02
) -> tuple[str, list[str]]:
    """Retourne (tableau markdown, régressions).

    Une régression est une baisse de qualité (ou une hausse d'erreurs) supérieure à
    `tolerance` en valeur absolue ; la latence est rapportée mais n'est pas bloquante.
    """
    lines = ["| Métrique | Référence | Candidat | Écart |", "|---|---|---|---|"]
    regressions = []
    for key, label, higher_is_better in METRICS:
        before, after = baseline.get(key), candidate.get(key)
        if before is None or after is None:
            lines.append(f"| {label} | n/a | n/a | |")
            continue
        delta = after - before
        lines.append(f"| {label} | {before:.3f} | {after:.3f} | {delta:+.3f} |")
        is_latency = key.startswith("latency")
        worse = delta < -tolerance if higher_is_better else delta > tolerance
        if worse and not is_latency:
            regressions.append(f"{label} : {before:.3f} -> {after:.3f}")
    return "\n".join(lines), regressions
