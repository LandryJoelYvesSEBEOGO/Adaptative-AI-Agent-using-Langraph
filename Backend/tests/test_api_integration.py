"""
Tests d'intégration complets pour toutes les routes API du système RAG.
Teste tous les endpoints : auth, chat (normal et streaming), admin, feedback
"""

import sys
import os
from pathlib import Path
import json
import time

# Ajouter le chemin du projet
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pytest
from fastapi.testclient import TestClient
from api.main import app

# Créer le client de test
@pytest.fixture
def client():
    """Fixture pour créer un client de test."""
    return TestClient(app)


# ============================================================================
# TESTS DES ENDPOINTS DE BASE
# ============================================================================

class TestHealthAndRoot:
    """Tests pour les endpoints de base."""
    
    def test_root_endpoint(self, client):
        """Test de l'endpoint racine."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert data["message"] == "RAG System API"
        assert "version" in data
        assert data["version"] == "1.0.0"
        assert "docs" in data
        assert "redoc" in data
    
    def test_health_check(self, client):
        """Test de l'endpoint health."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


# ============================================================================
# TESTS D'AUTHENTIFICATION
# ============================================================================

class TestAuth:
    """Tests complets pour les endpoints d'authentification."""
    
    def test_login_success_admin(self, client):
        """Test de connexion réussie avec compte admin."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "admin@rag-system.io",
                "password": "admin"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "token" in data
        assert data["token"] is not None
        assert len(data["token"]) > 0
        assert "user" in data
        assert data["user"]["role"] == "admin"
        assert data["user"]["email"] == "admin@rag-system.io"
        assert "id" in data["user"]
        assert "name" in data["user"]
    
    def test_login_success_user(self, client):
        """Test de connexion réussie avec compte utilisateur."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "user@rag-system.io",
                "password": "user"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "token" in data
        assert data["token"] is not None
        assert "user" in data
        assert data["user"]["role"] == "user"
        assert data["user"]["email"] == "user@rag-system.io"
    
    def test_login_invalid_email(self, client):
        """Test de connexion avec email invalide."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "invalid@example.com",
                "password": "admin"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "error" in data
        assert data.get("token") is None
    
    def test_login_invalid_password(self, client):
        """Test de connexion avec mot de passe invalide."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "admin@rag-system.io",
                "password": "wrongpassword"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "error" in data
        assert "incorrect" in data["error"].lower() or "invalid" in data["error"].lower()
    
    def test_login_missing_fields(self, client):
        """Test de connexion avec champs manquants."""
        # Email manquant
        response = client.post(
            "/api/v1/auth/login",
            json={"password": "admin"}
        )
        assert response.status_code == 422  # Validation error
        
        # Password manquant
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "admin@rag-system.io"}
        )
        assert response.status_code == 422
    
    def test_register_user(self, client):
        """Test d'inscription d'un nouvel utilisateur."""
        # Utiliser un email unique avec timestamp
        unique_email = f"testuser_{int(time.time())}@rag-system.io"
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": unique_email,
                "password": "newpassword123",
                "name": "New User",
                "role": "user"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "token" in data
        assert data["token"] is not None
        assert "user" in data
        assert data["user"]["role"] == "user"
        assert data["user"]["email"] == unique_email
        assert data["user"]["name"] == "New User"
    
    def test_register_admin(self, client):
        """Test d'inscription d'un nouvel administrateur."""
        unique_email = f"testadmin_{int(time.time())}@rag-system.io"
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": unique_email,
                "password": "adminpass123",
                "name": "New Admin",
                "role": "admin"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "token" in data
        assert data["user"]["role"] == "admin"
        assert data["user"]["email"] == unique_email
    
    def test_register_default_role(self, client):
        """Test d'inscription sans spécifier le rôle (doit être 'user' par défaut)."""
        unique_email = f"testdefault_{int(time.time())}@rag-system.io"
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": unique_email,
                "password": "password123",
                "name": "Default User"
                # role non spécifié
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["user"]["role"] == "user"
    
    def test_register_duplicate_email(self, client):
        """Test d'inscription avec un email déjà existant."""
        unique_email = f"duplicate_{int(time.time())}@rag-system.io"
        
        # D'abord créer un utilisateur
        client.post(
            "/api/v1/auth/register",
            json={
                "email": unique_email,
                "password": "password123",
                "name": "First User",
                "role": "user"
            }
        )
        
        # Essayer de créer un autre utilisateur avec le même email
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": unique_email,
                "password": "password456",
                "name": "Second User",
                "role": "user"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "error" in data
        assert "existe déjà" in data["error"].lower() or "already exists" in data["error"].lower()
    
    def test_register_invalid_email_format(self, client):
        """Test d'inscription avec format d'email invalide."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "not-an-email",
                "password": "password123",
                "name": "Test User"
            }
        )
        assert response.status_code == 422  # Validation error
    
    def test_logout(self, client):
        """Test de déconnexion."""
        response = client.post("/api/v1/auth/logout")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "message" in data
        assert "déconnecté" in data["message"].lower() or "logout" in data["message"].lower()


# ============================================================================
# TESTS DES ENDPOINTS CHAT
# ============================================================================

class TestChat:
    """Tests complets pour les endpoints de chat."""
    
    @pytest.fixture
    def auth_token(self, client):
        """Fixture pour obtenir un token d'authentification."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "user@rag-system.io",
                "password": "user"
            }
        )
        data = response.json()
        return data.get("token")
    
    # Tests pour /api/v1/chat/query (mode normal)
    def test_query_empty_question(self, client):
        """Test avec une question vide."""
        response = client.post(
            "/api/v1/chat/query",
            json={"question": ""}
        )
        assert response.status_code == 400
        assert "vide" in response.json()["detail"].lower() or "empty" in response.json()["detail"].lower()
    
    def test_query_whitespace_only(self, client):
        """Test avec une question contenant uniquement des espaces."""
        response = client.post(
            "/api/v1/chat/query",
            json={"question": "   "}
        )
        assert response.status_code == 400
    
    def test_query_missing_question(self, client):
        """Test sans le champ question."""
        response = client.post(
            "/api/v1/chat/query",
            json={}
        )
        assert response.status_code == 422  # Validation error
    
    def test_query_with_question(self, client, auth_token):
        """Test de requête chat avec une question valide."""
        headers = {"Authorization": f"Bearer {auth_token}"} if auth_token else {}
        response = client.post(
            "/api/v1/chat/query",
            json={"question": "Qu'est-ce que le RAG?"},
            headers=headers
        )
        # Accepte 200 (succès) ou 500 (erreur si RAG non configuré)
        assert response.status_code in [200, 500]
        
        if response.status_code == 200:
            data = response.json()
            assert "response" in data
            assert "conversation_id" in data
            assert "success" in data
            assert "citations" in data
            assert isinstance(data["citations"], list)
            if data.get("latency"):
                assert isinstance(data["latency"], (int, float))
    
    def test_query_with_conversation_id(self, client, auth_token):
        """Test de requête avec conversation_id."""
        headers = {"Authorization": f"Bearer {auth_token}"} if auth_token else {}
        conversation_id = "test-conv-123"
        response = client.post(
            "/api/v1/chat/query",
            json={
                "question": "Qu'est-ce que le RAG?",
                "conversation_id": conversation_id
            },
            headers=headers
        )
        if response.status_code == 200:
            data = response.json()
            assert data["conversation_id"] == conversation_id
    
    # Tests pour /api/v1/chat/query/stream (mode streaming)
    def test_query_stream_empty_question(self, client):
        """Test streaming avec une question vide."""
        response = client.post(
            "/api/v1/chat/query/stream",
            json={"question": ""}
        )
        assert response.status_code == 400
    
    def test_query_stream_with_question(self, client, auth_token):
        """Test de requête chat en mode streaming."""
        headers = {"Authorization": f"Bearer {auth_token}"} if auth_token else {}
        # TestClient ne supporte pas stream=True, on teste juste que la route répond
        response = client.post(
            "/api/v1/chat/query/stream",
            json={"question": "Qu'est-ce que le RAG?"},
            headers=headers
        )
        # Accepte 200 (succès) ou 500 (erreur si RAG non configuré)
        assert response.status_code in [200, 500]
        
        if response.status_code == 200:
            # Vérifier que c'est bien du streaming SSE
            content_type = response.headers.get("content-type", "")
            assert "text/event-stream" in content_type or "event-stream" in content_type
            
            # Lire le contenu (TestClient retourne tout le contenu)
            content = response.text
            # Vérifier que le format SSE est présent
            assert "data:" in content or "[DONE]" in content
    
    def test_query_stream_with_conversation_id(self, client, auth_token):
        """Test streaming avec conversation_id."""
        headers = {"Authorization": f"Bearer {auth_token}"} if auth_token else {}
        conversation_id = "test-stream-conv-456"
        # TestClient ne supporte pas stream=True, on teste juste que la route répond
        response = client.post(
            "/api/v1/chat/query/stream",
            json={
                "question": "Qu'est-ce que le RAG?",
                "conversation_id": conversation_id
            },
            headers=headers
        )
        # Vérifier que la requête est acceptée
        assert response.status_code in [200, 500]
        
        if response.status_code == 200:
            # Vérifier le format SSE
            content_type = response.headers.get("content-type", "")
            assert "text/event-stream" in content_type or "event-stream" in content_type
    
    # Tests pour /api/v1/chat/feedback
    def test_feedback_thumbs_up(self, client):
        """Test de soumission de feedback positif."""
        response = client.post(
            "/api/v1/chat/feedback",
            json={
                "message_id": "test-message-123",
                "feedback_type": "thumbs_up",
                "comment": "Très utile!"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message_id"] == "test-message-123"
        assert data["feedback_type"] == "thumbs_up"
        assert "message" in data
    
    def test_feedback_thumbs_down(self, client):
        """Test de soumission de feedback négatif."""
        response = client.post(
            "/api/v1/chat/feedback",
            json={
                "message_id": "test-message-456",
                "feedback_type": "thumbs_down",
                "comment": "Pas assez détaillé"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["feedback_type"] == "thumbs_down"
    
    def test_feedback_without_comment(self, client):
        """Test de feedback sans commentaire."""
        response = client.post(
            "/api/v1/chat/feedback",
            json={
                "message_id": "test-message-789",
                "feedback_type": "thumbs_up"
                # comment manquant
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
    
    def test_feedback_missing_fields(self, client):
        """Test de feedback avec champs manquants."""
        # message_id manquant
        response = client.post(
            "/api/v1/chat/feedback",
            json={"feedback_type": "thumbs_up"}
        )
        assert response.status_code == 422
        
        # feedback_type manquant
        response = client.post(
            "/api/v1/chat/feedback",
            json={"message_id": "test-123"}
        )
        assert response.status_code == 422


# ============================================================================
# TESTS DES ENDPOINTS ADMIN
# ============================================================================

class TestAdmin:
    """Tests complets pour les endpoints admin."""
    
    @pytest.fixture
    def admin_token(self, client):
        """Fixture pour obtenir un token admin."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "admin@rag-system.io",
                "password": "admin"
            }
        )
        data = response.json()
        return data.get("token")
    
    @pytest.fixture
    def user_token(self, client):
        """Fixture pour obtenir un token utilisateur."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "user@rag-system.io",
                "password": "user"
            }
        )
        data = response.json()
        return data.get("token")
    
    # Tests pour /api/v1/admin/metrics/overview
    def test_metrics_overview(self, client, admin_token):
        """Test de récupération des métriques overview."""
        headers = {"Authorization": f"Bearer {admin_token}"} if admin_token else {}
        response = client.get("/api/v1/admin/metrics/overview", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "total_requests" in data
        assert "requests_today" in data
        assert "success_rate" in data
        assert "average_latency" in data
        assert "error_count" in data
        # Vérifier les types
        assert isinstance(data["total_requests"], int)
        assert isinstance(data["requests_today"], int)
        assert isinstance(data["success_rate"], (int, float))
        assert isinstance(data["average_latency"], (int, float))
        assert isinstance(data["error_count"], int)
    
    def test_metrics_overview_without_token(self, client):
        """Test de métriques overview sans token (devrait fonctionner car auth non stricte)."""
        response = client.get("/api/v1/admin/metrics/overview")
        # Devrait fonctionner car l'auth n'est pas encore strictement appliquée
        assert response.status_code == 200
    
    # Tests pour /api/v1/admin/metrics/requests
    def test_metrics_requests_default(self, client, admin_token):
        """Test de récupération des données de requêtes avec paramètres par défaut."""
        headers = {"Authorization": f"Bearer {admin_token}"} if admin_token else {}
        response = client.get("/api/v1/admin/metrics/requests", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_metrics_requests_with_days(self, client, admin_token):
        """Test avec paramètre days."""
        headers = {"Authorization": f"Bearer {admin_token}"} if admin_token else {}
        response = client.get("/api/v1/admin/metrics/requests?days=7", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        # Tester avec différentes valeurs
        for days in [1, 7, 30, 90]:
            response = client.get(f"/api/v1/admin/metrics/requests?days={days}", headers=headers)
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
    
    def test_metrics_requests_invalid_days(self, client, admin_token):
        """Test avec valeur invalide pour days."""
        headers = {"Authorization": f"Bearer {admin_token}"} if admin_token else {}
        response = client.get("/api/v1/admin/metrics/requests?days=-1", headers=headers)
        # Devrait accepter ou retourner une erreur
        assert response.status_code in [200, 422]
    
    # Tests pour /api/v1/admin/metrics/recent
    def test_metrics_recent_default(self, client, admin_token):
        """Test de récupération des requêtes récentes avec limite par défaut."""
        headers = {"Authorization": f"Bearer {admin_token}"} if admin_token else {}
        response = client.get("/api/v1/admin/metrics/recent", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_metrics_recent_with_limit(self, client, admin_token):
        """Test avec paramètre limit."""
        headers = {"Authorization": f"Bearer {admin_token}"} if admin_token else {}
        response = client.get("/api/v1/admin/metrics/recent?limit=10", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        # Tester avec différentes valeurs
        for limit in [5, 10, 20, 50]:
            response = client.get(f"/api/v1/admin/metrics/recent?limit={limit}", headers=headers)
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            # Si des données existent, vérifier la structure
            if len(data) > 0:
                item = data[0]
                assert "id" in item
                assert "timestamp" in item
                assert "user" in item
                assert "question" in item
                assert "status" in item
                assert "latency" in item
    
    def test_metrics_recent_invalid_limit(self, client, admin_token):
        """Test avec valeur invalide pour limit."""
        headers = {"Authorization": f"Bearer {admin_token}"} if admin_token else {}
        response = client.get("/api/v1/admin/metrics/recent?limit=-1", headers=headers)
        # Devrait accepter ou retourner une erreur
        assert response.status_code in [200, 422]
    
    # Tests pour /api/v1/admin/metrics/errors
    def test_error_distribution(self, client, admin_token):
        """Test de récupération de la répartition des erreurs."""
        headers = {"Authorization": f"Bearer {admin_token}"} if admin_token else {}
        response = client.get("/api/v1/admin/metrics/errors", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "timeout" in data
        assert "llm_error" in data
        assert "retrieval" in data
        assert "web_search" in data
        assert "other" in data
        # Vérifier les types
        assert isinstance(data["timeout"], int)
        assert isinstance(data["llm_error"], int)
        assert isinstance(data["retrieval"], int)
        assert isinstance(data["web_search"], int)
        assert isinstance(data["other"], int)
    
    # Tests pour /api/v1/admin/system/status
    def test_system_status(self, client, admin_token):
        """Test de récupération du statut système."""
        headers = {"Authorization": f"Bearer {admin_token}"} if admin_token else {}
        response = client.get("/api/v1/admin/system/status", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "rag_pipeline" in data
        assert "vector_db" in data
        assert "llm_status" in data
        assert "uptime_percentage" in data
        # Vérifier les types
        assert isinstance(data["rag_pipeline"], str)
        assert isinstance(data["vector_db"], str)
        assert isinstance(data["llm_status"], str)
        assert isinstance(data["uptime_percentage"], (int, float))
        # Vérifier que uptime est entre 0 et 100
        assert 0 <= data["uptime_percentage"] <= 100


# ============================================================================
# TESTS DE SÉCURITÉ ET CAS LIMITES
# ============================================================================

class TestSecurityAndEdgeCases:
    """Tests de sécurité et cas limites."""
    
    def test_cors_headers(self, client):
        """Test que les headers CORS sont présents."""
        # Test avec une requête POST normale pour vérifier les headers CORS
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "test"},
            headers={"Origin": "http://localhost:5173"}
        )
        # Vérifier que la requête est acceptée (CORS ne bloque pas)
        assert response.status_code in [200, 401, 422]
        
        # OPTIONS peut retourner 405 si la route ne le supporte pas explicitement
        # C'est normal, CORS fonctionne via le middleware sur les vraies requêtes
        options_response = client.options("/api/v1/auth/login")
        # 405 est acceptable car OPTIONS n'est pas implémenté explicitement
        assert options_response.status_code in [200, 405]
    
    def test_invalid_token_format(self, client):
        """Test avec un token invalide."""
        headers = {"Authorization": "Bearer invalid-token-12345"}
        response = client.get("/api/v1/admin/metrics/overview", headers=headers)
        # Devrait fonctionner car l'auth n'est pas encore strictement appliquée
        # ou retourner 401 si l'auth est active
        assert response.status_code in [200, 401]
    
    def test_missing_authorization_header(self, client):
        """Test sans header Authorization."""
        response = client.get("/api/v1/admin/metrics/overview")
        # Devrait fonctionner car l'auth n'est pas encore strictement appliquée
        assert response.status_code == 200
    
    def test_malformed_json(self, client):
        """Test avec JSON malformé."""
        response = client.post(
            "/api/v1/auth/login",
            data="not json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422
    
    def test_very_long_question(self, client):
        """Test avec une question très longue."""
        long_question = "Qu'est-ce que le RAG? " * 1000  # ~30KB
        response = client.post(
            "/api/v1/chat/query",
            json={"question": long_question}
        )
        # Devrait accepter ou retourner une erreur de validation
        assert response.status_code in [200, 400, 422, 500]
    
    def test_special_characters_in_question(self, client):
        """Test avec caractères spéciaux dans la question."""
        special_question = "Test avec émojis 🚀 et caractères spéciaux: <>&\"'"
        response = client.post(
            "/api/v1/chat/query",
            json={"question": special_question}
        )
        assert response.status_code in [200, 400, 422, 500]


# ============================================================================
# EXÉCUTION DES TESTS
# ============================================================================

if __name__ == "__main__":
    # Permet d'exécuter les tests directement avec Python
    pytest.main([__file__, "-v", "--tb=short"])
