"""Streamlit front end for the Google Maps Scraper Kit.

Run locally:      pip install -r app/requirements.txt && streamlit run app/streamlit_app.py
Streamlit Cloud:  main file app/streamlit_app.py; set APP_PASSWORD in the app's Secrets.

It starts the kit's own engine (scripts/engine.py), runs scripts/scrape.py with the form's options and
shows the table with a download button. Scraped values are third-party text: shown as data only.
"""
import hmac, io, json, os, re, subprocess, sys, tempfile, time, urllib.parse, urllib.request
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable
st.set_page_config(page_title="MC - Buscador de Leads por Geolocalidade", page_icon="📍", layout="wide")


def password():
    """Gate the app when APP_PASSWORD is set (Streamlit secrets or environment)."""
    try:
        expected = st.secrets.get("APP_PASSWORD", "")
    except Exception:  # no secrets file at all
        expected = ""
    expected = expected or os.environ.get("APP_PASSWORD", "")
    if not expected or st.session_state.get("auth"):
        return True
    pw = st.text_input("Senha", type="password")
    if pw and hmac.compare_digest(pw, expected):
        st.session_state.auth = True
        st.rerun()
    elif pw:
        st.error("Senha incorreta.")
    return False


def engine(cmd):
    r = subprocess.run([PY, "scripts/engine.py", cmd], cwd=ROOT, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=600)
    return r.returncode, (r.stdout + r.stderr).strip()


@st.cache_resource(show_spinner="Iniciando o motor (primeira vez pode levar ~1 min)...")
def ensure_engine():
    code, out = engine("status")
    if "✓ Running" in out:
        return out
    code, out = engine("start")
    return engine("status")[1] or out


UA = "google-maps-scraper-kit-streamlit/1.0 (+https://github.com/Mahanaicoach/google-maps-scraper-kit)"


def _get_json(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=20) as r:
        return json.loads(r.read())


@st.cache_data(ttl=7 * 24 * 3600, show_spinner=False)
def geocode(place, country):
    """Place name -> ("lat", "lon") or None. Streamlit Cloud shares its IP with many apps, so
    OpenStreetMap's Nominatim often answers 429 there: retry once, then fall back to Photon (also
    OpenStreetMap data, free, no key). Cached, so the same place is looked up once a week."""
    q = {"format": "json", "limit": 1, "q": place}
    if country:
        q["countrycodes"] = country.lower()
    for wait in (0, 2):
        time.sleep(wait)
        try:
            hits = _get_json("https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(q))
            if hits:
                return str(hits[0]["lat"]), str(hits[0]["lon"])
            break  # answered, nothing found: Photon may still know it
        except Exception:
            pass
    try:
        feats = _get_json("https://photon.komoot.io/api/?" + urllib.parse.urlencode({"q": place, "limit": 5}))
        feats = feats.get("features", [])
        if country:  # prefer a hit in the chosen country
            feats = [f for f in feats if f.get("properties", {}).get("countrycode", "").lower() == country.lower()] or feats
        if feats:
            lon, lat = feats[0]["geometry"]["coordinates"][:2]
            return str(lat), str(lon)
    except Exception:
        pass
    return None


def parse_coords(text):
    """ "-23.55, -46.63" (as Google Maps copies it on a right-click) -> ("-23.55", "-46.63") or None."""
    m = re.fullmatch(r"\s*(-?\d{1,2}(?:\.\d+)?)\s*[,; ]\s*(-?\d{1,3}(?:\.\d+)?)\s*", text or "")
    if m and abs(float(m[1])) <= 90 and abs(float(m[2])) <= 180:
        return m[1], m[2]
    return None


if not password():
    st.stop()

st.title("📍 MC - Buscador de Leads por Geolocalidade")
st.caption("Raspa listagens do Google Maps e devolve nome, telefone, email, site, categoria, endereço, "
           "nota e avaliações. Uso pesado pode fazer o Google limitar o IP temporariamente.")

status = ensure_engine()
if "✓ Running" not in status:
    st.error("O motor não iniciou.")
    st.code(status)
    if st.button("Tentar de novo"):
        ensure_engine.clear()
        st.rerun()
    st.stop()

with st.form("scrape"):
    c1, c2 = st.columns([2, 1])
    keyword = c1.text_input("Busca", placeholder="dentistas em Curitiba")
    city = c2.text_input("Cidade (opcional)", placeholder="Curitiba, PR")
    coords_txt = st.text_input("Coordenadas (opcional)", placeholder="-23.5505, -46.6333",
                               help="No Google Maps, clique com o botão direito no local e clique nos números "
                                    "do topo do menu para copiar. Com elas, a cidade não precisa ser localizada.")
    c3, c4, c5, c6 = st.columns(4)
    depth = c3.slider("Profundidade (~20 por passo)", 1, 6, 2)
    lang = c4.text_input("Idioma", "pt", max_chars=2)
    country = c5.text_input("País", "br", max_chars=2)
    max_time = c6.number_input("Tempo máximo (s)", 60, 3600, 600, step=60)
    c7, c8, c9, c10 = st.columns(4)
    emails = c7.checkbox("Buscar emails nos sites", True)
    socials = c8.checkbox("Redes sociais", True)
    no_website = c9.checkbox("Só quem NÃO tem site")
    has_phone = c10.checkbox("Só com telefone")
    c11, c12, c13 = st.columns(3)
    min_rating = c11.number_input("Nota mínima (0 = sem filtro)", 0.0, 5.0, 0.0, step=0.5)
    min_reviews = c12.number_input("Mín. de avaliações (0 = sem filtro)", 0, 100000, 0)
    grid = c13.number_input("Grade N×N (0 = desligada, precisa de cidade)", 0, 10, 0)
    go = st.form_submit_button("🔎 Raspar", type="primary")

if go:
    if not keyword.strip():
        st.warning("Digite uma busca.")
        st.stop()
    if grid and not city.strip():
        st.warning("A grade precisa de uma cidade.")
        st.stop()
    coords = parse_coords(coords_txt)
    if coords_txt.strip() and not coords:
        st.warning("Coordenadas inválidas. Use o formato -23.5505, -46.6333")
        st.stop()
    if not grid and not coords:  # the grid needs scrape.py's bounding box, so it geocodes there
        with st.spinner("Localizando..."):
            coords = geocode(city.strip() or keyword.strip(), country.strip())
        if not coords:
            st.error("Não consegui localizar o lugar (o serviço de mapas está ocupado ou não achou). "
                     "Preencha a Cidade com algo como \"Jundiaí, SP\", ou cole as Coordenadas do Google Maps.")
            st.stop()
    if depth >= 5 or grid:
        st.info("Busca grande: pode levar vários minutos e aumenta o risco de limite de IP pelo Google.")
    out = Path(tempfile.mkdtemp()) / "leads.csv"
    args = [PY, "scripts/scrape.py", keyword.strip(), *(coords or ()), "--depth", str(depth), "--lang", lang.strip() or "pt",
            "--max-time", str(int(max_time)), "--out", str(out)]
    if grid:  # with coordinates, --city would make scrape.py geocode again
        args += ["--city", city.strip()]
    if country.strip():
        args += ["--country", country.strip()]
    if not emails:
        args.append("--no-email")
    if not socials:
        args.append("--no-socials")
    if no_website:
        args.append("--no-website")
    if has_phone:
        args.append("--has-phone")
    if min_rating:
        args += ["--min-rating", str(min_rating)]
    if min_reviews:
        args += ["--min-reviews", str(int(min_reviews))]
    if grid:
        args += ["--grid", str(int(grid))]

    log_box, lines, start = st.empty(), [], time.time()
    with st.spinner("Raspando..."):
        p = subprocess.Popen(args, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                             encoding="utf-8", errors="replace", env=dict(os.environ, PYTHONUNBUFFERED="1"))
        for raw in p.stdout:
            for line in raw.replace("\r", "\n").splitlines():
                if line.strip() and not line.startswith("  •"):  # status lines only; the table shows the rows
                    lines.append(line)
                    log_box.code("\n".join(lines[-15:]))
        p.wait()
    took = int(time.time() - start)

    if out.exists() and out.stat().st_size:
        df = pd.read_csv(out, encoding="utf-8-sig", dtype=str).fillna("")
        st.session_state.result = (df, keyword.strip())
        st.success(f"{len(df)} lugares em {took} s.")
    else:
        st.session_state.pop("result", None)
        st.error(f"Nenhum resultado (código {p.returncode}). Veja o log acima.")

if "result" in st.session_state:
    df, kw = st.session_state.result
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Lugares", len(df))
    for col, label, name in ((m2, "Com telefone", "phone"), (m3, "Com email", "emails"), (m4, "Com site", "website")):
        col.metric(label, int((df[name] != "").sum()) if name in df else 0)
    st.dataframe(df, width="stretch", hide_index=True)
    safe = "".join(ch if ch.isalnum() else "-" for ch in kw.lower()).strip("-")[:40] or "leads"
    # on_click="ignore": no rerun on click, so the file is still there when the browser fetches it
    d1, d2, _ = st.columns([1, 1, 3])
    xlsx = io.BytesIO()
    df.to_excel(xlsx, index=False, sheet_name="Leads")
    d1.download_button("⬇️ Baixar Excel (.xlsx)", xlsx.getvalue(), file_name=f"leads-{safe}.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                       on_click="ignore", type="primary", width="stretch")
    # Excel in Portuguese expects ";" between columns; a UTF-8 BOM keeps the accents
    d2.download_button("⬇️ Baixar CSV", df.to_csv(index=False, sep=";").encode("utf-8-sig"),
                       file_name=f"leads-{safe}.csv", mime="text/csv", on_click="ignore",
                       width="stretch")
    st.caption("Telefones e emails são dados pessoais: guarde e use conforme a LGPD.")
