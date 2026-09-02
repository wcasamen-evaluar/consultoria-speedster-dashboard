"""
generar_pdf.py ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â sistema de diseÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â±o fiel al HTML de referencia Evaluar.com
"""

import io, json, math, re, unicodedata
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame,
    Paragraph, Spacer, Table, TableStyle,
    Image, PageBreak, HRFlowable, NextPageTemplate, Flowable, KeepTogether,
)
from reportlab.graphics import renderPDF
from reportlab.graphics.shapes import Drawing, Group, Path as RLPath, Rect, String
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.pdfmetrics import stringWidth

W, H = A4

# Paleta fiel al CSS del HTML
INK       = colors.HexColor("#22194e")
INK2      = colors.HexColor("#3a3170")
INK_SOFT  = colors.HexColor("#6b638f")
PAPER     = colors.HexColor("#faf8f3")
PAPER2    = colors.HexColor("#f3efe6")
LINE      = colors.HexColor("#e4dfd3")
LINE_STR  = colors.HexColor("#c9c2b3")
MAGENTA   = colors.HexColor("#ff4298")
AMBER     = colors.HexColor("#ffab48")
GOOD      = colors.HexColor("#2f7d5e")
WARN      = colors.HexColor("#b45a1f")
BAD       = colors.HexColor("#a32a4d")
WHITE     = colors.white

BANDA_COLOR = {
    "Alto Desempe\u00f1o":  {"fg": GOOD, "hex_fg": "#2f7d5e", "hex_bg": "#eaf4ef"},
    "Satisfactorio":   {"fg": WARN, "hex_fg": "#b45a1f", "hex_bg": "#fdf3ea"},
    "Bajo Desempe\u00f1o":  {"fg": WARN, "hex_fg": "#b45a1f", "hex_bg": "#fdf3ea"},
    "Insatisfactorio": {"fg": BAD,  "hex_fg": "#a32a4d", "hex_bg": "#fbeaef"},
}

TIPOS_ORDEN = ["Autoevaluaci\u00f3n", "Jefe", "Subordinado", "Pares", "Cliente Interno"]

PAD_TOP = 1.97*cm
PAD_LAT = 2.26*cm
PAD_BOT = 2.54*cm

TOTAL_PAGES = 4
ASSETS_DIR = Path(__file__).resolve().parent / "assets"
COVER_BG_OPTIMIZED = ASSETS_DIR / "portada_evaluar_bg_optimized.jpg"
COVER_BG = ASSETS_DIR / "portada_evaluar_bg.png"
LOGO_COVER = ASSETS_DIR / "logo_evaluar_cover_from_svg.png"
LOGO_HEADER = ASSETS_DIR / "logo_evaluar_header.png"
SPEEDSTER_LOGO = Path(__file__).resolve().parent.parent / "logos" / "speedster_logo.png"
COMPETENCIAS_POT_JSON = ASSETS_DIR / "competencias_potencial.json"
COMPETENCIAS_INTERPRETACION_JSON = ASSETS_DIR / "competencias_interpretacion.json"
DISC_JSON = ASSETS_DIR / "disc.json"
LOGO_DISC = ASSETS_DIR / "logo_disc.png"
CAP_JSON = ASSETS_DIR / "cap.json"
DESEMPENO_360_JSON = ASSETS_DIR / "desempeno_360_interpretaciones.json"
OBJETIVOS_JSON = ASSETS_DIR / "objetivos_interpretaciones.json"

POTENCIAL_MARCO_LECTURA = (
    "Este informe tiene como propósito brindar una visión integral de las capacidades y atributos evaluados. "
    "La información busca convertirse en una herramienta de autoconocimiento, reflexión y construcción de acciones "
    "concretas de desarrollo, facilitando la identificación de fortalezas, oportunidades de crecimiento y posibles rutas "
    "para potenciar el impacto organizacional. "
    "Los resultados reflejan tendencias obtenidas durante el proceso de evaluación y deben interpretarse como un "
    "insumo para el desarrollo continuo, acompañado de conversaciones de feedback y acciones de crecimiento profesional."
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def spacer(h): return Spacer(1, h*cm)
def hr(color=LINE, t=0.5, sb=6, sa=6):
    return HRFlowable(width="100%", thickness=t, color=color,
                      spaceBefore=sb, spaceAfter=sa)

def banda_desde_pts(p):
    if p >= 90: return "Alto Desempe\u00f1o"
    if p >= 80: return "Satisfactorio"
    if p >= 70: return "Bajo Desempe\u00f1o"
    return "Insatisfactorio"

def bc(banda, campo):
    return BANDA_COLOR.get(banda,
        {"fg":INK_SOFT,"hex_fg":"#6b638f","hex_bg":"#f5f5f5"})[campo]

def sty(name, **kw):
    base = dict(fontName="Helvetica", fontSize=10, textColor=INK2,
                leading=15, spaceAfter=0, spaceBefore=0)
    return ParagraphStyle(name, **{**base, **kw})


class RoundedBox(Flowable):
    def __init__(self, child, width, fill=colors.white, stroke=LINE, radius=8, pad=0, stroke_width=0.6):
        super().__init__()
        self.child = child
        self.width = width
        self.fill = fill
        self.stroke = stroke
        self.radius = radius
        self.pad = pad
        self.stroke_width = stroke_width

    def wrap(self, availWidth, availHeight):
        child_w, child_h = self.child.wrap(self.width - 2*self.pad, availHeight)
        self.height = child_h + 2*self.pad
        return self.width, self.height

    def draw(self):
        self.canv.saveState()
        self.canv.setFillColor(self.fill)
        self.canv.setStrokeColor(self.stroke)
        self.canv.setLineWidth(self.stroke_width)
        self.canv.roundRect(0, 0, self.width, self.height, self.radius, fill=1, stroke=1)
        self.child.drawOn(self.canv, self.pad, self.pad)
        self.canv.restoreState()


def E():
    return {
        "eyebrow":     sty("ey", fontName="Helvetica", fontSize=8,
                           textColor=MAGENTA, leading=12),
        "section_id":  sty("sid", fontName="Helvetica", fontSize=8,
                           textColor=INK_SOFT, leading=12),
        "section_h":   sty("sh", fontName="Helvetica-Bold", fontSize=22,
                           textColor=INK, leading=28),
        "h3":          sty("h3", fontName="Helvetica-Bold", fontSize=14,
                           textColor=INK, leading=20),
        "th":          sty("th", fontName="Helvetica-Bold", fontSize=8,
                           textColor=INK_SOFT, leading=11),
        "td":          sty("td", fontName="Helvetica", fontSize=10,
                           textColor=INK, leading=14),
        "td_comp":     sty("tdc", fontName="Helvetica-Bold", fontSize=10,
                           textColor=INK, leading=14),
        "td_num":      sty("tdn", fontName="Helvetica-Bold", fontSize=10,
                           textColor=INK, leading=14, alignment=TA_RIGHT),
        "nota":        sty("nota", fontName="Helvetica-Oblique", fontSize=8,
                           textColor=INK_SOFT, leading=12),
        "body":        sty("body", fontName="Helvetica", fontSize=10,
                           textColor=INK2, leading=16, alignment=TA_JUSTIFY),
    }

# ---------------------------------------------------------------------------
# GrÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¡ficos matplotlib
# ---------------------------------------------------------------------------

def crear_gauge(puntaje, banda, ancho_cm=6.5, alto_cm=4.8):
    fig, ax = plt.subplots(figsize=(ancho_cm/2.54, alto_cm/2.54),
                           subplot_kw=dict(aspect="equal"))
    ax.set_xlim(-1.4, 1.4); ax.set_ylim(-0.65, 1.4); ax.axis("off")
    fig.patch.set_facecolor("#faf8f3")

    for lo, hi, col in [(0,70,"#fbeaef"),(70,80,"#fdf3ea"),
                        (80,90,"#fdf3ea"),(90,100,"#eaf4ef")]:
        t1 = 180-(lo/100)*180; t2 = 180-(hi/100)*180
        ax.add_patch(mpatches.Wedge((0,0),1.05,t2,t1,width=0.30,
                     facecolor=col, edgecolor="#faf8f3", linewidth=2))

    fg = bc(banda, "hex_fg")
    ang = math.radians(180-(puntaje/100)*180)
    ax.plot([0,0.74*math.cos(ang)],[0,0.74*math.sin(ang)],
            color=fg, lw=2.5, solid_capstyle="round", zorder=5)
    ax.add_patch(plt.Circle((0,0),0.065,color=fg,zorder=6))

    ax.text(0,-0.22,f"{puntaje:.1f}",ha="center",va="center",
            fontsize=26,fontweight="bold",color=fg,fontfamily="DejaVu Sans")
    ax.text(0,-0.46,banda,ha="center",va="center",
            fontsize=7.5,color="#6b638f",fontfamily="DejaVu Sans")

    for val,lbl in [(0,"0"),(70,"70"),(80,"80"),(90,"90"),(100,"100")]:
        a = math.radians(180-(val/100)*180)
        ax.text(1.22*math.cos(a),1.22*math.sin(a),lbl,
                ha="center",va="center",fontsize=6,
                color="#c9c2b3",fontfamily="DejaVu Sans")

    buf = io.BytesIO()
    plt.savefig(buf,format="png",dpi=160,bbox_inches="tight",
                facecolor="#faf8f3")
    plt.close(fig); buf.seek(0)
    return Image(buf, width=ancho_cm*cm, height=alto_cm*cm)


def crear_radar(competencias, banda, ancho_cm=13, alto_cm=10):
    etiq = list(competencias.keys())
    vals = [competencias[c]["puntaje"] for c in etiq]
    n = len(etiq)
    if n < 3:
        return _barras_fallback(competencias, ancho_cm, alto_cm)

    angles = np.linspace(0,2*np.pi,n,endpoint=False).tolist()
    vc = vals+[vals[0]]; ac = angles+[angles[0]]

    fg = bc(banda,"hex_fg"); bg = bc(banda,"hex_bg")

    fig, ax = plt.subplots(figsize=(ancho_cm/2.54,alto_cm/2.54),
                           subplot_kw=dict(polar=True))
    fig.patch.set_facecolor("#ffffff"); ax.set_facecolor("#ffffff")

    theta = np.linspace(0,2*np.pi,300)
    for lo,hi,col in [(65,70,"#fbeaef"),(70,80,"#fdf3ea"),
                      (80,90,"#fdf3ea"),(90,100,"#eaf4ef")]:
        ax.fill_between(theta,lo,hi,color=col,alpha=0.28,zorder=0)

    ax.plot(ac,vc,color=fg,linewidth=2,zorder=3)
    ax.fill(ac,vc,color=bg,alpha=0.50,zorder=2)
    ax.scatter(angles,vals,color=fg,s=25,zorder=4)

    etiq_c = [e if len(e)<=18 else e[:16]+"..." for e in etiq]
    ax.set_xticks(angles)
    ax.set_xticklabels(etiq_c,fontsize=8,color="#22194e",
                       fontfamily="DejaVu Sans")
    ax.tick_params(axis="x",pad=10)
    ax.set_ylim(60,100)
    ax.set_yticks([70,80,90,100])
    ax.set_yticklabels(["70","80","90","100"],
                       fontsize=6.5,color="#c9c2b3",fontfamily="DejaVu Sans")
    ax.grid(color="#e4dfd3",linewidth=0.6)
    ax.spines["polar"].set_color("#e4dfd3")

    buf = io.BytesIO()
    plt.savefig(buf,format="png",dpi=160,bbox_inches="tight",
                facecolor="#ffffff")
    plt.close(fig); buf.seek(0)
    return Image(buf, width=ancho_cm*cm, height=alto_cm*cm)


def _barras_fallback(competencias, ancho_cm, alto_cm):
    etiq = list(competencias.keys())
    vals = [competencias[c]["puntaje"] for c in etiq]
    fig, ax = plt.subplots(figsize=(ancho_cm/2.54, alto_cm/2.54))
    ax.barh(etiq, vals, color="#ff4298", height=0.5)
    ax.set_xlim(60,105)
    buf = io.BytesIO()
    plt.savefig(buf,format="png",dpi=160,bbox_inches="tight",facecolor="#fff")
    plt.close(fig); buf.seek(0)
    return Image(buf, width=ancho_cm*cm, height=alto_cm*cm)

# ---------------------------------------------------------------------------
# Header / Footer
# ---------------------------------------------------------------------------

def _header(c, nombre, proceso, page_num):
    if SPEEDSTER_LOGO.exists():
        try:
            img = ImageReader(str(SPEEDSTER_LOGO))
            iw, ih = img.getSize()
            logo_w = 5.20*cm
            logo_h = logo_w * (ih / iw)
            max_h = 1.60*cm
            if logo_h > max_h:
                logo_h = max_h
                logo_w = logo_h * (iw / ih)
            c.drawImage(
                str(SPEEDSTER_LOGO),
                PAD_LAT,
                H - 0.45*cm - logo_h,
                width=logo_w,
                height=logo_h,
                mask="auto",
            )
        except Exception:
            pass
    else:
        c.setFont("Helvetica-Bold", 16)
        c.setFillColor(INK)
        c.drawString(PAD_LAT, H - 1.25*cm, "Speedster")
    if LOGO_HEADER.exists():
        logo_w = 3.45*cm
        logo_h = logo_w * (80 / 356)
        c.drawImage(
            str(LOGO_HEADER),
            W - 0.62*cm - logo_w,
            H - 0.78*cm - logo_h,
            width=logo_w,
            height=logo_h,
            mask="auto",
        )
    else:
        c.setFont("Helvetica-BoldOblique", 16)
        c.setFillColor(INK)
        c.drawRightString(W - PAD_LAT, H - 1.25*cm, "evaluar")


def _footer(c, proceso, page_num):
    y = 0.58*cm
    c.setFont("Helvetica", 8)
    c.setFillColor(INK_SOFT)
    c.drawRightString(W - PAD_LAT, y, f"{page_num:02d} / {TOTAL_PAGES:02d}")

# ---------------------------------------------------------------------------
# Portada
# ---------------------------------------------------------------------------

def _portada(c, nombre, proceso, cliente, fecha, cargo="", area=""):
    c.setFillColor(PAPER); c.rect(0,0,W,H,fill=1,stroke=0)

    # Acento decorativo esquina superior derecha
    c.setFillColorRGB(1,0.259,0.596,alpha=0.07)
    c.circle(W+30, H+10, 190, fill=1, stroke=0)
    c.setFillColorRGB(1,0.671,0.282,alpha=0.05)
    c.circle(W, H+40, 140, fill=1, stroke=0)

    # Header
    y = H - PAD_TOP
    c.setStrokeColor(LINE); c.setLineWidth(0.5)
    c.line(PAD_LAT, y-0.70*cm, W-PAD_LAT, y-0.70*cm)
    c.setFont("Helvetica-Bold",9); c.setFillColor(MAGENTA)
    c.drawString(PAD_LAT, y-0.44*cm, "evaluar.com")
    c.setStrokeColor(LINE_STR); c.setLineWidth(0.5)
    c.line(PAD_LAT+1.9*cm, y-0.14*cm, PAD_LAT+1.9*cm, y-0.62*cm)
    c.setFont("Helvetica",8.5); c.setFillColor(INK_SOFT)
    c.drawString(PAD_LAT+2.1*cm, y-0.44*cm, cliente)
    c.setFont("Helvetica",8); c.setFillColor(INK_SOFT)
    c.drawRightString(W-PAD_LAT, y-0.44*cm, fecha)

    # Hero: eyebrow
    y_hero = H*0.60
    c.setFont("Helvetica-Bold",7.5); c.setFillColor(MAGENTA)
    c.drawString(PAD_LAT, y_hero+1.1*cm, proceso.upper())
    c.setStrokeColor(MAGENTA); c.setLineWidth(1.5)
    c.line(PAD_LAT, y_hero+0.82*cm, PAD_LAT+1.1*cm, y_hero+0.82*cm)

    # Nombre (dividido en dos lÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â­neas)
    partes = nombre.split()
    mitad  = max(1, len(partes)//2)
    l1 = " ".join(partes[:mitad])
    l2 = " ".join(partes[mitad:])

    c.setFont("Helvetica-Bold",42); c.setFillColor(INK)
    c.drawString(PAD_LAT, y_hero, l1)
    if l2:
        c.setFont("Helvetica-BoldOblique",42); c.setFillColor(INK2)
        c.drawString(PAD_LAT, y_hero-1.65*cm, l2)

    y_sep = y_hero - (2.55*cm if l2 else 1.30*cm)
    c.setStrokeColor(LINE); c.setLineWidth(0.5)
    c.line(PAD_LAT, y_sep, W-PAD_LAT, y_sep)

    # Ficha en grid 2 col
    campos = [("Proceso", proceso), ("Empresa", cliente)]
    if cargo: campos.insert(0, ("Rol / Puesto", cargo))
    if area:  campos.append(("\u00c1rea", area))

    col_w = (W - 2*PAD_LAT) / 2
    y_fi  = y_sep - 0.55*cm

    for i, (k, v) in enumerate(campos):
        x = PAD_LAT + (i%2)*col_w
        y = y_fi - (i//2)*1.35*cm
        c.setFont("Helvetica",7.5); c.setFillColor(INK_SOFT)
        c.drawString(x, y, k.upper())
        c.setFont("Helvetica-Bold",12); c.setFillColor(INK)
        v2 = v if len(v) <= 34 else v[:32]+"..."
        c.drawString(x, y-0.42*cm, v2)

    # Footer portada
    yf = PAD_BOT
    c.setStrokeColor(LINE); c.setLineWidth(0.5)
    c.line(PAD_LAT, yf+0.55*cm, W-PAD_LAT, yf+0.55*cm)
    c.setFont("Helvetica",8); c.setFillColor(INK_SOFT)
    c.drawString(PAD_LAT, yf+0.25*cm,
                 "Reporte Individual  \u00b7  Confidencial \u00b7 Uso interno de RRHH")
    c.drawRightString(W-PAD_LAT, yf+0.25*cm, f"01 / {TOTAL_PAGES:02d}")

# Portada de resultados
# ---------------------------------------------------------------------------

def _portada(c, nombre, proceso, cliente, fecha, cargo="", area="", contexto_integral=None):
    cover_bg = COVER_BG_OPTIMIZED if COVER_BG_OPTIMIZED.exists() else COVER_BG
    if cover_bg.exists():
        c.drawImage(str(cover_bg), 0, 0, width=W, height=H, preserveAspectRatio=False, mask="auto")
    else:
        c.setFillColor(colors.HexColor("#24164f"))
        c.rect(0, 0, W, H, fill=1, stroke=0)

    _draw_cover_logo(c, W - 0.55*cm, H - 0.45*cm, width=4.25*cm)

    ficha = (contexto_integral or {}).get("ficha", {}) or {}
    score = _cover_score(contexto_integral)

    x = 1.38*cm
    y = 8.70*cm
    cargo_linea = _texto(cargo or ficha.get("cargo") or proceso).upper()
    if len(cargo_linea) > 42:
        cargo_linea = cargo_linea[:39] + "..."

    c.setFillColor(WHITE)
    c.setFont("Helvetica", 13)
    c.drawString(x, y + 2.85*cm, cargo_linea)

    c.setFont("Helvetica-Bold", 27)
    c.drawString(x, y + 1.55*cm, "REPORTE DE")
    c.drawString(x, y + 0.60*cm, "RESULTADOS")

    _draw_pill(
        c,
        x,
        y - 0.28*cm,
        7.7*cm,
        0.55*cm,
        f"Finalizado: {fecha}",
        colors.HexColor("#e8e5ff"),
        colors.HexColor("#5b36d6"),
        size=8,
    )
    _draw_pill(
        c,
        x,
        y - 1.23*cm,
        7.7*cm,
        0.55*cm,
        f"Adecuaci\u00f3n: {score:.0f}%",
        colors.HexColor("#fff8ec"),
        colors.HexColor("#ff7a00"),
        size=8,
    )

    y_info = 3.65*cm
    _draw_contact_line(c, x, y_info, "person", nombre)
    _draw_contact_line(c, x, y_info - 0.56*cm, "brief", _texto(cargo or ficha.get("cargo") or proceso))
    area_txt = _texto(area or ficha.get("area") or ficha.get("empresa") or cliente)
    _draw_contact_line(c, x, y_info - 1.12*cm, "mail", area_txt)

    c.setFillColor(colors.HexColor("#15151f"))
    c.setFont("Helvetica-Bold", 18)
    c.drawRightString(W - 0.85*cm, 2.05*cm, cliente.upper()[:18])


# ---------------------------------------------------------------------------
# Tablas
# ---------------------------------------------------------------------------

def _tabla_tipos(desglose, pesos, ancho, estilos):
    tipos = [t for t in TIPOS_ORDEN if t in desglose]
    enc = [Paragraph(x, estilos["th"]) for x in
           ["TIPO DE EVALUADOR","PESO","PUNTAJE","BANDA"]]
    filas = [enc]
    for t in tipos:
        pts = desglose[t]; peso = pesos.get(t,0)
        banda = banda_desde_pts(pts); fg = bc(banda,"fg")
        filas.append([
            Paragraph(t, estilos["td_comp"]),
            Paragraph(f"{peso:.0f}%",
                      ParagraphStyle("p",fontName="Helvetica",fontSize=10,
                                     textColor=INK_SOFT,leading=14,
                                     alignment=TA_RIGHT)),
            Paragraph(f"<b>{pts:.1f}</b>",
                      ParagraphStyle("n",fontName="Helvetica-Bold",fontSize=10,
                                     textColor=fg,leading=14,alignment=TA_RIGHT)),
            Paragraph(banda,
                      ParagraphStyle("b",fontName="Helvetica-Bold",fontSize=8,
                                     textColor=fg,leading=12)),
        ])

    t = Table(filas, colWidths=[ancho*.38,ancho*.12,ancho*.18,ancho*.32],
              repeatRows=1)
    t.setStyle(TableStyle([
        ("TOPPADDING",    (0,0),(-1,0),7),("BOTTOMPADDING",(0,0),(-1,0),5),
        ("LINEBELOW",     (0,0),(-1,0),0.8,LINE_STR),
        ("TOPPADDING",    (0,1),(-1,-1),7),("BOTTOMPADDING",(0,1),(-1,-1),7),
        ("LINEBELOW",     (0,1),(-1,-1),0.4,LINE),
        ("LEFTPADDING",   (0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(-1,-1),4),
        ("VALIGN",        (0,0),(-1,-1),"MIDDLE"),
        ("ALIGN",         (1,0),(2,-1),"RIGHT"),
    ]))
    return t


def _tabla_competencias(competencias, ancho, estilos):
    tipos = []
    for d in competencias.values():
        for t in TIPOS_ORDEN:
            if t in d["desglose_tipo"] and t not in tipos:
                tipos.append(t)

    primer = next(iter(competencias.values()))

    enc1 = [Paragraph("COMPETENCIA", estilos["th"])]
    for t in tipos:
        enc1.append(Paragraph(t.upper(), estilos["th"]))
    enc1.append(Paragraph("PONDERADO", estilos["th"]))

    enc2 = [Paragraph("", estilos["th"])]
    for t in tipos:
        p = primer["pesos_aplicados"].get(t, 0)
        enc2.append(Paragraph(f"{p:.0f}%",
                    ParagraphStyle("pw",fontName="Helvetica",fontSize=8,
                                   textColor=MAGENTA,leading=11,
                                   alignment=TA_CENTER)))
    enc2.append(Paragraph("", estilos["th"]))

    filas = [enc1, enc2]
    for nom, d in competencias.items():
        banda = d["clasificacion"]["etiqueta"]; fg = bc(banda,"fg")
        fila = [Paragraph(nom, estilos["td_comp"])]
        for t in tipos:
            pts = d["desglose_tipo"].get(t)
            if pts is not None:
                fila.append(Paragraph(f"{pts:.1f}", estilos["td_num"]))
            else:
                fila.append(Paragraph("-",
                            ParagraphStyle("dash",fontName="Helvetica",
                                           fontSize=9,textColor=INK_SOFT,
                                           leading=13,alignment=TA_RIGHT)))
        fila.append(Paragraph(f"<b>{d['puntaje']:.1f}</b>",
                    ParagraphStyle("pond",fontName="Helvetica-Bold",fontSize=11,
                                   textColor=fg,leading=14,alignment=TA_RIGHT)))
        filas.append(fila)

    n = len(tipos)
    cw = [ancho*.30] + [(ancho*.50)/max(n,1)]*n + [ancho*.20]
    t  = Table(filas, colWidths=cw, repeatRows=2)

    style = [
        ("TOPPADDING",    (0,0),(-1,1),6),
        ("BOTTOMPADDING", (0,0),(-1,0),4),("BOTTOMPADDING",(0,1),(-1,1),6),
        ("LINEBELOW",     (0,0),(-1,0),0.5,LINE_STR),
        ("LINEBELOW",     (0,1),(-1,1),0.8,LINE_STR),
        ("TOPPADDING",    (0,2),(-1,-1),8),("BOTTOMPADDING",(0,2),(-1,-1),8),
        ("LINEBELOW",     (0,2),(-1,-1),0.4,LINE),
        ("LEFTPADDING",   (0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(-1,-1),4),
        ("VALIGN",        (0,0),(-1,-1),"MIDDLE"),
        ("ALIGN",         (1,0),(-1,-1),"RIGHT"),
        ("ALIGN",         (0,0),(0,-1),"LEFT"),
    ]
    for i in range(len(competencias)):
        if i%2==0:
            style.append(("BACKGROUND",(0,i+2),(-2,i+2),PAPER2))
    t.setStyle(TableStyle(style))
    return t


def _fmt_score_360(valor, dec=2):
    try:
        num = float(valor)
    except Exception:
        return "-"
    if abs(num - round(num)) < 0.005:
        return f"{num:.0f}"
    return f"{num:.{dec}f}".rstrip("0").rstrip(".")


def _tipo_eval_label(tipo):
    mapa = {
        "Autoevaluacion": "Autoevaluaci\u00f3n",
        "AutoevaluaciÃƒÆ’Ã‚Â³n": "Autoevaluaci\u00f3n",
        "Jefe": "Jefe Directo",
        "Cliente Interno": "Clientes Internos",
        "Pares": "Pares",
        "Subordinado": "Reportes Directos",
        "Reportes Directos": "Reportes Directos",
    }
    return mapa.get(tipo, tipo)


def _orden_tipos_360(tipos):
    orden = {
        "autoevaluacion": 0,
        "jefe": 1,
        "cliente interno": 2,
        "pares": 3,
        "subordinado": 4,
        "reportes directos": 4,
    }
    return sorted(tipos, key=lambda t: orden.get(_normalizar_clave(t), 99))


def _score_chip_360(valor, font_size=7.8, width_cm=1.28, compact=False, color_override=None, bg_override=None):
    try:
        num = float(valor)
    except Exception:
        num = None
    color = color_override or _color_puntaje_360(num or 0)
    bg = bg_override or ("#e5fff4" if (num or 0) >= 90 else "#fff2df" if (num or 0) >= 70 else "#ffe7ee")
    p = Paragraph(_fmt_score_360(valor), ParagraphStyle(
        "score_chip_360", fontName="Helvetica-Bold", fontSize=font_size,
        textColor=colors.HexColor(color), leading=9.2, alignment=TA_CENTER,
    ))
    t = Table([[p]], colWidths=[width_cm*cm])
    t.setStyle(TableStyle([
        ("TOPPADDING", (0,0), (-1,-1), 3 if compact else 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 3 if compact else 4),
        ("LEFTPADDING", (0,0), (-1,-1), 2),
        ("RIGHTPADDING", (0,0), (-1,-1), 2),
    ]))
    return RoundedBox(t, width_cm*cm, fill=colors.HexColor(bg), stroke=colors.HexColor(bg), radius=5, pad=0, stroke_width=0)


def _detalle_evaluacion_360(competencias, desglose, pesos, puntaje_global, ancho, estilos, compact=False):
    tipos = []
    for d in competencias.values():
        for t in d.get("desglose_tipo", {}):
            if t not in tipos:
                tipos.append(t)
    tipos = _orden_tipos_360(tipos)

    title_style = ParagraphStyle(
        "detalle360_title", fontName="Helvetica-Bold", fontSize=9.8 if compact else 10.6,
        textColor=INK, leading=12 if compact else 13,
    )
    label_style = ParagraphStyle(
        "detalle360_label", fontName="Helvetica", fontSize=7.8 if compact else 8.4,
        textColor=INK_SOFT, leading=9.2 if compact else 10, alignment=TA_RIGHT,
    )
    band = Table([[
        Paragraph("Competencias", title_style),
        Paragraph("Promedio general", label_style),
        _score_chip_360(puntaje_global, font_size=7.7 if compact else 8.2, width_cm=1.30 if compact else 1.38, compact=compact),
    ]], colWidths=[ancho - 5.45*cm, 3.55*cm, 1.45*cm])
    band.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), colors.HexColor("#fbfaff")),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("LEFTPADDING", (0,0), (-1,-1), 13 if compact else 15),
        ("RIGHTPADDING", (0,0), (-1,-1), 8),
        ("TOPPADDING", (0,0), (-1,-1), 6 if compact else 9),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6 if compact else 9),
    ]))
    band_box = RoundedBox(band, ancho, fill=colors.HexColor("#fbfaff"), stroke=colors.HexColor("#fbfaff"), radius=10, pad=0, stroke_width=0)

    th = ParagraphStyle(
        "detalle360_th", fontName="Helvetica-Bold", fontSize=6.6 if compact else 7.2,
        textColor=INK_SOFT, leading=8.0 if compact else 8.8, alignment=TA_CENTER,
    )
    th_left = ParagraphStyle(
        "detalle360_th_left", parent=th, alignment=TA_LEFT,
    )
    td = ParagraphStyle(
        "detalle360_td", fontName="Helvetica", fontSize=7.3 if compact else 8.0,
        textColor=INK2, leading=9.2 if compact else 10.2, alignment=TA_CENTER,
    )
    td_comp = ParagraphStyle(
        "detalle360_td_comp", fontName="Helvetica", fontSize=7.35 if compact else 8.1,
        textColor=INK2, leading=9.3 if compact else 10.5,
    )

    header = [Paragraph("Competencia", th_left)]
    for tipo in tipos:
        peso = float(pesos.get(tipo, 0) or 0)
        header.append(Paragraph(f"{_tipo_eval_label(tipo)}<br/><font color='#9b96b8'>{peso:.0f} %</font>", th))
    header.append(Paragraph("Resultado", th))

    averages = [Paragraph("", th_left)]
    for tipo in tipos:
        averages.append(_score_chip_360(desglose.get(tipo), font_size=6.7 if compact else 7.2, width_cm=1.10 if compact else 1.18, compact=compact))
    averages.append(Paragraph("", th))

    data = [header, averages]
    for idx, (nom, d) in enumerate(competencias.items(), start=1):
        fila = [Paragraph(f"{idx}. {_texto(nom)}", td_comp)]
        for tipo in tipos:
            valor = d.get("desglose_tipo", {}).get(tipo)
            fila.append(Paragraph(_fmt_score_360(valor), td) if valor is not None else Paragraph("-", td))
        fila.append(_score_chip_360(d.get("puntaje"), font_size=6.9 if compact else 7.5, width_cm=1.12 if compact else 1.22, compact=compact))
        data.append(fila)

    comp_w = ancho * 0.25
    result_w = 1.85*cm
    tipo_w = (ancho - comp_w - result_w) / max(len(tipos), 1)
    table = Table(data, colWidths=[comp_w] + [tipo_w]*len(tipos) + [result_w], repeatRows=2)
    style = [
        ("BACKGROUND", (0,0), (-1,1), colors.HexColor("#fbfaff")),
        ("BOX", (0,0), (-1,-1), 0.55, colors.HexColor("#ded8fb")),
        ("INNERGRID", (0,0), (-1,-1), 0.35, colors.HexColor("#e9e7f8")),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("LEFTPADDING", (0,0), (-1,-1), 7 if compact else 8),
        ("RIGHTPADDING", (0,0), (-1,-1), 7 if compact else 8),
        ("TOPPADDING", (0,0), (-1,0), 5 if compact else 8),
        ("BOTTOMPADDING", (0,0), (-1,0), 2 if compact else 3),
        ("TOPPADDING", (0,1), (-1,1), 2 if compact else 3),
        ("BOTTOMPADDING", (0,1), (-1,1), 5 if compact else 8),
        ("TOPPADDING", (0,2), (-1,-1), 5 if compact else 9),
        ("BOTTOMPADDING", (0,2), (-1,-1), 5 if compact else 9),
        ("ALIGN", (1,1), (-1,-1), "CENTER"),
    ]
    for i in range(2, len(data)):
        if i % 2 == 0:
            style.append(("BACKGROUND", (0,i), (-1,i), colors.HexColor("#fdfcff")))
    table.setStyle(TableStyle(style))

    return [band_box, spacer(0.22 if compact else 0.45), table]


def _wrap_label_chart(text, max_len=16):
    words = _texto(text, "").split()
    lines = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) <= max_len:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return "\n".join(lines[:2])


def _valor_org_competencia(nombre, item, promedios_org):
    if promedios_org:
        valor = promedios_org.get(_normalizar_clave(nombre))
        if valor is not None:
            try:
                return float(valor)
            except Exception:
                pass
    return float(item.get("puntaje", 0) or 0)


def crear_mapa_competencias_360(competencias, promedios_org=None, ancho_cm=10.3, alto_cm=10.3):
    labels = list(competencias.keys())
    vals_eval = [float(competencias[c]["puntaje"]) for c in labels]
    vals_org = [_valor_org_competencia(c, competencias[c], promedios_org or {}) for c in labels]
    n = len(labels)
    if n < 3:
        return _barras_fallback(competencias, ancho_cm, alto_cm)

    angles = np.linspace(0, 2*np.pi, n, endpoint=False).tolist()
    ac = angles + [angles[0]]
    eval_closed = vals_eval + [vals_eval[0]]
    org_closed = vals_org + [vals_org[0]]

    fig, ax = plt.subplots(
        figsize=(ancho_cm/2.54, alto_cm/2.54),
        subplot_kw=dict(polar=True),
    )
    fig.patch.set_facecolor("#ffffff")
    ax.set_facecolor("#ffffff")
    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)
    ax.set_ylim(0, 126)
    ax.set_yticks([20, 40, 60, 80, 100])
    ax.set_yticklabels([])
    ax.grid(color="#ded8fb", linewidth=0.75)
    ax.spines["polar"].set_visible(False)

    ax.plot(ac, org_closed, color="#5b36d6", linewidth=1.55, zorder=3)
    ax.fill(ac, org_closed, color="#5b36d6", alpha=0.10, zorder=1)
    ax.plot(ac, eval_closed, color="#ff66c4", linewidth=1.85, zorder=4)
    ax.fill(ac, eval_closed, color="#ff66c4", alpha=0.34, zorder=2)
    ax.scatter(angles, vals_eval, s=16, color="#ff66c4", edgecolor="#ffffff", linewidth=0.6, zorder=5)

    ax.set_xticks(angles)
    ax.set_xticklabels([])
    ax.tick_params(axis="x", pad=0, length=0)

    for angle, label in zip(angles, labels):
        x_vis = math.sin(angle)
        y_vis = math.cos(angle)
        ha = "left" if x_vis > 0.28 else "right" if x_vis < -0.28 else "center"
        va = "bottom" if y_vis > 0.48 else "top" if y_vis < -0.48 else "center"
        ax.text(
            angle,
            122,
            _wrap_label_chart(label, max_len=13),
            ha=ha,
            va=va,
            fontsize=6.25,
            color="#3a3170",
            fontfamily="DejaVu Sans",
            fontweight="bold",
            linespacing=1.05,
            clip_on=False,
        )

    for angle, val in zip(angles, vals_eval):
        x_vis = math.sin(angle)
        ha = "left" if x_vis > 0.45 else "right" if x_vis < -0.45 else "center"
        ax.text(
            angle,
            106,
            _fmt_score_360(val, dec=1),
            ha=ha,
            va="center",
            fontsize=5.85,
            color="#6b638f",
            fontfamily="DejaVu Sans",
            bbox=dict(boxstyle="round,pad=0.10", facecolor="#ffffff", edgecolor="none", alpha=0.78),
            clip_on=False,
        )

    buf = io.BytesIO()
    fig.subplots_adjust(top=0.86, bottom=0.14, left=0.14, right=0.86)
    plt.savefig(buf, format="png", dpi=175, facecolor="#ffffff")
    plt.close(fig)
    buf.seek(0)
    return Image(buf, width=ancho_cm*cm, height=alto_cm*cm)


def _tabla_mapa_competencias_360(competencias, promedios_org, ancho, estilos):
    th = ParagraphStyle(
        "map360_th", fontName="Helvetica-Bold", fontSize=7.4,
        textColor=INK_SOFT, leading=9, alignment=TA_LEFT,
    )
    th_center = ParagraphStyle("map360_th_c", parent=th, alignment=TA_CENTER)
    td = ParagraphStyle(
        "map360_td", fontName="Helvetica", fontSize=8.0,
        textColor=INK2, leading=10,
    )
    dot_eval = "<font color='#ff66c4'>o</font> "
    dot_org = "<font color='#5b36d6'>o</font> "
    data = [[
        Paragraph("Competencia", th),
        Paragraph(f"{dot_eval}Individual", th_center),
        Paragraph(f"{dot_org}Organizaci\u00f3n", th_center),
    ]]
    for nombre, item in competencias.items():
        puntaje = float(item.get("puntaje", 0) or 0)
        org = _valor_org_competencia(nombre, item, promedios_org or {})
        data.append([
            Paragraph(_texto(nombre), td),
            _score_chip_360(puntaje, font_size=7.2, width_cm=1.25, compact=True, color_override="#ff2fa0", bg_override="#fff0f8"),
            _score_chip_360(org, font_size=7.2, width_cm=1.25, compact=True, color_override="#5b36d6", bg_override="#f0ecff"),
        ])

    table = Table(data, colWidths=[ancho*0.43, ancho*0.285, ancho*0.285], repeatRows=1)
    style = [
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#fbfaff")),
        ("BOX", (0,0), (-1,-1), 0.55, colors.HexColor("#ded8fb")),
        ("INNERGRID", (0,0), (-1,-1), 0.35, colors.HexColor("#e9e7f8")),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("LEFTPADDING", (0,0), (-1,-1), 10),
        ("RIGHTPADDING", (0,0), (-1,-1), 10),
        ("TOPPADDING", (0,0), (-1,0), 8),
        ("BOTTOMPADDING", (0,0), (-1,0), 8),
        ("TOPPADDING", (0,1), (-1,-1), 7),
        ("BOTTOMPADDING", (0,1), (-1,-1), 7),
        ("ALIGN", (1,1), (-1,-1), "CENTER"),
    ]
    for i in range(1, len(data)):
        if i % 2 == 0:
            style.append(("BACKGROUND", (0,i), (-1,i), colors.HexColor("#fdfcff")))
    table.setStyle(TableStyle(style))
    return table


def _mapa_competencias_360_page(competencias, promedios_org, ancho, estilos):
    title_row = Table([[
        Paragraph("Mapa de competencias", ParagraphStyle(
            "map360_title", fontName="Helvetica-Bold", fontSize=16.4,
            textColor=INK, leading=20,
        )),
    ]], colWidths=[ancho])
    title_row.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("LEFTPADDING", (0,0), (-1,-1), 0),
        ("RIGHTPADDING", (0,0), (-1,-1), 0),
        ("TOPPADDING", (0,0), (-1,-1), 0),
        ("BOTTOMPADDING", (0,0), (-1,-1), 0),
    ]))
    chart = crear_mapa_competencias_360(competencias, promedios_org, ancho_cm=11.45, alto_cm=11.45)
    chart_table = Table([[chart]], colWidths=[ancho])
    chart_table.setStyle(TableStyle([
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("LEFTPADDING", (0,0), (-1,-1), 0),
        ("RIGHTPADDING", (0,0), (-1,-1), 0),
        ("TOPPADDING", (0,0), (-1,-1), 0),
        ("BOTTOMPADDING", (0,0), (-1,-1), 0),
    ]))
    return [
        title_row,
        spacer(0.22),
        chart_table,
        spacer(0.22),
        _tabla_mapa_competencias_360(competencias, promedios_org, ancho, estilos),
    ]


def _bar_score_item(value, color_hex="#ff2fa0", width_cm=3.75, height_cm=0.38):
    try:
        val = max(0, min(100, float(value)))
    except Exception:
        val = 0
    width = width_cm * cm
    height = height_cm * cm
    track_w = width - 0.75*cm
    bar_h = 0.075*cm
    y = height / 2 - bar_h / 2
    drawing = Drawing(width, height)
    drawing.add(Rect(0, y, track_w, bar_h, fillColor=colors.HexColor("#e6e5ee"), strokeColor=None))
    drawing.add(Rect(0, y, track_w * (val / 100), bar_h, fillColor=colors.HexColor(color_hex), strokeColor=None))
    drawing.add(String(track_w + 0.22*cm, y - 0.02*cm, _fmt_score_360(val, dec=1),
                       fontName="Helvetica-Bold", fontSize=6.2,
                       fillColor=colors.HexColor("#3a3170")))
    return drawing


def _competencia_items_card(nombre, items, ancho):
    title = Table([[
        Paragraph(_texto(nombre), ParagraphStyle(
            "item360_comp_title", fontName="Helvetica-Bold", fontSize=9.4,
            textColor=INK, leading=11,
        )),
    ]], colWidths=[ancho])
    title.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("LEFTPADDING", (0,0), (-1,-1), 0),
        ("RIGHTPADDING", (0,0), (-1,-1), 0),
        ("TOPPADDING", (0,0), (-1,-1), 0),
        ("BOTTOMPADDING", (0,0), (-1,-1), 0),
    ]))

    th = ParagraphStyle(
        "item360_th", fontName="Helvetica-Bold", fontSize=6.45,
        textColor=INK_SOFT, leading=7.7,
    )
    td = ParagraphStyle(
        "item360_td", fontName="Helvetica", fontSize=6.25,
        textColor=INK2, leading=7.5,
    )
    head = [
        Paragraph("Comportamiento", th),
        Paragraph("<font color='#ff2fa0'>o</font> Individual", th),
        Paragraph("<font color='#5b36d6'>o</font> Organizaci\u00f3n", th),
    ]
    data = [head]
    for item in items:
        data.append([
            Paragraph(_texto(item.get("item")), td),
            _bar_score_item(item.get("puntaje"), "#ff2fa0", width_cm=3.35, height_cm=0.32),
            _bar_score_item(item.get("organizacion"), "#5b36d6", width_cm=3.35, height_cm=0.32),
        ])
    table = Table(data, colWidths=[ancho*0.38, ancho*0.31, ancho*0.31], repeatRows=1)
    style = [
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#fbfaff")),
        ("BOX", (0,0), (-1,-1), 0.45, colors.HexColor("#ded8fb")),
        ("INNERGRID", (0,0), (-1,-1), 0.25, colors.HexColor("#ebe8f8")),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("LEFTPADDING", (0,0), (-1,-1), 7),
        ("RIGHTPADDING", (0,0), (-1,-1), 7),
        ("TOPPADDING", (0,0), (-1,0), 5),
        ("BOTTOMPADDING", (0,0), (-1,0), 5),
        ("TOPPADDING", (0,1), (-1,-1), 4),
        ("BOTTOMPADDING", (0,1), (-1,-1), 4),
    ]
    for i in range(1, len(data)):
        if i % 2 == 0:
            style.append(("BACKGROUND", (0,i), (-1,i), colors.HexColor("#fdfcff")))
    table.setStyle(TableStyle(style))

    inner = [title, spacer(0.10), table]
    wrapped = Table([[inner]], colWidths=[ancho])
    wrapped.setStyle(TableStyle([
        ("LEFTPADDING", (0,0), (-1,-1), 0),
        ("RIGHTPADDING", (0,0), (-1,-1), 0),
        ("TOPPADDING", (0,0), (-1,-1), 0),
        ("BOTTOMPADDING", (0,0), (-1,-1), 0),
    ]))
    return wrapped


def _items_360_pages(items_360, ancho, orden_competencias=None, por_pagina=6):
    competencias_items = [(comp, vals) for comp, vals in (items_360 or {}).items() if vals]
    if orden_competencias:
        orden = {_normalizar_clave(comp): idx for idx, comp in enumerate(orden_competencias)}
        competencias_items.sort(key=lambda pair: orden.get(_normalizar_clave(pair[0]), 999))
    pages = []
    for start in range(0, len(competencias_items), por_pagina):
        chunk = competencias_items[start:start + por_pagina]
        flow = [
            Paragraph("Comportamientos espec\u00edficos", ParagraphStyle(
                "items360_title", fontName="Helvetica-Bold", fontSize=13.8,
                textColor=INK, leading=16,
            )),
            spacer(0.14),
        ]
        for idx, (comp, vals) in enumerate(chunk):
            flow.append(_competencia_items_card(comp, vals, ancho))
            if idx < len(chunk) - 1:
                flow.append(spacer(0.20))
        pages.append(flow)
    return pages


def _leyenda_bandas(ancho, estilos):
    items = [
        ("Alto Desempe\u00f1o", "\u2265 90", "#eaf4ef", "#2f7d5e"),
        ("Satisfactorio", "80-89", "#fdf3ea", "#b45a1f"),
        ("Bajo Desempe\u00f1o", "70-79", "#fdf3ea", "#b45a1f"),
        ("Insatisfactorio","< 70","#fbeaef","#a32a4d"),
    ]
    celdas = []
    for etiq, rng, bg, fg in items:
        inner = Table([[Paragraph(
            f"<b>{etiq}</b>   {rng}",
            ParagraphStyle("ley",fontName="Helvetica-Bold",fontSize=8.5,
                           textColor=colors.HexColor(fg),leading=13),
        )]], colWidths=[ancho/4 - 0.4*cm])
        inner.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(-1,-1),colors.HexColor(bg)),
            ("TOPPADDING",    (0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5),
            ("LEFTPADDING",   (0,0),(-1,-1),8),("RIGHTPADDING",(0,0),(-1,-1),8),
        ]))
        celdas.append(inner)

    t = Table([celdas], colWidths=[ancho/4]*4)
    t.setStyle(TableStyle([
        ("LEFTPADDING",  (0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(-1,-1),4),
        ("TOPPADDING",   (0,0),(-1,-1),0),("BOTTOMPADDING",(0,0),(-1,-1),0),
        ("VALIGN",       (0,0),(-1,-1),"TOP"),
    ]))
    return t

# ---------------------------------------------------------------------------
# Texto descriptivo por banda
# ---------------------------------------------------------------------------

def _desc_banda(banda):
    return {
        "Alto Desempe\u00f1o": (
            "El colaborador demuestra un desempe\u00f1o que supera las expectativas "
            "de manera consistente. Sus resultados reflejan dominio s\u00f3lido de "
            "las competencias evaluadas y lo posicionan como referente positivo "
            "dentro del equipo."
        ),
        "Satisfactorio": (
            "El colaborador cumple con las expectativas del rol de forma adecuada. "
            "Las competencias evaluadas est\u00e1n en el nivel esperado, con oportunidades "
            "puntuales de mejora para alcanzar un desempe\u00f1o destacado."
        ),
        "Bajo Desempe\u00f1o": (
            "El colaborador cumple parcialmente con las expectativas. Se identifican "
            "brechas en varias competencias que requieren atenci\u00f3n y un plan de "
            "desarrollo estructurado para alcanzar el nivel requerido."
        ),
        "Insatisfactorio": (
            "El colaborador no alcanza las expectativas m\u00ednimas del rol. Se requiere "
            "intervenci\u00f3n inmediata con acompa\u00f1amiento continuo y seguimiento "
            "estrecho para revertir esta situaci\u00f3n."
        ),
    }.get(banda, "")


def _cover_score(contexto):
    integrado = (contexto or {}).get("integrado", {}) or {}
    for key in ("integrada", "potencial", "evd_360"):
        valor = integrado.get(key)
        try:
            if valor is not None and not math.isnan(float(valor)):
                return float(valor)
        except Exception:
            continue
    resultado = (contexto or {}).get("resultado_360", {}) or {}
    return float(resultado.get("puntaje_global", 0) or 0)


def _draw_pill(c, x, y, w, h, text, fill, color, font="Helvetica-Bold", size=8):
    c.saveState()
    c.setFillColor(fill)
    c.roundRect(x, y, w, h, h / 2, fill=1, stroke=0)
    c.setFillColor(color)
    c.setFont(font, size)
    c.drawCentredString(x + w / 2, y + h * 0.34, text)
    c.restoreState()


def _draw_cover_logo(c, x_right, y_top, width=3.0*cm):
    """Dibuja el logo de Evaluar sobre la portada."""
    if LOGO_COVER.exists():
        img = ImageReader(str(LOGO_COVER))
        iw, ih = img.getSize()
        ratio = ih / iw if iw else 96 / 380
        c.drawImage(
            img,
            x_right - width,
            y_top - width * ratio,
            width=width,
            height=width * ratio,
            mask="auto",
        )
        return
    c.saveState()
    font = "Helvetica-BoldOblique"
    size = 18
    text = "evaluar"
    total = stringWidth(text, font, size)
    scale = width / total
    c.translate(x_right - width, y_top - size * scale)
    c.scale(scale, scale)
    c.setFont(font, size)
    c.setFillColor(WHITE)
    c.drawString(0, 0, text)
    c.restoreState()


def _draw_contact_line(c, x, y, icon, text):
    c.saveState()
    c.setStrokeColor(WHITE)
    c.setFillColor(WHITE)
    c.setLineWidth(1)
    if icon == "person":
        c.circle(x + 0.08*cm, y + 0.08*cm, 0.07*cm, stroke=1, fill=0)
        c.arc(x, y - 0.06*cm, x + 0.16*cm, y + 0.09*cm, 20, 140)
    elif icon == "brief":
        c.roundRect(x, y - 0.02*cm, 0.18*cm, 0.14*cm, 0.02*cm, stroke=1, fill=0)
        c.line(x + 0.06*cm, y + 0.13*cm, x + 0.12*cm, y + 0.13*cm)
    else:
        c.rect(x, y - 0.02*cm, 0.18*cm, 0.13*cm, stroke=1, fill=0)
        c.line(x, y + 0.11*cm, x + 0.09*cm, y + 0.04*cm)
        c.line(x + 0.18*cm, y + 0.11*cm, x + 0.09*cm, y + 0.04*cm)
    c.setFont("Helvetica", 8.2)
    c.drawString(x + 0.38*cm, y, text[:58])
    c.restoreState()


def _valor_num(valor, dec=1, vacio="-"):
    try:
        if valor is None or (isinstance(valor, float) and math.isnan(valor)):
            return vacio
        return f"{float(valor):.{dec}f}"
    except Exception:
        return vacio


def _limpiar_mojibake(texto):
    if not isinstance(texto, str):
        return texto
    limpio = texto

    for _ in range(3):
        if not any(marca in limpio for marca in ("Ãƒ", "Ã‚", "Ã¢")):
            break
        try:
            reparado = limpio.encode("latin1", errors="ignore").decode("utf-8", errors="ignore")
        except Exception:
            break
        if not reparado or reparado == limpio:
            break
        limpio = reparado

    reemplazos = {
        "\u00c3\u0192\u00e2\u20ac\u2122\u00c3\u201a\u00c2\u00a1": "a",
        "\u00c3\u0192\u00e2\u20ac\u2122\u00c3\u201a\u00c2\u00a9": "e",
        "\u00c3\u0192\u00e2\u20ac\u2122\u00c3\u201a\u00c2\u00ad": "i",
        "\u00c3\u0192\u00e2\u20ac\u2122\u00c3\u201a\u00c2\u00b3": "o",
        "\u00c3\u0192\u00e2\u20ac\u2122\u00c3\u201a\u00c2\u00ba": "u",
        "\u00c3\u0192\u00e2\u20ac\u2122\u00c3\u201a\u00c2\u00b1": "n",
        "\u00c3\u0192\u00c2\u00a2\u00c3\u00a2\u00e2\u201a\u00ac\u00c5\u00a1\u00c3\u201a\u00c2\u00ac\u00c3\u0192\u00e2\u20ac\u0161\u00c3\u201a\u00c2\u00a2": "-",
        "\u00c3\u00a2\u00e2\u201a\u00ac\u00c2\u00a2": "-",
        "\u00e2\u20ac\u00a2": "-",
        "\u00c2\u00a0": " ",
        "\u00c2": "",
    }
    for origen, destino in reemplazos.items():
        limpio = limpio.replace(origen, destino)
    return limpio


def _texto(valor, vacio="-"):
    if valor is None:
        return vacio
    try:
        if isinstance(valor, float) and math.isnan(valor):
            return vacio
    except Exception:
        pass
    texto = _limpiar_mojibake(str(valor)).strip()
    return texto if texto else vacio


def _normalizar_clave(valor):
    texto = _texto(valor, "")
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(ch for ch in texto if not unicodedata.combining(ch))
    texto = re.sub(r"[^a-zA-Z0-9]+", " ", texto).strip().casefold()
    return re.sub(r"\s+", " ", texto)


def _catalogo_potencial():
    if not COMPETENCIAS_POT_JSON.exists():
        return {}
    try:
        data = json.loads(COMPETENCIAS_POT_JSON.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return {
        item.get("competencia"): item
        for item in data.get("competencias", [])
        if item.get("competencia")
    }


def _catalogo_competencias_interpretacion():
    if not COMPETENCIAS_INTERPRETACION_JSON.exists():
        return {}
    try:
        data = json.loads(COMPETENCIAS_INTERPRETACION_JSON.read_text(encoding="utf-8"))
    except Exception:
        return {}
    catalogo = {}
    for item in data.get("competencies", []):
        name = item.get("name")
        if name:
            catalogo[_normalizar_clave(name)] = item
    return catalogo


def _catalogo_disc():
    if not DISC_JSON.exists():
        return {}
    try:
        data = json.loads(DISC_JSON.read_text(encoding="utf-8"))
    except Exception:
        return {}
    catalogo = {}
    for item in data.get("archetypes", []):
        for key in (item.get("code"), item.get("archetype"), item.get("name")):
            if key:
                catalogo[_normalizar_clave(key)] = item
    return catalogo


def _disc_arquetipo_item(potencial):
    catalogo = _catalogo_disc()
    for key in (potencial.get("arquetipo"), potencial.get("disc")):
        item = catalogo.get(_normalizar_clave(key))
        if item:
            return item
    return {}


def _cap_config():
    if not CAP_JSON.exists():
        return {"ranges": []}
    try:
        return json.loads(CAP_JSON.read_text(encoding="utf-8"))
    except Exception:
        return {"ranges": []}


def _desempeno_360_config():
    if not DESEMPENO_360_JSON.exists():
        return {"ranges": [], "description_text": ""}
    try:
        return json.loads(DESEMPENO_360_JSON.read_text(encoding="utf-8"))
    except Exception:
        return {"ranges": [], "description_text": ""}


def _interpretacion_360(puntaje):
    try:
        valor = float(puntaje)
    except Exception:
        valor = 0
    for item in _desempeno_360_config().get("ranges", []):
        start = float(item.get("from", 0))
        end = float(item.get("to", 0))
        if valor >= start and valor < end:
            return item
    return {
        "label": "Sin rango",
        "title": "Resultado no clasificado",
        "interpretation": "El resultado no coincide con los rangos configurados.",
    }


def _objetivos_config():
    if not OBJETIVOS_JSON.exists():
        return {"ranges": [], "description_text": ""}
    try:
        return json.loads(OBJETIVOS_JSON.read_text(encoding="utf-8"))
    except Exception:
        return {"ranges": [], "description_text": ""}


def _interpretacion_objetivos(puntaje):
    try:
        valor = float(puntaje)
    except Exception:
        valor = 0
    for item in _objetivos_config().get("ranges", []):
        start = float(item.get("from", 0))
        end = float(item.get("to", 0))
        if valor >= start and valor < end:
            return item
    return {
        "label": "Sin rango",
        "title": "Resultado no clasificado",
        "interpretation": "El resultado no coincide con los rangos configurados.",
    }


def _color_puntaje_360(puntaje):
    try:
        valor = float(puntaje)
    except Exception:
        valor = 0
    if valor >= 90:
        return "#12c987"
    if valor >= 70:
        return "#ff8a00"
    return "#ff3b4f"


def _cap_interpretacion(score):
    if score is None:
        return {
            "name": "Sin dato",
            "interpretation": "No hay competencias de potencial suficientes para calcular el resultado global.",
        }
    percent = float(score) * 100
    for item in _cap_config().get("ranges", []):
        start = float(item.get("from", 0))
        end = float(item.get("to", 0))
        if end > 1:
            value = percent
            start_cmp = start * 100 if start <= 1 else start
            end_cmp = end
        else:
            value = score
            start_cmp = start
            end_cmp = end
        if value >= start_cmp and value < end_cmp:
            return item
    return {
        "name": "Sin rango",
        "interpretation": "El resultado global no coincide con los rangos configurados.",
    }


def _cap_color(name):
    if name in {"Alto potencial", "Potencial Alto", "Ajustado al Perfil"}:
        return colors.HexColor("#00A651")
    if name in {"Potencial medio", "Potencial Medio", "Cercano al Perfil"}:
        return colors.HexColor("#FF8A00")
    return colors.HexColor("#E53935")


def _cap_bg_color(name):
    if name in {"Alto potencial", "Potencial Alto", "Ajustado al Perfil"}:
        return colors.HexColor("#EAF7F0")
    if name in {"Potencial medio", "Potencial Medio", "Cercano al Perfil"}:
        return colors.HexColor("#FFF3E2")
    return colors.HexColor("#FDEBEC")


def _cap_color_hex(name):
    if name in {"Alto potencial", "Potencial Alto", "Ajustado al Perfil"}:
        return "#00A651"
    if name in {"Potencial medio", "Potencial Medio", "Cercano al Perfil"}:
        return "#FF8A00"
    return "#E53935"


def _level_color(label):
    if label in {"Muy desarrollado", "Desarrollado"}:
        return colors.HexColor("#00A651")
    if label in {"Moderadamente desarrollado", "En desarrollo"}:
        return colors.HexColor("#FF8A00")
    return colors.HexColor("#E53935")


def _level_bg_color(label):
    if label in {"Muy desarrollado", "Desarrollado"}:
        return colors.HexColor("#EAF7F0")
    if label in {"Moderadamente desarrollado", "En desarrollo"}:
        return colors.HexColor("#FFF3E2")
    return colors.HexColor("#FDEBEC")


def _card_table(content, width, bg="#ffffff", border="#e4dfd3", pad=10, radius=10):
    fill = colors.HexColor(bg) if isinstance(bg, str) else bg
    stroke = colors.HexColor(border) if isinstance(border, str) else border
    table = Table([[content]], colWidths=[width - 2*pad])
    table.setStyle(TableStyle([
        ("TOPPADDING", (0,0), (-1,-1), 0),
        ("BOTTOMPADDING", (0,0), (-1,-1), 0),
        ("LEFTPADDING", (0,0), (-1,-1), 0),
        ("RIGHTPADDING", (0,0), (-1,-1), 0),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
    ]))
    return RoundedBox(table, width, fill=fill, stroke=stroke, radius=radius, pad=pad, stroke_width=0.6)


def _nivel_competencia(catalog_item, valor):
    if not catalog_item:
        return {}
    try:
        score = float(valor)
    except Exception:
        return {}
    levels = catalog_item.get("levels", []) or []
    for level in levels:
        start = level.get("value_from")
        end = level.get("value_to")
        if start is None or end is None:
            continue
        upper_ok = score <= end if score >= 10 and float(end) >= 10 else score < end
        if score >= float(start) and upper_ok:
            return level
    return levels[0] if levels else {}


def _split_recommendations(text):
    text = _texto(text, "")
    if not text:
        return []
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    pattern = r"(?=(?:^|\s)(?:[a-h]\)|\d+\.))"
    parts = [part.strip(" \n\t;.-") for part in re.split(pattern, text) if part.strip(" \n\t;.-")]
    if len(parts) <= 1:
        parts = [line.strip(" \n\t;.-") for line in text.split("\n") if line.strip(" \n\t;.-")]
    limpias = []
    for part in parts[:5]:
        part = _texto(part, "")
        part = re.sub(r"^(?:[-\u2022]+|[a-h]\)|\d+\.)\s*", "", part).strip()
        part = re.sub(r"^[^\wÁÉÍÓÚÜÑáéíóúüñ¿¡]+", "", part).strip()
        if part:
            limpias.append(part)
    return limpias


def _metric_chip(label, value, color, bg="#ffffff"):
    content = [
        Paragraph(label.upper(), ParagraphStyle(
            "chip_l", fontName="Helvetica-Bold", fontSize=6.7,
            textColor=INK_SOFT, leading=8, alignment=TA_CENTER,
        )),
        Paragraph(value, ParagraphStyle(
            "chip_v", fontName="Helvetica-Bold", fontSize=8.4,
            textColor=color, leading=10, alignment=TA_CENTER,
        )),
    ]
    t = Table([[content]], colWidths=[2.45*cm])
    t.setStyle(TableStyle([
        ("TOPPADDING", (0,0), (-1,-1), 3),
        ("BOTTOMPADDING", (0,0), (-1,-1), 3),
        ("LEFTPADDING", (0,0), (-1,-1), 5),
        ("RIGHTPADDING", (0,0), (-1,-1), 5),
    ]))
    return RoundedBox(
        t,
        2.45*cm,
        fill=colors.HexColor(bg) if isinstance(bg, str) else bg,
        stroke=color,
        radius=7,
        stroke_width=0.7,
    )


def _level_badge(label):
    color = _level_color(label)
    bg = _level_bg_color(label)
    p = Paragraph(label, ParagraphStyle(
        "level_badge", fontName="Helvetica", fontSize=8.6,
        textColor=color, leading=10, alignment=TA_CENTER,
    ))
    t = Table([[p]], colWidths=[2.45*cm])
    t.setStyle(TableStyle([
        ("TOPPADDING", (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ("LEFTPADDING", (0,0), (-1,-1), 7),
        ("RIGHTPADDING", (0,0), (-1,-1), 7),
    ]))
    return RoundedBox(t, 2.45*cm, fill=bg, stroke=color, radius=10, stroke_width=0.7)


def _competencia_icon(color_hex="#5b36d6"):
    color = colors.HexColor(color_hex)
    d = Drawing(13, 16)
    d.add(Rect(2.5, 2.0, 9.0, 12.0, strokeColor=color, fillColor=None, strokeWidth=1.4))
    p = RLPath(strokeColor=color, fillColor=None, strokeWidth=1.2)
    p.moveTo(4.5, 14.0)
    p.lineTo(4.5, 5.6)
    p.lineTo(7.0, 7.8)
    p.lineTo(9.5, 5.6)
    p.lineTo(9.5, 14.0)
    d.add(p)
    return d


def _competencia_detalle_card(item, catalogo, ancho, estilos):
    nombre = _texto(item.get("competencia"))
    valor = item.get("valor")
    esperado = item.get("esperado")
    brecha = item.get("brecha")
    ajuste = item.get("ajuste")
    catalog_item = catalogo.get(_normalizar_clave(nombre), {})
    nivel = _nivel_competencia(catalog_item, valor)
    nivel_label = _texto(nivel.get("label"), "Sin nivel")

    try:
        ajuste_val = float(ajuste)
    except Exception:
        ajuste_val = None
    cap_name = _cap_interpretacion(ajuste_val).get("name") if ajuste_val is not None else "Sin dato"
    color = _level_color(nivel_label)
    bg = _level_bg_color(nivel_label)

    definition = _texto(catalog_item.get("definition"), "")
    interpretation = _texto(nivel.get("interpretation"), "No hay interpretaci\u00f3n configurada para este nivel.")
    recommendation = _texto(nivel.get("recommendation"), "")

    bullets = _split_recommendations(recommendation)
    title_style = ParagraphStyle(
        "comp_result_title", fontName="Helvetica-Bold", fontSize=10.9,
        textColor=INK_SOFT, leading=13,
    )
    section_style = ParagraphStyle(
        "comp_result_section", fontName="Helvetica-Bold", fontSize=9.5,
        textColor=colors.HexColor("#5b36d6"), leading=11.4,
    )
    body_style = ParagraphStyle(
        "comp_result_body", fontName="Helvetica", fontSize=8.4,
        textColor=INK_SOFT, leading=11.2, alignment=TA_JUSTIFY,
    )
    bullet_style = ParagraphStyle(
        "rec_bullet", fontName="Helvetica", fontSize=7.7,
        textColor=INK_SOFT, leading=9.8, leftIndent=13, firstLineIndent=-7,
    )
    rec_flow = [
        Paragraph(f"\u2022&nbsp;&nbsp;{rec}", bullet_style)
        for rec in bullets
    ] or [Paragraph("No hay recomendaciones configuradas para esta competencia.", estilos["nota"])]

    result_chip = RoundedBox(
        Table([[Paragraph(
            f"Resultado: {_valor_num(valor, 1)}",
            ParagraphStyle(
                "comp_result_chip", fontName="Helvetica-Bold", fontSize=8.8,
                textColor=color, leading=10.4, alignment=TA_CENTER,
            ),
        )]], colWidths=[2.75*cm]),
        2.75*cm,
        fill=bg,
        stroke=bg,
        radius=5,
        pad=3,
        stroke_width=0,
    )
    level_badge = RoundedBox(
        Table([[Paragraph(
            nivel_label,
            ParagraphStyle(
                "comp_level_badge_new", fontName="Helvetica", fontSize=8.7,
                textColor=color, leading=10.2, alignment=TA_CENTER,
            ),
        )]], colWidths=[2.55*cm]),
        2.55*cm,
        fill=bg,
        stroke=bg,
        radius=5,
        pad=3,
        stroke_width=0,
    )

    head_left = Table(
        [[_competencia_icon("#5b36d6"), Paragraph(nombre, title_style), result_chip]],
        colWidths=[0.48*cm, 4.95*cm, 3.00*cm],
    )
    head_left.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("LEFTPADDING", (0,0), (-1,-1), 0),
        ("RIGHTPADDING", (0,0), (-1,-1), 4),
        ("TOPPADDING", (0,0), (-1,-1), 0),
        ("BOTTOMPADDING", (0,0), (-1,-1), 0),
    ]))
    head = Table([[head_left, level_badge]], colWidths=[ancho - 3.70*cm, 2.75*cm])
    head.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("LEFTPADDING", (0,0), (-1,-1), 0),
        ("RIGHTPADDING", (0,0), (-1,-1), 0),
        ("TOPPADDING", (0,0), (-1,-1), 0),
        ("BOTTOMPADDING", (0,0), (-1,-1), 0),
        ("ALIGN", (1,0), (1,0), "RIGHT"),
    ]))

    body = [
        head,
        spacer(0.28),
        Paragraph("Interpretaci\u00f3n", section_style),
        spacer(0.08),
        Paragraph(interpretation, body_style),
        spacer(0.18),
        Paragraph("Recomendaciones", section_style),
        spacer(0.08),
        *rec_flow,
    ]

    card = Table([[body]], colWidths=[ancho - 0.40*cm])
    card.setStyle(TableStyle([
        ("TOPPADDING", (0,0), (-1,-1), 10),
        ("BOTTOMPADDING", (0,0), (-1,-1), 10),
        ("LEFTPADDING", (0,0), (-1,-1), 12),
        ("RIGHTPADDING", (0,0), (-1,-1), 12),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
    ]))
    rounded = RoundedBox(
        card,
        ancho,
        fill=colors.HexColor("#f5f3ff"),
        stroke=colors.HexColor("#e6e1fb"),
        radius=10,
        pad=0,
        stroke_width=0.55,
    )
    return KeepTogether([rounded, spacer(0.25)])


def crear_donut_cap(percent, label, ancho_cm=4.2, alto_cm=4.2):
    valor = 0 if percent is None else max(0, min(100, float(percent)))
    fig, ax = plt.subplots(figsize=(ancho_cm/2.54, alto_cm/2.54), subplot_kw=dict(aspect="equal"))
    fig.patch.set_facecolor("#ffffff")
    ax.axis("off")
    color = "#00A651" if label in {"Alto potencial", "Potencial Alto", "Ajustado al Perfil"} else "#FF8A00" if label in {"Potencial medio", "Potencial Medio", "Cercano al Perfil"} else "#E53935"
    ax.pie(
        [valor, 100 - valor],
        startangle=90,
        counterclock=False,
        colors=[color, "#e8f1fb"],
        wedgeprops=dict(width=0.18, edgecolor="#ffffff"),
    )
    ax.text(0, 0.10, f"{valor:.0f}%", ha="center", va="center",
            fontsize=21, fontweight="bold", color=color, fontfamily="DejaVu Sans")
    ax.text(0, -0.24, "GLOBAL", ha="center", va="center",
            fontsize=8, color="#6b638f", fontfamily="DejaVu Sans")
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=170, bbox_inches="tight", facecolor="#ffffff")
    plt.close(fig)
    buf.seek(0)
    return Image(buf, width=ancho_cm*cm, height=alto_cm*cm)


def crear_donut_360(percent, color_hex="#12c987", ancho_cm=3.05, alto_cm=3.05):
    valor = 0 if percent is None else max(0, min(100, float(percent)))
    fig, ax = plt.subplots(figsize=(ancho_cm/2.54, alto_cm/2.54), subplot_kw=dict(aspect="equal"))
    fig.patch.set_facecolor("#ffffff")
    ax.axis("off")
    ax.pie(
        [valor, 100 - valor],
        startangle=90,
        counterclock=False,
        radius=1.16,
        colors=[color_hex, "#eeeafb"],
        wedgeprops=dict(width=0.11, edgecolor="#ffffff", linewidth=2),
    )
    ax.text(0, 0.06, f"{valor:.2f}%", ha="center", va="center",
            fontsize=12.4, fontweight="bold", color="#22194e", fontfamily="DejaVu Sans")
    ax.text(0, -0.22, "resultado", ha="center", va="center",
            fontsize=6.8, color="#8b86a8", fontfamily="DejaVu Sans")
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=170, bbox_inches="tight", facecolor="#ffffff")
    plt.close(fig)
    buf.seek(0)
    return Image(buf, width=ancho_cm*cm, height=alto_cm*cm)


def _mini_icon(label, color_hex="#6f3cff", bg_hex="#f0ecff"):
    color = colors.HexColor(color_hex)
    bg = colors.HexColor(bg_hex)
    text = Paragraph(label, ParagraphStyle(
        "mini_icon", fontName="Helvetica-Bold", fontSize=12,
        textColor=color, leading=14, alignment=TA_CENTER,
    ))
    inner = Table([[text]], colWidths=[0.95*cm])
    inner.setStyle(TableStyle([
        ("TOPPADDING", (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("LEFTPADDING", (0,0), (-1,-1), 0),
        ("RIGHTPADDING", (0,0), (-1,-1), 0),
    ]))
    return RoundedBox(inner, 0.95*cm, fill=bg, stroke=bg, radius=8, pad=0, stroke_width=0)


def _pill_flow(label, color_hex="#5b36d6", bg_hex="#f0ecff", width_cm=3.0, font_size=7.6):
    text = Paragraph(label, ParagraphStyle(
        "pill_flow", fontName="Helvetica-Bold", fontSize=font_size,
        textColor=colors.HexColor(color_hex), leading=9.2, alignment=TA_CENTER,
    ))
    t = Table([[text]], colWidths=[width_cm*cm])
    t.setStyle(TableStyle([
        ("LEFTPADDING", (0,0), (-1,-1), 0),
        ("RIGHTPADDING", (0,0), (-1,-1), 0),
        ("TOPPADDING", (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ]))
    return RoundedBox(t, width_cm*cm, fill=colors.HexColor(bg_hex), stroke=colors.HexColor(bg_hex), radius=8, pad=0, stroke_width=0)


def _card_360_descripcion(ancho):
    cfg = _desempeno_360_config()
    title_style = ParagraphStyle(
        "card360_title", fontName="Helvetica-Bold", fontSize=10.2,
        textColor=INK, leading=12.5,
    )
    body_style = ParagraphStyle(
        "card360_body", fontName="Helvetica", fontSize=10.0,
        textColor=INK2, leading=14.4, alignment=TA_JUSTIFY,
    )
    eyebrow_style = ParagraphStyle(
        "card360_eyebrow", fontName="Helvetica-Bold", fontSize=7.2,
        textColor=MAGENTA, leading=9,
    )
    row = Table([[
        [
            Paragraph("MARCO DE LECTURA", eyebrow_style),
            spacer(0.06),
            Paragraph("Descripci\u00f3n de la evaluaci\u00f3n", title_style),
            spacer(0.18),
            Paragraph(_texto(cfg.get("description_text")), body_style),
        ],
    ]], colWidths=[ancho - 2.0*cm])
    row.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 0),
        ("RIGHTPADDING", (0,0), (-1,-1), 0),
        ("TOPPADDING", (0,0), (-1,-1), 0),
        ("BOTTOMPADDING", (0,0), (-1,-1), 0),
    ]))
    content = [row]
    return _card_table(content, ancho, bg="#fbfaff", border="#ded8fb", pad=15, radius=12)


def _card_360_puntuacion(puntaje, banda, ancho):
    info = _interpretacion_360(puntaje)
    color_hex = _color_puntaje_360(puntaje)
    title_style = ParagraphStyle(
        "card360_score_title", fontName="Helvetica-Bold", fontSize=10.8,
        textColor=INK, leading=13,
    )
    body_style = ParagraphStyle(
        "card360_score_body", fontName="Helvetica", fontSize=9.45,
        textColor=INK2, leading=13.2, alignment=TA_LEFT,
    )
    label_style = ParagraphStyle(
        "card360_label", fontName="Helvetica-Bold", fontSize=7.4,
        textColor=colors.HexColor(color_hex), leading=9,
    )
    left = [
        Paragraph("Puntuaci\u00f3n general", title_style),
        spacer(0.08),
        Paragraph(_texto(info.get("label")).upper(), label_style),
        spacer(0.14),
        Paragraph(f"<b>{_texto(info.get('title'))}.</b> {_texto(info.get('interpretation'))}", body_style),
    ]
    score_panel = RoundedBox(
        Table([[crear_donut_360(puntaje, color_hex, ancho_cm=3.25, alto_cm=3.25)]], colWidths=[3.55*cm]),
        3.78*cm,
        fill=colors.white,
        stroke=colors.HexColor("#eeeafb"),
        radius=14,
        pad=6,
        stroke_width=0.5,
    )
    row = Table([[
        left,
        score_panel,
    ]], colWidths=[ancho - 5.25*cm, 3.78*cm])
    row.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("LEFTPADDING", (0,0), (-1,-1), 0),
        ("RIGHTPADDING", (0,0), (-1,-1), 0),
        ("RIGHTPADDING", (0,0), (0,0), 14),
        ("TOPPADDING", (0,0), (-1,-1), 0),
        ("BOTTOMPADDING", (0,0), (-1,-1), 0),
        ("ALIGN", (1,0), (1,0), "CENTER"),
    ]))
    return _card_table([row], ancho, bg="#ffffff", border="#ded8fb", pad=15, radius=12)


def _card_potencial_descripcion(ancho):
    content = [
        Paragraph("MARCO DE LECTURA", ParagraphStyle(
            "pot_desc_eye", fontName="Helvetica-Bold", fontSize=7.2,
            textColor=MAGENTA, leading=9,
        )),
        spacer(0.06),
        Paragraph("Descripción de la evaluación", ParagraphStyle(
            "pot_desc_title", fontName="Helvetica-Bold", fontSize=10.5,
            textColor=INK, leading=12.5,
        )),
        spacer(0.16),
        Paragraph(_texto(POTENCIAL_MARCO_LECTURA), ParagraphStyle(
            "pot_desc_body", fontName="Helvetica", fontSize=9.55,
            textColor=INK2, leading=13.8, alignment=TA_JUSTIFY,
        )),
    ]
    return _card_table(content, ancho, bg="#fbfaff", border="#ded8fb", pad=15, radius=12)


def _card_potencial_puntuacion(cap, cap_info, ancho):
    cap_percent = cap.get("percent")
    cap_name = _texto(cap_info.get("name"), "Sin dato")
    color_hex = _cap_color_hex(cap_name)
    left = [
        Paragraph("Puntuación general", ParagraphStyle(
            "pot_score_title", fontName="Helvetica-Bold", fontSize=10.8,
            textColor=INK, leading=13,
        )),
        spacer(0.08),
        Paragraph(cap_name.upper(), ParagraphStyle(
            "pot_score_label", fontName="Helvetica-Bold", fontSize=7.4,
            textColor=colors.HexColor(color_hex), leading=9,
        )),
        spacer(0.14),
        Paragraph(
            f"<b>{cap_name}.</b> {_texto(cap_info.get('interpretation'))}",
            ParagraphStyle(
                "pot_score_body", fontName="Helvetica", fontSize=9.45,
                textColor=INK2, leading=13.2, alignment=TA_LEFT,
            ),
        ),
    ]
    score_panel = RoundedBox(
        Table([[crear_donut_360(cap_percent or 0, color_hex, ancho_cm=3.25, alto_cm=3.25)]], colWidths=[3.55*cm]),
        3.78*cm,
        fill=colors.white,
        stroke=colors.HexColor("#eeeafb"),
        radius=14,
        pad=6,
        stroke_width=0.5,
    )
    row = Table([[left, score_panel]], colWidths=[ancho - 5.25*cm, 3.78*cm])
    row.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("LEFTPADDING", (0,0), (-1,-1), 0),
        ("RIGHTPADDING", (0,0), (-1,-1), 0),
        ("RIGHTPADDING", (0,0), (0,0), 14),
        ("TOPPADDING", (0,0), (-1,-1), 0),
        ("BOTTOMPADDING", (0,0), (-1,-1), 0),
        ("ALIGN", (1,0), (1,0), "CENTER"),
    ]))
    return _card_table([row], ancho, bg="#ffffff", border="#ded8fb", pad=15, radius=12)


def _header_360(nombre, subtitulo, ancho, empresa=""):
    avatar = Drawing(0.86*cm, 0.86*cm)
    avatar.add(Rect(0, 0, 0.86*cm, 0.86*cm, rx=0.43*cm, ry=0.43*cm, fillColor=colors.HexColor("#fff0f8"), strokeColor=None))
    initials = "".join(part[:1] for part in _texto(nombre, "R").split()[:2]).upper() or "R"
    avatar.add(String(0.43*cm, 0.29*cm, initials, fontName="Helvetica-Bold", fontSize=7.0, textAnchor="middle", fillColor=colors.HexColor("#ff4298")))
    badge = _pill_flow("EVALUACI\u00d3N DESEMPE\u00d1O", "#ff7a00", "#fff4e8", width_cm=4.2, font_size=7.0)
    row = Table([[avatar, Spacer(1, 1), badge, Spacer(1, 1)]], colWidths=[1.15*cm, ancho - 6.1*cm, 4.35*cm, 0.60*cm])
    row.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("ALIGN", (2,0), (2,0), "RIGHT"),
        ("LEFTPADDING", (0,0), (-1,-1), 0),
        ("RIGHTPADDING", (0,0), (-1,-1), 0),
        ("TOPPADDING", (0,0), (-1,-1), 0),
        ("BOTTOMPADDING", (0,0), (-1,-1), 0),
    ]))
    return RoundedBox(row, ancho, fill=colors.HexColor("#151326"), stroke=colors.HexColor("#151326"), radius=12, pad=13, stroke_width=0)


def _header_resultado(nombre, subtitulo, badge, ancho, accent="#ff4298", empresa="", jefe=""):
    avatar = Drawing(0.86*cm, 0.86*cm)
    avatar.add(Rect(0, 0, 0.86*cm, 0.86*cm, rx=0.43*cm, ry=0.43*cm, fillColor=colors.HexColor("#fff0f8"), strokeColor=None))
    initials = "".join(part[:1] for part in _texto(nombre, "R").split()[:2]).upper() or "R"
    avatar.add(String(0.43*cm, 0.29*cm, initials, fontName="Helvetica-Bold", fontSize=7.0, textAnchor="middle", fillColor=colors.HexColor(accent)))
    text = [
        Paragraph(_texto(nombre), ParagraphStyle(
            "header_result_name", fontName="Helvetica-Bold", fontSize=12.2,
            textColor=WHITE, leading=15,
        )),
        Paragraph(_texto(subtitulo, "General"), ParagraphStyle(
            "header_result_sub", fontName="Helvetica", fontSize=9.2,
            textColor=colors.HexColor("#c9c5df"), leading=11,
        )),
    ]
    if empresa:
        text.append(Paragraph(_texto(empresa), ParagraphStyle(
            "header_result_empresa", fontName="Helvetica", fontSize=8.2,
            textColor=colors.HexColor("#a9a3c4"), leading=10,
        )))
    if jefe:
        text.append(Paragraph(f"Jefe: {_texto(jefe)}", ParagraphStyle(
            "header_result_jefe", fontName="Helvetica", fontSize=7.8,
            textColor=colors.HexColor("#a9a3c4"), leading=9.2,
        )))
    badge_flow = _pill_flow(_texto(badge).upper(), "#ff7a00", "#fff4e8", width_cm=3.25, font_size=7.2)
    row = Table([[avatar, text, badge_flow]], colWidths=[1.15*cm, ancho - 5.1*cm, 3.45*cm])
    row.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("LEFTPADDING", (0,0), (-1,-1), 0),
        ("RIGHTPADDING", (0,0), (-1,-1), 0),
        ("TOPPADDING", (0,0), (-1,-1), 0),
        ("BOTTOMPADDING", (0,0), (-1,-1), 0),
    ]))
    return RoundedBox(row, ancho, fill=colors.HexColor("#151326"), stroke=colors.HexColor("#151326"), radius=12, pad=13, stroke_width=0)


def _header_evaluacion_simple(nombre, titulo, ancho, accent="#ff4298"):
    avatar = Drawing(0.86*cm, 0.86*cm)
    avatar.add(Rect(0, 0, 0.86*cm, 0.86*cm, rx=0.43*cm, ry=0.43*cm, fillColor=colors.HexColor("#fff0f8"), strokeColor=None))
    initials = "".join(part[:1] for part in _texto(nombre, "R").split()[:2]).upper() or "R"
    avatar.add(String(0.43*cm, 0.29*cm, initials, fontName="Helvetica-Bold", fontSize=7.0, textAnchor="middle", fillColor=colors.HexColor(accent)))
    badge = _pill_flow(_texto(titulo).upper(), "#ff7a00", "#fff4e8", width_cm=4.55, font_size=6.9)
    row = Table([[avatar, Spacer(1, 1), badge, Spacer(1, 1)]], colWidths=[1.15*cm, ancho - 6.45*cm, 4.70*cm, 0.60*cm])
    row.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("ALIGN", (2,0), (2,0), "RIGHT"),
        ("LEFTPADDING", (0,0), (-1,-1), 0),
        ("RIGHTPADDING", (0,0), (-1,-1), 0),
        ("TOPPADDING", (0,0), (-1,-1), 0),
        ("BOTTOMPADDING", (0,0), (-1,-1), 0),
    ]))
    return RoundedBox(row, ancho, fill=colors.HexColor("#151326"), stroke=colors.HexColor("#151326"), radius=12, pad=13, stroke_width=0)


def _context_chip(label, value, width_cm):
    content = [
        Paragraph(label.upper(), ParagraphStyle(
            "obj_ctx_l", fontName="Helvetica-Bold", fontSize=6.4,
            textColor=INK_SOFT, leading=7.8,
        )),
        Paragraph(_texto(value), ParagraphStyle(
            "obj_ctx_v", fontName="Helvetica-Bold", fontSize=8.1,
            textColor=INK, leading=9.8,
        )),
    ]
    t = Table([[content]], colWidths=[width_cm*cm])
    t.setStyle(TableStyle([
        ("LEFTPADDING", (0,0), (-1,-1), 8),
        ("RIGHTPADDING", (0,0), (-1,-1), 8),
        ("TOPPADDING", (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
    ]))
    return RoundedBox(t, width_cm*cm, fill=colors.HexColor("#fbfaff"), stroke=colors.HexColor("#ded8fb"), radius=8, pad=0, stroke_width=0.5)


def _logo_flow(path, width_cm, max_height_cm):
    if not path.exists():
        return Spacer(1, max_height_cm * cm)
    try:
        img = ImageReader(str(path))
        iw, ih = img.getSize()
        width = width_cm * cm
        height = width * (ih / iw)
        max_height = max_height_cm * cm
        if height > max_height:
            height = max_height
            width = height * (iw / ih)
        return Image(str(path), width=width, height=height)
    except Exception:
        return Spacer(1, max_height_cm * cm)


def _compact_data_chip(label, value, width_cm):
    content = [
        Paragraph(label.upper(), ParagraphStyle(
            "coverless_chip_l", fontName="Helvetica-Bold", fontSize=6.8,
            textColor=INK_SOFT, leading=8,
        )),
        Paragraph(_texto(value), ParagraphStyle(
            "coverless_chip_v", fontName="Helvetica-Bold", fontSize=7.4,
            textColor=INK, leading=8.6,
        )),
    ]
    t = Table([[content]], colWidths=[width_cm*cm])
    t.setStyle(TableStyle([
        ("LEFTPADDING", (0,0), (-1,-1), 8),
        ("RIGHTPADDING", (0,0), (-1,-1), 8),
        ("TOPPADDING", (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
    ]))
    return RoundedBox(t, width_cm*cm, fill=colors.HexColor("#fbfaff"), stroke=colors.HexColor("#ded8fb"), radius=7, pad=0, stroke_width=0.45)


def _primera_hoja_intro(nombre, cargo, empresa, jefe, ancho, badge="Evaluación de Competencias"):
    logo_row = Table(
        [[
            _logo_flow(SPEEDSTER_LOGO, 5.20, 1.60),
            _logo_flow(LOGO_HEADER, 3.65, 0.85),
        ]],
        colWidths=[ancho/2, ancho/2],
    )
    logo_row.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("ALIGN", (0,0), (0,0), "LEFT"),
        ("ALIGN", (1,0), (1,0), "RIGHT"),
        ("LEFTPADDING", (0,0), (-1,-1), 0),
        ("RIGHTPADDING", (0,0), (-1,-1), 0),
        ("TOPPADDING", (0,0), (-1,-1), 0),
        ("BOTTOMPADDING", (0,0), (-1,-1), 0),
    ]))

    return [
        logo_row,
        spacer(0.18),
        _header_resultado(nombre, cargo, badge, ancho, accent="#ff4298", empresa=empresa, jefe=jefe),
        spacer(0.45),
    ]


def _card_objetivos_descripcion(ancho):
    cfg = _objetivos_config()
    content = [
        Paragraph("MARCO DE LECTURA", ParagraphStyle(
            "obj_desc_eye", fontName="Helvetica-Bold", fontSize=7.2,
            textColor=MAGENTA, leading=9,
        )),
        spacer(0.06),
        Paragraph("Descripci\u00f3n de la evaluaci\u00f3n", ParagraphStyle(
            "obj_desc_title", fontName="Helvetica-Bold", fontSize=10.5,
            textColor=INK, leading=12.5,
        )),
        spacer(0.16),
        Paragraph(_texto(cfg.get("description_text")), ParagraphStyle(
            "obj_desc_body", fontName="Helvetica", fontSize=10.0,
            textColor=INK2, leading=14.4, alignment=TA_JUSTIFY,
        )),
    ]
    return _card_table(content, ancho, bg="#fbfaff", border="#ded8fb", pad=15, radius=12)


def _card_objetivos_puntuacion(objetivos, ancho):
    puntaje = objetivos.get("puntaje")
    info = _interpretacion_objetivos(puntaje)
    color_hex = _color_puntaje_360(puntaje or 0)
    left = [
        Paragraph("Puntuaci\u00f3n general", ParagraphStyle(
            "obj_score_title", fontName="Helvetica-Bold", fontSize=10.8,
            textColor=INK, leading=13,
        )),
        spacer(0.08),
        Paragraph(_texto(info.get("label")).upper(), ParagraphStyle(
            "obj_score_label", fontName="Helvetica-Bold", fontSize=7.4,
            textColor=colors.HexColor(color_hex), leading=9,
        )),
        spacer(0.14),
        Paragraph(f"<b>{_texto(info.get('title'))}.</b> {_texto(info.get('interpretation'))}", ParagraphStyle(
            "obj_score_body", fontName="Helvetica", fontSize=9.45,
            textColor=INK2, leading=13.2, alignment=TA_LEFT,
        )),
    ]
    score_panel = RoundedBox(
        Table([[crear_donut_360(puntaje or 0, color_hex, ancho_cm=3.25, alto_cm=3.25)]], colWidths=[3.55*cm]),
        3.78*cm,
        fill=colors.white,
        stroke=colors.HexColor("#eeeafb"),
        radius=14,
        pad=6,
        stroke_width=0.5,
    )
    row = Table([[left, score_panel]], colWidths=[ancho - 5.25*cm, 3.78*cm])
    row.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("LEFTPADDING", (0,0), (-1,-1), 0),
        ("RIGHTPADDING", (0,0), (-1,-1), 0),
        ("RIGHTPADDING", (0,0), (0,0), 14),
        ("TOPPADDING", (0,0), (-1,-1), 0),
        ("BOTTOMPADDING", (0,0), (-1,-1), 0),
        ("ALIGN", (1,0), (1,0), "CENTER"),
    ]))
    return _card_table([row], ancho, bg="#ffffff", border="#ded8fb", pad=15, radius=12)


def _objetivos_section_flow(nombre, ficha, objetivos, objetivos_detalle, ancho, incluir_header=True):
    cargo = ficha.get("cargo") or objetivos.get("cargo_objetivo") or "Objetivos"
    empresa = ficha.get("empresa") or ""
    jefe = ficha.get("jefe") or objetivos.get("jefe") or ""
    flow = []
    if incluir_header:
        flow += [
            _header_evaluacion_simple(nombre, "Evaluación de Objetivos", ancho, accent="#ff4298"),
            spacer(0.34),
        ]
    flow += [
        _card_objetivos_descripcion(ancho),
        spacer(0.34),
        _card_objetivos_puntuacion(objetivos, ancho),
        spacer(0.34),
        Paragraph("Objetivos evaluados", ParagraphStyle(
            "obj_detail_title", fontName="Helvetica-Bold", fontSize=11.4,
            textColor=INK, leading=14,
        )),
        spacer(0.16),
        _tabla_objetivos_detalle(objetivos_detalle, ancho),
    ]
    return flow


def _tabla_objetivos_detalle(items, ancho):
    if not items:
        return Paragraph("No hay detalle de objetivos disponible para este colaborador.", ParagraphStyle(
            "obj_empty", fontName="Helvetica", fontSize=8.5, textColor=INK_SOFT, leading=11,
        ))
    th = ParagraphStyle(
        "obj_tbl_th", fontName="Helvetica-Bold", fontSize=7.2,
        textColor=INK_SOFT, leading=9,
    )
    td = ParagraphStyle(
        "obj_tbl_td", fontName="Helvetica", fontSize=7.6,
        textColor=INK2, leading=9.6,
    )
    data = [[Paragraph("Objetivo", th), Paragraph("Resultado", th)]]
    for item in items:
        data.append([
            Paragraph(_texto(item.get("objetivo")), td),
            _score_chip_360(item.get("puntaje"), font_size=7.0, width_cm=1.25, compact=True),
        ])
    table = Table(data, colWidths=[ancho - 2.2*cm, 2.2*cm], repeatRows=1)
    style = [
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#fbfaff")),
        ("BOX", (0,0), (-1,-1), 0.45, colors.HexColor("#ded8fb")),
        ("INNERGRID", (0,0), (-1,-1), 0.25, colors.HexColor("#ebe8f8")),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("LEFTPADDING", (0,0), (-1,-1), 8),
        ("RIGHTPADDING", (0,0), (-1,-1), 8),
        ("TOPPADDING", (0,0), (-1,0), 6),
        ("BOTTOMPADDING", (0,0), (-1,0), 6),
        ("TOPPADDING", (0,1), (-1,-1), 5),
        ("BOTTOMPADDING", (0,1), (-1,-1), 5),
        ("ALIGN", (1,1), (1,-1), "CENTER"),
    ]
    for i in range(1, len(data)):
        if i % 2 == 0:
            style.append(("BACKGROUND", (0,i), (-1,i), colors.HexColor("#fdfcff")))
    table.setStyle(TableStyle(style))
    return table


def _tabla_resumen_potencial(potencial, ancho, estilos):
    filas = [
        ["Evaluaci\u00f3n de potencial", _valor_num(potencial.get("evaluacion_potencial"))],
        ["Potencial 2025", _valor_num(potencial.get("potencial_2025"))],
        ["Escala benchmark", _texto(potencial.get("escala_benchmark"))],
        ["Escala potencial", _texto(potencial.get("escala_potencial"))],
        ["DISC", _texto(potencial.get("disc"))],
        ["IQ", _texto(potencial.get("iq"))],
    ]
    data = []
    for idx in range(0, len(filas), 2):
        k1, v1 = filas[idx]
        k2, v2 = filas[idx + 1]
        data.append([
            Paragraph(k1.upper(), estilos["th"]),
            Paragraph(v1, estilos["td_comp"]),
            Paragraph(k2.upper(), estilos["th"]),
            Paragraph(v2, estilos["td_comp"]),
        ])
    t = Table(data, colWidths=[ancho*.22, ancho*.28, ancho*.22, ancho*.28])
    t.setStyle(TableStyle([
        ("TOPPADDING", (0,0), (-1,-1), 8),
        ("BOTTOMPADDING", (0,0), (-1,-1), 8),
        ("LINEBELOW", (0,0), (-1,-1), 0.4, LINE),
        ("LEFTPADDING", (0,0), (-1,-1), 0),
        ("RIGHTPADDING", (0,0), (-1,-1), 6),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
    ]))
    return t


def _tabla_ficha_integral(ficha, ancho, estilos):
    filas = [
        ["Empresa", _texto(ficha.get("empresa")), "Pais", _texto(ficha.get("pais"))],
        ["Cargo", _texto(ficha.get("cargo")), "Area", _texto(ficha.get("area"))],
        ["Jefe", _texto(ficha.get("jefe")), "Grupo", _texto(ficha.get("grupo"))],
    ]
    data = []
    for k1, v1, k2, v2 in filas:
        data.append([
            Paragraph(k1.upper(), estilos["th"]),
            Paragraph(v1, estilos["td"]),
            Paragraph(k2.upper(), estilos["th"]),
            Paragraph(v2, estilos["td"]),
        ])
    t = Table(data, colWidths=[ancho*.16, ancho*.34, ancho*.16, ancho*.34])
    t.setStyle(TableStyle([
        ("TOPPADDING", (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("LINEBELOW", (0,0), (-1,-1), 0.4, LINE),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("LEFTPADDING", (0,0), (-1,-1), 0),
        ("RIGHTPADDING", (0,0), (-1,-1), 6),
    ]))
    return t


def _tabla_indicadores_integrales(contexto, ancho, estilos):
    integrado = contexto.get("integrado", {}) or {}
    objetivos = contexto.get("objetivos", {}) or {}
    potencial = contexto.get("potencial", {}) or {}
    ninebox = contexto.get("ninebox", {}) or {}
    filas = [
        ["Indicador", "Puntaje", "Lectura"],
        ["Resultado integrado", _valor_num(integrado.get("integrada"), 0), _texto(integrado.get("escala_integrada"))],
        ["Desempe\u00f1o 360", _valor_num(integrado.get("evd_360")), "Evaluaci\u00f3n multifuente"],
        ["Objetivos", _valor_num(objetivos.get("puntaje")), f"{_texto(objetivos.get('objetivos'))} objetivos"],
        ["Potencial", _valor_num(potencial.get("evaluacion_potencial")), _texto(potencial.get("escala_potencial"))],
        ["Ninebox", _texto(ninebox.get("cuadrante")), _texto(ninebox.get("cuadrante_nombre"))],
    ]
    data = []
    for i, fila in enumerate(filas):
        row = []
        for c in fila:
            if isinstance(c, Flowable):
                row.append(c)
            else:
                row.append(Paragraph(str(c), estilos["th"] if i == 0 else estilos["td"]))
        data.append(row)
    t = Table(data, colWidths=[ancho*.42, ancho*.18, ancho*.40], repeatRows=1)
    t.setStyle(TableStyle([
        ("TOPPADDING", (0,0), (-1,0), 7),
        ("BOTTOMPADDING", (0,0), (-1,0), 5),
        ("LINEBELOW", (0,0), (-1,0), 0.8, LINE_STR),
        ("TOPPADDING", (0,1), (-1,-1), 8),
        ("BOTTOMPADDING", (0,1), (-1,-1), 8),
        ("LINEBELOW", (0,1), (-1,-1), 0.4, LINE),
        ("LEFTPADDING", (0,0), (-1,-1), 0),
        ("RIGHTPADDING", (0,0), (-1,-1), 6),
        ("ALIGN", (1,1), (1,-1), "RIGHT"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
    ]))
    return t


def _tabla_potencial_competencias(items, ancho, estilos):
    catalogo = _catalogo_potencial()
    filas = [["Competencia", "Valor", "Esperado", "Brecha", "Lectura"]]
    for item in items[:8]:
        comp = _texto(item.get("competencia"))
        meta = catalogo.get(comp, {})
        ajuste = item.get("ajuste")
        lectura = "Ajustada" if _valor_num(ajuste, 0) == "0" else "Oportunidad"
        if meta.get("ajuste_promedio") is not None:
            lectura = f"{lectura} / prom. {meta['ajuste_promedio']:.1f}"
        filas.append([
            comp,
            _valor_num(item.get("valor"), 0),
            _valor_num(item.get("esperado"), 0),
            _valor_num(item.get("brecha"), 0),
            lectura,
        ])
    data = []
    for i, fila in enumerate(filas):
        row = []
        for c in fila:
            if isinstance(c, Flowable):
                row.append(c)
            else:
                row.append(Paragraph(str(c), estilos["th"] if i == 0 else estilos["td"]))
        data.append(row)
    t = Table(data, colWidths=[ancho*.40, ancho*.11, ancho*.13, ancho*.12, ancho*.24], repeatRows=1)
    t.setStyle(TableStyle([
        ("TOPPADDING", (0,0), (-1,0), 7),
        ("BOTTOMPADDING", (0,0), (-1,0), 5),
        ("LINEBELOW", (0,0), (-1,0), 0.8, LINE_STR),
        ("TOPPADDING", (0,1), (-1,-1), 7),
        ("BOTTOMPADDING", (0,1), (-1,-1), 7),
        ("LINEBELOW", (0,1), (-1,-1), 0.4, LINE),
        ("LEFTPADDING", (0,0), (-1,-1), 0),
        ("RIGHTPADDING", (0,0), (-1,-1), 4),
        ("ALIGN", (1,1), (-1,-1), "RIGHT"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
    ]))
    return t


def _tabla_cap_competencias(items, ancho, estilos, limite=12):
    filas = [["Competencia", "Esperado", "Obtenido", "Brecha", "Ajuste"]]
    datos = items[:limite]
    for item in datos:
        ajuste = item.get("ajuste")
        try:
            ajuste_val = float(ajuste)
            ajuste_txt = f"{ajuste_val * 100:.0f}%"
            ajuste_name = _cap_interpretacion(ajuste_val).get("name")
            ajuste_cell = Paragraph(
                ajuste_txt,
                ParagraphStyle(
                    "ajuste_chip",
                    fontName="Helvetica-Bold",
                    fontSize=8.5,
                    textColor=_cap_color(ajuste_name),
                    leading=11,
                    alignment=TA_CENTER,
                ),
            )
        except Exception:
            ajuste_val = 0
            ajuste_cell = Paragraph("-", estilos["td"])
        filas.append([
            _texto(item.get("competencia")),
            _valor_num(item.get("esperado"), 1),
            _valor_num(item.get("valor"), 1),
            _valor_num(item.get("brecha"), 1),
            ajuste_cell,
        ])
    data = []
    for i, fila in enumerate(filas):
        row = []
        for c in fila:
            if isinstance(c, Flowable):
                row.append(c)
            else:
                row.append(Paragraph(str(c), estilos["th"] if i == 0 else estilos["td"]))
        data.append(row)
    table = Table(data, colWidths=[ancho*.44, ancho*.14, ancho*.15, ancho*.13, ancho*.14], repeatRows=1)
    style = [
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#f1f6ff")),
        ("TEXTCOLOR", (0,0), (-1,0), INK),
        ("TOPPADDING", (0,0), (-1,0), 7),
        ("BOTTOMPADDING", (0,0), (-1,0), 7),
        ("TOPPADDING", (0,1), (-1,-1), 6),
        ("BOTTOMPADDING", (0,1), (-1,-1), 6),
        ("LINEBELOW", (0,0), (-1,-1), 0.35, LINE),
        ("LEFTPADDING", (0,0), (-1,-1), 6),
        ("RIGHTPADDING", (0,0), (-1,-1), 6),
        ("ALIGN", (1,1), (-1,-1), "RIGHT"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
    ]
    for row_idx, item in enumerate(datos, start=1):
        try:
            ajuste_val = float(item.get("ajuste"))
        except Exception:
            ajuste_val = 0
        name = _cap_interpretacion(ajuste_val).get("name")
        color = _cap_color(name)
        bg = _cap_bg_color(name)
        style.append(("TEXTCOLOR", (4,row_idx), (4,row_idx), color))
        style.append(("BACKGROUND", (4,row_idx), (4,row_idx), bg))
        style.append(("FONTNAME", (4,row_idx), (4,row_idx), "Helvetica-Bold"))
    table.setStyle(TableStyle(style))
    return table


def _semaforo_cap(ancho, estilos):
    cards = []
    for item in _cap_config().get("ranges", []):
        start = float(item.get("from", 0))
        end = float(item.get("to", 0))
        if end > 1:
            start_pct = start * 100 if start <= 1 else start
            end_pct = min(end, 101)
            end_visible = 100 if end_pct >= 101 else end_pct - 0.01
            rango = f"{start_pct:.0f} a {end_visible:.2f}%".replace(".", ",")
        else:
            end_visible = 100 if end >= 1.01 else end * 100 - 0.01
            rango = f"{start * 100:.0f} a {end_visible:.2f}%".replace(".", ",")
        name = item["name"]
        color = _cap_color(name)
        bg = _cap_bg_color(name)
        inner = Table(
            [[[
                Paragraph(rango, ParagraphStyle(
                    "sem_r", fontName="Helvetica-Bold", fontSize=8,
                    textColor=INK_SOFT, leading=10,
                )),
                Paragraph(name, ParagraphStyle(
                    "sem_n", fontName="Helvetica-Bold", fontSize=9.2,
                    textColor=color, leading=12,
                )),
            ]]],
            colWidths=[ancho],
        )
        inner.setStyle(TableStyle([
            ("TOPPADDING", (0,0), (-1,-1), 7),
            ("BOTTOMPADDING", (0,0), (-1,-1), 7),
            ("LEFTPADDING", (0,0), (-1,-1), 10),
            ("RIGHTPADDING", (0,0), (-1,-1), 10),
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ]))
        cards.append(RoundedBox(inner, ancho, fill=bg, stroke=bg, radius=9, pad=0, stroke_width=0))
        cards.append(Spacer(1, 0.14*cm))
    return Table([[cards]], colWidths=[ancho])


def crear_grafico_disc(d, i, s, c, size_cm=8.0):
    valores = {
        "D": 0 if d is None or (isinstance(d, float) and math.isnan(d)) else float(d),
        "I": 0 if i is None or (isinstance(i, float) and math.isnan(i)) else float(i),
        "S": 0 if s is None or (isinstance(s, float) and math.isnan(s)) else float(s),
        "C": 0 if c is None or (isinstance(c, float) and math.isnan(c)) else float(c),
    }
    colores = {
        "D": "#ef2d24",
        "I": "#f6ca11",
        "S": "#59b844",
        "C": "#0068b7",
    }
    theta = {
        "I": math.pi / 4,
        "D": 3 * math.pi / 4,
        "C": 5 * math.pi / 4,
        "S": 7 * math.pi / 4,
    }

    fig_w_cm = size_cm + 2.2
    fig, ax = plt.subplots(figsize=(fig_w_cm/2.54, size_cm/2.54), subplot_kw=dict(polar=True))
    fig.patch.set_facecolor("#ffffff")
    ax.set_facecolor("#ffffff")
    ax.set_theta_zero_location("E")
    ax.set_theta_direction(1)
    ax.set_ylim(0, 10)
    ax.set_yticks(range(1, 11))
    ax.set_yticklabels([str(v) for v in range(1, 11)], fontsize=5.5, color="#b8b4cc")
    ax.set_xticks([])
    ax.grid(color="#e6e3ef", linewidth=0.6)
    ax.spines["polar"].set_color("#e6e3ef")
    ax.spines["polar"].set_linewidth(0.8)

    for key in ["I", "D", "C", "S"]:
        ax.bar(
            theta[key],
            max(0, min(10, valores[key])),
            width=math.pi / 2,
            bottom=0,
            color=colores[key],
            edgecolor="#ffffff",
            linewidth=1.2,
            align="center",
            alpha=0.98,
        )
    for angle in [0, math.pi / 2, math.pi, 3 * math.pi / 2]:
        ax.plot([angle, angle], [0, 10], color="#ffffff", linewidth=1.2, zorder=5)

    handles = [
        mpatches.Patch(color=colores["D"], label="Dominante"),
        mpatches.Patch(color=colores["I"], label="Influyente"),
        mpatches.Patch(color=colores["S"], label="Servicial"),
        mpatches.Patch(color=colores["C"], label="Cumplido"),
    ]
    leg = ax.legend(
        handles=handles,
        loc="upper center",
        bbox_to_anchor=(0.5, 1.12),
        ncol=4,
        frameon=False,
        fontsize=6.2,
        handlelength=1.8,
        columnspacing=0.7,
    )
    for text in leg.get_texts():
        text.set_color("#8b86a8")

    fig.subplots_adjust(top=0.82, bottom=0.08, left=0.07, right=0.93)
    buf = io.BytesIO()
    plt.savefig(
        buf,
        format="jpg",
        dpi=135,
        facecolor="#ffffff",
        pil_kwargs={"quality": 82, "optimize": True},
    )
    plt.close(fig)
    buf.seek(0)
    return Image(buf, width=fig_w_cm*cm, height=size_cm*cm)


def _disc_score_pills(potencial, ancho, estilos):
    colores = [
        ("D", "#ef2d24", potencial.get("d")),
        ("I", "#f6ca11", potencial.get("i")),
        ("S", "#59b844", potencial.get("s")),
        ("C", "#0068b7", potencial.get("c")),
    ]
    cells = []
    for label, color_hex, value in colores:
        color = colors.HexColor(color_hex)
        cells.append(_metric_chip(label, _valor_num(value, 0), color, "#ffffff"))
    t = Table([cells], colWidths=[ancho/4]*4)
    t.setStyle(TableStyle([
        ("LEFTPADDING", (0,0), (-1,-1), 0),
        ("RIGHTPADDING", (0,0), (-1,-1), 6),
        ("TOPPADDING", (0,0), (-1,-1), 0),
        ("BOTTOMPADDING", (0,0), (-1,-1), 0),
    ]))
    return t


def _disc_bullet_flow(items, style, max_items=5):
    flow = []
    for item in (items or [])[:max_items]:
        flow.append(Paragraph(f"- {_texto(item, '')}", style))
        flow.append(Spacer(1, 0.035*cm))
    return flow or [Paragraph("- Sin informacion disponible.", style)]


def _disc_two_col_block(left_title, left_items, right_title, right_items, ancho):
    title_left = ParagraphStyle(
        "disc_insight_title_l", fontName="Helvetica-Bold", fontSize=10.2,
        textColor=colors.HexColor("#20c477"), leading=12.0,
    )
    title_right = ParagraphStyle(
        "disc_insight_title_r", fontName="Helvetica-Bold", fontSize=10.2,
        textColor=colors.HexColor("#ef2d24"), leading=12.0,
    )
    bullet = ParagraphStyle(
        "disc_insight_bullet", fontName="Helvetica", fontSize=7.8,
        textColor=INK_SOFT, leading=10.2, leftIndent=7, firstLineIndent=-5,
    )
    col_w = (ancho - 0.45*cm) / 2
    t = Table(
        [[
            [Paragraph(left_title, title_left), *_disc_bullet_flow(left_items, bullet)],
            [Paragraph(right_title, title_right), *_disc_bullet_flow(right_items, bullet)],
        ]],
        colWidths=[col_w, col_w],
    )
    t.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 0),
        ("RIGHTPADDING", (0,0), (-1,-1), 10),
        ("TOPPADDING", (0,0), (-1,-1), 0),
        ("BOTTOMPADDING", (0,0), (-1,-1), 0),
    ]))
    return t


def _disc_motivadores_block(motivators, demotivators, ancho):
    title_m = ParagraphStyle(
        "disc_motiv_title", fontName="Helvetica-Bold", fontSize=9.8,
        textColor=colors.HexColor("#5ff0a6"), leading=11.4,
    )
    title_d = ParagraphStyle(
        "disc_demotiv_title", fontName="Helvetica-Bold", fontSize=9.8,
        textColor=colors.HexColor("#ffc94a"), leading=11.4,
    )
    bullet = ParagraphStyle(
        "disc_motiv_bullet", fontName="Helvetica-Bold", fontSize=7.45,
        textColor=colors.white, leading=9.7, leftIndent=7, firstLineIndent=-5,
    )
    col_w = (ancho - 1.0*cm) / 2
    inner = Table(
        [[
            [Paragraph("Motivadores:", title_m), *_disc_bullet_flow(motivators, bullet)],
            [Paragraph("Desmotivadores:", title_d), *_disc_bullet_flow(demotivators, bullet)],
        ]],
        colWidths=[col_w, col_w],
    )
    inner.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 0),
        ("RIGHTPADDING", (0,0), (-1,-1), 16),
        ("TOPPADDING", (0,0), (-1,-1), 0),
        ("BOTTOMPADDING", (0,0), (-1,-1), 0),
    ]))
    return RoundedBox(
        inner,
        ancho,
        fill=colors.HexColor("#7c67d8"),
        stroke=colors.HexColor("#7c67d8"),
        radius=13,
        pad=15,
        stroke_width=0,
    )


def _disc_section_flow(contexto, ancho, estilos):
    potencial = contexto.get("potencial", {}) or {}
    item = _disc_arquetipo_item(potencial)
    arquetipo = _texto(potencial.get("disc") or item.get("archetype"), "Sin dato")
    nombre = _texto(item.get("name"), arquetipo)
    codigo = _texto(potencial.get("arquetipo") or item.get("code"), "")
    descripcion = _texto(item.get("personality"), "No hay una descripci\u00f3n DISC configurada para este arquetipo.")

    title_row = []
    if LOGO_DISC.exists():
        title_row.append(Image(str(LOGO_DISC), width=0.62*cm, height=0.62*cm))
    else:
        title_row.append(Paragraph("DISC", estilos["th"]))
    title_row.append(Paragraph("DISC PROFESSIONAL PROFILE", ParagraphStyle(
        "disc_title", fontName="Helvetica-Bold", fontSize=15.5,
        textColor=colors.HexColor("#5b36d6"), leading=19,
    )))
    header = Table([title_row], colWidths=[0.82*cm, ancho - 0.82*cm])
    header.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("LEFTPADDING", (0,0), (-1,-1), 0),
        ("RIGHTPADDING", (0,0), (-1,-1), 0),
        ("TOPPADDING", (0,0), (-1,-1), 0),
        ("BOTTOMPADDING", (0,0), (-1,-1), 0),
    ]))

    arq_badge_text = f"{nombre} ({codigo})" if codigo else arquetipo
    arq_badge = RoundedBox(
        Table([[Paragraph(arq_badge_text, ParagraphStyle(
            "disc_badge", fontName="Helvetica-Bold", fontSize=10,
            textColor=colors.HexColor("#5b36d6"), leading=12, alignment=TA_CENTER,
        ))]], colWidths=[5.2*cm]),
        5.2*cm,
        fill=colors.HexColor("#fff8dc"),
        stroke=colors.HexColor("#f6ca11"),
        radius=12,
        pad=0,
        stroke_width=0.6,
    )

    info = [
        arq_badge,
        spacer(0.18),
        Paragraph(descripcion, ParagraphStyle(
            "disc_body", fontName="Helvetica", fontSize=9.2,
            textColor=INK_SOFT, leading=12.8, alignment=TA_JUSTIFY,
        )),
    ]
    chart = crear_grafico_disc(
        potencial.get("d"),
        potencial.get("i"),
        potencial.get("s"),
        potencial.get("c"),
        size_cm=7.2,
    )
    chart_table = Table([[chart]], colWidths=[ancho])
    chart_table.setStyle(TableStyle([
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("LEFTPADDING", (0,0), (-1,-1), 0),
        ("RIGHTPADDING", (0,0), (-1,-1), 0),
        ("TOPPADDING", (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 0),
    ]))
    return [
        header,
        spacer(0.31),
        *info,
        spacer(0.22),
        chart_table,
        spacer(0.38),
        _disc_two_col_block(
            "Fortalezas:",
            item.get("strengths", []),
            "\u00c1reas de mejora:",
            item.get("weaknesses", []),
            ancho,
        ),
        spacer(0.42),
        _disc_motivadores_block(
            item.get("motivators", []),
            item.get("demotivators", []),
            ancho,
        ),
    ]


def _tiene_numero_real(valor):
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return False
    return math.isfinite(numero) and numero > 0


def _tiene_texto_real(valor):
    texto = _texto(valor, "").strip()
    return bool(texto) and texto.casefold() not in {"sin dato", "nan", "none", "null", "-"}


def _primer_texto_real(*valores, default=""):
    for valor in valores:
        if _tiene_texto_real(valor):
            return _texto(valor)
    return default


def _tiene_potencial(contexto):
    if not contexto:
        return False
    competencias = contexto.get("competencias_potencial", []) or []
    cap = contexto.get("cap", {}) or {}
    return bool(competencias) or _tiene_numero_real(cap.get("percent"))


def _tiene_disc(contexto):
    if not contexto:
        return False
    potencial = contexto.get("potencial", {}) or {}
    if not potencial:
        return False
    if _tiene_texto_real(potencial.get("disc")) or _tiene_texto_real(potencial.get("arquetipo")):
        return True
    return any(_tiene_numero_real(potencial.get(col)) for col in ("d", "i", "s", "c"))


def _tiene_desempeno_360(resultado):
    if not resultado:
        return False
    return _tiene_numero_real(resultado.get("puntaje_global")) and bool(resultado.get("competencias"))


def _tiene_objetivos(contexto):
    if not contexto:
        return False
    objetivos = contexto.get("objetivos", {}) or {}
    detalle = contexto.get("objetivos_detalle", []) or []
    return _tiene_numero_real(objetivos.get("puntaje")) or bool(detalle)

# ---------------------------------------------------------------------------
# FunciÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â³n principal
# ---------------------------------------------------------------------------

def generar_pdf(nombre, resultado, proceso, cliente, fecha,
                cargo="", area="", ruta_salida="informe.pdf",
                contexto_integral=None):

    global TOTAL_PAGES
    contexto_integral = contexto_integral or {}
    hay_potencial = _tiene_potencial(contexto_integral)
    hay_disc = _tiene_disc(contexto_integral)
    hay_360 = _tiene_desempeno_360(resultado)
    hay_objetivos = _tiene_objetivos(contexto_integral)
    competencias_pot_total = len((contexto_integral or {}).get("competencias_potencial", []) or []) if hay_potencial else 0
    paginas_detalle_pot = math.ceil(competencias_pot_total / 4) if competencias_pot_total else 0
    items_360_total = len((contexto_integral or {}).get("items_360", {}) or {}) if hay_360 else 0
    paginas_items_360 = math.ceil(items_360_total / 6) if items_360_total else 0
    TOTAL_PAGES = 0
    if hay_potencial:
        TOTAL_PAGES += 1 + paginas_detalle_pot
    if hay_disc:
        TOTAL_PAGES += 1
    if hay_360:
        TOTAL_PAGES += 2 + paginas_items_360
    if hay_objetivos:
        TOTAL_PAGES += 1
    TOTAL_PAGES = max(TOTAL_PAGES, 1)

    estilos = E()
    ancho_cont = W - 2*PAD_LAT

    frame_y = 1.55*cm
    frame_h = H - PAD_TOP - 0.55*cm - frame_y
    frame   = Frame(PAD_LAT, frame_y, ancho_cont, frame_h,
                    leftPadding=0, rightPadding=0,
                    topPadding=0, bottomPadding=0, showBoundary=0)
    frame_first = Frame(PAD_LAT, frame_y, ancho_cont, H - 0.95*cm - frame_y,
                        leftPadding=0, rightPadding=0,
                        topPadding=0, bottomPadding=0, showBoundary=0)

    def on_first(canvas, doc):
        canvas.saveState()
        _footer(canvas, proceso, doc.page)
        canvas.restoreState()

    def on_later(canvas, doc):
        canvas.saveState()
        _header(canvas, nombre, proceso, doc.page)
        _footer(canvas, proceso, doc.page)
        canvas.restoreState()

    doc = BaseDocTemplate(ruta_salida, pagesize=A4,
                          pageCompression=1,
                          leftMargin=0, rightMargin=0,
                          topMargin=0, bottomMargin=0)
    doc.addPageTemplates([
        PageTemplate(id="primera",   frames=[frame_first],     onPage=on_first),
        PageTemplate(id="contenido", frames=[frame],           onPage=on_later),
    ])

    puntaje_global = resultado["puntaje_global"]
    banda_global   = resultado["clasificacion"]["etiqueta"]
    competencias   = resultado["competencias"]
    desglose       = resultado["desglose_global"]
    pesos          = resultado["pesos_aplicados"]

    ficha_intro = (contexto_integral or {}).get("ficha", {}) or {}
    objetivos_intro = (contexto_integral or {}).get("objetivos", {}) or {}
    cargo_intro = _primer_texto_real(
        cargo,
        ficha_intro.get("cargo"),
        ficha_intro.get("cargo_objetivo"),
        objetivos_intro.get("cargo_objetivo"),
        proceso,
    )
    empresa_intro = _primer_texto_real(ficha_intro.get("empresa"), cliente, default="Speedster")
    jefe_intro = _primer_texto_real(ficha_intro.get("jefe"), objetivos_intro.get("jefe"))
    primera_badge = "Evaluación de Competencias"
    if not hay_potencial and hay_360:
        primera_badge = "Evaluación Desempeño"
    elif not hay_potencial and not hay_360 and hay_objetivos:
        primera_badge = "Evaluación de Objetivos"
    story = _primera_hoja_intro(nombre, cargo_intro, empresa_intro, jefe_intro, ancho_cont, badge=primera_badge)
    if not hay_potencial:
        story += [
            _tabla_ficha_integral(ficha_intro, ancho_cont, estilos),
            spacer(0.28),
        ]
    primera_seccion = True
    contenido_agregado = False

    def nueva_pagina():
        nonlocal primera_seccion
        if primera_seccion:
            story.append(NextPageTemplate("contenido"))
            primera_seccion = False
        story.append(PageBreak())

    if hay_potencial:
        competencias_pot = contexto_integral.get("competencias_potencial", []) or []
        cap = contexto_integral.get("cap", {}) or {}
        cap_score = cap.get("score")
        cap_info = _cap_interpretacion(cap_score)
        story += [
            _card_potencial_descripcion(ancho_cont),
            spacer(0.34),
            _card_potencial_puntuacion(cap, cap_info, ancho_cont),
            spacer(0.34),
            Paragraph("Competencias consideradas", estilos["h3"]),
            spacer(0.2),
            _tabla_cap_competencias(competencias_pot, ancho_cont, estilos, limite=12),
        ]
        contenido_agregado = True
        if competencias_pot:
            nueva_pagina()
            story += [
                Paragraph("INTERPRETACI\u00d3N DE RESULTADOS<br/>DE COMPETENCIAS", ParagraphStyle(
                    "section_h_pot_compact", fontName="Helvetica-Bold", fontSize=18.5,
                    textColor=INK, leading=23,
                )),
                hr(LINE, sb=5, sa=5),
                spacer(0.03),
            ]
            catalogo_comp = _catalogo_competencias_interpretacion()
            for comp_item in competencias_pot:
                story.append(_competencia_detalle_card(comp_item, catalogo_comp, ancho_cont, estilos))

    if hay_disc:
        if contenido_agregado:
            nueva_pagina()
        story += _disc_section_flow(contexto_integral, ancho_cont, estilos)
        contenido_agregado = True

    if hay_360:
        if contenido_agregado:
            nueva_pagina()
            story += [
                _header_360(nombre, cargo_intro, ancho_cont, empresa_intro),
                spacer(0.32),
            ]
        story += [
            _card_360_descripcion(ancho_cont),
            spacer(0.32),
            _card_360_puntuacion(puntaje_global, banda_global, ancho_cont),
            spacer(0.30),
            Paragraph("Detalle de la evaluaci\u00f3n", ParagraphStyle(
                "detalle_eval_title", fontName="Helvetica-Bold", fontSize=11.8,
                textColor=INK, leading=14,
            )),
            spacer(0.18),
            *_detalle_evaluacion_360(competencias, desglose, pesos, puntaje_global, ancho_cont, estilos, compact=True),
        ]
        contenido_agregado = True
        nueva_pagina()
        story += _mapa_competencias_360_page(
            competencias,
            contexto_integral.get("promedios_organizacion_360", {}) if contexto_integral else {},
            ancho_cont,
            estilos,
        )
        for page in _items_360_pages(
            contexto_integral.get("items_360", {}) if contexto_integral else {},
            ancho_cont,
            list(competencias.keys()),
        ):
            nueva_pagina()
            story += page

    if hay_objetivos:
        if contenido_agregado:
            nueva_pagina()
        story += _objetivos_section_flow(
            nombre,
            contexto_integral.get("ficha", {}),
            contexto_integral.get("objetivos", {}),
            contexto_integral.get("objetivos_detalle", []),
            ancho_cont,
            incluir_header=contenido_agregado,
        )
        contenido_agregado = True

    if not contenido_agregado:
        story.append(Paragraph("No hay resultados disponibles para este colaborador en el proceso seleccionado.", estilos["body"]))
    doc.build(story)
    print(f"  OK  {ruta_salida}")



