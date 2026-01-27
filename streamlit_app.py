import streamlit as st
import requests
import json
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import re
import time
import datetime
import random
import urllib.parse
import html
import textwrap

# -----------------------------------------------------------------------------
# 0. DEPENDENCY CHECK
# -----------------------------------------------------------------------------
try:
    import feedparser
except ImportError:
    st.error("❌ 缺少必要组件：feedparser。请在 requirements.txt 中添加 'feedparser' 或运行 pip install feedparser。")
    st.stop()

# ================= 🔐 1. KEY MANAGEMENT =================
try:
    EXA_API_KEY = st.secrets.get("EXA_API_KEY", None)
    GOOGLE_API_KEY = st.secrets.get("GOOGLE_API_KEY", None)
    NEWS_API_KEY = st.secrets.get("NEWS_API_KEY", None)
    KEYS_LOADED = True
except:
    EXA_API_KEY = None
    GOOGLE_API_KEY = None
    NEWS_API_KEY = None
    KEYS_LOADED = False

if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

# ================= 🛠️ DEPENDENCY CHECK (EXA) =================
try:
    from exa_py import Exa
    EXA_AVAILABLE = True
except ImportError:
    EXA_AVAILABLE = False

# ================= 🕵️‍♂️ 2. SYSTEM CONFIGURATION =================
st.set_page_config(
    page_title="Be Holmes | Reality Check",
    page_icon="🕵️‍♂️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ================= 🧠 3. STATE MANAGEMENT =================
default_state = {
    "messages": [],
    "current_market": None,
    "search_candidates": [],     # Stores list of found markets
    "search_stage": "input",     # input -> selection -> analysis
    "user_news_text": "",
    "is_processing": False,
    "last_user_input": "",
    "news_category": "all",
    "market_sort": "volume"
}

for key, value in default_state.items():
    if key not in st.session_state:
        st.session_state[key] = value

# ================= 🎨 4. UI THEME (CRIMSON MODE) =================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;900&family=Plus+Jakarta+Sans:wght@400;700&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap');

    .stApp {
        background-image: linear-gradient(rgba(0, 0, 0, 0.92), rgba(20, 0, 0, 0.96)), 
                          url('https://upload.cc/i1/2026/01/20/s8pvXA.jpg');
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
        font-family: 'Inter', sans-serif;
    }
    
    .hero-title {
        font-family: 'Inter', sans-serif;
        font-weight: 700;
        font-size: 3.5rem; 
        color: #ffffff;
        text-align: center;
        letter-spacing: -2px;
        margin-bottom: 5px;
        padding-top: 2vh;
        text-shadow: 0 0 30px rgba(220, 38, 38, 0.6);
    }
    .hero-subtitle {
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 1rem;
        color: #9ca3af; 
        text-align: center;
        margin-bottom: 30px;
        font-weight: 400;
    }

    /* Fixed Time Zone Bar */
    .world-clock-bar {
        display: flex; 
        justify-content: space-between; 
        background: rgba(0,0,0,0.5); 
        padding: 8px 12px; 
        border-radius: 6px; 
        margin-bottom: 15px;
        border: 1px solid rgba(220, 38, 38, 0.2);
        font-family: 'JetBrains Mono', monospace;
    }
    .clock-item { font-size: 0.75rem; color: #9ca3af; display: flex; align-items: center; gap: 6px; }
    .clock-item b { color: #e5e7eb; font-weight: 700; }
    .clock-time { color: #f87171; }

    /* Category Tabs */
    div.stButton > button {
        background: linear-gradient(90deg, #991b1b 0%, #7f1d1d 100%) !important;
        color: white !important;
        border: 1px solid #b91c1c !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        transition: all 0.3s !important;
    }
    div.stButton > button:hover {
        background: linear-gradient(90deg, #dc2626 0%, #b91c1c 100%) !important;
        box-shadow: 0 0 15px rgba(220, 38, 38, 0.6) !important;
        border-color: #fca5a5 !important;
        transform: scale(1.02) !important;
    }

    /* News Cards */
    .news-grid-card {
        background: rgba(20, 0, 0, 0.6);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-left: 3px solid #dc2626;
        border-radius: 8px;
        padding: 15px;
        height: 100%;
        min-height: 140px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        transition: all 0.3s ease-in-out;
    }
    .news-grid-card:hover {
        background: rgba(40, 0, 0, 0.8);
        border-color: #ef4444;
        box-shadow: 0 0 15px rgba(220, 38, 38, 0.2);
        transform: translateY(-2px);
    }
    .news-meta {
        font-size: 0.7rem;
        color: #fca5a5;
        font-weight: 600;
        margin-bottom: 8px;
        display: flex;
        justify-content: space-between;
    }
    .news-body {
        font-size: 0.9rem;
        color: #e5e7eb;
        line-height: 1.4;
        font-weight: 500;
        margin-bottom: 15px;
        display: -webkit-box;
        -webkit-line-clamp: 3;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }
    
    /* Market Card Modern */
    .market-card-modern {
        background: rgba(255, 255, 255, 0.02);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 10px;
        transition: all 0.2s;
        cursor: pointer;
    }
    .market-card-modern:hover {
        border-color: #ef4444;
        background: rgba(40, 0, 0, 0.3);
        transform: translateY(-2px);
    }
    .market-head {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        margin-bottom: 10px;
    }
    .market-title-mod {
        font-size: 0.85rem;
        color: #e5e7eb;
        font-weight: 600;
        line-height: 1.3;
        flex: 1;
        margin-right: 10px;
    }
    .market-vol {
        font-size: 0.7rem;
        color: #9ca3af;
        white-space: nowrap;
        background: rgba(255,255,255,0.05);
        padding: 2px 6px;
        border-radius: 4px;
        font-family: 'JetBrains Mono', monospace;
    }
    .outcome-row {
        display: flex;
        justify-content: space-between;
        gap: 10px;
    }
    .outcome-box {
        flex: 1;
        padding: 8px;
        border-radius: 6px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-family: 'JetBrains Mono', monospace;
    }
    .outcome-box.yes { background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.2); }
    .outcome-box.no { background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.2); }
    .outcome-label { font-size: 0.75rem; font-weight: 600; }
    .outcome-price { font-size: 1rem; font-weight: 700; }
    .yes-color { color: #10b981; }
    .no-color { color: #ef4444; }

    /* Input Area */
    .stTextArea textarea {
        background-color: rgba(20, 0, 0, 0.6) !important;
        border: 1px solid #7f1d1d !important;
        color: white !important;
        border-radius: 12px !important;
        font-size: 1rem !important;
    }
    .stTextArea textarea:focus {
        border-color: #ef4444 !important;
        box-shadow: 0 0 10px rgba(220, 38, 38, 0.4) !important;
    }
    
    /* Analysis Card */
    .analysis-card {
        background: rgba(20, 0, 0, 0.8);
        border: 1px solid #7f1d1d;
        border-radius: 12px;
        padding: 20px;
        margin-top: 20px;
        margin-bottom: 20px;
    }
    
    /* Chat Input styling */
    .stChatInput input {
        background-color: rgba(20, 0, 0, 0.6) !important;
        color: white !important;
        border: 1px solid #7f1d1d !important;
    }

    /* Hub Button */
    .hub-btn {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        width: 100%;
        height: 70px;
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 10px;
        text-align: center;
        text-decoration: none;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        backdrop-filter: blur(5px);
        margin-bottom: 10px;
        cursor: pointer;
    }
    .hub-btn:hover {
        background: rgba(40, 0, 0, 0.6);
        border-color: #ef4444;
        transform: translateY(-3px);
        box-shadow: 0 5px 15px rgba(220, 38, 38, 0.3);
    }
    .hub-content { display: flex; flex-direction: column; align-items: center; }
    .hub-emoji { font-size: 1.4rem; line-height: 1.2; margin-bottom: 4px; filter: grayscale(0.2); }
    .hub-btn:hover .hub-emoji { filter: grayscale(0); transform: scale(1.1); transition: transform 0.2s;}
    .hub-text { 
        font-family: 'Inter', sans-serif;
        font-size: 0.8rem; 
        color: #d1d5db; 
        font-weight: 600; 
        letter-spacing: 0.5px;
    }
    .hub-btn:hover .hub-text { color: #ffffff; }
    
    /* Global Trends Buttons (Fixed) */
    .trend-row { display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 20px; justify-content: flex-start; }
    .trend-fixed-btn {
        background: rgba(220, 38, 38, 0.1);
        border: 1px solid rgba(220, 38, 38, 0.3);
        color: #fca5a5;
        padding: 8px 16px;
        border-radius: 6px;
        font-size: 0.85rem;
        font-weight: 600;
        text-decoration: none;
        display: flex;
        align-items: center;
        gap: 8px;
        transition: all 0.2s;
    }
    .trend-fixed-btn:hover {
        background: rgba(220, 38, 38, 0.4);
        color: white;
        border-color: #ef4444;
        transform: translateY(-2px);
    }
    .ex-link {
        font-size: 0.7rem; color: #6b7280; text-decoration: none; margin-top: 5px; display: block; text-align: right;
    }
    .ex-link:hover { color: #ef4444; }
</style>
""", unsafe_allow_html=True)

# ================= 🧠 5. LOGIC CORE =================

# --- 🔥 A. Crypto Prices (Extended List) ---
@st.cache_data(ttl=60)
def fetch_crypto_prices_v2():
    symbols = [
        "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", 
        "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "SHIBUSDT", "DOTUSDT", 
        "LINKUSDT", "TRXUSDT", "MATICUSDT", "LTCUSDT", "BCHUSDT", 
        "UNIUSDT", "NEARUSDT", "APTUSDT", "FILUSDT", "ICPUSDT",
        "PEPEUSDT", "WIFUSDT", "SUIUSDT", "FETUSDT"
    ]
    crypto_data = []
    try:
        url = "https://api.binance.com/api/v3/ticker/24hr"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            all_tickers = {t['symbol']: t for t in response.json()}
            for sym in symbols:
                if sym in all_tickers:
                    ticker = all_tickers[sym]
                    symbol_clean = sym.replace('USDT', '')
                    price = float(ticker['lastPrice'])
                    change_24h = float(ticker['priceChangePercent'])
                    volume = float(ticker['volume'])
                    
                    if price >= 1000: price_str = f"${price:,.0f}"
                    elif price >= 1: price_str = f"${price:,.2f}"
                    else: price_str = f"${price:.4f}"
                    
                    if volume >= 1000000: vol_str = f"{volume/1000000:.1f}M"
                    elif volume >= 1000: vol_str = f"{volume/1000:.1f}K"
                    else: vol_str = f"{volume:.0f}"
                    
                    crypto_data.append({
                        "symbol": symbol_clean,
                        "price": price_str,
                        "change": change_24h,
                        "volume": vol_str,
                        "trend": "up" if change_24h > 0 else "down"
                    })
    except: pass 
    if not crypto_data:
        crypto_data = [{"symbol": "BTC", "price": "$94,250", "change": 2.3, "volume": "25.5B", "trend": "up"}]
    return crypto_data

# --- 🔥 B. Categorized News Fetcher ---
@st.cache_data(ttl=300)
def fetch_categorized_news_v2():
    def fetch_rss(url, limit=20):
        items = []
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:limit]:
                time_display = "Recent"
                if hasattr(entry, 'published_parsed'):
                    try:
                        dt = datetime.datetime.fromtimestamp(time.mktime(entry.published_parsed))
                        diff = datetime.datetime.now() - dt
                        if diff.total_seconds() < 3600: time_display = f"{int(diff.total_seconds()/60)}m ago"
                        else: time_display = f"{int(diff.total_seconds()/3600)}h ago"
                    except: pass
                items.append({
                    "title": entry.title,
                    "source": entry.get("source", {}).get("title", "News"),
                    "link": entry.link,
                    "time": time_display
                })
        except: pass
        return items

    feeds = {
        "all": "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en",
        "politics": "https://rss.nytimes.com/services/xml/rss/nyt/Politics.xml",
        "tech": "https://techcrunch.com/feed/",
        "web3": "https://www.coindesk.com/arc/outboundfeeds/rss/"
    }
    return {k: fetch_rss(v, 30) for k, v in feeds.items()}

# --- 🔥 C. Polymarket Fetcher (UNIFIED & ROBUST) ---
def process_polymarket_event(event):
    """
    Core function to process ANY Polymarket event.
    Returns standardized data structure.
    """
    try:
        title = event.get('title', 'Untitled').strip()
        if not title: return None
        
        # 1. Sensitive Keyword Filter
        SENSITIVE_KEYWORDS = ["china", "chinese", "xi jinping", "taiwan", "ccp", "beijing", "hong kong", "communist"]
        if any(kw in title.lower() for kw in SENSITIVE_KEYWORDS): return None

        # 2. Status Filter
        if event.get('closed') is True: return None
        if not event.get('markets'): return None
        
        # 3. Find Main Market (Highest Volume)
        markets_list = event.get('markets', [])
        markets_list.sort(key=lambda x: float(x.get('volume', 0) or 0), reverse=True)
        m = markets_list[0]
        
        vol = float(m.get('volume', 0) or 0)
        if vol < 1000: return None # Filter Dead Markets
        
        if vol >= 1000000: vol_str = f"${vol/1000000:.1f}M"
        elif vol >= 1000: vol_str = f"${
