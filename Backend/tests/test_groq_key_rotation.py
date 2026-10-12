"""
Script de test pour le système de rotation des clés API Groq.

Ce script teste :
1. L'initialisation du gestionnaire avec plusieurs clés
2. La rotation automatique en cas de rate limit
3. Le fallback entre les clés
"""
import os
import sys
from pathlib import Path

# S'assurer qu'on est à la racine du projet backend
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.groq_key_manager import get_groq_key_manager, GroqKeyManager
from langchain_core.messages import HumanMessage
from config.Config import Config

def test_key_manager_initialization():
    """Test l'initialisation du gestionnaire de clés."""
    print("=" * 60)
    print("TEST 1: Initialisation du gestionnaire de clés")
    print("=" * 60)
    
    try:
        manager = get_groq_key_manager()
        print(f"✅ Gestionnaire initialisé avec {len(manager.api_keys)} clé(s) API")
        print(f"   Clé actuelle: {manager.get_current_key()[:20]}...")
        return manager
    except Exception as e:
        print(f"❌ Erreur lors de l'initialisation: {e}")
        return None

def test_key_rotation():
    """Test la rotation manuelle des clés."""
    print("\n" + "=" * 60)
    print("TEST 2: Rotation manuelle des clés")
    print("=" * 60)
    
    try:
        manager = get_groq_key_manager()
        original_key = manager.get_current_key()
        print(f"Clé initiale: {original_key[:20]}...")
        
        # Tester la rotation
        if len(manager.api_keys) > 1:
            manager.rotate_to_next_key()
            new_key = manager.get_current_key()
            print(f"Clé après rotation: {new_key[:20]}...")
            
            if new_key != original_key:
                print("✅ Rotation réussie")
            else:
                print("⚠️ Rotation n'a pas changé la clé (peut être normal si toutes les clés sont identiques)")
        else:
            print("⚠️ Une seule clé configurée, rotation non testable")
    except Exception as e:
        print(f"❌ Erreur lors de la rotation: {e}")

def test_rate_limit_detection():
    """Test la détection des erreurs de rate limit."""
    print("\n" + "=" * 60)
    print("TEST 3: Détection des erreurs de rate limit")
    print("=" * 60)
    
    try:
        manager = get_groq_key_manager()
        current_key = manager.get_current_key()
        
        # Simuler une erreur de rate limit
        class MockRateLimitError(Exception):
            def __str__(self):
                return "Rate limit exceeded. Try again in 5m"
        
        error = MockRateLimitError()
        handled = manager.handle_rate_limit_error(error)
        
        if handled:
            print("✅ Erreur de rate limit détectée et gérée")
            print(f"   Clé bloquée: {current_key[:20]}...")
            print(f"   Bloquée jusqu'à: {manager.key_status.get(current_key, {}).get('blocked_until', 0)}")
        else:
            print("⚠️ Erreur non reconnue comme rate limit")
    except Exception as e:
        print(f"❌ Erreur lors du test: {e}")

def test_llm_invoke():
    """Test un appel LLM réel avec fallback."""
    print("\n" + "=" * 60)
    print("TEST 4: Appel LLM avec fallback automatique")
    print("=" * 60)
    
    try:
        manager = get_groq_key_manager()
        
        # Test avec un message simple
        messages = [HumanMessage(content="Say 'Hello' in one word.")]
        
        print("Envoi d'une requête simple au LLM...")
        response = manager.invoke_with_fallback(messages, json_mode=False)
        
        if hasattr(response, 'content'):
            print(f"✅ Réponse reçue: {response.content[:100]}...")
        else:
            print(f"✅ Réponse reçue: {str(response)[:100]}...")
            
    except Exception as e:
        print(f"❌ Erreur lors de l'appel LLM: {e}")
        print(f"   Type d'erreur: {type(e).__name__}")

def test_llm_stream():
    """Test un stream LLM avec fallback."""
    print("\n" + "=" * 60)
    print("TEST 5: Stream LLM avec fallback automatique")
    print("=" * 60)
    
    try:
        manager = get_groq_key_manager()
        
        # Test avec un message simple
        messages = [HumanMessage(content="Count from 1 to 5, one number per line.")]
        
        print("Stream d'une requête simple au LLM...")
        chunks = []
        for chunk in manager.stream_with_fallback(messages, json_mode=False):
            if hasattr(chunk, 'content') and chunk.content:
                chunks.append(chunk.content)
                print(chunk.content, end='', flush=True)
        
        print("\n✅ Stream terminé")
        print(f"   Nombre de chunks reçus: {len(chunks)}")
            
    except Exception as e:
        print(f"❌ Erreur lors du stream LLM: {e}")
        print(f"   Type d'erreur: {type(e).__name__}")

def display_configuration():
    """Affiche la configuration actuelle."""
    print("\n" + "=" * 60)
    print("CONFIGURATION ACTUELLE")
    print("=" * 60)
    
    main_key = getattr(Config, 'GROQ_API_KEY', None)
    additional_keys = getattr(Config, 'GROQ_API_KEYS', [])
    
    print(f"Clé principale (GROQ_API_KEY): {'✅ Configurée' if main_key else '❌ Non configurée'}")
    if main_key:
        print(f"   {main_key[:30]}...")
    
    print(f"Clés supplémentaires (GROQ_API_KEYS): {len(additional_keys)} clé(s)")
    for i, key in enumerate(additional_keys, 1):
        print(f"   Clé {i}: {key[:30]}...")
    
    print(f"\nModèle Groq: {getattr(Config, 'GROQ_model', 'N/A')}")

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("TESTS DU SYSTÈME DE ROTATION DES CLÉS API GROQ")
    print("=" * 60)
    
    # Afficher la configuration
    display_configuration()
    
    # Exécuter les tests
    manager = test_key_manager_initialization()
    
    if manager:
        test_key_rotation()
        test_rate_limit_detection()
        
        # Tests avec appels réels (peuvent échouer si pas de clés valides)
        print("\n⚠️ Les tests suivants nécessitent des clés API valides.")
        user_input = input("Voulez-vous tester les appels LLM réels ? (o/n): ")
        
        if user_input.lower() in ['o', 'oui', 'y', 'yes']:
            test_llm_invoke()
            test_llm_stream()
        else:
            print("Tests LLM réels ignorés.")
    
    print("\n" + "=" * 60)
    print("TESTS TERMINÉS")
    print("=" * 60)

