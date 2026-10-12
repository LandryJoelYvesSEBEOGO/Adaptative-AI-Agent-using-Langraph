"""Le schéma OpenAPI versionné (source du client TypeScript) doit refléter l'API actuelle."""

from tests.api_stub import install

install()

from scripts.export_openapi import TARGET, build_schema, render  # noqa: E402


def test_committed_openapi_is_up_to_date():
    assert TARGET.exists(), "Frontend/openapi.json manquant : python -m scripts.export_openapi"
    assert TARGET.read_text(encoding="utf-8") == render(build_schema()), (
        "Frontend/openapi.json est périmé : python -m scripts.export_openapi puis npm run api:generate"
    )


def test_every_route_has_typed_responses_for_the_client():
    paths = build_schema()["paths"]
    for route in (
        "/api/v1/auth/login",
        "/api/v1/auth/me",
        "/api/v1/chat/query",
        "/api/v1/chat/conversations",
        "/api/v1/admin/users",
        "/api/v1/documents",
    ):
        assert route in paths
    login = paths["/api/v1/auth/login"]["post"]["responses"]["200"]["content"]["application/json"]
    assert login["schema"]["$ref"].endswith("LoginResponse")
