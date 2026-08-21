import ast
import unittest
from pathlib import Path

import pandas as pd

from reporte import calculos
from reporte import integrado


class NineboxLabelsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ruta = Path(__file__).resolve().parents[1] / "dashboard_360.py"
        arbol = ast.parse(ruta.read_text(encoding="utf-8-sig"))
        funciones = [
            nodo
            for nodo in arbol.body
            if isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef))
            and nodo.name == "filtrar_ninebox_general"
        ]
        modulo = ast.Module(body=funciones, type_ignores=[])
        espacio = {"pd": pd}
        exec(compile(modulo, str(ruta), "exec"), espacio)
        cls.filtrar_ninebox_general = staticmethod(
            espacio["filtrar_ninebox_general"]
        )

    def test_los_nombres_corresponden_a_las_nueve_posiciones(self):
        esperados = {
            1: "Super Estrella",
            2: "Estrella del futuro",
            3: "Enigma",
            4: "Estrella en su área",
            5: "Colaborador clave",
            6: "Dilema",
            7: "Comprometido",
            8: "Eficaz",
            9: "Bajo rendimiento",
        }
        self.assertEqual(integrado.NINEBOX_LABELS, esperados)

    def test_dashboard_y_reporte_comparten_los_mismos_nombres(self):
        ruta = Path(__file__).resolve().parents[1] / "dashboard_360.py"
        arbol = ast.parse(ruta.read_text(encoding="utf-8-sig"))
        etiquetas_dashboard = None
        for nodo in arbol.body:
            if not isinstance(nodo, ast.Assign):
                continue
            if any(
                isinstance(destino, ast.Name) and destino.id == "NINEBOX_LABELS"
                for destino in nodo.targets
            ):
                etiquetas_dashboard = ast.literal_eval(nodo.value)
                break

        self.assertEqual(etiquetas_dashboard, integrado.NINEBOX_LABELS)

    def test_el_encabezado_de_cargos_se_reemplazo_por_ranking(self):
        ruta = Path(__file__).resolve().parents[1] / "dashboard_360.py"
        contenido = ruta.read_text(encoding="utf-8-sig")
        self.assertIn('st.markdown("**Ranking**")', contenido)
        self.assertNotIn("Cargos con mejor cumplimiento", contenido)

    def test_los_ejes_ninebox_usan_competencias_y_desempeno(self):
        ruta = Path(__file__).resolve().parents[1] / "dashboard_360.py"
        contenido = ruta.read_text(encoding="utf-8-sig")
        self.assertIn('title=dict(text="Competencias"', contenido)
        self.assertIn('title=dict(text="Desempeño"', contenido)
        self.assertNotIn('title=dict(text="Potencial"', contenido)
        self.assertNotIn('title=dict(text="Desempeño 360"', contenido)

    def test_los_colores_coinciden_con_la_matriz_de_referencia(self):
        esperados = {
            1: "#4EA72F",
            2: "#C5E0B3",
            3: "#EAEAEA",
            4: "#528139",
            5: "#FFC000",
            6: "#FF99FF",
            7: "#0071C0",
            8: "#9F2522",
            9: "#FE0000",
        }
        ruta = Path(__file__).resolve().parents[1] / "dashboard_360.py"
        arbol = ast.parse(ruta.read_text(encoding="utf-8-sig"))
        colores_dashboard = None
        for nodo in arbol.body:
            if not isinstance(nodo, ast.Assign):
                continue
            if any(
                isinstance(destino, ast.Name) and destino.id == "NINEBOX_COLORES"
                for destino in nodo.targets
            ):
                colores_dashboard = ast.literal_eval(nodo.value)
                break

        self.assertEqual(colores_dashboard, esperados)

    def test_cortes_ninebox_redondean_al_entero_con_half_up(self):
        self.assertEqual(calculos.redondear_corte_ninebox(98.8), 99)
        self.assertEqual(calculos.redondear_corte_ninebox(98.5), 99)
        self.assertEqual(calculos.redondear_corte_ninebox(97.9), 98)

    def test_el_nivel_alto_del_ninebox_comienza_en_99(self):
        self.assertEqual(calculos.corte_superior_ninebox(97.8), 99)
        self.assertEqual(calculos.corte_superior_ninebox(98.8), 99)
        self.assertEqual(calculos.corte_superior_ninebox(99.6), 100)

    def test_puntaje_inferior_al_corte_entero_no_es_super_estrella(self):
        datos = pd.DataFrame(
            {
                "colaborador": ["Persona A", "Persona B"],
                "match_nombre": ["persona a", "persona b"],
                "potencial": [100.0, 99.0],
                "desempeno_360": [98.9, 98.7],
            }
        )

        resultado = integrado.clasificar_ninebox(datos).set_index("colaborador")

        self.assertEqual(resultado.loc["Persona A", "nivel_potencial"], "alto")
        self.assertNotEqual(resultado.loc["Persona A", "nivel_desempeno"], "alto")
        self.assertNotEqual(resultado.loc["Persona A", "cuadrante"], 1)
        self.assertNotEqual(
            resultado.loc["Persona A", "cuadrante_nombre"],
            "Super Estrella",
        )

    def test_potencial_98_9_permanece_en_el_nivel_medio(self):
        datos = pd.DataFrame(
            {
                "colaborador": ["Persona A", "Persona B", "Persona C"],
                "match_key": [
                    "email:persona.a@example.com",
                    "email:persona.b@example.com",
                    "email:persona.c@example.com",
                ],
                "potencial": [98.9, 97.0, 100.0],
                "desempeno_360": [100.0, 90.0, 100.0],
            }
        )

        resultado = integrado.clasificar_ninebox(datos).set_index("colaborador")

        self.assertEqual(resultado.loc["Persona A", "potencial"], 98.9)
        self.assertEqual(resultado.loc["Persona A", "nivel_potencial"], "medio")
        self.assertNotEqual(resultado.loc["Persona A", "cuadrante"], 1)
        self.assertNotEqual(
            resultado.loc["Persona A", "cuadrante_nombre"],
            "Super Estrella",
        )

    def test_dashboard_muestra_los_rangos_sin_decimales(self):
        ruta = Path(__file__).resolve().parents[1] / "dashboard_360.py"
        contenido = ruta.read_text(encoding="utf-8-sig")

        self.assertIn("cortes['potencial_sup']:.0f", contenido)
        self.assertIn("cortes['potencial_inf']:.0f", contenido)
        self.assertIn("cortes['desempeno_sup']:.0f", contenido)
        self.assertIn("cortes['desempeno_inf']:.0f", contenido)

    def test_un_filtro_no_recalcula_el_cuadrante_general(self):
        clasificado_general = pd.DataFrame(
            {
                "colaborador": ["Persona A", "Persona B", "Persona C"],
                "match_key": [
                    "email:persona.a@example.com",
                    "email:persona.b@example.com",
                    "email:persona.c@example.com",
                ],
                "potencial": [99.0, 85.0, 70.0],
                "desempeno_360": [99.0, 85.0, 70.0],
                "nivel_potencial": ["alto", "medio", "bajo"],
                "nivel_desempeno": ["alto", "medio", "bajo"],
                "cuadrante": [1, 5, 9],
                "cuadrante_nombre": [
                    "Super Estrella",
                    "Colaborador clave",
                    "Bajo rendimiento",
                ],
            }
        )
        visibles = pd.DataFrame(
            {
                "colaborador": ["Persona B"],
                "match_key": ["email:persona.b@example.com"],
                "potencial": [85.0],
                "desempeno_360": [85.0],
            }
        )

        resultado = self.filtrar_ninebox_general(
            clasificado_general,
            visibles,
        )

        self.assertEqual(len(resultado), 1)
        self.assertEqual(resultado.iloc[0]["colaborador"], "Persona B")
        self.assertEqual(resultado.iloc[0]["cuadrante"], 5)
        self.assertEqual(
            resultado.iloc[0]["cuadrante_nombre"],
            "Colaborador clave",
        )

    def test_dashboard_calcula_el_ninebox_general_antes_de_los_filtros(self):
        ruta = Path(__file__).resolve().parents[1] / "dashboard_360.py"
        contenido = ruta.read_text(encoding="utf-8-sig")

        posicion_general = contenido.index("df_ninebox_general = preparar_ninebox")
        posicion_filtros = contenido.index("if hay_filtros_globales:")
        self.assertLess(posicion_general, posicion_filtros)
        self.assertIn("cortes = cortes_ninebox_general", contenido)
        self.assertNotIn("cortes = cortes_ninebox(df_ninebox_base)", contenido)

    def test_dashboard_unifica_un_segundo_nombre_adicional(self):
        ruta = Path(__file__).resolve().parents[1] / "dashboard_360.py"
        arbol = ast.parse(ruta.read_text(encoding="utf-8-sig"))
        requeridas = {
            "normalizar_nombre_match",
            "normalizar_correo",
            "preparar_ninebox",
            "expandir_llaves_match",
        }
        funciones = [
            nodo
            for nodo in arbol.body
            if isinstance(nodo, ast.FunctionDef) and nodo.name in requeridas
        ]
        espacio = {"pd": pd, "motor_360": calculos}
        exec(compile(ast.Module(body=funciones, type_ignores=[]), str(ruta), "exec"), espacio)

        resultado = espacio["preparar_ninebox"](
            pd.DataFrame(
                [{
                    "colaborador": "Indhira Mendoza Coste",
                    "global": 81.75,
                    "email_colaborador": "imendoza@speedster.com.do",
                }]
            ),
            pd.DataFrame(
                [{
                    "colaborador": "Mendoza Coste Indhira Severiana",
                    "evaluacion_potencial": 79.91,
                    "correo": pd.NA,
                }]
            ),
        )

        self.assertEqual(len(resultado), 1)
        self.assertEqual(resultado.iloc[0]["colaborador"], "Indhira Mendoza Coste")
        self.assertEqual(resultado.iloc[0]["potencial"], 79.91)

    def test_indice_global_no_duplica_el_nombre_ampliado(self):
        ruta = Path(__file__).resolve().parents[1] / "dashboard_360.py"
        arbol = ast.parse(ruta.read_text(encoding="utf-8-sig"))
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
        exec(compile(ast.Module(body=funciones, type_ignores=[]), str(ruta), "exec"), espacio)

        indice = espacio["construir_indice_colaboradores"](
            {
                "df_global": pd.DataFrame(
                    [{
                        "colaborador": "Indhira Mendoza Coste",
                        "email_colaborador": "imendoza@speedster.com.do",
                    }]
                ),
                "df_metadata": pd.DataFrame(),
            },
            {
                "df_personas": pd.DataFrame(
                    [{
                        "colaborador": "Mendoza Coste Indhira Severiana",
                        "correo": pd.NA,
                    }]
                )
            },
            {
                "df_colaboradores": pd.DataFrame(
                    [{
                        "colaborador": "Indhira Mendoza Coste",
                        "email_colaborador": "imendoza@speedster.com.do",
                    }]
                )
            },
        )

        self.assertEqual(len(indice), 1)
        self.assertEqual(indice.iloc[0]["correo"], "imendoza@speedster.com.do")


if __name__ == "__main__":
    unittest.main()
