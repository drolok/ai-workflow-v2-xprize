# -*- coding: utf-8 -*-
"""Mide la calidad de RECUPERACION del RAG contra un conjunto de referencia.

Que mide y que NO
-----------------
Mide si el documento correcto aparece entre los primeros k resultados. Eso es lo
que determina si el modelo puede responder: si el documento no se recupera, no
hay generacion que lo arregle.

NO mide la calidad de la redaccion de la respuesta. Eso exige un juez LLM, y con
un modelo local que tarda minutos por respuesta sale caro y ruidoso. Umbral para
agregarlo: cuando el RAG se use para responderle a un usuario final y no solo
para que una sesion encuentre en que archivo esta algo.

Las metricas
------------
- recall@k : en que porcentaje de preguntas el documento correcto aparece entre
             los k primeros. Es la metrica que importa.
- MRR      : promedio de 1/posicion del acierto. Distingue "salio primero" de
             "salio quinto", que recall@5 trata igual.
- abstencion: en consultas marcadas sin_respuesta, no devolver ningun documento.
- exactitud global@k: aciertos de recuperacion mas abstenciones correctas sobre
                      el conjunto completo.

Nunca imprime la clave de la API.
"""
import json
import os
import shutil
import sqlite3
import sys
import time
import urllib.request

RAIZ = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(RAIZ, "storage", "anythingllm.db")
GOLDEN = os.path.join(RAIZ, "rag_golden_set.json")
BASE = "http://127.0.0.1:3110"
TOP_N = 5
CANDIDATOS_INICIALES = 100
CANDIDATOS_MAXIMOS = 1600
POLITICA_TASK111 = os.path.join(RAIZ, "task111_artifact_sources.json")

RESPALDO = "03_Tchasky/BANCO_PREGUNTAS_ESTADO.backup_20260721_003533.md"
FUENTES_DUPLICADAS = {
    "03_Tchasky/docs/adr/0001-worktree-isolation-para-paralelismo.md",
    "03_Tchasky/docs/adr/0002-cola-premoderacion-comentarios-resena.md",
    "03_Tchasky/docs/adr/0003-deteccion-soft-pago-fuera-plataforma.md",
}

with open(POLITICA_TASK111, encoding="utf-8") as archivo_politica:
    FUENTES_ARTEFACTO_TASK111 = {
        str(fuente).strip().replace("\\", "/").lstrip("./").casefold()
        for fuente in json.load(archivo_politica)["artifact_sources"]
    }

ESCENARIOS = (
    ("control", False, False, False, False),
    ("sin lote_*", True, False, False, False),
    ("sin lote_*, respaldo y duplicados", True, True, True, False),
    ("sin ARTEFACTO TASK-111", False, False, False, True),
)


def credenciales():
    tmp = os.path.join(os.environ.get("TEMP", "/tmp"), "_eval_allm.db")
    shutil.copy(DB, tmp)  # copia: no se toca la base que usa el contenedor
    con = sqlite3.connect(tmp)
    tabla = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")
             if "api_key" in r[0].lower()]
    if not tabla:
        sys.exit("No se encontro la tabla de claves de API.")
    clave = con.execute("SELECT secret FROM %s LIMIT 1" % tabla[0]).fetchone()[0]
    return clave


def normalizar_ruta(valor):
    """Normaliza separadores sin perder la identidad completa de la fuente."""
    return str(valor or "").strip().replace("\\", "/").lstrip("./")


def buscar(clave, espacio, pregunta, top_n):
    req = urllib.request.Request(
        "%s/api/v1/workspace/%s/vector-search" % (BASE, espacio),
        data=json.dumps({"query": pregunta, "topN": top_n}).encode("utf-8"),
        headers={"Authorization": "Bearer %s" % clave, "Content-Type": "application/json"},
    )
    datos = json.loads(urllib.request.urlopen(req, timeout=120).read())
    resultados = []
    for r in datos.get("results", []):
        meta = r.get("metadata") or {}
        resultados.append({
            "fuente": normalizar_ruta(meta.get("docSource")),
            "texto": str(r.get("text") or ""),
        })
    return resultados


def es_lote(fuente):
    nombre = fuente.rsplit("/", 1)[-1].casefold()
    return nombre.startswith("lote_")


def filtrar(
    resultados,
    quitar_lotes,
    quitar_respaldo,
    quitar_duplicados,
    quitar_artefactos,
):
    """Aplica el contrafactual y devuelve los cinco primeros elegibles."""
    elegibles = []
    duplicados_vistos = set()
    fuentes_duplicadas = {normalizar_ruta(f).casefold() for f in FUENTES_DUPLICADAS}
    respaldo = normalizar_ruta(RESPALDO).casefold()

    for resultado in resultados:
        fuente = resultado["fuente"]
        fuente_comparable = fuente.casefold()
        if quitar_lotes and es_lote(fuente):
            continue
        if quitar_respaldo and fuente_comparable == respaldo:
            continue
        if quitar_artefactos and fuente_comparable in FUENTES_ARTEFACTO_TASK111:
            continue
        if quitar_duplicados and fuente_comparable in fuentes_duplicadas:
            clave_duplicado = (fuente_comparable, resultado["texto"])
            if clave_duplicado in duplicados_vistos:
                continue
            duplicados_vistos.add(clave_duplicado)
        elegibles.append(resultado)
        if len(elegibles) == TOP_N:
            break
    return elegibles


def preparar_escenarios(clave, espacio, pregunta):
    """Amplia la busqueda si un filtro no deja cinco candidatos medibles."""
    top_n = CANDIDATOS_INICIALES
    while True:
        resultados = buscar(clave, espacio, pregunta, top_n)
        preparados = {
            nombre: filtrar(resultados, lotes, respaldo, duplicados, artefactos)
            for nombre, lotes, respaldo, duplicados, artefactos in ESCENARIOS
        }
        if all(len(r) >= TOP_N for r in preparados.values()):
            return preparados
        if len(resultados) < top_n or top_n >= CANDIDATOS_MAXIMOS:
            # Si el endpoint agotó candidatos por debajo de su umbral, devolver
            # los que existan. Tener menos de cinco es un resultado medible, no
            # un error de infraestructura.
            return preparados
        top_n = min(top_n * 2, CANDIDATOS_MAXIMOS)


def main():
    cfg = json.load(open(GOLDEN, encoding="utf-8"))
    espacio = cfg["_espacio"]
    preguntas = cfg["preguntas"]
    clave = credenciales()

    posiciones = {nombre: [] for nombre, *_ in ESCENARIOS}
    abstenciones = {nombre: [] for nombre, *_ in ESCENARIOS}
    errores = {nombre: [] for nombre, *_ in ESCENARIOS}
    print("La identidad se compara por metadata.docSource completo.")
    print(
        "TASK-111 simula la exclusión de %d fuentes clasificadas ARTEFACTO."
        % len(FUENTES_ARTEFACTO_TASK111)
    )
    for numero, caso in enumerate(preguntas, 1):
        sin_respuesta = bool(caso.get("sin_respuesta", False))
        esperado_crudo = caso.get("esperado")
        if sin_respuesta != (esperado_crudo is None):
            sys.exit("Caso sin respuesta incoherente en pregunta %d." % numero)
        esperado = normalizar_ruta(esperado_crudo)
        if not sin_respuesta and "/" not in esperado:
            sys.exit("La fuente esperada no es una ruta completa: %s" % esperado_crudo)
        try:
            t0 = time.time()
            resultados = preparar_escenarios(clave, espacio, caso["pregunta"])
            tardanza = time.time() - t0
        except Exception as exc:                      # red caida, embebedor caido
            print("\n%02d. %s" % (numero, caso["pregunta"]))
            print("    ERROR: %s" % exc)
            for nombre in posiciones:
                posiciones[nombre].append(None)
                abstenciones[nombre].append(None)
                errores[nombre].append(True)
            continue

        print("\n%02d. %s" % (numero, caso["pregunta"]))
        print("    Esperado: %s" % (esperado if esperado else "SIN RESPUESTA"))
        for nombre, *_ in ESCENARIOS:
            candidatos = resultados[nombre]
            ganador = candidatos[0]["fuente"] if candidatos else "sin resultados"
            if sin_respuesta:
                abstuvo = not candidatos
                posiciones[nombre].append(None)
                abstenciones[nombre].append(abstuvo)
                errores[nombre].append(False)
                print("    %-34s abstencion=%s | ganador=%s" %
                      (nombre, "SI" if abstuvo else "NO", ganador))
            else:
                pos = next(
                    (i for i, r in enumerate(candidatos, 1)
                     if r["fuente"].casefold() == esperado.casefold()),
                    None,
                )
                posiciones[nombre].append(pos)
                abstenciones[nombre].append(None)
                errores[nombre].append(False)
                print("    %-34s pos=%s | ganador=%s" % (nombre, pos or "-", ganador))
        print("    Tiempo de consulta: %.1fs" % tardanza)

    total = len(preguntas)
    respondibles = len([p for p in preguntas if not p.get("sin_respuesta", False)])
    negativas = total - respondibles
    print("\n" + "-" * 142)
    print("ESCENARIO".ljust(38), "RECALL@1", "RECALL@3", "RECALL@5", "MRR",
          "ABSTENCION", "EXACTITUD@5")
    print("-" * 142)
    for nombre, *_ in ESCENARIOS:
        validas = [p for p in posiciones[nombre] if p is not None]
        recalls = []
        for k in (1, 3, 5):
            aciertos = len([p for p in validas if p <= k])
            recalls.append("%5.1f%% (%d/%d)" %
                           (100.0 * aciertos / respondibles, aciertos, respondibles))
        abstenciones_correctas = len([a for a in abstenciones[nombre] if a is True])
        aciertos_cinco = len([p for p in validas if p <= 5])
        exactitud = ((aciertos_cinco + abstenciones_correctas) / total
                     if total else 0.0)
        mrr = sum(1.0 / p for p in validas) / respondibles if respondibles else 0.0
        texto_abstencion = ("%5.1f%% (%d/%d)" %
                            (100.0 * abstenciones_correctas / negativas,
                             abstenciones_correctas, negativas)
                            if negativas else "n/a")
        print(nombre.ljust(38), recalls[0].ljust(15), recalls[1].ljust(15),
              recalls[2].ljust(15), ("%5.3f" % mrr).ljust(7),
              texto_abstencion.ljust(15), "%5.1f%% (%d/%d)" %
              (100.0 * exactitud, aciertos_cinco + abstenciones_correctas, total))
        fallos_tecnicos = len([e for e in errores[nombre] if e])
        if fallos_tecnicos:
            print("  ADVERTENCIA: %d consultas tuvieron error técnico." % fallos_tecnicos)
    print("\nLeer esto asi: recall@5 bajo = el documento no se recupera y no hay")
    print("generacion que lo arregle. recall@5 alto con MRR bajo = se recupera")
    print("pero mal rankeado, y compite con ruido por el contexto. Abstencion baja")
    print("= el buscador atribuye relevancia incluso cuando el corpus no responde.")


if __name__ == "__main__":
    main()
