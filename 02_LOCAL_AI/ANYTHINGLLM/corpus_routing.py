# -*- coding: utf-8 -*-
"""Enrutamiento suave por corpus y diversidad por ``docSource``.

Esta capa recibe una lista de candidatos semánticos ya ordenada. Devuelve una
permutación de esa misma lista: no filtra candidatos ni consulta o modifica el
índice. El enrutamiento aplica una bonificación de rango según la consulta y la
ruta completa de cada fuente. Después, la diversidad limita la repetición de
una fuente en el tramo que se entregará como top-k.

La propiedad central es comprobable: cada candidato de entrada aparece una y
solo una vez en la salida. Por tanto, una ruta puede bajar o subir de posición,
pero nunca queda excluida por pertenecer a otro corpus.
"""
from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple


RAIZ = Path(__file__).resolve().parent
PERFILES_PREDETERMINADOS = RAIZ / "routing_profiles.json"

RUTA_TCHASKY = "tchasky"
RUTA_PERSONAL = "personal"
RUTA_CIBERSEGURIDAD = "ciberseguridad"
RUTA_FRAMEWORK = "framework"
RUTA_RESTO = "resto"
RUTAS = (
    RUTA_TCHASKY,
    RUTA_PERSONAL,
    RUTA_CIBERSEGURIDAD,
    RUTA_FRAMEWORK,
    RUTA_RESTO,
)

# Los nombres provienen de las rutas del manifiesto de Framework Skills. No se
# agrega metadata a los documentos: se sigue clasificando por docSource.
SLUGS_FRAMEWORK = frozenset(
    {
        "brainstorming",
        "dispatching-parallel-agents",
        "executing-plans",
        "finishing-a-development-branch",
        "receiving-code-review",
        "requesting-code-review",
        "subagent-driven-development",
        "systematic-debugging",
        "test-driven-development",
        "using-git-worktrees",
        "using-superpowers",
        "verification-before-completion",
        "writing-plans",
        "writing-skills",
    }
)


@dataclass(frozen=True)
class SenalRuta:
    termino: str
    peso: float


@dataclass(frozen=True)
class ClasificacionConsulta:
    pesos: Mapping[str, float]
    puntajes: Mapping[str, float]
    coincidencias: Mapping[str, Tuple[str, ...]]


@dataclass(frozen=True)
class TrazaCandidato:
    indice_original: int
    fuente: str
    corpus: str
    rango_original: int
    peso_ruta: float
    rango_ajustado: float


@dataclass(frozen=True)
class ResultadoEnrutamiento:
    seleccion_top_k: List[Mapping[str, Any]]
    candidatos: List[Mapping[str, Any]]
    clasificacion: ClasificacionConsulta
    traza: List[TrazaCandidato]
    top_k_incompleto_por_falta_de_diversidad: bool


def normalizar_ruta(valor: Any) -> str:
    """Conserva la identidad completa y normaliza solo separadores/prefijo."""
    return str(valor or "").strip().replace("\\", "/").lstrip("./")


def _normalizar_texto(valor: Any) -> str:
    texto = unicodedata.normalize("NFKD", str(valor or "").casefold())
    texto = "".join(caracter for caracter in texto if not unicodedata.combining(caracter))
    return " ".join(re.findall(r"[a-z0-9]+", texto))


def fuente_de(candidato: Mapping[str, Any]) -> str:
    """Obtiene docSource de candidatos normalizados o de la respuesta de la API."""
    for clave in ("docSource", "source", "fuente"):
        if candidato.get(clave):
            return normalizar_ruta(candidato[clave])
    metadata = candidato.get("metadata")
    if isinstance(metadata, Mapping):
        return normalizar_ruta(metadata.get("docSource"))
    return ""


def corpus_de_fuente(fuente: Any) -> str:
    """Clasifica una fuente usando únicamente su ruta completa."""
    ruta = normalizar_ruta(fuente).casefold()
    if ruta.startswith("03_tchasky/"):
        return RUTA_TCHASKY
    if ruta.startswith("10_personal/"):
        return RUTA_PERSONAL
    if ruta.startswith("skills/"):
        partes = ruta.split("/")
        if len(partes) > 1 and partes[1] in SLUGS_FRAMEWORK:
            return RUTA_FRAMEWORK
        return RUTA_CIBERSEGURIDAD
    return RUTA_RESTO


def cargar_perfiles(ruta: Path = PERFILES_PREDETERMINADOS) -> Dict[str, Tuple[SenalRuta, ...]]:
    datos = json.loads(Path(ruta).read_text(encoding="utf-8"))
    perfiles_crudos = datos.get("perfiles")
    if not isinstance(perfiles_crudos, dict):
        raise ValueError("routing_profiles.json debe contener un objeto 'perfiles'.")

    perfiles: Dict[str, Tuple[SenalRuta, ...]] = {}
    for corpus in RUTAS:
        entradas = perfiles_crudos.get(corpus, [])
        if not isinstance(entradas, list):
            raise ValueError("El perfil %s debe ser una lista." % corpus)
        senales: List[SenalRuta] = []
        for entrada in entradas:
            if not isinstance(entrada, dict) or not entrada.get("termino"):
                raise ValueError("Señal inválida en el perfil %s." % corpus)
            peso = float(entrada.get("peso", 1.0))
            if peso <= 0:
                raise ValueError("El peso de una señal debe ser positivo.")
            senales.append(SenalRuta(_normalizar_texto(entrada["termino"]), peso))
        perfiles[corpus] = tuple(senales)
    return perfiles


def clasificar_consulta(
    consulta: str,
    perfiles: Optional[Mapping[str, Sequence[SenalRuta]]] = None,
    puntaje_minimo: float = 2.0,
    saturacion: float = 4.0,
) -> ClasificacionConsulta:
    """Calcula pesos blandos por corpus; cero significa orden sin preferencia."""
    if puntaje_minimo < 0:
        raise ValueError("puntaje_minimo no puede ser negativo.")
    if saturacion <= 0:
        raise ValueError("saturacion debe ser mayor que cero.")
    perfiles = perfiles or cargar_perfiles()
    consulta_normalizada = " %s " % _normalizar_texto(consulta)
    puntajes: Dict[str, float] = {corpus: 0.0 for corpus in RUTAS}
    coincidencias: Dict[str, Tuple[str, ...]] = {}

    for corpus in RUTAS:
        encontradas: List[str] = []
        for senal in perfiles.get(corpus, ()):
            if senal.termino and " %s " % senal.termino in consulta_normalizada:
                puntajes[corpus] += senal.peso
                encontradas.append(senal.termino)
        coincidencias[corpus] = tuple(encontradas)

    pesos = {
        corpus: (min(1.0, puntaje / saturacion) if puntaje >= puntaje_minimo else 0.0)
        for corpus, puntaje in puntajes.items()
    }
    return ClasificacionConsulta(pesos, puntajes, coincidencias)


def _clave_documento(candidato: Mapping[str, Any], indice: int) -> str:
    fuente = fuente_de(candidato).casefold()
    # Un candidato sin docSource no debe bloquear a todos los demás candidatos
    # defectuosos como si fueran un mismo documento.
    return fuente if fuente else "__sin_docsource__:%d" % indice


def enrutar_y_diversificar(
    consulta: str,
    candidatos: Sequence[Mapping[str, Any]],
    *,
    top_k: int = 5,
    maximo_por_documento: int = 1,
    bonificacion_rangos: float = 40.0,
    puntaje_minimo: float = 2.0,
    saturacion: float = 4.0,
    perfiles: Optional[Mapping[str, Sequence[SenalRuta]]] = None,
) -> ResultadoEnrutamiento:
    """Reordena sin excluir y limita repeticiones en el primer ``top_k``.

    ``bonificacion_rangos`` es el máximo número de posiciones que puede ganar
    un candidato cuya zona tenga peso 1. Una clasificación débil recibe una
    fracción de esa bonificación. El rango semántico original resuelve empates.

    ``seleccion_top_k`` cumple el límite de forma estricta. Si no existen
    suficientes documentos distintos, contiene menos de ``top_k`` elementos.
    ``candidatos`` conserva además la permutación completa para que ningún
    documento deje de estar disponible para paginación o una selección mayor.
    """
    if top_k < 1:
        raise ValueError("top_k debe ser al menos 1.")
    if maximo_por_documento < 1:
        raise ValueError("maximo_por_documento debe ser al menos 1.")
    if bonificacion_rangos < 0:
        raise ValueError("bonificacion_rangos no puede ser negativa.")

    clasificacion = clasificar_consulta(
        consulta,
        perfiles=perfiles,
        puntaje_minimo=puntaje_minimo,
        saturacion=saturacion,
    )
    anotados = []
    for indice, candidato in enumerate(candidatos):
        fuente = fuente_de(candidato)
        corpus = corpus_de_fuente(fuente)
        peso = float(clasificacion.pesos.get(corpus, 0.0))
        rango = indice + 1
        ajustado = rango - bonificacion_rangos * peso
        anotados.append(
            {
                "indice": indice,
                "candidato": candidato,
                "fuente": fuente,
                "corpus": corpus,
                "rango": rango,
                "peso": peso,
                "ajustado": ajustado,
            }
        )

    enrutados = sorted(anotados, key=lambda item: (item["ajustado"], item["rango"]))
    limite = min(top_k, len(enrutados))
    cabecera = []
    conteo_por_documento: Dict[str, int] = {}
    for item in enrutados:
        if len(cabecera) >= limite:
            break
        clave = _clave_documento(item["candidato"], item["indice"])
        if conteo_por_documento.get(clave, 0) >= maximo_por_documento:
            continue
        cabecera.append(item)
        conteo_por_documento[clave] = conteo_por_documento.get(clave, 0) + 1

    incompleto = len(cabecera) < limite
    elegidos = {item["indice"] for item in cabecera}
    cola = [item for item in enrutados if item["indice"] not in elegidos]
    ordenados = cabecera + cola
    traza = [
        TrazaCandidato(
            indice_original=item["indice"],
            fuente=item["fuente"],
            corpus=item["corpus"],
            rango_original=item["rango"],
            peso_ruta=item["peso"],
            rango_ajustado=item["ajustado"],
        )
        for item in ordenados
    ]
    return ResultadoEnrutamiento(
        seleccion_top_k=[item["candidato"] for item in cabecera],
        candidatos=[item["candidato"] for item in ordenados],
        clasificacion=clasificacion,
        traza=traza,
        top_k_incompleto_por_falta_de_diversidad=incompleto,
    )


def rerank_candidates(
    consulta: str,
    candidatos: Sequence[Mapping[str, Any]],
    **parametros: Any,
) -> List[Mapping[str, Any]]:
    """Atajo para consumidores que no necesitan la traza de diagnóstico."""
    return enrutar_y_diversificar(consulta, candidatos, **parametros).candidatos


def select_top_k(
    consulta: str,
    candidatos: Sequence[Mapping[str, Any]],
    **parametros: Any,
) -> List[Mapping[str, Any]]:
    """Devuelve el top-k que cumple estrictamente el máximo por documento."""
    return enrutar_y_diversificar(consulta, candidatos, **parametros).seleccion_top_k
