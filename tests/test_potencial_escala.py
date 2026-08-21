import ast
import json
import unittest
from pathlib import Path

import pandas as pd

from reporte import potencial


class EscalaPotencialTest(unittest.TestCase):
    def test_redondea_antes_de_clasificar_con_cortes_80_y_85(self):
        casos = {
            57.05: "Potencial Bajo",
            79.49: "Potencial Bajo",
            79.50: "Potencial Medio",
            84.49: "Potencial Medio",
            84.50: "Potencial Medio",
            84.51: "Potencial Alto",
            100: "Potencial Alto",
        }

        for puntaje, etiqueta in casos.items():
            with self.subTest(puntaje=puntaje):
                self.assertEqual(
                    potencial.clasificar_nivel_potencial(puntaje),
                    etiqueta,
                )

    def test_dashboard_y_motor_comparten_los_mismos_limites(self):
        ruta = Path(__file__).resolve().parents[1] / "dashboard_360.py"
        arbol = ast.parse(ruta.read_text(encoding="utf-8-sig"))
        limites_dashboard = None
        for nodo in arbol.body:
            if not isinstance(nodo, ast.Assign):
                continue
            if any(
                isinstance(destino, ast.Name) and destino.id == "POTENCIAL_LIMITES"
                for destino in nodo.targets
            ):
                limites_dashboard = ast.literal_eval(nodo.value)
                break

        self.assertEqual(limites_dashboard, potencial.LIMITES_NIVEL_POTENCIAL)

    def test_pdf_usa_los_mismos_limites(self):
        ruta = (
            Path(__file__).resolve().parents[1]
            / "reporte"
            / "assets"
            / "cap.json"
        )
        config = json.loads(ruta.read_text(encoding="utf-8"))
        rangos = [(item["from"], item["to"]) for item in config["ranges"]]

        self.assertEqual(rangos, [(0, 80), (80, 85), (85, 101)])

    def test_niveles_de_competencias_usan_los_nombres_del_reporte(self):
        casos = {
            79.49: "Alejado del perfil",
            79.50: "Cercano al Perfil",
            84.50: "Cercano al Perfil",
            84.51: "Ajuste al perfil",
        }

        for puntaje, etiqueta in casos.items():
            with self.subTest(puntaje=puntaje):
                self.assertEqual(
                    potencial.clasificar_nivel_competencias(puntaje),
                    etiqueta,
                )

        self.assertEqual(
            potencial.RANGOS_NIVELES_COMPETENCIAS,
            {
                "Alejado del perfil": "0 - 79",
                "Cercano al Perfil": "80 - 84",
                "Ajuste al perfil": "85 - 100",
            },
        )

    def test_valores_muestra_solo_competencias_con_evaluacion(self):
        datos = pd.DataFrame(
            {
                "competencia": ["Integridad", "Integridad", "Creatividad"],
                "ajuste": [0.90, 0.80, None],
            }
        )

        resultado = potencial.resumir_competencias_evaluadas(
            datos,
            ["Creatividad", "Integridad", "Competencia sin evaluar"],
        )

        self.assertEqual(resultado["competencia"].tolist(), ["Integridad"])
        self.assertAlmostEqual(resultado.iloc[0]["puntaje"], 85.0)

    def test_valores_incluye_competencias_nuevas_evaluadas(self):
        datos = pd.DataFrame(
            {
                "competencia": ["Competencia nueva", "Integridad"],
                "ajuste": [0.75, 0.90],
            }
        )

        resultado = potencial.resumir_competencias_evaluadas(
            datos,
            ["Integridad"],
        )

        self.assertEqual(
            resultado["competencia"].tolist(),
            ["Integridad", "Competencia nueva"],
        )

    def test_valores_se_ordenan_de_mayor_a_menor_promedio(self):
        datos = pd.DataFrame(
            {
                "competencia": ["Creatividad", "Integridad", "Proactividad"],
                "ajuste": [0.75, 0.98, 0.86],
            }
        )

        resultado = potencial.resumir_competencias_evaluadas(datos)

        self.assertEqual(
            resultado["competencia"].tolist(),
            ["Integridad", "Proactividad", "Creatividad"],
        )
        self.assertEqual(resultado["puntaje"].tolist(), [98.0, 86.0, 75.0])


if __name__ == "__main__":
    unittest.main()
