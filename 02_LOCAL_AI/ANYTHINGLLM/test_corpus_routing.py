# -*- coding: utf-8 -*-
"""Pruebas sintéticas de TASK-112; no acceden a AnythingLLM ni a LanceDB."""
import unittest

from corpus_routing import (
    RUTA_CIBERSEGURIDAD,
    RUTA_FRAMEWORK,
    RUTA_PERSONAL,
    RUTA_RESTO,
    RUTA_TCHASKY,
    clasificar_consulta,
    corpus_de_fuente,
    enrutar_y_diversificar,
    fuente_de,
)


def candidato(identificador, fuente):
    return {
        "id_prueba": identificador,
        "text": "fragmento sintético %s" % identificador,
        "metadata": {"docSource": fuente},
    }


class ClasificacionDeRutasTest(unittest.TestCase):
    def test_clasifica_solo_por_docsource_completo(self):
        casos = {
            "03_Tchasky/OPS/RUNBOOK.md": RUTA_TCHASKY,
            r"10_Personal\MODELO_PERSONAL\nota.md": RUTA_PERSONAL,
            "skills/analyzing-memory-dumps-with-volatility/SKILL.md": RUTA_CIBERSEGURIDAD,
            "skills/systematic-debugging/SKILL.md": RUTA_FRAMEWORK,
            "06_CONVERSACIONES_CLAUDE_EXPORT/nota.md": RUTA_RESTO,
        }
        for ruta, esperado in casos.items():
            with self.subTest(ruta=ruta):
                self.assertEqual(corpus_de_fuente(ruta), esperado)

    def test_consulta_puede_priorizar_mas_de_un_corpus(self):
        clasificacion = clasificar_consulta(
            "Antes de afirmar que las pruebas pasan, revisa el SBOM y una dependencia vulnerable."
        )
        self.assertGreater(clasificacion.pesos[RUTA_FRAMEWORK], 0)
        self.assertGreater(clasificacion.pesos[RUTA_CIBERSEGURIDAD], 0)

    def test_consulta_sin_senal_no_inventa_una_ruta(self):
        clasificacion = clasificar_consulta("¿Dónde está la información que necesito?")
        self.assertTrue(all(peso == 0 for peso in clasificacion.pesos.values()))


class EnrutamientoNoExcluyenteTest(unittest.TestCase):
    def test_promueve_la_zona_indicada_por_la_consulta(self):
        entrada = [
            candidato("t1", "03_Tchasky/arquitectura.md"),
            candidato("o1", "notas/generales.md"),
            candidato("p1", "10_Personal/Perfil_Entrenamiento_Nutricion.md"),
        ]
        resultado = enrutar_y_diversificar(
            "¿Qué calorías requiere el entrenamiento?",
            entrada,
            top_k=3,
            maximo_por_documento=1,
            bonificacion_rangos=40,
        )
        self.assertEqual(resultado.candidatos[0]["id_prueba"], "p1")

    def test_todos_los_candidatos_siguen_alcanzables(self):
        entrada = [
            candidato("t1", "03_Tchasky/a.md"),
            candidato("p1", "10_Personal/b.md"),
            candidato("c1", "skills/analyzing-memory-dumps-with-volatility/SKILL.md"),
            candidato("f1", "skills/systematic-debugging/SKILL.md"),
            candidato("o1", "conversaciones/e.md"),
        ]
        resultado = enrutar_y_diversificar(
            "Necesito usar Volatility con una captura de memoria RAM.",
            entrada,
            top_k=3,
            maximo_por_documento=1,
        )
        self.assertEqual(len(resultado.candidatos), len(entrada))
        self.assertEqual(
            {id(item) for item in resultado.candidatos},
            {id(item) for item in entrada},
        )
        self.assertEqual(
            sorted(item["id_prueba"] for item in resultado.candidatos),
            sorted(item["id_prueba"] for item in entrada),
        )

    def test_bonificacion_cero_conserva_el_orden_semantico_antes_de_diversidad(self):
        entrada = [
            candidato("a", "03_Tchasky/a.md"),
            candidato("b", "10_Personal/b.md"),
            candidato("c", "skills/systematic-debugging/SKILL.md"),
        ]
        resultado = enrutar_y_diversificar(
            "Volatility",
            entrada,
            top_k=3,
            maximo_por_documento=1,
            bonificacion_rangos=0,
        )
        self.assertEqual([c["id_prueba"] for c in resultado.candidatos], ["a", "b", "c"])


class DiversidadDocumentalTest(unittest.TestCase):
    def test_un_documento_no_copa_el_top_k_si_hay_alternativas(self):
        entrada = [
            candidato("a1", "03_Tchasky/a.md"),
            candidato("a2", "03_Tchasky/a.md"),
            candidato("a3", "03_Tchasky/a.md"),
            candidato("b1", "03_Tchasky/b.md"),
            candidato("c1", "03_Tchasky/c.md"),
            candidato("d1", "03_Tchasky/d.md"),
            candidato("e1", "03_Tchasky/e.md"),
        ]
        resultado = enrutar_y_diversificar(
            "consulta neutra",
            entrada,
            top_k=5,
            maximo_por_documento=1,
            bonificacion_rangos=0,
        )
        fuentes_top = [fuente_de(item) for item in resultado.seleccion_top_k]
        self.assertEqual(len(fuentes_top), len(set(fuentes_top)))
        self.assertEqual([c["id_prueba"] for c in resultado.seleccion_top_k], ["a1", "b1", "c1", "d1", "e1"])
        self.assertEqual(len(resultado.candidatos), len(entrada))

    def test_no_rompe_el_limite_si_faltan_documentos_distintos(self):
        entrada = [
            candidato("a1", "03_Tchasky/a.md"),
            candidato("a2", "03_Tchasky/a.md"),
            candidato("b1", "03_Tchasky/b.md"),
        ]
        resultado = enrutar_y_diversificar(
            "consulta neutra",
            entrada,
            top_k=3,
            maximo_por_documento=1,
            bonificacion_rangos=0,
        )
        self.assertEqual(len(resultado.seleccion_top_k), 2)
        self.assertEqual(len(resultado.candidatos), 3)
        self.assertTrue(resultado.top_k_incompleto_por_falta_de_diversidad)

    def test_candidatos_sin_docsource_no_se_colapsan_entre_si(self):
        entrada = [
            {"id_prueba": "x1", "metadata": {}},
            {"id_prueba": "x2", "metadata": {}},
            candidato("a1", "03_Tchasky/a.md"),
        ]
        resultado = enrutar_y_diversificar(
            "consulta neutra",
            entrada,
            top_k=3,
            maximo_por_documento=1,
            bonificacion_rangos=0,
        )
        self.assertFalse(resultado.top_k_incompleto_por_falta_de_diversidad)
        self.assertEqual(len(resultado.seleccion_top_k), 3)
        self.assertEqual(len(resultado.candidatos), 3)


if __name__ == "__main__":
    unittest.main()
