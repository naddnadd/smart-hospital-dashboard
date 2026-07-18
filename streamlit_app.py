import re
import json
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    page_title="Smart Hospital Nusantara — Audit Transformasi Digital",
    layout="wide",
)

BASE_DIR = Path(__file__).parent
HTML_PATH = BASE_DIR / "app.html"
GEOJSON_PATH = BASE_DIR / "indonesia-province.json"


@st.cache_data(show_spinner="Menyiapkan dashboard (memuat peta provinsi)...")
def build_html() -> str:
    html = HTML_PATH.read_text(encoding="utf-8")
    geojson_text = GEOJSON_PATH.read_text(encoding="utf-8")

    # Validasi ringan supaya kalau formatnya aneh, langsung ketahuan di awal.
    json.loads(geojson_text)

    # 1) Suntikkan isi indonesia-province.json langsung ke dalam HTML,
    #    lewat <script type="application/json">, persis seperti cara RAW data
    #    (data-json) sudah disuntikkan di file aslinya.
    injected = f'<script id="geojson-json" type="application/json">{geojson_text}</script>\n</head>'
    html, n_head = re.subn(r"</head>", injected, html, count=1)
    if n_head == 0:
        raise RuntimeError("Tag </head> tidak ditemukan di app.html — cek isi filenya.")

    # 2) Ganti fungsi loadProvinceGeoJSON() yang tadinya fetch("indonesia-province.json")
    #    (butuh web server / Live Server) supaya membaca dari script tag di atas.
    pattern = re.compile(
        r"async function loadProvinceGeoJSON\(\)\s*\{.*?\}",
        re.DOTALL,
    )
    new_fn = (
        "async function loadProvinceGeoJSON() {\n"
        "  return JSON.parse(document.getElementById('geojson-json').textContent);\n"
        "}"
    )
    html, n_fn = pattern.subn(new_fn, html, count=1)
    if n_fn == 0:
        st.warning(
            "Pola fungsi loadProvinceGeoJSON() tidak ditemukan. "
            "Peta provinsi mungkin masih mencoba fetch() dan gagal di Streamlit. "
            "Cek apakah app.html sudah diedit dari versi aslinya."
        )

    return html


html_content = build_html()
components.html(html_content, height=4200, scrolling=True)
