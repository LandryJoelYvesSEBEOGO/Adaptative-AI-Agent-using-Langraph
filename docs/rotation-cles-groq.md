# Système de Rotation des Clés API Groq

## Vue d'ensemble

Ce système permet de gérer automatiquement plusieurs clés API Groq avec rotation automatique en cas de rate limit (erreur 429). Cela améliore la résilience du système en permettant de continuer à fonctionner même si une clé API atteint sa limite de requêtes.

## Fonctionnalités

- ✅ **Rotation automatique** : Passage automatique à la clé suivante en cas de rate limit
- ✅ **Détection intelligente** : Détection automatique des erreurs 429 (rate limit)
- ✅ **Blocage temporaire** : Les clés bloquées sont temporairement ignorées (7 minutes par défaut)
- ✅ **Fallback transparent** : Aucune modification nécessaire dans le code existant
- ✅ **Support streaming** : Fonctionne avec les appels `invoke()` et `stream()`
- ✅ **Mode JSON** : Support du mode JSON pour les réponses structurées

## Configuration

### Variables d'environnement

Dans votre fichier `.env`, vous pouvez configurer :

```env
# Clé principale (obligatoire)
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Clés supplémentaires (optionnel, séparées par des virgules)
GROQ_API_KEYS=gsk_yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy,gsk_zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz
```

**Note** : Si `GROQ_API_KEY` est défini, il sera automatiquement inclus dans la liste des clés disponibles. Les doublons sont automatiquement supprimés.

### Exemple de configuration

```env
# Option 1: Une seule clé (comportement par défaut)
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Option 2: Plusieurs clés
GROQ_API_KEY=gsk_primary_key_here
GROQ_API_KEYS=gsk_backup_key_1,gsk_backup_key_2,gsk_backup_key_3
```

## Utilisation

### Utilisation automatique

Le système est déjà intégré dans `Rag_model.py` et `Data_processing.py`. Aucune modification n'est nécessaire dans votre code existant. Le gestionnaire de clés est utilisé automatiquement pour tous les appels LLM.

### Utilisation manuelle

Si vous souhaitez utiliser le gestionnaire de clés dans votre propre code :

```python
from src.core.groq_key_manager import get_groq_key_manager
from langchain_core.messages import HumanMessage

# Récupérer le gestionnaire
manager = get_groq_key_manager()

# Appel avec fallback automatique
messages = [HumanMessage(content="Votre question ici")]
response = manager.invoke_with_fallback(messages, json_mode=False)

# Stream avec fallback automatique
for chunk in manager.stream_with_fallback(messages, json_mode=False):
    print(chunk.content, end='')
```

## Fonctionnement

### 1. Initialisation

Lors du premier appel, le gestionnaire :
- Charge toutes les clés depuis `Config.GROQ_API_KEY` et `Config.GROQ_API_KEYS`
- Supprime les doublons
- Initialise le cache des instances LLM
- Sélectionne la première clé comme clé active

### 2. Détection des rate limits

Lorsqu'une erreur se produit :
- Le gestionnaire vérifie si c'est une erreur 429 (rate limit)
- Si oui, la clé actuelle est bloquée pour 7 minutes (420 secondes)
- Le système passe automatiquement à la clé suivante disponible

### 3. Rotation

La rotation se fait de manière circulaire :
- Clé 1 → Clé 2 → Clé 3 → Clé 1 → ...
- Les clés bloquées sont ignorées jusqu'à leur déblocage automatique

### 4. Gestion des erreurs

- **Erreur 429 (rate limit)** : Rotation automatique vers la clé suivante
- **Autres erreurs** : Propagation normale de l'erreur (pas de rotation)
- **Toutes les clés bloquées** : Exception levée avec message explicite

## Tests

Un script de test est disponible pour vérifier le fonctionnement :

```bash
cd Backend
python tests/test_groq_key_rotation.py
```

Le script teste :
1. ✅ L'initialisation du gestionnaire
2. ✅ La rotation manuelle des clés
3. ✅ La détection des erreurs de rate limit
4. ✅ Les appels LLM réels avec fallback (optionnel)

## Architecture

```
┌─────────────────────────────────────┐
│   GroqKeyManager                    │
│                                     │
│  - api_keys: List[str]             │
│  - current_key_index: int          │
│  - key_status: Dict[str, Dict]    │
│  - _llm_cache: Dict[str, ChatGroq] │
│                                     │
│  + get_current_key()               │
│  + get_current_llm()               │
│  + invoke_with_fallback()           │
│  + stream_with_fallback()           │
│  + handle_rate_limit_error()        │
│  + rotate_to_next_key()             │
└─────────────────────────────────────┘
         │
         ├───> ChatGroq (clé 1)
         ├───> ChatGroq (clé 2)
         └───> ChatGroq (clé 3)
```

## Détails techniques

### Blocage des clés

- **Durée par défaut** : 7 minutes (420 secondes)
- **Extraction automatique** : Si le message d'erreur contient "try again in Xm", la durée est extraite automatiquement
- **Compteur d'erreurs** : Chaque clé garde un compteur du nombre de fois qu'elle a été bloquée

### Cache des instances LLM

Les instances `ChatGroq` sont mises en cache par clé et mode (JSON/normal) pour éviter de recréer des objets inutilement.

### Thread-safety

Le gestionnaire utilise une instance globale (singleton pattern) pour garantir la cohérence entre les différents appels.

## Limitations

1. **Pas de persistance** : Les statuts de blocage ne sont pas persistés entre les redémarrages
2. **Durée fixe** : La durée de blocage est fixe (7 minutes) sauf si extraite du message d'erreur
3. **Pas de monitoring** : Aucun monitoring des taux d'utilisation par clé (pour l'instant)

## Améliorations futures possibles

- [ ] Persistance des statuts de blocage (fichier/DB)
- [ ] Monitoring des taux d'utilisation par clé
- [ ] Rotation proactive basée sur les quotas
- [ ] Configuration de la durée de blocage par variable d'environnement
- [ ] Logs détaillés des rotations et blocages

## Dépannage

### "Aucune clé API Groq configurée"

Vérifiez que `GROQ_API_KEY` est défini dans votre fichier `.env`.

### "Toutes les clés API Groq sont épuisées"

Toutes les clés sont temporairement bloquées. Attendez quelques minutes ou ajoutez plus de clés.

### Les rotations ne fonctionnent pas

Vérifiez que vous avez configuré plusieurs clés dans `GROQ_API_KEYS` et qu'elles sont valides.

## Support

Pour toute question ou problème, consultez les logs du système qui affichent les rotations et blocages avec des emojis pour faciliter le débogage :
- 🔄 Rotation vers une nouvelle clé
- ⚠️ Clé bloquée (rate limit)
- ❌ Toutes les clés bloquées

