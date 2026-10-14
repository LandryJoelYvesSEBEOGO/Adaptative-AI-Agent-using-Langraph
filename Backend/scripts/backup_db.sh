#!/bin/sh
# Sauvegarde PostgreSQL (pg_dump, format « custom » compressé) avec rotation.
#
#   BACKUP_URL=postgresql://user:pass@host:5432/rag BACKUP_DIR=/backups ./scripts/backup_db.sh
#
# Variables : BACKUP_URL (obligatoire ; une URL SQLAlchemy « postgresql+psycopg:// » est acceptée),
#             BACKUP_DIR (défaut ./backups), RETENTION_DAYS (défaut 14).
# La sauvegarde est écrite sous un nom provisoire puis renommée : un fichier .dump est toujours complet.
set -eu

URL="${BACKUP_URL:-${DATABASE_URL:-}}"
[ -n "$URL" ] || { echo "BACKUP_URL (ou DATABASE_URL) est requis" >&2; exit 2; }
URL=$(printf '%s' "$URL" | sed 's#^postgresql+[a-z0-9]*://#postgresql://#')

DIR="${BACKUP_DIR:-./backups}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"
mkdir -p "$DIR"

FILE="$DIR/rag-$(date -u +%Y%m%dT%H%M%SZ).dump"
pg_dump --format=custom --no-owner --file "$FILE.partial" "$URL"
mv "$FILE.partial" "$FILE"
echo "Sauvegarde écrite : $FILE ($(wc -c < "$FILE") octets)"

# Rotation : on supprime les sauvegardes plus anciennes que RETENTION_DAYS (et les .partial orphelins)
find "$DIR" -maxdepth 1 \( -name 'rag-*.dump' -o -name 'rag-*.dump.partial' \) -mtime +"$RETENTION_DAYS" -delete
