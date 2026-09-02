import tempfile
import unittest
from pathlib import Path

import pandas as pd
from openpyxl import Workbook

from reporte import calculos, integrado, potencial


class PotencialFormatosTest(unittest.TestCase):
    def _guardar(self, filas: list[list[object]]) -> Path:
        carpeta = tempfile.TemporaryDirectory()
        self.addCleanup(carpeta.cleanup)
        ruta = Path(carpeta.name) / "potencial.xlsx"
        libro = Workbook()
        hoja = libro.active
        hoja.title = "Potencial"
        for fila in filas:
            hoja.append(fila)
        libro.save(ruta)
        return ruta

    def test_lee_formato_historico_macrotech(self):
        grupos = [None] * 28
        grupos[13:17] = ["Autocontrol"] * 4
        grupos[17:21] = ["Iniciativa"] * 4
        grupos[21] = "IQ"
        grupos[22:28] = ["Disc"] * 6

        encabezados = [
            "Correo", "NOMBRE COMPLETO", "No. Identificación", "Empresa",
            "Cargo", "Jefe", "País", "Área", "Grupo", "Potencial 2025",
            "Evaluación de Potencial", "Escala Benchmark externo",
            "Escala Potencial", "Valor", "Esperado", "Brecha", "Autocontrol",
            "Valor2", "Esperado2", "Brecha2", "Iniciativa", None,
            "Arquetipo", "Intensidad", "D", "I", "S", "C",
        ]
        datos = [
            "ana@example.com", "Ana Pérez", "1", "Macrotech", "Analista",
            "Jefe Uno", "DO", "Operaciones", "A", 90, 91,
            "Ajustado al perfil", "Ajustado al perfil", 8, 9, -1, 0.89,
            7, 8, -1, 0.88, "Medio (100)", "Analítico (C)", 7, 2, 3, 4, 9,
        ]
        ruta = self._guardar([[None] * 28, grupos, encabezados, datos])

        resultado = potencial.leer_potencial(ruta)

        self.assertEqual(resultado["resumen"]["personas"], 1)
        self.assertEqual(resultado["catalogo_competencias"], ["Autocontrol", "Iniciativa"])
        self.assertEqual(len(resultado["df_competencias"]), 2)
        self.assertEqual(resultado["df_personas"].iloc[0]["colaborador"], "Ana Pérez")
        self.assertEqual(resultado["df_personas"].iloc[0]["arquetipo"], "C")
        self.assertEqual(resultado["df_personas"].iloc[0]["escala_benchmark"], "Alto potencial")
        self.assertEqual(resultado["df_personas"].iloc[0]["escala_potencial"], "Alto potencial")

    def test_lee_formato_speedster_y_prioriza_nombres_apellidos(self):
        grupos = [None] * 32
        grupos[20:24] = ["Autocontrol"] * 4
        grupos[24] = "Detalles del candidato"
        grupos[25] = "IQ"
        grupos[26:32] = ["Disc"] * 6

        encabezados = [
            "Ranking", "CAP", "COMPETENCIAS", "Nombres", "Apellidos",
            "Nombre del Proceso", "Nombre del Perfil", "Inicio", "Fin",
            "Reclutador", "No. Identificación", "Estado", "Origen",
            "Agregado al proceso por", "Contratado el", "Etiquetas",
            "Fecha de Ingreso a Proceso", "Fecha de Finalización de Proceso",
            "Discapacidad", "Reubicación laboral", "Valor", "Esperado",
            "Brecha", "Cumplimiento", None, None, "Arquetipo", "Intensidad",
            "D", "I", "S", "C",
        ]
        datos = [
            1, 91, 91, "Ana María", "Pérez", "Speedster 2026",
            "Gerencia Comercial", None, None, None, "2", "Finalizado", None,
            None, None, None, None, None, None, None, 8, 9, -1, 0.89,
            "detalle", "Medio (100)", "Analítico (C)", 7, 2, 3, 4, 9,
        ]
        ruta = self._guardar([grupos, encabezados, datos])

        resultado = potencial.leer_potencial(ruta)
        persona = resultado["df_personas"].iloc[0]
        competencia = resultado["df_competencias"].iloc[0]

        self.assertEqual(persona["colaborador"], "Ana María Pérez")
        self.assertEqual(persona["cargo"], "Gerencia Comercial")
        self.assertEqual(persona["evaluacion_potencial"], 91)
        self.assertEqual(persona["escala_benchmark"], "Alto potencial")
        self.assertEqual(persona["escala_potencial"], "Alto potencial")
        self.assertEqual(persona["arquetipo"], "C")
        self.assertEqual(resultado["catalogo_competencias"], ["Autocontrol"])
        self.assertAlmostEqual(competencia["ajuste"], 0.89)

    def test_empareja_nombres_aunque_lleguen_en_orden_inverso(self):
        self.assertEqual(
            integrado.normalizar_nombre_match("Ana María Pérez Soto"),
            integrado.normalizar_nombre_match("Pérez Soto Ana María"),
        )

    def test_empareja_un_segundo_nombre_adicional_si_la_coincidencia_es_unica(self):
        self.assertEqual(
            calculos.resolver_nombre_equivalente_unico(
                "Indhira Mendoza Coste",
                ["Mendoza Coste Indhira Severiana"],
            ),
            calculos.normalizar_nombre_persona("Mendoza Coste Indhira Severiana"),
        )
        self.assertEqual(
            calculos.resolver_nombre_equivalente_unico(
                "Ana María Pérez",
                ["Ana María Pérez Soto", "Ana María Pérez Ruiz"],
            ),
            "",
        )

    def test_unifica_indhira_en_integrado_y_ninebox(self):
        df_360 = pd.DataFrame(
            [{
                "colaborador": "Indhira Mendoza Coste",
                "global": 81.75,
                "email_colaborador": "imendoza@speedster.com.do",
            }]
        )
        df_objetivos = pd.DataFrame(
            [{
                "colaborador": "Indhira Mendoza Coste",
                "email_colaborador": "imendoza@speedster.com.do",
                "puntaje": 84.0,
            }]
        )
        df_potencial = pd.DataFrame(
            [{
                "colaborador": "Mendoza Coste Indhira Severiana",
                "evaluacion_potencial": 79.91,
            }]
        )

        resultado = integrado.preparar_resultado_integrado(
            df_360,
            df_objetivos,
            df_potencial,
            pd.DataFrame(),
        )
        ninebox = integrado.preparar_ninebox(df_360, df_potencial)

        self.assertEqual(len(resultado), 1)
        self.assertEqual(resultado.iloc[0]["colaborador"], "Indhira Mendoza Coste")
        self.assertEqual(resultado.iloc[0]["potencial"], 79.91)
        self.assertEqual(resultado.iloc[0]["etiqueta_integrada"], "Completa")
        self.assertEqual(len(ninebox), 1)
        self.assertEqual(ninebox.iloc[0]["colaborador"], "Indhira Mendoza Coste")


if __name__ == "__main__":
    unittest.main()
