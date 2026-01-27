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

# --- 🔥 C. Polymarket Fetcher (FILTERED & EXPANDED) ---
@st.cache_data(ttl=60)
def fetch_polymarket_v5_simple(limit=60):
    try:
        url = "https://gamma-api.polymarket.com/events?limit=200&closed=false"
        resp = requests.get(url, timeout=8).json()
        markets = []
        
        SENSITIVE_KEYWORDS = [
            "china", "chinese", "xi jinping", "taiwan", "ccp", "beijing", 
            "hong kong", "communist", "pla", "scs", "south china sea"
        ]
        
        if isinstance(resp, list):
            for event in resp:
                try:
                    title = event.get('title', 'Untitled').strip()
                    if not title: continue
                    
                    title_lower = title.lower()
                    if any(kw in title_lower for kw in SENSITIVE_KEYWORDS):
                        continue

                    if event.get('closed') is True: continue
                    if not event.get('markets'): continue
                    m = event['markets'][0]
                    vol = float(m.get('volume', 0))
                    if vol < 1000: continue
                    
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

# --- 🔥 D. NEW AGENT LOGIC (Dual Engine: Arb Trader vs Macro Strategist) ---
def generate_keywords(user_text):
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        prompt = f"Extract 2-3 most critical keywords from this news to search on a prediction market. Return ONLY keywords separated by spaces. Input: {user_text}"
        resp = model.generate_content(prompt)
        return resp.text.strip()
    except: return user_text

def fetch_market_by_slug(slug):
    """通过slug获取市场数据，包含所有子市场"""
    try:
        api_url = f"https://gamma-api.polymarket.com/events?slug={slug}"
        data = requests.get(api_url, timeout=5).json()
        if data and isinstance(data, list):
            event = data[0]
            
            # 过滤敏感话题
            if any(kw in event['title'].lower() for kw in ["china", "xi jinping", "taiwan"]): 
                return None

            # 收集所有子市场
            all_markets = []
            total_volume = 0
            
            for m in event.get('markets', []):
                outcomes = json.loads(m.get('outcomes')) if isinstance(m.get('outcomes'), str) else m.get('outcomes')
                prices = json.loads(m.get('outcomePrices')) if isinstance(m.get('outcomePrices'), str) else m.get('outcomePrices')
                vol = float(m.get('volume', 0))
                total_volume += vol
                
                # 如果是二元市场（Yes/No）
                if len(outcomes) == 2 and 'Yes' in outcomes and 'No' in outcomes:
                    yes_idx = outcomes.index('Yes')
                    no_idx = outcomes.index('No')
                    market_info = {
                        "question": m.get('question', event['title']),
                        "type": "binary",
                        "yes_price": float(prices[yes_idx]) * 100 if yes_idx < len(prices) else 0,
                        "no_price": float(prices[no_idx]) * 100 if no_idx < len(prices) else 0,
                        "volume": vol
                    }
                # 如果是多选市场
                else:
                    options = []
                    for i, out in enumerate(outcomes):
                        if i < len(prices):
                            options.append({
                                "option": out,
                                "price": float(prices[i]) * 100
                            })
                    market_info = {
                        "question": m.get('question', event['title']),
                        "type": "multiple",
                        "options": options,
                        "volume": vol
                    }
                
                all_markets.append(market_info)
            
            # 生成简化的odds字符串用于列表显示
            if all_markets:
                first_market = all_markets[0]
                if first_market['type'] == 'binary':
                    odds_display = f"Yes: {first_market['yes_price']:.1f}% | No: {first_market['no_price']:.1f}%"
                else:
                    top_options = sorted(first_market['options'], key=lambda x: x['price'], reverse=True)[:3]
                    odds_display = " | ".join([f"{opt['option']}: {opt['price']:.1f}%" for opt in top_options])
            else:
                odds_display = "No data"
            
            return {
                "title": event['title'],
                "odds": odds_display,
                "volume": f"${total_volume:,.0f}",
                "slug": slug,
                "url": f"https://polymarket.com/event/{slug}",
                "markets": all_markets,  # 包含所有子市场的详细信息
                "total_volume": total_volume
            }
    except:
        return None

def search_markets_by_api(user_query):
    """通过Polymarket API直接搜索相关市场"""
    candidates = []
    try:
        # 提取关键词
        keywords = generate_keywords(user_query).lower().split()
        
        # 获取活跃市场
        url = "https://gamma-api.polymarket.com/events?limit=200&closed=false"
        resp = requests.get(url, timeout=8).json()
        
        if isinstance(resp, list):
            for event in resp:
                try:
                    title = event.get('title', '').strip()
                    if not title: continue
                    
                    title_lower = title.lower()
                    
                    # 过滤敏感话题
                    if any(kw in title_lower for kw in ["china", "chinese", "xi jinping", "taiwan", "ccp"]): 
                        continue
                    
                    # 关键词匹配度评分
                    match_score = sum(1 for kw in keywords if kw in title_lower)
                    if match_score == 0: continue
                    
                    if event.get('closed') is True: continue
                    if not event.get('markets'): continue
                    
                    # 收集所有子市场
                    all_markets = []
                    total_volume = 0
                    
                    for m in event.get('markets', []):
                        outcomes = json.loads(m.get('outcomes')) if isinstance(m.get('outcomes'), str) else m.get('outcomes')
                        prices = json.loads(m.get('outcomePrices')) if isinstance(m.get('outcomePrices'), str) else m.get('outcomePrices')
                        vol = float(m.get('volume', 0))
                        total_volume += vol
                        
                        # 如果是二元市场（Yes/No）
                        if len(outcomes) == 2 and 'Yes' in outcomes and 'No' in outcomes:
                            yes_idx = outcomes.index('Yes')
                            no_idx = outcomes.index('No')
                            market_info = {
                                "question": m.get('question', event['title']),
                                "type": "binary",
                                "yes_price": float(prices[yes_idx]) * 100 if yes_idx < len(prices) else 0,
                                "no_price": float(prices[no_idx]) * 100 if no_idx < len(prices) else 0,
                                "volume": vol
                            }
                        # 如果是多选市场
                        else:
                            options = []
                            for i, out in enumerate(outcomes):
                                if i < len(prices):
                                    options.append({
                                        "option": out,
                                        "price": float(prices[i]) * 100
                                    })
                            market_info = {
                                "question": m.get('question', event['title']),
                                "type": "multiple",
                                "options": options,
                                "volume": vol
                            }
                        
                        all_markets.append(market_info)
                    
                    # 降低音量要求以获取更多结果
                    if total_volume < 100: continue
                    
                    # 生成简化的odds字符串用于列表显示
                    if all_markets:
                        first_market = all_markets[0]
                        if first_market['type'] == 'binary':
                            odds_display = f"Yes: {first_market['yes_price']:.1f}% | No: {first_market['no_price']:.1f}%"
                        else:
                            top_options = sorted(first_market['options'], key=lambda x: x['price'], reverse=True)[:3]
                            odds_display = " | ".join([f"{opt['option']}: {opt['price']:.1f}%" for opt in top_options])
                    else:
                        odds_display = "No data"
                    
                    if total_volume >= 1000000: vol_str = f"${total_volume/1000000:.1f}M"
                    elif total_volume >= 1000: vol_str = f"${total_volume/1000:.0f}K"
                    else: vol_str = f"${total_volume:.0f}"
                    
                    candidates.append({
                        "title": title,
                        "odds": odds_display,
                        "volume": vol_str,
                        "slug": event.get('slug', ''),
                        "url": f"https://polymarket.com/event/{event.get('slug', '')}",
                        "match_score": match_score,
                        "vol_raw": total_volume,
                        "markets": all_markets  # 包含所有子市场
                    })
                except: 
                    continue
            
            # 按匹配度和音量排序
            candidates.sort(key=lambda x: (x['match_score'], x['vol_raw']), reverse=True)
    except:
        pass
    
    return candidates[:15]  # 返回最多15个结果

def search_market_data_list(user_query):
    """增强版市场搜索：结合Exa搜索和API直接搜索"""
    if not EXA_AVAILABLE or not EXA_API_KEY: 
        # Fallback: 直接通过API搜索相关市场
        return search_markets_by_api(user_query)
    
    candidates = []
    try:
        exa = Exa(EXA_API_KEY)
        keywords = generate_keywords(user_query)
        
        # 策略1: 精确搜索
        search_resp = exa.search(
            f"site:polymarket.com {keywords}",
            num_results=10,
            type="neural",
            include_domains=["polymarket.com"]
        )
        
        for result in search_resp.results:
            match = re.search(r'polymarket\.com/event/([^/]+)', result.url)
            if match:
                slug = match.group(1)
                market_data = fetch_market_by_slug(slug)
                if market_data and market_data not in candidates:
                    candidates.append(market_data)
        
        # 策略2: 如果结果少于3个，使用API直接搜索
        if len(candidates) < 3:
            api_results = search_markets_by_api(user_query)
            for result in api_results:
                if result not in candidates:
                    candidates.append(result)
    except:
        # 出错时使用API搜索作为备选
        return search_markets_by_api(user_query)
    
    return candidates[:15]  # 返回最多15个结果

def is_chinese_input(text):
    return bool(re.search(r'[\u4e00-\u9fff]', text))

# Helper to simulate asset prices for context (In prod, use real API)
def get_asset_context():
    return """
    📊 **[Global Macro Anchors]**
    - Gold (XAU): ~$2,350 (Safe Haven)
    - Oil (WTI): ~$80 (Geopolitics)
    - USD Index (DXY): ~104 (Global Liquidity)
    """

def get_agent_response(history, market_data):
    """
    Handles the full chat conversation with DUAL ENGINE logic (Arb Trader vs Macro Strategist).
    """
    model = genai.GenerativeModel('gemini-2.5-flash')
    current_date = datetime.datetime.now().strftime("%Y-%m-%d")
    macro_anchors = get_asset_context()
    
    first_query = history[0]['content'] if history else ""
    is_cn = is_chinese_input(first_query)
    
    # === PATH A: PREDICTION MARKET FOUND (ARBITRAGE MODE) ===
    if market_data:
        # 构建详细的市场信息
        markets_detail = []
        for idx, m in enumerate(market_data.get('markets', []), 1):
            if m['type'] == 'binary':
                markets_detail.append(
                    f"   {idx}. **{m['question']}**\n"
                    f"      - Yes: {m['yes_price']:.1f}% | No: {m['no_price']:.1f}%\n"
                    f"      - Volume: ${m['volume']:,.0f}"
                )
            else:
                options_str = "\n".join([f"      - {opt['option']}: {opt['price']:.1f}%" for opt in m['options']])
                markets_detail.append(
                    f"   {idx}. **{m['question']}**\n"
                    f"{options_str}\n"
                    f"      - Volume: ${m['volume']:,.0f}"
                )
        
        markets_info = "\n\n".join(markets_detail) if markets_detail else "No market data"
        
        if is_cn:
            market_context = f"""
            ✅ **[已锁定预测市场事件]**
            - **事件:** {market_data['title']}
            - **总交易量:** {market_data['volume']}
            - **子市场数量:** {len(market_data.get('markets', []))}
            
            **所有子市场详情:**
{markets_info}
            
            {macro_anchors}
            """
            system_prompt = f"""
            你是一位 **事件驱动型对冲基金经理 (Event-Driven PM)**，专精于 **预测市场套利 (Prediction Market Arbitrage)**。
            当前日期: {current_date}
            
            **绝对指令 (NON-NEGOTIABLE):**
            1. **禁止寒暄:** 不要说"作为一名..."，直接开始分析。
            2. **全面分析:** 这个事件包含 {len(market_data.get('markets', []))} 个子市场，你需要分析所有子市场的赔率分布，找出最佳交易机会。
            3. **语言强制:** **必须全程使用中文回答**。
            4. **强制链接:** 提到标的时使用Markdown链接。

            {market_context}
            
            --- 预测市场狙击备忘录 ---
            
            ### 0. 📰 事件背景速览
            * **一句话还原**: 发生了什么？
            
            ### 1. 🎲 Polymarket 狙击策略 (核心)
            * **赔率分布分析**: 
              - 逐一分析每个子市场的赔率
              - 市场赔率(Implied Prob) vs 你的真实概率评估(True Prob)
              - 识别哪些子市场存在 EV+ 机会
            * **最佳交易指令** (按优先级排序):
              1. **首选标的**: [子市场名称]
                 - **买入方向**: [Yes / No / 具体选项]
                 - **目标赔率**: 在什么价格区间入手？
                 - **凯利公式**: 建议仓位比例
              2. **次选标的**: (如果有)
                 - 同上格式
            
            ### 2. 🩸 宏观逻辑校验
            * **驱动因子**: 各个子市场的赔率变动背后的逻辑是什么？
            * **相关性**: 不同子市场之间是否存在逻辑矛盾或套利空间？
            * **潜在催化剂**: 未来24-48小时内什么消息会导致赔率剧烈波动？
            
            ### 3. 📈 关联资产对冲 (Capital Markets)
            * **股票/Crypto**: 如何在传统市场放大收益或对冲风险？
              - **标的**: [代码+链接] (如 [SPY](https://finance.yahoo.com/quote/SPY))
              - **逻辑**: 如果预测正确，这个资产会怎么走？
            
            ### 4. 🏁 最终决策
            * 一句话交易指令（优先级最高的标的）。
            """
        else:
            market_context = f"""
            ✅ **[TARGET ACQUIRED: POLYMARKET EVENT]**
            - **Event:** {market_data['title']}
            - **Total Volume:** {market_data['volume']}
            - **Sub-Markets:** {len(market_data.get('markets', []))}
            
            **All Sub-Market Details:**
{markets_info}
            
            {macro_anchors}
            """
            system_prompt = f"""
            You are an **Event-Driven Portfolio Manager** specializing in **Prediction Market Arbitrage**.
            Current Date: {current_date}
            
            **STRICT RULES:**
            1. **NO INTRO:** Start directly.
            2. **COMPREHENSIVE ANALYSIS:** This event contains {len(market_data.get('markets', []))} sub-markets. Analyze ALL of them to find the best EV+ opportunities.
            3. **LANGUAGE:** English Only.
            4. **LINKS:** Mandatory.

            {market_context}
            
            --- ARBITRAGE MEMO ---
            
            ### 0. 📰 Quick Context
            * **The Event**: De-noise the headline.
            
            ### 1. 🎲 Polymarket Sniper Strategy (CORE)
            * **Odds Distribution Analysis**:
              - Analyze each sub-market's odds
              - Market Implied Prob vs. Your True Prob
              - Identify which sub-markets have Positive EV
            * **Top Trading Opportunities** (ranked by priority):
              1. **Primary Target**: [Sub-market name]
                 - **Action**: Buy [Yes / No / Specific Option]
                 - **Entry Zone**: Target price
                 - **Sizing**: Kelly Criterion estimate
              2. **Secondary Target**: (if applicable)
                 - Same format
            
            ### 2. 🩸 Logic Check
            * **Drivers**: What drives the odds in each sub-market?
            * **Correlation**: Any logical contradictions or arbitrage between sub-markets?
            * **Catalyst**: What next event moves these odds?
            
            ### 3. 📈 Correlated Asset Hedges
            * **Equities/Crypto**: How to leverage this view in traditional markets?
              - **Ticker**: [Link]
              - **Correlation**: If Polymarket bet wins, does this asset moon or tank?
            
            ### 4. 🏁 Final Verdict
            * Bottom line instruction (highest priority target).
            """

    # === PATH B: NO MARKET FOUND (MACRO STRATEGIST MODE) ===
    else:
        if is_cn:
            market_context = f"❌ **无直接预测市场数据**。请基于以下宏观锚点进行推演：\n{macro_anchors}"
            system_prompt = f"""
            你是一位 **地缘政治情报交易员 (Geopolitical Alpha Trader)**，曾任职于 Bridgewater。
            当前日期: {current_date}
            
            **绝对指令:**
            1. **禁止寒暄:** 不要说废话，直接输出报告。
            2. **逻辑推演:** 既然没有直接的赌局，你需要寻找股市/汇市的"代理赌局" (Proxy Trades)。
            3. **语言强制:** **必须全程使用中文回答**。
            4. **强制链接:** 必须加链接。

            {market_context}
            
            --- 地缘政治 Alpha 交易备忘录 ---
            
            ### 0. 📰 情报背景 (Context)
            * **事实还原**: 去噪后的核心事件。
            * **情报评级**: [高/中/低] 信号强度。
            
            ### 1. 🗺️ 博弈地图 (Game Theory)
            * **关键决策者**: 谁在桌上？他们的【目标函数】是什么？
            * **二阶效应**: 如果A发生，B会如何报复？推演博弈树。
            
            ### 2. 🎯 市场定价错误 (Mispricing)
            * **当前共识**: 市场现在Price-in了什么？
            * **预期差**: 市场忽略了哪个维度的风险或机会？
            
            ### 3. 📊 交易架构设计 (The Trade)
            * **核心命题**: 一句话定义赌注。
            * **头寸结构**:
              - **方向性头寸 (60%)**: [标的+链接]。*入场逻辑。*
              - **对冲头寸 (25%)**: [标的+链接]。*必须与核心逻辑自洽 (Anti-Contradiction)。*
              - **期权/凸性 (15%)**: 捕捉尾部风险。
            * **压力测试**: 若核心假设失效，最大回撤是多少？
            
            ### 4. ⚡ 执行路线图
            * **监测**: 盯着哪个指标？
            * **失效**: 出现什么信号说明我们错了？
            
            ### 5. 🚨 最终指令
            * [做多/做空] [资产] [仓位]
            """
        else:
            market_context = f"❌ **NO DIRECT MARKET DATA**. Derive logic from macro anchors:\n{macro_anchors}"
            system_prompt = f"""
            You are a **Geopolitical Alpha Trader** (ex-Bridgewater).
            Current Date: {current_date}
            
            **STRICT RULES:**
            1. **NO INTRO:** Start directly.
            2. **PROXY TRADES:** Since no prediction market exists, find the best "Proxy Trades" in equities/FX.
            3. **LANGUAGE:** English Only.
            4. **LINKS:** Mandatory.

            {market_context}
            
            --- Geopolitical Alpha Trade Memo ---
            
            ### 0. 📰 Intelligence Context
            * **Fact Check**: De-noise the event.
            * **Rating**: [High/Med/Low] Signal Strength.
            
            ### 1. 🗺️ Game Theory Map
            * **Players**: Who matters? What are their incentives?
            * **Second-Order**: If A happens, what does B do?
            
            ### 2. 🎯 Market Mispricing
            * **Consensus**: What is priced in?
            * **The Gap**: What is the market missing?
            
            ### 3. 📊 Trade Architecture
            * **Thesis**: One sentence bet.
            * **Positions**:
              - **Directional (60%)**: [Ticker+Link]. *Logic.*
              - **Hedge (25%)**: [Ticker+Link]. *Must be consistent.*
              - **Convexity (15%)**: Tail risk options.
            * **Stress Test**: Drawdown risk if thesis fails.
            
            ### 4. ⚡ Execution
            * **Watch**: Key indicators.
            * **Invalidation**: When to fold?
            
            ### 5. 🚨 Final Order
            * [Long/Short] [Asset] [Size]
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
st.markdown('<div class="hero-title">Be Holmes</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-subtitle">Narrative vs. Reality Engine</div>', unsafe_allow_html=True)

# --- Search Bar & Workflow ---
_, s_mid, _ = st.columns([1, 6, 1])
with s_mid:
    def on_input_change():
        st.session_state.search_stage = "input"
        st.session_state.search_candidates = []
        
    input_val = st.session_state.get("user_news_text", "")
    user_query = st.text_area("Analyze News", value=input_val, height=70, 
                              placeholder="Paste a headline (e.g., 'Fed decision in April')...", 
                              label_visibility="collapsed",
                              on_change=on_input_change, key="news_input_box")
    
    # === Step 1: SEARCH Button ===
    if st.session_state.search_stage == "input":
        if st.button("🔍 Search Markets", use_container_width=True):
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
                c1, c2 = st.columns([4, 1])
                with c1:
                    st.info(f"**{m['title']}**\n\nOdds: {m['odds']} (Vol: {m['volume']})")
                with c2:
                    if st.button("Analyze", key=f"btn_{idx}", use_container_width=True):
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
        
        # 构建子市场的HTML显示
        markets_html = ""
        for idx, market in enumerate(m.get('markets', []), 1):
            if market['type'] == 'binary':
                markets_html += f"""
                <div style="background:rgba(255,255,255,0.03); padding:10px; border-radius:6px; margin-bottom:8px; border-left:3px solid #ef4444;">
                    <div style="font-size:0.85rem; color:#e5e7eb; font-weight:600; margin-bottom:6px;">{idx}. {market['question']}</div>
                    <div style="display:flex; gap:10px;">
                        <div style="flex:1; background:rgba(16,185,129,0.1); padding:6px; border-radius:4px; border:1px solid rgba(16,185,129,0.2);">
                            <span style="font-size:0.7rem; color:#9ca3af;">Yes</span>
                            <span style="font-size:0.95rem; color:#10b981; font-weight:700; font-family:'JetBrains Mono'; margin-left:8px;">{market['yes_price']:.1f}%</span>
                        </div>
                        <div style="flex:1; background:rgba(239,68,68,0.1); padding:6px; border-radius:4px; border:1px solid rgba(239,68,68,0.2);">
                            <span style="font-size:0.7rem; color:#9ca3af;">No</span>
                            <span style="font-size:0.95rem; color:#ef4444; font-weight:700; font-family:'JetBrains Mono'; margin-left:8px;">{market['no_price']:.1f}%</span>
                        </div>
                    </div>
                    <div style="font-size:0.7rem; color:#6b7280; margin-top:4px; text-align:right;">Vol: ${market['volume']:,.0f}</div>
                </div>
                """
            else:
                options_html = ""
                sorted_options = sorted(market['options'], key=lambda x: x['price'], reverse=True)
                for opt in sorted_options:
                    bar_width = opt['price']
                    options_html += f"""
                    <div style="margin-bottom:4px;">
                        <div style="display:flex; justify-content:space-between; font-size:0.75rem; margin-bottom:2px;">
                            <span style="color:#e5e7eb;">{opt['option']}</span>
                            <span style="color:#fbbf24; font-weight:700; font-family:'JetBrains Mono';">{opt['price']:.1f}%</span>
                        </div>
                        <div style="background:rgba(255,255,255,0.1); height:4px; border-radius:2px; overflow:hidden;">
                            <div style="background:#fbbf24; height:100%; width:{bar_width}%;"></div>
                        </div>
                    </div>
                    """
                markets_html += f"""
                <div style="background:rgba(255,255,255,0.03); padding:10px; border-radius:6px; margin-bottom:8px; border-left:3px solid #fbbf24;">
                    <div style="font-size:0.85rem; color:#e5e7eb; font-weight:600; margin-bottom:8px;">{idx}. {market['question']}</div>
                    {options_html}
                    <div style="font-size:0.7rem; color:#6b7280; margin-top:6px; text-align:right;">Vol: ${market['volume']:,.0f}</div>
                </div>
                """
        
        st.markdown(f"""
        <div style="background:rgba(20,0,0,0.8); border-left:4px solid #ef4444; padding:15px; border-radius:8px; margin-bottom:20px;">
            <div style="font-size:0.8rem; color:#9ca3af; text-transform:uppercase;">🎯 Selected Prediction Market Event</div>
            <div style="font-size:1.2rem; color:#e5e7eb; font-weight:bold; margin-top:5px; margin-bottom:15px;">{m['title']}</div>
            
            <div style="display:flex; gap:15px; margin-bottom:15px; padding:10px; background:rgba(255,255,255,0.05); border-radius:6px;">
                <div>
                    <div style="font-size:0.7rem; color:#9ca3af;">Total Volume</div>
                    <div style="font-size:1rem; color:#fbbf24; font-weight:700; font-family:'JetBrains Mono';">{m['volume']}</div>
                </div>
                <div>
                    <div style="font-size:0.7rem; color:#9ca3af;">Sub-Markets</div>
                    <div style="font-size:1rem; color:#10b981; font-weight:700; font-family:'JetBrains Mono';">{len(m.get('markets', []))}</div>
                </div>
            </div>
            
            <div style="font-size:0.8rem; color:#ef4444; font-weight:600; margin-bottom:10px; text-transform:uppercase;">All Sub-Markets:</div>
            {markets_html}
            
            <a href="{m['url']}" target="_blank" style="display:inline-block; margin-top:10px; color:#fca5a5; font-size:0.8rem; text-decoration:none;">🔗 View on Polymarket</a>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="background:rgba(255,255,255,0.05); padding:10px; border-radius:8px; margin-bottom:20px; text-align:center; color:#6b7280; font-size:0.8rem;">
            🤖 Pure AI Analysis (No Market Data Selected)
        </div>
        """, unsafe_allow_html=True)

    # Chat History
    for msg in st.session_state.messages:
        if msg['role'] == 'user':
            with st.chat_message("user"):
                st.write(msg['content'].replace("Analyze this news: ", "News: "))
        else:
            with st.chat_message("assistant"):
                st.markdown(msg['content'])

    # Chat Input
    if prompt := st.chat_input("Ask a follow-up question (e.g. 'What about Tesla?')..."):
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
        if sc1.button("💵 Volume", use_container_width=True): st.session_state.market_sort = "volume"
        if sc2.button("🔥 Activity", use_container_width=True): st.session_state.market_sort = "active"
        
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
