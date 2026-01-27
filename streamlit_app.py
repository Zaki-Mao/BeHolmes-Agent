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
    "first_visit": True,
    "last_search_query": "",
    "search_results": [],
    "show_market_selection": False,
    "selected_market_index": -1,
    "direct_analysis_mode": False,
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

# --- 🔥 C. Polymarket Fetcher (FILTERED) ---
@st.cache_data(ttl=60)
def fetch_polymarket_v5_simple(limit=60):
    try:
        # Fetch more to allow for filtering
        url = "https://gamma-api.polymarket.com/events?limit=200&closed=false"
        resp = requests.get(url, timeout=8).json()
        markets = []
        
        # 敏感词过滤 (Sensitive Keywords)
        SENSITIVE_KEYWORDS = [
            "china", "chinese", "xi jinping", "taiwan", "ccp", "beijing", 
            "hong kong", "communist", "pla", "scs", "south china sea"
        ]
        
        if isinstance(resp, list):
            for event in resp:
                try:
                    title = event.get('title', 'Untitled').strip()
                    if not title: continue
                    
                    # 1. 敏感词过滤 (Case insensitive)
                    title_lower = title.lower()
                    if any(kw in title_lower for kw in SENSITIVE_KEYWORDS):
                        continue

                    if not event.get('markets'): continue
                    m = event['markets'][0]
                    vol = float(m.get('volume', 0))
                    if vol <= 0: continue
                    
                    if vol >= 1000000: vol_str = f"${vol/1000000:.1f}M"
                    elif vol >= 1000: vol_str = f"${vol/1000:.0f}K"
                    else: vol_str = f"${vol:.0f}"
                    
                    markets.append({
                        "title": title,
                        "slug": event.get('slug', ''),
                        "volume": vol,
                        "vol_str": vol_str
                    })
                except: continue
        
        markets.sort(key=lambda x: x['volume'], reverse=True)
        return markets[:limit]
    except: return []

# --- 🔥 D. NEW AGENT LOGIC ---
def generate_keywords(user_text):
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        prompt = f"Extract 2-3 most critical keywords from this news to search on a prediction market. Return ONLY keywords separated by spaces. Input: {user_text}"
        resp = model.generate_content(prompt)
        return resp.text.strip()
    except: return user_text

def search_market_data(user_query):
    if not EXA_AVAILABLE or not EXA_API_KEY: return None
    try:
        exa = Exa(EXA_API_KEY)
        keywords = generate_keywords(user_query)
        search_resp = exa.search(
            f"site:polymarket.com {keywords}",
            num_results=3,
            type="neural",
            include_domains=["polymarket.com"]
        )
        for result in search_resp.results:
            match = re.search(r'polymarket\.com/event/([^/]+)', result.url)
            if match:
                slug = match.group(1)
                api_url = f"https://gamma-api.polymarket.com/events?slug={slug}"
                data = requests.get(api_url, timeout=5).json()
                if data and isinstance(data, list):
                    event = data[0]
                    m = event['markets'][0]
                    outcomes = json.loads(m.get('outcomes')) if isinstance(m.get('outcomes'), str) else m.get('outcomes')
                    prices = json.loads(m.get('outcomePrices')) if isinstance(m.get('outcomePrices'), str) else m.get('outcomePrices')
                    vol = float(m.get('volume', 0))
                    odds_str = []
                    for i, out in enumerate(outcomes):
                        if i < len(prices):
                            prob = float(prices[i]) * 100
                            odds_str.append(f"{out}: {prob:.1f}%")
                    return {
                        "title": event['title'],
                        "odds": " | ".join(odds_str[:4]),
                        "volume": f"${vol:,.0f}",
                        "slug": slug,
                        "url": f"https://polymarket.com/event/{slug}"
                    }
    except: pass
    return None

def analyze_with_agent(user_news, market_data):
    model = genai.GenerativeModel('gemini-2.5-flash')
    current_date = datetime.datetime.now().strftime("%Y-%m-%d")
    
    market_context = f"""
    ✅ **REAL-TIME POLYMARKET DATA FOUND**
    - Market: {market_data['title']}
    - Odds: {market_data['odds']}
    - Volume: {market_data['volume']}
    INSTRUCTION: Compare news claim against odds.
    """ if market_data else "❌ **NO DIRECT PREDICTION MARKET FOUND**. Rely on logical inference."

    system_prompt = f"""
    You are **Be Holmes**, a top-tier Hedge Fund Analyst.
    Current Date: {current_date}
    
    TARGET: Analyze news input for TRUTH and INVESTMENT ALPHA.
    
    {market_context}
    
    --- ANALYSIS PROTOCOL ---
    1. **REALITY AUDIT**: Assess source credibility and validate against Market Odds (if provided).
    2. **SECOND-ORDER THINKING**: If true, what is the ripple effect?
    3. **INVESTMENT TARGETS**: Identify Sectors, specific Tickers/Assets, and Direction.
    
    --- OUTPUT FORMAT (Markdown) ---
    ### 🎯 Reality Verdict: [Verdict]
    **Probability:** [0-100]%
    *(Justification)*
    
    ### 🕵️‍♂️ Deep Dive
    [Professional breakdown]
    
    ### 🚀 Investment Signals (Alpha)
    * **📈 Bullish / Long:**
        * **Sectors:** [List]
        * **Tickers:** [List] - *Why*
    * **📉 Bearish / Short:**
        * **Assets:** [List]
        * **Risk:** [Brief risk]
    """
    
    messages = [
        {"role": "user", "parts": [system_prompt]},
        {"role": "user", "parts": [f"News Input: {user_news}"]}
    ]
    try:
        response = model.generate_content(messages)
        return response.text
    except Exception as e:
        return f"Agent Analysis Failed: {str(e)}"

# ================= 🖥️ 6. MAIN LAYOUT =================

# --- Header ---
st.markdown('<div class="hero-title">Be Holmes</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-subtitle">Narrative vs. Reality Engine</div>', unsafe_allow_html=True)

# --- Search Bar ---
_, s_mid, _ = st.columns([1, 6, 1])
with s_mid:
    input_val = st.session_state.get("user_news_text", "")
    user_query = st.text_area("Analyze News", value=input_val, height=70, placeholder="Paste a headline (e.g., 'Unitree robot on Spring Festival Gala')...", label_visibility="collapsed")
    
    if st.button("⚖️ Reality Check", use_container_width=True):
        if user_query:
            st.session_state.is_processing = True
            st.session_state.messages = [] 
            
            with st.spinner("🕵️‍♂️ Searching Prediction Markets..."):
                market_data = search_market_data(user_query)
                st.session_state.current_market = market_data
            
            with st.spinner("🧠 Generating Alpha Signals..."):
                analysis_text = analyze_with_agent(user_query, market_data)
                st.session_state.messages.append({"role": "assistant", "content": analysis_text})
                
            st.session_state.is_processing = False
            st.rerun()

st.markdown("<br>", unsafe_allow_html=True)

if not st.session_state.messages:
    col_news, col_markets = st.columns([1, 1], gap="large")
    
    # === LEFT: News Feed ===
    with col_news:
        st.markdown("""
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px; border-bottom:1px solid rgba(220,38,38,0.3); padding-bottom:8px;">
            <div style="font-size:0.9rem; font-weight:700; color:#ef4444; letter-spacing:1px;">📡 LIVE NEWS STREAM</div>
            <div style="font-size:0.7rem; color:#ef4444;">● LIVE</div>
        </div>
        """, unsafe_allow_html=True)

        trend_html = """
        <div class="trend-row">
            <a href="https://trends.google.com/trending?geo=US" target="_blank" class="trend-fixed-btn">📈 Google Trends</a>
            <a href="https://twitter.com/explore/tabs/trending" target="_blank" class="trend-fixed-btn">🐦 Twitter Trends</a>
            <a href="https://www.jin10.com/" target="_blank" class="trend-fixed-btn">⚡ Jin10 Data</a>
            <a href="https://www.bloomberg.com/" target="_blank" class="trend-fixed-btn">📊 Bloomberg</a>
            <a href="https://www.reddit.com/r/all/" target="_blank" class="trend-fixed-btn">🤖 Reddit</a>
        </div>
        """
        st.markdown(trend_html, unsafe_allow_html=True)

        cat_cols = st.columns(4)
        cats = ["all", "politics", "web3", "tech"]
        labels = {"all": "🌐 All", "politics": "🏛️ Politics", "web3": "₿ Web3", "tech": "🤖 Tech"}
        for i, c in enumerate(cats):
            if cat_cols[i].button(labels[c], key=c, use_container_width=True):
                st.session_state.news_category = c
                st.rerun()

        @st.fragment(run_every=1)
        def render_news_feed():
            now_utc = datetime.datetime.now(datetime.timezone.utc)
            t_nyc = (now_utc - datetime.timedelta(hours=5)).strftime("%H:%M")
            t_lon = now_utc.strftime("%H:%M")
            t_abd = (now_utc + datetime.timedelta(hours=4)).strftime("%H:%M")
            t_bjs = (now_utc + datetime.timedelta(hours=8)).strftime("%H:%M")
            
            st.markdown(f"""
<div class="world-clock-bar">
    <span class="clock-item"><b>NYC</b> <span class="clock-time">{t_nyc}</span></span>
    <span class="clock-item"><b>LON</b> <span class="clock-time">{t_lon}</span></span>
    <span class="clock-item"><b>ABD</b> <span class="clock-time">{t_abd}</span></span>
    <span class="clock-item"><b>BJS</b> <span class="clock-time" style="color:#ef4444">{t_bjs}</span></span>
</div>
""", unsafe_allow_html=True)

            if st.session_state.news_category == "web3":
                data = fetch_crypto_prices_v2()
                if data:
                    rows = [data[i:i+2] for i in range(0, len(data), 2)]
                    for row in rows:
                        cols = st.columns(2)
                        for i, coin in enumerate(row):
                            color = "#10b981" if coin['trend'] == "up" else "#ef4444"
                            cols[i].markdown(f"""
                            <div style="background:rgba(0,0,0,0.4); border:1px solid rgba(255,255,255,0.1); border-left:3px solid {color}; border-radius:8px; padding:12px; margin-bottom:8px;">
                                <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
                                    <span style="color:#e5e7eb; font-weight:700; font-size:0.9rem;">{coin['symbol']}</span>
                                    <span style="color:{color}; font-size:0.85rem;">{coin['change']:.2f}%</span>
                                </div>
                                <div style="display:flex; justify-content:space-between; align-items:center;">
                                    <span style="color:#fbbf24; font-weight:700; font-family:'JetBrains Mono'; font-size:1rem;">{coin['price']}</span>
                                    <a href="https://www.binance.com/en/trade/{coin['symbol']}_USDT" target="_blank" style="color:#ef4444; font-size:0.7rem; text-decoration:none; border:1px solid rgba(220,38,38,0.3); padding:2px 6px; border-radius:4px;">Trade</a>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                else:
                    st.info("Loading crypto data...")
            else:
                all_news = fetch_categorized_news_v2()
                news_list = all_news.get(st.session_state.news_category, all_news['all'])
                if news_list:
                    rows = [news_list[i:i+2] for i in range(0, min(len(news_list), 24), 2)]
                    for row in rows:
                        cols = st.columns(2)
                        for i, news in enumerate(row):
                            cols[i].markdown(f"""
                            <div class="news-grid-card">
                                <div>
                                    <div class="news-meta"><span>{news['source']}</span><span style="color:#ef4444">{news['time']}</span></div>
                                    <div class="news-body">{news['title']}</div>
                                </div>
                                <a href="{news['link']}" target="_blank" style="text-decoration:none; color:#ef4444; font-size:0.8rem; font-weight:600; text-align:right; display:block; margin-top:10px;">🔗 Read Source</a>
                            </div>
                            """, unsafe_allow_html=True)
                else:
                    st.info("No news available.")
        render_news_feed()

    # === RIGHT: Polymarket (Top Volume Only + Filtered) ===
    with col_markets:
        st.markdown('<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px; border-bottom:1px solid rgba(220,38,38,0.3); padding-bottom:8px;"><span style="font-size:0.9rem; font-weight:700; color:#ef4444;">💰 PREDICTION MARKETS (TOP VOLUME)</span></div>', unsafe_allow_html=True)
        
        sc1, sc2 = st.columns(2)
        if sc1.button("💵 Volume", use_container_width=True): st.session_state.market_sort = "volume"
        if sc2.button("🔥 Activity", use_container_width=True): st.session_state.market_sort = "active"
        
        # 🔥 UPDATED: Request 60 items
        markets = fetch_polymarket_v5_simple(60)
        
        if markets:
            rows = [markets[i:i+2] for i in range(0, len(markets), 2)]
            for row in rows:
                cols = st.columns(2)
                for i, m in enumerate(row):
                    cols[i].markdown(f"""
                    <a href="https://polymarket.com/event/{m['slug']}" target="_blank" style="text-decoration:none;">
                        <div class="market-card-modern">
                            <div class="market-head">
                                <div class="market-title-mod">{m['title']}</div>
                                <div class="market-vol">{m['vol_str']}</div>
                            </div>
                        </div>
                    </a>
                    """, unsafe_allow_html=True)
        else:
            st.info("Loading markets...")

else:
    # Analysis View
    st.markdown("---")
    if st.session_state.current_market:
        m = st.session_state.current_market
        st.markdown(f"""
        <div style="background:rgba(20,0,0,0.8); border-left:4px solid #ef4444; padding:15px; border-radius:8px; margin-bottom:20px;">
            <div style="font-size:0.8rem; color:#9ca3af; text-transform:uppercase;">🎯 Live Prediction Market Found</div>
            <div style="font-size:1.2rem; color:#e5e7eb; font-weight:bold; margin-top:5px;">{m['title']}</div>
            <div style="display:flex; justify-content:space-between; margin-top:10px; align-items:center;">
                <div style="font-family:'JetBrains Mono'; color:#ef4444; font-weight:700;">{m['odds']}</div>
                <div style="color:#6b7280; font-size:0.8rem;">Vol: {m['volume']}</div>
            </div>
            <a href="{m['url']}" target="_blank" style="display:inline-block; margin-top:10px; color:#fca5a5; font-size:0.8rem; text-decoration:none;">🔗 View on Polymarket</a>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="background:rgba(255,255,255,0.05); padding:10px; border-radius:8px; margin-bottom:20px; text-align:center; color:#6b7280; font-size:0.8rem;">
            No direct betting market found for this specific headline. Using AI logical inference.
        </div>
        """, unsafe_allow_html=True)

    for msg in st.session_state.messages:
        if msg['role'] == 'assistant':
            st.markdown(f"<div class='analysis-card'>{msg['content']}</div>", unsafe_allow_html=True)
            
    if st.button("⬅️ Back"):
        st.session_state.messages = []
        st.rerun()

# ================= 🌐 7. FOOTER =================
if not st.session_state.messages:
    st.markdown("---")
    st.markdown('<div style="text-align:center; color:#9ca3af; margin:25px 0; font-size:0.8rem; font-weight:700;">🌐 GLOBAL INTELLIGENCE HUB</div>', unsafe_allow_html=True)
    
    links = [
        {"n": "Jin10", "u": "https://www.jin10.com/", "i": "🇨🇳"},
        {"n": "WallStCN", "u": "https://wallstreetcn.com/live/global", "i": "🇨🇳"},
        {"n": "Zaobao", "u": "https://www.zaobao.com.sg/realtime/world", "i": "🇸🇬"},
        {"n": "SCMP", "u": "https://www.scmp.com/", "i": "🇭🇰"},
        {"n": "Nikkei", "u": "https://asia.nikkei.com/", "i": "🇯🇵"},
        {"n": "Bloomberg", "u": "https://www.bloomberg.com/", "i": "🇺🇸"},
        {"n": "Reuters", "u": "https://www.reuters.com/", "i": "🇬🇧"},
        {"n": "TechCrunch", "u": "https://techcrunch.com/", "i": "🇺🇸"},
        {"n": "CoinDesk", "u": "https://www.coindesk.com/", "i": "🪙"},
        {"n": "Al Jazeera", "u": "https://www.aljazeera.com/", "i": "🇶🇦"},
    ]
    
    rows = [links[i:i+5] for i in range(0, len(links), 5)]
    for row in rows:
        cols = st.columns(5)
        for i, l in enumerate(row):
            cols[i].markdown(f"""
            <a href="{l['u']}" target="_blank" class="hub-btn">
                <div class="hub-content"><span class="hub-emoji">{l['i']}</span><span class="hub-text">{l['n']}</span></div>
            </a>
            """, unsafe_allow_html=True)
    st.markdown("<br><br>", unsafe_allow_html=True)
