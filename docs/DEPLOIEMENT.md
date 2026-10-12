# Déploiement

Deux voies, toutes deux sans modification du code : le front et l'API partagent **la même origine** (`/api`), ce qui évite CORS et permet les cookies de session httpOnly.

## A. Un serveur (VPS) avec Docker Compose : le plus simple

```bash
cp Backend/.env.example Backend/.env      # clés d'API, JWT_SECRET_KEY, ADMIN_EMAIL / ADMIN_PASSWORD
printf 'SITE_ADDRESS=rag.exemple.fr\nPOSTGRES_PASSWORD=%s\n' "$(openssl rand -hex 24)" > .env.prod
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build
```

`docker-compose.prod.yml` lance PostgreSQL + pgvector, l'API (utilisateur non-root, migrations au démarrage), le front (nginx), **Caddy** (HTTPS Let's Encrypt automatique, seul service qui publie des ports 80/443) et la sauvegarde quotidienne. Le DNS de `SITE_ADDRESS` doit pointer vers le serveur.

Valeurs à fixer dans `Backend/.env` pour la production : `JWT_SECRET_KEY` (≥ 32 caractères aléatoires), `ADMIN_PASSWORD` fort, `ENVIRONMENT=prod`, `COOKIE_SECURE=true` (déjà forcés par le compose), et une clé par fournisseur utilisé.

Premier démarrage : se connecter avec le compte `ADMIN_*`, téléverser les PDF depuis la page Documents (ou `docker compose exec api python -m scripts.ingest_corpus data/raw`), puis changer le mot de passe administrateur.

## B. Front statique + API conteneurisée + Postgres managé

1. **Base** : Neon, Supabase ou RDS avec l'extension `vector` ; renseigner `DATABASE_URL=postgresql+psycopg://…?sslmode=require`.
2. **API** : construire `Backend/Dockerfile` et la déployer sur Fly.io, Render, Cloud Run, etc. Un volume persistant sur `/app/data` conserve les PDF téléversés (ou prévoir un stockage objet). Variables : celles de `Backend/.env` + `ENVIRONMENT=prod`, `COOKIE_SECURE=true`, `TRUST_PROXY_HEADERS=true`, `CORS_ORIGINS=https://<front>`.
3. **Front** : `npm run build` dans `Frontend/` produit `dist/` (Netlify, Vercel, Cloudflare Pages, S3 + CDN). Le front et l'API doivent rester sous le même domaine : règle de réécriture `/api/* → API` côté hébergeur (c'est ce que fait `nginx.conf` en voie A). Sinon définir `VITE_API_URL` et, pour des cookies inter-domaines, `COOKIE_SAMESITE=none` + `COOKIE_SECURE=true`.

## Points d'attention

- **Un seul processus d'API** : le rate limiting par fenêtre glissante est en mémoire ; avec plusieurs instances, chacune a ses compteurs (le quota quotidien, lui, est compté en base). Voir `api/ratelimit.py`.
- **Flux SSE** : les proxys ne doivent pas mettre les réponses en tampon (Caddy : `flush_interval -1`, nginx : `proxy_buffering off`, déjà configurés).
- **Mémoire** : `--extra ml` embarque PyTorch (reranker/embeddings locaux). Sans modèles locaux, construire avec `--build-arg UV_EXTRAS=""` pour une image bien plus légère.
- Sauvegardes, restauration et rotation des secrets : `docs/EXPLOITATION.md`.

## Non vérifié dans l'environnement de développement

Les fichiers de ce lot (`docker-compose.prod.yml`, `Caddyfile`, Dockerfile non-root) n'ont **pas été exécutés** : aucun démon Docker n'y est disponible. Seule la validité YAML a été contrôlée. Faire un premier déploiement de test avant d'ouvrir le service.
