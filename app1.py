# app.py — OCR Cute Edition basado en el código del profesor (cv2 + pytesseract)
import io, os, re, base64
from datetime import datetime

import streamlit as st
import cv2
import numpy as np
import pytesseract
from pytesseract import Output
from PIL import Image, ImageOps, ImageFilter, ImageDraw

# ──────────────────────────────────────────────
# Config general + tema cute (texto negro)
st.set_page_config(page_title="OCR Cute – Reconocimiento de Caracteres", page_icon="📸", layout="wide")

PALETTES = {
    "Rosa crema 🎀":   {"--bg":"linear-gradient(180deg,#fff8fb 0%, #ffe9f2 100%)","--card":"rgba(255,255,255,0.95)","--accent":"#ff84b0","--accent2":"#ffd0e0","--text":"#111","--shadow":"0 10px 30px rgba(255,132,176,.20)"},
    "Lavanda leche 💜": {"--bg":"linear-gradient(180deg,#fefcff 0%, #efe9ff 100%)","--card":"rgba(255,255,255,0.95)","--accent":"#8a6bff","--accent2":"#d8ceff","--text":"#111","--shadow":"0 10px 30px rgba(138,107,255,.18)"},
    "Menta durazno 🍑": {"--bg":"linear-gradient(180deg,#f7fff9 0%, #ffeede 100%)","--card":"rgba(255,255,255,0.95)","--accent":"#2fbf71","--accent2":"#b8f2cf","--text":"#111","--shadow":"0 10px 30px rgba(47,191,113,.18)"},
}

def apply_theme(p):
    css=f"""
    <style>
    :root {{
      --accent:{p['--accent']}; --accent2:{p['--accent2']}; --text:{p['--text']};
    }}
    [data-testid="stAppViewContainer"] {{ background:{p['--bg']} !important; }}
    .block-container {{ padding-top: 1rem; }}
    .card {{
      background:{p['--card']}; border:2px solid var(--accent2); border-radius:22px; padding:1rem 1.1rem;
      box-shadow:{p['--shadow']}; backdrop-filter: blur(6px);
    }}
    h1,h2,h3,label, p, span, div {{ color:var(--text) !important; }}
    .chip {{
      display:inline-flex; align-items:center; gap:.4rem; padding:.35rem .7rem; border-radius:999px;
      background:var(--accent2); color:var(--text); font-weight:600; font-size:.85rem; margin-right:.25rem;
    }}
    .divider {{
      width:100%; height:12px; border-radius:999px;
      background: linear-gradient(90deg, var(--accent), var(--accent2)); opacity:.65; margin:.8rem 0 1rem 0;
    }}
    div.stButton>button {{
      background:var(--accent); color:#fff; border:none; border-radius:16px; padding:.55rem 1rem; font-weight:700;
      box-shadow:0 6px 16px rgba(0,0,0,.08);
    }}
    div.stButton>button:hover {{ filter:brightness(1.06); transform: translateY(-1px); }}
    .stTextArea textarea, .stTextInput input, .stSelectbox [data-baseweb="select"]>div {{
      border-radius:14px !important; border:2px solid var(--accent2) !important; color:var(--text) !important;
    }}
    .stCameraInput label div {{ border-radius:14px; }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

# Sidebar (tema + sticker + filtros)
with st.sidebar:
    st.markdown("## 🎀 Estilo")
    theme_name = st.selectbox("Paleta", list(PALETTES.keys()), index=0)
    sticker = st.selectbox("Sticker", ["Gatito lector 🐱", "Estrella ✨", "Libreta 📒"], index=0)
    st.markdown("## 🎛️ Filtro base")
    filtro = st.radio("Aplicar Filtro",('Con Filtro', 'Sin Filtro'), index=0)

apply_theme(PALETTES[theme_name])

# Header con explicación y sticker (sin corazones)
colL, colR = st.columns([1.2,1], vertical_alignment="center")
with colL:
    st.markdown("# Reconocimiento óptico de\nCaracteres (OCR)")
    st.markdown(
        "- **OCR** convierte **imágenes** (fotos/escaneos) en **texto editable**.\n"
        "- Flujo: 1) Captura/carga la imagen · 2) Pre-procesamiento (mejorar contraste) · 3) OCR · 4) Copia o descarga el texto.\n"
        "- Útil para: apuntes, facturas, formularios, carteles, libros y más."
    )
    st.markdown(
        '<div class="chip">📸 Cámara</div> <div class="chip">🖼️ Upload</div> '
        '<div class="chip">🔤 OCR</div> <div class="chip">💾 TXT</div>', unsafe_allow_html=True
    )
with colR:
    if sticker == "Gatito lector 🐱":
        svg = """
        <svg viewBox="0 0 320 160" xmlns="http://www.w3.org/2000/svg">
         <defs><linearGradient id="bg" x1="0" x2="1"><stop stop-color="#B8F2CF"/><stop offset="1" stop-color="#FFD0E0"/></linearGradient></defs>
         <rect x="0" y="0" width="320" height="160" rx="20" fill="url(#bg)" opacity="0.35"/>
         <g transform="translate(70,30)">
           <ellipse cx="50" cy="60" rx="48" ry="40" fill="#fff"/>
           <path d="M20 40 L35 20 L40 45 Z" fill="#fff"/><path d="M80 40 L65 20 L60 45 Z" fill="#fff"/>
           <circle cx="40" cy="60" r="6" fill="#111"/><circle cx="60" cy="60" r="6" fill="#111"/>
           <path d="M35 75 Q50 85 65 75" stroke="#111" stroke-width="3" fill="none"/>
           <rect x="25" y="80" width="50" height="22" rx="4" fill="#8a6bff"/><line x1="50" y1="80" x2="50" y2="102" stroke="#fff"/>
         </g>
         <text x="160" y="145" text-anchor="middle" font-size="16" fill="#111" font-family="Arial">Lee imágenes y conviértelas en texto</text>
        </svg>"""
    elif sticker == "Estrella ✨":
        svg = """
        <svg viewBox="0 0 320 160" xmlns="http://www.w3.org/2000/svg">
          <defs><linearGradient id="bg" x1="0" x2="1"><stop stop-color="#FFD0E0"/><stop offset="1" stop-color="#D8CEFF"/></linearGradient></defs>
          <rect x="0" y="0" width="320" height="160" rx="20" fill="url(#bg)" opacity="0.35"/>
          <g transform="translate(110,35)"><path d="M50 0 L61 34 H96 L67 55 L78 89 L50 69 L22 89 L33 55 L4 34 H39 Z" fill="#ffb400"/></g>
          <text x="160" y="145" text-anchor="middle" font-size="16" fill="#111" font-family="Arial">Ilumina textos ocultos en tus fotos</text>
        </svg>"""
    else:
        svg = """
        <svg viewBox="0 0 320 160" xmlns="http://www.w3.org/2000/svg">
          <defs><linearGradient id="bg" x1="0" x2="1"><stop stop-color="#B8F2CF"/><stop offset="1" stop-color="#FFEEDC"/></linearGradient></defs>
          <rect x="0" y="0" width="320" height="160" rx="20" fill="url(#bg)" opacity="0.35"/>
          <rect x="70" y="35" width="180" height="90" rx="10" fill="#fff"/><line x1="120" y1="35" x2="120" y2="125" stroke="#ffd0e0"/>
          <text x="95" y="60" font-size="12" fill="#111" font-family="Arial">Notas</text>
          <text x="145" y="60" font-size="12" fill="#111" font-family="Arial">OCR</text>
          <text x="160" y="145" text-anchor="middle" font-size="16" fill="#111" font-family="Arial">Digitaliza tus apuntes rápidamente</text>
        </svg>"""
    st.markdown(f'<div class="card">{svg}</div>', unsafe_allow_html=True)

st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

# ──────────────────────────────────────────────
# Controles de idioma y entrada (manteniendo cámara del profe)
LANGS = {
    "Español (spa)": "spa",
    "English (eng)": "eng",
    "Português (por)": "por",
    "Français (fra)": "fra",
    "Italiano (ita)": "ita",
    "Deutsch (deu)": "deu",
}
c1, c2, c3 = st.columns([1,1,1])
with c1:
    langs = st.multiselect("Idiomas del OCR (instalados en Tesseract)", list(LANGS.keys()), default=["Español (spa)","English (eng)"])
    lang_arg = "+".join(LANGS[k] for k in langs) if langs else "spa"
with c2:
    psm = st.selectbox("Modo de segmentación (PSM)", [
        "3 – Fully automatic",
        "6 – Assume a single uniform block of text",
        "7 – Treat image as a single text line",
        "11 – Sparse text",
    ], index=0)
    psm_value = int(psm.split(" ")[0])
with c3:
    show_boxes = st.toggle("Resaltar palabras detectadas", value=True)

# Entrada: cámara o subir imagen
use_camera = st.toggle("Usar cámara", value=True)
img_file_buffer = None
img_input = None

if use_camera:
    st.markdown("### Toma una Foto")
    img_file_buffer = st.camera_input("Take Photo")
    if img_file_buffer is not None:
        bytes_data = img_file_buffer.getvalue()
        cv2_img = cv2.imdecode(np.frombuffer(bytes_data, np.uint8), cv2.IMREAD_COLOR)
else:
    st.markdown("### Sube una imagen")
    up = st.file_uploader("PNG/JPG", type=["png","jpg","jpeg"])
    if up:
        bytes_data = up.read()
        cv2_img = cv2.imdecode(np.frombuffer(bytes_data, np.uint8), cv2.IMREAD_COLOR)

# Filtros adicionales (además del invertir del profe)
st.markdown("### Pre-procesamiento")
colA, colB, colC, colD = st.columns(4)
with colA:
    use_gray = st.toggle("Escala de grises", value=True)
with colB:
    use_autocontrast = st.toggle("Autocontraste", value=True)
with colC:
    use_threshold = st.toggle("Umbral (binarizar)", value=True)
with colD:
    use_blur = st.toggle("Desenfoque suave", value=False)

def apply_filters(cv2_img, filtro_base="Con Filtro"):
    img = cv2_img.copy()
    if filtro_base == 'Con Filtro':
        img = cv2.bitwise_not(img)
    # PIL para algunas ops rápidas
    pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    if use_gray:
        pil = ImageOps.grayscale(pil)
    if use_autocontrast:
        pil = ImageOps.autocontrast(pil)
    if use_blur:
        pil = pil.filter(ImageFilter.MedianFilter(size=3))
    # Binarizar simple
    if use_threshold:
        arr = np.array(pil if pil.mode=="L" else pil.convert("L"))
        thr = int(arr.mean()*0.9)
        arr = (arr > thr).astype(np.uint8)*255
        pil = Image.fromarray(arr, mode="L")
    return pil

img_proc = None
if 'cv2_img' in locals() and cv2_img is not None:
    img_proc = apply_filters(cv2_img, filtro)

# Mostrar imágenes
if img_proc is not None:
    cX, cY = st.columns(2)
    with cX:
        st.markdown("#### Original")
        st.image(cv2.cvtColor(cv2_img, cv2.COLOR_BGR2RGB), use_column_width=True)
    with cY:
        st.markdown("#### Pre-procesada")
        st.image(img_proc, use_column_width=True)

# ──────────────────────────────────────────────
# OCR con pytesseract (manteniendo el espíritu del profe)
def ocr_text_and_boxes(pil_img: Image.Image, lang: str, psm_v: int):
    config = f'--oem 3 --psm {psm_v}'
    # Texto plano
    text = pytesseract.image_to_string(pil_img, lang=lang, config=config)
    # Data con cajas
    data = pytesseract.image_to_data(pil_img, lang=lang, config=config, output_type=Output.DICT)
    return text, data

go = st.button("🔍 Reconocer texto", type="primary", disabled=img_proc is None)

text_out = ""
overlay_img = None

if go and img_proc is not None:
    with st.spinner("Leyendo caracteres…"):
        try:
            text_out, data = ocr_text_and_boxes(img_proc, lang_arg, psm_value)
            st.success("¡Listo! Texto extraído 🎉")
            if show_boxes and "text" in data:
                overlay_img = img_proc.convert("RGB").copy()
                draw = ImageDraw.Draw(overlay_img)
                n = len(data["text"])
                color_hex = PALETTES[theme_name]["--accent"]
                # Convertir hex a RGB
                color = tuple(int(color_hex.lstrip('#')[i:i+2], 16) for i in (0, 2, 4)) if color_hex.startswith('#') else (255,0,0)
                for i in range(n):
                    txt = data["text"][i]
                    conf = int(data["conf"][i]) if data["conf"][i].isdigit() else -1
                    if txt and conf > 40:  # umbral de confianza
                        x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
                        draw.rectangle([(x, y), (x+w, y+h)], outline=color, width=2)
        except pytesseract.TesseractNotFoundError:
            st.error("No se encontró **Tesseract**. Instálalo y, si es necesario, configura su ruta en `pytesseract.pytesseract.tesseract_cmd`.")
        except Exception as e:
            st.error("Ocurrió un error ejecutando el OCR.")
            st.caption(f"Detalle técnico: {e}")

# Mostrar resultados
if text_out:
    if overlay_img:
        st.markdown("#### Detecciones")
        st.image(overlay_img, use_column_width=True)

    st.markdown("#### Texto reconocido")
    st.text_area("Resultado", value=text_out, height=220)

    # Copiar al portapapeles
    st.markdown(
        f"""
        <script>
        const txt = {repr(text_out)};
        navigator.clipboard.writeText(txt);
        </script>
        """, unsafe_allow_html=True
    )
    st.toast("Texto copiado al portapapeles ✅")

    # Descargar TXT
    fname = f"ocr_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    st.download_button("⬇️ Descargar TXT", data=text_out.encode("utf-8"), file_name=fname, mime="text/plain")

st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
st.caption("Tip: usa buena luz y mantén el documento recto. Si el texto sale tenue, activa **Autocontraste** y **Umbral**.")

    


    


