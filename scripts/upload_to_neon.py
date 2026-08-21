"""
Carga la base local del dashboard a Neon PostgreSQL.

Uso seguro:
    python scripts/upload_to_neon.py --dry-run
    python scripts/upload_to_neon.py

El script lee DATABASE_URL desde .streamlit/secrets.toml. Ese archivo no debe
subirse a GitHub.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reporte import calculos as motor_360  # noqa: E402
from reporte import objetivos as motor_objetivos  # noqa: E402
from reporte import potencial as motor_potencial  # noqa: E402


DEFAULT_EXCEL_PATTERN = "Fase_I_Evaluaci*n_360__180__90__copia_.xlsx"
SECRETS_PATH = ROOT / ".streamlit" / "secrets.toml"


def snake_case(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value))
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "_", text).strip("_")
    text = re.sub(r"_+", "_", text)
    if not text:
        text = "columna"
    if text[0].isdigit():
        text = f"col_{text}"
    return text


def normalizar_columnas_sql(df: pd.DataFrame) -> pd.DataFrame:
    salida = df.copy()
    vistos: dict[str, int] = {}
    columnas = []
    for columna in salida.columns:
        base = snake_case(columna)
        contador = vistos.get(base, 0)
        vistos[base] = contador + 1
        columnas.append(base if contador == 0 else f"{base}_{contador + 1}")
    salida.columns = columnas
    return salida


def buscar_excel(explicit_path: str | None) -> Path:
    if explicit_path:
        ruta = Path(explicit_path)
        if not ruta.is_absolute():
            ruta = ROOT / ruta
        if not ruta.exists():
            raise FileNotFoundError(f"No existe el archivo Excel: {ruta}")
        return ruta

    candidatos = sorted(ROOT.glob(DEFAULT_EXCEL_PATTERN))
    if not candidatos:
        raise FileNotFoundError(
            "No encontre el Excel base. Indica la ruta con --excel o ponlo en "
            f"la carpeta del proyecto con patron {DEFAULT_EXCEL_PATTERN!r}."
        )
    return candidatos[0]


def leer_database_url() -> str:
    if not SECRETS_PATH.exists():
        raise FileNotFoundError(f"No existe {SECRETS_PATH}")

    with SECRETS_PATH.open("rb") as handle:
        secrets = tomllib.load(handle)

    database_url = (
        secrets.get("DATABASE_URL")
        or secrets.get("database_url")
        or secrets.get("NEON_DATABASE_URL")
        or secrets.get("neon_database_url")
    )

    if not database_url:
        for section_name in ("database", "postgres", "postgresql", "neon"):
            section = secrets.get(section_name)
            if isinstance(section, dict):
                database_url = (
                    section.get("url")
                    or section.get("database_url")
                    or section.get("DATABASE_URL")
                )
                if database_url:
                    break

    if not database_url:
        connections = secrets.get("connections")
        if isinstance(connections, dict):
            for section in connections.values():
                if isinstance(section, dict):
                    database_url = (
                        section.get("url")
                        or section.get("database_url")
                        or section.get("DATABASE_URL")
                    )
                    if database_url:
                        break

    if not database_url:
        raise ValueError(
            "Falta DATABASE_URL en .streamlit/secrets.toml. "
            "Usa DATABASE_URL = \"postgresql://...\" o [connections.neon] url = \"postgresql://...\"."
        )
    if "usuario:clave" in database_url or "host.neon.tech" in database_url:
        raise ValueError("DATABASE_URL sigue con valores de ejemplo.")
    return str(database_url)


def preparar_tablas(excel_path: Path) -> dict[str, pd.DataFrame]:
    df_360 = motor_360.leer_exportacion_dashboard(excel_path)
    metadata_organizacional = motor_360.leer_metadata_organizacional(excel_path)
    if not metadata_organizacional.empty:
        df_360 = motor_360.completar_metadata_colaboradores(
            df_360,
            metadata_organizacional,
            "nombre_colaborador",
            "email_colaborador",
        )
    resultado_360 = motor_360.calcular_dashboard(df_360)
    resultado_potencial = motor_potencial.leer_potencial(excel_path)
    if not metadata_organizacional.empty:
        resultado_360["df_global"] = motor_360.completar_metadata_colaboradores(
            resultado_360["df_global"],
            metadata_organizacional,
            "colaborador",
            "email_colaborador",
        )
        resultado_potencial["df_personas"] = motor_360.completar_metadata_colaboradores(
            resultado_potencial["df_personas"],
            metadata_organizacional,
            "colaborador",
            "correo",
        )
        resultado_potencial["df_competencias"] = motor_360.completar_metadata_colaboradores(
            resultado_potencial["df_competencias"],
            metadata_organizacional,
            "colaborador",
            "correo",
        )
    resultado_objetivos = motor_objetivos.leer_objetivos(excel_path)

    metadata = pd.DataFrame(
        [
            {
                "cargado_en_utc": datetime.now(timezone.utc).isoformat(),
                "archivo_origen": excel_path.name,
                "filas_desempeno_raw": len(df_360),
                "colaboradores_desempeno": resultado_360["resumen_fuente"]["colaboradores"],
                "competencias_desempeno": resultado_360["resumen_fuente"]["competencias"],
                "items_desempeno": resultado_360["resumen_fuente"]["items"],
                "personas_potencial": resultado_potencial["resumen"]["personas"],
                "evaluados_potencial": resultado_potencial["resumen"]["evaluados"],
                "colaboradores_objetivos": resultado_objetivos["resumen"]["colaboradores"],
                "objetivos": resultado_objetivos["resumen"]["objetivos"],
                "resumen_potencial_json": json.dumps(
                    resultado_potencial["resumen"], ensure_ascii=False
                ),
                "resumen_objetivos_json": json.dumps(
                    resultado_objetivos["resumen"], ensure_ascii=False
                ),
            }
        ]
    )

    tablas = {
        "metadata_carga": metadata,
        "metadata_organizacional": metadata_organizacional,
        "desempeno_raw": resultado_360["df_fuente"],
        "desempeno_global": resultado_360["df_global"],
        "desempeno_competencias": resultado_360["df_comp"],
        "desempeno_competencias_promedio": resultado_360["df_comp_prom"],
        "desempeno_items": resultado_360["df_items"],
        "potencial_personas": resultado_potencial["df_personas"],
        "potencial_competencias": resultado_potencial["df_competencias"],
        "potencial_catalogo_competencias": pd.DataFrame(
            {"competencia": resultado_potencial["catalogo_competencias"]}
        ),
        "objetivos_raw": resultado_objetivos["df_fuente"],
        "objetivos_colaboradores": resultado_objetivos["df_colaboradores"],
        "objetivos_cargos": resultado_objetivos["df_cargos"],
        "objetivos_items": resultado_objetivos["df_objetivos"],
    }
    return {nombre: normalizar_columnas_sql(df) for nombre, df in tablas.items()}


def convertir_url_sqlalchemy(database_url: str) -> str:
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    return database_url


def subir_tablas(
    tablas: dict[str, pd.DataFrame],
    database_url: str,
    schema: str | None,
    if_exists: str,
) -> None:
    from sqlalchemy import create_engine, text

    engine = create_engine(convertir_url_sqlalchemy(database_url), pool_pre_ping=True)
    with engine.begin() as conn:
        conn.execute(text("select 1"))
        if schema and schema != "public":
            conn.execute(text(f'create schema if not exists "{schema}"'))

    for nombre, df in tablas.items():
        print(f"Subiendo {nombre}: {len(df):,} filas")
        df.to_sql(
            nombre,
            con=engine,
            schema=schema,
            if_exists=if_exists,
            index=False,
            chunksize=1000,
            method="multi",
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sube a Neon las tablas normalizadas del dashboard Macrotech."
    )
    parser.add_argument("--excel", help="Ruta del archivo base .xlsx.")
    parser.add_argument(
        "--schema",
        default="public",
        help="Schema destino en PostgreSQL. Por defecto: public.",
    )
    parser.add_argument(
        "--if-exists",
        choices=["replace", "append", "fail"],
        default="replace",
        help="Comportamiento si la tabla ya existe. Por defecto: replace.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Valida lectura y muestra conteos sin conectarse a Neon.",
    )
    args = parser.parse_args()

    excel_path = buscar_excel(args.excel)
    print(f"Archivo base: {excel_path.name}")

    tablas = preparar_tablas(excel_path)
    print("\nTablas preparadas:")
    for nombre, df in tablas.items():
        print(f"  - {nombre}: {len(df):,} filas x {len(df.columns)} columnas")

    if args.dry_run:
        print("\nDry-run completo. No se subio nada a Neon.")
        return

    database_url = leer_database_url()
    subir_tablas(tablas, database_url, args.schema, args.if_exists)
    print("\nCarga completa en Neon.")


if __name__ == "__main__":
    main()
