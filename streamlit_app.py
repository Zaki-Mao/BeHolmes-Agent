import streamlit as st
import requests
import json
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import re
import time
import datetime
import feedparser
import random
import urllib.parse

# ================= 🔐 0. KEY MANAGEMENT =================
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

# ================= 🛠️ DEPENDENCY CHECK =================
try:
    from exa_py import Exa
    EXA_AVAILABLE = True
except ImportError:
    EXA_AVAILABLE = False

# ================= 🕵️‍♂️ 1. SYSTEM CONFIGURATION =================
st.set_page_config(
    page_title="Be Holmes | Reality Check",
    page_icon="🕵️‍♂️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ================= 🧠 1.1 STATE MANAGEMENT =================
default_state = {
    "messages": [],
    "current_market": None,
    "news_category": "All", # 新增分类状态
    "search_results": [],
    "user_news_text": "",
    "is_processing": False
}

for key, value in default_state.items():
    if key not in st.session_state:
        st.session_state[key] = value

# ================= 🎨 2. UI THEME (CRIMSON/DARK MODE) =================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;900&family=JetBrains+Mono:wght@400;700&display=swap');

    /* Global Background */
    .stApp {
        background-image: linear-gradient(rgba(0, 0, 0, 0.92), rgba(20, 0, 0, 0.98)), 
                          url('https://upload.cc/i1/2026/01/20/s8pvXA.jpg');
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
        font-family: 'Inter', sans-serif;
    }
    
    /* Headers */
    .hero-title {
        font-family: 'Inter', sans-serif;
        font-weight: 800;
        font-size: 3rem; 
        color: #ffffff;
        text-align: center;
        letter-spacing: -2px;
        text-shadow: 0 0 40px rgba(220, 38, 38, 0.8);
        margin-top: 20px;
    }
    .section-header {
        font-size: 0.85rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        margin-bottom: 15px;
        padding-bottom: 8px;
        border-bottom: 1px solid rgba(220, 38, 38, 0.3);
        display: flex;
        align-items: center;
        gap: 8px;
        color: #ef4444;
    }

    /* 🔥 Google Trends Tags (Gradient) */
    .trend-container {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
        margin-bottom: 20px;
    }
    .trend-tag {
        padding: 5px 12px;
        border-radius: 4px;
        font-size: 0.8rem;
        font-weight: 600;
        color: white !important;
        text-decoration: none !important;
        transition: transform 0.2s;
        display: flex;
        align-items: center;
        gap: 6px;
    }
    .trend-tag:hover { transform: scale(1.05); box-shadow: 0 0 10px rgba(255,255,255,0.2); }
    .t-grad-1 { background: linear-gradient(135deg, #ef4444, #b91c1c); } /* Red */
    .t-grad-2 { background: linear-gradient(135deg, #ec4899, #be185d); } /* Pink */
    .t-grad-3 { background: linear-gradient(135deg, #8b5cf6, #6d28d9); } /* Purple */
    .trend-vol { font-size: 0.65rem; opacity: 0.8; background: rgba(0,0,0,0.3); padding: 1px 4px; border-radius: 3px; }

    /* 📰 News Cards */
    .news-card {
        background: rgba(255, 255, 255, 0.03);
        border-left: 2px solid #444;
        border-radius: 0 6px 6px 0;
        padding: 12px;
        height: 100%;
        min-height: 120px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        transition: all 0.3s;
    }
    .news-card:hover {
        background: rgba(255, 255, 255, 0.06);
        border-left-color: #ef4444;
    }
    .news-meta { font-size: 0.7rem; color: #9ca3af; display: flex; justify-content: space-between; margin-bottom: 6px; }
    .news-title { font-size: 0.9rem; font-weight: 500; color: #e5e7eb; line-height: 1.4; }
    .news-link-btn {
        display: block;
        margin-top: 10px;
        text-align: right;
        font-size: 0.75rem;
        color: #ef4444;
        text-decoration: none;
        font-weight: 600;
    }
    .news-link-btn:hover { text-decoration: underline; color: #fca5a5; }

    /* 💰 Polymarket Cards (Compact) */
    .poly-card {
        background: rgba(20, 20, 20, 0.6);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 0px; /* Managed by grid */
        height: 100%;
        transition: all 0.2s;
    }
    .poly-card:hover {
        border-color: #ef4444;
        background: rgba(40, 10, 10, 0.4);
    }
    .poly-head {
        display: flex;
        justify-content: space-between;
        margin-bottom: 8px;
        font-size: 0.7rem;
        color: #6b7280;
    }
    .poly-title {
        font-size: 0.85rem;
        font-weight: 600;
        color: #f3f4f6;
        line-height: 1.3;
        margin-bottom: 12px;
        height: 2.6em; /* Fixed height for 2 lines */
        overflow: hidden;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
    }
    .poly-bar {
        display: flex;
        height: 24px;
        border-radius: 4px;
        overflow: hidden;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.75rem;
        font-weight: 700;
    }
    .bar-yes {
        background: rgba(16, 185, 129, 0.2);
        color: #34d399;
        display: flex;
        align-items: center;
        padding-left: 6px;
        border-right: 1px solid rgba(0,0,0,0.5);
    }
    .bar-no {
        background: rgba(239, 68, 68, 0.2);
        color: #f87171;
        display: flex;
        align-items: center;
        justify-content: flex-end;
        padding-right: 6px;
        flex-grow: 1;
    }
    
    /* Footer Hub */
    .hub-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; }
    .hub-btn {
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.05);
        border-radius: 8px;
        padding: 10px;
        text-align: center;
        text-decoration: none;
        color: #9ca3af !important;
        transition: all 0.3s;
        display: flex;
        flex-direction: column;
        align-items: center;
    }
    .hub-btn:hover {
        background: rgba(255,255,255,0.08);
        border-color: #ef4444;
        color: white !important;
        transform: translateY(-2px);
    }
    .hub-emoji { font-size: 1.2rem; margin-bottom: 4px; }
    .hub-text { font-size: 0.7rem; font-weight: 600; text-transform: uppercase; }

    /* Input & Button Overrides */
    .stTextArea textarea { background: rgba(0,0,0,0.5) !important; border: 1px solid #333 !important; color: white !important; }
    .stTextArea textarea:focus { border-color: #ef4444 !important; }
    div.stButton > button {
        background: #b91c1c !important;
        color: white !important;
        border: none !important;
        width: 100%;
    }
    div.stButton > button:hover { background: #dc2626 !important; }
</style>
""", unsafe_allow_html=True)

# ================= 🧠 3. DATA FETCHING LOGIC =================

# --- 🔥 A. Real-Time Google Trends (with fallback) ---
@st.cache_data(ttl=3600)
def fetch_google_trends():
    url = "https://trends.google.com/trends/trendingsearches/daily/rss?geo=US"
    trends = []
    # User-Agent is crucial for Google
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    
    try:
        resp = requests.get(url, headers=headers, timeout=5)
        if resp.status_code == 200:
            feed = feedparser.parse(resp.content)
            for entry in feed.entries[:8]:
                traffic = "Hot"
                if hasattr(entry, 'ht_approx_traffic'):
                    traffic = entry.ht_approx_traffic
                trends.append({"name": entry.title, "vol": traffic})
    except: pass
    
    # Fallback if empty (prevent UI break)
    if not trends:
        trends = [{"name": "Bitcoin", "vol": "500K+"}, {"name": "AI", "vol": "200K+"}, {"name": "Nvidia", "vol": "100K+"}]
    return trends

# --- 🔥 B. News Fetcher (Category + Time Filter) ---
@st.cache_data(ttl=900) # 15 min cache
def fetch_news_by_category(category):
    news_items = []
    
    # 1. Build Query params based on Category
    params = {
        "language": "en",
        "pageSize": 60, # Fetch more to allow for filtering
        "apiKey": NEWS_API_KEY
    }
    
    if category == "Web3":
        url = "https://newsapi.org/v2/everything"
        params["q"] = "crypto OR bitcoin OR ethereum OR blockchain"
        params["sortBy"] = "publishedAt"
    elif category == "Politics":
        url = "https://newsapi.org/v2/top-headlines"
        params["category"] = "politics" # Sometimes works, otherwise use q
        params["country"] = "us"
    elif category == "Tech":
        url = "https://newsapi.org/v2/top-headlines"
        params["category"] = "technology"
    else: # All / General
        url = "https://newsapi.org/v2/top-headlines"
        params["category"] = "general"

    # 2. Try NewsAPI First
    if NEWS_API_KEY:
        try:
            resp = requests.get(url, params=params, timeout=5)
            data = resp.json()
            if data.get("status") == "ok":
                for art in data.get("articles", []):
                    # Filter [Removed]
                    if art['title'] == "[Removed]": continue
                    
                    # 🔥 Strict 24h Filter
                    pub_str = art.get("publishedAt")
                    time_ago = "Just now"
                    is_recent = True
                    
                    if pub_str:
                        try:
                            pub_dt = datetime.datetime.strptime(pub_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)
                            now_dt = datetime.datetime.now(datetime.timezone.utc)
                            diff = now_dt - pub_dt
                            hours = diff.total_seconds() / 3600
                            
                            if hours > 24: 
                                is_recent = False # Skip old news
                            elif hours < 1:
                                time_ago = f"{int(diff.total_seconds()/60)}m ago"
                            else:
                                time_ago = f"{int(hours)}h ago"
                        except: pass
                    
                    if is_recent:
                        news_items.append({
                            "title": art['title'],
                            "source": art['source']['name'],
                            "link": art['url'],
                            "time": time_ago
                        })
        except: pass

    # 3. Fallback to RSS if list is empty (e.g. API limit reached)
    if not news_items:
        rss_map = {
            "Web3": "https://www.coindesk.com/arc/outboundfeeds/rss/",
            "Tech": "https://techcrunch.com/feed/",
            "Politics": "https://rss.nytimes.com/services/xml/rss/nyt/Politics.xml",
            "All": "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en"
        }
        try:
            feed = feedparser.parse(rss_map.get(category, rss_map["All"]))
            for entry in feed.entries[:20]:
                news_items.append({
                    "title": entry.title,
                    "source": entry.get("source", {}).get("title", "RSS"),
                    "link": entry.link,
                    "time": "Recent"
                })
        except: pass
        
    return news_items[:20]

# --- 🔥 C. Polymarket Global Top Volume ---
@st.cache_data(ttl=60)
def fetch_top_polymarkets():
    # Fetch global top events by volume
    url = "https://gamma-api.polymarket.com/events?limit=20&sort=volume&order=desc&closed=false"
    markets = []
    
    try:
        resp = requests.get(url, timeout=5).json()
        if isinstance(resp, list):
            for event in resp:
                try:
                    # Get the main market (usually the first one)
                    m = event.get('markets', [])[0]
                    vol = float(m.get('volume', 0))
                    
                    # Decode prices
                    outcomes = json.loads(m.get('outcomes')) if isinstance(m.get('outcomes'), str) else m.get('outcomes')
                    prices = json.loads(m.get('outcomePrices')) if isinstance(m.get('outcomePrices'), str) else m.get('outcomePrices')
                    
                    # Only handle Binary (Yes/No) for clean UI
                    if len(outcomes) == 2 and len(prices) == 2:
                        yes_price = float(prices[0]) * 100
                        no_price = float(prices[1]) * 100
                        
                        # Format Volume ($10M, $500K)
                        if vol > 1000000: vol_str = f"${vol/1000000:.1f}M"
                        elif vol > 1000: vol_str = f"${vol/1000:.0f}K"
                        else: vol_str = f"${vol:.0f}"

                        markets.append({
                            "title": event.get('title'),
                            "vol_str": vol_str,
                            "vol_raw": vol,
                            "yes": int(yes_price),
                            "no": int(no_price),
                            "slug": event.get('slug')
                        })
                except: continue
    except: pass
    
    # Sort by Volume strictly descending
    markets.sort(key=lambda x: x['vol_raw'], reverse=True)
    return markets

# ================= 🖥️ 4. MAIN LAYOUT =================

# --- Header ---
st.markdown('<div class="hero-title">Be Holmes</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-subtitle">Narrative vs. Reality Engine</div>', unsafe_allow_html=True)

# --- Search Bar (Centered) ---
_, s_col, _ = st.columns([1, 6, 1])
with s_col:
    user_query = st.text_area("Analyze News", height=70, placeholder="Paste a headline to check reality...", label_visibility="collapsed")
    if st.button("⚖️ REALITY CHECK"):
        # (保持原有的 AI 分析逻辑，此处省略以节省篇幅，重点在 UI 更新)
        pass

st.markdown("<br>", unsafe_allow_html=True)

# --- Main Split Layout ---
col_left, col_right = st.columns([1, 1], gap="large")

# ================= 👈 LEFT COLUMN: TRENDS + NEWS =================
with col_left:
    # 1. Google Trends (Top)
    st.markdown('<div class="section-header">📈 LIVE SEARCH TRENDS</div>', unsafe_allow_html=True)
    trends = fetch_real_trends()
    
    # Use HTML for colorful tags with links
    trend_html = '<div class="trend-container">'
    gradients = ["t-grad-1", "t-grad-2", "t-grad-3"]
    
    for i, t in enumerate(trends):
        color_class = gradients[i % 3]
        safe_q = urllib.parse.quote(t['name'])
        trend_html += f"""
        <a href="https://www.google.com/search?q={safe_q}" target="_blank" class="trend-tag {color_class}">
            {t['name']} <span class="trend-vol">{t['vol']}</span>
        </a>
        """
    trend_html += '</div>'
    st.markdown(trend_html, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)

    # 2. News Feed Header & Filters
    c1, c2 = st.columns([1, 1])
    with c1:
        st.markdown('<div class="section-header" style="margin-bottom:0;">📡 GLOBAL WIRE (24H)</div>', unsafe_allow_html=True)
    with c2:
        # Category Filter Pills
        cat = st.radio("Category", ["All", "Web3", "Tech", "Politics"], horizontal=True, label_visibility="collapsed")
        if cat != st.session_state.news_category:
            st.session_state.news_category = cat
            # st.rerun() # Optional: rerun to refresh immediately

    # 3. News Grid (Dual Column)
    news_items = fetch_news_by_category(st.session_state.news_category)
    
    if not news_items:
        st.info("Scanning frequencies...")
    else:
        # Create 2-column layout for news cards
        for i in range(0, len(news_items), 2):
            row_cols = st.columns(2)
            # Card 1
            with row_cols[0]:
                item = news_items[i]
                st.markdown(f"""
                <div class="news-card">
                    <div class="news-meta">
                        <span>{item['source']}</span>
                        <span style="color:#ef4444">{item['time']}</span>
                    </div>
                    <div class="news-title">{item['title']}</div>
                    <a href="{item['link']}" target="_blank" class="news-link-btn">🔗 READ SOURCE</a>
                </div>
                """, unsafe_allow_html=True)
            
            # Card 2 (if exists)
            if i + 1 < len(news_items):
                with row_cols[1]:
                    item = news_items[i+1]
                    st.markdown(f"""
                    <div class="news-card">
                        <div class="news-meta">
                            <span>{item['source']}</span>
                            <span style="color:#ef4444">{item['time']}</span>
                        </div>
                        <div class="news-title">{item['title']}</div>
                        <a href="{item['link']}" target="_blank" class="news-link-btn">🔗 READ SOURCE</a>
                    </div>
                    """, unsafe_allow_html=True)
            
            st.markdown("<div style='margin-bottom:10px'></div>", unsafe_allow_html=True)

# ================= 👉 RIGHT COLUMN: POLYMARKET TOP VOL =================
with col_right:
    st.markdown('<div class="section-header">💰 GLOBAL PREDICTION MARKETS (BY VOLUME)</div>', unsafe_allow_html=True)
    
    top_markets = fetch_top_polymarkets()
    
    if not top_markets:
        st.info("Connecting to Polymarket...")
    else:
        # Create 2-column layout for markets
        for i in range(0, len(top_markets), 2):
            m_cols = st.columns(2)
            
            # Left Market Card
            with m_cols[0]:
                m = top_markets[i]
                st.markdown(f"""
                <a href="https://polymarket.com/event/{m['slug']}" target="_blank" style="text-decoration:none;">
                    <div class="poly-card">
                        <div class="poly-head">
                            <span>🔥 HOT</span>
                            <span style="color:#e5e7eb; font-weight:bold;">Vol: {m['vol_str']}</span>
                        </div>
                        <div class="poly-title">{m['title']}</div>
                        <div class="poly-bar">
                            <div class="bar-yes" style="width:{m['yes']}%">Yes {m['yes']}</div>
                            <div class="bar-no" style="width:{m['no']}%">{m['no']} No</div>
                        </div>
                    </div>
                </a>
                """, unsafe_allow_html=True)
                
            # Right Market Card (if exists)
            if i + 1 < len(top_markets):
                with m_cols[1]:
                    m = top_markets[i+1]
                    st.markdown(f"""
                    <a href="https://polymarket.com/event/{m['slug']}" target="_blank" style="text-decoration:none;">
                        <div class="poly-card">
                            <div class="poly-head">
                                <span>🔥 HOT</span>
                                <span style="color:#e5e7eb; font-weight:bold;">Vol: {m['vol_str']}</span>
                            </div>
                            <div class="poly-title">{m['title']}</div>
                            <div class="poly-bar">
                                <div class="bar-yes" style="width:{m['yes']}%">Yes {m['yes']}</div>
                                <div class="bar-no" style="width:{m['no']}%">{m['no']} No</div>
                            </div>
                        </div>
                    </a>
                    """, unsafe_allow_html=True)
            
            st.markdown("<div style='margin-bottom:10px'></div>", unsafe_allow_html=True)

# ================= 🌐 FOOTER: INTELLIGENCE HUB =================
st.markdown("---")
st.markdown('<div style="text-align:center; color:#6b7280; font-size:0.8rem; margin-bottom:20px; letter-spacing:2px;">🌐 GLOBAL INTELLIGENCE HUB</div>', unsafe_allow_html=True)

hub_data = [
    {"name": "Jin10", "icon": "🇨🇳", "url": "https://www.jin10.com/"},
    {"name": "WallStCN", "icon": "🇨🇳", "url": "https://wallstreetcn.com/live/global"},
    {"name": "Zaobao", "icon": "🇸🇬", "url": "https://www.zaobao.com.sg/realtime/world"},
    {"name": "SCMP", "icon": "🇭🇰", "url": "https://www.scmp.com/"},
    {"name": "Nikkei", "icon": "🇯🇵", "url": "https://asia.nikkei.com/"},
    {"name": "Bloomberg", "icon": "🇺🇸", "url": "https://www.bloomberg.com/"},
    {"name": "Reuters", "icon": "🇬🇧", "url": "https://www.reuters.com/"},
    {"name": "CoinDesk", "icon": "🪙", "url": "https://www.coindesk.com/"},
    {"name": "TechCrunch", "icon": "⚡", "url": "https://techcrunch.com/"},
    {"name": "Al Jazeera", "icon": "🇶🇦", "url": "https://www.aljazeera.com/"},
]

rows = [hub_data[i:i+5] for i in range(0, len(hub_data), 5)]
for row in rows:
    cols = st.columns(5)
    for i, item in enumerate(row):
        with cols[i]:
            st.markdown(f"""
            <a href="{item['url']}" target="_blank" class="hub-btn">
                <div class="hub-content">
                    <span class="hub-emoji">{item['icon']}</span>
                    <span class="hub-text">{item['name']}</span>
                </div>
            </a>
            """, unsafe_allow_html=True)

st.markdown("<br><br>", unsafe_allow_html=True)
