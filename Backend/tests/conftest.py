"""Configuration pytest : environnement de test et remise à zéro optionnelle de la base.

Les tests créent des comptes et des documents aux noms fixes : ils supposent une base vide.
SQLite (par défaut) est un fichier temporaire neuf à chaque exécution. Sur PostgreSQL, la CI
démarre d'une base vierge ; en local, `RAG_TEST_RESET_DB=1` vide le schéma `public` avant les
tests (à n'utiliser QUE sur une base jetable : toutes les données sont supprimées).
"""

import os

import pytest

from tests.api_stub import install

install()


@pytest.fixture(scope="session", autouse=True)
def reset_postgres_schema():
    from sqlalchemy import text

    from api.database import get_engine

    engine = get_engine()
    if engine.dialect.name == "postgresql" and os.environ.get("RAG_TEST_RESET_DB") == "1":
        with engine.begin() as connection:
            connection.execute(text("DROP SCHEMA public CASCADE"))
            connection.execute(text("CREATE SCHEMA public"))
    yield
