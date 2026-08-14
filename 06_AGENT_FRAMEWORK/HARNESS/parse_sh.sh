#!/usr/bin/env bash
# Parsea en lote los .sh listados en $1 (uno por linea, rutas con /).
# Emite "archivo|error" SOLO para los que fallan bash -n. Sin truncado.
while IFS= read -r f; do
    err=$(bash -n "$f" 2>&1) || printf '%s|%s\n' "$f" "$(printf '%s' "$err" | tr '\n' ' ')"
done < "$1"
