"""Streamlit user interface backed by the Django prediction API."""
import html
import os

import requests
import streamlit as st


st.set_page_config(page_title='KosMadiun | Estimasi kos', page_icon='🏡', layout='wide')
try:
    cloud_api_url = st.secrets.get('DJANGO_API_URL')
except Exception:
    # Streamlit raises when no local secrets.toml is configured.
    cloud_api_url = None
API_BASE = (cloud_api_url or os.environ.get(
    'DJANGO_API_URL', 'http://127.0.0.1:8000'
)).rstrip('/')
if 'dark_theme' not in st.session_state:
    st.session_state.dark_theme = False

dark_theme = st.session_state.dark_theme
theme_variables = (
    '--ink:#e5f2ec;--muted:#a0b5ac;--green:#75d0b1;--line:#2b4038;'
    '--page:#0d1714;--surface:#14231f;--field:#192b25;--pale:#1a3028;'
    '--result-border:#315344;--soft:#253a32;--mode:dark'
    if dark_theme else
    '--ink:#17332e;--muted:#71817c;--green:#176b5b;--line:#e1eae5;'
    '--page:#f5f8f5;--surface:#ffffff;--field:#fcfdfc;--pale:#edf7f1;'
    '--result-border:#d1e6d9;--soft:#f0f7f2;--mode:light'
)


def toggle_theme():
    st.session_state.dark_theme = not st.session_state.dark_theme


def render_bar_chart(points):
    """Build a responsive SVG bar chart without a dataframe/chart dependency."""
    if not points:
        return '<p>Belum ada data untuk ditampilkan.</p>'
    width, height = 760, 340
    left, right, top, bottom = 70, 24, 28, 58
    plot_width, plot_height = width - left - right, height - top - bottom
    max_value = max(float(point['harga_ribu']) for point in points) * 1.18 or 1
    slot = plot_width / len(points)
    bar_width = min(72, slot * .56)
    grid = []
    for tick in range(5):
        ratio = 1 - tick / 4
        y = top + plot_height * tick / 4
        grid.append(
            f'<line x1="{left}" y1="{y:.1f}" x2="{width-right}" y2="{y:.1f}" class="grid"/>'
            f'<text x="{left-10}" y="{y+4:.1f}" text-anchor="end" class="tick">{max_value*ratio:,.0f}</text>'
        )
    bars = []
    for index, point in enumerate(points):
        value = float(point['harga_ribu'])
        x = left + index * slot + (slot - bar_width) / 2
        bar_height = value / max_value * plot_height
        y = top + plot_height - bar_height
        distance = float(point['jarak_km'])
        label = point.get('label', f'{distance:g} km')
        bar_class = 'bar prediction' if point.get('is_prediction') else 'bar'
        fill = 'url(#kosPrediction)' if point.get('is_prediction') else 'url(#kosBar)'
        bars.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_width:.1f}" height="{bar_height:.1f}" rx="9" class="{bar_class}" fill="{fill}">'
            f'<title>{label} · {value:,.0f} ribu rupiah</title></rect>'
            f'<text x="{x+bar_width/2:.1f}" y="{max(top+14,y-9):.1f}" text-anchor="middle" class="value">{value:,.0f}</text>'
            f'<text x="{left+index*slot+slot/2:.1f}" y="{height-28}" text-anchor="middle" class="label">{label}</text>'
        )
    return f'''<div class="chart-shell"><svg viewBox="0 0 {width} {height}" role="img" aria-label="Grafik batang harga kos menurut jarak">
      <defs><linearGradient id="kosBar" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stop-color="#36a78b"/><stop offset="100%" stop-color="#176b5b"/></linearGradient><linearGradient id="kosPrediction" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stop-color="#e9a83b"/><stop offset="100%" stop-color="#be7620"/></linearGradient></defs>
      <style>.grid{{stroke:var(--line);stroke-dasharray:3 5}}.tick,.label{{font:12px system-ui;fill:var(--muted)}}.value{{font:600 11px system-ui;fill:var(--ink)}}</style>
      {''.join(grid)}<text transform="translate(18 {top+plot_height/2}) rotate(-90)" text-anchor="middle" class="label">Harga (ribu Rp)</text>
      {''.join(bars)}<text x="{left+plot_width/2}" y="{height-4}" text-anchor="middle" class="label">Jarak ke pusat kota</text>
    </svg></div>'''


st.markdown(f'<style>:root{{{theme_variables}}}</style>', unsafe_allow_html=True)
st.markdown('''
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@500;600;700;800&display=swap');
:root{color-scheme:var(--mode)}
.stApp{background:radial-gradient(ellipse at 10% 0%,color-mix(in srgb,var(--green) 12%,transparent) 0,transparent 34%),var(--page);color:var(--ink)}
.block-container{max-width:1180px;padding:2.3rem 2rem 3.5rem}
h1,h2,h3{font-family:Manrope, sans-serif!important;letter-spacing:-.045em!important;color:var(--ink)}
h1{font-size:clamp(2.4rem,5vw,3.55rem)!important;line-height:1.05!important;margin:.5rem 0 .8rem!important}
[data-testid="stHeader"]{background:transparent}
[data-testid="stToolbar"],[data-testid="stDecoration"]{display:none}
[data-testid="stVerticalBlockBorderWrapper"]{background:var(--surface);border-color:var(--line);border-radius:20px;box-shadow:0 14px 38px #17332e0b;padding:1.1rem}
[data-testid="stMetric"]{background:linear-gradient(125deg,var(--pale),var(--soft));border:1px solid var(--result-border);border-radius:14px;padding:16px 18px}
[data-testid="stMetricLabel"]{color:var(--muted)}
[data-testid="stMetricValue"]{font-family:Manrope,sans-serif;color:var(--ink);font-weight:750}
div.stButton>button,div.stFormSubmitButton>button{background:linear-gradient(135deg,#1b7865,#145b4e);color:#fff;border:0;border-radius:11px;font-weight:650;min-height:2.8rem;box-shadow:0 5px 13px #176b5b22;transition:transform .15s,box-shadow .15s}
div.stButton>button:hover,div.stFormSubmitButton>button:hover{background:linear-gradient(135deg,#176b5b,#104a40);transform:translateY(-1px);box-shadow:0 8px 16px #176b5b30}
[data-testid="stWidgetLabel"] p{font-weight:650;color:var(--ink)}
[data-baseweb="input"]>div,[data-baseweb="select"]>div{border-radius:10px;border-color:var(--line);background:var(--field)}
[data-baseweb="input"] input,[data-baseweb="select"] div{color:var(--ink)}
[data-testid="stCaptionContainer"]{color:var(--muted)}
.site-header{display:flex;align-items:center;gap:12px;padding:.6rem 0 1rem;border-bottom:1px solid var(--line);margin-bottom:1.5rem}
.site-mark{width:40px;height:40px;border-radius:13px;background:linear-gradient(140deg,#36a78b,#176b5b);display:grid;place-items:center;color:#fff;font-size:20px}
.site-name{font-family:Manrope,sans-serif;font-weight:800;font-size:1.08rem;letter-spacing:-.04em;color:var(--ink)}
.site-name span{color:var(--green)}.site-tagline{font-size:.76rem;color:var(--muted)}
.hero-kicker{display:inline-block;padding:6px 11px;border-radius:999px;background:var(--pale);border:1px solid var(--result-border);color:var(--green);font-size:.72rem;font-weight:750;letter-spacing:.13em}
.hero-copy{color:var(--muted);font-size:1.02rem;max-width:680px;margin:0 0 1.45rem}
.footnote{font-size:.76rem;color:var(--muted);padding-top:.75rem;border-top:1px dashed var(--line)}
.chart-shell{width:100%;margin:.4rem 0}.chart-shell svg{display:block;width:100%;height:auto;overflow:visible}
.auto-explanation{margin:.8rem 0 0;padding:1rem 1.05rem;border:1px solid var(--result-border);border-radius:13px;background:linear-gradient(125deg,var(--soft),var(--pale));color:var(--ink);font-size:.88rem;line-height:1.65}
.auto-explanation strong{display:block;margin-bottom:.25rem;color:var(--green);font-size:.68rem;letter-spacing:.1em;text-transform:uppercase}
.analysis-price{height:100%;min-height:240px;display:flex;flex-direction:column;justify-content:center;padding:1.1rem 1.25rem;border:1px solid var(--result-border);border-radius:14px;background:linear-gradient(125deg,var(--pale),var(--soft))}
.analysis-price span{color:var(--muted);font-size:.78rem}.analysis-price strong{margin-top:.25rem;color:var(--ink);font-family:Manrope,sans-serif;font-size:clamp(1.7rem,3vw,2.3rem);letter-spacing:-.04em}
.analysis-explanation{height:100%;min-height:240px;margin-top:0}
.analysis-bottom-space{height:.85rem}
[data-testid="stVerticalBlockBorderWrapper"]:has(.detail-panel-marker),[data-testid="stVerticalBlockBorderWrapper"]:has(.chart-panel-marker){box-sizing:border-box;min-height:620px}
.reference-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));grid-auto-rows:1fr;align-items:stretch;gap:.65rem;margin-top:.65rem;padding-bottom:1rem}
.reference-card{box-sizing:border-box;min-width:0;min-height:158px;height:100%;display:flex;flex-direction:column;padding:.72rem .75rem;border:1px solid var(--line);border-radius:12px;background:var(--surface)}
.reference-card{border-top:3px solid var(--green)}
.reference-index{color:var(--muted);font-size:.65rem;font-weight:700;letter-spacing:.1em}
.reference-name{font-weight:700;color:var(--ink);font-size:.82rem;overflow-wrap:anywhere}
.reference-price{margin:.28rem 0;color:var(--green);font-family:Manrope,sans-serif;font-size:1rem;font-weight:800}
.reference-delta{margin:.2rem 0 .35rem;color:var(--muted);font-size:.67rem;font-weight:600;line-height:1.35}
.reference-detail{margin-top:auto;padding-top:.55rem;color:var(--muted);font-size:.68rem;line-height:1.5}
.summary-strip{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:.65rem;margin-top:.85rem}
.summary-item{display:flex;align-items:center;gap:.7rem;padding:.72rem .9rem;border:1px solid var(--line);border-radius:12px;background:var(--surface)}
.summary-value{font-family:Manrope,sans-serif;color:var(--ink);font-size:.86rem;font-weight:750;white-space:nowrap}
.summary-label{color:var(--muted);font-size:.72rem;line-height:1.35}
.site-footer{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:.25rem;padding:1.1rem 0 .2rem;margin-top:1rem;border-top:1px solid var(--line);color:var(--muted);font-size:.75rem;text-align:center}
@media(max-width:760px){[data-testid="stVerticalBlockBorderWrapper"]:has(.detail-panel-marker),[data-testid="stVerticalBlockBorderWrapper"]:has(.chart-panel-marker){min-height:0}}
@media(max-width:680px){.reference-grid{grid-template-columns:1fr}.summary-strip{grid-template-columns:1fr}}
</style>''', unsafe_allow_html=True)

header_left, header_right = st.columns([12, 1], vertical_alignment='center')
with header_left:
    st.markdown('<div class="site-header"><div class="site-mark">⌂</div><div><div class="site-name">Kos<span>Madiun</span></div><div class="site-tagline">Estimasi sewa kos berbasis data</div></div></div>', unsafe_allow_html=True)
with header_right:
    st.button('☀' if dark_theme else '☾', key='theme_switch', on_click=toggle_theme,
              help='Ganti ke tema terang' if dark_theme else 'Ganti ke tema gelap')

st.markdown('<div class="hero-kicker">KOSMADIUN &nbsp; / &nbsp; MINI PROYEK SISTEM CERDAS</div>',
            unsafe_allow_html=True)
st.title('Temukan estimasi kos yang pas.')
st.markdown('<p class="hero-copy">Perkirakan harga sewa kos di Madiun dari jarak, fasilitas, dan rating. Model belajar dari data kos terbuka untuk memberi gambaran yang lebih terukur.</p>',
            unsafe_allow_html=True)

left, right = st.columns([.94, 1.06], gap='large', vertical_alignment='top')
with left:
    with st.container(border=True):
        st.markdown('<span class="detail-panel-marker"></span>', unsafe_allow_html=True)
        st.subheader('Detail kos')
        st.caption('Masukkan karakteristik kos yang ingin Anda perkirakan.')
        with st.form('prediction_form'):
            jarak = st.number_input('Jarak ke pusat kota (km)', min_value=0.0, max_value=30.0,
                                    value=2.0, step=0.1)
            ac_label = st.selectbox('Fasilitas AC', ['Tersedia', 'Tidak tersedia'])
            rating = st.slider('Rating (1–5)', min_value=1.0, max_value=5.0,
                               value=4.0, step=0.1)
            submitted = st.form_submit_button('Hitung estimasi  →', use_container_width=True)

        if submitted:
            st.session_state.pop('prediction', None)
            st.session_state.pop('prediction_chart', None)
            st.session_state.pop('explanation', None)
            st.session_state.pop('references', None)
            try:
                response = requests.post(
                    f'{API_BASE}/api/predict/',
                    json={'jarak_km': jarak, 'rating': rating,
                          'ac': 'ya' if ac_label == 'Tersedia' else 'tidak'},
                    timeout=15,
                )
                data = response.json()
                if not response.ok:
                    st.error(data.get('error', 'Prediksi gagal.'))
                else:
                    st.session_state['prediction'] = data['harga_rupiah']
                    st.session_state['prediction_chart'] = data['chart_data']
                    st.session_state['explanation'] = data['explanation']
                    st.session_state['references'] = data['references']
            except requests.RequestException:
                st.error('Tidak bisa menghubungi Django. Pastikan backend berjalan di port 8000.')

with right:
    with st.container(border=True):
        st.markdown('<span class="chart-panel-marker"></span>', unsafe_allow_html=True)
        st.subheader('Harga kos menurut jarak')
        st.caption('Rata-rata harga pada tiap kelompok jarak dari pusat kota.')
        try:
            chart_response = requests.get(f'{API_BASE}/api/chart/', timeout=15)
            chart_response.raise_for_status()
            chart_data = chart_response.json()
            points = st.session_state.get('prediction_chart', chart_data['data'])
            st.markdown(render_bar_chart(points), unsafe_allow_html=True)
            if st.session_state.get('prediction_chart'):
                st.caption(f"{chart_data['jumlah_data']} data kos · Batang emas menunjukkan prediksi input Anda.")
            else:
                st.caption(f"{chart_data['jumlah_data']} data kos · Harga ditampilkan dalam ribuan rupiah.")
        except (requests.RequestException, ValueError, KeyError):
            st.info('Grafik belum tersedia. Pastikan Django berjalan dan dataset dapat dibaca.')

        st.markdown('<div class="footnote">Model Ridge Regression · Fitur jarak, AC, dan rating · Estimasi bersifat informatif.</div>',
                    unsafe_allow_html=True)

if st.session_state.get('prediction') is not None and st.session_state.get('explanation'):
    with st.container(border=True):
        st.subheader('Hasil analisis')
        result_col, explanation_col = st.columns([.38, .62], gap='large', vertical_alignment='top')
        with result_col:
            formatted_price = f"Rp {st.session_state['prediction']:,.0f}".replace(',', '.')
            st.markdown(
                f'<div class="analysis-price"><span>Estimasi harga sewa per bulan</span><strong>{formatted_price}</strong></div>',
                unsafe_allow_html=True,
            )
        with explanation_col:
            safe_explanation = html.escape(st.session_state['explanation'])
            st.markdown(
                f'<div class="auto-explanation analysis-explanation"><strong>Penjelasan hasil</strong>{safe_explanation}</div>',
                unsafe_allow_html=True,
            )
        st.markdown('<div class="analysis-bottom-space"></div>', unsafe_allow_html=True)

references = st.session_state.get('references', [])
if references:
    with st.container(border=True):
        st.subheader('Kos referensi terdekat')
        st.caption('Harga aktual dari dataset untuk kos dengan jarak, fasilitas, dan rating yang paling mendekati input Anda.')
        cards = []
        for item in references:
            name = html.escape(item['nama'])
            ac_text = html.escape(item['ac'])
            comparison = html.escape(item['comparison_display'])
            cards.append(
                '<div class="reference-card">'
                        f'<div class="reference-index">REFERENSI {len(cards)+1:02d}</div>'
                f'<div class="reference-name">{name}</div>'
                f'<div class="reference-price">{item["harga_display"]}</div>'
                f'<div class="reference-delta">{comparison}</div>'
                f'<div class="reference-detail">{item["jarak_km"]:g} km · {ac_text}<br>Rating {item["rating"]:g}/5</div>'
                '</div>'
            )
        st.markdown('<div class="reference-grid">' + ''.join(cards) + '</div>',
                    unsafe_allow_html=True)

st.markdown('''
<div class="summary-strip">
  <div class="summary-item"><span class="summary-value">30</span><span class="summary-label">data kos<br>untuk pelatihan</span></div>
  <div class="summary-item"><span class="summary-value">Ridge</span><span class="summary-label">metode<br>regresi</span></div>
  <div class="summary-item"><span class="summary-value">3 fitur</span><span class="summary-label">jarak, AC,<br>dan rating</span></div>
</div>''', unsafe_allow_html=True)

st.markdown('<footer class="site-footer"><span>© 2026 KosMadiun · Mini Proyek Sistem Cerdas</span></footer>',
            unsafe_allow_html=True)
