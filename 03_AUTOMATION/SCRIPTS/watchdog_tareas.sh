#!/usr/bin/env bash
# watchdog_tareas.sh — vigilante de tareas despachadas a Codex.
#
# POR QUE EXISTE
# Durante la sesion del 13/08 los estancamientos se descubrian solo cuando el
# fundador preguntaba "estado". Un latido periodico no sirve: reporta tamano,
# no detecta que el tamano dejo de crecer. Y ademas cuesta tokens en cada aviso.
#
# COMO FUNCIONA, Y POR QUE NO CUESTA TOKENS
# Corre en silencio y SOLO termina cuando encuentra una anomalia. Lanzado en
# segundo plano, el harness avisa una unica vez: al salir. Mientras todo va bien
# no emite nada y no cuesta nada.
#
# Ademas escribe su estado en .ai/state/watchdog.json en cada ciclo, para que
# responder "estado" cueste una lectura de archivo en vez de cinco comandos.
#
# ANOMALIAS QUE DETECTA
#   1. Tarea estancada: su log no crece en STALL_MIN minutos.
#   2. Tarea muerta: no hay proceso vivo y tampoco informe final.
#   3. Servicio caido: AnythingLLM u Ollama dejan de responder.
#
# USO
#   bash 03_AUTOMATION/SCRIPTS/watchdog_tareas.sh          # desde WSL
#   bash 03_AUTOMATION/SCRIPTS/watchdog_tareas.sh 15 45    # stall_min ttl_horas

set -uo pipefail

RAIZ="/mnt/c/AI_WORKFLOW_V2"
STALL_MIN="${1:-12}"          # minutos sin crecer antes de declarar estancamiento
TTL_HORAS="${2:-8}"           # tope de vida del propio vigilante
GRACIA_MIN="${3:-25}"         # minutos que se tolera un servicio caido si hay tarea activa
INTERVALO=60                  # segundos entre ciclos
ESTADO="$RAIZ/.ai/state/watchdog.json"

mkdir -p "$RAIZ/.ai/state"
inicio=$(date +%s)
declare -A ultimo_tam
declare -A ultimo_cambio

anomalia() {
  # $1 = tipo, $2 = detalle
  printf 'ANOMALIA %s: %s\n' "$1" "$2"
  printf '{"estado":"anomalia","tipo":"%s","detalle":"%s","ts":"%s"}\n' \
    "$1" "$2" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$ESTADO"
  exit 1
}

while true; do
  ahora=$(date +%s)
  if (( ahora - inicio > TTL_HORAS * 3600 )); then
    printf 'FIN: el vigilante alcanzo su tope de %s horas sin anomalias.\n' "$TTL_HORAS"
    printf '{"estado":"fin_ttl","ts":"%s"}\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$ESTADO"
    exit 0
  fi

  vivas=0
  resumen=""

  for log in "$RAIZ"/.ai/task*_stream.log; do
    [ -e "$log" ] || continue
    base=$(basename "$log")
    num="${base#task}"; num="${num%%_*}"
    informe="$RAIZ/.ai/reports/TASK-${num}.raw.md"

    # Si ya entrego su informe, esta cerrada: no se vigila.
    [ -f "$informe" ] && continue

    # Solo vigila lo reciente: un log viejo de otra sesion no es una tarea viva.
    edad_log=$(( ahora - $(stat -c %Y "$log" 2>/dev/null || echo "$ahora") ))
    (( edad_log > 3600 )) && continue

    vivas=$((vivas+1))
    tam=$(stat -c %s "$log" 2>/dev/null || echo 0)
    prev="${ultimo_tam[$num]:-}"

    if [ -z "$prev" ]; then
      ultimo_tam[$num]=$tam
      ultimo_cambio[$num]=$ahora
    elif [ "$tam" != "$prev" ]; then
      ultimo_tam[$num]=$tam
      ultimo_cambio[$num]=$ahora
    else
      quieto=$(( (ahora - ${ultimo_cambio[$num]}) / 60 ))
      if (( quieto >= STALL_MIN )); then
        anomalia "estancada" "TASK-${num} lleva ${quieto} min sin escribir en su log y no entrego informe"
      fi
    fi

    # Proceso vivo?
    # Se exige que la coincidencia sea un proceso de codex, no cualquier linea de
    # comando que mencione el nombre de la tarea. Sin ese ancla, un shell que
    # contenga el texto se cuenta a si mismo como si la tarea siguiera viva:
    # es la misma trampa del autoemparejamiento que ya costo tiempo tres veces.
    if ! pgrep -f "codex.*TASK-${num}\.raw\.md" >/dev/null 2>&1; then
      anomalia "muerta" "TASK-${num} no tiene proceso de codex vivo y no existe su informe"
    fi

    resumen="${resumen}${num}:$((tam/1024))k "
  done

  # Servicios.
  # AnythingLLM esta publicado por Docker, asi que se alcanza desde WSL.
  #
  # PERIODO DE GRACIA, y nace de una falsa alarma real del 14/08 a las 11:05 UTC:
  # las tareas detienen el contenedor A PROPOSITO para respaldar, reembeber o
  # restaurar, y durante esa ventana no responde. Avisar ahi despierta al fundador
  # por algo que esta bien. Solo se declara anomalia si el servicio sigue caido
  # DESPUES de la gracia, o si esta caido sin ninguna tarea activa que lo explique.
  cod_allm=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 http://127.0.0.1:3110/api/ping 2>/dev/null)
  [ -n "$cod_allm" ] || cod_allm="000"
  if [ "$cod_allm" = "200" ]; then
    caido_desde=""
  else
    [ -n "${caido_desde:-}" ] || caido_desde=$ahora
    caido_min=$(( (ahora - caido_desde) / 60 ))
    if (( vivas == 0 )); then
      anomalia "servicio" "AnythingLLM respondio ${cod_allm} y no hay ninguna tarea activa que lo explique"
    elif (( caido_min >= GRACIA_MIN )); then
      anomalia "servicio" "AnythingLLM lleva ${caido_min} min sin responder, mas alla de la gracia de ${GRACIA_MIN} min"
    fi
  fi

  # Ollama corre NATIVO en Windows enlazado a loopback, asi que desde WSL es
  # invisible por diseno (gotcha 66). Preguntarle directo desde aqui da siempre
  # 000 y produce una falsa alarma: la primera version de este vigilante murio
  # por eso a los pocos segundos. Se consulta a traves del contenedor del router,
  # que si lo alcanza por la puerta de Docker.
  if docker exec anythingllm-router python3 -c "
import urllib.request, sys
try:
    with urllib.request.urlopen('http://host.docker.internal:11435/api/tags', timeout=10) as r:
        sys.exit(0 if r.status == 200 else 1)
except Exception:
    sys.exit(1)
" >/dev/null 2>&1; then
    cod_oll="200"
  else
    cod_oll="inalcanzable"
    anomalia "servicio" "Ollama no responde en el 11435 visto desde el contenedor del router"
  fi

  printf '{"estado":"ok","tareas_vivas":%s,"detalle":"%s","anythingllm":"%s","ollama":"%s","ts":"%s"}\n' \
    "$vivas" "$resumen" "$cod_allm" "$cod_oll" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$ESTADO"

  # Si no queda ninguna tarea viva, el vigilante cumplio su funcion y sale limpio.
  if (( vivas == 0 )); then
    printf 'FIN: no quedan tareas vivas que vigilar.\n'
    printf '{"estado":"fin_sin_tareas","ts":"%s"}\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$ESTADO"
    exit 0
  fi

  sleep "$INTERVALO"
done
