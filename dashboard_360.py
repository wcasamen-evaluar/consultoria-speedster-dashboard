"""
Dashboard de EvaluaciÃ³n 360Â° â€” Evaluar.com
==========================================
EjecuciÃ³n:
    pip install streamlit pandas openpyxl plotly
    streamlit run dashboard_360.py

â•â• CONFIGURACIÃ“N DEL PROYECTO â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
  Las dos constantes de abajo son los Ãºnicos valores que
  se deben editar al adaptar el dashboard a un nuevo proyecto.
â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
"""

import base64
import html as html_lib
import re
import unicodedata
from collections.abc import Mapping
from pathlib import Path

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

from reporte import calculos as motor_360
from reporte import potencial as motor_potencial
from reporte import objetivos as motor_objetivos
from reporte import integrado as motor_integrado
from reporte import db as data_db


SPEEDSTER_LOGO = Path(__file__).resolve().parent / "logos" / "speedster_logo.png"
ARCHIVO_BASE = next(
    Path(__file__).parent.glob("Fase_I_Evaluaci*n_360__180__90__copia_.xlsx"),
    Path(__file__).with_name("Fase_I_Evaluación_360__180__90__copia_.xlsx"),
)
VERSION_CARGA_BASE = 10
VERSION_CARGA_DB = 11

EXCLUIDOS_DESEMPENO_EMAILS = {
    "malvarado@macrotech.com.do",
    "jmartinez@cimer.com.do",
    "ananlli494@gmail.com",
    "asanchezmf123@gmail.com",
    "jeovannyjmm01@gmail.com",
    "matoswaskar40@gmail.com",
    "kcoronado@cai.com.do",
    "jvasquez@cesante.com",
}

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# CONFIGURACIÃ“N DEL PROYECTO â€” editar aquÃ­ si cambia el proyecto
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

# TransformaciÃ³n de respuesta (escala 1-5) a puntaje interno
MAPA_PUNTAJE = motor_360.ESCALA_TRANSFORM

# Pesos de ponderaciÃ³n por tipo de relaciÃ³n (deben sumar 1.0)
PESOS_PONDERACION = motor_360.PESOS_BASE.copy()
assert abs(sum(PESOS_PONDERACION.values()) - 1.0) < 1e-9, "Los pesos deben sumar 100%"

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# CONFIGURACIÃ“N DE PÃGINA
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
st.set_page_config(
    page_title="Evaluaci\u00f3n 360 | Evaluar",
    page_icon="ðŸ“Š",
    layout="wide",
    initial_sidebar_state="expanded",
)

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# ESTILOS EVALUAR
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
EVALUAR_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
}

/* Topbar */
.ev-topbar {
    background: #1a1a3e;
    padding: 14px 24px;
    border-radius: 10px;
    margin-bottom: 20px;
    display: flex;
    align-items: center;
    justify-content: space-between;
}
.ev-logo {
    font-size: 24px;
    font-weight: 700;
    color: white;
    letter-spacing: -0.5px;
}
.ev-logo-v {
    background: linear-gradient(90deg, #c13bc4, #f47c3c);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}
.ev-cycle {
    background: rgba(255,255,255,0.15);
    color: white;
    font-size: 12px;
    padding: 4px 14px;
    border-radius: 20px;
    font-weight: 500;
}
.ev-client-logos {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    gap: 12px;
    flex-wrap: wrap;
    min-width: 0;
}
.ev-client-logo-card {
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 58px;
    padding: 3px 14px;
    background: #ffffff;
    border: 1px solid rgba(255,255,255,0.75);
    border-radius: 10px;
    box-shadow: 0 4px 14px rgba(0,0,0,0.12);
}
.ev-client-logo {
    height: 54px;
    width: auto;
    max-width: 300px;
    object-fit: contain;
    padding: 2px 0;
}
@media (max-width: 900px) {
    .ev-topbar {
        align-items: flex-start;
        gap: 12px;
        flex-direction: column;
    }
    .ev-client-logos {
        justify-content: flex-start;
    }
    .ev-client-logo {
        height: 44px;
        max-width: 240px;
    }
    .ev-client-logo-card {
        min-height: 48px;
        padding: 2px 10px;
    }
}

/* KPI cards */
.kpi-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
    margin-bottom: 20px;
}
.kpi-card {
    background: white;
    border: 0.5px solid #e8e4f4;
    border-radius: 10px;
    padding: 16px;
}
.kpi-label {
    font-size: 11px;
    color: #6b6b8a;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.4px;
    margin-bottom: 6px;
}
.kpi-value {
    font-size: 28px;
    font-weight: 600;
    color: #1a1a3e;
}
.kpi-value.gradient {
    background: linear-gradient(135deg, #6c3fc5, #e8357a);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}
.kpi-value.green  { color: #185fa5; }  /* Alto desempeÃ±o = azul */
.kpi-sub { font-size: 11px; color: #6b6b8a; margin-top: 2px; }

/* Score chips â€” colores por escala de desempeÃ±o */
.chip {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 5px;
    font-size: 12px;
    font-weight: 600;
}
/* Alto desempeÃ±o  â‰¥ 90 â†’ azul */
.chip-alto  { background: #ddeeff; color: #0c447c; }
/* Satisfactorio  80â€“90 â†’ verde */
.chip-sat   { background: #e1f5ee; color: #085041; }
/* Bajo           70â€“80 â†’ Ã¡mbar */
.chip-bajo  { background: #faeeda; color: #633806; }
/* Insatisfactorio < 70 â†’ rojo */
.chip-insat { background: #fcebeb; color: #791f1f; }

/* SecciÃ³n */
.section-header {
    margin-bottom: 16px;
    padding-bottom: 10px;
    border-bottom: 1.5px solid #e8e4f4;
}
.section-title {
    font-size: 18px;
    font-weight: 600;
    color: #1a1a3e;
}
.section-sub {
    font-size: 13px;
    color: #6b6b8a;
    margin-top: 2px;
}

/* Tablas */
.ev-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
}
.ev-table th {
    font-weight: 600;
    color: #6b6b8a;
    padding: 6px 10px;
    text-align: left;
    border-bottom: 0.5px solid #e8e4f4;
    background: #f8f7fc;
}
.ev-table td {
    padding: 7px 10px;
    border-bottom: 0.5px solid #e8e4f4;
    color: #1a1a3e;
}
.ev-table tr:last-child td { border-bottom: none; }
.ev-table tr:hover td { background: #f5f0ff; }
.ev-items-group td {
    padding: 10px;
    background: #f0ebff;
    border-top: 1px solid #d9cff2;
    border-bottom: 1px solid #d9cff2;
}
.ev-items-group:first-child td { border-top: none; }
.ev-items-group:hover td { background: #f0ebff !important; }
.ev-items-group-content {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
}
.ev-items-group-name {
    color: #4f2c99;
    font-size: 13px;
    font-weight: 700;
}
.ev-items-group-meta {
    color: #6b6b8a;
    font-size: 11px;
    white-space: nowrap;
}
.ev-items-table th:last-child,
.ev-items-table td:last-child {
    width: 92px;
    text-align: right;
}

/* Sidebar */
.ev-sidebar-title {
    font-size: 13px;
    font-weight: 600;
    color: #1a1a3e;
    margin-bottom: 4px;
}

/* Ocultar elementos de Streamlit */
#MainMenu, footer, header { visibility: hidden; }
/* Espacio de seguridad para que los distintivos flotantes de Community Cloud
   no cubran los últimos valores o filas del dashboard. */
.block-container { padding-top: 1rem; padding-bottom: 5rem; }

/* Contenedor de filtros globales */
.ev-filter-container {
    background: white;
    border: 0.5px solid #e8e4f4;
    border-left: 3px solid #6c3fc5;
    border-radius: 10px;
    padding: 10px 16px 6px;
    margin-bottom: 8px;
}
.ev-filter-header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 2px;
}
.ev-filter-icon {
    font-size: 13px;
    color: #6c3fc5;
}
.ev-filter-title {
    font-size: 12px;
    font-weight: 600;
    color: #1a1a3e;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
.ev-filter-hint {
    font-size: 11px;
    color: #9b9bb5;
    margin-left: 4px;
}
.ev-filter-tag {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    background: #f0ebff;
    color: #6c3fc5;
    font-size: 12px;
    font-weight: 500;
    padding: 3px 10px;
    border-radius: 20px;
    margin: 2px;
}

/* Navegacion y filtros fijos sin depender del DOM interno de Streamlit */
.st-key-sticky_phase_nav {
    position: sticky;
    top: 0;
    z-index: 1003;
    background: white;
    padding-top: 4px;
    padding-bottom: 8px;
    box-shadow: 0 8px 12px -14px rgba(26, 26, 62, 0.28);
}
.st-key-sticky_filtros_desempeno,
.st-key-sticky_filtros_potencial {
    position: sticky;
    top: 58px;
    z-index: 1002;
    background: white;
    padding-top: 4px;
    padding-bottom: 6px;
    box-shadow: 0 8px 12px -12px rgba(26, 26, 62, 0.35);
}
.st-key-sticky_fase1_subnav {
    position: sticky;
    top: 148px;
    z-index: 1001;
    background: white;
    padding-top: 6px;
    padding-bottom: 8px;
    box-shadow: 0 8px 12px -12px rgba(26, 26, 62, 0.28);
}
.sticky-controls-spacer {
    height: 6px;
}
@media (max-width: 768px) {
    .st-key-sticky_filtros_desempeno,
    .st-key-sticky_filtros_potencial {
        top: 70px;
    }
    .st-key-sticky_fase1_subnav {
        top: 170px;
    }
}

/* Sidebar oscuro estilo Evaluar */
[data-testid="stSidebar"] {
    background: #1a1a3e !important;
}
/* Textos generales del sidebar en blanco */
[data-testid="stSidebar"] .stMarkdown p,
[data-testid="stSidebar"] .stMarkdown strong,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] .stMarkdown div {
    color: rgba(255,255,255,0.85) !important;
}
[data-testid="stSidebar"] hr {
    border-color: rgba(255,255,255,0.12) !important;
}
/* File uploader: fondo blanco y textos oscuros */
[data-testid="stSidebar"] [data-testid="stFileUploader"] {
    background: white;
    border-radius: 8px;
    padding: 6px;
}
[data-testid="stSidebar"] [data-testid="stFileUploader"] * {
    color: #1a1a3e !important;
}
[data-testid="stSidebar"] [data-testid="stFileUploader"] small,
[data-testid="stSidebar"] [data-testid="stFileUploader"] span,
[data-testid="stSidebar"] [data-testid="stFileUploader"] p {
    color: #4a4a6a !important;
}
/* BotÃ³n calcular con degradado Evaluar */
[data-testid="stSidebar"] button[kind="primary"] {
    background: linear-gradient(135deg, #c13bc4, #f47c3c) !important;
    border: none !important;
    color: white !important;
    font-weight: 600 !important;
}
[data-testid="stSidebar"] button[kind="primary"]:hover {
    opacity: 0.9;
}
/* LÃ­nea decorativa degradada bajo el logo */
.ev-sidebar-accent {
    height: 2px;
    background: linear-gradient(90deg, #c13bc4, #f47c3c);
    border-radius: 2px;
    margin: 12px 0 16px;
}

/* Navegador de fases â€” estilo custom */
.ev-nav {
    display: flex;
    gap: 6px;
    background: #1a1a3e;
    border-radius: 12px;
    padding: 8px;
    margin-bottom: 20px;
}
.ev-nav-btn {
    flex: 1;
    padding: 10px 12px;
    border-radius: 8px;
    border: none;
    cursor: pointer;
    font-family: 'DM Sans', sans-serif;
    font-size: 13px;
    font-weight: 600;
    color: rgba(255,255,255,0.55);
    background: transparent;
    transition: all 0.15s;
    text-align: center;
    white-space: nowrap;
}
.ev-nav-btn:hover {
    color: rgba(255,255,255,0.85);
    background: rgba(255,255,255,0.08);
}
.ev-nav-btn.active {
    background: white;
    color: #1a1a3e;
    box-shadow: 0 2px 8px rgba(0,0,0,0.15);
}

/* Bloques compactos para vistas con muchos colaboradores */
.ev-scroll-table {
    max-height: 360px;
    overflow-y: auto;
    border: 0.5px solid #e8e4f4;
    border-radius: 8px;
}
.ev-scroll-table table {
    margin: 0;
}
.ev-scroll-table thead th {
    position: sticky;
    top: 0;
    z-index: 1;
}
.ev-mini-note {
    color: #6b6b8a;
    font-size: 12px;
    margin: -4px 0 10px;
}
</style>
"""

st.markdown(EVALUAR_CSS, unsafe_allow_html=True)

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# CONSTANTES
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
TIPO_LABEL = {
    "autoEvaluation":    "Autoevaluaci\u00f3n",
    "bossToSubordinate": "Jefe",
    "subordinateToBoss": "Subordinado",
    "peerToPeer":        "Pares",
    "insideClients":     "Cliente interno",
}

ESCALA_RANGOS = [
    (100, 101, "Talento estrella", "#4B61D1"),
    (90, 100, "Alto Desempeño", "#008A4B"),
    (85, 90, "Satisfactorio", "#00B887"),
    (75, 85, "En desarrollo", "#F4B324"),
    (0, 75, "Espacio de crecimiento", "#D5005D"),
]
ESCALA_LABELS = [etiqueta for _, _, etiqueta, _ in ESCALA_RANGOS]
ESCALA_COLORES = [color for _, _, _, color in ESCALA_RANGOS]
ESCALA_FONDO = ["#e8eafd", "#d9f2e5", "#d8f7ee", "#fff0c9", "#fce0ec"]
ESCALA_TEXTO = ["#2f3ea0", "#006b3a", "#00795f", "#7a5200", "#8a003c"]
ESCALA_MIN = [desde for desde, _, _, _ in ESCALA_RANGOS]

OBJETIVOS_ESCALA_RANGOS = (
    {"label": "Talento estrella", "desde": 100, "hasta": 101, "color": "#4b61d1"},
    {"label": "Alto Desempeño", "desde": 90, "hasta": 100, "color": "#008a4b"},
    {"label": "Satisfactorio", "desde": 85, "hasta": 90, "color": "#00b887"},
    {"label": "En desarrollo", "desde": 75, "hasta": 85, "color": "#f4b324"},
    {"label": "Espacio de crecimiento", "desde": 0, "hasta": 75, "color": "#d5005d"},
)
OBJETIVOS_ESCALA_ORDEN = [banda["label"] for banda in OBJETIVOS_ESCALA_RANGOS]
OBJETIVOS_ESCALA_COLORES = {
    banda["label"]: banda["color"]
    for banda in OBJETIVOS_ESCALA_RANGOS
}

COLORES_TIPO = {
    "autoEvaluation":    "#6c3fc5",
    "bossToSubordinate": "#e8357a",
    "subordinateToBoss": "#f47c3c",
    "peerToPeer":        "#185fa5",
    "insideClients":     "#1d9e75",
}

PLOTLY_LAYOUT = dict(
    font_family="DM Sans",
    plot_bgcolor="white",
    paper_bgcolor="white",
    margin=dict(l=10, r=10, t=30, b=10),
)

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# HELPERS
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def clean_comp_name(s: str) -> str:
    """Elimina el prefijo numÃ©rico del nombre de secciÃ³n (ej: '2.1 ')."""
    import re
    return re.sub(r"^\d+\.\d+\s*", "", str(s)).strip()


def get_escala(v: float) -> int:
    for indice, (desde, hasta, _, _) in enumerate(ESCALA_RANGOS):
        if desde <= v < hasta:
            return indice
    return len(ESCALA_RANGOS) - 1


def score_color(v: float) -> str:
    return ESCALA_COLORES[get_escala(v)]


def chip_html(v: float) -> str:
    i = get_escala(v)
    bg, fg = ESCALA_FONDO[i], ESCALA_TEXTO[i]
    return f'<span class="chip" style="background:{bg};color:{fg}">{v:.2f}</span>'


def formato_peso(peso: float) -> str:
    return f"{peso * 100:.0f}%" if abs(peso * 100 - round(peso * 100)) < 0.01 else f"{peso * 100:.1f}%"


def etiquetas_tipo_con_pesos(df_comp: pd.DataFrame, tipos: list[str]) -> dict:
    del df_comp
    return {
        tipo: (
            f"{TIPO_LABEL.get(tipo, tipo)} ({formato_peso(PESOS_PONDERACION[tipo])})"
            if tipo in PESOS_PONDERACION
            else TIPO_LABEL.get(tipo, tipo)
        )
        for tipo in tipos
    }


def escala_label(v: float) -> str:
    return ESCALA_LABELS[get_escala(v)]


def escala_objetivos_label(v: float) -> str:
    puntaje = pd.to_numeric(pd.Series([v]), errors="coerce").iloc[0]
    if pd.isna(puntaje):
        return ""
    for banda in OBJETIVOS_ESCALA_RANGOS:
        if banda["desde"] <= puntaje < banda["hasta"]:
            return banda["label"]
    return ""


POTENCIAL_ESCALAS = motor_potencial.NIVELES_COMPETENCIAS
POTENCIAL_LIMITES = (80, 85)
POTENCIAL_COLORES = motor_potencial.COLORES_NIVELES_COMPETENCIAS
POTENCIAL_RANGOS = motor_potencial.RANGOS_NIVELES_COMPETENCIAS
DISC_PALETA = [
    "#185fa5", "#1d9e75", "#e6a700", "#d95f59", "#7c5cc4",
    "#285b78", "#f47c3c", "#6c3fc5", "#2f9f8f", "#b64e82",
]
IQ_PALETA = ["#285b78", "#3f7ee8", "#1d9e75", "#e6a700", "#f47c3c", "#d95f59", "#7c5cc4"]


def escala_potencial_label(valor: object) -> str:
    return motor_potencial.clasificar_nivel_competencias(valor)


CURVA_DESARROLLO_DESCRIPCIONES = {
    10: "Extremadamente desarrollada",
    9: "Muy desarrollada",
    8: "Desarrollada",
    7: "Sobre la media",
    6: "Medio-Superior",
    5: "Medio",
    4: "Medio Inferior",
    3: "Poco desarrollada",
    2: "Muy poco desarrollada",
    1: "Casi Inexistente",
    0: "Inexistente",
}
def reparar_texto(texto: object) -> str:
    if texto is None or pd.isna(texto):
        return ""
    valor = str(texto)
    if any(marca in valor for marca in ("Ã", "Â", "â")):
        try:
            valor = valor.encode("latin1").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            pass
    return valor


def clave_texto(texto: object) -> str:
    valor = reparar_texto(texto)
    valor = unicodedata.normalize("NFKD", valor)
    valor = "".join(ch for ch in valor if not unicodedata.combining(ch))
    valor = re.sub(r"[^a-zA-Z0-9]+", " ", valor).strip().casefold()
    return re.sub(r"\s+", " ", valor)


ORDEN_VALORES_POTENCIAL = [
    "Cultura Digital (Habilidad Digital)",
    "Alta Energía y dinamismo",
    "Ética profesional",
    "Proactividad",
    "Escucha activa",
    "Administración del tiempo",
    "Orden y la calidad (QA)",
    "Trabajo sin supervisión",
    "Responsabilidad",
    "Flexibilidad y Adaptabilidad",
    "Agresividad comercial (tipo cazador)",
    "Relaciones públicas",
    "Empatía",
    "Gestión de conflictos",
    "Orientación y adaptabilidad a las ventas",
    "Colaboración",
    "Inteligencia Emocional",
    "Gestión del riesgo/seguridad",
    "Trabajo en equipo",
    "Integridad",
    "Cumplimiento de Normas (Compliance)",
    "Construcción del conocimiento en equipo",
    "Orientación al Cliente",
    "Comunicación efectiva",
    "Habilidades de contacto",
    "Orientación / Asesoramiento",
    "Calidad del trabajo",
    "Negociación efectiva",
    "Discernimiento y criterio",
    "Escrupulosidad/Minuciosidad",
    "Administración de procesos",
    "Credibilidad técnica",
    "Productividad",
    "Búsqueda de datos e información",
    "Desarrollo de relaciones",
    "Resolución de problemas",
    "Gestión operativa",
    "Capacidad de planificación",
    "Trabajo bajo presión",
    "Impacto e influencia",
    "Iniciativa",
    "Pensamiento Analítico",
    "Capacidad de Gestión",
    "Orientación al Logro",
    "Asertividad",
    "Mejora continua",
    "Potencial de liderazgo",
    "Visión del Negocio",
    "Liderazgo ORIENTATIVO",
    "Didáctica",
    "Creatividad",
    "Innovación",
    "Pensamiento estratégico",
    "Desarrollo de equipo",
    "Autocontrol",
    "Liderazgo FACILITADOR",
    "Desarrollo de personas",
    "Gestión del riesgo",
    "Creación de equipos de alto rendimiento",
    "Toma de riesgos y decisiones",
    "Gestión estratégica del talento humano",
]


def color_valor_potencial(valor: float, limites: tuple[float, float]) -> tuple[str, str]:
    if pd.isna(valor):
        return "#f3f4f6", "#6b7280"
    if valor < limites[0]:
        return "#fcebeb", "#791f1f"
    if valor < limites[1]:
        return "#fff3cd", "#633806"
    return "#e1f5ee", "#085041"


def fig_valores_potencial(df: pd.DataFrame, limites: tuple[float, float]) -> go.Figure:
    datos = df[df["puntaje"].notna()].copy()
    datos["competencia"] = datos["competencia"].map(reparar_texto)
    altura = max(520, len(datos) * 24)
    datos["color_barra"] = datos["puntaje"].apply(
        lambda valor: "#d94a45" if valor < limites[0] else "#f0c419" if valor < limites[1] else "#36a65c"
    )
    fig = go.Figure(go.Bar(
        x=datos["puntaje"],
        y=datos["competencia"],
        orientation="h",
        marker=dict(
            color=datos["color_barra"],
            line=dict(color="rgba(26,26,62,0.18)", width=0.6),
        ),
        text=datos["puntaje"].map(lambda valor: f"{valor:.2f}%"),
        textposition="outside",
        cliponaxis=False,
        hovertemplate="%{y}<br>%{x:.2f}%<extra></extra>",
    ))
    fig.add_vrect(x0=0, x1=limites[0], fillcolor="#d94a45", opacity=0.20, line_width=0, layer="below")
    fig.add_vrect(x0=limites[0], x1=limites[1], fillcolor="#f0c419", opacity=0.25, line_width=0, layer="below")
    fig.add_vrect(x0=limites[1], x1=100, fillcolor="#36a65c", opacity=0.22, line_width=0, layer="below")
    layout_valores = {**PLOTLY_LAYOUT, "margin": dict(l=240, r=55, t=20, b=40)}
    fig.update_layout(
        **layout_valores,
        height=altura,
        showlegend=False,
        xaxis=dict(title="Promedio", range=[0, 103], ticksuffix="%", dtick=10, gridcolor="white"),
        yaxis=dict(
            title="",
            autorange="reversed",
            categoryorder="array",
            categoryarray=datos["competencia"].tolist(),
            tickfont_size=10,
        ),
    )
    return fig


def fig_medidor_potencial(valor: float, limites: tuple[float, float]) -> go.Figure:
    """Medidor del promedio filtrado con bandas de la escala indicada."""
    limite_bajo, limite_alto = limites
    valor_grafico = float(valor) if pd.notna(valor) else 0.0
    valor_aguja = min(100.0, max(0.0, valor_grafico))
    fig = go.Figure()

    def punto(angulo: float, radio: float) -> tuple[float, float]:
        return radio * np.cos(angulo), radio * np.sin(angulo)

    def agregar_segmento(inicio: float, fin: float, color: str) -> None:
        ang_inicio = np.pi - (inicio / 100.0) * np.pi
        ang_fin = np.pi - (fin / 100.0) * np.pi
        radio_ext, radio_int = 1.0, 0.68
        theta_ext = np.linspace(ang_inicio, ang_fin, 90)
        theta_int = np.linspace(ang_fin, ang_inicio, 90)
        x_ext = radio_ext * np.cos(theta_ext)
        y_ext = radio_ext * np.sin(theta_ext)
        x_int = radio_int * np.cos(theta_int)
        y_int = radio_int * np.sin(theta_int)
        fig.add_trace(go.Scatter(
            x=np.concatenate([x_ext, x_int]),
            y=np.concatenate([y_ext, y_int]),
            mode="lines",
            fill="toself",
            fillcolor=color,
            line=dict(color=color, width=0),
            hoverinfo="skip",
            showlegend=False,
        ))

    for inicio, fin, color in [
        (0, limite_bajo, "#d94a45"),
        (limite_bajo, limite_alto, "#f0c419"),
        (limite_alto, 100, "#36a65c"),
    ]:
        agregar_segmento(inicio, fin, color)

    angulo_aguja = np.pi - (valor_aguja / 100.0) * np.pi
    punta_x, punta_y = punto(angulo_aguja, 0.86)
    fig.add_shape(
        type="line",
        xref="x",
        yref="y",
        x0=0,
        y0=0,
        x1=punta_x,
        y1=punta_y,
        line=dict(color="#1a1a3e", width=3),
        layer="above",
    )

    fig.add_annotation(
        x=0,
        y=-0.11,
        text=f"{valor_grafico:.2f}",
        showarrow=False,
        font=dict(size=22, color="#1a1a3e", family="DM Sans"),
        xanchor="center",
        yanchor="middle",
    )
    fig.add_trace(go.Scatter(
        x=[-1.05, 1.05],
        y=[-0.22, 1.06],
        mode="markers",
        marker=dict(size=0, color="rgba(0,0,0,0)"),
        hoverinfo="skip",
        showlegend=False,
    ))
    fig.update_layout(
        height=210,
        margin=dict(l=12, r=12, t=8, b=8),
        paper_bgcolor="white",
        plot_bgcolor="white",
        font_family="DM Sans",
        xaxis=dict(visible=False, range=[-1.18, 1.18], fixedrange=True),
        yaxis=dict(
            visible=False,
            range=[-0.22, 1.18],
            scaleanchor="x",
            scaleratio=1,
            fixedrange=True,
        ),
    )
    return fig


def fig_escala_potencial(df: pd.DataFrame, columna: str) -> go.Figure:
    mapa_escala = {etiqueta.casefold(): etiqueta for etiqueta in POTENCIAL_ESCALAS}
    valores = (
        df[columna]
        .dropna()
        .astype(str)
        .str.strip()
        .str.casefold()
        .map(mapa_escala)
    )
    conteos = valores.value_counts().reindex(POTENCIAL_ESCALAS, fill_value=0)
    y_max = max(5, int(np.ceil(conteos.max() * 1.18))) if len(conteos) else 5
    layout = PLOTLY_LAYOUT.copy()
    layout["margin"] = dict(l=42, r=24, t=34, b=48)
    fig = go.Figure(go.Bar(
        x=POTENCIAL_ESCALAS,
        y=conteos.values,
        marker_color=[POTENCIAL_COLORES[escala] for escala in POTENCIAL_ESCALAS],
        text=conteos.values,
        textposition="outside",
        cliponaxis=False,
        hovertemplate="%{x}<br>%{y} colaboradores<extra></extra>",
    ))
    fig.update_layout(
        **layout,
        height=280,
        showlegend=False,
        xaxis=dict(
            tickfont_size=11,
            tickmode="array",
            tickvals=POTENCIAL_ESCALAS,
            ticktext=[
                f"{escala}<br>{POTENCIAL_RANGOS[escala]}"
                for escala in POTENCIAL_ESCALAS
            ],
        ),
        yaxis=dict(
            title="Colaboradores",
            gridcolor="#f0eef8",
            range=[0, y_max],
            rangemode="tozero",
        ),
    )
    return fig


def fig_distribucion_potencial(df: pd.DataFrame, dimension: str) -> go.Figure:
    serie = (
        df[dimension]
        .fillna("Sin dato")
        .replace("", "Sin dato")
        .map(reparar_texto)
    )
    conteos = serie.value_counts()
    etiquetas_cortas = {
        "Macrotech Farmaceutica": "Macrotech",
        "Macrotech Farmacéutica": "Macrotech",
        "República Dominicana": "R. Dominicana",
    }
    etiquetas = [etiquetas_cortas.get(str(valor), str(valor)) for valor in conteos.index]
    paleta = ["#3f7ee8", "#1d9e75", "#e6a700", "#d95f59", "#7c5cc4"]
    fig = go.Figure(go.Pie(
        labels=etiquetas,
        values=conteos.values,
        hole=0.52,
        sort=False,
        direction="clockwise",
        domain=dict(x=[0.08, 0.92], y=[0.08, 0.92]),
        marker=dict(colors=paleta[:len(conteos)], line=dict(color="white", width=2)),
        textposition="outside",
        texttemplate="%{label}<br>%{value} - %{percent}",
        textfont=dict(size=9),
        automargin=True,
        customdata=[str(valor) for valor in conteos.index],
        hovertemplate="%{customdata}<br>%{value} colaboradores<br>%{percent}<extra></extra>",
    ))
    layout_dona = {**PLOTLY_LAYOUT, "margin": dict(l=42, r=42, t=34, b=34)}
    fig.update_layout(
        **layout_dona,
        height=330,
        showlegend=False,
        uniformtext_minsize=9,
        uniformtext_mode="hide",
    )
    return fig


def fig_comparativo_potencial(df: pd.DataFrame) -> go.Figure:
    valores = [df["potencial_2025"].mean(), df["evaluacion_potencial"].mean()]
    coberturas = [df["potencial_2025"].notna().sum(), df["evaluacion_potencial"].notna().sum()]
    textos = [f"{valor:.2f}" if pd.notna(valor) else "Sin dato" for valor in valores]
    valores_validos = [valor for valor in valores if pd.notna(valor)]
    if valores_validos:
        eje_min = max(0, np.floor(min(valores_validos) * 2) / 2 - 1.5)
        eje_max = min(100, np.ceil(max(valores_validos) * 2) / 2 + 0.5)
        if eje_max - eje_min < 2:
            eje_min = max(0, eje_max - 2)
    else:
        eje_min, eje_max = 0, 100
    fig = go.Figure(go.Bar(
        x=["2025", "2026"],
        y=valores,
        marker_color=["#78a6f5", "#185fa5"],
        text=textos,
        textposition="outside",
        customdata=coberturas,
        hovertemplate="%{x}<br>Promedio %{y:.2f}<br>%{customdata} colaboradores<extra></extra>",
    ))
    fig.update_layout(
        **PLOTLY_LAYOUT,
        height=330,
        showlegend=False,
        yaxis=dict(
            title="Puntaje promedio",
            range=[eje_min, eje_max],
            dtick=0.5,
            tickformat=".1f",
            gridcolor="#e8e4f4",
        ),
        xaxis=dict(
            title="",
            type="category",
            tickmode="array",
            tickvals=["2025", "2026"],
            ticktext=["2025", "2026"],
            categoryorder="array",
            categoryarray=["2025", "2026"],
        ),
    )
    return fig


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# MOTOR DE CÃLCULO
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def contar_arquetipos_disc(df: pd.DataFrame) -> pd.DataFrame:
    if "disc" not in df.columns:
        return pd.DataFrame(columns=["arquetipo", "colaboradores", "participacion"])
    conteos = (
        df["disc"]
        .dropna()
        .astype(str)
        .str.strip()
        .replace("", np.nan)
        .dropna()
        .value_counts()
    )
    total = int(conteos.sum())
    if total == 0:
        return pd.DataFrame(columns=["arquetipo", "colaboradores", "participacion"])
    salida = conteos.rename_axis("arquetipo").reset_index(name="colaboradores")
    salida["participacion"] = salida["colaboradores"] / total
    return salida


def fig_disc_arquetipos(df_disc: pd.DataFrame) -> go.Figure:
    if df_disc.empty:
        fig = go.Figure()
        fig.update_layout(**PLOTLY_LAYOUT, height=420)
        return fig

    datos = df_disc.copy()
    maximo = int(datos["colaboradores"].max())
    rango_max = max(10, int(np.ceil(maximo / 10) * 10 + 10))
    colores = [DISC_PALETA[i % len(DISC_PALETA)] for i in range(len(datos))]
    theta = datos["arquetipo"].tolist() + [datos["arquetipo"].iloc[0]]
    valores = datos["colaboradores"].tolist() + [datos["colaboradores"].iloc[0]]

    fig = go.Figure(go.Scatterpolar(
        r=valores,
        theta=theta,
        mode="lines+markers+text",
        line=dict(color="#1a1a3e", width=2),
        fill="toself",
        fillcolor="rgba(24, 95, 165, 0.08)",
        marker=dict(
            size=9,
            color=colores + [colores[0]],
            line=dict(color="white", width=1.5),
        ),
        text=[f"{v}" for v in valores],
        textposition="top center",
        textfont=dict(size=10, color="#4a4a6a"),
        hovertemplate="%{theta}<br>%{r} colaboradores<extra></extra>",
        showlegend=False,
    ))
    layout = {**PLOTLY_LAYOUT, "margin": dict(l=55, r=55, t=34, b=34)}
    fig.update_layout(
        **layout,
        height=430,
        polar=dict(
            bgcolor="white",
            radialaxis=dict(
                range=[0, rango_max],
                gridcolor="#e8e4f4",
                tickfont_size=9,
                showline=False,
            ),
            angularaxis=dict(
                gridcolor="#f0eef8",
                tickfont_size=10,
                rotation=90,
                direction="clockwise",
            ),
        ),
    )
    return fig


def fig_disc_top_barras(df_disc: pd.DataFrame, top_n: int = 8) -> go.Figure:
    datos = df_disc.head(top_n).sort_values("colaboradores")
    colores = [DISC_PALETA[i % len(DISC_PALETA)] for i in range(len(datos))]
    fig = go.Figure(go.Bar(
        y=datos["arquetipo"],
        x=datos["colaboradores"],
        orientation="h",
        marker=dict(color=colores, line=dict(color="white", width=1)),
        text=datos["colaboradores"],
        textposition="outside",
        cliponaxis=False,
        hovertemplate="%{y}<br>%{x} colaboradores<extra></extra>",
    ))
    layout = {**PLOTLY_LAYOUT, "margin": dict(l=145, r=45, t=12, b=28)}
    fig.update_layout(
        **layout,
        height=300,
        showlegend=False,
        xaxis=dict(title="Colaboradores", gridcolor="#f0eef8", rangemode="tozero"),
        yaxis=dict(title="", tickfont_size=10),
    )
    return fig


def _extraer_puntaje_iq(etiqueta: object) -> float:
    import re
    match = re.search(r"\d+(?:[.,]\d+)?", str(etiqueta))
    if not match:
        return np.nan
    return float(match.group(0).replace(",", "."))


def contar_iq(df: pd.DataFrame) -> pd.DataFrame:
    if "iq" not in df.columns:
        return pd.DataFrame(columns=["iq", "puntaje", "colaboradores", "participacion"])
    valores = (
        df["iq"]
        .dropna()
        .astype(str)
        .str.strip()
        .replace("", np.nan)
        .dropna()
        .map(reparar_texto)
    )
    conteos = valores.value_counts()
    total = int(conteos.sum())
    if total == 0:
        return pd.DataFrame(columns=["iq", "puntaje", "colaboradores", "participacion"])
    salida = conteos.rename_axis("iq").reset_index(name="colaboradores")
    salida["puntaje"] = salida["iq"].apply(_extraer_puntaje_iq)
    salida["participacion"] = salida["colaboradores"] / total
    return salida.sort_values(["puntaje", "iq"], ascending=[True, True]).reset_index(drop=True)


def fig_iq_distribucion(df_iq: pd.DataFrame) -> go.Figure:
    datos = df_iq.copy()
    colores = [IQ_PALETA[i % len(IQ_PALETA)] for i in range(len(datos))]
    fig = go.Figure(go.Bar(
        y=datos["iq"],
        x=datos["colaboradores"],
        orientation="h",
        marker=dict(color=colores, line=dict(color="white", width=1)),
        text=datos["colaboradores"].astype(str) + " - " + datos["participacion"].map(lambda v: f"{v:.1%}"),
        textposition="outside",
        cliponaxis=False,
        customdata=np.stack([datos["puntaje"], datos["participacion"]], axis=-1),
        hovertemplate="%{y}<br>%{x} colaboradores<br>Puntaje %{customdata[0]:.0f}<br>%{customdata[1]:.1%}<extra></extra>",
    ))
    layout = {**PLOTLY_LAYOUT, "margin": dict(l=210, r=70, t=12, b=35)}
    fig.update_layout(
        **layout,
        height=max(300, len(datos) * 42 + 80),
        showlegend=False,
        xaxis=dict(title="Colaboradores", gridcolor="#f0eef8", rangemode="tozero", dtick=1),
        yaxis=dict(title="", tickfont_size=11),
    )
    return fig


def preparar_curva_desarrollo(df_competencias: pd.DataFrame, competencia: str) -> pd.DataFrame:
    if df_competencias.empty or "valor" not in df_competencias.columns:
        return pd.DataFrame(columns=["puntaje", "descripcion", "colaboradores", "participacion"])
    datos = df_competencias[df_competencias["competencia"] == competencia].copy()
    valores = pd.to_numeric(datos["valor"], errors="coerce").dropna()
    if valores.empty:
        return pd.DataFrame(columns=["puntaje", "descripcion", "colaboradores", "participacion"])
    puntajes = np.floor(valores).astype(int).clip(0, 10)
    conteos = puntajes.value_counts().reindex(range(0, 11), fill_value=0).sort_index()
    total = int(conteos.sum())
    tabla = pd.DataFrame({
        "puntaje": conteos.index.astype(int),
        "descripcion": [CURVA_DESARROLLO_DESCRIPCIONES[int(p)] for p in conteos.index],
        "colaboradores": conteos.values.astype(int),
    })
    tabla["participacion"] = tabla["colaboradores"] / total if total else 0
    return tabla


def fig_curva_desarrollo(tabla: pd.DataFrame, competencia: str) -> go.Figure:
    datos = tabla.copy()
    max_y = max(1, int(datos["colaboradores"].max()))
    x_curva = np.linspace(0, 10, 240)
    y_curva = np.exp(-0.5 * ((x_curva - 5) / 1.75) ** 2)
    y_curva = y_curva / y_curva.max() * max_y * 1.12

    fig = go.Figure()
    bandas = [
        (0, 1, "rgba(239, 83, 80, 0.30)"),
        (1, 2, "rgba(244, 115, 115, 0.30)"),
        (2, 3, "rgba(248, 173, 97, 0.34)"),
        (3, 4, "rgba(250, 202, 120, 0.38)"),
        (4, 5, "rgba(255, 237, 117, 0.45)"),
        (5, 6, "rgba(223, 237, 143, 0.42)"),
        (6, 7, "rgba(190, 226, 132, 0.40)"),
        (7, 8, "rgba(148, 218, 136, 0.38)"),
        (8, 9, "rgba(104, 203, 126, 0.36)"),
        (9, 10, "rgba(67, 181, 109, 0.34)"),
    ]
    for x0, x1, color in bandas:
        mascara = (x_curva >= x0) & (x_curva <= x1)
        x_segmento = x_curva[mascara]
        y_segmento = y_curva[mascara]
        if len(x_segmento):
            fig.add_trace(go.Scatter(
                x=x_segmento,
                y=y_segmento,
                mode="lines",
                line=dict(color="rgba(0,0,0,0)", width=0),
                fill="tozeroy",
                fillcolor=color,
                hoverinfo="skip",
                showlegend=False,
            ))

    fig.add_trace(go.Scatter(
        x=x_curva,
        y=y_curva,
        mode="lines",
        line=dict(color="#1a1a3e", width=2),
        fill="tozeroy",
        fillcolor="rgba(0,0,0,0)",
        hoverinfo="skip",
        name="Curva de referencia",
    ))
    fig.add_trace(go.Scatter(
        x=datos["puntaje"],
        y=datos["colaboradores"],
        mode="lines+markers",
        line=dict(color="#1a1a3e", width=2),
        marker=dict(color="white", size=7, line=dict(color="#1a1a3e", width=1.5)),
        customdata=np.stack([datos["descripcion"], datos["participacion"]], axis=-1),
        hovertemplate="Puntaje %{x}<br>%{customdata[0]}<br>%{y} colaboradores<br>%{customdata[1]:.1%}<extra></extra>",
        showlegend=False,
    ))
    for _, fila in datos.iterrows():
        fig.add_annotation(
            x=int(fila["puntaje"]),
            y=int(fila["colaboradores"]),
            text=str(int(fila["colaboradores"])),
            showarrow=False,
            yshift=10,
            font=dict(size=11, color="#111827"),
            bgcolor="white",
            bordercolor="#1a1a3e",
            borderwidth=1,
            borderpad=2,
        )
    layout = {**PLOTLY_LAYOUT, "margin": dict(l=40, r=30, t=45, b=75)}
    fig.update_layout(
        **layout,
        height=460,
        title=dict(text=competencia, x=0.5, xanchor="center", font=dict(size=18)),
        showlegend=False,
        xaxis=dict(
            title="Escala de desarrollo",
            range=[-0.5, 10.5],
            tickmode="array",
            tickvals=list(range(0, 11)),
            gridcolor="rgba(255,255,255,0.60)",
            zeroline=False,
        ),
        yaxis=dict(
            title="Colaboradores",
            rangemode="tozero",
            gridcolor="rgba(232,228,244,0.65)",
            side="right",
        ),
    )
    return fig


NINEBOX_COLORES = {
    1: "#4EA72F", 2: "#C5E0B3", 3: "#EAEAEA",
    4: "#528139", 5: "#FFC000", 6: "#FF99FF",
    7: "#0071C0", 8: "#9F2522", 9: "#FE0000",
}
NINEBOX_LABELS = {
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


def normalizar_nombre_match(nombre: object) -> str:
    return motor_360.normalizar_nombre_persona("" if nombre is None else nombre)


def normalizar_correo(correo: object) -> str:
    if correo is None or pd.isna(correo):
        return ""
    return str(correo).strip().casefold()


def valor_limpio(valor: object) -> str:
    if valor is None or pd.isna(valor):
        return ""
    texto = reparar_texto(valor)
    return "" if texto.casefold() in {"", "nan", "none", "n/a", "na", "-"} else texto


def preparar_ninebox(df_360_global: pd.DataFrame, df_potencial: pd.DataFrame) -> pd.DataFrame:
    desempeno_cols = ["colaborador", "global"] + [
        col for col in ["email_colaborador", "correo"] if col in df_360_global.columns
    ]
    desempeno = df_360_global[desempeno_cols].copy()
    potencial = df_potencial[
        [col for col in ["colaborador", "evaluacion_potencial", "correo", "correo_potencial", "correo_instancia"] if col in df_potencial.columns]
    ].copy()
    desempeno_original = desempeno.copy()
    potencial_original = potencial.copy()
    potencial_cols = list(potencial.columns)
    desempeno = expandir_llaves_match(
        desempeno,
        ["email_colaborador", "correo"],
        "colaborador",
        desempeno_cols,
    )
    potencial = expandir_llaves_match(
        potencial,
        ["correo", "correo_potencial", "correo_instancia"],
        "colaborador",
        potencial_cols,
    )
    nombres_potencial = potencial_original["colaborador"].dropna().astype(str).tolist()
    potencial_con_llave = potencial_original.assign(
        _match_nombre=potencial_original["colaborador"].map(normalizar_nombre_match)
    )
    alias_flexibles = []
    for nombre_desempeno in desempeno_original["colaborador"].dropna().astype(str).unique():
        match_desempeno = normalizar_nombre_match(nombre_desempeno)
        match_potencial = motor_360.resolver_nombre_equivalente_unico(
            nombre_desempeno,
            nombres_potencial,
        )
        if not match_potencial or match_potencial == match_desempeno:
            continue
        coincidencias = potencial_con_llave[
            potencial_con_llave["_match_nombre"].eq(match_potencial)
        ]
        if len(coincidencias) != 1:
            continue
        fila = coincidencias.iloc[0]
        registro = {"match_key": f"nombre::{match_desempeno}"}
        for columna in potencial_cols:
            registro[columna] = fila.get(columna)
        alias_flexibles.append(registro)
    if alias_flexibles:
        potencial = pd.concat(
            [potencial, pd.DataFrame(alias_flexibles)],
            ignore_index=True,
        ).drop_duplicates("match_key")
    merged = desempeno.merge(
        potencial,
        on="match_key",
        how="inner",
        suffixes=("_360", "_potencial"),
    )
    merged = merged.dropna(subset=["global", "evaluacion_potencial"]).copy()
    merged = merged.rename(columns={
        "colaborador_360": "colaborador",
        "global": "desempeno_360",
        "evaluacion_potencial": "potencial",
    })
    merged = merged.drop_duplicates("colaborador")
    return merged[["colaborador", "match_key", "potencial", "desempeno_360"]].sort_values("colaborador")


def construir_indice_colaboradores(res_360: dict, res_potencial: dict, res_objetivos: dict) -> pd.DataFrame:
    registros: dict[str, dict] = {}
    alias_correo: dict[str, str] = {}
    correos_con_potencial: set[str] = set()
    nombres_con_potencial: set[str] = set()

    def upsert(
        correos: object,
        colaborador: object,
        permitir_crear: bool = True,
        **campos: object,
    ) -> None:
        if isinstance(correos, (list, tuple, set)):
            correos_lista = list(correos)
        else:
            correos_lista = [correos]
        correo_keys = [normalizar_correo(correo) for correo in correos_lista]
        correo_keys = [correo for correo in dict.fromkeys(correo_keys) if correo]
        nombre = valor_limpio(colaborador)
        nombre_key = normalizar_nombre_match(nombre)
        if not correo_keys and not nombre_key:
            return

        key = next((alias_correo[correo] for correo in correo_keys if correo in alias_correo), None)
        if key is None and nombre_key:
            key = next(
                (
                    registro_key
                    for registro_key, registro in registros.items()
                    if registro.get("colaborador_key") == nombre_key
                ),
                None,
            )
        if key is None and nombre_key:
            nombre_equivalente = motor_360.resolver_nombre_equivalente_unico(
                nombre_key,
                [registro.get("colaborador_key", "") for registro in registros.values()],
            )
            claves_equivalentes = [
                registro_key
                for registro_key, registro in registros.items()
                if registro.get("colaborador_key") == nombre_equivalente
            ]
            if nombre_equivalente and len(claves_equivalentes) == 1:
                key = claves_equivalentes[0]
        if key is None and not permitir_crear:
            return
        if key is None:
            key = f"correo::{correo_keys[0]}" if correo_keys else f"nombre::{nombre_key}"

        actual = registros.setdefault(
            key,
            {
                "correo_key": correo_keys[0] if correo_keys else "",
                "correo_potencial_key": "",
                "correo_instancia_key": "",
                "colaborador_key": nombre_key,
                "correo": valor_limpio(correos_lista[0]) if correos_lista else "",
                "correo_potencial": "",
                "correo_instancia": "",
                "colaborador": nombre,
                "empresa": "",
                "cargo": "",
                "jefe": "",
                "pais": "",
                "area": "",
                "grupo": "",
            },
        )
        for correo_key in correo_keys:
            alias_correo[correo_key] = key
        if correo_keys and not actual.get("correo_key"):
            actual["correo_key"] = correo_keys[0]
        if nombre_key and not actual.get("colaborador_key"):
            actual["colaborador_key"] = nombre_key
        if correos_lista and valor_limpio(correos_lista[0]) and not actual.get("correo"):
            actual["correo"] = valor_limpio(correos_lista[0])
        if nombre and not actual.get("colaborador"):
            actual["colaborador"] = nombre
        for campo, valor in campos.items():
            limpio = valor_limpio(valor)
            if limpio and not actual.get(campo):
                actual[campo] = limpio

    df_potencial = res_potencial.get("df_personas", pd.DataFrame())
    if not df_potencial.empty:
        for _, fila in df_potencial.iterrows():
            correos_con_potencial.update(
                correo
                for correo in (
                    normalizar_correo(fila.get("correo")),
                    normalizar_correo(fila.get("correo_potencial")),
                    normalizar_correo(fila.get("correo_instancia")),
                )
                if correo
            )
            nombre_potencial = normalizar_nombre_match(fila.get("colaborador"))
            if nombre_potencial:
                nombres_con_potencial.add(nombre_potencial)
            upsert(
                [fila.get("correo"), fila.get("correo_potencial"), fila.get("correo_instancia")],
                fila.get("colaborador"),
                correo_potencial=fila.get("correo_potencial"),
                correo_instancia=fila.get("correo_instancia"),
                empresa=fila.get("empresa"),
                cargo=fila.get("cargo"),
                jefe=fila.get("jefe"),
                pais=fila.get("pais"),
                area=fila.get("area"),
                grupo=fila.get("grupo"),
            )

    df_obj = res_objetivos.get("df_colaboradores", pd.DataFrame())
    if not df_obj.empty:
        for _, fila in df_obj.iterrows():
            upsert(
                fila.get("email_colaborador"),
                fila.get("colaborador"),
                cargo=fila.get("cargo_objetivo"),
                jefe=fila.get("jefe"),
            )

    df_360 = res_360.get("df_global", pd.DataFrame())
    if not df_360.empty and {"email_colaborador", "colaborador"}.issubset(df_360.columns):
        for _, fila in df_360.drop_duplicates("colaborador").iterrows():
            correo_360 = normalizar_correo(fila.get("email_colaborador"))
            nombre_360 = normalizar_nombre_match(fila.get("colaborador"))
            sin_registro_potencial = (
                correo_360 not in correos_con_potencial
                and nombre_360 not in nombres_con_potencial
            )
            metadata_fallback = (
                {
                    "empresa": fila.get("empresa"),
                    "pais": fila.get("pais"),
                    "area": fila.get("area"),
                    "grupo": fila.get("grupo"),
                }
                if sin_registro_potencial
                else {}
            )
            upsert(
                fila.get("email_colaborador"),
                fila.get("colaborador"),
                **metadata_fallback,
            )

    df_metadata = res_360.get("df_metadata", pd.DataFrame())
    if not df_metadata.empty:
        for _, fila in df_metadata.drop_duplicates("colaborador").iterrows():
            correo_360 = normalizar_correo(fila.get("email_colaborador"))
            nombre_360 = normalizar_nombre_match(fila.get("colaborador"))
            sin_registro_potencial = (
                correo_360 not in correos_con_potencial
                and nombre_360 not in nombres_con_potencial
            )
            upsert(
                fila.get("email_colaborador"),
                fila.get("colaborador"),
                permitir_crear=False,
                **(
                    {
                        "empresa": fila.get("empresa"),
                        "pais": fila.get("pais"),
                        "area": fila.get("area"),
                        "grupo": fila.get("grupo"),
                    }
                    if sin_registro_potencial
                    else {}
                ),
            )

    for registro in registros.values():
        registro["correo_potencial_key"] = normalizar_correo(registro.get("correo_potencial"))
        registro["correo_instancia_key"] = normalizar_correo(registro.get("correo_instancia"))

    columnas = [
        "correo_key", "correo_potencial_key", "correo_instancia_key",
        "colaborador_key", "correo", "correo_potencial", "correo_instancia",
        "colaborador", "empresa", "cargo", "jefe", "pais", "area", "grupo",
    ]
    if not registros:
        return pd.DataFrame(columns=columnas)
    return pd.DataFrame(registros.values()).reindex(columns=columnas).sort_values("colaborador", kind="stable").reset_index(drop=True)


def filtrar_indice_global(indice: pd.DataFrame, filtros: dict[str, list[str]]) -> pd.DataFrame:
    filtrado = indice.copy()
    for columna, seleccion in filtros.items():
        if seleccion and columna in filtrado.columns:
            filtrado = filtrado[filtrado[columna].isin(seleccion)]
    return filtrado


def filtrar_por_universo(
    df: pd.DataFrame,
    correos: set[str],
    nombres: set[str],
    col_correo: str | list[str] | None = None,
    col_nombre: str | None = None,
) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    mascaras = []
    columnas_correo = []
    if isinstance(col_correo, str):
        columnas_correo = [col_correo]
    elif isinstance(col_correo, list):
        columnas_correo = col_correo
    for columna in columnas_correo:
        if columna in df.columns and correos:
            mascaras.append(df[columna].map(normalizar_correo).isin(correos))
    if col_nombre and col_nombre in df.columns and nombres:
        mascaras.append(df[col_nombre].map(normalizar_nombre_match).isin(nombres))
    if not mascaras:
        return df.iloc[0:0].copy()
    mascara = mascaras[0]
    for extra in mascaras[1:]:
        mascara = mascara | extra
    return df[mascara].copy()


def expandir_llaves_match(
    df: pd.DataFrame,
    columnas_correo: list[str],
    columna_nombre: str,
    columnas_salida: list[str],
) -> pd.DataFrame:
    registros = []
    if df.empty:
        return pd.DataFrame(columns=["match_key", *columnas_salida])
    for _, fila in df.iterrows():
        keys = []
        for columna in columnas_correo:
            if columna in df.columns:
                correo = normalizar_correo(fila.get(columna))
                if correo:
                    keys.append(f"email::{correo}")
        if columna_nombre in df.columns:
            nombre = normalizar_nombre_match(fila.get(columna_nombre))
            if nombre:
                keys.append(f"nombre::{nombre}")
        for key in dict.fromkeys(keys):
            registro = {"match_key": key}
            for columna in columnas_salida:
                registro[columna] = fila.get(columna)
            registros.append(registro)
    if not registros:
        return pd.DataFrame(columns=["match_key", *columnas_salida])
    return pd.DataFrame(registros).drop_duplicates("match_key")


def cortes_ninebox(df_ninebox: pd.DataFrame) -> dict:
    potencial_prom = df_ninebox["potencial"].mean()
    potencial_std = df_ninebox["potencial"].std(ddof=1)
    desempeno_prom = df_ninebox["desempeno_360"].mean()
    desempeno_std = df_ninebox["desempeno_360"].std(ddof=1)
    return {
        "potencial_prom": potencial_prom,
        "potencial_std": potencial_std,
        "potencial_sup": motor_360.corte_superior_ninebox(
            potencial_prom + potencial_std
        ),
        "potencial_inf": motor_360.redondear_corte_ninebox(
            potencial_prom - potencial_std
        ),
        "desempeno_prom": desempeno_prom,
        "desempeno_std": desempeno_std,
        "desempeno_sup": motor_360.corte_superior_ninebox(
            desempeno_prom + desempeno_std
        ),
        "desempeno_inf": motor_360.redondear_corte_ninebox(
            desempeno_prom - desempeno_std
        ),
    }


def clasificar_ninebox(df_ninebox: pd.DataFrame, cortes: dict) -> pd.DataFrame:
    df = df_ninebox.copy()

    def nivel(valor: float, inferior: float, superior: float) -> str:
        if valor >= superior:
            return "alto"
        if valor < inferior:
            return "bajo"
        return "medio"

    def cuadrante(potencial: str, desempeno: str) -> int:
        mapa = {
            ("alto", "alto"): 1, ("alto", "medio"): 2, ("alto", "bajo"): 3,
            ("medio", "alto"): 4, ("medio", "medio"): 5, ("medio", "bajo"): 6,
            ("bajo", "alto"): 7, ("bajo", "medio"): 8, ("bajo", "bajo"): 9,
        }
        return mapa[(potencial, desempeno)]

    df["nivel_potencial"] = df["potencial"].apply(
        lambda v: nivel(v, cortes["potencial_inf"], cortes["potencial_sup"])
    )
    df["nivel_desempeno"] = df["desempeno_360"].apply(
        lambda v: nivel(v, cortes["desempeno_inf"], cortes["desempeno_sup"])
    )
    df["cuadrante"] = [
        cuadrante(pot, desp) for pot, desp in zip(df["nivel_potencial"], df["nivel_desempeno"])
    ]
    df["cuadrante_nombre"] = df["cuadrante"].map(NINEBOX_LABELS)
    return df


def filtrar_ninebox_general(
    df_clasificado_general: pd.DataFrame,
    df_ninebox_visible: pd.DataFrame,
) -> pd.DataFrame:
    """Filtra personas sin modificar su cuadrante calculado en el universo general."""
    if df_clasificado_general.empty or df_ninebox_visible.empty:
        return df_clasificado_general.iloc[0:0].copy()
    llaves_visibles = set(df_ninebox_visible["match_key"].dropna())
    return df_clasificado_general[
        df_clasificado_general["match_key"].isin(llaves_visibles)
    ].copy()


def matriz_ninebox(df_clasificado: pd.DataFrame) -> pd.DataFrame:
    filas = ["alto", "medio", "bajo"]
    columnas = ["bajo", "medio", "alto"]
    matriz = pd.crosstab(
        df_clasificado["nivel_potencial"],
        df_clasificado["nivel_desempeno"],
    ).reindex(index=filas, columns=columnas, fill_value=0)
    return matriz


def fig_ninebox(df_clasificado: pd.DataFrame) -> go.Figure:
    filas = ["alto", "medio", "bajo"]
    columnas = ["bajo", "medio", "alto"]
    z_cuadrantes = [[3, 2, 1], [6, 5, 4], [9, 8, 7]]
    conteos = matriz_ninebox(df_clasificado)
    z = [[z_cuadrantes[i][j] for j in range(3)] for i in range(3)]
    colorscale = []
    for idx, q in enumerate(range(1, 10)):
        pos = idx / 8
        colorscale.append([pos, NINEBOX_COLORES[q]])
        colorscale.append([pos, NINEBOX_COLORES[q]])

    total = max(len(df_clasificado), 1)
    fig = go.Figure(go.Heatmap(
        z=z,
        x=["Bajo desempeño", "Desempeño medio", "Alto desempeño"],
        y=["Alto potencial", "Potencial medio", "Potencial bajo"],
        colorscale=colorscale,
        showscale=False,
        hoverinfo="skip",
        xgap=4,
        ygap=4,
    ))
    for i, fila in enumerate(filas):
        for j, columna in enumerate(columnas):
            cuadrante = z_cuadrantes[i][j]
            conteo = int(conteos.loc[fila, columna])
            pct = conteo / total
            label = NINEBOX_LABELS[cuadrante]
            color_texto = "#111111"
            fig.add_annotation(
                x=j,
                y=i,
                text=(
                    f"<b style='font-size:24px'>{conteo}</b><br>"
                    f"<span style='font-size:11px'>{label}</span><br>"
                    f"<span style='font-size:10px'>{pct:.1%}</span>"
                ),
                showarrow=False,
                font=dict(color=color_texto, size=13),
                align="center",
            )

    fig.update_layout(
        **{
            **PLOTLY_LAYOUT,
            "margin": dict(l=120, r=28, t=28, b=92),
            "height": 460,
            "paper_bgcolor": "#ffffff",
            "plot_bgcolor": "#ffffff",
        },
        xaxis=dict(
            title=dict(text="Desempeño", font=dict(size=13)),
            side="bottom",
            tickfont=dict(size=11),
            showgrid=False,
            zeroline=False,
            fixedrange=True,
        ),
        yaxis=dict(
            title=dict(text="Competencias", font=dict(size=13)),
            tickfont=dict(size=11),
            autorange="reversed",
            showgrid=False,
            zeroline=False,
            fixedrange=True,
        ),
    )
    return fig


def calcular(df: pd.DataFrame, weights: dict) -> dict:
    """Calcula el dashboard usando el motor compartido del proyecto."""
    filtrar_excluidos = getattr(
        motor_360,
        "filtrar_excluidos_desempeno",
        None,
    )
    if callable(filtrar_excluidos):
        df_calculo = filtrar_excluidos(df)
    else:
        df_calculo = df.copy()
        if "email_colaborador" in df_calculo.columns:
            correos = (
                df_calculo["email_colaborador"]
                .fillna("")
                .astype(str)
                .str.strip()
                .str.casefold()
            )
            df_calculo = df_calculo[
                ~correos.isin(EXCLUIDOS_DESEMPENO_EMAILS)
            ].copy()
    res = motor_360.calcular_dashboard(df_calculo, weights)
    res["df_global"]["escala_idx"] = res["df_global"]["global"].apply(get_escala)
    res["df_global"]["escala"] = res["df_global"]["escala_idx"].apply(lambda i: ESCALA_LABELS[i])
    extraer_metadata = getattr(
        motor_360,
        "extraer_metadata_colaboradores",
        None,
    )
    if callable(extraer_metadata):
        metadata_360 = extraer_metadata(df)
    else:
        # Compatibilidad con procesos de Streamlit que conservaron en memoria
        # una version anterior de reporte.calculos durante el redespliegue.
        columnas = {
            "nombre_colaborador": "colaborador",
            "email_colaborador": "email_colaborador",
            "empresa": "empresa",
            "pais": "pais",
            "país": "pais",
            "area": "area",
            "área": "area",
            "grupo": "grupo",
        }
        disponibles = [columna for columna in columnas if columna in df.columns]
        metadata_360 = df[disponibles].rename(columns=columnas).copy()
        for columna in ["email_colaborador", "empresa", "pais", "area", "grupo"]:
            if columna not in metadata_360.columns:
                metadata_360[columna] = pd.NA
        metadata_360 = (
            metadata_360[
                [
                    "colaborador",
                    "email_colaborador",
                    "empresa",
                    "pais",
                    "area",
                    "grupo",
                ]
            ]
            .drop_duplicates(subset=["colaborador"], keep="first")
        )
    if not metadata_360.empty:
        res["df_global"] = res["df_global"].merge(
            metadata_360,
            on="colaborador",
            how="left",
        )
    res["df_metadata"] = metadata_360
    return res


def resultado_360_vacio(df_fuente: pd.DataFrame) -> dict:
    tipos_activos = {t: w for t, w in PESOS_PONDERACION.items() if w > 0}
    return {
        "ciclo": "Evaluacion 360",
        "resumen_fuente": {
            "filas": 0,
            "colaboradores": 0,
            "competencias": 0,
            "items": 0,
            "preguntas_abiertas_omitidas": 0,
        },
        "df_global": pd.DataFrame(
            columns=[
                "colaborador",
                "global",
                "escala_idx",
                "escala",
                "email_colaborador",
                "empresa",
                "pais",
                "area",
                "grupo",
            ]
        ),
        "df_comp": pd.DataFrame(
            columns=["colaborador", "competencia", "puntaje"]
            + [f"tipo_{tipo}" for tipo in tipos_activos]
        ),
        "df_comp_prom": pd.DataFrame(columns=["competencia", "prom_comp"]),
        "rel_prom": {},
        "comp_rel": {},
        "df_items": pd.DataFrame(columns=["competencia", "item", "puntaje"]),
        "df_fuente": df_fuente.iloc[0:0].copy(),
        "tipos_activos": tipos_activos,
        "colaboradores": [],
        "competencias": [],
    }


def recalcular_360_filtrado(df_fuente: pd.DataFrame) -> dict:
    if df_fuente.empty:
        return resultado_360_vacio(df_fuente)
    try:
        return calcular(df_fuente, PESOS_PONDERACION)
    except ValueError:
        return resultado_360_vacio(df_fuente)


def resumen_potencial_filtrado(df_personas: pd.DataFrame, df_competencias: pd.DataFrame, catalogo: list[str]) -> dict:
    return {
        "personas": len(df_personas),
        "evaluados": int(df_personas["evaluacion_potencial"].notna().sum()) if "evaluacion_potencial" in df_personas else 0,
        "sin_evaluacion": int(df_personas["evaluacion_potencial"].isna().sum()) if "evaluacion_potencial" in df_personas else 0,
        "con_potencial_2025": int(df_personas["potencial_2025"].notna().sum()) if "potencial_2025" in df_personas else 0,
        "con_disc": int(df_personas["disc"].notna().sum()) if "disc" in df_personas else 0,
        "con_iq": int(df_personas["iq"].notna().sum()) if "iq" in df_personas else 0,
        "competencias_catalogo": len(catalogo),
        "competencias_con_datos": int(df_competencias["competencia"].nunique()) if "competencia" in df_competencias else 0,
    }


def recalcular_objetivos_desde_fuente(df_fuente: pd.DataFrame) -> dict:
    if df_fuente.empty:
        return motor_objetivos._vacio()

    df = df_fuente.copy()
    if "puntaje" not in df.columns and "calificacion_porcentaje" in df.columns:
        df["puntaje"] = pd.to_numeric(df["calificacion_porcentaje"], errors="coerce").clip(0, 100)
    if "cargo_objetivo" not in df.columns and "nombre_seccion" in df.columns:
        df["cargo_objetivo"] = df["nombre_seccion"]
    if "objetivo" not in df.columns and "pregunta_texto" in df.columns:
        df["objetivo"] = df["pregunta_texto"]
    df_colaboradores = (
        df.groupby(["nombre_colaborador", "email_colaborador"], dropna=False)
        .agg(
            puntaje=("puntaje", "mean"),
            objetivos=("objetivo", "nunique"),
            cargo_objetivo=("cargo_objetivo", lambda valores: " / ".join(sorted(set(map(str, valores.dropna()))))),
            jefe=("nombre_evaluador", lambda valores: " / ".join(sorted(set(map(str, valores.dropna()))))),
        )
        .reset_index()
        .rename(columns={"nombre_colaborador": "colaborador"})
        .sort_values("puntaje", ascending=False)
    )
    df_cargos = (
        df.groupby("cargo_objetivo", dropna=False)
        .agg(
            puntaje=("puntaje", "mean"),
            colaboradores=("nombre_colaborador", "nunique"),
            objetivos=("objetivo", "nunique"),
        )
        .reset_index()
        .sort_values("puntaje", ascending=False)
    )
    df_objetivos = (
        df.groupby(["cargo_objetivo", "objetivo"], dropna=False)
        .agg(
            puntaje=("puntaje", "mean"),
            colaboradores=("nombre_colaborador", "nunique"),
        )
        .reset_index()
        .sort_values("puntaje", ascending=False)
    )
    resumen = {
        "filas": len(df),
        "colaboradores": int(df["nombre_colaborador"].nunique()),
        "jefes": int(df["nombre_evaluador"].nunique()),
        "cargos": int(df["cargo_objetivo"].nunique()),
        "objetivos": int(df["objetivo"].nunique()),
        "promedio": float(df_colaboradores["puntaje"].mean()) if len(df_colaboradores) else 0.0,
        "ciclo": str(df["nombre_ciclo"].dropna().iloc[0]) if df["nombre_ciclo"].notna().any() else "Objetivos",
    }
    return {
        "df_fuente": df,
        "df_colaboradores": df_colaboradores,
        "df_cargos": df_cargos,
        "df_objetivos": df_objetivos,
        "resumen": resumen,
    }


def leer_config_app(clave: str, default=None):
    app_config = st.secrets.get("app", {})
    if isinstance(app_config, Mapping) and clave in app_config:
        return app_config.get(clave, default)
    return st.secrets.get(clave, default)


def resolver_fuente_datos() -> str:
    fuente = str(leer_config_app("DATA_SOURCE", "auto")).strip().lower()
    if fuente not in {"auto", "excel", "neon"}:
        fuente = "auto"
    if fuente == "auto":
        return "excel" if ARCHIVO_BASE.exists() else "neon"
    return fuente


def obtener_credenciales_auth() -> tuple[str, str]:
    auth = st.secrets.get("auth", {})
    if not isinstance(auth, Mapping):
        auth = {}
    usuario = str(auth.get("username", "evaluar"))
    clave = str(auth.get("password", "evaluar2026"))
    return usuario, clave


def requerir_login() -> None:
    if st.session_state.get("autenticado"):
        return

    usuario_ok, clave_ok = obtener_credenciales_auth()

    try:
        svg_bytes = Path(__file__).resolve().parent.joinpath("brand_evaluar_on_dark.svg").read_bytes()
        svg_b64 = base64.b64encode(svg_bytes).decode("ascii")
        logo_login_html = (
            f'<img class="login-logo" src="data:image/svg+xml;base64,{svg_b64}" alt="Evaluar">'
        )
    except FileNotFoundError:
        logo_login_html = '<span class="login-logo-fallback">Evaluar</span>'

    st.markdown(
        f"""
        <style>
        div[data-testid="stAppViewContainer"] {{
            background:
                radial-gradient(circle at 50% 18%, rgba(232, 53, 122, 0.08), transparent 26%),
                linear-gradient(180deg, #ffffff 0%, #fbfbfe 100%);
        }}
        .login-shell {{
            display: block;
            padding: 9vh 12px 0;
        }}
        .login-card {{
            width: min(100%, 360px);
            margin: 0 auto;
            background: #ffffff;
            border: 1px solid #ebe7f6;
            border-radius: 18px 18px 0 0;
            box-shadow: 0 22px 64px rgba(26, 26, 62, 0.10);
            overflow: hidden;
        }}
        .login-brand {{
            background: #1a1a3e;
            padding: 30px 28px 26px;
            border-bottom: 3px solid transparent;
            border-image: linear-gradient(90deg, #c13bc4, #ff4b4b, #f47c3c) 1;
        }}
        .login-logo {{
            height: 42px;
            width: auto;
            max-width: 100%;
            display: block;
            margin: 0 auto;
        }}
        .login-logo-fallback {{
            display: block;
            text-align: center;
            font-size: 36px;
            font-weight: 700;
            color: white;
            letter-spacing: -0.5px;
        }}
        .login-body {{
            padding: 24px 28px 12px;
            text-align: center;
        }}
        .login-title {{
            color: #1a1a3e;
            font-size: 17px;
            font-weight: 700;
            margin-bottom: 6px;
        }}
        .login-subtitle {{
            color: #6b6b8a;
            font-size: 13px;
            line-height: 1.45;
            margin-bottom: 6px;
        }}
        div[data-testid="stForm"] {{
            max-width: 360px;
            margin: -1px auto 0;
            padding: 4px 28px 28px;
            border: 1px solid #ebe7f6;
            border-top: 0;
            border-radius: 0 0 18px 18px;
            box-shadow: 0 22px 64px rgba(26, 26, 62, 0.10);
            background: #ffffff;
        }}
        div[data-testid="stForm"] label {{
            color: #1a1a3e;
            font-size: 12px;
            font-weight: 600;
        }}
        div[data-testid="stForm"] input {{
            border-radius: 10px;
            min-height: 42px;
        }}
        div[data-testid="stForm"] button {{
            border-radius: 10px;
            font-weight: 700;
            min-height: 42px;
            background: #ff4b4b;
            color: white;
            border: 0;
        }}
        div[data-testid="stForm"] button:hover {{
            background: #e8357a;
            color: white;
            border: 0;
        }}
        </style>
        <div class="login-shell">
            <div class="login-card">
                <div class="login-brand">{logo_login_html}</div>
                <div class="login-body">
                    <div class="login-title">Dashboard confidencial</div>
                    <div class="login-subtitle">
                        Accede con las credenciales autorizadas para consultar los resultados.
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    _, centro, _ = st.columns([1, 1.05, 1])
    with centro:
        with st.form("login_form"):
            usuario = st.text_input("Usuario")
            clave = st.text_input("Clave", type="password")
            enviar = st.form_submit_button("Ingresar", use_container_width=True)

    if enviar:
        if usuario == usuario_ok and clave == clave_ok:
            st.session_state.autenticado = True
            st.rerun()
        else:
            st.error("Usuario o clave incorrectos.")

    st.stop()


@st.cache_data(show_spinner="Cargando base local de talento...")
def cargar_base_excel(
    ruta: str, ultima_modificacion: int, version_carga: int
) -> tuple[dict, dict, dict]:
    """Carga ambas fases desde el Excel local."""
    del ultima_modificacion, version_carga
    df_desempeno = motor_360.leer_exportacion_dashboard(ruta)
    res_360 = calcular(df_desempeno, PESOS_PONDERACION)
    res_potencial = motor_potencial.leer_potencial(ruta)
    metadata = motor_360.leer_metadata_organizacional(ruta)
    if not metadata.empty:
        res_360["df_global"] = motor_360.completar_metadata_colaboradores(
            res_360["df_global"],
            metadata,
            "colaborador",
            "email_colaborador",
        )
        res_360["df_metadata"] = metadata
        res_potencial["df_personas"] = motor_360.completar_metadata_colaboradores(
            res_potencial["df_personas"],
            metadata,
            "colaborador",
            "correo",
        )
        res_potencial["df_competencias"] = motor_360.completar_metadata_colaboradores(
            res_potencial["df_competencias"],
            metadata,
            "colaborador",
            "correo",
        )
    return (
        res_360,
        res_potencial,
        motor_objetivos.leer_objetivos(ruta),
    )


@st.cache_data(show_spinner="Cargando base de talento desde Neon...")
def cargar_base_neon(database_url: str, schema: str, version_carga: int) -> tuple[dict, dict, dict]:
    """Carga ambas fases desde PostgreSQL y recalcula las metricas del dashboard."""
    del version_carga
    df_desempeno, res_potencial, res_objetivos = data_db.leer_base_dashboard(database_url, schema)
    metadata = motor_360.leer_metadata_organizacional(ARCHIVO_BASE)
    if not metadata.empty:
        df_desempeno = motor_360.completar_metadata_colaboradores(
            df_desempeno,
            metadata,
            "nombre_colaborador",
            "email_colaborador",
        )
        res_potencial["df_personas"] = motor_360.completar_metadata_colaboradores(
            res_potencial["df_personas"],
            metadata,
            "colaborador",
            "correo",
        )
        res_potencial["df_competencias"] = motor_360.completar_metadata_colaboradores(
            res_potencial["df_competencias"],
            metadata,
            "colaborador",
            "correo",
        )
    return calcular(df_desempeno, PESOS_PONDERACION), res_potencial, res_objetivos


def cargar_datos_dashboard() -> tuple[dict, dict, dict, dict]:
    fuente = resolver_fuente_datos()
    if fuente == "excel":
        if not ARCHIVO_BASE.exists():
            raise FileNotFoundError(f"No se encontro el archivo base: {ARCHIVO_BASE.name}")
        res_local, potencial_local, objetivos_local = cargar_base_excel(
            str(ARCHIVO_BASE), ARCHIVO_BASE.stat().st_mtime_ns, VERSION_CARGA_BASE
        )
        return res_local, potencial_local, objetivos_local, {
            "tipo": "excel",
            "nombre": ARCHIVO_BASE.name,
            "detalle": "Desempeño - Potencial",
        }

    try:
        database_url = data_db.resolver_database_url(st.secrets)
        schema = str(leer_config_app("DB_SCHEMA", "public"))
        res_db, potencial_db, objetivos_db = cargar_base_neon(database_url, schema, VERSION_CARGA_DB)
        return res_db, potencial_db, objetivos_db, {
            "tipo": "neon",
            "nombre": "Neon PostgreSQL",
            "detalle": f"schema: {schema}",
        }
    except ModuleNotFoundError as exc:
        if exc.name == "psycopg" and ARCHIVO_BASE.exists():
            res_local, potencial_local, objetivos_local = cargar_base_excel(
                str(ARCHIVO_BASE), ARCHIVO_BASE.stat().st_mtime_ns, VERSION_CARGA_BASE
            )
            return res_local, potencial_local, objetivos_local, {
                "tipo": "excel",
                "nombre": ARCHIVO_BASE.name,
                "detalle": "Excel local (fallback: falta psycopg)",
            }
        raise


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# GRÃFICOS
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def fig_escala(df_global: pd.DataFrame) -> go.Figure:
    counts = [len(df_global[df_global["escala_idx"] == i]) for i in range(len(ESCALA_LABELS))]
    max_count = max(counts) if counts else 0
    x_max = max(5, int(np.ceil(max_count * 1.12)))
    layout = PLOTLY_LAYOUT.copy()
    layout["margin"] = dict(l=170, r=48, t=18, b=36)
    fig = go.Figure(go.Bar(
        x=counts,
        y=ESCALA_LABELS,
        orientation="h",
        marker_color=ESCALA_COLORES,
        text=counts,
        textposition="outside",
        cliponaxis=False,
        hovertemplate="%{y}<br>%{x} colaboradores<extra></extra>",
    ))
    fig.update_layout(
        **layout,
        height=260,
        xaxis=dict(
            title="Colaboradores",
            range=[0, x_max],
            gridcolor="#f0eef8",
            rangemode="tozero",
        ),
        yaxis=dict(
            title="",
            autorange="reversed",
            tickfont_size=12,
        ),
        showlegend=False,
    )
    return fig


def fig_relaciones(rel_prom: dict) -> go.Figure:
    tipos  = [t for t in TIPO_LABEL if t in rel_prom]
    labels = [TIPO_LABEL[t] for t in tipos]
    vals   = [rel_prom[t] for t in tipos]

    Y_MIN, Y_MAX = 60, 102

    fig = go.Figure()

    # â”€â”€ Bandas de fondo por escala â”€â”€
    bandas = [
        (100, Y_MAX, "rgba(75, 97, 209, 0.12)", "Talento estrella"),
        (90, 100, "rgba(0, 138, 75, 0.12)", "Alto Desempeño"),
        (85, 90, "rgba(0, 184, 135, 0.12)", "Satisfactorio"),
        (75, 85, "rgba(244, 179, 36, 0.12)", "En desarrollo"),
        (Y_MIN, 75, "rgba(213, 0, 93, 0.10)", "Espacio de crecimiento"),
    ]
    for y0, y1, color, nombre in bandas:
        fig.add_hrect(
            y0=y0, y1=y1,
            fillcolor=color,
            line_width=0,
            annotation_text=nombre,
            annotation_position="right",
            annotation=dict(font_size=9, font_color="#999", xanchor="left"),
        )

    # â”€â”€ LÃ­neas de corte sutiles â”€â”€
    for corte in [75, 85, 90, 100]:
        fig.add_hline(
            y=corte,
            line_dash="dot",
            line_color="rgba(0,0,0,0.15)",
            line_width=1,
        )

    # â”€â”€ LÃ­nea de valores con marcadores â”€â”€
    fig.add_trace(go.Scatter(
        x=labels, y=vals,
        mode="lines+markers+text",
        line=dict(color="#1a1a3e", width=2.5),
        marker=dict(
            color=[score_color(v) for v in vals],
            size=10,
            line=dict(color="white", width=2),
        ),
        text=[f"{v:.2f}" for v in vals],
        textposition="top center",
        textfont=dict(size=12, color="#1a1a3e", family="DM Sans"),
        showlegend=False,
    ))

    fig.update_layout(
        **PLOTLY_LAYOUT,
        height=300,
        yaxis=dict(range=[Y_MIN, Y_MAX], gridcolor="rgba(0,0,0,0)", tickfont_size=11),
        xaxis=dict(tickfont_size=12, tickfont_color="#1a1a3e"),
    )
    return fig


def fig_comp_barras(df_comp_prom: pd.DataFrame) -> go.Figure:
    df = df_comp_prom.sort_values("prom_comp")
    fig = go.Figure(go.Bar(
        y=df["competencia"], x=df["prom_comp"],
        orientation="h",
        marker_color=[score_color(v) for v in df["prom_comp"]],
        text=[f"{v:.2f}" for v in df["prom_comp"]],
        textposition="outside",
    ))
    fig.update_layout(**PLOTLY_LAYOUT,
                      height=max(260, len(df) * 34 + 60),
                      xaxis=dict(range=[60, 105], gridcolor="#f0eef8"),
                      yaxis=dict(tickfont_size=11))
    return fig


def fig_radar(df_comp_prom: pd.DataFrame) -> go.Figure:
    cats  = df_comp_prom["competencia"].tolist()
    vals  = df_comp_prom["prom_comp"].tolist()
    cats  += [cats[0]]
    vals  += [vals[0]]

    fig = go.Figure(go.Scatterpolar(
        r=vals, theta=cats,
        fill="toself",
        line_color="#6c3fc5",
        fillcolor="rgba(108,63,197,0.12)",
        marker=dict(color="#6c3fc5", size=5),
    ))
    fig.update_layout(
        **PLOTLY_LAYOUT,
        height=340,
        polar=dict(
            radialaxis=dict(range=[60, 100], tickfont_size=9, gridcolor="#e8e4f4"),
            angularaxis=dict(tickfont_size=10),
        ),
    )
    return fig


def fig_rel_comp(comp_rel: dict, competencias: list, tipo_labels: dict | None = None) -> go.Figure:
    tipos = [t for t in TIPO_LABEL if t in comp_rel]
    tipo_labels = tipo_labels or TIPO_LABEL
    fig = go.Figure()
    for tipo in tipos:
        vals = [comp_rel[tipo].get(c, None) for c in competencias]
        fig.add_trace(go.Bar(
            name=tipo_labels.get(tipo, TIPO_LABEL[tipo]), x=competencias, y=vals,
            marker_color=COLORES_TIPO.get(tipo, "#888"),
        ))
    layout = PLOTLY_LAYOUT.copy()
    layout["margin"] = dict(l=12, r=12, t=56, b=92)
    fig.update_layout(
        **layout,
        height=330,
        barmode="group",
        legend=dict(
            orientation="h",
            x=0,
            xanchor="left",
            y=1.18,
            yanchor="bottom",
            font_size=11,
        ),
        yaxis=dict(range=[60, 105], gridcolor="#f0eef8"),
        xaxis=dict(tickfont_size=10, tickangle=-35),
    )
    return fig


def fig_colab_ranking(
    df_global: pd.DataFrame,
    height: int | None = None,
    colaborador_sel: str | None = None,
) -> go.Figure:
    df = df_global.sort_values("global")
    line_colors = [
        "#1a1a3e" if colaborador_sel and colab == colaborador_sel else "rgba(0,0,0,0)"
        for colab in df["colaborador"]
    ]
    line_widths = [
        2 if colaborador_sel and colab == colaborador_sel else 0
        for colab in df["colaborador"]
    ]
    fig = go.Figure(go.Bar(
        y=df["colaborador"], x=df["global"],
        orientation="h",
        marker_color=[score_color(v) for v in df["global"]],
        marker_line_color=line_colors,
        marker_line_width=line_widths,
        text=[f"{v:.2f}" for v in df["global"]],
        textposition="outside",
    ))
    layout = PLOTLY_LAYOUT.copy()
    layout["margin"] = dict(l=12, r=48, t=24, b=24)
    fig.update_layout(
        **layout,
        height=height or max(220, min(520, len(df) * 28 + 80)),
        xaxis=dict(range=[60, 105], gridcolor="#f0eef8"),
        yaxis=dict(tickfont_size=10),
    )
    return fig


def fig_colab_radar(df_comp: pd.DataFrame, colaborador: str) -> go.Figure:
    df = df_comp[df_comp["colaborador"] == colaborador]
    cats = df["competencia"].tolist() + [df["competencia"].iloc[0]]
    vals = df["puntaje"].tolist()    + [df["puntaje"].iloc[0]]

    fig = go.Figure(go.Scatterpolar(
        r=vals, theta=cats,
        fill="toself",
        line_color="#e8357a",
        fillcolor="rgba(232,53,122,0.10)",
        marker=dict(color="#e8357a", size=5),
    ))
    fig.update_layout(
        **PLOTLY_LAYOUT,
        height=300,
        polar=dict(
            radialaxis=dict(range=[60, 100], tickfont_size=9, gridcolor="#e8e4f4"),
            angularaxis=dict(tickfont_size=10),
        ),
    )
    return fig


def fig_objetivos_distribucion(df_colab: pd.DataFrame) -> go.Figure:
    etiquetas = df_colab["puntaje"].map(escala_objetivos_label)
    conteos = etiquetas.value_counts().reindex(OBJETIVOS_ESCALA_ORDEN, fill_value=0)
    fig = go.Figure(go.Bar(
        x=OBJETIVOS_ESCALA_ORDEN,
        y=conteos.values,
        marker_color=[OBJETIVOS_ESCALA_COLORES[label] for label in OBJETIVOS_ESCALA_ORDEN],
        text=conteos.values,
        textposition="outside",
        hovertemplate="%{x}<br>%{y} colaboradores<extra></extra>",
    ))
    fig.update_layout(
        **PLOTLY_LAYOUT,
        height=280,
        showlegend=False,
        xaxis=dict(tickfont_size=11),
        yaxis=dict(title="Colaboradores", gridcolor="#f0eef8", rangemode="tozero"),
    )
    return fig


def fig_objetivos_bullet(promedio: float) -> go.Figure:
    color_resultado = OBJETIVOS_ESCALA_COLORES.get(
        escala_objetivos_label(promedio),
        "#1f3f77",
    )
    fig = go.Figure(go.Indicator(
        mode="number+gauge",
        value=float(promedio),
        number={"valueformat": ".0f", "font": {"size": 18, "color": "#1a1a3e"}},
        gauge={
            "shape": "bullet",
            "axis": {"range": [0, 100], "tickmode": "array", "tickvals": [0, 25, 50, 75, 85, 90, 100]},
            "bar": {"color": color_resultado, "thickness": 0.42},
            "steps": [
                {"range": [0, 75], "color": "#f7bfd7"},
                {"range": [75, 85], "color": "#fbe1a7"},
                {"range": [85, 90], "color": "#a9edd9"},
                {"range": [90, 100], "color": "#a8ddc2"},
            ],
        },
        domain={"x": [0.05, 0.95], "y": [0.2, 0.85]},
        title={"text": "Evaluación Objetivos", "font": {"size": 16}},
    ))
    fig.update_layout(
        height=190,
        margin=dict(l=18, r=18, t=30, b=12),
        paper_bgcolor="white",
        font_family="DM Sans",
    )
    return fig


def fig_objetivos_dimension(
    df_dim: pd.DataFrame,
    dimension: str,
    mostrar_bandas: bool = True,
    decimales: int = 0,
    colorear_por_escala: bool = False,
) -> go.Figure:
    datos = df_dim.sort_values("puntaje", ascending=True)
    colores = (
        [
            OBJETIVOS_ESCALA_COLORES.get(
                escala_objetivos_label(puntaje),
                "#1f3f77",
            )
            for puntaje in datos["puntaje"]
        ]
        if colorear_por_escala
        else "#1f3f77"
    )
    fig = go.Figure(go.Bar(
        y=datos[dimension],
        x=datos["puntaje"],
        orientation="h",
        marker_color=colores,
        text=[f"{v:.{decimales}f}" for v in datos["puntaje"]],
        textposition="outside",
        customdata=datos[["colaboradores", "participacion"]],
        hovertemplate="%{y}<br>Promedio %{x:.2f}<br>%{customdata[0]} colaboradores<br>%{customdata[1]:.1%}<extra></extra>",
    ))
    if mostrar_bandas:
        fig.add_vrect(x0=50, x1=70, fillcolor="#ff7276", opacity=0.75, line_width=0, layer="below")
        fig.add_vrect(x0=70, x1=80, fillcolor="#ffe180", opacity=0.85, line_width=0, layer="below")
        fig.add_vrect(x0=80, x1=90, fillcolor="#7fd3a1", opacity=0.78, line_width=0, layer="below")
        fig.add_vrect(x0=90, x1=100, fillcolor="#82a9e6", opacity=0.85, line_width=0, layer="below")
    layout = PLOTLY_LAYOUT.copy()
    layout["margin"] = dict(l=20, r=42, t=34, b=32)
    fig.update_layout(
        **layout,
        height=max(260, len(datos) * 38 + 90),
        xaxis=dict(range=[50, 100], tickmode="array", tickvals=[50, 60, 70, 80, 90, 100], side="top"),
        yaxis=dict(title="", tickfont_size=11),
        showlegend=False,
    )
    return fig


def fig_objetivos_cargos(df_cargos: pd.DataFrame, top_n: int = 15) -> go.Figure:
    datos = df_cargos.sort_values("puntaje", ascending=True).tail(top_n)
    fig = go.Figure(go.Bar(
        y=datos["cargo_objetivo"],
        x=datos["puntaje"],
        orientation="h",
        marker_color=[score_color(v) for v in datos["puntaje"]],
        text=[f"{v:.2f}" for v in datos["puntaje"]],
        textposition="outside",
        customdata=datos[["colaboradores", "objetivos"]],
        hovertemplate="%{y}<br>Puntaje %{x:.2f}<br>%{customdata[0]} colaboradores<br>%{customdata[1]} objetivos<extra></extra>",
    ))
    layout = PLOTLY_LAYOUT.copy()
    layout["margin"] = dict(l=12, r=52, t=18, b=36)
    fig.update_layout(
        **layout,
        height=max(320, len(datos) * 30 + 80),
        xaxis=dict(title="Puntaje", range=[0, 105], gridcolor="#f0eef8"),
        yaxis=dict(tickfont_size=10),
        showlegend=False,
    )
    return fig


def fig_objetivos_colaboradores(df_colab: pd.DataFrame, top_n: int = 20) -> go.Figure:
    datos = df_colab.sort_values("puntaje", ascending=True).tail(top_n)
    fig = go.Figure(go.Bar(
        y=datos["colaborador"],
        x=datos["puntaje"],
        orientation="h",
        marker_color=[score_color(v) for v in datos["puntaje"]],
        text=[f"{v:.2f}" for v in datos["puntaje"]],
        textposition="outside",
        customdata=datos[["cargo_objetivo", "jefe", "objetivos"]],
        hovertemplate="%{y}<br>Puntaje %{x:.2f}<br>%{customdata[0]}<br>Jefe: %{customdata[1]}<br>%{customdata[2]} objetivos<extra></extra>",
    ))
    layout = PLOTLY_LAYOUT.copy()
    layout["margin"] = dict(l=12, r=52, t=18, b=36)
    fig.update_layout(
        **layout,
        height=max(360, len(datos) * 28 + 80),
        xaxis=dict(title="Puntaje", range=[0, 105], gridcolor="#f0eef8"),
        yaxis=dict(tickfont_size=10),
        showlegend=False,
    )
    return fig


def enriquecer_objetivos(
    df_colab: pd.DataFrame,
    df_fuente: pd.DataFrame,
    df_potencial_personas: pd.DataFrame,
) -> pd.DataFrame:
    df = df_colab.copy()
    potencial_cols = ["colaborador", "empresa", "pais", "grupo"]
    potencial = df_potencial_personas[
        [col for col in potencial_cols if col in df_potencial_personas.columns]
    ].copy()
    if not potencial.empty:
        potencial["match_nombre"] = potencial["colaborador"].map(normalizar_nombre_match)
        potencial = potencial.drop_duplicates("match_nombre")
        df["match_nombre"] = df["colaborador"].map(normalizar_nombre_match)
        df = df.merge(
            potencial.drop(columns=["colaborador"], errors="ignore"),
            on="match_nombre",
            how="left",
        )
    evaluadores = set(df_fuente["nombre_evaluador"].dropna().map(normalizar_nombre_match))
    df["gente_a_cargo"] = df["colaborador"].map(
        lambda nombre: "SI" if normalizar_nombre_match(nombre) in evaluadores else "NO"
    )
    for col in ["grupo", "empresa", "pais"]:
        if col not in df.columns:
            df[col] = "Sin dato"
        df[col] = df[col].fillna("Sin dato").replace("", "Sin dato")
    df["grupo"] = df["grupo"].astype(str).str.title()
    df["grupo"] = df["grupo"].replace({
        "Tácticos": "Tácticos",
        "No Aplica": "No aplica",
    })
    return df


def resumen_dimension_objetivos(df_colab: pd.DataFrame, dimension: str) -> pd.DataFrame:
    if df_colab.empty:
        return pd.DataFrame(columns=[dimension, "puntaje", "colaboradores", "participacion"])
    total = max(1, df_colab["colaborador"].nunique())
    resumen = (
        df_colab.groupby(dimension, dropna=False)
        .agg(
            puntaje=("puntaje", "mean"),
            colaboradores=("colaborador", "nunique"),
        )
        .reset_index()
    )
    resumen["participacion"] = resumen["colaboradores"] / total
    return resumen.sort_values(["puntaje", "colaboradores"], ascending=[False, False])


def render_tabla_dimension_objetivos(
    titulo: str,
    df_resumen: pd.DataFrame,
    dimension: str,
    total_colab: int,
    promedio: float,
    altura_max: int | None = None,
    encabezado_promedio: str = "Promedio de Objetivos",
    decimales: int = 0,
) -> None:
    st.markdown(f"**{titulo}**")
    estilo = "overflow-x:auto"
    if altura_max is not None:
        estilo += f";max-height:{altura_max}px;overflow-y:auto"
    html = f'<div style="{estilo}"><table class="ev-table">'
    html += (
        f"<thead><tr><th>{titulo}</th><th style='text-align:right'>{encabezado_promedio}</th>"
        "<th style='text-align:right'>Colaboradores</th><th style='text-align:right'>Participación</th></tr></thead><tbody>"
    )
    for _, fila in df_resumen.iterrows():
        etiqueta = html_lib.escape(str(fila[dimension]))
        html += (
            "<tr>"
            f"<td style='font-weight:600'>{etiqueta}</td>"
            f"<td style='text-align:right;color:#185fa5;font-weight:700'>{fila['puntaje']:.{decimales}f}</td>"
            f"<td style='text-align:right'>{int(fila['colaboradores'])}</td>"
            f"<td style='text-align:right'>{fila['participacion']:.0%}</td>"
            "</tr>"
        )
    html += (
        "<tr style='font-weight:700;background:#f8f7fc'>"
        "<td>Total general</td>"
        f"<td style='text-align:right;color:#185fa5'>{promedio:.{decimales}f}</td>"
        f"<td style='text-align:right'>{total_colab}</td>"
        "<td style='text-align:right'>100%</td>"
        "</tr></tbody></table></div>"
    )
    st.markdown(html, unsafe_allow_html=True)


def render_tabla_escala_objetivos(df_colab: pd.DataFrame) -> None:
    st.markdown("**Escala de objetivos**")
    etiquetas = df_colab["puntaje"].map(escala_objetivos_label)
    conteos = etiquetas.value_counts().reindex(OBJETIVOS_ESCALA_ORDEN, fill_value=0)
    html = '<div style="overflow-x:auto"><table class="ev-table">'
    html += "<thead><tr><th>Escala de objetivos</th><th style='text-align:right'>Colaboradores</th></tr></thead><tbody>"
    for etiqueta, conteo in conteos.items():
        html += (
            "<tr>"
            f"<td style='font-weight:600;color:{OBJETIVOS_ESCALA_COLORES[etiqueta]}'>{etiqueta}</td>"
            f"<td style='text-align:right'>{int(conteo)}</td>"
            "</tr>"
        )
    html += (
        "<tr style='font-weight:700;background:#f8f7fc'>"
        f"<td>Total general</td><td style='text-align:right'>{int(conteos.sum())}</td>"
        "</tr></tbody></table></div>"
    )
    st.markdown(html, unsafe_allow_html=True)


def preparar_resultado_integrado(
    df_360_global: pd.DataFrame,
    df_obj_colab: pd.DataFrame,
    df_potencial: pd.DataFrame,
    df_obj_fuente: pd.DataFrame,
    df_360_metadata: pd.DataFrame | None = None,
) -> pd.DataFrame:
    # Mantiene una sola regla de integración para dashboard, Excel y PDFs.
    return motor_integrado.preparar_resultado_integrado(
        df_360_global,
        df_obj_colab,
        df_potencial,
        df_obj_fuente,
        df_360_metadata,
    )


def _preparar_resultado_integrado_legacy(
    df_360_global: pd.DataFrame,
    df_obj_colab: pd.DataFrame,
    df_potencial: pd.DataFrame,
    df_obj_fuente: pd.DataFrame,
    df_360_metadata: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Implementación anterior conservada para comparación durante la migración."""
    df_360_para_integrar = df_360_global.copy()
    if df_360_metadata is not None and not df_360_metadata.empty:
        correos_con_puntaje = set(
            df_360_para_integrar.get(
                "email_colaborador", pd.Series(dtype=object)
            ).map(normalizar_correo)
        )
        nombres_con_puntaje = set(
            df_360_para_integrar.get(
                "colaborador", pd.Series(dtype=object)
            ).map(normalizar_nombre_match)
        )
        metadata_adicional = df_360_metadata[
            ~df_360_metadata["email_colaborador"].map(normalizar_correo).isin(
                correos_con_puntaje
            )
            & ~df_360_metadata["colaborador"].map(normalizar_nombre_match).isin(
                nombres_con_puntaje
            )
        ].copy()
        if not metadata_adicional.empty:
            metadata_adicional["global"] = np.nan
            df_360_para_integrar = pd.concat(
                [df_360_para_integrar, metadata_adicional],
                ignore_index=True,
                sort=False,
            )
    base_360_cols = ["colaborador", "global"] + [
        col
        for col in [
            "email_colaborador", "correo", "empresa", "pais", "area", "grupo"
        ]
        if col in df_360_para_integrar.columns
    ]
    base_360 = df_360_para_integrar[base_360_cols].rename(
        columns={
            "colaborador": "colaborador_360",
            "global": "evd_360",
            "empresa": "empresa_360",
            "pais": "pais_360",
            "area": "area_360",
            "grupo": "grupo_360",
        }
    ).copy()
    base_obj_cols = [col for col in ["colaborador", "email_colaborador", "puntaje", "cargo_objetivo", "jefe"] if col in df_obj_colab.columns]
    base_obj = df_obj_colab[base_obj_cols].rename(
        columns={"colaborador": "colaborador_obj", "puntaje": "objetivos"}
    ).copy()
    base_pot = df_potencial[
        [
            col for col in [
                "colaborador", "correo", "correo_potencial", "correo_instancia",
                "evaluacion_potencial", "empresa", "pais", "grupo", "cargo", "area", "jefe"
            ]
            if col in df_potencial.columns
        ]
    ].rename(columns={"colaborador": "colaborador_pot", "evaluacion_potencial": "potencial"}).copy()

    base_360 = expandir_llaves_match(
        base_360,
        ["email_colaborador", "correo"],
        "colaborador_360",
        list(base_360.columns),
    )
    base_obj = expandir_llaves_match(
        base_obj,
        ["email_colaborador"],
        "colaborador_obj",
        list(base_obj.columns),
    )
    base_pot = expandir_llaves_match(
        base_pot,
        ["correo", "correo_potencial", "correo_instancia"],
        "colaborador_pot",
        list(base_pot.columns),
    )

    integrado = base_360.merge(base_obj, on="match_key", how="outer")
    integrado = integrado.merge(base_pot, on="match_key", how="outer")
    integrado["colaborador"] = integrado["colaborador_360"].combine_first(integrado["colaborador_obj"])
    integrado["colaborador"] = integrado["colaborador"].combine_first(integrado["colaborador_pot"])
    integrado = integrado.drop_duplicates("colaborador")

    sin_registro_potencial = (
        integrado["colaborador_pot"].isna()
        if "colaborador_pot" in integrado.columns
        else pd.Series(True, index=integrado.index)
    )
    for campo in ["empresa", "pais", "area", "grupo"]:
        campo_360 = f"{campo}_360"
        if campo not in integrado.columns:
            integrado[campo] = pd.NA
        if campo_360 in integrado.columns:
            integrado.loc[sin_registro_potencial, campo] = integrado.loc[
                sin_registro_potencial, campo
            ].combine_first(
                integrado.loc[sin_registro_potencial, campo_360]
            )

    evaluadores = set(df_obj_fuente["nombre_evaluador"].dropna().map(normalizar_nombre_match)) if not df_obj_fuente.empty else set()
    integrado["gente_a_cargo"] = integrado["colaborador"].map(
        lambda nombre: "SI" if normalizar_nombre_match(nombre) in evaluadores else "NO"
    )

    def etiqueta(row):
        tiene_360 = pd.notna(row.get("evd_360")) and row.get("evd_360") > 0
        tiene_obj = pd.notna(row.get("objetivos")) and row.get("objetivos") > 0
        tiene_pot = pd.notna(row.get("potencial")) and row.get("potencial") > 0
        if tiene_360 and tiene_obj and tiene_pot:
            return "Completa"
        if tiene_360 and tiene_obj:
            return "360+obj"
        if tiene_360 and tiene_pot:
            return "360+pot"
        if tiene_obj and tiene_pot:
            return "obj+pot"
        if tiene_360:
            return "Solo 360"
        if tiene_obj:
            return "Solo obj"
        if tiene_pot:
            return "Solo pot"
        return ""

    integrado["etiqueta_integrada"] = integrado.apply(etiqueta, axis=1)

    def calcular_integrada(row):
        etiqueta_val = row["etiqueta_integrada"]
        if etiqueta_val == "Completa":
            return round(row["evd_360"] * 0.30 + row["objetivos"] * 0.30 + row["potencial"] * 0.40, 0)
        if etiqueta_val == "360+obj":
            return round(row["evd_360"] * 0.50 + row["objetivos"] * 0.50, 0)
        if etiqueta_val == "360+pot":
            return round(row["evd_360"] * 0.60 + row["potencial"] * 0.40, 0)
        if etiqueta_val == "obj+pot":
            return round(row["objetivos"] * 0.60 + row["potencial"] * 0.40, 0)
        return np.nan

    integrado["integrada"] = integrado.apply(calcular_integrada, axis=1)
    integrado["escala_integrada"] = integrado["integrada"].apply(
        lambda valor: escala_objetivos_label(valor) if pd.notna(valor) else ""
    )
    for col in ["empresa", "pais", "grupo", "cargo_objetivo", "jefe"]:
        if col not in integrado.columns:
            integrado[col] = "Sin dato"
        integrado[col] = integrado[col].fillna("Sin dato").replace("", "Sin dato")
    return integrado.sort_values("integrada", ascending=False, na_position="last")


def resumen_dimension_integrada(df: pd.DataFrame, dimension: str, valor_col: str = "integrada") -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=[dimension, "puntaje", "colaboradores", "participacion"])
    total = max(1, df["colaborador"].nunique())
    resumen = (
        df.groupby(dimension, dropna=False)
        .agg(
            puntaje=(valor_col, "mean"),
            colaboradores=("colaborador", "nunique"),
        )
        .reset_index()
    )
    resumen["participacion"] = resumen["colaboradores"] / total
    return resumen.sort_values(["puntaje", "colaboradores"], ascending=[False, False])


def fig_integrada_bullet(promedio: float) -> go.Figure:
    fig = fig_objetivos_bullet(promedio)
    fig.data[0].gauge.steps = ()
    fig.data[0].title.text = ""
    fig.data[0].number.valueformat = ".2f"
    return fig


def fig_integrada_escala(df: pd.DataFrame) -> go.Figure:
    conteos = df["escala_integrada"].value_counts().reindex(OBJETIVOS_ESCALA_ORDEN, fill_value=0)
    fig = go.Figure(go.Bar(
        x=OBJETIVOS_ESCALA_ORDEN,
        y=conteos.values,
        marker_color=[OBJETIVOS_ESCALA_COLORES[label] for label in OBJETIVOS_ESCALA_ORDEN],
        text=conteos.values,
        textposition="outside",
        hovertemplate="%{x}<br>%{y} colaboradores<extra></extra>",
    ))
    fig.update_layout(
        **PLOTLY_LAYOUT,
        height=330,
        showlegend=False,
        xaxis=dict(tickfont_size=10),
        yaxis=dict(title="Colaboradores", gridcolor="#f0eef8", rangemode="tozero"),
    )
    return fig


CONFIG_INTEGRADO = {
    "Completa": {
        "tab": "Desempeño + Objetivos + Competencias",
        "titulo": "Resultados integrados Desempeño + Objetivos + Competencias",
        "promedio": "Promedio Completa",
        "colaboradores": "Colaboradores Completa",
        "sub": "Desempeño 30% · Objetivos 30% · Competencias 40%",
        "detalle": [("evd_360", "Desempeño"), ("objetivos", "Objetivos"), ("potencial", "Competencias")],
    },
    "360+obj": {
        "tab": "Desempeño + Objetivos",
        "titulo": "Resultados integrados Desempeño + Objetivos",
        "promedio": "Promedio 360+obj",
        "colaboradores": "Colaboradores 360+obj",
        "sub": "Desempeño 50% · Objetivos 50%",
        "detalle": [("evd_360", "Desempeño"), ("objetivos", "Objetivos")],
    },
    "360+pot": {
        "tab": "Desempeño + Competencias",
        "titulo": "Resultados integrados Desempeño + Competencias",
        "promedio": "Promedio 360+pot",
        "colaboradores": "Colaboradores 360+pot",
        "sub": "Desempeño 60% · Competencias 40%",
        "detalle": [("evd_360", "Desempeño"), ("potencial", "Competencias")],
    },
    "obj+pot": {
        "tab": "Objetivos + Competencias",
        "titulo": "Resultados integrados Objetivos + Competencias",
        "promedio": "Promedio obj+pot",
        "colaboradores": "Colaboradores obj+pot",
        "sub": "Objetivos 60% · Competencias 40%",
        "detalle": [("objetivos", "Objetivos"), ("potencial", "Competencias")],
    },
}


def render_tabla_escala_integrada(df: pd.DataFrame, titulo: str) -> None:
    conteos = df["escala_integrada"].value_counts().reindex(OBJETIVOS_ESCALA_ORDEN, fill_value=0)
    html = '<div style="overflow-x:auto"><table class="ev-table">'
    html += f"<thead><tr><th>{html_lib.escape(titulo)}</th><th style='text-align:right'>Colaboradores</th></tr></thead><tbody>"
    for etiqueta, conteo in conteos.items():
        html += (
            "<tr>"
            f"<td style='font-weight:600;color:{OBJETIVOS_ESCALA_COLORES[etiqueta]}'>{etiqueta}</td>"
            f"<td style='text-align:right'>{int(conteo)}</td>"
            "</tr>"
        )
    html += (
        "<tr style='font-weight:700;background:#f8f7fc'>"
        f"<td>Total general</td><td style='text-align:right'>{int(conteos.sum())}</td>"
        "</tr></tbody></table></div>"
    )
    st.markdown(html, unsafe_allow_html=True)


def dimension_disponible(df: pd.DataFrame, candidatas: list[str]) -> list[str]:
    disponibles = []
    for col in candidatas:
        if col in df.columns and df[col].fillna("Sin dato").ne("Sin dato").any():
            disponibles.append(col)
    return disponibles


def render_resultado_integrado_tipo(
    df_base: pd.DataFrame,
    etiqueta: str,
    universo_total: int,
) -> None:
    config = CONFIG_INTEGRADO[etiqueta]
    df_tipo_base = df_base[df_base["etiqueta_integrada"] == etiqueta].copy()
    if df_tipo_base.empty:
        st.info(f"No hay colaboradores para {config['tab']} con la base actual.")
        return

    key_base = etiqueta.replace("+", "_").replace(" ", "_").lower()
    filtro_1, filtro_2, filtro_3 = st.columns(3)
    with filtro_1:
        filtro_colabs = st.multiselect(
            "Colaboradores",
            sorted(df_tipo_base["colaborador"].dropna().unique().tolist()),
            key=f"filtro_integrado_{key_base}_colabs",
            placeholder=f"Todos los colaboradores {config['tab']}",
        )
    with filtro_2:
        filtro_gente = st.multiselect(
            "Gente a cargo",
            sorted(df_tipo_base["gente_a_cargo"].dropna().unique().tolist()),
            key=f"filtro_integrado_{key_base}_gente",
            placeholder="Todos",
        )
    with filtro_3:
        filtro_escala = st.multiselect(
            "Escala integrada",
            OBJETIVOS_ESCALA_ORDEN,
            key=f"filtro_integrado_{key_base}_escala",
            placeholder="Todas las escalas",
        )

    df_tipo = df_tipo_base.copy()
    if filtro_colabs:
        df_tipo = df_tipo[df_tipo["colaborador"].isin(filtro_colabs)]
    if filtro_gente:
        df_tipo = df_tipo[df_tipo["gente_a_cargo"].isin(filtro_gente)]
    if filtro_escala:
        df_tipo = df_tipo[df_tipo["escala_integrada"].isin(filtro_escala)]

    promedio = float(df_tipo["integrada"].mean()) if len(df_tipo) else 0.0
    total = len(df_tipo)
    alto = int((df_tipo["integrada"] >= 90).sum())

    kpi_i1, kpi_i2, kpi_i3, kpi_i4 = st.columns(4)
    with kpi_i1:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">{config['promedio']}</div>
            <div class="kpi-value gradient">{promedio:.2f}</div>
            <div class="kpi-sub">{config['sub']}</div>
        </div>""", unsafe_allow_html=True)
    with kpi_i2:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">{config['colaboradores']}</div>
            <div class="kpi-value">{total}</div>
            <div class="kpi-sub">con fuentes disponibles</div>
        </div>""", unsafe_allow_html=True)
    with kpi_i3:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Alto desempeño o superior</div>
            <div class="kpi-value green">{alto}</div>
            <div class="kpi-sub">integrada >= 90</div>
        </div>""", unsafe_allow_html=True)
    with kpi_i4:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Participación</div>
            <div class="kpi-value">{(total / max(1, universo_total)):.0%}</div>
            <div class="kpi-sub">sobre universo integrado</div>
        </div>""", unsafe_allow_html=True)

    dimensiones = dimension_disponible(df_tipo, ["grupo", "cargo_objetivo", "pais", "empresa", "gente_a_cargo"])
    principal_dim = dimensiones[0] if dimensiones else "gente_a_cargo"
    df_principal_base = df_tipo.copy()
    if principal_dim == "grupo":
        grupos_validos = df_principal_base[principal_dim].astype("string").str.strip()
        df_principal_base = df_principal_base[
            grupos_validos.notna()
            & grupos_validos.ne("")
            & grupos_validos.str.casefold().ne("sin dato")
        ]
    df_principal = resumen_dimension_integrada(df_principal_base, principal_dim)
    total_principal = len(df_principal_base)
    promedio_principal = (
        float(df_principal_base["integrada"].mean())
        if total_principal
        else 0.0
    )

    panel_izq, panel_centro, panel_der = st.columns([0.9, 1.55, 1.1])
    with panel_izq:
        render_tabla_escala_integrada(df_tipo, f"Escala {config['tab']}")
    with panel_centro:
        st.markdown(f"**{config['titulo']}**")
        st.plotly_chart(
            fig_integrada_bullet(promedio),
            use_container_width=True,
            key=f"integrado_bullet_{key_base}",
        )
        st.markdown(f"**Resultado por {principal_dim.replace('_', ' ')}**")
        st.plotly_chart(
            fig_objetivos_dimension(
                df_principal,
                principal_dim,
                mostrar_bandas=False,
                decimales=2,
                colorear_por_escala=True,
            ),
            use_container_width=True,
            key=f"integrado_dimension_{key_base}",
        )
        st.markdown("**Escala integrada**")
        st.plotly_chart(
            fig_integrada_escala(df_tipo),
            use_container_width=True,
            key=f"integrado_escala_{key_base}",
        )
    with panel_der:
        st.markdown(f"**Colaboradores {config['tab']}**")
        html = '<div class="ev-scroll-table"><table class="ev-table">'
        html += "<thead><tr><th>Colaborador</th>"
        for _, label in config["detalle"]:
            html += f"<th style='text-align:right'>{label}</th>"
        html += "<th>Nivel</th><th style='text-align:right'>Integrada</th></tr></thead><tbody>"
        for _, fila in df_tipo.sort_values("integrada", ascending=False).iterrows():
            html += "<tr>"
            html += f"<td style='font-weight:600'>{html_lib.escape(str(fila['colaborador']))}</td>"
            for col, _ in config["detalle"]:
                valor = fila.get(col)
                html += f"<td style='text-align:right'>{valor:.2f}</td>" if pd.notna(valor) else "<td style='text-align:right'>-</td>"
            html += f"<td>{html_lib.escape(str(fila['escala_integrada']))}</td>"
            html += f"<td style='text-align:right'>{chip_html(fila['integrada'])}</td>"
            html += "</tr>"
        html += "</tbody></table></div>"
        st.markdown(html, unsafe_allow_html=True)

        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        render_tabla_dimension_objetivos(
            principal_dim.replace("_", " ").title(),
            df_principal,
            principal_dim,
            total_principal,
            promedio_principal,
            encabezado_promedio="Promedio",
            decimales=2,
        )


def imagen_data_uri(ruta: str | Path) -> str | None:
    path = Path(ruta)
    if not path.exists():
        return None

    mime_por_extension = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".svg": "image/svg+xml",
        ".webp": "image/webp",
    }
    mime = mime_por_extension.get(path.suffix.lower(), "application/octet-stream")
    data_b64 = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{data_b64}"


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# SIDEBAR
requerir_login()

try:
    res, res_potencial, res_objetivos, fuente_datos = cargar_datos_dashboard()
except Exception as exc:
    st.error(f"No se pudo cargar la base del dashboard: {exc}")
    st.stop()

indice_global = construir_indice_colaboradores(res, res_potencial, res_objetivos)

# El Ninebox se clasifica siempre con el universo general, antes de aplicar
# cualquier filtro global. Los filtros posteriores solo reducen las personas
# visibles y nunca recalculan cortes ni cuadrantes.
df_ninebox_general = preparar_ninebox(
    res["df_global"],
    res_potencial["df_personas"],
)
cortes_ninebox_general = (
    cortes_ninebox(df_ninebox_general)
    if len(df_ninebox_general) >= 2
    else None
)
df_ninebox_clasificado_general = (
    clasificar_ninebox(df_ninebox_general, cortes_ninebox_general)
    if cortes_ninebox_general is not None
    else df_ninebox_general.copy()
)

FILTROS_GLOBALES_KEYS = [
    "filtro_global_cargo",
    "filtro_global_jefe",
    "filtro_global_pais",
    "filtro_global_area",
    "filtro_global_grupo",
]


def limpiar_filtros_globales() -> None:
    for key in FILTROS_GLOBALES_KEYS:
        st.session_state[key] = []


with st.sidebar:
    logo_evaluar_uri = imagen_data_uri(
        Path(__file__).resolve().parent / "brand_evaluar_on_dark.svg"
    )
    if logo_evaluar_uri:
        st.markdown(
            f'<div style="padding:16px 8px 0;text-align:center">'
            f'<img src="{logo_evaluar_uri}" alt="Evaluar" '
            f'style="width:100%;max-width:220px;height:auto"></div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown("""
        <div style="padding:16px 8px 0;text-align:center">
            <span style="font-size:26px;font-weight:700;color:white">Evaluar</span>
        </div>
        """, unsafe_allow_html=True)

    # Linea decorativa degradada
    st.markdown('<div class="ev-sidebar-accent"></div>', unsafe_allow_html=True)

    st.markdown("**Fuente de datos**")
    st.markdown(
        f'<div style="font-size:11px;color:rgba(255,255,255,0.65);line-height:1.4">'
        f'{html_lib.escape(fuente_datos["nombre"])}<br>{html_lib.escape(fuente_datos["detalle"])}</div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="ev-sidebar-accent"></div>', unsafe_allow_html=True)

    st.markdown("**Filtros globales**")
    opciones_globales = {
        col: sorted(indice_global[col].dropna().loc[indice_global[col].dropna() != ""].unique().tolist())
        if col in indice_global.columns else []
        for col in ["cargo", "jefe", "pais", "area", "grupo"]
    }
    st.text_input(
        "Empresa",
        value="Speedster",
        disabled=True,
        key="filtro_global_empresa_fija",
    )
    filtro_global_empresa = []
    filtro_global_cargo = st.multiselect(
        "Cargo",
        opciones_globales["cargo"],
        key="filtro_global_cargo",
        placeholder="Todos",
    )
    filtro_global_jefe = st.multiselect(
        "Jefe",
        opciones_globales["jefe"],
        key="filtro_global_jefe",
        placeholder="Todos",
    )
    filtro_global_pais = st.multiselect(
        "País",
        opciones_globales["pais"],
        key="filtro_global_pais",
        placeholder="Todos",
    )
    filtro_global_area = st.multiselect(
        "Área",
        opciones_globales["area"],
        key="filtro_global_area",
        placeholder="Todas",
    )
    filtro_global_grupo = st.multiselect(
        "Grupo",
        opciones_globales["grupo"],
        key="filtro_global_grupo",
        placeholder="Todos",
    )
    filtros_globales = {
        "empresa": filtro_global_empresa,
        "cargo": filtro_global_cargo,
        "jefe": filtro_global_jefe,
        "pais": filtro_global_pais,
        "area": filtro_global_area,
        "grupo": filtro_global_grupo,
    }
    hay_filtros_globales = any(filtros_globales.values())
    indice_global_filtrado = filtrar_indice_global(indice_global, filtros_globales)
    st.markdown(
        f'<div style="font-size:11px;color:rgba(255,255,255,0.65);line-height:1.4">'
        f'Universo activo: {len(indice_global_filtrado):,} colaboradores</div>',
        unsafe_allow_html=True,
    )
    if hay_filtros_globales:
        st.button(
            "Limpiar filtros globales",
            use_container_width=True,
            on_click=limpiar_filtros_globales,
        )

    st.markdown('<div class="ev-sidebar-accent"></div>', unsafe_allow_html=True)

    # Pesos activos - solo lectura
    st.markdown("**Pesos de ponderaci\u00f3n activos**")
    for tipo, peso in PESOS_PONDERACION.items():
        label = TIPO_LABEL.get(tipo, tipo)
        st.markdown(
            f'<div style="display:flex;justify-content:space-between;font-size:12px;'
            f'color:rgba(255,255,255,0.6);padding:3px 0">'
            f'<span>{label}</span>'
            f'<span style="font-weight:600;color:rgba(255,255,255,0.9)">{int(peso*100)}%</span></div>',
            unsafe_allow_html=True,
        )

    st.markdown('<div class="ev-sidebar-accent"></div>', unsafe_allow_html=True)


if hay_filtros_globales:
    correos_globales = set()
    for columna_correo in ["correo_key", "correo_potencial_key", "correo_instancia_key"]:
        if columna_correo in indice_global_filtrado.columns:
            correos_globales.update(
                indice_global_filtrado[columna_correo]
                .dropna()
                .loc[indice_global_filtrado[columna_correo] != ""]
                .tolist()
            )
    nombres_globales = set(
        indice_global_filtrado["colaborador_key"].dropna().loc[indice_global_filtrado["colaborador_key"] != ""]
    )

    df_360_filtrado = filtrar_por_universo(
        res["df_fuente"],
        correos_globales,
        nombres_globales,
        col_correo="email_colaborador",
        col_nombre="nombre_colaborador",
    )
    res = recalcular_360_filtrado(df_360_filtrado)

    df_pot_personas = filtrar_por_universo(
        res_potencial["df_personas"],
        correos_globales,
        nombres_globales,
        col_correo=["correo", "correo_potencial", "correo_instancia"],
        col_nombre="colaborador",
    )
    df_pot_competencias = filtrar_por_universo(
        res_potencial["df_competencias"],
        correos_globales,
        nombres_globales,
        col_correo=["correo", "correo_potencial", "correo_instancia"],
        col_nombre="colaborador",
    )
    catalogo_competencias = res_potencial.get("catalogo_competencias", [])
    res_potencial = {
        **res_potencial,
        "df_personas": df_pot_personas,
        "df_competencias": df_pot_competencias,
        "resumen": resumen_potencial_filtrado(df_pot_personas, df_pot_competencias, catalogo_competencias),
    }

    df_obj_filtrado = filtrar_por_universo(
        res_objetivos["df_fuente"],
        correos_globales,
        nombres_globales,
        col_correo="email_colaborador",
        col_nombre="nombre_colaborador",
    )
    res_objetivos = recalcular_objetivos_desde_fuente(df_obj_filtrado)


# DASHBOARD
resumen_fuente = res.get("resumen_fuente", {})

logo_evaluar_uri = imagen_data_uri(
    Path(__file__).resolve().parent / "brand_evaluar_on_dark.svg"
)
logo_evaluar_html = (
    f'<img src="{logo_evaluar_uri}" alt="Evaluar" '
    f'style="height:32px;width:auto;display:block">'
    if logo_evaluar_uri
    else '<span style="font-size:22px;font-weight:700;color:white">Evaluar</span>'
)
logo_speedster_uri = imagen_data_uri(SPEEDSTER_LOGO)
logo_speedster_html = (
    f'<img class="ev-client-logo" src="{logo_speedster_uri}" alt="Speedster">'
    if logo_speedster_uri
    else '<span style="font-size:22px;font-weight:700;color:#008b8b">Speedster</span>'
)

st.markdown(f"""
<div class="ev-topbar">
    <div style="display:flex;align-items:center">{logo_evaluar_html}</div>
    <div class="ev-client-logos"><div class="ev-client-logo-card">{logo_speedster_html}</div></div>
</div>
""", unsafe_allow_html=True)

FASES = [
    ("fase1", "Evaluaci\u00f3n de Desempeño"),
    ("fase2", "Evaluaci\u00f3n de Competencias"),
    ("fase3", "Evaluaci\u00f3n de Objetivos"),
    ("res_int", "Resultado Integrado"),
    ("ninebox", "Ninebox"),
]


def render_nav_botones(opciones: list[tuple[str, str]], estado_key: str, prefijo_key: str) -> str:
    """Navegacion estable basada en botones, sin depender de tabs internas."""
    claves_validas = {key for key, _ in opciones}
    if estado_key not in st.session_state or st.session_state[estado_key] not in claves_validas:
        st.session_state[estado_key] = opciones[0][0]

    cols = st.columns(len(opciones))
    for col, (key, label) in zip(cols, opciones):
        with col:
            activa = st.session_state[estado_key] == key
            if st.button(
                label,
                key=f"{prefijo_key}_{key}",
                use_container_width=True,
                type="primary" if activa else "secondary",
            ):
                st.session_state[estado_key] = key
                st.rerun()
    return st.session_state[estado_key]


if "fase_activa" not in st.session_state:
    st.session_state.fase_activa = "fase1"

with st.container(key="sticky_phase_nav"):
    render_nav_botones(FASES, "fase_activa", "nav")

fase_activa = st.session_state.fase_activa
st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

if fase_activa == "fase1":
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    todos_colaboradores = sorted(res["df_global"]["colaborador"].tolist())
    with st.container(key="sticky_filtros_desempeno"):
        st.markdown("""
        <div class="ev-filter-container">
            <div class="ev-filter-header">
                <span class="ev-filter-icon"></span>
                <span class="ev-filter-title">Filtros de desempeño</span>
                <span class="ev-filter-hint">Aplican a toda la Fase I</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        filtro_col_f1, filtro_nivel_f1, limpiar_f1 = st.columns([3, 2, 1])
        with filtro_col_f1:
            filtro_colaboradores = st.multiselect(
                "Colaboradores",
                options=todos_colaboradores,
                placeholder="Todos los colaboradores",
                key="filtro_desempeno_colaboradores",
            )
        with filtro_nivel_f1:
            filtro_niveles_desempeno = st.multiselect(
                "Desempeño",
                options=ESCALA_LABELS,
                placeholder="Todos los niveles",
                key="filtro_desempeno_niveles",
            )
        with limpiar_f1:
            st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
            filtros_activos_f1 = bool(filtro_colaboradores or filtro_niveles_desempeno)
            if filtros_activos_f1 and st.button(
                "Limpiar", key="limpiar_filtro_desempeno", use_container_width=True
            ):
                st.session_state.filtro_desempeno_colaboradores = []
                st.session_state.filtro_desempeno_niveles = []
                st.rerun()
    st.markdown('<div class="sticky-controls-spacer"></div>', unsafe_allow_html=True)

    df_global_f = res["df_global"].copy()
    if filtro_colaboradores:
        df_global_f = df_global_f[df_global_f["colaborador"].isin(filtro_colaboradores)].copy()
    if filtro_niveles_desempeno:
        df_global_f = df_global_f[df_global_f["escala"].isin(filtro_niveles_desempeno)].copy()
    colabs_activos = df_global_f["colaborador"].tolist()
    df_comp_f = res["df_comp"][res["df_comp"]["colaborador"].isin(colabs_activos)].copy()
    df_fuente_f = res["df_fuente"][
        res["df_fuente"]["nombre_colaborador"].isin(colabs_activos)
    ].copy()
    df_items_f = motor_360.calcular_items(df_fuente_f, PESOS_PONDERACION)

    if len(df_comp_f):
        df_global_f = (
            df_comp_f.groupby("colaborador")["puntaje"]
            .mean()
            .reset_index()
            .rename(columns={"puntaje": "global"})
            .sort_values("global", ascending=False)
        )
        df_global_f["escala_idx"] = df_global_f["global"].apply(get_escala)
        df_global_f["escala"] = df_global_f["escala_idx"].apply(lambda i: ESCALA_LABELS[i])

        df_comp_prom_f = (
            df_comp_f.groupby("competencia")["puntaje"]
            .mean().reset_index()
            .rename(columns={"puntaje": "prom_comp"})
            .sort_values("prom_comp", ascending=False)
        )
        rel_prom_f = {}
        comp_rel_f = {}
        for tipo in res["tipos_activos"]:
            col_t = f"tipo_{tipo}"
            if col_t in df_comp_f.columns:
                valores_tipo = df_comp_f[col_t].dropna()
                if len(valores_tipo):
                    rel_prom_f[tipo] = valores_tipo.mean()
                comp_rel_f[tipo] = (
                    df_comp_f.groupby("competencia")[col_t].mean().dropna().to_dict()
                )
        tipo_labels_pesos_f = etiquetas_tipo_con_pesos(df_comp_f, list(res["tipos_activos"].keys()))
    else:
        df_comp_prom_f = pd.DataFrame(columns=["competencia", "prom_comp"])
        rel_prom_f = {}
        comp_rel_f = {}
        tipo_labels_pesos_f = TIPO_LABEL

    # KPIs de Fase I
    total_colab = len(df_global_f)
    prom_global = df_global_f["global"].mean() if len(df_global_f) else 0
    n_alto      = len(df_global_f[df_global_f["global"] >= 90])
    n_comp      = len(df_comp_prom_f)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Promedio global 360</div>
            <div class="kpi-value gradient">{prom_global:.2f}</div>
            <div class="kpi-sub">{escala_label(prom_global)}</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Colaboradores</div>
            <div class="kpi-value">{total_colab}</div>
            <div class="kpi-sub">{"seleccionado" if total_colab == 1 else "evaluados"}</div>
        </div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Competencias</div>
            <div class="kpi-value">{n_comp}</div>
            <div class="kpi-sub">evaluadas</div>
        </div>""", unsafe_allow_html=True)
    with c4:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Alto desempeño o superior</div>
            <div class="kpi-value green">{n_alto}</div>
            <div class="kpi-sub">colaboradores >= 90</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # Subnavegacion de Fase I. Usamos botones para evitar inconsistencias de
    # st.tabs en Streamlit Cloud cuando cambian filtros y se preserva el scroll.
    FASE1_TABS = [
        ("resumen", "Resumen"),
        ("competencias", "Competencias"),
        ("relacion", "Por relaci\u00f3n"),
        ("colaboradores", "Colaboradores"),
        ("items", "\u00cdtems"),
    ]
    with st.container(key="sticky_fase1_subnav"):
        fase1_tab = render_nav_botones(FASE1_TABS, "fase1_tab", "fase1_tab")

    # â”€â”€ Subtab: Resumen â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    if fase1_tab == "resumen":
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("**Distribución por escala de desempeño**")
            st.plotly_chart(fig_escala(df_global_f), use_container_width=True, key="res_escala")
        with col_b:
            st.markdown("**Promedio por tipo de relaci\u00f3n**")
            st.plotly_chart(fig_relaciones(rel_prom_f), use_container_width=True, key="res_relaciones")

        col_c, col_d = st.columns(2)
        comp_top, comp_fortalecer = motor_360.seleccionar_competencias_resumen(
            df_comp_prom_f
        )
        with col_c:
            st.markdown("**Top competencias**")
            for _, row in comp_top.iterrows():
                v = row["prom_comp"]
                pct = int((v - 65) / 35 * 100)
                color = score_color(v)
                st.markdown(f"""
                <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px">
                    <span style="font-size:12px;color:#6b6b8a;flex:1;min-width:0;overflow:hidden;
                        text-overflow:ellipsis;white-space:nowrap" title="{row['competencia']}">{row['competencia']}</span>
                    <div style="width:100px;height:6px;background:#e8e4f4;border-radius:3px;overflow:hidden">
                        <div style="width:{pct}%;height:100%;background:{color};border-radius:3px"></div>
                    </div>
                    <span style="font-size:13px;font-weight:600;color:{color};min-width:38px">{v:.2f}</span>
                </div>""", unsafe_allow_html=True)
        with col_d:
            st.markdown("**Competencias a fortalecer**")
            for _, row in comp_fortalecer.iterrows():
                v = row["prom_comp"]
                pct = int((v - 65) / 35 * 100)
                color = score_color(v)
                st.markdown(f"""
                <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px">
                    <span style="font-size:12px;color:#6b6b8a;flex:1;min-width:0;overflow:hidden;
                        text-overflow:ellipsis;white-space:nowrap" title="{row['competencia']}">{row['competencia']}</span>
                    <div style="width:100px;height:6px;background:#e8e4f4;border-radius:3px;overflow:hidden">
                        <div style="width:{pct}%;height:100%;background:{color};border-radius:3px"></div>
                    </div>
                    <span style="font-size:13px;font-weight:600;color:{color};min-width:38px">{v:.2f}</span>
                </div>""", unsafe_allow_html=True)

    # â”€â”€ Subtab: Competencias â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    if fase1_tab == "competencias":
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("**Puntaje por competencia**")
            st.plotly_chart(fig_comp_barras(df_comp_prom_f), use_container_width=True, key="comp_barras")
        with col_b:
            st.markdown("**Radar de competencias**")
            st.plotly_chart(fig_radar(df_comp_prom_f), use_container_width=True, key="comp_radar")

        st.markdown("**Detalle por colaborador x competencia**")
        df_pivot = df_comp_f.pivot_table(index="colaborador", columns="competencia", values="puntaje").reset_index()
        df_pivot["__g"] = df_pivot.iloc[:, 1:].mean(axis=1, numeric_only=True)
        df_pivot = df_pivot.sort_values("__g", ascending=False).drop(columns="__g")
        comp_cols = [c for c in df_pivot.columns if c != "colaborador"]
        html  = '<div style="overflow-x:auto"><table class="ev-table"><thead><tr>'
        html += '<th>Colaborador</th><th>Global</th>' + "".join(f"<th>{c}</th>" for c in comp_cols) + "</tr></thead><tbody>"
        for _, row in df_pivot.iterrows():
            html += f'<tr><td style="font-weight:500">{row["colaborador"]}</td><td>{chip_html(row[comp_cols].mean())}</td>'
            for c in comp_cols:
                v = row[c]
                html += f"<td>{chip_html(v)}</td>" if pd.notna(v) else "<td style='color:#aaa;text-align:center'>&mdash;</td>"
            html += "</tr>"
        html += "</tbody></table></div>"
        st.markdown(html, unsafe_allow_html=True)

    # â”€â”€ Subtab: Por relaciÃ³n â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    if fase1_tab == "relacion":
        col_a, col_b = st.columns(2)
        competencias_f = df_comp_prom_f["competencia"].tolist()
        with col_a:
            st.markdown("**Promedio global por tipo de relaci\u00f3n**")
            st.plotly_chart(fig_relaciones(rel_prom_f), use_container_width=True, key="rel_relaciones")
        with col_b:
            st.markdown("**Competencias x relaci\u00f3n**")
            st.plotly_chart(
                fig_rel_comp(comp_rel_f, competencias_f, tipo_labels_pesos_f),
                use_container_width=True,
                key="rel_comp",
            )

        st.markdown("**Tabla: promedio por competencia y relaci\u00f3n**")
        tipos_con_datos = [t for t in TIPO_LABEL if t in comp_rel_f]
        html  = '<div style="overflow-x:auto"><table class="ev-table"><thead><tr><th>Competencia</th>'
        html += "".join(f"<th>{tipo_labels_pesos_f.get(t, TIPO_LABEL[t])}</th>" for t in tipos_con_datos) + "</tr></thead><tbody>"
        for comp in competencias_f:
            html += f'<tr><td style="font-weight:500">{comp}</td>'
            for t in tipos_con_datos:
                v = comp_rel_f.get(t, {}).get(comp)
                html += f"<td>{chip_html(v)}</td>" if v is not None else "<td style='color:#aaa;text-align:center'>&mdash;</td>"
            html += "</tr>"
        html += "</tbody></table></div>"
        st.markdown(html, unsafe_allow_html=True)

    # â”€â”€ Subtab: Colaboradores â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    if fase1_tab == "colaboradores":
        opciones_colab = df_global_f.sort_values("global", ascending=False)["colaborador"].tolist()
        if opciones_colab:
            control_colab, control_top = st.columns([3, 1])
            with control_colab:
                colaborador_sel = st.selectbox(
                    "Detalle individual",
                    options=opciones_colab,
                    key="colaborador_detalle_fase1",
                )
            with control_top:
                top_n = st.selectbox(
                    "Ranking visible",
                    options=[15, 25, 50],
                    index=1,
                    format_func=lambda n: f"Top {n}",
                    key="ranking_visible_fase1",
                )

            df_colab = df_comp_f[df_comp_f["colaborador"] == colaborador_sel]
            g = df_global_f[df_global_f["colaborador"] == colaborador_sel]["global"].values[0]

            df_rank_base = df_global_f.sort_values("global", ascending=False).copy()
            df_rank = df_rank_base.head(top_n).copy()
            seleccionado_fuera_top = colaborador_sel not in df_rank["colaborador"].tolist()
            if seleccionado_fuera_top:
                df_rank = pd.concat([
                    df_rank,
                    df_rank_base[df_rank_base["colaborador"] == colaborador_sel],
                ], ignore_index=True)

            rank_col, detail_col = st.columns([1.05, 0.95])
            with rank_col:
                st.markdown("**Ranking de colaboradores**")
                nota_extra = " Incluye el colaborador seleccionado fuera del Top." if seleccionado_fuera_top else ""
                st.markdown(
                    f'<div class="ev-mini-note">Mostrando {len(df_rank)} de {len(df_rank_base)} colaboradores.{nota_extra}</div>',
                    unsafe_allow_html=True,
                )
                st.plotly_chart(
                    fig_colab_ranking(df_rank, height=420, colaborador_sel=colaborador_sel),
                    use_container_width=True,
                    key="colab_ranking",
                )

                with st.expander("Ver ranking completo en tabla", expanded=False):
                    html = '<div class="ev-scroll-table"><table class="ev-table">'
                    html += "<thead><tr><th>#</th><th>Colaborador</th><th>Puntaje</th><th>Escala</th></tr></thead><tbody>"
                    for pos, (_, row) in enumerate(df_rank_base.iterrows(), start=1):
                        es_sel = row["colaborador"] == colaborador_sel
                        estilo = ' style="background:#f5f0ff;font-weight:600"' if es_sel else ""
                        nombre = html_lib.escape(str(row["colaborador"]))
                        html += f"<tr{estilo}><td>{pos}</td><td>{nombre}</td><td>{chip_html(row['global'])}</td><td>{escala_label(row['global'])}</td></tr>"
                    html += "</tbody></table></div>"
                    st.markdown(html, unsafe_allow_html=True)

            with detail_col:
                st.markdown("**Detalle individual**")
                st.markdown(f"""
                <div style="background:white;border:0.5px solid #e8e4f4;border-radius:10px;padding:16px">
                    <div style="font-size:16px;font-weight:600;color:#1a1a3e;margin-bottom:4px">{colaborador_sel}</div>
                    <div style="font-size:24px;font-weight:700;color:{score_color(g)};margin-bottom:4px">{g:.2f}</div>
                    <div style="font-size:12px;color:#6b6b8a;margin-bottom:16px">{escala_label(g)}</div>
                """, unsafe_allow_html=True)
                for _, row in df_colab.sort_values("puntaje", ascending=False).iterrows():
                    v = row["puntaje"]
                    pct = int((v - 65) / 35 * 100)
                    st.markdown(f"""
                    <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px">
                        <span style="font-size:11px;color:#6b6b8a;flex:1;white-space:nowrap;overflow:hidden;
                            text-overflow:ellipsis" title="{row['competencia']}">{row['competencia']}</span>
                        <div style="width:80px;height:5px;background:#e8e4f4;border-radius:3px;overflow:hidden">
                            <div style="width:{pct}%;height:100%;background:{score_color(v)};border-radius:3px"></div>
                        </div>
                        <span style="font-size:12px;font-weight:600;color:{score_color(v)};min-width:36px">{v:.2f}</span>
                    </div>""", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
                st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
                st.markdown("**Radar individual**")
                st.plotly_chart(fig_colab_radar(df_comp_f, colaborador_sel), use_container_width=True, key="colab_radar")

            st.markdown("**Desglose por relaci\u00f3n**")
            tipos_disp = [t for t in TIPO_LABEL if f"tipo_{t}" in df_colab.columns]
            if tipos_disp:
                tipo_labels_colab = etiquetas_tipo_con_pesos(df_colab, tipos_disp)
                html  = '<div style="overflow-x:auto"><table class="ev-table"><thead><tr><th>Competencia</th>'
                html += "".join(f"<th>{tipo_labels_colab.get(t, TIPO_LABEL[t])}</th>" for t in tipos_disp) + "</tr></thead><tbody>"
                for _, row in df_colab.sort_values("puntaje", ascending=False).iterrows():
                    html += f'<tr><td style="font-weight:500">{row["competencia"]}</td>'
                    for t in tipos_disp:
                        v = row.get(f"tipo_{t}")
                        html += f"<td>{chip_html(v)}</td>" if pd.notna(v) else "<td style='color:#aaa;text-align:center'>&mdash;</td>"
                    html += "</tr>"
                html += "</tbody></table></div>"
                st.markdown(html, unsafe_allow_html=True)
        else:
            st.info("No hay colaboradores con los filtros aplicados.")

    # â”€â”€ Subtab: Ãtems â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    if fase1_tab == "items":
        st.markdown("**Puntaje por \u00edtem (promedio ponderado)**")
        comp_options = ["Todas las competencias"] + sorted(df_items_f["competencia"].unique().tolist())
        filtro_comp  = st.selectbox("Competencia", comp_options, label_visibility="collapsed")
        df_items_show = df_items_f.copy()
        if filtro_comp != "Todas las competencias":
            df_items_show = df_items_show[df_items_show["competencia"] == filtro_comp]
        html  = '<div style="overflow-x:auto"><table class="ev-table ev-items-table">'
        html += "<thead><tr><th>Item</th><th>Puntaje</th></tr></thead><tbody>"
        for competencia, df_grupo in df_items_show.groupby("competencia", sort=True):
            promedio = df_grupo["puntaje"].mean()
            cantidad = len(df_grupo)
            nombre = html_lib.escape(str(competencia))
            etiqueta_items = "\u00edtem" if cantidad == 1 else "\u00edtems"
            html += (
                '<tr class="ev-items-group"><td colspan="2">'
                '<div class="ev-items-group-content">'
                f'<span class="ev-items-group-name">{nombre}</span>'
                f'<span class="ev-items-group-meta">{cantidad} {etiqueta_items} &middot; Promedio {promedio:.2f}</span>'
                "</div></td></tr>"
            )
            for _, row in df_grupo.sort_values("puntaje", ascending=False).iterrows():
                item = html_lib.escape(str(row["item"]))
                html += f'<tr><td>{item}</td><td>{chip_html(row["puntaje"])}</td></tr>'
        html += "</tbody></table></div>"
        st.markdown(html, unsafe_allow_html=True)


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# FASE II - POTENCIAL
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
def _proximamente(fase: str):
    st.markdown(f"""
    <div style="text-align:center;padding:60px 20px">
        <div style="font-size:12px;letter-spacing:0.18em;text-transform:uppercase;color:#7b6fb0;margin-bottom:12px">Pr\u00f3ximamente</div>
        <div style="font-size:18px;font-weight:600;color:#1a1a3e;margin-bottom:6px">{fase}</div>
        <div style="font-size:13px;color:#6b6b8a">
            Esta secci\u00f3n se habilitar\u00e1 cuando se cargue el archivo correspondiente.
        </div>
    </div>
    """, unsafe_allow_html=True)

if fase_activa == "fase2":
    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
    resumen_potencial = res_potencial["resumen"]
    df_potencial = res_potencial["df_personas"].copy()
    df_potencial["nivel_potencial"] = df_potencial["evaluacion_potencial"].map(escala_potencial_label)

    with st.container(key="sticky_filtros_potencial"):
        st.markdown("""
        <div class="ev-filter-container">
            <div class="ev-filter-header">
                <span class="ev-filter-icon"></span>
                <span class="ev-filter-title">Filtros de potencial</span>
                <span class="ev-filter-hint">Aplican a toda la Fase II</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        filtro_pot_col, filtro_pot_nivel = st.columns([3, 2])
        with filtro_pot_col:
            nombres_potencial = st.multiselect(
                "Colaboradores",
                options=sorted(df_potencial["colaborador"].dropna().unique().tolist()),
                placeholder="Todos los colaboradores",
                key="filtro_potencial_colaboradores",
            )
        with filtro_pot_nivel:
            niveles_potencial = st.multiselect(
                "Nivel de Competencias",
                options=POTENCIAL_ESCALAS,
                placeholder="Todos los niveles",
                key="filtro_potencial_niveles",
            )
    st.markdown('<div class="sticky-controls-spacer"></div>', unsafe_allow_html=True)

    if nombres_potencial:
        df_potencial = df_potencial[df_potencial["colaborador"].isin(nombres_potencial)]
    if niveles_potencial:
        df_potencial = df_potencial[df_potencial["nivel_potencial"].isin(niveles_potencial)]

    df_potencial_evaluado = df_potencial[df_potencial["evaluacion_potencial"].notna()].copy()
    df_valores_potencial = res_potencial["df_competencias"].copy()
    colabs_potencial_activos = df_potencial["colaborador"].dropna().unique().tolist()
    if nombres_potencial or niveles_potencial:
        df_valores_potencial = df_valores_potencial[
            df_valores_potencial["colaborador"].isin(colabs_potencial_activos)
        ]

    sub_f2_res, sub_f2_pot, sub_f2_disc, sub_f2_iq, sub_f2_curvas, sub_f2_colaboradores = st.tabs([
        "Resumen", "Valores", "DISC / Arquetipos", "IQ Inteligencia", "Curvas de Desarrollo", "Colaboradores",
    ])
    with sub_f2_res:
        total_potencial = len(df_potencial_evaluado)
        promedio_potencial = df_potencial_evaluado["evaluacion_potencial"].mean()
        kpi_pot_1, kpi_pot_2 = st.columns(2)
        with kpi_pot_1:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-label">Colaboradores</div>
                <div class="kpi-value">{total_potencial}</div>
                <div class="kpi-sub">con evaluaci\u00f3n de potencial</div>
            </div>""", unsafe_allow_html=True)
        with kpi_pot_2:
            promedio_texto = f"{promedio_potencial:.2f}" if pd.notna(promedio_potencial) else "&mdash;"
            promedio_nivel = escala_potencial_label(promedio_potencial) if pd.notna(promedio_potencial) else "&mdash;"
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-label">Evaluaci\u00f3n de potencial</div>
                <div class="kpi-value green">{promedio_texto}</div>
                <div class="kpi-sub">{promedio_nivel}</div>
            </div>""", unsafe_allow_html=True)

        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
        if df_potencial_evaluado.empty:
            st.info("No hay colaboradores con evaluaci\u00f3n de potencial para los filtros seleccionados.")
        else:
            medidor_1, medidor_2 = st.columns(2)
            with medidor_1:
                st.markdown("**Resultado global de potencial**")
                st.plotly_chart(
                    fig_medidor_potencial(promedio_potencial, POTENCIAL_LIMITES),
                    use_container_width=True,
                    key="potencial_medidor_global",
                )
            with medidor_2:
                st.markdown("**Distribuci\u00f3n por nivel de competencias**")
                st.plotly_chart(
                    fig_escala_potencial(df_potencial_evaluado, "nivel_potencial"),
                    use_container_width=True,
                    key="potencial_escala_nivel",
                )

            graf_1, graf_2 = st.columns(2)
            with graf_1:
                st.markdown("**Colaboradores por empresa**")
                st.plotly_chart(
                    fig_distribucion_potencial(df_potencial, "empresa"),
                    use_container_width=True,
                    key="potencial_empresa",
                )
            with graf_2:
                st.markdown("**Colaboradores por pais**")
                st.plotly_chart(
                    fig_distribucion_potencial(df_potencial, "pais"),
                    use_container_width=True,
                    key="potencial_pais",
                )
    with sub_f2_pot:
        limites_valores = (70, 85)

        tabla_valores = motor_potencial.resumir_competencias_evaluadas(
            df_valores_potencial,
            ORDEN_VALORES_POTENCIAL,
        )

        tabla_col, grafico_col = st.columns([1, 3])
        with tabla_col:
            st.markdown("**Valores**")
            html = '<div style="overflow-x:auto"><table class="ev-table"><thead><tr>'
            html += '<th>Competencia</th><th style="text-align:right">Promedio</th></tr></thead><tbody>'
            for _, fila in tabla_valores.iterrows():
                competencia = html_lib.escape(reparar_texto(fila["competencia"]))
                fondo, texto = color_valor_potencial(fila["puntaje"], limites_valores)
                valor = f"{fila['puntaje']:.2f}%" if pd.notna(fila["puntaje"]) else "&mdash;"
                html += (
                    f'<tr><td>{competencia}</td>'
                    f'<td style="text-align:right;background:{fondo};color:{texto};font-weight:600">'
                    f'{valor}</td></tr>'
                )
            html += "</tbody></table></div>"
            st.markdown(html, unsafe_allow_html=True)

        with grafico_col:
            st.markdown("**Promedio por valor**")
            if tabla_valores["puntaje"].notna().any():
                st.plotly_chart(
                    fig_valores_potencial(tabla_valores, limites_valores),
                    use_container_width=True,
                    key="valores_potencial_grafico",
                )
            else:
                st.info("No hay valores disponibles para los filtros seleccionados.")
    with sub_f2_disc:
        tabla_disc = contar_arquetipos_disc(df_potencial)
        total_disc = int(tabla_disc["colaboradores"].sum()) if not tabla_disc.empty else 0
        total_base_disc = len(df_potencial)
        cobertura_disc = total_disc / total_base_disc if total_base_disc else np.nan
        arquetipo_lider = tabla_disc.iloc[0] if not tabla_disc.empty else None

        disc_kpi_1, disc_kpi_2, disc_kpi_3 = st.columns(3)
        with disc_kpi_1:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-label">Colaboradores con DISC</div>
                <div class="kpi-value">{total_disc}</div>
                <div class="kpi-sub">de {total_base_disc} colaboradores filtrados</div>
            </div>""", unsafe_allow_html=True)
        with disc_kpi_2:
            cobertura_txt = f"{cobertura_disc:.1%}" if pd.notna(cobertura_disc) else "&mdash;"
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-label">Cobertura DISC</div>
                <div class="kpi-value green">{cobertura_txt}</div>
                <div class="kpi-sub">personas con arquetipo asignado</div>
            </div>""", unsafe_allow_html=True)
        with disc_kpi_3:
            lider_nombre = html_lib.escape(str(arquetipo_lider["arquetipo"])) if arquetipo_lider is not None else "&mdash;"
            lider_valor = int(arquetipo_lider["colaboradores"]) if arquetipo_lider is not None else 0
            lider_part = f"{arquetipo_lider['participacion']:.1%}" if arquetipo_lider is not None else "&mdash;"
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-label">Arquetipo dominante</div>
                <div class="kpi-value" style="font-size:22px">{lider_nombre}</div>
                <div class="kpi-sub">{lider_valor} colaboradores &middot; {lider_part}</div>
            </div>""", unsafe_allow_html=True)

        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
        if tabla_disc.empty:
            st.info("No hay arquetipos DISC disponibles para los filtros seleccionados.")
        else:
            tabla_col, radar_col = st.columns([0.9, 1.5])
            with tabla_col:
                st.markdown("**Arquetipos**")
                html = '<div class="ev-scroll-table"><table class="ev-table">'
                html += "<thead><tr><th>Arquetipo</th><th style='text-align:right'>Colaboradores</th><th style='text-align:right'>%</th></tr></thead><tbody>"
                max_disc = tabla_disc["colaboradores"].max()
                for idx, fila in tabla_disc.iterrows():
                    color = DISC_PALETA[idx % len(DISC_PALETA)]
                    arquetipo = html_lib.escape(str(fila["arquetipo"]))
                    colaboradores = int(fila["colaboradores"])
                    participacion = f"{fila['participacion']:.1%}"
                    ancho = int(colaboradores / max_disc * 100) if max_disc else 0
                    html += (
                        "<tr>"
                        f"<td><div style='font-weight:600;color:#1a1a3e'>{arquetipo}</div>"
                        "<div style='height:5px;background:#f0eef8;border-radius:5px;overflow:hidden;margin-top:5px'>"
                        f"<div style='width:{ancho}%;height:100%;background:{color};border-radius:5px'></div>"
                        "</div></td>"
                        f"<td style='text-align:right;font-weight:700;color:{color}'>{colaboradores}</td>"
                        f"<td style='text-align:right;color:#6b6b8a'>{participacion}</td>"
                        "</tr>"
                    )
                html += (
                    "<tr style='font-weight:700;background:#f8f7fc'>"
                    f"<td>Total general</td><td style='text-align:right'>{total_disc}</td><td style='text-align:right'>100.0%</td>"
                    "</tr></tbody></table></div>"
                )
                st.markdown(html, unsafe_allow_html=True)

            with radar_col:
                st.markdown("**Mapa radial de arquetipos**")
                st.plotly_chart(
                    fig_disc_arquetipos(tabla_disc),
                    use_container_width=True,
                    key="disc_arquetipos_radial",
                )

            st.markdown("**Arquetipos con mayor presencia**")
            st.plotly_chart(
                fig_disc_top_barras(tabla_disc, top_n=min(8, len(tabla_disc))),
                use_container_width=True,
                key="disc_arquetipos_top",
            )

    with sub_f2_iq:
        tabla_iq = contar_iq(df_potencial)
        total_iq = int(tabla_iq["colaboradores"].sum()) if not tabla_iq.empty else 0
        total_base_iq = len(df_potencial)
        cobertura_iq = total_iq / total_base_iq if total_base_iq else np.nan
        promedio_iq = (
            np.average(tabla_iq["puntaje"], weights=tabla_iq["colaboradores"])
            if not tabla_iq.empty and tabla_iq["puntaje"].notna().any()
            else np.nan
        )
        rango_lider_iq = (
            tabla_iq.sort_values(["colaboradores", "puntaje"], ascending=[False, True]).iloc[0]
            if not tabla_iq.empty else None
        )

        iq_kpi_1, iq_kpi_2, iq_kpi_3 = st.columns(3)
        with iq_kpi_1:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-label">Colaboradores con IQ</div>
                <div class="kpi-value">{total_iq}</div>
                <div class="kpi-sub">de {total_base_iq} colaboradores filtrados</div>
            </div>""", unsafe_allow_html=True)
        with iq_kpi_2:
            promedio_txt = f"{promedio_iq:.1f}" if pd.notna(promedio_iq) else "&mdash;"
            cobertura_txt = f"{cobertura_iq:.1%}" if pd.notna(cobertura_iq) else "&mdash;"
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-label">Promedio IQ</div>
                <div class="kpi-value green">{promedio_txt}</div>
                <div class="kpi-sub">cobertura {cobertura_txt}</div>
            </div>""", unsafe_allow_html=True)
        with iq_kpi_3:
            rango_nombre = html_lib.escape(str(rango_lider_iq["iq"])) if rango_lider_iq is not None else "&mdash;"
            rango_valor = int(rango_lider_iq["colaboradores"]) if rango_lider_iq is not None else 0
            rango_part = f"{rango_lider_iq['participacion']:.1%}" if rango_lider_iq is not None else "&mdash;"
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-label">Rango mas frecuente</div>
                <div class="kpi-value" style="font-size:22px">{rango_nombre}</div>
                <div class="kpi-sub">{rango_valor} colaboradores &middot; {rango_part}</div>
            </div>""", unsafe_allow_html=True)

        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
        if tabla_iq.empty:
            st.info("No hay datos de IQ para los filtros seleccionados.")
        else:
            graf_iq, tabla_iq_col = st.columns([1.5, 0.9])
            with graf_iq:
                st.markdown("**Distribucion por factor Inteligencia**")
                st.plotly_chart(
                    fig_iq_distribucion(tabla_iq),
                    use_container_width=True,
                    key="iq_inteligencia_distribucion",
                )
            with tabla_iq_col:
                st.markdown("**Detalle IQ**")
                html = '<div class="ev-scroll-table"><table class="ev-table">'
                html += "<thead><tr><th>Factor Inteligencia</th><th style='text-align:right'>Puntaje</th><th style='text-align:right'>Colab.</th><th style='text-align:right'>%</th></tr></thead><tbody>"
                for _, fila in tabla_iq.iterrows():
                    etiqueta = html_lib.escape(str(fila["iq"]))
                    puntaje = f"{fila['puntaje']:.0f}" if pd.notna(fila["puntaje"]) else "&mdash;"
                    html += (
                        "<tr>"
                        f"<td style='font-weight:600'>{etiqueta}</td>"
                        f"<td style='text-align:right'>{puntaje}</td>"
                        f"<td style='text-align:right;font-weight:700;color:#185fa5'>{int(fila['colaboradores'])}</td>"
                        f"<td style='text-align:right;color:#6b6b8a'>{fila['participacion']:.1%}</td>"
                        "</tr>"
                    )
                html += (
                    "<tr style='font-weight:700;background:#f8f7fc'>"
                    f"<td>Total general</td><td></td><td style='text-align:right'>{total_iq}</td><td style='text-align:right'>100.0%</td>"
                    "</tr></tbody></table></div>"
                )
                st.markdown(html, unsafe_allow_html=True)
    with sub_f2_curvas:
        competencias_curva = [
            comp for comp in ORDEN_VALORES_POTENCIAL
            if comp in set(df_valores_potencial["competencia"].dropna().unique())
        ]
        if not competencias_curva:
            st.info("No hay competencias disponibles para construir curvas de desarrollo con los filtros seleccionados.")
        else:
            selector_curva, resumen_curva = st.columns([2.2, 1])
            with selector_curva:
                competencia_curva = st.selectbox(
                    "Competencia",
                    options=competencias_curva,
                    key="curva_desarrollo_competencia",
                )

            tabla_curva = preparar_curva_desarrollo(df_valores_potencial, competencia_curva)
            total_curva = int(tabla_curva["colaboradores"].sum()) if not tabla_curva.empty else 0
            puntaje_promedio_curva = (
                np.average(tabla_curva["puntaje"], weights=tabla_curva["colaboradores"])
                if total_curva else np.nan
            )
            moda_curva = (
                tabla_curva.sort_values(["colaboradores", "puntaje"], ascending=[False, True]).iloc[0]
                if total_curva else None
            )
            with resumen_curva:
                promedio_txt = f"{puntaje_promedio_curva:.1f}" if pd.notna(puntaje_promedio_curva) else "&mdash;"
                moda_txt = (
                    f"{int(moda_curva['puntaje'])} &middot; {html_lib.escape(str(moda_curva['descripcion']))}"
                    if moda_curva is not None else "&mdash;"
                )
                st.markdown(f"""
                <div class="kpi-card">
                    <div class="kpi-label">Distribucion seleccionada</div>
                    <div class="kpi-value">{promedio_txt}</div>
                    <div class="kpi-sub">{total_curva} registros &middot; moda {moda_txt}</div>
                </div>""", unsafe_allow_html=True)

            if tabla_curva.empty:
                st.info("La competencia seleccionada no tiene puntajes disponibles para los filtros actuales.")
            else:
                graf_curva, tabla_curva_col = st.columns([1.55, 0.85])
                with graf_curva:
                    st.markdown("**Curva de desarrollo**")
                    st.plotly_chart(
                        fig_curva_desarrollo(tabla_curva, competencia_curva),
                        use_container_width=True,
                        key="curva_desarrollo_grafico",
                    )
                with tabla_curva_col:
                    st.markdown("**Escala y frecuencia**")
                    html = '<div class="ev-scroll-table"><table class="ev-table">'
                    html += "<thead><tr><th>Descripcion</th><th style='text-align:right'>Escala</th><th style='text-align:right'>Colab.</th><th style='text-align:right'>%</th></tr></thead><tbody>"
                    for _, fila in tabla_curva.sort_values("puntaje", ascending=False).iterrows():
                        descripcion = html_lib.escape(str(fila["descripcion"]))
                        html += (
                            "<tr>"
                            f"<td style='font-weight:600'>{descripcion}</td>"
                            f"<td style='text-align:right'>{int(fila['puntaje'])}</td>"
                            f"<td style='text-align:right;font-weight:700;color:#185fa5'>{int(fila['colaboradores'])}</td>"
                            f"<td style='text-align:right;color:#6b6b8a'>{fila['participacion']:.1%}</td>"
                            "</tr>"
                        )
                    html += (
                        "<tr style='font-weight:700;background:#f8f7fc'>"
                        f"<td>Total general</td><td></td><td style='text-align:right'>{total_curva}</td><td style='text-align:right'>100.0%</td>"
                        "</tr></tbody></table></div>"
                    )
                    st.markdown(html, unsafe_allow_html=True)

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    with sub_f2_colaboradores:
        st.markdown("**Personas evaluadas y nivel de competencias**")
        if df_potencial_evaluado.empty:
            st.info("No hay personas evaluadas para los filtros seleccionados.")
        else:
            tabla_evaluados = df_potencial_evaluado.copy()
            orden_niveles = {
                nivel: indice
                for indice, nivel in enumerate(reversed(POTENCIAL_ESCALAS))
            }
            tabla_evaluados["orden_nivel"] = tabla_evaluados["nivel_potencial"].map(orden_niveles)
            tabla_evaluados = tabla_evaluados.sort_values(
                ["orden_nivel", "evaluacion_potencial", "colaborador"],
                ascending=[True, False, True],
                na_position="last",
            )

            html = '<div class="ev-scroll-table"><table class="ev-table">'
            html += (
                "<thead><tr><th>Colaborador</th><th>Identificación</th><th>Empresa</th><th>Cargo</th>"
                "<th style='text-align:right'>Puntaje</th>"
                "<th>Nivel de Competencias</th></tr></thead><tbody>"
            )
            fondos_nivel = {
                "Alto potencial": "#e5f4ea",
                "Potencial medio": "#fff6d6",
                "Potencial bajo": "#fbe9e8",
            }
            for _, fila in tabla_evaluados.iterrows():
                colaborador_valor = fila.get("colaborador")
                colaborador = (
                    html_lib.escape(str(colaborador_valor))
                    if pd.notna(colaborador_valor) and str(colaborador_valor).strip()
                    else "Sin dato"
                )
                identificacion_valor = fila.get("identificacion")
                identificacion = (
                    html_lib.escape(str(identificacion_valor))
                    if pd.notna(identificacion_valor) and str(identificacion_valor).strip()
                    else "&mdash;"
                )
                empresa_valor = fila.get("empresa")
                empresa = (
                    html_lib.escape(str(empresa_valor))
                    if pd.notna(empresa_valor) and str(empresa_valor).strip()
                    else "&mdash;"
                )
                cargo_valor = fila.get("cargo")
                cargo = (
                    html_lib.escape(str(cargo_valor))
                    if pd.notna(cargo_valor) and str(cargo_valor).strip()
                    else "&mdash;"
                )
                puntaje = f"{float(fila['evaluacion_potencial']):.2f}"
                nivel = str(fila["nivel_potencial"])
                nivel_seguro = html_lib.escape(nivel)
                color_nivel = POTENCIAL_COLORES.get(nivel, "#6b6b8a")
                fondo_nivel = fondos_nivel.get(nivel, "#f2f2f7")
                html += (
                    "<tr>"
                    f"<td style='font-weight:600'>{colaborador}</td>"
                    f"<td>{identificacion}</td><td>{empresa}</td><td>{cargo}</td>"
                    f"<td style='text-align:right;font-weight:700'>{puntaje}</td>"
                    "<td>"
                    f"<span style='display:inline-block;padding:4px 9px;border-radius:999px;"
                    f"background:{fondo_nivel};color:{color_nivel};font-weight:700;white-space:nowrap'>"
                    f"{nivel_seguro}</span></td></tr>"
                )
            html += "</tbody></table></div>"
            st.markdown(html, unsafe_allow_html=True)

# FASE III - EVALUACION DE OBJETIVOS
if fase_activa == "fase3":
    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
    df_obj_colab_base = res_objetivos["df_colaboradores"].copy()
    df_obj_fuente_base = res_objetivos["df_fuente"].copy()

    if df_obj_colab_base.empty:
        _proximamente("Fase III - Evaluacion de Objetivos")
    else:
        filtro_obj_1, filtro_obj_2 = st.columns(2)
        with filtro_obj_1:
            filtro_obj_colabs = st.multiselect(
                "Colaboradores",
                sorted(df_obj_colab_base["colaborador"].dropna().unique().tolist()),
                key="filtro_objetivos_colaboradores",
                placeholder="Todos los colaboradores",
            )
        with filtro_obj_2:
            filtro_obj_escala = st.multiselect(
                "Nivel de desempeño",
                OBJETIVOS_ESCALA_ORDEN,
                key="filtro_objetivos_escala",
                placeholder="Todos los niveles",
            )

        df_obj_colab = df_obj_colab_base.copy()
        if filtro_obj_colabs:
            df_obj_colab = df_obj_colab[df_obj_colab["colaborador"].isin(filtro_obj_colabs)]
        df_obj_colab["nivel_desempeno"] = df_obj_colab["puntaje"].map(escala_objetivos_label)
        if filtro_obj_escala:
            df_obj_colab = df_obj_colab[df_obj_colab["nivel_desempeno"].isin(filtro_obj_escala)]

        colabs_obj_activos = df_obj_colab["colaborador"].dropna().unique().tolist()
        df_obj_fuente = df_obj_fuente_base[df_obj_fuente_base["nombre_colaborador"].isin(colabs_obj_activos)].copy()
        evaluadores_obj = set(df_obj_fuente_base["nombre_evaluador"].dropna().map(normalizar_nombre_match))
        df_obj_colab["gente_a_cargo"] = df_obj_colab["colaborador"].map(
            lambda nombre: "SI" if normalizar_nombre_match(nombre) in evaluadores_obj else "NO"
        )

        df_obj_cargos = (
            df_obj_fuente.groupby("cargo_objetivo", dropna=False)
            .agg(
                puntaje=("puntaje", "mean"),
                colaboradores=("nombre_colaborador", "nunique"),
                objetivos=("objetivo", "nunique"),
            )
            .reset_index()
            .sort_values("puntaje", ascending=False)
        )
        df_obj_items = (
            df_obj_fuente.groupby(["cargo_objetivo", "objetivo"], dropna=False)
            .agg(
                puntaje=("puntaje", "mean"),
                colaboradores=("nombre_colaborador", "nunique"),
            )
            .reset_index()
            .sort_values("puntaje", ascending=False)
        )

        promedio_obj = float(df_obj_colab["puntaje"].mean()) if len(df_obj_colab) else 0.0
        alto_obj = int((df_obj_colab["puntaje"] >= 90).sum()) if len(df_obj_colab) else 0
        total_obj_colab = len(df_obj_colab)
        total_obj_items = int(df_obj_fuente["objetivo"].nunique()) if len(df_obj_fuente) else 0
        df_obj_gente = resumen_dimension_objetivos(df_obj_colab, "gente_a_cargo")

        k1, k2, k3, k4 = st.columns(4)
        with k1:
            st.markdown(f"""
                <div class="kpi-card">
                <div class="kpi-label">Promedio objetivos</div>
                <div class="kpi-value gradient">{promedio_obj:.2f}</div>
                <div class="kpi-sub">{escala_objetivos_label(promedio_obj)}</div>
            </div>""", unsafe_allow_html=True)
        with k2:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-label">Colaboradores</div>
                <div class="kpi-value">{total_obj_colab}</div>
                <div class="kpi-sub">con objetivos evaluados</div>
            </div>""", unsafe_allow_html=True)
        with k3:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-label">Objetivos</div>
                <div class="kpi-value">{total_obj_items}</div>
                <div class="kpi-sub">unicos evaluados</div>
            </div>""", unsafe_allow_html=True)
        with k4:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-label">Alto cumplimiento</div>
                <div class="kpi-value green">{alto_obj}</div>
                <div class="kpi-sub">colaboradores >= 90</div>
            </div>""", unsafe_allow_html=True)

        sub_f3_res, sub_f3_obj, sub_f3_colab = st.tabs([
            "Resumen", "Objetivos", "Colaboradores",
        ])
        with sub_f3_res:
            graf_a, graf_b = st.columns(2)
            with graf_a:
                st.markdown("**Escala de evaluación de objetivos**")
                st.plotly_chart(
                    fig_objetivos_distribucion(df_obj_colab),
                    use_container_width=True,
                    key="obj_distribucion",
                )
            with graf_b:
                st.markdown("**Ranking**")
                st.plotly_chart(
                    fig_objetivos_cargos(df_obj_cargos),
                    use_container_width=True,
                    key="obj_cargos",
                )

            tabla_a, tabla_b = st.columns([0.85, 1.15])
            with tabla_a:
                render_tabla_escala_objetivos(df_obj_colab)
                render_tabla_dimension_objetivos(
                    "Gente a cargo",
                    df_obj_gente,
                    "gente_a_cargo",
                    total_obj_colab,
                    promedio_obj,
                )
            with tabla_b:
                st.markdown("**Cargos / puestos**")
                st.markdown(
                    f'<div class="ev-mini-note">Mostrando {len(df_obj_cargos)} cargos/puestos con los filtros aplicados.</div>',
                    unsafe_allow_html=True,
                )
                html = '<div class="ev-scroll-table"><table class="ev-table">'
                html += "<thead><tr><th>Cargo</th><th style='text-align:right'>Promedio</th><th style='text-align:right'>Colab.</th><th style='text-align:right'>Objetivos</th></tr></thead><tbody>"
                for _, fila in df_obj_cargos.sort_values("puntaje", ascending=False).iterrows():
                    html += (
                        "<tr>"
                        f"<td style='font-weight:600'>{html_lib.escape(str(fila['cargo_objetivo']))}</td>"
                        f"<td style='text-align:right'>{chip_html(fila['puntaje'])}</td>"
                        f"<td style='text-align:right'>{int(fila['colaboradores'])}</td>"
                        f"<td style='text-align:right'>{int(fila['objetivos'])}</td>"
                        "</tr>"
                    )
                html += "</tbody></table></div>"
                st.markdown(html, unsafe_allow_html=True)

        with sub_f3_obj:
            cargos_opciones = ["Todos los cargos"] + sorted(df_obj_items["cargo_objetivo"].dropna().unique().tolist())
            cargo_sel_obj = st.selectbox("Cargo", cargos_opciones, key="objetivos_cargo_selector")
            df_items_show = df_obj_items.copy()
            if cargo_sel_obj != "Todos los cargos":
                df_items_show = df_items_show[df_items_show["cargo_objetivo"] == cargo_sel_obj]

            st.markdown("**Cumplimiento por objetivo**")
            html = '<div class="ev-scroll-table"><table class="ev-table">'
            html += "<thead><tr><th>Cargo</th><th>Objetivo</th><th style='text-align:right'>Colab.</th><th style='text-align:right'>Puntaje</th></tr></thead><tbody>"
            for _, fila in df_items_show.sort_values("puntaje", ascending=False).iterrows():
                html += (
                    "<tr>"
                    f"<td style='font-weight:600'>{html_lib.escape(str(fila['cargo_objetivo']))}</td>"
                    f"<td>{html_lib.escape(str(fila['objetivo']))}</td>"
                    f"<td style='text-align:right'>{int(fila['colaboradores'])}</td>"
                    f"<td style='text-align:right'>{chip_html(fila['puntaje'])}</td>"
                    "</tr>"
                )
            html += "</tbody></table></div>"
            st.markdown(html, unsafe_allow_html=True)

        with sub_f3_colab:
            graf_col, tabla_col = st.columns([1.1, 1.2])
            with graf_col:
                st.markdown("**Ranking de colaboradores**")
                st.plotly_chart(
                    fig_objetivos_colaboradores(df_obj_colab),
                    use_container_width=True,
                    key="obj_colaboradores",
                )
            with tabla_col:
                st.markdown("**Detalle por colaborador**")
                html = '<div class="ev-scroll-table"><table class="ev-table">'
                html += "<thead><tr><th>Colaborador</th><th>Cargo</th><th>Jefe</th><th>Nivel</th><th>Gente a cargo</th><th style='text-align:right'>Objetivos</th><th style='text-align:right'>Puntaje</th></tr></thead><tbody>"
                for _, fila in df_obj_colab.sort_values("puntaje", ascending=False).iterrows():
                    html += (
                        "<tr>"
                        f"<td style='font-weight:600'>{html_lib.escape(str(fila['colaborador']))}</td>"
                        f"<td>{html_lib.escape(str(fila['cargo_objetivo']))}</td>"
                        f"<td>{html_lib.escape(str(fila['jefe']))}</td>"
                        f"<td>{html_lib.escape(str(fila['nivel_desempeno']))}</td>"
                        f"<td>{html_lib.escape(str(fila['gente_a_cargo']))}</td>"
                        f"<td style='text-align:right'>{int(fila['objetivos'])}</td>"
                        f"<td style='text-align:right'>{chip_html(fila['puntaje'])}</td>"
                        "</tr>"
                    )
                html += "</tbody></table></div>"
                st.markdown(html, unsafe_allow_html=True)

# RESULTADO INTEGRADO
if fase_activa == "res_int":
    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
    df_integrado_base = preparar_resultado_integrado(
        res["df_global"],
        res_objetivos["df_colaboradores"],
        res_potencial["df_personas"],
        res_objetivos["df_fuente"],
        res.get("df_metadata"),
    )

    sub_ri_completa, sub_ri_360_obj, sub_ri_360_pot, sub_ri_obj_pot, sub_ri_colab = st.tabs([
        "Desempeño + Objetivos + Competencias",
        "Desempeño + Objetivos",
        "Desempeño + Competencias",
        "Objetivos + Competencias",
        "Colaboradores",
    ])

    with sub_ri_completa:
        render_resultado_integrado_tipo(df_integrado_base, "Completa", len(df_integrado_base))

    with sub_ri_360_obj:
        render_resultado_integrado_tipo(df_integrado_base, "360+obj", len(df_integrado_base))
    with sub_ri_360_pot:
        render_resultado_integrado_tipo(df_integrado_base, "360+pot", len(df_integrado_base))
    with sub_ri_obj_pot:
        render_resultado_integrado_tipo(df_integrado_base, "obj+pot", len(df_integrado_base))
    with sub_ri_colab:
        df_colab_integrado = df_integrado_base[pd.notna(df_integrado_base["integrada"])].copy()
        if df_colab_integrado.empty:
            st.info("No hay colaboradores con resultado integrado calculable.")
        else:
            filtros_colab_1, filtros_colab_2, filtros_colab_3 = st.columns(3)
            with filtros_colab_1:
                filtro_colab_integrado = st.multiselect(
                    "Colaboradores",
                    sorted(df_colab_integrado["colaborador"].dropna().unique().tolist()),
                    key="filtro_integrado_detalle_colabs",
                    placeholder="Todos los colaboradores integrados",
                )
            with filtros_colab_2:
                filtro_tipo_integrado = st.multiselect(
                    "Tipo de integración",
                    [cfg for cfg in CONFIG_INTEGRADO.keys() if cfg in df_colab_integrado["etiqueta_integrada"].unique()],
                    key="filtro_integrado_detalle_tipo",
                    placeholder="Todos los tipos",
                    format_func=lambda valor: CONFIG_INTEGRADO.get(valor, {}).get("tab", valor),
                )
            with filtros_colab_3:
                filtro_nivel_integrado = st.multiselect(
                    "Escala integrada",
                    OBJETIVOS_ESCALA_ORDEN,
                    key="filtro_integrado_detalle_nivel",
                    placeholder="Todas las escalas",
                )

            if filtro_colab_integrado:
                df_colab_integrado = df_colab_integrado[df_colab_integrado["colaborador"].isin(filtro_colab_integrado)]
            if filtro_tipo_integrado:
                df_colab_integrado = df_colab_integrado[df_colab_integrado["etiqueta_integrada"].isin(filtro_tipo_integrado)]
            if filtro_nivel_integrado:
                df_colab_integrado = df_colab_integrado[df_colab_integrado["escala_integrada"].isin(filtro_nivel_integrado)]

            st.markdown("**Detalle general de colaboradores integrados**")
            html = '<div class="ev-scroll-table"><table class="ev-table">'
            html += "<thead><tr><th>Colaborador</th><th>Tipo</th><th>Nivel</th><th>Grupo</th><th>Empresa</th><th>País</th><th style='text-align:right'>Desempeño</th><th style='text-align:right'>Objetivos</th><th style='text-align:right'>Competencias</th><th style='text-align:right'>Integrada</th></tr></thead><tbody>"
            for _, fila in df_colab_integrado.sort_values("integrada", ascending=False).iterrows():
                tipo_label = CONFIG_INTEGRADO.get(fila["etiqueta_integrada"], {}).get("tab", fila["etiqueta_integrada"])
                html += (
                    "<tr>"
                    f"<td style='font-weight:600'>{html_lib.escape(str(fila['colaborador']))}</td>"
                    f"<td>{html_lib.escape(str(tipo_label))}</td>"
                    f"<td>{html_lib.escape(str(fila['escala_integrada']))}</td>"
                    f"<td>{html_lib.escape(str(fila['grupo']))}</td>"
                    f"<td>{html_lib.escape(str(fila['empresa']))}</td>"
                    f"<td>{html_lib.escape(str(fila['pais']))}</td>"
                    f"<td style='text-align:right'>{fila['evd_360']:.0f}</td>" if pd.notna(fila.get("evd_360")) else "<td style='text-align:right'>-</td>"
                )
                html += f"<td style='text-align:right'>{fila['objetivos']:.0f}</td>" if pd.notna(fila.get("objetivos")) else "<td style='text-align:right'>-</td>"
                html += f"<td style='text-align:right'>{fila['potencial']:.0f}</td>" if pd.notna(fila.get("potencial")) else "<td style='text-align:right'>-</td>"
                html += f"<td style='text-align:right'>{chip_html(fila['integrada'])}</td></tr>"
            html += "</tbody></table></div>"
            st.markdown(html, unsafe_allow_html=True)

# NINEBOX
if fase_activa == "ninebox":
    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
    df_ninebox_visible = preparar_ninebox(
        res["df_global"],
        res_potencial["df_personas"],
    )
    df_ninebox_base = filtrar_ninebox_general(
        df_ninebox_clasificado_general,
        df_ninebox_visible,
    )

    if df_ninebox_general.empty:
        st.info("No hay colaboradores con datos emparejados de desempeño 360 y potencial.")
    elif cortes_ninebox_general is None:
        st.info("Se requieren al menos dos colaboradores emparejados para calcular los puntos de corte del ninebox.")
    elif df_ninebox_base.empty:
        st.info("No hay colaboradores con desempeño y potencial para los filtros globales seleccionados.")
    else:
        nombres_ninebox = sorted(df_ninebox_base["colaborador"].dropna().unique().tolist())
        cortes = cortes_ninebox_general
        df_ninebox_clasificado_base = df_ninebox_base
        seleccion_ninebox = st.session_state.get("filtro_ninebox_colaboradores", [])
        df_ninebox_kpi = df_ninebox_clasificado_base.copy()
        if seleccion_ninebox:
            df_ninebox_kpi = df_ninebox_kpi[df_ninebox_kpi["colaborador"].isin(seleccion_ninebox)]

        kpi_conteos = df_ninebox_kpi["cuadrante"].value_counts()
        kpi_total = len(df_ninebox_kpi)
        kpi_alto_alto = int(kpi_conteos.get(1, 0))
        kpi_medio_medio = int(kpi_conteos.get(5, 0))
        kpi_bajo_bajo = int(kpi_conteos.get(9, 0))

        kpi_cols = st.columns(4)
        kpi_datos = [
            ("Personas", kpi_total, "con desempeño 360 y potencial"),
            ("Alto-Alto", kpi_alto_alto, "alto potencial y alto desempeño"),
            ("Medio-Medio", kpi_medio_medio, "zona central del ninebox"),
            ("Bajo-Bajo", kpi_bajo_bajo, "bajo potencial y bajo desempeño"),
        ]
        for col, (titulo, valor, subtitulo) in zip(kpi_cols, kpi_datos):
            with col:
                st.markdown(
                    f"""
                    <div class="kpi-card">
                        <div class="kpi-label">{titulo}</div>
                        <div class="kpi-value">{valor}</div>
                        <div class="kpi-sub">{subtitulo}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        filtro_ninebox = st.multiselect(
            "Colaboradores",
            options=nombres_ninebox,
            placeholder="Todos los colaboradores emparejados",
            key="filtro_ninebox_colaboradores",
        )
        df_ninebox_clasificado = df_ninebox_clasificado_base.copy()
        if filtro_ninebox:
            df_ninebox_clasificado = df_ninebox_clasificado[
                df_ninebox_clasificado["colaborador"].isin(filtro_ninebox)
            ]

        if df_ninebox_clasificado.empty:
            st.info("No hay colaboradores con desempeño y potencial para los filtros seleccionados.")
        else:
            st.markdown("**Puntos de corte**")
            cortes_html = '<div style="overflow-x:auto"><table class="ev-table"><thead><tr>'
            cortes_html += "<th></th><th>Promedio</th><th>Desviación</th><th>Rango sup</th><th>Rango inf</th></tr></thead><tbody>"
            cortes_html += (
                "<tr><td style='font-weight:700'>Potencial</td>"
                f"<td>{cortes['potencial_prom']:.1f}</td><td>{cortes['potencial_std']:.1f}</td>"
                f"<td>{cortes['potencial_sup']:.0f}</td><td>{cortes['potencial_inf']:.0f}</td></tr>"
            )
            cortes_html += (
                "<tr><td style='font-weight:700'>Evd 360</td>"
                f"<td>{cortes['desempeno_prom']:.1f}</td><td>{cortes['desempeno_std']:.1f}</td>"
                f"<td>{cortes['desempeno_sup']:.0f}</td><td>{cortes['desempeno_inf']:.0f}</td></tr>"
            )
            cortes_html += "</tbody></table></div>"
            st.markdown(cortes_html, unsafe_allow_html=True)

            matriz_col, tabla_col = st.columns([1.05, 1.15])
            with matriz_col:
                st.markdown("**Matriz Ninebox**")
                st.plotly_chart(
                    fig_ninebox(df_ninebox_clasificado),
                    use_container_width=True,
                    key="ninebox_matriz",
                )
                st.markdown(
                    f"<div class='ev-mini-note'><b>Muestra:</b> {len(df_ninebox_clasificado)} colaboradores emparejados</div>",
                    unsafe_allow_html=True,
                )

            with tabla_col:
                st.markdown("**Colaboradores por cuadrante**")
                tabla = df_ninebox_clasificado.sort_values(
                    ["cuadrante", "potencial", "desempeno_360"],
                    ascending=[True, False, False],
                )
                html = '<div class="ev-scroll-table" style="max-height:520px"><table class="ev-table">'
                html += (
                    "<thead><tr><th>Nombres</th><th style='text-align:right'># cuadrante</th>"
                    "<th>Colaboradores</th><th style='text-align:right'>POTENCIAL</th>"
                    "<th style='text-align:right'>360</th></tr></thead><tbody>"
                )
                for cuadrante, grupo in tabla.groupby("cuadrante", sort=True):
                    color = NINEBOX_COLORES.get(int(cuadrante), "#f8f7fc")
                    nombre_cuadrante = html_lib.escape(NINEBOX_LABELS.get(int(cuadrante), f"Cuadrante {cuadrante}"))
                    html += (
                        f"<tr style='background:{color};font-weight:700'>"
                        f"<td>{nombre_cuadrante}</td><td style='text-align:right'>{int(cuadrante)}</td>"
                        f"<td style='text-align:right'>{len(grupo)}</td><td></td><td></td></tr>"
                    )
                    for _, fila in grupo.iterrows():
                        nombre = html_lib.escape(str(fila["colaborador"]))
                        html += (
                            "<tr>"
                            f"<td>{nombre}</td>"
                            f"<td style='text-align:right'>{int(fila['cuadrante'])}</td>"
                            "<td style='text-align:right'>1</td>"
                            f"<td style='text-align:right'>{fila['potencial']:.1f}</td>"
                            f"<td style='text-align:right'>{fila['desempeno_360']:.1f}</td>"
                            "</tr>"
                        )
                html += "</tbody></table></div>"
                st.markdown(html, unsafe_allow_html=True)

