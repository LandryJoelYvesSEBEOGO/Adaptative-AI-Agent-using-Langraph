# Frontend — RAG System

Interface de chat et tableau de bord d'administration du RAG System.

**Stack** : React, TypeScript, Vite, Tailwind CSS, shadcn/ui, TanStack Query, Zustand, Recharts.

## Lancement

```bash
npm install
cp .env.example .env.local
npm run dev
```

L'application est servie sur http://localhost:8080 et attend l'API sur l'URL définie par `VITE_API_BASE_URL` (défaut : `http://127.0.0.1:8000/api/v1`).

## Scripts

| Commande | Rôle |
|---|---|
| `npm run dev` | Serveur de développement |
| `npm run build` | Build de production dans `dist/` |
| `npm run preview` | Prévisualisation du build |
| `npm run lint` | ESLint |

## Organisation

| Dossier | Contenu |
|---|---|
| `src/pages/` | Pages : accueil, connexion, chat, et `admin/` |
| `src/components/` | Composants applicatifs ; `ui/` contient les composants shadcn |
| `src/services/` | Client HTTP, gestion des erreurs, configuration de l'API |
| `src/stores/` | État global (authentification) |
| `src/hooks/`, `src/lib/` | Hooks et utilitaires |
