# Guide de Démarrage de l'API Backend

## 🚀 Démarrage Rapide

### Option 1 : Utiliser le script run_api.py (Recommandé)

```bash
cd Backend
python run_api.py
```

### Option 2 : Utiliser uvicorn directement

```bash
cd Backend
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

### Option 3 : Avec l'environnement virtuel

```bash
cd Backend
.\venv\Scripts\Activate.ps1  # Windows PowerShell
# ou
.\venv\Scripts\activate.bat  # Windows CMD
python run_api.py
```

## ✅ Vérification

Une fois démarré, vous devriez voir :
```
🚀 Démarrage du serveur RAG System API...
🌐 URLs disponibles:
   • API:         http://localhost:8000
   • Health:      http://localhost:8000/health
   • Documentation: http://localhost:8000/docs
⚠️  IMPORTANT: Utilisez 'localhost' ou '127.0.0.1' dans votre navigateur
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Application startup complete.
```

**⚠️ Note importante** : Le serveur écoute sur `0.0.0.0:8000` (toutes les interfaces), mais vous devez accéder via `http://localhost:8000` ou `http://127.0.0.1:8000` dans votre navigateur. N'utilisez **PAS** `http://0.0.0.0:8000` dans l'URL du navigateur !

## 🔍 Tests de Connexion

1. **Health Check** : Ouvrez dans votre navigateur :
   - http://localhost:8000/health
   - Devrait retourner : `{"status":"healthy"}`

2. **Documentation API** : 
   - http://localhost:8000/docs (Swagger UI)
   - http://localhost:8000/redoc (ReDoc)

3. **Endpoint racine** :
   - http://localhost:8000/
   - Devrait retourner les informations de l'API

## ⚠️ Problèmes Courants

### Port 8000 déjà utilisé
```bash
# Windows : Trouver le processus utilisant le port 8000
netstat -ano | findstr :8000

# Tuer le processus (remplacez PID par le numéro trouvé)
taskkill /PID <PID> /F
```

### Module non trouvé
```bash
# Installer les dépendances
pip install -r requirement.txt
```

### Erreur CORS
Vérifiez que `Backend/api/middleware.py` contient bien l'origine de votre frontend (par défaut : http://localhost:5173)

## 📝 Notes

- Le backend doit être démarré **avant** le frontend
- L'API écoute sur `http://0.0.0.0:8000` (accessible via `http://localhost:8000`)
- Le mode `reload=True` permet le rechargement automatique lors des modifications



## Variables d'environnement d'authentification

À définir dans `Backend/.env` avant de lancer l'API :

| Variable | Obligatoire | Description |
|---|---|---|
| `JWT_SECRET_KEY` | Oui (32 caractères min.) | Clé de signature des JWT. Générer avec `python -c "import secrets; print(secrets.token_urlsafe(48))"`. L'API refuse de démarrer sans elle. |
| `ADMIN_EMAIL` / `ADMIN_PASSWORD` | Non | Crée un compte administrateur au démarrage. |
| `DEFAULT_USER_EMAIL` / `DEFAULT_USER_PASSWORD` | Non | Crée un compte utilisateur standard au démarrage. |

Les routes `/api/v1/chat/*` exigent un token valide, et `/api/v1/admin/*` un token de rôle `admin`.
