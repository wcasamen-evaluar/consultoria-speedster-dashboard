import ast
import unittest
from pathlib import Path

import pandas as pd

from reporte import calculos, objetivos, potencial


ROOT = Path(__file__).resolve().parents[1]
EXCEL = ROOT / "Fase_I_Evaluación_360__180__90__copia_.xlsx"


class MetadataSpeedsterTest(unittest.TestCase):
    def test_lee_la_base_organizacional_y_fija_empresa(self):
        metadata = calculos.leer_metadata_organizacional(EXCEL)

        self.assertEqual(len(metadata), 36)
        self.assertEqual(set(metadata["empresa"]), {"Speedster"})
        for columna in ["pais", "area", "cargo", "grupo"]:
            self.assertTrue(metadata[columna].notna().all(), columna)

    def test_completa_indhira_aunque_el_nombre_tenga_un_componente_extra(self):
        metadata = calculos.leer_metadata_organizacional(EXCEL)
        datos = pd.DataFrame(
            [{
                "colaborador": "Mendoza Coste Indhira Severiana",
                "correo": pd.NA,
            }]
        )

        resultado = calculos.completar_metadata_colaboradores(
            datos,
            metadata,
            "colaborador",
            "correo",
        ).iloc[0]

        self.assertEqual(resultado["correo"], "imendoza@speedster.com.do")
        self.assertEqual(resultado["empresa"], "Speedster")
        self.assertEqual(resultado["pais"], "República Dominicana")
        self.assertTrue(str(resultado["area"]).strip())
        self.assertTrue(str(resultado["grupo"]).strip())

    def test_indice_real_tiene_cobertura_total_de_los_filtros(self):
        df_360 = calculos.leer_exportacion_dashboard(EXCEL)
        metadata = calculos.leer_metadata_organizacional(EXCEL)
        df_360 = calculos.completar_metadata_colaboradores(
            df_360,
            metadata,
            "nombre_colaborador",
            "email_colaborador",
        )
        df_calculo = calculos.filtrar_excluidos_desempeno(df_360)
        res_360 = calculos.calcular_dashboard(df_calculo, calculos.PESOS_BASE)
        res_360["df_global"] = calculos.completar_metadata_colaboradores(
            res_360["df_global"],
            metadata,
            "colaborador",
            "email_colaborador",
        )
        res_360["df_metadata"] = metadata
        res_potencial = potencial.leer_potencial(EXCEL)
        res_potencial["df_personas"] = calculos.completar_metadata_colaboradores(
            res_potencial["df_personas"],
            metadata,
            "colaborador",
            "correo",
        )
        res_objetivos = objetivos.leer_objetivos(EXCEL)

        ruta_dashboard = ROOT / "dashboard_360.py"
        arbol = ast.parse(ruta_dashboard.read_text(encoding="utf-8-sig"))
        requeridas = {
            "normalizar_nombre_match",
            "normalizar_correo",
            "valor_limpio",
            "construir_indice_colaboradores",
        }
        funciones = [
            nodo
            for nodo in arbol.body
            if isinstance(nodo, ast.FunctionDef) and nodo.name in requeridas
        ]
        espacio = {
            "pd": pd,
            "motor_360": calculos,
            "reparar_texto": lambda valor: str(valor).strip(),
        }
        exec(
            compile(ast.Module(body=funciones, type_ignores=[]), str(ruta_dashboard), "exec"),
            espacio,
        )
        indice = espacio["construir_indice_colaboradores"](
            res_360,
            res_potencial,
            res_objetivos,
        )

        self.assertEqual(len(indice), 35)
        for columna in ["empresa", "pais", "area", "grupo"]:
            cobertura = indice[columna].fillna("").astype(str).str.strip().ne("")
            self.assertTrue(cobertura.all(), columna)
        self.assertEqual(set(indice["empresa"]), {"Speedster"})


if __name__ == "__main__":
    unittest.main()
