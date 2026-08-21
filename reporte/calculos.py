"""
calculos.py
===========
Motor compartido para Evaluacion 360.

Lo usan:
    - reporte/main.py para generar PDFs individuales.
    - dashboard_360.py para vistas agregadas en Streamlit.
"""

from pathlib import Path
from collections import Counter
from collections.abc import Iterable
import math
import re
import unicodedata

import pandas as pd


# ---------------------------------------------------------------------------
# Constantes de negocio
# ---------------------------------------------------------------------------

ESCALA_TRANSFORM = {
    5: 100,
    4: 90,
    3: 85,
    2: 75,
    1: 65,
}

PESOS_BASE = {
    "autoEvaluation": 0.10,
    "bossToSubordinate": 0.40,
    "subordinateToBoss": 0.25,
    "peerToPeer": 0.15,
    "insideClients": 0.10,
}

TIPOS_DISPLAY = {
    "autoEvaluation": "Autoevaluación",
    "bossToSubordinate": "Jefe",
    "subordinateToBoss": "Subordinado",
    "peerToPeer": "Pares",
    "insideClients": "Cliente Interno",
}

BANDAS = [
    (100, 101, "Talento estrella", "#4B61D1"),
    (90, 100, "Alto Desempeño", "#008A4B"),
    (85, 90, "Satisfactorio", "#00B887"),
    (75, 85, "En desarrollo", "#F4B324"),
    (0, 75, "Espacio de crecimiento", "#D5005D"),
]

HOJAS_EVALUACION = ("Desempeño", "Resultado consulta", "datos")
COLUMNAS_REQUERIDAS = [
    "nombre_colaborador",
    "nombre_seccion",
    "tipo_evaluacion",
    "respuesta_valor",
]
COLUMNAS_EXPORTACION_EVALUAR = [
    "nombre_ciclo",
    "nombre_colaborador",
    "email_colaborador",
    "curp",
    "employee_id",
    "categoria",
    "pregunta_abierta",
    "nombre_seccion",
    "pregunta_texto",
    "tipo_evaluacion",
    "nombre_evaluador",
    "email_evaluador",
    "respuesta_valor",
    "calificacion_porcentaje",
]
ESCALA_DASHBOARD = [etiqueta for _, _, etiqueta, _ in BANDAS]

EXCLUIDOS_DESEMPENO = {
    "malvarado@macrotech.com.do": "Marcos Alvarado Aponte",
    "jmartinez@cimer.com.do": "Joel Martínez Croussett",
    "ananlli494@gmail.com": "Ananlli Mora Peguero",
    "asanchezmf123@gmail.com": "Andres Confesor Sánchez Montero",
    "jeovannyjmm01@gmail.com": "Jeovanny De Jesus Molina Martínez",
    "matoswaskar40@gmail.com": "Waskar Emilio Matos Pérez",
    "kcoronado@cai.com.do": "Karen Libell Coronado Paulino",
    "jvasquez@cesante.com": "Juan Vásquez",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def clasificar(puntaje: float) -> dict:
    """Devuelve etiqueta y color para un puntaje dado."""
    for lo, hi, etiqueta, color in BANDAS:
        if lo <= puntaje < hi:
            return {"etiqueta": etiqueta, "color": color}
    return {"etiqueta": "Sin clasificación", "color": "#6B7280"}


def redondear_corte_ninebox(valor: float) -> int:
    """Redondea un punto de corte positivo al entero más cercano (half-up)."""
    return int(math.floor(float(valor) + 0.5))


def corte_superior_ninebox(valor: float) -> int:
    """Define el inicio entero del nivel alto del Ninebox.

    En la escala 0-100 usada por Macrotech, el nivel alto comienza en 99.
    Los puntajes individuales conservan sus decimales, por lo que 98.9 sigue
    perteneciendo al nivel medio.
    """
    return min(100, max(99, redondear_corte_ninebox(valor)))


def limpiar_nombre_competencia(nombre: str) -> str:
    """Elimina prefijos numericos como '2.1 ' del nombre de competencia."""
    return re.sub(r"^\d+(\.\d+)?\s+", "", str(nombre).strip())


def normalizar_nombre_persona(valor: object) -> str:
    """Crea una llave de nombre tolerante a tildes y al orden de sus partes."""
    if valor is None or pd.isna(valor):
        return ""
    texto = unicodedata.normalize("NFKD", str(valor))
    texto = "".join(char for char in texto if not unicodedata.combining(char))
    tokens = re.sub(r"[^a-z0-9]+", " ", texto.casefold()).split()
    return " ".join(sorted(tokens))


def nombres_persona_equivalentes(valor_a: object, valor_b: object) -> bool:
    """Compara nombres admitiendo un único componente adicional.

    La equivalencia flexible solo aplica cuando el nombre más corto contiene
    al menos tres componentes. Así se cubren segundos nombres omitidos sin
    convertir coincidencias breves o ambiguas en emparejamientos automáticos.
    """
    nombre_a = normalizar_nombre_persona(valor_a)
    nombre_b = normalizar_nombre_persona(valor_b)
    if not nombre_a or not nombre_b:
        return False
    if nombre_a == nombre_b:
        return True

    tokens_a = Counter(nombre_a.split())
    tokens_b = Counter(nombre_b.split())
    cantidad_a = sum(tokens_a.values())
    cantidad_b = sum(tokens_b.values())
    if min(cantidad_a, cantidad_b) < 3 or abs(cantidad_a - cantidad_b) != 1:
        return False

    corto, largo = (tokens_a, tokens_b) if cantidad_a < cantidad_b else (tokens_b, tokens_a)
    return all(cantidad <= largo[token] for token, cantidad in corto.items())


def resolver_nombre_equivalente_unico(valor: object, candidatos: Iterable[object]) -> str:
    """Devuelve la llave normalizada solo cuando existe una coincidencia única."""
    nombre = normalizar_nombre_persona(valor)
    if not nombre:
        return ""
    claves = {
        clave
        for candidato in candidatos
        if (clave := normalizar_nombre_persona(candidato))
    }
    if nombre in claves:
        return nombre
    equivalentes = {
        clave for clave in claves if nombres_persona_equivalentes(nombre, clave)
    }
    return next(iter(equivalentes)) if len(equivalentes) == 1 else ""


def _clave_nombre_persona(valor: object) -> str:
    return normalizar_nombre_persona(valor)


def filtrar_excluidos_desempeno(df: pd.DataFrame) -> pd.DataFrame:
    """Retira del cálculo 360 a las personas excluidas por regla de negocio."""
    if df.empty:
        return df.copy()

    mascara = pd.Series(False, index=df.index)
    if "email_colaborador" in df.columns:
        correos = df["email_colaborador"].fillna("").astype(str).str.strip().str.casefold()
        mascara = mascara | correos.isin(EXCLUIDOS_DESEMPENO)
    if "nombre_colaborador" in df.columns:
        nombres_excluidos = {
            _clave_nombre_persona(nombre)
            for nombre in EXCLUIDOS_DESEMPENO.values()
        }
        mascara = mascara | df["nombre_colaborador"].map(
            _clave_nombre_persona
        ).isin(nombres_excluidos)
    return df.loc[~mascara].copy()


def seleccionar_competencias_resumen(
    df_competencias: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Divide fortalezas y oportunidades sin repetir competencias.

    Con menos de ocho competencias reparte el universo completo entre ambos
    lados (el lado de fortalezas recibe una adicional cuando el total es
    impar). Con ocho o más conserva el máximo visual de cuatro por lado.
    """
    if df_competencias.empty:
        vacio = df_competencias.copy()
        return vacio, vacio

    ordenadas = (
        df_competencias
        .drop_duplicates(subset=["competencia"])
        .sort_values("prom_comp", ascending=False)
        .reset_index(drop=True)
    )
    total = len(ordenadas)
    if total < 8:
        cantidad_top = (total + 1) // 2
        cantidad_fortalecer = total // 2
    else:
        cantidad_top = 4
        cantidad_fortalecer = 4

    top = ordenadas.head(cantidad_top).copy()
    fortalecer = (
        ordenadas.tail(cantidad_fortalecer)
        .sort_values("prom_comp", ascending=True)
        .copy()
        if cantidad_fortalecer
        else ordenadas.iloc[0:0].copy()
    )
    return top, fortalecer


def calcular_pesos_redistribuidos(tipos_presentes: list, weights: dict | None = None) -> dict:
    """
    Redistribuye el peso de tipos faltantes en partes iguales entre los presentes.

    Regla de negocio:
    si faltan calificaciones, sus pesos se suman, se dividen entre las
    calificaciones existentes y ese incremento se suma al peso original
    de cada calificacion existente.
    """
    weights = weights or PESOS_BASE
    tipos_unicos = list(dict.fromkeys(tipos_presentes))
    pesos_presentes = {t: weights[t] for t in tipos_unicos if t in weights and weights[t] > 0}
    if not pesos_presentes:
        raise ValueError(f"Ningun tipo reconocido en: {tipos_presentes}")
    peso_faltante = sum(
        peso for tipo, peso in weights.items()
        if peso > 0 and tipo not in pesos_presentes
    )
    incremento = peso_faltante / len(pesos_presentes)
    return {tipo: peso + incremento for tipo, peso in pesos_presentes.items()}


def _idx_escala(puntaje: float) -> int:
    for indice, (desde, hasta, _, _) in enumerate(BANDAS):
        if desde <= puntaje < hasta:
            return indice
    return len(BANDAS) - 1


# ---------------------------------------------------------------------------
# Lectura y normalizacion de datos
# ---------------------------------------------------------------------------

def normalizar_dataframe(df: pd.DataFrame, verbose: bool = True) -> pd.DataFrame:
    """
    Limpia una hoja de evaluacion y agrega 'puntaje' y 'competencia'.
    """
    df = df.copy()
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")

    faltantes = [c for c in COLUMNAS_REQUERIDAS if c not in df.columns]
    if faltantes:
        raise ValueError(f"Columnas faltantes en el Excel: {faltantes}")

    for col in [
        "nombre_colaborador",
        "nombre_seccion",
        "tipo_evaluacion",
        "nombre_evaluador",
        "respuesta_valor",
    ]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()

    df["respuesta_valor"] = pd.to_numeric(df["respuesta_valor"], errors="coerce")

    n_antes = len(df)
    df = df[df["respuesta_valor"].isin([1, 2, 3, 4, 5])].copy()
    n_descartadas = n_antes - len(df)
    if verbose and n_descartadas:
        print(f"  ! Se descartaron {n_descartadas} filas con respuesta_valor invalido.")

    df["puntaje"] = df["respuesta_valor"].map(ESCALA_TRANSFORM)
    df["competencia"] = df["nombre_seccion"].apply(limpiar_nombre_competencia)
    return df


def extraer_metadata_colaboradores(df: pd.DataFrame) -> pd.DataFrame:
    """Extrae metadatos personales de Fase I con nombres de columna estables."""
    columnas_salida = [
        "colaborador", "email_colaborador", "empresa", "pais", "area", "grupo"
    ]
    if df.empty or "nombre_colaborador" not in df.columns:
        return pd.DataFrame(columns=columnas_salida)

    alias = {
        "email_colaborador": ("email_colaborador",),
        "empresa": ("empresa",),
        "pais": ("pais", "país"),
        "area": ("area", "área"),
        "grupo": ("grupo",),
    }
    seleccion = pd.DataFrame({"colaborador": df["nombre_colaborador"]})
    for destino, candidatas in alias.items():
        origen = next((col for col in candidatas if col in df.columns), None)
        seleccion[destino] = df[origen] if origen else pd.NA

    seleccion = seleccion[seleccion["colaborador"].notna()].copy()
    for columna in columnas_salida:
        seleccion[columna] = seleccion[columna].apply(
            lambda valor: valor.strip() if isinstance(valor, str) else valor
        )

    def primer_valor(valores: pd.Series):
        validos = valores[
            valores.notna()
            & valores.astype(str).str.strip().ne("")
            & ~valores.astype(str).str.strip().str.casefold().isin(
                {"nan", "none", "n/a", "na", "-"}
            )
        ]
        return validos.iloc[0] if len(validos) else pd.NA

    return (
        seleccion.groupby("colaborador", sort=False, as_index=False)
        .agg({col: primer_valor for col in columnas_salida if col != "colaborador"})
        .reindex(columns=columnas_salida)
    )


def _clave_columna_organizacional(valor: object) -> str:
    if valor is None or pd.isna(valor):
        return ""
    texto = unicodedata.normalize("NFKD", str(valor))
    texto = "".join(char for char in texto if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", texto.casefold()).strip()


def _texto_organizacional(valor: object) -> object:
    if valor is None or pd.isna(valor):
        return pd.NA
    texto = re.sub(r"\s+", " ", str(valor)).strip()
    return texto if texto and texto.casefold() not in {"nan", "none", "n/a", "na", "-"} else pd.NA


def resolver_archivo_metadata_organizacional(ruta_fuente: str | Path) -> Path | None:
    """Localiza la base maestra opcional que contiene segmentaciones."""
    ruta = Path(ruta_fuente).resolve()
    candidatos = [
        ruta if ruta.name.casefold() == "base speedster.xlsx" else None,
        ruta.parent / "documentos_raw" / "Base Speedster.xlsx",
        ruta.parent / "Base Speedster.xlsx",
        Path(__file__).resolve().parents[1] / "documentos_raw" / "Base Speedster.xlsx",
    ]
    return next((candidato for candidato in candidatos if candidato and candidato.is_file()), None)


def leer_metadata_organizacional(ruta_fuente: str | Path) -> pd.DataFrame:
    """Lee Empresa, País, Área, Cargo y Grupo desde la base maestra Speedster."""
    columnas_salida = [
        "colaborador",
        "email_colaborador",
        "empresa",
        "pais",
        "area",
        "cargo",
        "grupo",
        "gente_a_cargo",
    ]
    ruta_metadata = resolver_archivo_metadata_organizacional(ruta_fuente)
    if ruta_metadata is None:
        return pd.DataFrame(columns=columnas_salida)

    xls = pd.ExcelFile(ruta_metadata)
    try:
        hoja = next(
            (
                nombre
                for nombre in xls.sheet_names
                if "usuarios" in _clave_columna_organizacional(nombre)
            ),
            xls.sheet_names[0],
        )
        muestra = pd.read_excel(xls, sheet_name=hoja, header=None, nrows=12)
        fila_encabezado = next(
            (
                indice
                for indice, fila in muestra.iterrows()
                if "email" in {_clave_columna_organizacional(valor) for valor in fila}
                and any(
                    _clave_columna_organizacional(valor).startswith("nombre evaluado")
                    for valor in fila
                )
            ),
            None,
        )
        if fila_encabezado is None:
            return pd.DataFrame(columns=columnas_salida)
        df = pd.read_excel(xls, sheet_name=hoja, header=int(fila_encabezado))
    finally:
        xls.close()

    claves = {columna: _clave_columna_organizacional(columna) for columna in df.columns}

    def buscar(*predicados):
        return next(
            (
                columna
                for columna, clave in claves.items()
                if any(predicado(clave) for predicado in predicados)
            ),
            None,
        )

    col_nombre = buscar(lambda clave: clave.startswith("nombre evaluado"))
    col_apellidos = buscar(lambda clave: clave.startswith("apellidos evaluado"))
    col_email = buscar(lambda clave: clave == "email")
    col_pais = buscar(lambda clave: clave.startswith("pais"))
    col_area = buscar(
        lambda clave: "unidad de negocio" in clave,
        lambda clave: clave == "area",
    )
    col_cargo = buscar(lambda clave: "rol puesto" in clave)
    col_grupo = buscar(lambda clave: "grupo ocupacional" in clave)
    col_gente = buscar(lambda clave: "gente a cargo" in clave)
    if col_nombre is None and col_email is None:
        return pd.DataFrame(columns=columnas_salida)

    nombres = df[col_nombre].map(_texto_organizacional) if col_nombre else pd.Series(pd.NA, index=df.index)
    apellidos = df[col_apellidos].map(_texto_organizacional) if col_apellidos else pd.Series(pd.NA, index=df.index)
    metadata = pd.DataFrame(index=df.index)
    metadata["colaborador"] = (
        nombres.fillna("").astype(str).str.strip()
        + " "
        + apellidos.fillna("").astype(str).str.strip()
    ).str.replace(r"\s+", " ", regex=True).str.strip()
    metadata["email_colaborador"] = (
        df[col_email].map(_texto_organizacional) if col_email else pd.NA
    )
    metadata["empresa"] = "Speedster"
    metadata["pais"] = df[col_pais].map(_texto_organizacional) if col_pais else pd.NA
    metadata["area"] = df[col_area].map(_texto_organizacional) if col_area else pd.NA
    metadata["cargo"] = df[col_cargo].map(_texto_organizacional) if col_cargo else pd.NA
    metadata["grupo"] = df[col_grupo].map(_texto_organizacional) if col_grupo else pd.NA
    metadata["gente_a_cargo"] = df[col_gente].map(_texto_organizacional) if col_gente else pd.NA
    metadata.loc[
        metadata["pais"].map(_clave_columna_organizacional).eq("republica dominicana"),
        "pais",
    ] = "República Dominicana"
    metadata = metadata[
        metadata["colaborador"].ne("") | metadata["email_colaborador"].notna()
    ].copy()
    metadata["email_colaborador"] = (
        metadata["email_colaborador"].fillna("").astype(str).str.strip().str.casefold()
    )
    return metadata.drop_duplicates(
        subset=["email_colaborador", "colaborador"],
        keep="first",
    ).reindex(columns=columnas_salida).reset_index(drop=True)


def completar_metadata_colaboradores(
    df: pd.DataFrame,
    metadata: pd.DataFrame,
    columna_nombre: str,
    columna_email: str | None = None,
) -> pd.DataFrame:
    """Completa segmentaciones por correo o por una coincidencia única de nombre."""
    resultado = df.copy()
    if resultado.empty or metadata.empty or columna_nombre not in resultado.columns:
        return resultado

    campos = ["empresa", "pais", "area", "cargo", "grupo", "gente_a_cargo"]
    for campo in campos:
        if campo not in resultado.columns:
            resultado[campo] = pd.NA
    if columna_email and columna_email not in resultado.columns:
        resultado[columna_email] = pd.NA

    meta = metadata.copy()
    meta["_match_email"] = (
        meta["email_colaborador"].fillna("").astype(str).str.strip().str.casefold()
    )
    meta["_match_nombre"] = meta["colaborador"].map(normalizar_nombre_persona)
    nombres_metadata = meta["_match_nombre"].dropna().astype(str).tolist()

    def valor_real(valor: object) -> bool:
        return pd.notna(valor) and str(valor).strip().casefold() not in {"", "nan", "none", "n/a", "na", "-"}

    for indice, fila in resultado.iterrows():
        coincidencias = pd.DataFrame()
        if columna_email:
            correo = fila.get(columna_email)
            correo_key = str(correo).strip().casefold() if valor_real(correo) else ""
            if correo_key:
                coincidencias = meta[meta["_match_email"].eq(correo_key)]
        if coincidencias.empty:
            nombre_key = resolver_nombre_equivalente_unico(
                fila.get(columna_nombre),
                nombres_metadata,
            )
            if nombre_key:
                coincidencias = meta[meta["_match_nombre"].eq(nombre_key)]
        if len(coincidencias) != 1:
            continue
        persona = coincidencias.iloc[0]
        if columna_email and not valor_real(resultado.at[indice, columna_email]):
            resultado.at[indice, columna_email] = persona.get("email_colaborador")
        for campo in campos:
            if not valor_real(resultado.at[indice, campo]) and valor_real(persona.get(campo)):
                resultado.at[indice, campo] = persona.get(campo)
    return resultado


def leer_excel(ruta: str | Path, sheet_name: str | None = "Resultado consulta") -> pd.DataFrame:
    """
    Lee el Excel de evaluacion y devuelve DataFrame limpio.

    Prioriza 'Desempeño' o 'Resultado consulta' y también acepta archivos
    procesados con hoja 'datos'.
    """
    xls = pd.ExcelFile(ruta)
    hojas = list(xls.sheet_names)

    candidatas = []
    if sheet_name:
        candidatas.append(sheet_name)
    candidatas.extend(h for h in HOJAS_EVALUACION if h not in candidatas)
    candidatas.extend(h for h in hojas if h not in candidatas)

    errores = {}
    for hoja in candidatas:
        if hoja not in hojas:
            continue
        df_hoja = pd.read_excel(xls, sheet_name=hoja, dtype=str)
        try:
            return normalizar_dataframe(df_hoja)
        except ValueError as exc:
            errores[hoja] = str(exc)

    detalle = "; ".join(f"{hoja}: {err}" for hoja, err in errores.items())
    raise ValueError(
        "No se encontro una hoja de evaluacion valida. "
        f"Hojas disponibles: {hojas}. {detalle}"
    )


def leer_exportacion_dashboard(ruta: str | Path) -> pd.DataFrame:
    """Lee y valida el exporte oficial de Fase I generado por Evaluar.com."""
    xls = pd.ExcelFile(ruta)
    hoja = next(
        (nombre for nombre in ("Desempeño", "Resultado consulta") if nombre in xls.sheet_names),
        None,
    )
    if hoja is None:
        raise ValueError(
            "El archivo no corresponde al exporte oficial de Fase I: "
            "debe contener la hoja 'Desempeño'."
        )

    df = pd.read_excel(xls, sheet_name=hoja, dtype=str)
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")

    faltantes = [col for col in COLUMNAS_EXPORTACION_EVALUAR if col not in df.columns]
    if faltantes:
        raise ValueError(
            "El exporte de Evaluar.com esta incompleto. "
            f"Columnas faltantes: {', '.join(faltantes)}."
        )
    if df.empty:
        raise ValueError(f"La hoja '{hoja}' no contiene registros.")

    abiertas = df["pregunta_abierta"].fillna("").str.strip().str.upper().isin(
        ["SI", "SÍ", "YES", "TRUE", "1"]
    )
    filas_abiertas = int(abiertas.sum())
    df = df.loc[~abiertas].copy()

    campos_clave = [
        "nombre_ciclo",
        "nombre_colaborador",
        "nombre_seccion",
        "pregunta_texto",
        "tipo_evaluacion",
        "respuesta_valor",
    ]
    vacios = {
        col: int((df[col].isna() | df[col].fillna("").str.strip().eq("")).sum())
        for col in campos_clave
    }
    vacios = {col: cantidad for col, cantidad in vacios.items() if cantidad}
    if vacios:
        detalle = ", ".join(f"{col}: {cantidad}" for col, cantidad in vacios.items())
        raise ValueError(f"Hay campos obligatorios vacios en el exporte ({detalle}).")

    respuestas = pd.to_numeric(df["respuesta_valor"], errors="coerce")
    invalidas = ~respuestas.isin([1, 2, 3, 4, 5])
    if invalidas.any():
        raise ValueError(
            f"Hay {int(invalidas.sum())} respuestas fuera de la escala permitida 1-5."
        )

    tipos = set(df["tipo_evaluacion"].str.strip().unique())
    desconocidos = sorted(tipos - set(PESOS_BASE))
    if desconocidos:
        raise ValueError(
            "El archivo contiene tipos de evaluacion no reconocidos: "
            + ", ".join(desconocidos)
        )

    duplicadas = int(df.duplicated().sum())
    if duplicadas:
        raise ValueError(f"El exporte contiene {duplicadas} filas duplicadas.")

    normalizado = normalizar_dataframe(df, verbose=False)
    normalizado.attrs["filas_preguntas_abiertas_omitidas"] = filas_abiertas
    return normalizado


# ---------------------------------------------------------------------------
# Motor para informes PDF
# ---------------------------------------------------------------------------

def _calcular_competencias_ponderadas(
    df: pd.DataFrame,
    weights: dict | None = None,
) -> pd.DataFrame:
    """Calcula competencias sin redondeos intermedios para todas las salidas."""
    weights = weights or PESOS_BASE
    tipos_activos = {t: w for t, w in weights.items() if w > 0}

    paso1 = (
        df.groupby(["nombre_colaborador", "competencia", "tipo_evaluacion"])
        ["puntaje"]
        .mean()
        .reset_index()
        .rename(columns={"puntaje": "prom_items"})
    )

    registros = []
    for (col, comp), grp in paso1.groupby(["nombre_colaborador", "competencia"]):
        presentes = [t for t in tipos_activos if t in grp["tipo_evaluacion"].values]
        if not presentes:
            continue
        pesos_redistribuidos = calcular_pesos_redistribuidos(presentes, weights)
        puntaje = 0.0
        desglose = {}
        for tipo in presentes:
            valor = grp.loc[grp["tipo_evaluacion"] == tipo, "prom_items"].values[0]
            puntaje += valor * pesos_redistribuidos[tipo]
            desglose[tipo] = valor
        registros.append({
            "colaborador": col,
            "competencia": comp,
            "puntaje": puntaje,
            **{f"tipo_{tipo}": desglose.get(tipo) for tipo in tipos_activos},
        })

    return pd.DataFrame(registros)


def _calcular_globales(df_comp: pd.DataFrame) -> pd.DataFrame:
    """Promedia competencias conservando la misma precisión en cada superficie."""
    return (
        df_comp.groupby("colaborador")["puntaje"]
        .mean()
        .reset_index()
        .rename(columns={"puntaje": "global"})
        .sort_values("global", ascending=False)
    )


def calcular_colaborador(df_col: pd.DataFrame) -> dict:
    """
    Calcula el resultado individual de un colaborador.
    """
    df_col = normalizar_dataframe(df_col, verbose=False) if "puntaje" not in df_col.columns else df_col.copy()
    competencias_unicas = sorted(df_col["competencia"].unique())
    tipos_presentes_global = df_col["tipo_evaluacion"].unique().tolist()
    df_comp_calculo = _calcular_competencias_ponderadas(df_col)
    puntajes_comp_sin_redondear = (
        df_comp_calculo.set_index("competencia")["puntaje"].to_dict()
    )

    resultados_competencias = {}

    for competencia in competencias_unicas:
        df_comp = df_col[df_col["competencia"] == competencia]

        puntaje_por_tipo_sin_redondear = {}
        for tipo in df_comp["tipo_evaluacion"].unique():
            items = df_comp[df_comp["tipo_evaluacion"] == tipo]["puntaje"]
            puntaje_por_tipo_sin_redondear[tipo] = float(items.mean())

        tipos_en_comp = list(puntaje_por_tipo_sin_redondear.keys())
        pesos = calcular_pesos_redistribuidos(tipos_en_comp)

        puntaje_comp_sin_redondear = puntajes_comp_sin_redondear[competencia]
        puntaje_comp = round(puntaje_comp_sin_redondear, 2)

        resultados_competencias[competencia] = {
            "puntaje": puntaje_comp,
            "clasificacion": clasificar(puntaje_comp_sin_redondear),
            "desglose_tipo": {
                TIPOS_DISPLAY.get(t, t): round(puntaje_por_tipo_sin_redondear[t], 2)
                for t in PESOS_BASE
                if t in puntaje_por_tipo_sin_redondear
            },
            "pesos_aplicados": {
                TIPOS_DISPLAY.get(t, t): round(pesos[t] * 100, 1)
                for t in pesos
            },
        }

    puntaje_global_sin_redondear = float(
        _calcular_globales(df_comp_calculo)["global"].iloc[0]
    )
    puntaje_global = round(puntaje_global_sin_redondear, 2)

    desglose_global = {}
    for tipo in PESOS_BASE:
        items = df_col[df_col["tipo_evaluacion"] == tipo]["puntaje"]
        if len(items) > 0:
            desglose_global[TIPOS_DISPLAY[tipo]] = round(float(items.mean()), 2)

    pesos_globales = calcular_pesos_redistribuidos(tipos_presentes_global)

    return {
        "puntaje_global": puntaje_global,
        "clasificacion": clasificar(puntaje_global_sin_redondear),
        "competencias": resultados_competencias,
        "desglose_global": desglose_global,
        "pesos_aplicados": {
            TIPOS_DISPLAY.get(t, t): round(pesos_globales[t] * 100, 1)
            for t in pesos_globales
        },
        "tipos_presentes": [TIPOS_DISPLAY.get(t, t) for t in tipos_presentes_global],
        "n_items": len(df_col),
    }


def calcular_todos(df: pd.DataFrame) -> dict:
    """
    Ejecuta el calculo para todos los colaboradores.
    Retorna dict: {nombre_colaborador: resultado}.
    """
    df = normalizar_dataframe(df, verbose=False) if "puntaje" not in df.columns else df.copy()
    df = filtrar_excluidos_desempeno(df)
    resultados = {}
    for nombre, grupo in df.groupby("nombre_colaborador"):
        print(f"  -> Calculando: {nombre}")
        resultados[nombre] = calcular_colaborador(grupo)
    return resultados


# ---------------------------------------------------------------------------
# Motor para dashboard agregado
# ---------------------------------------------------------------------------

def calcular_items(df: pd.DataFrame, weights: dict | None = None) -> pd.DataFrame:
    """Calcula el puntaje ponderado por ítem para el conjunto de filas recibido."""
    df = normalizar_dataframe(df, verbose=False) if "puntaje" not in df.columns else df.copy()
    df = filtrar_excluidos_desempeno(df)
    weights = weights or PESOS_BASE
    tipos_activos = {tipo: peso for tipo, peso in weights.items() if peso > 0}

    paso_item = (
        df.groupby(["competencia", "pregunta_texto", "tipo_evaluacion"])["puntaje"]
        .mean()
        .reset_index()
        .rename(columns={"puntaje": "prom_item_tipo"})
    )

    registros = []
    for (competencia, item), grupo in paso_item.groupby(["competencia", "pregunta_texto"]):
        presentes = [tipo for tipo in tipos_activos if tipo in grupo["tipo_evaluacion"].values]
        if not presentes:
            continue
        pesos_redistribuidos = calcular_pesos_redistribuidos(presentes, weights)
        puntaje = sum(
            grupo.loc[grupo["tipo_evaluacion"] == tipo, "prom_item_tipo"].iloc[0]
            * pesos_redistribuidos[tipo]
            for tipo in presentes
        )
        registros.append({"competencia": competencia, "item": item, "puntaje": puntaje})

    if not registros:
        return pd.DataFrame(columns=["competencia", "item", "puntaje"])
    return pd.DataFrame(registros).sort_values("puntaje", ascending=False)


def calcular_dashboard(df: pd.DataFrame, weights: dict | None = None) -> dict:
    """
    Calcula los indicadores agregados usados por dashboard_360.py.
    """
    df = normalizar_dataframe(df, verbose=False) if "puntaje" not in df.columns else df.copy()
    df = filtrar_excluidos_desempeno(df)
    weights = weights or PESOS_BASE
    tipos_activos = {t: w for t, w in weights.items() if w > 0}

    df_comp = _calcular_competencias_ponderadas(df, weights)
    if df_comp.empty:
        raise ValueError("No hay datos validos para calcular indicadores.")

    df_global = _calcular_globales(df_comp)

    df_comp_prom = (
        df_comp.groupby("competencia")["puntaje"]
        .mean()
        .reset_index()
        .rename(columns={"puntaje": "prom_comp"})
        .sort_values("prom_comp", ascending=False)
    )

    rel_prom = {}
    for tipo in tipos_activos:
        col_t = f"tipo_{tipo}"
        if col_t in df_comp.columns:
            vals = df_comp[col_t].dropna()
            if len(vals):
                rel_prom[tipo] = vals.mean()

    comp_rel = {}
    for tipo in tipos_activos:
        col_t = f"tipo_{tipo}"
        if col_t in df_comp.columns:
            comp_rel[tipo] = (
                df_comp.groupby("competencia")[col_t]
                .mean()
                .dropna()
                .to_dict()
            )

    df_items = calcular_items(df, weights)

    df_global["escala_idx"] = df_global["global"].apply(_idx_escala)
    df_global["escala"] = df_global["escala_idx"].apply(lambda i: ESCALA_DASHBOARD[i])

    ciclo = df["nombre_ciclo"].iloc[0] if "nombre_ciclo" in df.columns else "Evaluacion 360"

    return dict(
        ciclo=ciclo,
        resumen_fuente={
            "filas": len(df),
            "colaboradores": df["nombre_colaborador"].nunique(),
            "competencias": df["competencia"].nunique(),
            "items": df["pregunta_texto"].nunique(),
            "preguntas_abiertas_omitidas": df.attrs.get("filas_preguntas_abiertas_omitidas", 0),
        },
        df_global=df_global,
        df_comp=df_comp,
        df_comp_prom=df_comp_prom,
        rel_prom=rel_prom,
        comp_rel=comp_rel,
        df_items=df_items,
        df_fuente=df,
        tipos_activos=tipos_activos,
        colaboradores=df_global["colaborador"].tolist(),
        competencias=df_comp_prom["competencia"].tolist(),
    )


# ---------------------------------------------------------------------------
# Validacion por consola
# ---------------------------------------------------------------------------

def imprimir_resultado(nombre: str, resultado: dict):
    """Imprime el resultado de un colaborador de forma legible."""
    sep = "-" * 70
    print(f"\n{sep}")
    print(f"  COLABORADOR: {nombre}")
    print(
        f"  Puntaje global: {resultado['puntaje_global']} "
        f"-> {resultado['clasificacion']['etiqueta']}"
    )
    print(f"  Items procesados: {resultado['n_items']}")

    print("\n  Pesos aplicados:")
    for tipo, peso in resultado["pesos_aplicados"].items():
        print(f"    {tipo:<25} {peso}%")

    print("\n  Desglose global por tipo de evaluador:")
    for tipo, pts in resultado["desglose_global"].items():
        print(f"    {tipo:<25} {pts}")

    print("\n  Resultados por competencia:")
    print(f"    {'Competencia':<40} {'Puntaje':>8}  {'Banda'}")
    print(f"    {'-'*40} {'-'*8}  {'-'*20}")
    for comp, datos in resultado["competencias"].items():
        print(f"    {comp:<40} {datos['puntaje']:>8}  {datos['clasificacion']['etiqueta']}")
        for tipo, pts in datos["desglose_tipo"].items():
            print(f"      {'- ' + tipo:<40} {pts:>8}")


if __name__ == "__main__":
    import sys

    carpeta = Path("datos")
    excels = list(carpeta.glob("*.xlsx")) if carpeta.exists() else []

    if not excels:
        print("ERROR: No se encontro ningun .xlsx en la carpeta 'datos/'")
        print("       Coloca el archivo exportado de Evaluar.com ahi y vuelve a ejecutar.")
        sys.exit(1)

    ruta = excels[0]
    print(f"Leyendo: {ruta}")

    df_eval = leer_excel(ruta)
    print(f"Filas validas: {len(df_eval)}")
    print(f"Colaboradores: {df_eval['nombre_colaborador'].nunique()}")

    resultados = calcular_todos(df_eval)
    for nombre, resultado in resultados.items():
        imprimir_resultado(nombre, resultado)

    print(f"\n{'-'*70}")
    print("Calculo completado sin errores.")
