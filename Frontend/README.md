# Frontend — RAG System

Interface de chat et tableau de bord d'administration du RAG System.

**Stack** : React 19, TypeScript (strict), Vite, Tailwind CSS 4, shadcn/ui, TanStack Query, react-markdown, react-pdf, Recharts.

## Lancement

```bash
npm install
cp .env.example .env.local
npm run dev
```

L'application est servie sur http://localhost:8080 ; le serveur Vite relaie `/api` vers le backend (`VITE_PROXY_TARGET`, défaut `http://127.0.0.1:8000`) : même origine, donc cookies de session sans configuration CORS.

## Scripts

| Commande | Rôle |
|---|---|
| `npm run dev` | Serveur de développement |
| `npm run build` | Typage puis build de production dans `dist/` |
| `npm run typecheck` | TypeScript strict |
| `npx eslint .` | Lint |
| `npm test` | Tests unitaires et composants (Vitest) |
| `npm run test:e2e` | Parcours navigateur (Playwright) : `npm run build` d'abord ; `PLAYWRIGHT_CHROMIUM_PATH` pour utiliser un Chromium déjà installé |
| `npm run api:generate` | Régénère `src/api/schema.d.ts` depuis `openapi.json` |

Le client API est **généré** : après un changement du backend, lancer `uv run python -m scripts.export_openapi` dans `Backend/`, puis `npm run api:generate`.

## Organisation

| Dossier | Contenu |
|---|---|
| `src/api/` | Client typé (`openapi-fetch`), renouvellement de session, flux SSE (`stream.ts`), hooks TanStack Query |
| `src/auth/` | Session (cookie httpOnly) : `useSession`, `useLogin`, `useLogout` |
| `src/pages/` | Pages : accueil, connexion / inscription, chat, et `admin/` (dashboard, métriques, requêtes, documents, utilisateurs) |
| `src/components/chat/` | Messages Markdown, citations, panneau des sources avec aperçu PDF |
| `src/components/` | Autres composants ; `ui/` contient les composants shadcn utilisés |
| `src/hooks/` | `useChat` (flux, Stop, régénération) |
| `e2e/` | Parcours navigateur |
