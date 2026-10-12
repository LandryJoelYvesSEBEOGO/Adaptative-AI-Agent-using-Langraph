#!/bin/sh
# Restaure une sauvegarde dans une base PostgreSQL (avec l'extension pgvector installée).
#
#   RESTORE_URL=postgresql://user:pass@host:5432/rag ./scripts/restore_db.sh backups/rag-….dump
#
# --clean --if-exists : les objets existants sont remplacés. À lancer sur une base vide ou, en cas
# de reprise après incident, API arrêtée. Voir docs/EXPLOITATION.md.
set -eu

DUMP="${1:?usage : restore_db.sh <fichier.dump>}"
URL="${RESTORE_URL:-${DATABASE_URL:-}}"
[ -n "$URL" ] || { echo "RESTORE_URL (ou DATABASE_URL) est requis" >&2; exit 2; }
URL=$(printf '%s' "$URL" | sed 's#^postgresql+[a-z0-9]*://#postgresql://#')

pg_restore --clean --if-exists --no-owner --dbname "$URL" "$DUMP"
echo "Restauration terminée depuis $DUMP"
