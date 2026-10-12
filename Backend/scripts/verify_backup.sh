#!/bin/sh
# Vérifie qu'une sauvegarde est restaurable : la restaure dans une base temporaire (créée puis
# supprimée) et affiche le nombre de lignes des tables principales.
#
#   ADMIN_URL=postgresql://user:pass@host:5432/postgres ./scripts/verify_backup.sh backups/rag-….dump
#
# ADMIN_URL doit pouvoir créer des bases et l'extension vector (superutilisateur).
set -eu

DUMP="${1:?usage : verify_backup.sh <fichier.dump>}"
ADMIN="${ADMIN_URL:?ADMIN_URL est requis (connexion pouvant créer une base)}"
ADMIN=$(printf '%s' "$ADMIN" | sed 's#^postgresql+[a-z0-9]*://#postgresql://#')
DB="rag_verify_$(date -u +%s)_$$"
BASE="${ADMIN%/*}"          # URL sans le nom de base
TARGET="$BASE/$DB"

psql "$ADMIN" -v ON_ERROR_STOP=1 -q -c "CREATE DATABASE \"$DB\""
trap 'psql "$ADMIN" -q -c "DROP DATABASE IF EXISTS \"$DB\"" >/dev/null 2>&1 || true' EXIT

pg_restore --no-owner --exit-on-error --dbname "$TARGET" "$DUMP"
for table in users conversations messages documents chunks rag_requests feedback; do
    count=$(psql "$TARGET" -At -c "SELECT count(*) FROM $table" 2>/dev/null || echo "absente")
    echo "$table=$count"
done
echo "OK : la sauvegarde $DUMP est restaurable"
