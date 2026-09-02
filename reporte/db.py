"""Acceso a datos para el dashboard Streamlit."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pandas as pd

from reporte import objetivos as motor_objetivos
from reporte import potencial as motor_potencial


def resolver_database_url(secrets: Mapping[str, Any]) -> str:
    """Obtiene la URL de PostgreSQL desde formatos comunes de secrets.toml."""
    database_url = (
        secrets.get("DATABASE_URL")
        or secrets.get("database_url")
        or secrets.get("NEON_DATABASE_URL")
        or secrets.get("neon_database_url")
    )

    if not database_url:
        for section_name in ("database", "postgres", "postgresql", "neon"):
            section = secrets.get(section_name)
            if isinstance(section, Mapping):
                database_url = (
                    section.get("url")
                    or section.get("database_url")
                    or section.get("DATABASE_URL")
                )
                if database_url:
                    break

    if not database_url:
        connections = secrets.get("connections")
        if isinstance(connections, Mapping):
            for section in connections.values():
                if isinstance(section, Mapping):
                    database_url = (
                        section.get("url")
                        or section.get("database_url")
                        or section.get("DATABASE_URL")
                    )
                    if database_url:
                        break

    if not database_url:
        raise ValueError(
            "Falta DATABASE_URL en secrets. Configura DATABASE_URL o "
            "[database] url en .streamlit/secrets.toml."
        )

    return str(database_url)


def convertir_url_sqlalchemy(database_url: str) -> str:
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    return database_url


def leer_tabla(database_url: str, tabla: str, schema: str = "public") -> pd.DataFrame:
    from sqlalchemy import create_engine

    engine = create_engine(convertir_url_sqlalchemy(database_url), pool_pre_ping=True)
    return pd.read_sql_table(tabla, con=engine, schema=schema)


def _resumen_potencial(df_personas: pd.DataFrame, df_competencias: pd.DataFrame) -> dict:
    evaluados = int(df_personas["evaluacion_potencial"].notna().sum())
    return {
        "personas": len(df_personas),
        "evaluados": evaluados,
        "sin_evaluacion": len(df_personas) - evaluados,
        "con_potencial_2025": int(df_personas["potencial_2025"].notna().sum()),
        "con_disc": int(df_personas["disc"].notna().sum()),
        "con_iq": int(df_personas["iq"].notna().sum()),
        "competencias_catalogo": int(df_competencias["competencia"].nunique()),
        "competencias_con_datos": int(df_competencias["competencia"].nunique()),
    }


def leer_base_dashboard(database_url: str, schema: str = "public") -> tuple[pd.DataFrame, dict, dict]:
    """Lee desde Neon las tablas necesarias para reconstruir el dashboard."""
    df_desempeno = leer_tabla(database_url, "desempeno_raw", schema)
    df_personas = leer_tabla(database_url, "potencial_personas", schema)
    df_competencias = leer_tabla(database_url, "potencial_competencias", schema)

    try:
        catalogo = leer_tabla(database_url, "potencial_catalogo_competencias", schema)
        catalogo_competencias = catalogo["competencia"].dropna().astype(str).tolist()
    except Exception:
        catalogo_competencias = sorted(
            df_competencias["competencia"].dropna().astype(str).unique().tolist()
        )

    for col in ["respuesta_valor", "puntaje"]:
        if col in df_desempeno.columns:
            df_desempeno[col] = pd.to_numeric(df_desempeno[col], errors="coerce")

    for col in ["potencial_2025", "evaluacion_potencial"]:
        if col in df_personas.columns:
            df_personas[col] = pd.to_numeric(df_personas[col], errors="coerce")

    # Las etiquetas se derivan siempre del puntaje para que una carga histórica
    # de Neon no contradiga los cortes oficiales vigentes.
    if "evaluacion_potencial" in df_personas.columns:
        escala_oficial = df_personas["evaluacion_potencial"].map(
            motor_potencial.clasificar_nivel_potencial
        )
        escala_oficial = escala_oficial.replace("", pd.NA)
        df_personas["escala_benchmark"] = escala_oficial
        df_personas["escala_potencial"] = escala_oficial

    for col in ["valor", "esperado", "brecha", "ajuste"]:
        if col in df_competencias.columns:
            df_competencias[col] = pd.to_numeric(df_competencias[col], errors="coerce")

    res_potencial = {
        "df_personas": df_personas,
        "df_competencias": df_competencias,
        "resumen": _resumen_potencial(df_personas, df_competencias),
        "catalogo_competencias": catalogo_competencias,
    }

    try:
        res_objetivos = {
            "df_fuente": leer_tabla(database_url, "objetivos_raw", schema),
            "df_colaboradores": leer_tabla(database_url, "objetivos_colaboradores", schema),
            "df_cargos": leer_tabla(database_url, "objetivos_cargos", schema),
            "df_objetivos": leer_tabla(database_url, "objetivos_items", schema),
        }
        for df in res_objetivos.values():
            for col in ["puntaje", "objetivos", "colaboradores", "respuesta_valor", "calificacion_porcentaje"]:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
        res_objetivos["resumen"] = {
            "filas": len(res_objetivos["df_fuente"]),
            "colaboradores": int(res_objetivos["df_colaboradores"]["colaborador"].nunique()),
            "jefes": int(res_objetivos["df_colaboradores"]["jefe"].nunique()),
            "cargos": int(res_objetivos["df_cargos"]["cargo_objetivo"].nunique()),
            "objetivos": int(res_objetivos["df_objetivos"]["objetivo"].nunique()),
            "promedio": float(res_objetivos["df_colaboradores"]["puntaje"].mean())
            if len(res_objetivos["df_colaboradores"]) else 0.0,
            "ciclo": str(res_objetivos["df_fuente"]["nombre_ciclo"].dropna().iloc[0])
            if len(res_objetivos["df_fuente"]) and res_objetivos["df_fuente"]["nombre_ciclo"].notna().any()
            else "Objetivos",
        }
    except Exception:
        res_objetivos = motor_objetivos._vacio()

    return df_desempeno, res_potencial, res_objetivos
