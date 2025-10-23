# app.py — OCR (base del profesor) + estética kawaii y extras no invasivos
import streamlit as st
import cv2
import numpy as np
import pytesseract
from pytesseract import Output
from PIL import Image
from datetime import datetime

# Si lo necesitas en Windows/Mac, descomenta y pon la ruta:
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

st.set_page_config(page_title="📸✨ OCR Kawaii — Convierte tus fotos en texto", page_icon="🧁", layout="centered")

# ---------- Cabecera creativa (no interfiere con el flujo del profe) ----------
st.title("📸✨ OCR Kawaii — Convierte tus fotos en texto")
st.caption("Reconocimiento óptico de caracteres (OCR) · Toma una foto o sube una imagen y obtén el texto editable.")

# Ilustración SVG suave (opcional) — no requiere archivo local
svg = """
<svg viewBox="0 0 320 120" xmlns="http://www.w3.org/2000/svg">
  <defs><linearGradient id="bg" x1="0" x2="1"><stop stop-color="#FFD7E2"/><stop offset="1" stop-color="#CDEEE0"/></linearGradient></defs>
  <rect x="0" y="0" width="320" height="120" rx="16" fill="url(#bg)" opacity="0.5"/>
  <g transform="translate(30,25)">
    <ellipse cx="40" cy="35" rx="36" ry="28" fill="#fff"/>
    <path d="M20 25 L30 10 L35 27 Z" fill="#fff"/><path d="M60 25 L50 10 L45 27 Z" fill="#fff"/>
    <circle cx="33" cy="35" r="5" fill="#111"/><circle cx="47" cy="35" r="5" fill="#111"/>
    <path d="M33 48 Q40 54 47 48" stroke="#111" stroke-width="3" fill="none"/>
    <rect x="22" y="58" width="36" height="12" rx="3" fill="#8a6bff"/><line x1="40" y1="58" x2="40" y2="70" stroke="#fff"/>
  </g>
  <text x="180" y="70" font-size="14" fill="#111" font-family="Arial">Saca una foto y te damos el texto ✨</text>
</svg>
"""
st.markdown(f'<div style="display:flex;justify-content:center;">{svg}</div>', unsafe_allow_html=True)
st.write("")

# ---------- Cámara (misma usabilidad del profesor) ----------
# IMPORTANTE: conservamos el orden original y el nombre de la variable
img_file_buffer = st.camera_input("Toma una Foto", key="camera_widget")

# ---------- Sidebar del profesor + extras opcionales ----------
with st.sidebar:
    st.subheader("Aplicar Filtro")
    filtro = st.radio("Aplicar Filtro", ('Con Filtro', 'Sin Filtro'), index=0)

    st.markdown("---")
    st.subheader("Opcional: subir imagen")
    up = st.file_uploader("PNG/JPG", type=["png", "jpg", "jpeg"])
    st.caption("Si subes una imagen y no tomas foto, usaremos la imagen subida.")

    st.markdown("---")
    st.subheader("Opciones Tesseract (opcionales)")
    lang = st.selectbox("Idioma", ["auto (eng)", "Español (spa)", "English (eng)", "Português (por)", "Français (fra)"], index=0)
    lang_map = {
        "auto (eng)": "eng",  # por compatibilidad simple
        "Español (spa)": "spa",
        "English (eng)": "eng",
        "Português (por)": "por",
        "Français (fra)": "fra"
    }
    lang_code = lang_map[lang]

    psm = st.selectbox(
        "PSM (segmentación)",
        ["3 – Fully automatic", "6 – Single uniform block", "7 – Single text line", "11 – Sparse text"],
        index=0
    )
    psm_value = int(psm.split(" ")[0])

# ---------- Lógica EXACTA del profe + mejoras suaves ----------
# Priorizamos la foto de la cámara. Si no hay, usamos upload si existe.
bytes_data = None
if img_file_buffer is not None:
    bytes_data = img_file_buffer.getvalue()
elif up is not None:
    bytes_data = up.read()

if bytes_data is not None:
    # Igual que el profe: cv2.imdecode sobre el buffer
    cv2_img = cv2.imdecode(np.frombuffer(bytes_data, np.uint8), cv2.IMREAD_COLOR)

    # Filtro del profesor (invertir colores)
    if filtro == 'Con Filtro':
        cv2_img = cv2.bitwise_not(cv2_img)
    else:
        cv2_img = cv2_img

    # Conversión a RGB para Tesseract
    img_rgb = cv2.cvtColor(cv2_img, cv2.COLOR_BGR2RGB)

    # ---- Opcionales ligeros: PSM/Idioma (no cambian el flujo original) ----
    config = f'--oem 3 --psm {psm_value}'
    try:
        text = pytesseract.image_to_string(img_rgb, lang=lang_code, config=config)
    except pytesseract.TesseractNotFoundError:
        st.error("No se encontró **Tesseract**. Instálalo y, si hace falta, configura su ruta en `pytesseract.pytesseract.tesseract_cmd`.")
        text = ""
    except Exception as e:
        st.error("Ocurrió un error ejecutando el OCR.")
        st.caption(f"Detalle técnico: {e}")
        text = ""

    # Mostrar resultado (mantengo el st.write del profe, añado text_area y descarga)
    st.subheader("Texto reconocido")
    st.text_area("Resultado", value=text, height=220)
    st.write(text)  # línea del profe (por compatibilidad con su demo)

    # Descargar TXT
    fname = f"ocr_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    st.download_button("⬇️ Descargar TXT", data=(text or "").encode("utf-8"),
                       file_name=fname, mime="text/plain")

    # Resaltar palabras (opcional, no rompe el flujo)
    with st.expander("Ver detecciones resaltadas (opcional)"):
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
                    cv2.rectangle(overlay, (x, y), (x+w, y+h), (255, 105, 180), 2)  # rosa suave
            st.image(overlay, caption="Palabras detectadas", use_column_width=True)
        except Exception:
            st.caption("No se pudieron generar las cajas esta vez (opcional).")

else:
    st.info("Toma una foto con tu cámara o sube una imagen desde la barra lateral. 💖")
