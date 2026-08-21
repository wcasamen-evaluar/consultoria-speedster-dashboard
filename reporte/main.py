"""Orquestador del generador de informes integrales.

Uso desde la raiz del proyecto:

    python reporte/main.py

Por defecto usa el mismo Excel raiz del dashboard y genera un PDF de
prueba para el primer colaborador en reporte/output/.
"""

from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import generar_pdf
import integrado


CLIENTE = "Speedster"
PROCESO = "Evaluacion de Desempeno 360"
FECHA = datetime.now().strftime("%d/%m/%Y")
CARPETA_OUTPUT = Path(__file__).parent / "output"


def _slug(nombre: str) -> str:
    texto = unicodedata.normalize("NFKD", nombre)
    texto = "".join(ch for ch in texto if not unicodedata.combining(ch))
    texto = re.sub(r"[^a-zA-Z0-9]+", "_", texto).strip("_")
    return texto or "colaborador"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Genera informes PDF integrales desde el Excel raiz del dashboard."
    )
    parser.add_argument(
        "--excel",
        type=Path,
        default=None,
        help="Ruta opcional al Excel fuente. Si se omite, usa el Excel raiz del dashboard.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=CARPETA_OUTPUT,
        help="Carpeta de salida para los PDFs.",
    )
    parser.add_argument(
        "--limite",
        type=int,
        default=1,
        help="Genera solo los primeros N colaboradores. Por defecto genera 1 para pruebas.",
    )
    parser.add_argument(
        "--todos",
        action="store_true",
        help="Genera informes para todos los colaboradores.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    print("=" * 60)
    print("  Speedster - Generador de Informes Integrales")
    print(f"  Cliente : {CLIENTE}")
    print(f"  Proceso : {PROCESO}")
    print(f"  Fecha   : {FECHA}")
    print("=" * 60)

    try:
        base = integrado.cargar_base_reportes(args.excel)
    except Exception as exc:
        print(f"\nERROR: no se pudo cargar la base del dashboard: {exc}")
        sys.exit(1)

    reportes = base["reportes"]
    print(f"\nExcel fuente     : {base['ruta_excel']}")
    print(f"Colaboradores    : {len(reportes)}")
    print(f"Potencial        : {base['res_potencial']['resumen']['evaluados']} evaluados")
    print(f"Objetivos        : {base['res_objetivos']['resumen']['colaboradores']} colaboradores")
    print(f"Integrados       : {int(base['df_integrado']['integrada'].notna().sum())} colaboradores")

    args.output.mkdir(parents=True, exist_ok=True)

    errores = []
    items = list(reportes.items())
    if not args.todos and args.limite:
        items = items[: args.limite]

    print()
    for nombre, paquete in items:
        ruta_pdf = args.output / f"Informe_integral_{_slug(nombre)}.pdf"
        try:
            generar_pdf.generar_pdf(
                nombre=nombre,
                resultado=paquete["resultado_360"],
                proceso=PROCESO,
                cliente=CLIENTE,
                fecha=FECHA,
                cargo=paquete["ficha"].get("cargo", ""),
                area=paquete["ficha"].get("area", ""),
                ruta_salida=str(ruta_pdf),
                contexto_integral=paquete,
            )
        except Exception as exc:
            print(f"  x  Error generando PDF para {nombre}: {exc}")
            errores.append((nombre, str(exc)))

    print()
    print("=" * 60)
    if errores:
        print(f"  Completado con {len(errores)} error(es):")
        for nombre, err in errores:
            print(f"    - {nombre}: {err}")
    else:
        print(f"  OK  {len(items)} PDF(s) generado(s) en '{args.output}/'")
    print("=" * 60)


if __name__ == "__main__":
    main()
