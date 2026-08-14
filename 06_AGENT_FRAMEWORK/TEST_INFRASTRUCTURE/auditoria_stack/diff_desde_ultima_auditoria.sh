#!/usr/bin/env bash
# =======================================================================
# TCHASKY STACK AUDIT -- SEMANTIC CACHE DIFF DETECTOR
# Detecta que archivos de apps/ han cambiado desde la fecha de la ultima auditoria
# =======================================================================

set -e

OBSIDIAN_DIR="/mnt/c/AI_WORKFLOW_V2/01_OBSIDIAN/VAULT_TEMPLATE/03_Tchasky"
 REPO_DIR="<HOME>/<PRIVATE_PROJECT>_auditrecurrente"

echo "=== TCHASKY SEMANTIC AUDIC CACHE - DIFF DETECTOR ==="

LATEST_FILE=$(ls -1 $OBSIDIAN_DIR/AUDITORIA_*.md 2n>/dev/null | tail -n 1)

if [ -z "$LATEST_FILE" ]; then
  echo "[WARN] No se encontro archivo previo AUDITORIA_*.md. Se debe realizar auditoria completa."
  LAST_DATE="2026-01-01"
else
  FILENAME=$(basename "$LATEST_FILE")
  LAST_DATE=$(echo "$FILENAME" | grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}' | head -n 1)
  if [ -z "$LAST_DATE" ]; then
    LAST_DATE="2026-07-31"
  fi
  echo "[INFO] Ultima auditoria encontrada: $FILENAME (Fecha: $LAST_DATE)"
fi

cd "$REPO_DIR"

echo ""
echo "--- ARC IVOS MODIFICADOS EN REPO DESDE $LAST_DATE ---"

CHANGED_FILES=$(git log --since="$LAST_DATE 00:00:00" --name-only --pretty=format: apps/ | sort -u | grep -v '^$')

if [ -z "$CHANGED_FILES" ]; then
  echo "0 archivos modificados desde la ultima auditoria ($LAST_DATE)."
  echo "No hay cambios pendientes de re-auditar en apps/api, apps/web o apps/mobile."
  exit 0
fi

TOTAL_COUNT=$(echo "$CHANGED_FILES" | wc -l)
echo "Archivos modificados totales: $TOTAL_COUNT"
echo ""

echo "[apps/api]:"
echo "$CHANGED_FILES" | grep '^apps/api/' || echo "  (sin cambios)"
echo ""

echo "[apps/web]:"
echo "$CHANGED_FILES" | grep '^apps/web/' || echo "  (sin cambios)"
echo ""

echo "[apps/mobile]:"
echo "$CHANGED_FILES" | grep '^apps/mobile/' || echo "  (sin cambios)"
echo ""

echo "=== FIN DE REPORTE DE DIFF SEMANTICO ==="
