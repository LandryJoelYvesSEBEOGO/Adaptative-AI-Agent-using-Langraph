"""Exporte le schéma OpenAPI de l'API dans Frontend/openapi.json (source du client TypeScript).

uv run python -m scripts.export_openapi          # écrit le fichier
uv run python -m scripts.export_openapi --check  # échoue s'il n'est plus à jour (CI)
"""

import argparse
import json
import os
import sys
from pathlib import Path

TARGET = Path(__file__).resolve().parents[2] / "Frontend" / "openapi.json"


def build_schema() -> dict:
    # L'export n'a besoin ni de base ni de clés : valeurs neutres pour importer l'application.
    os.environ.setdefault("JWT_SECRET_KEY", "openapi-export-" + "x" * 32)
    from api.main import app

    return app.openapi()


def render(schema: dict) -> str:
    return json.dumps(schema, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    content = render(build_schema())
    if args.check:
        if not TARGET.exists() or TARGET.read_text(encoding="utf-8") != content:
            print(
                f"{TARGET} n'est pas à jour : lancer `uv run python -m scripts.export_openapi` "
                "puis `npm run api:generate` dans Frontend/.",
                file=sys.stderr,
            )
            return 1
        return 0
    TARGET.write_text(content, encoding="utf-8")
    print(f"Écrit : {TARGET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
