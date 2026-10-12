"""L5.2 : limitation de débit, frein au bourrage d'identifiants et quota quotidien."""

import pytest
from fastapi.testclient import TestClient

from tests.api_stub import install

install()

from api.main import app  # noqa: E402
from api.ratelimit import SlidingWindowLimiter, limiter  # noqa: E402
from config.settings import get_settings  # noqa: E402


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def test_sliding_window_blocks_then_releases():
    clock = FakeClock()
    lim = SlidingWindowLimiter(clock)
    assert [lim.hit("k", 3, 60) for _ in range(3)] == [None, None, None]
    assert lim.hit("k", 3, 60) == 60  # 4e requête : attendre la fin de la fenêtre
    clock.now += 30
    assert lim.hit("k", 3, 60) == 30
    clock.now += 31  # la première requête est sortie de la fenêtre
    assert lim.hit("k", 3, 60) is None
    assert lim.hit("autre", 3, 60) is None  # clés indépendantes


def test_limiter_does_not_grow_without_bound(monkeypatch):
    monkeypatch.setattr("api.ratelimit.MAX_TRACKED_KEYS", 10)
    clock = FakeClock()
    lim = SlidingWindowLimiter(clock)
    for i in range(10):
        lim.hit(f"k{i}", 1, 60)
    clock.now += 120
    lim.hit("nouveau", 1, 60)  # déclenche le nettoyage des clés expirées
    assert len(lim._hits) == 1


@pytest.fixture
def client():
    settings = get_settings()
    saved = {
        name: getattr(settings, name)
        for name in (
            "RATE_LIMIT_ENABLED",
            "RATE_LIMIT_AUTH_PER_MINUTE",
            "RATE_LIMIT_LOGIN_ACCOUNT_PER_MINUTE",
            "RATE_LIMIT_CHAT_PER_MINUTE",
            "DAILY_QUESTION_QUOTA",
            "TRUST_PROXY_HEADERS",
        )
    }
    settings.RATE_LIMIT_ENABLED = True
    limiter.reset()
    with TestClient(app) as c:
        yield c
    for name, value in saved.items():
        setattr(settings, name, value)
    limiter.reset()


def register(client, email):
    r = client.post(
        "/api/v1/auth/register", json={"email": email, "password": "Passw0rd!", "name": "N"}
    )
    return {"Authorization": f"Bearer {r.json()['token']}"}


def test_login_brute_force_on_one_account_is_slowed_down(client):
    get_settings().RATE_LIMIT_LOGIN_ACCOUNT_PER_MINUTE = 3
    get_settings().RATE_LIMIT_AUTH_PER_MINUTE = 100
    body = {"email": "victim@example.com", "password": "wrong"}
    codes = [client.post("/api/v1/auth/login", json=body).status_code for _ in range(5)]
    assert codes == [200, 200, 200, 429, 429]
    blocked = client.post("/api/v1/auth/login", json=body)
    assert int(blocked.headers["retry-after"]) >= 1
    # un autre compte n'est pas affecté
    other = client.post("/api/v1/auth/login", json={"email": "other@example.com", "password": "x"})
    assert other.status_code == 200


def test_per_ip_limit_on_auth_routes(client):
    get_settings().RATE_LIMIT_AUTH_PER_MINUTE = 3
    get_settings().RATE_LIMIT_LOGIN_ACCOUNT_PER_MINUTE = 100
    codes = [
        client.post(
            "/api/v1/auth/login", json={"email": f"u{i}@example.com", "password": "x"}
        ).status_code
        for i in range(5)
    ]
    assert codes == [200, 200, 200, 429, 429]


def test_forwarded_header_is_ignored_unless_proxy_is_trusted(client):
    get_settings().RATE_LIMIT_AUTH_PER_MINUTE = 2
    get_settings().RATE_LIMIT_LOGIN_ACCOUNT_PER_MINUTE = 100

    def attempt(forwarded):
        return client.post(
            "/api/v1/auth/login",
            json={"email": "a@example.com", "password": "x"},
            headers={"X-Forwarded-For": forwarded},
        ).status_code

    # confiance désactivée : changer d'en-tête ne contourne pas la limite
    assert [attempt(f"1.1.1.{i}") for i in range(3)] == [200, 200, 429]

    limiter.reset()
    get_settings().TRUST_PROXY_HEADERS = True
    # derrière un proxy de confiance : chaque client réel (dernière entrée ajoutée par le proxy) a sa limite
    assert [attempt("evil, 10.0.0.1"), attempt("evil, 10.0.0.1"), attempt("evil, 10.0.0.1")] == [
        200,
        200,
        429,
    ]
    assert attempt("evil, 10.0.0.2") == 200


def test_chat_rate_limit_is_per_user(client):
    get_settings().RATE_LIMIT_CHAT_PER_MINUTE = 2
    get_settings().DAILY_QUESTION_QUOTA = 0
    alice, bob = register(client, "rl-alice@example.com"), register(client, "rl-bob@example.com")
    client.cookies.clear()

    def ask(headers):
        return client.post("/api/v1/chat/query", json={"question": "3M capex?"}, headers=headers)

    assert [ask(alice).status_code for _ in range(3)] == [200, 200, 429]
    assert ask(bob).status_code == 200  # un autre utilisateur n'est pas pénalisé
    stream = client.post("/api/v1/chat/query/stream", json={"question": "x"}, headers=alice)
    assert stream.status_code == 429 and "Retry-After" in stream.headers


def test_daily_quota_applies_to_users_but_not_admins(client):
    settings = get_settings()
    settings.DAILY_QUESTION_QUOTA = 2
    settings.RATE_LIMIT_CHAT_PER_MINUTE = 100
    user = register(client, "quota-user@example.com")
    client.cookies.clear()
    admin_token = client.post(
        "/api/v1/auth/login", json={"email": "boss@example.com", "password": "Sup3rS3cret!"}
    ).json()["token"]
    admin = {"Authorization": f"Bearer {admin_token}"}

    def ask(headers):
        return client.post("/api/v1/chat/query", json={"question": "3M capex?"}, headers=headers)

    assert [ask(user).status_code for _ in range(2)] == [200, 200]
    over = ask(user)
    assert over.status_code == 429
    assert "Quota quotidien atteint (2 questions)" in over.json()["detail"]
    assert int(over.headers["retry-after"]) > 0
    assert all(ask(admin).status_code == 200 for _ in range(4))  # administrateurs exemptés


def test_limits_can_be_disabled(client):
    get_settings().RATE_LIMIT_ENABLED = False
    get_settings().RATE_LIMIT_AUTH_PER_MINUTE = 1
    codes = {
        client.post(
            "/api/v1/auth/login", json={"email": "z@example.com", "password": "x"}
        ).status_code
        for _ in range(4)
    }
    assert codes == {200}
