# app.py — OCR Kawaii (mantiene flujo del profesor + estética cute)
import streamlit as st
import cv2
import numpy as np
import pytesseract
from pytesseract import Output
from PIL import Image
from datetime import datetime

# ── Config básica ───────────────────────────────────────
st.set_page_config(page_title="📸✨ OCR ", page_icon="🧁", layout="centered")

# ── Tema cute (suave, sin romper widgets) ───────────────
PALETTES = {
    "Rosa crema 🎀":   {"bg":"linear-gradient(180deg,#fff8fb 0%, #ffe9f2 100%)","card":"rgba(255,255,255,0.95)","accent":"#ff84b0","accent2":"#ffd0e0","text":"#111"},
    "Lavanda leche 💜": {"bg":"linear-gradient(180deg,#fefcff 0%, #efe9ff 100%)","card":"rgba(255,255,255,0.95)","accent":"#8a6bff","accent2":"#d8ceff","text":"#111"},
    "Menta durazno 🍑": {"bg":"linear-gradient(180deg,#f7fff9 0%, #ffeede 100%)","card":"rgba(255,255,255,0.95)","accent":"#2fbf71","accent2":"#b8f2cf","text":"#111"},
}
with st.sidebar:
    st.markdown("## 🎀 Estilo")
    theme_name = st.selectbox("Paleta", list(PALETTES.keys()), index=0)

p = PALETTES[theme_name]
st.markdown(f"""
<style>
[data-testid="stAppViewContainer"] {{background:{p['bg']} !important;}}
h1, h2, h3, label, p, span, div {{ color:{p['text']} !important; }}
.card {{ background:{p['card']}; border:2px solid {p['accent2']}; border-radius:22px; padding:1rem 1.1rem; backdrop-filter:blur(6px); }}
.chip {{ display:inline-flex; align-items:center; gap:.4rem; padding:.35rem .7rem; border-radius:999px;
         background:{p['accent2']}; color:{p['text']}; font-weight:600; font-size:.85rem; margin-right:.25rem;}}
.divider {{ width:100%; height:10px; border-radius:999px; background:linear-gradient(90deg,{p['accent']},{p['accent2']});
           opacity:.65; margin:.8rem 0 1rem 0;}}
div.stButton>button {{ background:{p['accent']}; color:#fff; border:none; border-radius:16px; padding:.55rem 1rem; font-weight:700; }}
div.stButton>button:hover {{ filter:brightness(1.06); transform:translateY(-1px); }}
.stTextArea textarea, .stSelectbox [data-baseweb="select"]>div {{ border-radius:14px !important; border:2px solid {p['accent2']} !important; }}
.stCameraInput label div {{ border-radius:14px; }}
</style>
""", unsafe_allow_html=True)

# ── Cabecera creativa (solo decorativa) ─────────────────
st.title("📸✨ OCR Kawaii — Convierte tus fotos en texto")
st.caption("Reconocimiento óptico de caracteres (OCR): toma una foto o sube una imagen y te devolvemos el texto editable.")
svg = f"""
<svg viewBox="0 0 320 120" xmlns="http://www.w3.org/2000/svg">
  <defs><linearGradient id="bg" x1="0" x2="1"><stop stop-color="{p['accent2']}"/><stop offset="1" stop-color="#CDEEE0"/></linearGradient></defs>
  <rect x="0" y="0" width="320" height="120" rx="16" fill="url(#bg)" opacity="0.5"/>
  <g transform="translate(30,25)">
    <ellipse cx="40" cy="35" rx="36" ry="28" fill="#fff"/>
    <path d="M20 25 L30 10 L35 27 Z" fill="#fff"/><path d="M60 25 L50 10 L45 27 Z" fill="#fff"/>
    <circle cx="33" cy="35" r="5" fill="#111"/><circle cx="47" cy="35" r="5" fill="#111"/>
    <path d="M33 48 Q40 54 47 48" stroke="#111" stroke-width="3" fill="none"/>
    <rect x="22" y="58" width="36" height="12" rx="3" fill="{p['accent']}"/><line x1="40" y1="58" x2="40" y2="70" stroke="#fff"/>
  </g>
  <text x="180" y="70" font-size="14" fill="#111" font-family="Arial">Saca una foto y te damos el texto ✨</text>
</svg>
"""
st.markdown(f'<div class="card" style="display:flex;justify-content:center;">{svg}</div>', unsafe_allow_html=True)
st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

# ── Sidebar del profe + extras (sin romper flujo) ──────
with st.sidebar:
    st.subheader("Aplicar filtro")
    filtro = st.radio("Filtro base", ('Con Filtro', 'Sin Filtro'), index=0)

    st.markdown("---")
    st.subheader("Subir imagen (opcional)")
    up = st.file_uploader("PNG/JPG", type=["png","jpg","jpeg"])
    st.caption("Si no tomas foto, usaremos esta imagen.")

    st.markdown("---")
    st.subheader("Tesseract (opcional)")
    lang = st.selectbox("Idioma", ["auto (eng)", "Español (spa)", "English (eng)", "Português (por)", "Français (fra)"], index=0)
    lang_map = {"auto (eng)":"eng","Español (spa)":"spa","English (eng)":"eng","Português (por)":"por","Français (fra)":"fra"}
    lang_code = lang_map[lang]
    psm = st.selectbox("PSM", ["3 – Fully automatic","6 – Single uniform block","7 – Single line","11 – Sparse text"], index=0)
    psm_value = int(psm.split(" ")[0])

# ── CÁMARA (exacto al profe) ───────────────────────────
img_file_buffer = st.camera_input("Toma una foto", key="camera_widget")

# ── Flujo original: si hay foto, procesa; si no, intenta upload ──
bytes_data = None
if img_file_buffer is not None:
    bytes_data = img_file_buffer.getvalue()
elif up is not None:
    bytes_data = up.read()

if bytes_data is not None:
    # Igual que el profe
    cv2_img = cv2.imdecode(np.frombuffer(bytes_data, np.uint8), cv2.IMREAD_COLOR)

    # Filtro del profe (invertir)
    if filtro == 'Con Filtro':
        cv2_img = cv2.bitwise_not(cv2_img)

    # A color → RGB para Tesseract
    img_rgb = cv2.cvtColor(cv2_img, cv2.COLOR_BGR2RGB)

    # OCR inmediato (como el profe), con idioma/psm opcionales
    config = f'--oem 3 --psm {psm_value}'
    try:
        text = pytesseract.image_to_string(img_rgb, lang=lang_code, config=config)
    except pytesseract.TesseractNotFoundError:
        st.error("No se encontró **Tesseract**. Instálalo y (si hace falta) configura `pytesseract.pytesseract.tesseract_cmd`.")
        text = ""
    except Exception as e:
        st.error("Error ejecutando el OCR.")
        st.caption(f"Detalle técnico: {e}")
        text = ""

    # Salida: mantenemos st.write + UI cute extra
    st.subheader("Texto reconocido")
    st.text_area("Resultado", value=text, height=220)
    st.write(text)

    # Descarga rápida
    fname = f"ocr_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    st.download_button("⬇️ Descargar TXT", data=(text or "").encode("utf-8"),
                       file_name=fname, mime="text/plain")

    # Detecciones (opcional, no interfiere)
    with st.expander("Ver palabras detectadas (opcional)"):
        try:
            data = pytesseract.image_to_data(img_rgb, lang=lang_code, config=config, output_type=Output.DICT)
            overlay = img_rgb.copy()
            n = len(data["text"])
            for i in range(n):
                txt = data["text"][i]
                conf_str = str(data["conf"][i])
                conf = int(conf_str) if conf_str.isdigit() else -1
                if txt and conf > 40:
                    x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
                    cv2.rectangle(overlay, (x, y), (x+w, y+h), (255,105,180), 2)  # rosa
            st.image(overlay, caption="Palabras detectadas", use_column_width=True)
        except Exception:
            st.caption("No se pudieron generar las cajas esta vez.")

else:
    # Tips útiles (en lugar de dejarlo vacío)
    st.markdown(
        f"""
<div class="card">
<b>¿Cómo usarlo?</b><br>
1) Presiona <b>Toma una foto</b> y autoriza la cámara, o sube una imagen desde la barra lateral.<br>
2) (Opcional) Ajusta <i>Idioma</i> y <i>PSM</i> si el texto sale raro.<br>
3) ¡Listo! El texto aparecerá aquí y podrás <b>descargarlo</b>.
</div>
""", unsafe_allow_html=True)

