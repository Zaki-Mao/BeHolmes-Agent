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
    page_title="Be Holmes | News Analysis",
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

# --- 🔥 C. Polymarket Fetcher (ENHANCED - supports Sub-markets & Liquidity) ---
def process_polymarket_event(event):
    """
    Core function to process ANY Polymarket event.
    Returns standardized data structure tailored for generate_market_context.
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
        
        # --- NEW: Extract Data for Context Generator ---
        # Liquidity
        liquidity = float(m.get('liquidity', 0) or 0)
        
        # 24h Price Change
        change_24h = float(m.get('oneDayPriceChange', 0) or m.get('priceChange24h', 0) or 0)

        # Volume String Formatting
        if vol >= 1000000: vol_str = f"${vol/1000000:.1f}M"
        elif vol >= 1000: vol_str = f"${vol/1000:.0f}K"
        else: vol_str = f"${vol:.0f}"

        # 4. Parse Odds (Robust)
        outcomes = json.loads(m.get('outcomes')) if isinstance(m.get('outcomes'), str) else m.get('outcomes')
        prices = json.loads(m.get('outcomePrices')) if isinstance(m.get('outcomePrices'), str) else m.get('outcomePrices')
        
        outcome_data = []
        if outcomes and prices:
            for i, out in enumerate(outcomes):
                if i < len(prices):
                    try:
                        # Price is usually 0.72 in API, convert to percentage for list, keep decimal for context
                        raw_price = float(prices[i]) 
                        prob_percent = raw_price * 100
                        outcome_data.append((str(out), prob_percent, raw_price))
                    except: continue
        
        if not outcome_data: return None

        # Sort by Probability (High to Low)
        outcome_data.sort(key=lambda x: x[1], reverse=True)
        
        # Get Top Probability (0.0 - 1.0 format) for the Generator
        top_prob_decimal = outcome_data[0][2] 
        
        # Format Top 3 Odds for Display
        top_odds = [f"{o}: {p:.1f}%" for o, p, r in outcome_data[:3]]
        odds_str = " | ".join(top_odds)

        # 5. Extract Details for All Sub-Markets (V1.3 UPGRADE)
        all_sub_markets = []
        # We process the top 6 sub-markets to provide rich context
        for sub_m in markets_list[:6]:
            try:
                # Basic sub-market data
                q_text = sub_m.get('question', title)
                sub_out = json.loads(sub_m.get('outcomes')) if isinstance(sub_m.get('outcomes'), str) else sub_m.get('outcomes')
                sub_pri = json.loads(sub_m.get('outcomePrices')) if isinstance(sub_m.get('outcomePrices'), str) else sub_m.get('outcomePrices')
                sub_vol = float(sub_m.get('volume', 0) or 0)
                
                # Determine top outcome for this sub-market
                best_opt = ""
                best_price = 0.0
                if sub_out and sub_pri:
                    temp_ops = []
                    for i, o in enumerate(sub_out):
                        if i < len(sub_pri):
                            try:
                                p_val = float(sub_pri[i])
                                temp_ops.append((o, p_val))
                            except: continue
                    temp_ops.sort(key=lambda x: x[1], reverse=True)
                    if temp_ops:
                        best_opt = temp_ops[0][0]
                        best_price = temp_ops[0][1]

                # Structure for UI
                sub_data = {
                    "question": q_text,
                    "volume": sub_vol,
                    "type": "binary" if len(sub_out) == 2 else "multiple",
                    "options": [],
                    # Extra fields for Context Generator
                    "top_option": best_opt,
                    "top_price": best_price
                }
                
                # Fill options for UI
                if len(sub_out) == 2 and "Yes" in sub_out and "No" in sub_out:
                    y_idx = sub_out.index("Yes")
                    n_idx = sub_out.index("No")
                    sub_data['yes_price'] = float(sub_pri[y_idx]) * 100 if y_idx < len(sub_pri) else 0
                    sub_data['no_price'] = float(sub_pri[n_idx]) * 100 if n_idx < len(sub_pri) else 0
                else:
                    for i, o in enumerate(sub_out):
                        if i < len(sub_pri):
                            sub_data['options'].append({
                                "option": str(o), 
                                "price": float(sub_pri[i]) * 100
                            })
                all_sub_markets.append(sub_data)
            except: continue

        # Return standardized dict matching generate_market_context requirements
        return {
            "title": title,
            "slug": event.get('slug', ''),
            "volume": vol,
            "vol_str": vol_str, # This is the formatted string (e.g. $50M)
            "odds": odds_str,
            "url": f"https://polymarket.com/event/{event.get('slug', '')}",
            "markets": all_sub_markets,
            
            # Fields specifically for generate_market_context:
            "probability": top_prob_decimal, # 0.72
            "liquidity": liquidity,          # 150000.0
            "change_24h": change_24h         # 0.05
        }
    except: return None

@st.cache_data(ttl=60)
def fetch_polymarket_v5_simple(limit=60, sort_mode='volume'):
    """
    Fetch Top Markets for Homepage.
    Supports server-side sorting with robust fallback.
    """
    try:
        base_url = "https://gamma-api.polymarket.com/events?closed=false"
        
        # 1. Attempt API Sorting (Try sorting by volume or liquidity)
        if sort_mode == 'volume':
            # Try getting top liquidity/volume events (API dependent)
            # Increased limit to 500 to catch old whales if API sort fails
            api_url = f"{base_url}&limit=500" 
        else:
            # Active/Trending
            api_url = f"{base_url}&limit=50"

        resp = requests.get(api_url, timeout=12) 
        
        # Fallback if API fails
        if resp.status_code != 200:
            return []

        data = resp.json()
        markets = []
        
        if isinstance(data, list):
            for event in data:
                market_data = process_polymarket_event(event)
                if market_data:
                    markets.append(market_data)
        
        # 2. Strong Local Sort (Crucial for "Volume" view)
        if sort_mode == 'volume':
            markets.sort(key=lambda x: x['volume'], reverse=True)
        # 'active' usually implies the default API return order (Trending)
            
        return markets[:limit]
    except Exception as e:
        return []

def search_market_data_list(user_query):
    """Search Markets by Keyword - REVERTED TO OLD LOGIC"""
    if not EXA_AVAILABLE or not EXA_API_KEY: return []
    candidates = []
    try:
        exa = Exa(EXA_API_KEY)
        keywords = generate_keywords(user_query) 
        
        # INCREASED num_results back to 25 to cast a wider net
        search_resp = exa.search(
            f"site:polymarket.com {keywords}",
            num_results=25, 
            type="neural",
            include_domains=["polymarket.com"]
        )
        
        seen_slugs = set()
        for result in search_resp.results:
            match = re.search(r'polymarket\.com/event/([^/]+)', result.url)
            if match:
                slug = match.group(1).split('?')[0] # Basic cleaning
                if slug in seen_slugs: continue
                seen_slugs.add(slug)
                
                api_url = f"https://gamma-api.polymarket.com/events?slug={slug}"
                data = requests.get(api_url, timeout=5).json()
                
                if data and isinstance(data, list):
                    market_data = process_polymarket_event(data[0])
                    if market_data:
                        candidates.append(market_data)
    except: pass
    return candidates # Return all found

# --- 🔥 D. AGENT LOGIC (REVERTED KEYWORDS + NEW CONTEXT) ---
def generate_keywords(user_text):
    # REVERTED TO OLD (WORKING) PROMPT
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        prompt = f"Extract 2-3 most critical keywords from this news to search on a prediction market. **CRITICAL: Translate keywords to English if input is Chinese.** Return ONLY keywords separated by spaces. Input: {user_text}"
        resp = model.generate_content(prompt)
        return resp.text.strip()
    except: return user_text

def is_chinese_input(text):
    return bool(re.search(r'[\u4e00-\u9fff]', text))

def generate_market_context(market_data, is_cn=True):
    """
    根据Polymarket数据，生成增强版的市场背景解读 (DeepSeek Logic).
    """
    if not market_data:
        # Fallback if no market data is selected
        if is_cn:
            return "❌ **无直接预测市场数据**。"
        else:
            return "❌ **NO DIRECT MARKET DATA**."

    # 假设 market_data 包含字段：title, probability, volume, liquidity, change_24h, url
    title = market_data.get('title', 'N/A')
    prob = market_data.get('probability', 0)  # 例如：0.72 表示72%
    # 这里我们传入 vol_str ($50M) 以保证显示美观
    volume = market_data.get('vol_str', 'N/A') 
    liquidity = market_data.get('liquidity', 0)
    change_24h = market_data.get('change_24h', 0)  # 例如：0.05 表示概率上升5个百分点
    url = market_data.get('url', '#')
    
    # 动态判断文本
    trend_text = "上涨" if change_24h > 0 else "下跌" if change_24h < 0 else "持平"
    confidence_text = "高" if liquidity > 100000 else "中等" if liquidity > 10000 else "较低"  # 假设流动性阈值
    
    # English equivalents for English Mode
    trend_text_en = "up" if change_24h > 0 else "down" if change_24h < 0 else "flat"
    confidence_text_en = "High" if liquidity > 100000 else "Medium" if liquidity > 10000 else "Low"

    # --- Generate Sub-market String ---
    sub_markets_str = ""
    if market_data.get('markets'):
        sub_items = []
        for sm in market_data['markets']:
            # Safe get for sub-market fields
            q = sm.get('question', 'Sub-market')
            top = sm.get('top_option', 'N/A')
            price = sm.get('top_price', 0) * 100
            item = f"- **{q}**: 倾向于 **{top}** ({price:.1f}%)" if is_cn else f"- **{q}**: Leaning **{top}** ({price:.1f}%)"
            sub_items.append(item)
        sub_markets_str = "\n".join(sub_items)

    if is_cn:
        market_context = f"""
### ✅ 市场真实资金共识（来自Polymarket）

**📊 核心指标速览**
* **预测问题：** [{title}]({url})
* **当前隐含概率：** **{prob:.0%}** （较24小时前 **{trend_text} {abs(change_24h):.1%}**）
* **市场流动性：** ${liquidity:,.0f} （共识置信度：**{confidence_text}**）
* **近期交易量：** {volume}

**🧩 相关细分市场参考 (Sub-Markets)**
{sub_markets_str}

**💡 你的新闻共识探测器解读**
1. **市场定价 vs. 新闻情绪**：当前市场认为此事发生的可能性为 **{prob:.0%}**。如果你的新闻源显得更乐观或更悲观，就存在值得探究的“预期差”。
2. **共识强度与趋势**：市场信心正在 **{trend_text}**，且流动性水平表明该共识的可靠性 **{confidence_text}**。
3. **使用建议**：可将此 **{prob:.0%}** 的概率作为你判断该新闻可信度的**中性基准**。若新闻观点与此概率偏离极大，请务必警惕并寻找更多佐证。
"""
    else:
        market_context = f"""
### ✅ Real-Money Market Consensus (via Polymarket)

**📊 Key Metrics**
* **Market:** [{title}]({url})
* **Implied Probability:** **{prob:.0%}** ({trend_text_en} {abs(change_24h):.1%} in 24h)
* **Market Liquidity:** ${liquidity:,.0f} (Confidence: **{confidence_text_en}**)
* **Recent Volume:** {volume}

**🧩 Sub-Market Context**
{sub_markets_str}

**💡 Your Consensus Detector's Take**
1. **Market vs. News Hype:** The market prices a **{prob:.0%}** chance. Any significant deviation in your news source suggests a **mispricing** to investigate.
2. **Strength & Trend:** Consensus is **{trend_text_en}**, with **{confidence_text_en}** reliability due to liquidity.
3. **How to Use This:** Treat **{prob:.0%}** as your **neutral baseline** for credibility. Be skeptical if news narratives deviate wildly from this anchor.
"""
    return market_context

def get_agent_response(history, market_data):
    model = genai.GenerativeModel('gemini-2.5-flash')
    current_date = datetime.datetime.now().strftime("%Y-%m-%d")
    first_query = history[0]['content'] if history else ""
    is_cn = is_chinese_input(first_query)
    
    # 1. Market Context (Using NEW Logic)
    market_context = generate_market_context(market_data, is_cn)

    # 2. System Prompt (PM Mode - STRICTLY UNCHANGED)
    if is_cn:
        system_prompt = f"""
        你是一位管理亿级美元资金的 **全球宏观对冲基金经理 (Global Macro PM)**。
        当前日期: {current_date}
        
        **核心指令:**
        1. **直接输出:** 不要自我介绍，直接开始分析。
        2. **逻辑自洽:** 严禁逻辑断层。
        3. **强制链接:** 提到标的时必须加链接 (如 [NVDA](https://finance.yahoo.com/quote/NVDA))。
        4. **语言强制:** **必须全程使用中文回答**。

        {market_context}
        
        --- 基金经理决策备忘录 ---
        
        ### 0. 新闻背景速览 (Context)
        * **事件还原**: 用通俗语言概括发生了什么。
        * **背景知识**: 为什么这件事值得关注？
        
        ### 1. 市场情绪与共识 (Market Sentiment & Consensus)
        * **当前共识**: 市场目前Price-in了什么？基于预测市场数据，市场目前如何看待这件事？市场情绪是乐观还是悲观？
        * **预期差**: 你的差异化观点是什么？
        * **其他市场信号**: 如有，补充其他相关市场数据（例如，相关公司的股价、搜索指数等）。
        
        ### 2. 多角度分析 (Multi-perspective Analysis)
        * **支持方观点**: 列出支持事件发生的理由和主要支持者。
        * **反对方观点**: 列出反对事件发生的理由和主要反对者。
        * **中立/第三方观点**: 提供其他角度或中立观点。

        ### 3. 事实核查与验证 (Fact Check & Verification)
        * **信息来源可靠性***: 评估新闻来源的可信度。
        * **相关证据***: 列出已知事实或证据，支持或反驳该新闻。
        * **专家观点***: 如有，汇总专家意见。
        
        ### 4. 影响分析 (Impact Analysis)
        * **如果发生**:事件发生会带来哪些影响？（对行业、市场、社会等） -> 资产影响。
        * **如果不发生**: 事件不发生会如何？若核心假设失效，最大回撤是多少？
        * **时间线**: 事件可能的时间线是怎么样的？
        
        ### 5. 交易执行 (The Trade Book)
        * **核心多头 (Long)**:
            * **标的**: [代码+链接]
            * **头寸**: 建议仓位。
            * **逻辑**: 为什么买它？
        * **核心空头/对冲 (Short/Hedge)**:
            * **标的**: [代码+链接]
            * **逻辑**: 对冲什么风险？
        * **⏳ 期限**: 持仓多久？
            
        ### 6. 最终指令 (PM Conclusion)
        * 一句话总结交易方向。
        """
    else:
        system_prompt = f"""
        You are a **Global Macro Portfolio Manager (PM)**.
        Current Date: {current_date}
        
        **INSTRUCTIONS:**
        1. **DIRECT START:** Do NOT introduce yourself. Start immediately.
        2. **LOGIC:** Maintain strict logical consistency.
        3. **LINKS:** Link all tickers (e.g. [AAPL](https://finance.yahoo.com/quote/AAPL)).
        4. **LANGUAGE:** English Only.

        {market_context}
        
        --- INVESTMENT MEMORANDUM ---
        
        ### 0. News Context Snapshot (Context)
        * **Event Recap**: Summarize what happened in plain language.
        * **Background Knowledge**: Why does this matter?
        
        ### 1. Market Sentiment & Consensus (Market Sentiment & Consensus)
        * **Current Consensus**: What is currently Price-in by the market? Based on prediction market data, how does the market currently view this event? Is the market sentiment optimistic or pessimistic?
        * **The Gap**: What is your differentiated view?
        * **Other Market Signals**: If any, supplement with other relevant market data (e.g., related company stock prices, search indices, etc.).
        
        ### 2. Multi-perspective Analysis (Multi-perspective Analysis)
        * **Proponent View**: List reasons supporting the event's occurrence and main supporters.
        * **Opponent View**: List reasons opposing the event's occurrence and main opponents.
        * **Neutral/Third-party View**: Provide other angles or neutral perspectives.

        ### 3. Fact Check & Verification (Fact Check & Verification)
        * **Source Reliability**: Evaluate the credibility of the news source.
        * **Relevant Evidence**: List known facts or evidence that support or refute the news.
        * **Expert Opinions**: If any, summarize expert opinions.
        
        ### 4. Impact Analysis (Impact Analysis)
        * **If It Happens**: What impacts will the event bring? (To industry, market, society, etc.) -> Asset Impact.
        * **If It Doesn't Happen**: What happens if the event does not occur? If the core assumption fails, what is the maximum drawdown?
        * **Timeline**: What is the potential timeline of the event?
        
        ### 5. Trade Execution (The Trade Book)
        * **Core Long (Long)**:
            * **Ticker**: [Code+Link]
            * **Position**: Suggested sizing.
            * **Logic**: Why buy it?
        * **Core Short/Hedge (Short/Hedge)**:
            * **Ticker**: [Code+Link]
            * **Logic**: What risk to hedge?
        * **⏳ Duration**: How long to hold?
            
        ### 6. Final Verdict (PM Conclusion)
        * One-sentence summary of trading direction.
        """
    
    api_messages = [{"role": "user", "parts": [system_prompt]}]
    for msg in history:
        role = "user" if msg['role'] == "user" else "model"
        api_messages.append({"role": role, "parts": [msg['content']]})
        
    try:
        response = model.generate_content(api_messages)
        return response.text
    except Exception as e:
        return f"Agent Analysis Failed: {str(e)}"

# ================= 🖥️ 6. MAIN LAYOUT =================

# --- Header ---
st.markdown('<div class="hero-title">BeHolmes News Analysis</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-subtitle">Narrative vs. Reality Engine</div>', unsafe_allow_html=True)

# --- Search Bar & Workflow ---
_, s_mid, _ = st.columns([1, 6, 1])
with s_mid:
    def on_input_change():
        st.session_state.search_stage = "input"
        st.session_state.search_candidates = []
        
    input_val = st.session_state.get("user_news_text", "")
    # Use a unique key for the text area to allow programmatic clearing if needed, though we sync state
    user_query = st.text_area("Analyze News", value=input_val, height=70, 
                              placeholder="Paste a headline (e.g., 'Unitree robot on Spring Festival Gala')...", 
                              label_visibility="collapsed",
                              on_change=on_input_change, key="news_input_box")
    
    # === Step 1: SEARCH Button ===
    if st.session_state.search_stage == "input":
        if st.button("Begin Analysis", use_container_width=True):
            if st.session_state.news_input_box:
                st.session_state.user_news_text = st.session_state.news_input_box
                with st.spinner("🕵️‍♂️ Hunting for prediction markets..."):
                    candidates = search_market_data_list(st.session_state.user_news_text)
                    st.session_state.search_candidates = candidates
                    st.session_state.search_stage = "selection"
                    st.rerun()

    # === Step 2: SELECTION List ===
    elif st.session_state.search_stage == "selection":
        st.markdown("##### 🧐 Select a Market to Reality Check:")
        if st.session_state.search_candidates:
            for idx, m in enumerate(st.session_state.search_candidates):
                # Native Container with Styling
                with st.container():
                    st.markdown(f"""
                    <div style="padding:12px; background:rgba(255,255,255,0.03); border-radius:8px; border:1px solid rgba(255,255,255,0.1); margin-bottom:10px;">
                        <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                            <div style="flex:1;">
                                <div style="font-weight:700; font-size:1rem; color:#e5e7eb;">{m['title']}</div>
                                <div style="font-size:0.8rem; color:#9ca3af; margin-top:4px;">{m['odds']}</div>
                                <div style="font-size:0.75rem; color:#6b7280; font-family:'JetBrains Mono'; margin-top:4px;">Vol: {m['vol_str']}</div>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    if st.button("Analyze This", key=f"btn_{idx}", use_container_width=True):
                        st.session_state.current_market = m
                        st.session_state.search_stage = "analysis"
                        st.session_state.messages = [{"role": "user", "content": f"Analyze this news: {st.session_state.user_news_text}"}]
                        st.rerun()
        else:
            st.warning("No direct markets found.")

        st.markdown("---")
        if st.button("📝 Analyze News Only (No Market)", use_container_width=True):
            st.session_state.current_market = None
            st.session_state.search_stage = "analysis"
            st.session_state.messages = [{"role": "user", "content": f"Analyze this news: {st.session_state.user_news_text}"}]
            st.rerun()
            
        if st.button("⬅️ Start Over"):
            st.session_state.search_stage = "input"
            st.rerun()

    # === Step 3: ANALYSIS Execution (Initial Run) ===
    elif st.session_state.search_stage == "analysis":
        if st.session_state.messages and st.session_state.messages[-1]['role'] == 'user':
            with st.spinner("🧠 Generating Alpha Signals..."):
                response_text = get_agent_response(st.session_state.messages, st.session_state.current_market)
                st.session_state.messages.append({"role": "assistant", "content": response_text})
                st.rerun()

st.markdown("<br>", unsafe_allow_html=True)

# === DISPLAY ANALYSIS & CHAT (Interactive Mode) ===
if st.session_state.messages and st.session_state.search_stage == "analysis":
    
    if st.session_state.current_market:
        m = st.session_state.current_market
        # 1. Market Header (Native Metric Lookalike)
        with st.container():
            st.markdown(f"""
            <div style="background:rgba(20,0,0,0.8); border-left:4px solid #ef4444; padding:15px; border-radius:8px; margin-bottom:15px;">
                <div style="font-size:0.8rem; color:#9ca3af; text-transform:uppercase; letter-spacing:1px;">🎯 Selected Market</div>
                <div style="font-size:1.4rem; color:#ffffff; font-weight:800; margin:5px 0;">{m['title']}</div>
                <div style="font-family:'JetBrains Mono'; color:#ef4444; font-size:1rem;">{m['vol_str']} Volume</div>
                <a href="{m['url']}" target="_blank" style="display:inline-block; margin-top:10px; color:#fca5a5; font-size:0.8rem; text-decoration:none;">🔗 Open on Polymarket</a>
            </div>
            """, unsafe_allow_html=True)

        # 2. Sub-Markets Loop (Native Streamlit)
        st.markdown("##### 📊 Sub-Market Details")
        for idx, market in enumerate(m.get('markets', []), 1):
            with st.container():
                st.markdown(f"**{idx}. {market['question']}**")
                
                if market['type'] == 'binary':
                    c1, c2 = st.columns(2)
                    with c1:
                        st.progress(market['yes_price'] / 100)
                        st.caption(f"Yes: {market['yes_price']:.1f}%")
                    with c2:
                        st.progress(market['no_price'] / 100)
                        st.caption(f"No: {market['no_price']:.1f}%")
                else:
                    try:
                        sorted_opts = sorted(market.get('options', []), key=lambda x: x.get('price', 0), reverse=True)[:3]
                    except: sorted_opts = []
                    
                    for opt in sorted_opts:
                        c1, c2 = st.columns([1, 4])
                        with c1:
                            st.write(f"{opt['price']:.1f}%")
                        with c2:
                            st.progress(min(opt['price'] / 100, 1.0))
                            st.caption(opt['option'])
                st.divider()

    else:
        st.info("🤖 Pure AI Analysis (No Market Data Selected)")

    # Chat History
    for msg in st.session_state.messages:
        if msg['role'] == 'user':
            with st.chat_message("user"):
                st.write(msg['content'].replace("Analyze this news: ", "News: "))
        else:
            with st.chat_message("assistant"):
                st.markdown(msg['content'])

    # Chat Input
    if prompt := st.chat_input("Ask a follow-up question..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.rerun()

    st.markdown("---")
    if st.button("⬅️ Start New Analysis"):
        st.session_state.messages = []
        st.session_state.search_stage = "input"
        st.rerun()

# ================= 🖥️ DASHBOARD (Only if no analysis active) =================
if not st.session_state.messages and st.session_state.search_stage == "input":
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

    # === RIGHT: Polymarket (Top 60) ===
    with col_markets:
        st.markdown('<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px; border-bottom:1px solid rgba(220,38,38,0.3); padding-bottom:8px;"><span style="font-size:0.9rem; font-weight:700; color:#ef4444;">💰 PREDICTION MARKETS (TOP VOLUME)</span></div>', unsafe_allow_html=True)
        
        sc1, sc2 = st.columns(2)
        if sc1.button("💵 Volume", use_container_width=True): 
            st.session_state.market_sort = "volume"
            st.rerun() # Force Rerun to refresh list
        if sc2.button("🔥 Activity", use_container_width=True): 
            st.session_state.market_sort = "active"
            st.rerun() # Force Rerun to refresh list
        
        # Pass sort_mode to fetcher
        markets = fetch_polymarket_v5_simple(60, sort_mode=st.session_state.market_sort)
        
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

# ================= 🌐 7. FOOTER =================
if not st.session_state.messages and st.session_state.search_stage == "input":
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
