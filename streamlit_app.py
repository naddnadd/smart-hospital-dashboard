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

    json.loads(geojson_text)

    # 1) Isi indonesia-province.json
    injected = f'<script id="geojson-json" type="application/json">{geojson_text}</script>\n</head>'
    html, n_head = re.subn(r"</head>", injected, html, count=1)
    if n_head == 0:
        raise RuntimeError("Tag </head> tidak ditemukan di app.html — cek isi filenya.")

    # 2) fungsi loadProvinceGeoJSON()
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

    # 3) Patch CSS
    vh_fix = "<style>html,body{min-height:0 !important;}</style>\n</head>"
    html, n_vhfix = re.subn(r"</head>", vh_fix, html, count=1)
    if n_vhfix == 0:
        st.warning("Gagal menyisipkan CSS fix min-height:100vh.")

    # 4) Auto-resize
    autoresize_script = """
<script>
(function () {
  function getFrame() {
    try { return window.frameElement; } catch (e) { return null; }
  }

  function measure() {
    // Setelah CSS fix di atas, scrollHeight sudah murni tinggi konten,
    // tidak lagi terikat ke min-height:100vh.
    return Math.max(
      document.documentElement.scrollHeight,
      document.body ? document.body.scrollHeight : 0
    );
  }

  function resize() {
    const frame = getFrame();
    if (!frame) return;
    const h = measure();
    if (h && h !== frame._lastHeight) {
      frame._lastHeight = h;
      frame.style.height = h + 'px';
      frame.setAttribute('height', h);
      const wrapper = frame.parentElement;
      if (wrapper) wrapper.style.height = h + 'px';
    }
  }

  window.addEventListener('load', resize);
  document.addEventListener('DOMContentLoaded', resize);
  window.addEventListener('resize', resize);
  if (document.fonts && document.fonts.ready) {
    document.fonts.ready.then(resize);
  }

  // Terus pantau selama halaman hidup: menangkap pindah tab, animasi chart,
  // tile peta yang telat render, dsb — bukan cuma beberapa detik pertama.
  if (window.ResizeObserver) {
    new ResizeObserver(resize).observe(document.body);
  }

  // Klik (ganti tab, ganti sub-pilar, toggle rekomendasi, dsb) sering memicu
  // perubahan tinggi yang baru "kelihatan" belakangan — peta Leaflet baru
  // invalidateSize() 50ms kemudian, animasi Chart.js ~1 detik, dst. Paksa
  // ukur ulang beberapa kali setelah setiap klik supaya tidak ketinggalan.
  document.addEventListener('click', function () {
    [0, 150, 400, 800, 1500].forEach(function (delay) {
      setTimeout(resize, delay);
    });
  }, true);

  // Jaring pengaman tambahan di detik-detik awal (untuk browser lama / race condition).
  let tries = 0;
  const interval = setInterval(function () {
    resize();
    tries += 1;
    if (tries > 30) clearInterval(interval);
  }, 250);
})();
</script>
</body>"""
    html, n_body = re.subn(r"</body>", autoresize_script, html, count=1)
    if n_body == 0:
        st.warning(
            "Tag </body> tidak ditemukan di app.html — auto-resize tinggi iframe dilewati."
        )

    return html


html_content = build_html()

st.markdown(
    """
    <style>
      .block-container {
          padding: 0 !important;
          max-width: 100% !important;
      }
      iframe {
          width: 100% !important;
          display: block !important;
      }
    </style>
    """,
    unsafe_allow_html=True,
)

components.html(html_content, height=800, scrolling=False)
