# app.py — OCR Cute Edition basado en el código del profesor
import re
from datetime import datetime

import streamlit as st
import cv2
import numpy as np
import pytesseract
from pytesseract import Output
from PIL import Image, ImageOps, ImageFilter, ImageDraw

# ─────────────────────────────────────────────────────
# Configuración y tema (texto negro para alto contraste)
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

# Sidebar
with st.sidebar:
    st.markdown("## 🎀 Estilo")
    theme_name = st.selectbox("Paleta", list(PALETTES.keys()), index=0)
    st.markdown("## 🎛️ Filtro base")
    filtro = st.radio("Aplicar Filtro",('Con Filtro', 'Sin Filtro'), index=0)

apply_theme(PALETTES[theme_name])

# ─────────────────────────────────────────────────────
# Encabezado y explicación
st.title("Reconocimiento óptico de caracteres (OCR)")
st.caption("Convierte imágenes (fotos/escaneos) en texto editable")

st.markdown(
    "- **OCR** convierte **imágenes** en **texto** que puedes copiar/editar.\n"
    "- Flujo: 1) Captura o sube la imagen · 2) Preprocesa para mejorar contraste · 3) Ejecuta OCR · 4) Copia o descarga el resultado.\n"
    "- Usos: apuntes, facturas, formularios, carteles, libros, etc."
)
st.markdown('<div class="chip">📸 Cámara</div> <div class="chip">🖼️ Upload</div> <div class="chip">🔤 OCR</div> <div class="chip">💾 TXT</div>', unsafe_allow_html=True)
st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────────────
# Controles de idioma y PSM (Tesseract)
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
    langs = st.multiselect("Idiomas del OCR (instalados en Tesseract)", list(LANGS.keys()),
                           default=["Español (spa)","English (eng)"])
    lang_arg = "+".join(LANGS[k] for k in langs) if langs else "spa"
with c2:
    psm = st.selectbox("Modo de segmentación (PSM)", [
        "3 – Fully automatic",
        "6 – Single uniform block",
        "7 – Single text line",
        "11 – Sparse text",
    ], index=0)
    psm_value = int(psm.split(" ")[0])
with c3:
    show_boxes = st.toggle("Resaltar palabras detectadas", value=True)

# ─────────────────────────────────────────────────────
# ENTRADA estable: Cámara o Upload (con key fija)
use_camera = st.toggle("Usar cámara", value=True, key="use_camera")

cv2_img = None
if use_camera:
    st.subheader("Toma una foto")
    img_file_buffer = st.camera_input(
        "Cámara",
        key="camera_widget",
        help="Si no ves la cámara: permite acceso en el navegador y recarga la página."
    )
    if img_file_buffer is not None:
        bytes_data = img_file_buffer.getvalue()
        cv2_img = cv2.imdecode(np.frombuffer(bytes_data, np.uint8), cv2.IMREAD_COLOR)
else:
    st.subheader("Sube una imagen")
    up = st.file_uploader("PNG/JPG", type=["png","jpg","jpeg"], key="uploader_widget")
    if up is not None:
        bytes_data = up.read()
        cv2_img = cv2.imdecode(np.frombuffer(bytes_data, np.uint8), cv2.IMREAD_COLOR)

# ─────────────────────────────────────────────────────
# Preprocesamiento: filtro del profe + extras simples
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
    # Filtro original del profesor
    if filtro_base == 'Con Filtro':
        img = cv2.bitwise_not(img)

    pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    if use_gray:
        pil = ImageOps.grayscale(pil)
    if use_autocontrast:
        pil = ImageOps.autocontrast(pil)
    if use_blur:
        pil = pil.filter(ImageFilter.MedianFilter(size=3))
    if use_threshold:
        arr = np.array(pil if pil.mode == "L" else pil.convert("L"))
        thr = int(arr.mean() * 0.9)
        arr = (arr > thr).astype(np.uint8) * 255
        pil = Image.fromarray(arr, mode="L")

    return pil

img_proc = None
if cv2_img is not None:
    img_proc = apply_filters(cv2_img, filtro)

# Mostrar original y preprocesada
if img_proc is not None:
    cX, cY = st.columns(2)
    with cX:
        st.markdown("#### Original")
        st.image(cv2.cvtColor(cv2_img, cv2.COLOR_BGR2RGB), use_column_width=True)
    with cY:
        st.markdown("#### Pre-procesada")
        st.image(img_proc, use_column_width=True)

# ─────────────────────────────────────────────────────
# OCR con pytesseract (texto + cajas)
def ocr_text_and_boxes(pil_img: Image.Image, lang: str, psm_v: int):
    config = f'--oem 3 --psm {psm_v}'
    text = pytesseract.image_to_string(pil_img, lang=lang, config=config)
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
                # usa el color de acento del tema
                color_hex = PALETTES[theme_name]["--accent"]
                color = (255, 0, 0)
                if color_hex.startswith("#") and len(color_hex) == 7:
                    color = tuple(int(color_hex[i:i+2], 16) for i in (1, 3, 5))
                for i in range(n):
                    txt = data["text"][i]
                    conf_str = str(data["conf"][i])
                    conf = int(conf_str) if conf_str.isdigit() else -1
                    if txt and conf > 40:
                        x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
                        draw.rectangle([(x, y), (x+w, y+h)], outline=color, width=2)
        except pytesseract.TesseractNotFoundError:
            st.error("No se encontró **Tesseract**. Instálalo y, si hace falta, configura su ruta en `pytesseract.pytesseract.tesseract_cmd`.")
        except Exception as e:
            st.error("Ocurrió un error ejecutando el OCR.")
            st.caption(f"Detalle técnico: {e}")

# ─────────────────────────────────────────────────────
# Resultados y acciones
if text_out:
    if overlay_img:
        st.markdown("#### Detecciones")
        st.image(overlay_img, use_column_width=True)

    st.markdown("#### Texto reconocido")
    st.text_area("Resultado", value=text_out, height=220)

    # Copiar al portapapeles (JS)
    st.markdown(
        f"""
        <script>
        const txt = {repr(text_out)};
        navigator.clipboard.writeText(txt);
        </script>
        """,
        unsafe_allow_html=True
    )
    st.toast("Texto copiado al portapapeles ✅")

    # Descargar TXT
    fname = f"ocr_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    st.download_button("⬇️ Descargar TXT", data=text_out.encode("utf-8"),
                       file_name=fname, mime="text/plain")

st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
st.caption("Tip: usa buena luz y mantén el documento recto. Si el texto sale tenue, activa **Autocontraste** y **Umbral**.")

