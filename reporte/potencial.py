"""Lectura y normalización de la hoja Potencial para el dashboard y reportes."""

from __future__ import annotations

import re
import unicodedata
import warnings
from pathlib import Path

import pandas as pd

warnings.filterwarnings("ignore", category=pd.errors.PerformanceWarning)

HOJA_POTENCIAL = "Potencial"
LIMITES_NIVEL_POTENCIAL = (80, 85)
NIVELES_POTENCIAL = [
    "Potencial bajo",
    "Potencial medio",
    "Alto potencial",
]
NIVELES_COMPETENCIAS = NIVELES_POTENCIAL
ETIQUETAS_ESCALA = NIVELES_POTENCIAL
MAPA_ESCALA = {
    **{etiqueta.casefold(): etiqueta for etiqueta in ETIQUETAS_ESCALA},
    "potencial bajo": "Potencial bajo",
    "potencial medio": "Potencial medio",
    "potencial alto": "Alto potencial",
    "alto potencial": "Alto potencial",
    "alejado al perfil": "Potencial bajo",
    "alejado del perfil": "Potencial bajo",
    "cercano al perfil": "Potencial medio",
    "ajustado al perfil": "Alto potencial",
    "ajuste al perfil": "Alto potencial",
}
RANGOS_NIVELES_COMPETENCIAS = {
    "Potencial bajo": "0 - 79,99",
    "Potencial medio": "80 - 84,99",
    "Alto potencial": "85 - 100",
}
COLORES_NIVELES_COMPETENCIAS = {
    "Potencial bajo": "#d94a45",
    "Potencial medio": "#f0a000",
    "Alto potencial": "#1d9e75",
}


def clasificar_nivel_potencial(valor: object) -> str:
    """Aplica la escala oficial a la cifra original, sin redondearla."""
    puntaje = pd.to_numeric(pd.Series([valor]), errors="coerce").iloc[0]
    if pd.isna(puntaje):
        return ""
    if float(puntaje) >= LIMITES_NIVEL_POTENCIAL[1]:
        return "Alto potencial"
    if float(puntaje) >= LIMITES_NIVEL_POTENCIAL[0]:
        return "Potencial medio"
    return "Potencial bajo"


def clasificar_nivel_competencias(valor: object) -> str:
    """Mantiene el alias usado por el dashboard con las etiquetas oficiales."""
    return clasificar_nivel_potencial(valor)


def resumir_competencias_evaluadas(
    df_competencias: pd.DataFrame,
    orden_preferido: list[str] | None = None,
) -> pd.DataFrame:
    """Promedia únicamente competencias que tienen un ajuste evaluado.

    Ordena de mayor a menor promedio. El catálogo histórico y el orden de
    aparición solo se usan para desempatar resultados iguales.
    """
    columnas_salida = ["competencia", "clave_competencia", "puntaje"]
    if (
        df_competencias.empty
        or "competencia" not in df_competencias
        or "ajuste" not in df_competencias
    ):
        return pd.DataFrame(columns=columnas_salida)

    datos = df_competencias[["competencia", "ajuste"]].copy()
    datos["competencia"] = datos["competencia"].apply(_limpiar_texto)
    datos["clave_competencia"] = datos["competencia"].map(_clave_encabezado)
    datos["ajuste"] = pd.to_numeric(datos["ajuste"], errors="coerce")
    datos["orden_origen"] = range(len(datos))
    datos = datos[
        datos["ajuste"].notna() & datos["clave_competencia"].ne("")
    ].copy()
    if datos.empty:
        return pd.DataFrame(columns=columnas_salida)

    resumen = (
        datos.groupby("clave_competencia", sort=False, as_index=False)
        .agg(
            competencia=("competencia", "first"),
            puntaje=("ajuste", "mean"),
            orden_origen=("orden_origen", "min"),
        )
    )
    resumen["puntaje"] = resumen["puntaje"].mul(100)

    catalogo = orden_preferido or []
    mapa_catalogo = {
        _clave_encabezado(competencia): (indice, competencia)
        for indice, competencia in enumerate(catalogo)
    }
    resumen["orden_catalogo"] = resumen["clave_competencia"].map(
        lambda clave: mapa_catalogo.get(clave, (len(catalogo), ""))[0]
    )
    resumen["es_nueva"] = ~resumen["clave_competencia"].isin(mapa_catalogo)
    resumen["competencia"] = resumen.apply(
        lambda fila: mapa_catalogo.get(
            fila["clave_competencia"],
            (None, fila["competencia"]),
        )[1],
        axis=1,
    )
    resumen = resumen.sort_values(
        ["puntaje", "es_nueva", "orden_catalogo", "orden_origen"],
        ascending=[False, True, True, True],
        kind="stable",
    )
    return resumen[columnas_salida].reset_index(drop=True)


def contar_escala(df: pd.DataFrame, columna: str) -> pd.Series:
    """Cuenta una escala ignorando diferencias de mayúsculas y espacios."""
    valores = (
        df[columna]
        .dropna()
        .astype(str)
        .str.strip()
        .str.casefold()
        .map(MAPA_ESCALA)
    )
    return valores.value_counts().reindex(ETIQUETAS_ESCALA, fill_value=0)


def _limpiar_texto(valor):
    return valor.strip() if isinstance(valor, str) else valor


def _codigo_arquetipo(valor):
    if not isinstance(valor, str):
        return pd.NA
    match = re.search(r"\(([^)]+)\)", valor)
    return match.group(1).strip() if match else valor.strip()


def _clave_encabezado(valor: object) -> str:
    """Normaliza encabezados sin depender de tildes o sufijos de pandas."""
    if valor is None or pd.isna(valor):
        return ""
    texto = unicodedata.normalize("NFKD", str(valor))
    texto = "".join(char for char in texto if not unicodedata.combining(char))
    texto = re.sub(r"\.\d+$", "", texto.strip().casefold())
    return re.sub(r"[^a-z0-9]+", " ", texto).strip()


def _detectar_filas_encabezado(raw: pd.DataFrame) -> tuple[int, int]:
    """Ubica las filas de campos y grupos en variantes históricas y nuevas.

    La exportación histórica usa dos filas auxiliares antes de los campos. La
    exportación nueva usa una fila de grupos y otra de campos; en el archivo
    original algunos campos personales aparecen en la fila de grupos. Se
    detecta la fila con la secuencia Valor/Esperado/Brecha y se conserva la
    fila inmediatamente anterior como catálogo de competencias.
    """
    limite = min(len(raw), 10)
    mejor_fila = -1
    mejor_puntaje = -1
    for indice in range(limite):
        claves = [_clave_encabezado(valor) for valor in raw.iloc[indice].tolist()]
        metricas = sum(
            clave.startswith(("valor", "esperado", "brecha"))
            for clave in claves
        )
        identidad = sum(
            clave in {
                "nombre completo",
                "nombre del perfil",
                "nombres",
                "apellidos",
                "correo",
                "correo potencial",
            }
            for clave in claves
        )
        puntaje = metricas * 10 + identidad
        if puntaje > mejor_puntaje:
            mejor_fila = indice
            mejor_puntaje = puntaje

    if mejor_fila < 0 or mejor_puntaje <= 0:
        raise ValueError(
            "No se pudo identificar la fila de encabezados de la hoja 'Potencial'."
        )
    return mejor_fila, max(0, mejor_fila - 1)


def _completar_encabezados_persona(
    df: pd.DataFrame,
    raw: pd.DataFrame,
    fila_encabezado: int,
) -> pd.DataFrame:
    """Recupera campos personales ubicados en la fila superior del exporte."""
    if fila_encabezado <= 0:
        return df
    fila_superior = raw.iloc[fila_encabezado - 1].tolist()
    renombres = {}
    for indice, columna in enumerate(df.columns):
        if indice >= len(fila_superior) or not str(columna).startswith("Unnamed"):
            continue
        candidato = fila_superior[indice]
        clave = _clave_encabezado(candidato)
        if clave in {
            "email",
            "correo",
            "correo potencial",
            "correo instancia",
            "nombre completo",
            "nombres",
            "apellidos",
            "nombre del perfil",
            "empresa",
            "cargo",
            "jefe",
            "grupo",
            "pais",
            "area",
            "cap",
            "competencias",
            "potencial 2025",
            "evaluacion de potencial",
            "escala benchmark externo",
            "escala potencial",
        }:
            renombres[columna] = str(candidato).strip()
    return df.rename(columns=renombres)


def _clasificar_potencial(
    valor,
    limites: tuple[float, float],
):
    puntaje = pd.to_numeric(pd.Series([valor]), errors="coerce").iloc[0]
    if pd.isna(puntaje):
        return pd.NA
    bajo, alto = limites
    if puntaje >= alto:
        return "Alto potencial"
    if puntaje >= bajo:
        return "Potencial medio"
    return "Potencial bajo"


def _preparar_columnas_persona(df: pd.DataFrame) -> pd.DataFrame:
    rename_map = {
        "Email": "correo",
        "Correo": "correo",
        "Correo Potencial": "correo_potencial",
        "Correo Instancia": "correo_instancia",
        "No. IdentificaciÃ³n": "identificacion",
        "No. Identificación": "identificacion",
        "PaÃ­s": "pais",
        "País": "pais",
        "Ãrea": "area",
        "Área": "area",
        "CAP": "potencial_2025",
        "COMPETENCIAS": "evaluacion_potencial",
        "EvaluaciÃ³n de Potencial": "evaluacion_potencial",
        "Evaluación de Potencial": "evaluacion_potencial",
        "Potencial 2025": "potencial_2025",
        "Escala Benchmark externo": "escala_benchmark",
        "Escala Potencial": "escala_potencial",
    }
    df = df.rename(columns={col: rename_map.get(col, col) for col in df.columns})

    # Prioridad de identidad: nombre completo explícito, nombres/apellidos y,
    # únicamente en el formato histórico, Nombre del Perfil.
    if "colaborador" not in df.columns and "NOMBRE COMPLETO" in df.columns:
        df["colaborador"] = df["NOMBRE COMPLETO"]
    if "colaborador" not in df.columns and {"Nombres", "Apellidos"}.issubset(df.columns):
        df["colaborador"] = (
            df["Nombres"].fillna("").astype(str).str.strip()
            + " "
            + df["Apellidos"].fillna("").astype(str).str.strip()
        ).str.strip()
    if "colaborador" not in df.columns and "Nombre del Perfil" in df.columns:
        df["colaborador"] = df["Nombre del Perfil"]

    if "Nombre del Perfil" in df.columns:
        df["perfil"] = df["Nombre del Perfil"]
        if "Cargo" not in df.columns and "cargo" not in df.columns:
            df["cargo"] = df["perfil"]

    defaults = {
        "correo": df.get("correo_potencial", pd.NA),
        "correo_potencial": pd.NA,
        "correo_instancia": pd.NA,
        "identificacion": pd.NA,
        "empresa": pd.NA,
        "pais": pd.NA,
        "area": pd.NA,
        "escala_benchmark": pd.NA,
        "escala_potencial": pd.NA,
        "potencial_2025": pd.NA,
        "evaluacion_potencial": pd.NA,
    }
    for original in ["Empresa", "Cargo", "Jefe", "Grupo"]:
        if original in df.columns:
            df[original.lower()] = df[original]
    for col, default in defaults.items():
        if col not in df.columns:
            df[col] = default
    for col in ["cargo", "jefe", "grupo"]:
        if col not in df.columns:
            df[col] = pd.NA
    return df


def leer_potencial(ruta: str | Path) -> dict:
    """Convierte la matriz ancha de Potencial en tablas de personas y competencias."""
    with pd.ExcelFile(ruta) as xls:
        if HOJA_POTENCIAL not in xls.sheet_names:
            raise ValueError("El archivo base debe contener la hoja 'Potencial'.")

        raw = pd.read_excel(xls, sheet_name=HOJA_POTENCIAL, header=None)
        header_row, grupos_row = _detectar_filas_encabezado(raw)
        grupos = raw.iloc[grupos_row].tolist() if header_row > 0 else [pd.NA] * raw.shape[1]
        df = pd.read_excel(xls, sheet_name=HOJA_POTENCIAL, header=header_row)
    df = _completar_encabezados_persona(df, raw, header_row)
    rename_grupos = {}
    for idx, col in enumerate(df.columns):
        grupo = grupos[idx] if idx < len(grupos) else pd.NA
        if str(col).startswith("Unnamed") and isinstance(grupo, str) and grupo.strip().casefold() == "iq":
            rename_grupos[col] = "IQ"
    if rename_grupos:
        df = df.rename(columns=rename_grupos)
    df = _preparar_columnas_persona(df)

    if "colaborador" not in df.columns:
        raise ValueError("La hoja 'Potencial' debe contener el nombre del colaborador.")

    df = df[df["colaborador"].notna()].copy()
    df["colaborador"] = df["colaborador"].astype(str).str.strip()
    if df["colaborador"].duplicated().any():
        duplicados = int(df["colaborador"].duplicated().sum())
        raise ValueError(f"La hoja 'Potencial' contiene {duplicados} nombres duplicados.")

    for col in ["potencial_2025", "evaluacion_potencial"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    if df["evaluacion_potencial"].notna().sum() == 0 and "potencial_2025" in df.columns:
        df["evaluacion_potencial"] = df["potencial_2025"]
    # El puntaje numérico es la fuente oficial. Se recalculan ambas columnas
    # para no heredar etiquetas históricas o inconsistentes del archivo origen.
    escala_oficial = df["evaluacion_potencial"].apply(clasificar_nivel_potencial)
    escala_oficial = escala_oficial.replace("", pd.NA)
    df["escala_benchmark"] = escala_oficial
    df["escala_potencial"] = escala_oficial

    columnas = list(df.columns)
    competencias = []
    catalogo_competencias = []
    for inicio in range(len(columnas)):
        if inicio + 3 >= len(columnas):
            break
        col_valor, col_esperado, col_brecha, col_ajuste = columnas[inicio:inicio + 4]
        if not (
            _clave_encabezado(col_valor).startswith("valor")
            and _clave_encabezado(col_esperado).startswith("esperado")
            and _clave_encabezado(col_brecha).startswith("brecha")
        ):
            continue
        candidatos_grupo = [
            grupos[indice]
            for indice in range(inicio, min(inicio + 4, len(grupos)))
            if isinstance(grupos[indice], str) and grupos[indice].strip()
        ]
        nombre_competencia = candidatos_grupo[0] if candidatos_grupo else col_ajuste
        if pd.isna(nombre_competencia) or str(nombre_competencia).startswith("Unnamed"):
            continue
        nombre_competencia = str(nombre_competencia).strip()
        if _clave_encabezado(nombre_competencia) in {
            "valor", "esperado", "brecha", "ajuste", "cumplimiento"
        }:
            continue
        if nombre_competencia in catalogo_competencias:
            continue
        catalogo_competencias.append(nombre_competencia)

        bloque = df[
            [
                "correo",
                "correo_potencial",
                "correo_instancia",
                "colaborador",
                "empresa",
                "cargo",
                "jefe",
                "area",
                "grupo",
                col_valor,
                col_esperado,
                col_brecha,
                col_ajuste,
            ]
        ].copy()
        bloque.columns = [
            "correo",
            "correo_potencial",
            "correo_instancia",
            "colaborador",
            "empresa",
            "cargo",
            "jefe",
            "area",
            "grupo",
            "valor",
            "esperado",
            "brecha",
            "ajuste",
        ]
        bloque["competencia"] = nombre_competencia
        for col in ["valor", "esperado", "brecha", "ajuste"]:
            bloque[col] = pd.to_numeric(bloque[col], errors="coerce")
        bloque = bloque[bloque[["valor", "esperado", "brecha", "ajuste"]].notna().any(axis=1)]
        competencias.append(bloque)

    df_competencias = (
        pd.concat(competencias, ignore_index=True)
        if competencias
        else pd.DataFrame(
            columns=[
                "correo",
                "correo_potencial",
                "correo_instancia",
                "colaborador",
                "empresa",
                "cargo",
                "jefe",
                "area",
                "grupo",
                "valor",
                "esperado",
                "brecha",
                "ajuste",
                "competencia",
            ]
        )
    )
    for col in ["correo", "correo_potencial", "correo_instancia", "colaborador", "empresa", "cargo", "jefe", "area", "grupo"]:
        df_competencias[col] = df_competencias[col].apply(_limpiar_texto)

    for col in ["IQ", "Arquetipo", "Intensidad", "D", "I", "S", "C"]:
        if col not in df.columns:
            df[col] = pd.NA
    if "DISC" not in df.columns:
        df["DISC"] = df.get("Arquetipo", pd.NA)

    df_personas = df[
        [
            "correo",
            "correo_potencial",
            "correo_instancia",
            "colaborador",
            "identificacion",
            "empresa",
            "cargo",
            "jefe",
            "pais",
            "area",
            "grupo",
            "potencial_2025",
            "evaluacion_potencial",
            "escala_benchmark",
            "escala_potencial",
            "IQ",
            "DISC",
            "Arquetipo",
            "Intensidad",
            "D",
            "I",
            "S",
            "C",
        ]
    ].copy()
    df_personas.columns = [
        "correo",
        "correo_potencial",
        "correo_instancia",
        "colaborador",
        "identificacion",
        "empresa",
        "cargo",
        "jefe",
        "pais",
        "area",
        "grupo",
        "potencial_2025",
        "evaluacion_potencial",
        "escala_benchmark",
        "escala_potencial",
        "iq",
        "disc",
        "arquetipo",
        "intensidad",
        "d",
        "i",
        "s",
        "c",
    ]
    df_personas["disc"] = df_personas["disc"].combine_first(df_personas["arquetipo"])
    df_personas["arquetipo"] = df_personas["arquetipo"].apply(_codigo_arquetipo)
    for col in ["d", "i", "s", "c", "intensidad"]:
        df_personas[col] = pd.to_numeric(df_personas[col], errors="coerce")
    for col in [
        "correo",
        "correo_potencial",
        "correo_instancia",
        "colaborador",
        "empresa",
        "cargo",
        "jefe",
        "pais",
        "area",
        "grupo",
        "escala_benchmark",
        "escala_potencial",
        "iq",
        "disc",
        "arquetipo",
    ]:
        df_personas[col] = df_personas[col].apply(_limpiar_texto)

    for col in ["escala_benchmark", "escala_potencial"]:
        df_personas[col] = df_personas[col].apply(
            lambda valor: MAPA_ESCALA.get(valor.casefold(), valor)
            if isinstance(valor, str)
            else valor
        )

    evaluados = int(df_personas["evaluacion_potencial"].notna().sum())
    return {
        "df_personas": df_personas,
        "df_competencias": df_competencias,
        "resumen": {
            "personas": len(df_personas),
            "evaluados": evaluados,
            "sin_evaluacion": len(df_personas) - evaluados,
            "con_potencial_2025": int(df_personas["potencial_2025"].notna().sum()),
            "con_disc": int(df_personas["disc"].notna().sum()),
            "con_arquetipo": int(df_personas["arquetipo"].notna().sum()),
            "con_iq": int(df_personas["iq"].notna().sum()),
            "competencias_catalogo": len(catalogo_competencias),
            "competencias_con_datos": int(df_competencias["competencia"].nunique()),
        },
        "catalogo_competencias": catalogo_competencias,
    }
