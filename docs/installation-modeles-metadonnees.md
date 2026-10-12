# Installation des Modèles pour l'Extraction de Métadonnées Locales

Ce guide explique comment installer les modèles nécessaires pour l'extraction de métadonnées avec des modèles locaux (sans appels LLM).

## Dépendances Python

Installez les packages Python nécessaires :

```bash
cd Backend
pip install keybert spacy bertopic transformers sentence-transformers nltk torch
```

## Modèles spaCy

spaCy nécessite des modèles de langue pré-entraînés. Installez au moins un des modèles suivants :

### Option 1 : Modèle standard (recommandé pour débuter)
```bash
python -m spacy download en_core_web_sm
```

### Option 2 : Modèle Transformer (meilleure qualité, plus lourd)
```bash
python -m spacy download en_core_web_trf
```

**Note** : Le code essaiera automatiquement le modèle transformer en premier, puis le modèle standard en fallback.

## Modèles Transformers (T5/Pegasus)

Les modèles de résumé seront téléchargés automatiquement lors du premier usage :
- `t5-small` (par défaut, ~240MB)
- `facebook/bart-large-cnn` (fallback, ~1.6GB)

Ces modèles sont téléchargés depuis Hugging Face automatiquement.

## Vérification de l'installation

Pour vérifier que tout est installé correctement, vous pouvez exécuter :

```python
# Test KeyBERT
from keybert import KeyBERT
model = KeyBERT(model='all-MiniLM-L6-v2')
print("✅ KeyBERT OK")

# Test spaCy
import spacy
nlp = spacy.load("en_core_web_sm")
print("✅ spaCy OK")

# Test BERTopic
from bertopic import BERTopic
print("✅ BERTopic OK")

# Test Transformers
from transformers import pipeline
print("✅ Transformers OK")
```

## Configuration

Dans `config/Config.py`, assurez-vous que :

```python
METADATA_USE_LOCAL_MODELS = True  # Utiliser modèles locaux au lieu de LLM
METADATA_ENRICHMENT_ENABLED = True  # Activer l'enrichissement
```

## Utilisation

Lors de la reconstruction des index (`python scripts/rebuild_index.py`), les modèles locaux seront utilisés automatiquement si `METADATA_USE_LOCAL_MODELS = True`.

## Avantages

- ✅ Pas de coût API
- ✅ Pas de rate limits
- ✅ Fonctionne hors ligne
- ✅ Plus rapide (pas de latence réseau)
- ✅ Données privées (pas d'envoi à des services externes)

## Inconvénients

- ⚠️ Consommation mémoire/GPU
- ⚠️ Installation initiale plus longue
- ⚠️ Qualité parfois légèrement inférieure aux LLM (mais généralement très bonne)

## Dépannage

### Erreur "spacy model not found"
```bash
python -m spacy download en_core_web_sm
```

### Erreur "CUDA out of memory"
Les modèles utiliseront automatiquement le CPU si CUDA n'est pas disponible ou si la mémoire GPU est insuffisante.

### Erreur "nltk data not found"
```python
import nltk
nltk.download('punkt')
```

Le code a un fallback si nltk n'est pas disponible, donc cette étape est optionnelle.

