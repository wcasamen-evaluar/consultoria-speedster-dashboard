import ast
import json
import unittest
from pathlib import Path

import pandas as pd

from reporte import integrado


class ReportesMetadataEscalasTest(unittest.TestCase):
    def test_pdf_clasifica_decimales_sin_redondearlos(self):
        raiz = Path(__file__).resolve().parents[1]
        ruta_pdf = raiz / "reporte" / "generar_pdf.py"
        arbol = ast.parse(ruta_pdf.read_text(encoding="utf-8-sig"))
        funcion = next(
            nodo
            for nodo in arbol.body
            if isinstance(nodo, ast.FunctionDef)
            and nodo.name == "_cap_interpretacion"
        )
        config = json.loads(
            (raiz / "reporte" / "assets" / "cap.json").read_text(encoding="utf-8")
        )
        espacio = {"_cap_config": lambda: config}
        exec(
            compile(ast.Module(body=[funcion], type_ignores=[]), str(ruta_pdf), "exec"),
            espacio,
        )
        clasificar = espacio["_cap_interpretacion"]

        self.assertEqual(
            clasificar(0.7991)["name"],
            "Potencial bajo",
        )
        self.assertEqual(
            clasificar(0.8000)["name"],
            "Potencial medio",
        )
        self.assertEqual(
            clasificar(0.8500)["name"],
            "Alto potencial",
        )

    def test_metadata_360_solo_completa_personas_sin_potencial(self):
        desempeno = pd.DataFrame(
            {
                "colaborador": ["Sin Potencial", "Con Potencial"],
                "global": [90.0, 91.0],
                "email_colaborador": ["sin@example.com", "con@example.com"],
                "empresa": ["Empresa 360", "Empresa 360"],
                "pais": ["Pais 360", "Pais 360"],
                "area": ["Area 360", "Area 360"],
                "grupo": ["GRUPO 360", "GRUPO 360"],
            }
        )
        objetivos = pd.DataFrame(
            {
                "colaborador": ["Sin Potencial", "Con Potencial"],
                "email_colaborador": ["sin@example.com", "con@example.com"],
                "puntaje": [88.0, 89.0],
                "cargo_objetivo": ["Cargo", "Cargo"],
                "jefe": ["Jefe", "Jefe"],
            }
        )
        potencial = pd.DataFrame(
            {
                "colaborador": ["Con Potencial"],
                "correo": ["con@example.com"],
                "correo_potencial": ["con@example.com"],
                "correo_instancia": ["con@example.com"],
                "evaluacion_potencial": [90.0],
                "empresa": ["Empresa Potencial"],
                "pais": ["Pais Potencial"],
                "area": ["Area Potencial"],
                "grupo": ["GRUPO POTENCIAL"],
                "cargo": ["Cargo Potencial"],
            }
        )
        fuente_objetivos = pd.DataFrame(columns=["nombre_evaluador"])

        resultado = integrado.preparar_resultado_integrado(
            desempeno,
            objetivos,
            potencial,
            fuente_objetivos,
        ).set_index("colaborador")

        self.assertEqual(resultado.loc["Sin Potencial", "empresa"], "Empresa 360")
        self.assertEqual(resultado.loc["Sin Potencial", "grupo"], "GRUPO 360")
        self.assertEqual(
            resultado.loc["Con Potencial", "empresa"],
            "Empresa Potencial",
        )
        self.assertEqual(
            resultado.loc["Con Potencial", "grupo"],
            "GRUPO POTENCIAL",
        )

    def test_pdf_prioriza_puntaje_oficial_de_competencias(self):
        cap_recalculado = {"percent": 84.60, "score": 0.846}
        potencial = {"evaluacion_potencial": 84.41}

        cap_oficial = integrado._cap_con_puntaje_oficial(
            cap_recalculado,
            potencial,
        )

        self.assertEqual(cap_oficial["percent"], 84.41)
        self.assertEqual(cap_oficial["score"], 0.8441)

    def test_pdf_conserva_el_corte_superior_de_competencias(self):
        cap_oficial = integrado._cap_con_puntaje_oficial(
            {"percent": 84.40},
            {"evaluacion_potencial": 84.51},
        )

        self.assertEqual(cap_oficial["percent"], 84.51)
        self.assertEqual(cap_oficial["score"], 0.8451)


if __name__ == "__main__":
    unittest.main()
