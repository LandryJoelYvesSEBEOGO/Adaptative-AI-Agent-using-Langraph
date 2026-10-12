"""L2.5 : une requête RAG lente ne doit pas bloquer l'API."""

import asyncio
import time

import httpx
import pytest

from tests.api_stub import install

fake = install()

DELAY = 0.6

from api.main import app, lifespan  # noqa: E402


@pytest.fixture(autouse=True)
def slow_rag():
    fake.rag_delay = DELAY  # simule un appel LLM bloquant
    yield
    fake.rag_delay = 0.0


@pytest.mark.anyio
async def test_two_slow_requests_run_in_parallel_and_health_stays_responsive():
    transport = httpx.ASGITransport(app=app)
    async with lifespan(app), httpx.AsyncClient(transport=transport, base_url="http://t") as c:
        reg = await c.post(
            "/api/v1/auth/register",
            json={"email": "par@example.com", "password": "Passw0rd!", "name": "P"},
        )
        headers = {"Authorization": f"Bearer {reg.json()['token']}"}

        async def ask(i):
            return await c.post("/api/v1/chat/query", json={"question": f"q{i}"}, headers=headers)

        started = time.perf_counter()
        slow = asyncio.gather(ask(1), ask(2))
        await asyncio.sleep(0.1)
        t0 = time.perf_counter()
        health = await c.get("/health")
        health_latency = time.perf_counter() - t0
        r1, r2 = await slow
        elapsed = time.perf_counter() - started

    assert r1.status_code == r2.status_code == 200
    assert health.status_code == 200
    assert health_latency < DELAY / 2, "la boucle d'événements est bloquée"
    assert elapsed < DELAY * 1.7, f"requêtes sérialisées ({elapsed:.2f}s)"


@pytest.fixture
def anyio_backend():
    return "asyncio"
