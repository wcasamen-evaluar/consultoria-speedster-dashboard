import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class BrandingSpeedsterTest(unittest.TestCase):
    def test_evaluar_se_mantiene_y_speedster_es_el_unico_logo_de_cliente(self):
        self.assertTrue((ROOT / "logos" / "speedster_logo.png").is_file())

        dashboard = (ROOT / "dashboard_360.py").read_text(encoding="utf-8")
        pdf = (ROOT / "reporte" / "generar_pdf.py").read_text(encoding="utf-8")

        for fuente in (dashboard, pdf):
            self.assertIn("speedster_logo.png", fuente)
            self.assertNotIn("Logo Macrotech", fuente)
            self.assertNotIn("Logo CIMER", fuente)
            self.assertNotIn("Logo-CAI", fuente)

        self.assertIn("brand_evaluar_on_dark.svg", dashboard)
        self.assertIn("ev-client-logo-card", dashboard)
        self.assertIn("background: #ffffff;", dashboard)
        self.assertIn("logo_evaluar_header.png", pdf)
        self.assertIn("logo_evaluar_cover_from_svg.png", pdf)

    def test_cliente_predeterminado_es_speedster(self):
        main = (ROOT / "reporte" / "main.py").read_text(encoding="utf-8")
        integrado = (ROOT / "reporte" / "integrado.py").read_text(encoding="utf-8")
        self.assertIn('CLIENTE = "Speedster"', main)
        self.assertIn('default="Speedster"', integrado)

    def test_empresa_es_fija_y_no_un_filtro_vacio(self):
        dashboard = (ROOT / "dashboard_360.py").read_text(encoding="utf-8")
        self.assertIn('value="Speedster"', dashboard)
        self.assertIn('key="filtro_global_empresa_fija"', dashboard)
        self.assertNotIn('key="filtro_global_empresa"', dashboard)


if __name__ == "__main__":
    unittest.main()
