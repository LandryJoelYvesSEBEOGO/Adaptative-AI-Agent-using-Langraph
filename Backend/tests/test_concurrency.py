"""L2.5 : une recherche lente et bloquante ne doit pas figer l'API."""

import asyncio
import time

import httpx
import pytest

from tests.api_stub import install

state = install()

from api.main import app, lifespan  # noqa: E402

DELAY = 0.6


@pytest.fixture(autouse=True)
def slow_search():
    state.search_delay = DELAY  # simule un accès base / réseau bloquant
    yield
    state.search_delay = 0.0


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

    assert r1.status_code == r2.status_code == 200, (r1.text, r2.text)
    assert health.status_code == 200
    assert health_latency < DELAY / 2, "la boucle d'événements est bloquée"
    assert elapsed < DELAY * 1.7, f"requêtes sérialisées ({elapsed:.2f}s)"
