# -*- coding: utf-8 -*-
"""Compara recuperación densa con enrutamiento y diversidad.

Hace una sola consulta amplia por pregunta y evalúa la base y todas las
variantes sobre exactamente los mismos candidatos. No escribe en LanceDB ni
modifica AnythingLLM.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import tempfile
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

from corpus_routing import (
    cargar_perfiles,
    corpus_de_fuente,
    enrutar_y_diversificar,
    fuente_de,
    normalizar_ruta,
)


RAIZ = Path(__file__).resolve().parent
DB_PREDETERMINADA = RAIZ / "storage" / "anythingllm.db"
GOLDEN_PREDETERMINADO = RAIZ / "rag_golden_set.json"
SONDA_PREDETERMINADA = RAIZ / "TASK-108_ROUTING_PROBE_2026-08-13.json"
PERFILES_PREDETERMINADOS = RAIZ / "routing_profiles.json"
BASE_PREDETERMINADA = "http://127.0.0.1:3110"
GOLDEN_SHA256_ESPERADO = "603293c5dd3d5beec1a9054d3bd51563d7f5cd2c327cbd619d480ee134b9778f"
GOLDEN_VERSION_ESPERADA = "88-preguntas-v3-task115"
TOTAL_ESPERADO = 88
RESPONDIBLES_ESPERADAS = 80
SIN_RESPUESTA_ESPERADAS = 8

ORIGEN_A_CORPUS = {
    "03_Tchasky/**": "tchasky",
    "10_Personal/**": "personal",
    "Cybersecurity Skills Reference": "ciberseguridad",
    "Framework Skills Superpowers": "framework",
}


def lista_enteros(valor: str) -> List[int]:
    try:
        numeros = [int(parte.strip()) for parte in valor.split(",") if parte.strip()]
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Se esperaba una lista como 1,2,3.") from exc
    if not numeros or any(numero < 1 for numero in numeros):
        raise argparse.ArgumentTypeError("Todos los límites deben ser enteros positivos.")
    return sorted(set(numeros))


def lista_no_negativos(valor: str) -> List[float]:
    try:
        numeros = [float(parte.strip()) for parte in valor.split(",") if parte.strip()]
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Se esperaba una lista como 0,20,40,80.") from exc
    if not numeros or any(numero < 0 for numero in numeros):
        raise argparse.ArgumentTypeError("Todas las bonificaciones deben ser no negativas.")
    return sorted(set(numeros))


def argumentos() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Mide el conjunto oficial de 80+8 con y sin enrutamiento/diversidad."
    )
    parser.add_argument("--base-url", default=BASE_PREDETERMINADA)
    parser.add_argument("--golden", type=Path, default=GOLDEN_PREDETERMINADO)
    parser.add_argument("--sonda", type=Path, default=SONDA_PREDETERMINADA)
    parser.add_argument("--perfiles", type=Path, default=PERFILES_PREDETERMINADOS)
    parser.add_argument("--db", type=Path, default=DB_PREDETERMINADA)
    parser.add_argument("--api-key-env", default="ANYTHINGLLM_API_KEY")
    parser.add_argument("--candidate-pool", type=int, default=100)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument(
        "--document-caps",
        type=lista_enteros,
        default=[1, 2, 3],
        help="Valores de N que se compararán sin repetir consultas HTTP.",
    )
    parser.add_argument("--routing-bonus-ranks", type=float, default=40.0)
    parser.add_argument(
        "--routing-bonus-sweep",
        type=lista_no_negativos,
        default=[],
        help="Bonificaciones adicionales que se compararán con N=1 sobre el mismo pool.",
    )
    parser.add_argument("--minimum-route-score", type=float, default=2.0)
    parser.add_argument("--route-saturation", type=float, default=4.0)
    parser.add_argument(
        "--score-threshold",
        type=float,
        default=0.0,
        help="Umbral por petición, no persistente. Cero conserva el pool para reordenarlo.",
    )
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument(
        "--output",
        type=Path,
        default=RAIZ / "TASK-119_MEASUREMENT.json",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Valida contratos y parámetros sin consultar AnythingLLM.",
    )
    args = parser.parse_args()
    if args.candidate_pool < args.top_k:
        parser.error("candidate-pool debe ser mayor o igual que top-k.")
    if args.top_k < 1:
        parser.error("top-k debe ser positivo.")
    if args.routing_bonus_ranks < 0:
        parser.error("routing-bonus-ranks no puede ser negativo.")
    return args


def sha256(ruta: Path) -> str:
    digest = hashlib.sha256()
    with ruta.open("rb") as archivo:
        for bloque in iter(lambda: archivo.read(1024 * 1024), b""):
            digest.update(bloque)
    return digest.hexdigest()


class CambioGolden(RuntimeError):
    """Indica que la vara cambió durante una corrida certificada."""


def leer_json_estable(ruta: Path) -> tuple[Dict[str, Any], Dict[str, Any]]:
    """Lee contenido y metadatos de una versión estable del archivo."""
    estado_antes = ruta.stat()
    contenido = ruta.read_bytes()
    estado_despues = ruta.stat()
    firma_antes = (estado_antes.st_size, estado_antes.st_mtime_ns)
    firma_despues = (estado_despues.st_size, estado_despues.st_mtime_ns)
    if firma_antes != firma_despues:
        raise CambioGolden("El conjunto dorado cambió mientras se estaba leyendo.")
    try:
        datos = json.loads(contenido.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SystemExit("El conjunto dorado no es JSON UTF-8 válido: %s" % exc) from exc
    huella = {
        "sha256": hashlib.sha256(contenido).hexdigest(),
        "bytes": len(contenido),
        "mtime_ns": estado_despues.st_mtime_ns,
    }
    return datos, huella


def verificar_golden_inmutable(ruta: Path, huella_inicial: Mapping[str, Any]) -> None:
    _, huella_actual = leer_json_estable(ruta)
    if huella_actual != dict(huella_inicial):
        raise CambioGolden(
            "El conjunto dorado cambió durante la corrida; se aborta para no mezclar varas. "
            "Huella inicial=%s, huella actual=%s."
            % (huella_inicial.get("sha256"), huella_actual.get("sha256"))
        )


def cargar_contratos(
    args: argparse.Namespace,
) -> tuple[Dict[str, Any], Dict[int, str], Dict[str, Any]]:
    golden, huella_golden = leer_json_estable(args.golden)
    respondibles = [p for p in golden.get("preguntas", []) if not p.get("sin_respuesta", False)]
    sin_respuesta = [p for p in golden.get("preguntas", []) if p.get("sin_respuesta", False)]
    if huella_golden["sha256"] != GOLDEN_SHA256_ESPERADO:
        raise SystemExit(
            "Este arnés certifica el conjunto TASK-115 con SHA-256 %s; encontró %s."
            % (GOLDEN_SHA256_ESPERADO, huella_golden["sha256"])
        )
    cuentas = (len(golden.get("preguntas", [])), len(respondibles), len(sin_respuesta))
    esperadas = (TOTAL_ESPERADO, RESPONDIBLES_ESPERADAS, SIN_RESPUESTA_ESPERADAS)
    if cuentas != esperadas:
        raise SystemExit(
            "Este arnés certifica %d entradas (%d respondibles y %d sin respuesta); "
            "encontró %d (%d y %d)." % (esperadas + cuentas)
        )
    if golden.get("_version") != GOLDEN_VERSION_ESPERADA:
        raise SystemExit(
            "Versión inesperada del conjunto: %r." % golden.get("_version")
        )
    for numero, caso in enumerate(golden["preguntas"], 1):
        es_negativa = bool(caso.get("sin_respuesta", False))
        if es_negativa != (caso.get("esperado") is None):
            raise SystemExit("Caso sin respuesta incoherente en la pregunta %d." % numero)
        if es_negativa:
            continue
        esperado = normalizar_ruta(caso.get("esperado"))
        if not esperado or "/" not in esperado:
            raise SystemExit("Fuente esperada inválida en la pregunta %d." % numero)

    sonda = json.loads(args.sonda.read_text(encoding="utf-8"))
    if sonda.get("method") != "oracle corpus routing over one unified LanceDB namespace":
        raise SystemExit("La sonda de TASK-108 no tiene el contrato esperado.")
    origen_historico: Dict[int, str] = {}
    for fila in sonda.get("results", []):
        origen = fila.get("origin")
        if origen not in ORIGEN_A_CORPUS:
            raise SystemExit("Origen desconocido en la sonda: %r" % origen)
        origen_historico[int(fila["number"])] = ORIGEN_A_CORPUS[origen]
    if len(origen_historico) != 42:
        raise SystemExit("La sonda de TASK-108 ya no contiene sus 42 casos históricos.")

    origen_por_numero = {
        numero: corpus_de_fuente(caso.get("esperado"))
        for numero, caso in enumerate(golden["preguntas"], 1)
        if not caso.get("sin_respuesta", False)
    }
    for numero, corpus_historico in origen_historico.items():
        if origen_por_numero.get(numero) != corpus_historico:
            raise SystemExit(
                "La clasificación de corpus ya no coincide con TASK-108 en la pregunta %d."
                % numero
            )
    return golden, origen_por_numero, huella_golden


def obtener_clave(nombre_variable: str, ruta_db: Path) -> str:
    """Prefiere el entorno; el respaldo temporal evita abrir la base activa."""
    clave_entorno = os.environ.get(nombre_variable, "").strip()
    if clave_entorno:
        return clave_entorno

    descriptor, nombre_temporal = tempfile.mkstemp(prefix="task112_api_", suffix=".db")
    os.close(descriptor)
    try:
        shutil.copy2(ruta_db, nombre_temporal)
        conexion = sqlite3.connect(nombre_temporal)
        try:
            tablas = [
                fila[0]
                for fila in conexion.execute("SELECT name FROM sqlite_master WHERE type='table'")
                if "api_key" in fila[0].casefold()
            ]
            if not tablas:
                raise SystemExit("No se encontró la tabla de claves de API.")
            tabla = tablas[0].replace('"', '""')
            fila = conexion.execute('SELECT secret FROM "%s" LIMIT 1' % tabla).fetchone()
            if not fila or not fila[0]:
                raise SystemExit("No se encontró una clave de API utilizable.")
            return str(fila[0])
        finally:
            conexion.close()
    finally:
        try:
            os.unlink(nombre_temporal)
        except FileNotFoundError:
            pass


def buscar(
    base_url: str,
    clave: str,
    espacio: str,
    pregunta: str,
    cantidad: int,
    umbral: Optional[float],
    timeout: float,
) -> List[Mapping[str, Any]]:
    cuerpo = {"query": pregunta, "topN": cantidad}
    if umbral is not None:
        cuerpo["scoreThreshold"] = umbral
    solicitud = urllib.request.Request(
        "%s/api/v1/workspace/%s/vector-search" % (base_url.rstrip("/"), espacio),
        data=json.dumps(cuerpo).encode("utf-8"),
        headers={
            "Authorization": "Bearer %s" % clave,
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(solicitud, timeout=timeout) as respuesta:
            datos = json.loads(respuesta.read())
    except urllib.error.HTTPError as exc:
        detalle = exc.read(500).decode("utf-8", errors="replace")
        raise RuntimeError("AnythingLLM respondió HTTP %d: %s" % (exc.code, detalle)) from exc
    resultados = datos.get("results")
    if not isinstance(resultados, list):
        raise RuntimeError("La respuesta de vector-search no contiene una lista results.")
    return [resultado for resultado in resultados if isinstance(resultado, Mapping)]


def posicion(fuente_esperada: str, candidatos: Sequence[Mapping[str, Any]], top_k: int) -> Optional[int]:
    objetivo = normalizar_ruta(fuente_esperada).casefold()
    for rango, candidato in enumerate(candidatos[:top_k], 1):
        if fuente_de(candidato).casefold() == objetivo:
            return rango
    return None


def resumen_candidato(candidato: Mapping[str, Any]) -> Dict[str, Any]:
    resumen: Dict[str, Any] = {"docSource": fuente_de(candidato)}
    for clave in ("score", "similarity", "distance"):
        if clave in candidato:
            resumen[clave] = candidato[clave]
    return resumen


def calcular_metricas(
    posiciones: Sequence[Optional[int]],
    total_respondibles: int,
    abstenciones: Sequence[Optional[bool]],
    total_sin_respuesta: int,
) -> Dict[str, Any]:
    metricas: Dict[str, Any] = {}
    for k in (1, 3, 5):
        aciertos = sum(1 for valor in posiciones if valor is not None and valor <= k)
        metricas["recall@%d" % k] = {
            "aciertos": aciertos,
            "total": total_respondibles,
            "porcentaje": (
                100.0 * aciertos / total_respondibles if total_respondibles else 0.0
            ),
        }
    metricas["mrr@5"] = (
        sum(1.0 / valor for valor in posiciones if valor is not None and valor <= 5)
        / total_respondibles
        if total_respondibles
        else 0.0
    )
    abstenciones_correctas = sum(valor is True for valor in abstenciones)
    metricas["abstencion"] = {
        "aciertos": abstenciones_correctas,
        "total": total_sin_respuesta,
        "porcentaje": (
            100.0 * abstenciones_correctas / total_sin_respuesta
            if total_sin_respuesta
            else None
        ),
    }
    aciertos_cinco = metricas["recall@5"]["aciertos"]
    total_global = total_respondibles + total_sin_respuesta
    metricas["exactitud_global@5"] = {
        "aciertos": aciertos_cinco + abstenciones_correctas,
        "total": total_global,
        "porcentaje": (
            100.0 * (aciertos_cinco + abstenciones_correctas) / total_global
            if total_global
            else 0.0
        ),
    }
    return metricas


def guardar(ruta: Path, informe: Mapping[str, Any]) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    temporal = ruta.with_suffix(ruta.suffix + ".tmp")
    temporal.write_text(json.dumps(informe, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporal.replace(ruta)


def main() -> int:
    args = argumentos()
    golden, origen_por_numero, huella_golden = cargar_contratos(args)
    perfiles = cargar_perfiles(args.perfiles)
    especificaciones = [
        {
            "nombre": "enrutamiento_diversidad_n%d" % limite,
            "maximo_por_documento": limite,
            "bonificacion_rangos": args.routing_bonus_ranks,
        }
        for limite in args.document_caps
    ]
    for bonificacion in args.routing_bonus_sweep:
        etiqueta = "%g" % bonificacion
        especificaciones.append(
            {
                "nombre": "bonificacion_%s_n1" % etiqueta.replace(".", "_").replace("-", "m"),
                "maximo_por_documento": 1,
                "bonificacion_rangos": bonificacion,
            }
        )
    escenarios = ["base_semantica"] + [e["nombre"] for e in especificaciones]
    if len(escenarios) != len(set(escenarios)):
        raise SystemExit("Los parámetros producen nombres de escenario duplicados.")
    respondibles = sum(not p.get("sin_respuesta", False) for p in golden["preguntas"])
    negativas = len(golden["preguntas"]) - respondibles
    parametros = {
        "candidate_pool": args.candidate_pool,
        "top_k": args.top_k,
        "document_caps": args.document_caps,
        "routing_bonus_ranks": args.routing_bonus_ranks,
        "routing_bonus_sweep": args.routing_bonus_sweep,
        "minimum_route_score": args.minimum_route_score,
        "route_saturation": args.route_saturation,
        "score_threshold_respondibles": args.score_threshold,
        "abstencion": (
            "usa el umbral vigente del workspace omitiendo scoreThreshold en la petición"
        ),
    }
    informe: Dict[str, Any] = {
        "estado": "solo_validacion" if args.validate_only else "en_progreso",
        "inicio": datetime.now().astimezone().isoformat(),
        "metodo": "un pool semántico compartido; reordenamiento no excluyente por ruta y docSource",
        "advertencia": "No es búsqueda híbrida y no modifica el índice ni la configuración.",
        "golden": {
            "ruta": str(args.golden),
            **huella_golden,
            "version": golden.get("_version"),
            "entradas": len(golden["preguntas"]),
            "preguntas_respondibles": respondibles,
            "preguntas_sin_respuesta": negativas,
            "valor_por_acierto_puntos": 100.0 / respondibles,
        },
        "sonda_task108": {
            "ruta": str(args.sonda),
            "sha256": sha256(args.sonda),
            "recall_at_4": json.loads(args.sonda.read_text(encoding="utf-8")).get("recall_at_4"),
            "casos_historicos_validados": 42,
        },
        "perfiles": {"ruta": str(args.perfiles), "sha256": sha256(args.perfiles)},
        "parametros": parametros,
        "escenarios": escenarios,
        "especificaciones_capa": especificaciones,
        "resultados": [],
    }

    def certificar_inmutabilidad() -> None:
        try:
            verificar_golden_inmutable(args.golden, huella_golden)
        except CambioGolden as exc:
            informe["estado"] = "abortado_por_cambio_del_golden"
            informe["error_integridad"] = str(exc)
            informe["fin"] = datetime.now().astimezone().isoformat()
            guardar(args.output, informe)
            raise SystemExit(str(exc)) from exc

    if args.validate_only:
        certificar_inmutabilidad()
        informe["estado"] = "validado_sin_consultar_indice"
        guardar(args.output, informe)
        print(
            "Contratos válidos: %d entradas, %d respondibles, %d sin respuesta y SHA-256 fijado."
            % (len(golden["preguntas"]), respondibles, negativas)
        )
        print("La sonda histórica de TASK-108 conserva sus 42 casos.")
        print("No se consultó AnythingLLM ni el índice.")
        print("RESULTADO=%s" % args.output)
        return 0

    clave = obtener_clave(args.api_key_env, args.db)
    espacio = golden["_espacio"]
    posiciones: Dict[str, List[Optional[int]]] = {nombre: [] for nombre in escenarios}
    abstenciones: Dict[str, List[Optional[bool]]] = {nombre: [] for nombre in escenarios}
    errores = 0

    for numero, caso in enumerate(golden["preguntas"], 1):
        certificar_inmutabilidad()
        es_negativa = bool(caso.get("sin_respuesta", False))
        esperado = normalizar_ruta(caso.get("esperado"))
        registro: Dict[str, Any] = {
            "numero": numero,
            "pregunta": caso["pregunta"],
            "sin_respuesta": es_negativa,
            "esperado": esperado or None,
        }
        if not es_negativa:
            registro["corpus_esperado"] = origen_por_numero[numero]
        inicio = time.monotonic()
        escenarios_registrados = set()
        try:
            candidatos = buscar(
                args.base_url,
                clave,
                espacio,
                caso["pregunta"],
                args.candidate_pool,
                None if es_negativa else args.score_threshold,
                args.timeout,
            )
            certificar_inmutabilidad()
            registro["candidatos_recibidos"] = len(candidatos)
            registro["duracion_segundos"] = time.monotonic() - inicio
            if es_negativa:
                abstuvo_base = not candidatos
                abstenciones["base_semantica"].append(abstuvo_base)
                registro["base_semantica"] = {
                    "abstencion": abstuvo_base,
                    "top": [resumen_candidato(c) for c in candidatos[: args.top_k]],
                }
            else:
                pos_base = posicion(esperado, candidatos, args.top_k)
                posiciones["base_semantica"].append(pos_base)
                registro["base_semantica"] = {
                    "posicion": pos_base,
                    "top": [resumen_candidato(c) for c in candidatos[: args.top_k]],
                }
            escenarios_registrados.add("base_semantica")

            for especificacion in especificaciones:
                nombre = especificacion["nombre"]
                resultado = enrutar_y_diversificar(
                    caso["pregunta"],
                    candidatos,
                    top_k=args.top_k,
                    maximo_por_documento=especificacion["maximo_por_documento"],
                    bonificacion_rangos=especificacion["bonificacion_rangos"],
                    puntaje_minimo=args.minimum_route_score,
                    saturacion=args.route_saturation,
                    perfiles=perfiles,
                )
                if es_negativa:
                    abstuvo_capa = not resultado.seleccion_top_k
                    abstenciones[nombre].append(abstuvo_capa)
                    resultado_caso: Dict[str, Any] = {"abstencion": abstuvo_capa}
                else:
                    pos_capa = posicion(esperado, resultado.seleccion_top_k, args.top_k)
                    posiciones[nombre].append(pos_capa)
                    resultado_caso = {"posicion": pos_capa}
                escenarios_registrados.add(nombre)
                rutas_priorizadas = [
                    ruta for ruta, peso in resultado.clasificacion.pesos.items() if peso > 0
                ]
                resultado_caso.update({
                    "rutas_priorizadas": rutas_priorizadas,
                    "pesos_ruta": dict(resultado.clasificacion.pesos),
                    "coincidencias": {
                        ruta: list(valores)
                        for ruta, valores in resultado.clasificacion.coincidencias.items()
                        if valores
                    },
                    "top_k_incompleto_por_falta_de_diversidad": (
                        resultado.top_k_incompleto_por_falta_de_diversidad
                    ),
                    "top": [
                        resumen_candidato(c) for c in resultado.seleccion_top_k
                    ],
                })
                registro[nombre] = resultado_caso
        except Exception as exc:  # conserva un informe parcial ante fallos de infraestructura
            errores += 1
            registro["error"] = "%s: %s" % (type(exc).__name__, exc)
            for nombre in escenarios:
                if nombre not in escenarios_registrados:
                    if es_negativa:
                        abstenciones[nombre].append(None)
                    else:
                        posiciones[nombre].append(None)
        informe["resultados"].append(registro)
        informe["consultas_completadas"] = len(informe["resultados"])
        informe["errores_tecnicos"] = errores
        guardar(args.output, informe)
        if es_negativa:
            print(
                "%02d/%d sin_respuesta abstencion_base=%s"
                % (
                    len(informe["resultados"]),
                    len(golden["preguntas"]),
                    "sí" if registro.get("base_semantica", {}).get("abstencion") else "no",
                )
            )
        else:
            print(
                "%02d/%d base=%s %s"
                % (
                    len(informe["resultados"]),
                    len(golden["preguntas"]),
                    registro.get("base_semantica", {}).get("posicion") or "-",
                    " ".join(
                        "%s=%s"
                        % (nombre, registro.get(nombre, {}).get("posicion") or "-")
                        for nombre in escenarios[1:]
                    ),
                )
            )

    certificar_inmutabilidad()
    informe["fin"] = datetime.now().astimezone().isoformat()
    informe["estado"] = "completo" if errores == 0 else "completo_con_errores"
    informe["metricas"] = {
        nombre: calcular_metricas(
            posiciones[nombre], respondibles, abstenciones[nombre], negativas
        )
        for nombre in escenarios
    }
    base = informe["metricas"]["base_semantica"]
    informe["deltas_puntos_vs_base"] = {
        nombre: {
            clave: metricas[clave]["porcentaje"] - base[clave]["porcentaje"]
            for clave in ("recall@1", "recall@3", "recall@5")
        }
        for nombre, metricas in informe["metricas"].items()
        if nombre != "base_semantica"
    }
    guardar(args.output, informe)

    print("\nESCENARIO                         RECALL@1  RECALL@3  RECALL@5  MRR@5  ABSTENCION")
    for nombre in escenarios:
        metrica = informe["metricas"][nombre]
        print(
            "%-33s %8.1f%% %8.1f%% %8.1f%% %6.3f %8.1f%%"
            % (
                nombre,
                metrica["recall@1"]["porcentaje"],
                metrica["recall@3"]["porcentaje"],
                metrica["recall@5"]["porcentaje"],
                metrica["mrr@5"],
                metrica["abstencion"]["porcentaje"],
            )
        )
    print("RESULTADO=%s" % args.output)
    return 0 if errores == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
