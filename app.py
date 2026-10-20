import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pytrends.request import TrendReq
import yfinance as yf
import time

st.set_page_config(page_title="BTC vs Google Trends", layout="wide")

st.title("₿ BTC vs. Google Trends")
st.caption("Einfache Version — auf Knopfdruck aktualisieren")

# Standard-Begriffe (weniger = schneller + weniger Rate-Limits)
DEFAULT_KEYWORDS = [
    "Bitcoin",
    "Ethereum",
    "Solana",
    "XRP",
    "Cryptocurrency"
]

with st.sidebar:
    st.header("Einstellungen")
    keywords_text = st.text_area(
        "Begriffe (eine pro Zeile)",
        "\n".join(DEFAULT_KEYWORDS),
        height=180
    )
    keywords = [k.strip() for k in keywords_text.splitlines() if k.strip()][:8]  # max 8
    
    timeframe = st.selectbox("Zeitraum", ["today 12-m", "today 5-y", "all"], index=0)
    refresh = st.button("🔄 Aktualisieren", type="primary")

@st.cache_data(ttl=3600)
def load_data(keywords, timeframe):
    pytrends = TrendReq(hl="en-US", tz=360, retries=2, backoff_factor=1)
    series = {}
    
    for i, kw in enumerate(keywords):
        try:
            pytrends.build_payload([kw], timeframe=timeframe, geo="")
            df = pytrends.interest_over_time()
            if not df.empty and kw in df.columns:
                s = df[kw]
                if "isPartial" in df.columns:
                    s = s[~df["isPartial"]]
                series[kw] = s
            time.sleep(1.5)
        except Exception as e:
            st.warning(f"Fehler bei {kw}: {e}")
    
    trends = pd.DataFrame(series) if series else pd.DataFrame()
    if trends.empty:
        return None, None
    
    # BTC Preis
    start = trends.index.min().strftime("%Y-%m-%d")
    btc = yf.download("BTC-USD", start=start, interval="1wk", progress=False)
    if isinstance(btc.columns, pd.MultiIndex):
        btc = btc.droplevel(1, axis=1)
    btc = btc[["Close"]].rename(columns={"Close": "BTC"})
    btc.index = btc.index.tz_localize(None)
    
    return trends, btc

if refresh or "data" not in st.session_state:
    with st.spinner("Lade Daten..."):
        trends, btc = load_data(tuple(keywords), timeframe)
        st.session_state.data = (trends, btc)

trends, btc = st.session_state.get("data", (None, None))

if trends is not None and not trends.empty:
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    colors = ["#f39c12", "#3498db", "#1abc9c", "#e74c3c", "#9b59b6", "#2ecc71", "#e67e22", "#95a5a6"]
    
    for i, col in enumerate(trends.columns):
        fig.add_trace(
            go.Scatter(
                x=trends.index, y=trends[col],
                name=col, stackgroup="one",
                line=dict(width=0, color=colors[i % len(colors)]),
                fillcolor=colors[i % len(colors)]
            ),
            secondary_y=False
        )
    
    if btc is not None and not btc.empty:
        btc_aligned = btc.reindex(trends.index, method="nearest")
        fig.add_trace(
            go.Scatter(
                x=btc_aligned.index, y=btc_aligned["BTC"],
                name="BTC Preis", mode="lines",
                line=dict(color="white", width=2.5)
            ),
            secondary_y=True
        )
    
    fig.update_layout(
        template="plotly_dark",
        height=650,
        legend=dict(orientation="h", y=1.1),
        hovermode="x unified"
    )
    fig.update_yaxes(title_text="Google Trends (gestapelt)", secondary_y=False)
    fig.update_yaxes(title_text="BTC (USD)", secondary_y=True, tickprefix="$")
    
    st.plotly_chart(fig, use_container_width=True)
    
    with st.expander("Daten anzeigen"):
        st.dataframe(trends.tail(15))
else:
    st.info("Klicke auf **Aktualisieren**, um den Chart zu laden.")

st.caption("Tipp: Nicht zu oft aktualisieren. Google Trends hat Rate-Limits.")
