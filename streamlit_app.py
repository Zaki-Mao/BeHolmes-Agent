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

# ================= 🎨 2. UI THEME (RED THEME) =================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;900&family=Plus+Jakarta+Sans:wght@400;700&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap');

    .stApp {
        background-image: linear-gradient(rgba(0, 0, 0, 0.9), rgba(20, 0, 0, 0.95)), 
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
    .category-tabs {
        display: flex;
        gap: 10px;
        margin-bottom: 15px;
        justify-content: center;
        flex-wrap: wrap;
    }
    .category-tab {
        padding: 8px 16px;
        background: rgba(20, 0, 0, 0.4);
        border: 1px solid rgba(220, 38, 38, 0.3);
        border-radius: 6px;
        color: #fca5a5;
        cursor: pointer;
        transition: all 0.3s;
        font-size: 0.85rem;
        font-weight: 600;
    }
    .category-tab:hover {
        background: rgba(220, 38, 38, 0.2);
        border-color: #ef4444;
    }
    .category-tab.active {
        background: rgba(220, 38, 38, 0.4);
        border-color: #ef4444;
        color: white;
    }

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
    
    /* Market Card - 双列布局优化 */
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
    
    .analysis-card {
        background: rgba(20, 0, 0, 0.8);
        border: 1px solid #7f1d1d;
        border-radius: 12px;
        padding: 20px;
        margin-top: 20px;
    }

    /* Trending Tags - 渐变色彩 */
    .trend-container {
        display: flex;
        flex-wrap: wrap;
        gap: 12px;
        justify-content: center;
        margin-bottom: 15px;
    }
    .trend-tag {
        background: rgba(20, 0, 0, 0.4);
        border: 1px solid rgba(220, 38, 38, 0.3);
        padding: 6px 14px;
        border-radius: 4px;
        font-size: 0.85rem;
        font-family: 'JetBrains Mono', monospace;
        cursor: pointer;
        transition: all 0.3s;
        display: flex;
        align-items: center;
        text-decoration: none;
    }
    .trend-tag:hover {
        transform: scale(1.05);
        box-shadow: 0 0 10px rgba(220, 38, 38, 0.3);
    }
    .trend-vol {
        font-size: 0.7rem;
        margin-left: 8px;
        padding-left: 8px;
        border-left: 1px solid rgba(220, 38, 38, 0.3);
    }
    
    /* 热度渐变色 */
    .trend-hot { 
        background: linear-gradient(135deg, rgba(220, 38, 38, 0.3), rgba(239, 68, 68, 0.2));
        border-color: #ef4444;
        color: #fca5a5;
    }
    .trend-warm { 
        background: linear-gradient(135deg, rgba(251, 146, 60, 0.3), rgba(249, 115, 22, 0.2));
        border-color: #fb923c;
        color: #fdba74;
    }
    .trend-cool { 
        background: linear-gradient(135deg, rgba(59, 130, 246, 0.3), rgba(37, 99, 235, 0.2));
        border-color: #3b82f6;
        color: #93c5fd;
    }

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
</style>
""", unsafe_allow_html=True)

# ================= 🧠 3. LOGIC CORE =================

# --- 🔥 A. News Logic - 分类支持 (只显示24h内) ---
@st.cache_data(ttl=300)
def fetch_categorized_news():
    """获取分类新闻，只保留24小时内的，增加数量"""
    all_news = {"politics": [], "web3": [], "tech": [], "general": []}
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    cutoff_time = now_utc - datetime.timedelta(hours=24)
    
    # 关键词映射 - 扩展关键词以获取更多相关新闻
    categories_keywords = {
        "politics": ["election", "government", "congress", "senate", "president", "policy", "vote", 
                     "democrat", "republican", "political", "minister", "parliament", "diplomacy"],
        "web3": ["crypto", "bitcoin", "ethereum", "blockchain", "nft", "defi", "web3", "token", 
                 "binance", "coinbase", "metamask", "solana", "polygon", "dogecoin"],
        "tech": ["ai", "artificial intelligence", "tech", "apple", "google", "microsoft", "startup", 
                 "software", "hardware", "openai", "meta", "amazon", "tesla", "spacex", "nvidia"]
    }
    
    def categorize_news(title):
        title_lower = title.lower()
        for cat, keywords in categories_keywords.items():
            if any(kw in title_lower for kw in keywords):
                return cat
        return "general"
    
    def is_within_24h(pub_time_str):
        try:
            dt = datetime.datetime.strptime(pub_time_str, "%Y-%m-%dT%H:%M:%SZ")
            dt = dt.replace(tzinfo=datetime.timezone.utc)
            return dt >= cutoff_time
        except:
            return False
    
    # 1. NewsAPI - 增加获取数量
    if NEWS_API_KEY:
        try:
            # 获取多个类别以增加覆盖面
            categories_to_fetch = ["general", "technology", "business", "science"]
            
            for category in categories_to_fetch:
                url = f"https://newsapi.org/v2/top-headlines?category={category}&language=en&pageSize=100&apiKey={NEWS_API_KEY}"
                response = requests.get(url, timeout=10)
                data = response.json()
                
                if data.get("status") == "ok":
                    for article in data.get("articles", []):
                        if article['title'] == "[Removed]" or not article['title'] or not article['url']:
                            continue
                        
                        pub_time = article.get('publishedAt')
                        if not pub_time or not is_within_24h(pub_time):
                            continue
                        
                        time_display = "LIVE"
                        try:
                            dt = datetime.datetime.strptime(pub_time, "%Y-%m-%dT%H:%M:%SZ")
                            dt = dt.replace(tzinfo=datetime.timezone.utc)
                            diff = now_utc - dt
                            
                            if diff.total_seconds() < 3600:
                                time_display = f"{int(diff.total_seconds()/60)}m ago"
                            else:
                                time_display = f"{int(diff.total_seconds()/3600)}h ago"
                        except:
                            pass

                        news_item = {
                            "title": article['title'],
                            "source": article['source']['name'] or "NewsAPI",
                            "link": article['url'],
                            "time": time_display
                        }
                        
                        cat = categorize_news(article['title'])
                        # 避免重复
                        if news_item not in all_news[cat]:
                            all_news[cat].append(news_item)
        except:
            pass

    # 2. Google News Fallback
    if sum(len(v) for v in all_news.values()) < 40:
        try:
            rss_url = "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en"
            feed = feedparser.parse(rss_url)
            
            for entry in feed.entries[:150]:  # 增加获取数量
                if hasattr(entry, 'published_parsed'):
                    try:
                        dt_utc = datetime.datetime.fromtimestamp(time.mktime(entry.published_parsed), datetime.timezone.utc)
                        if dt_utc < cutoff_time:
                            continue
                        
                        diff = now_utc - dt_utc
                        if diff.total_seconds() < 3600:
                            time_display = f"{int(diff.total_seconds()/60)}m ago"
                        else:
                            time_display = f"{int(diff.total_seconds()/3600)}h ago"
                    except:
                        continue
                else:
                    continue
                
                news_item = {
                    "title": entry.title,
                    "source": entry.source.title if hasattr(entry, 'source') else "Google News",
                    "link": entry.link,
                    "time": time_display
                }
                
                cat = categorize_news(entry.title)
                if news_item not in all_news[cat]:
                    all_news[cat].append(news_item)
        except:
            pass
    
    return all_news

# --- 🔥 B. Google Trends - 实时趋势版本 ---
@st.cache_data(ttl=1800)
def fetch_google_trends():
    """获取Google实时趋势数据"""
    trends = []
    
    # 方法1: 尝试 Google Trends 每日趋势 RSS
    try:
        url = "https://trends.google.com/trends/trendingsearches/daily/rss?geo=US"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        response = requests.get(url, headers=headers, timeout=8)
        
        if response.status_code == 200:
            feed = feedparser.parse(response.content)
            for entry in feed.entries[:20]:  # 增加到20条
                traffic = "10K+"
                if hasattr(entry, 'ht_approx_traffic'):
                    traffic = entry.ht_approx_traffic.replace(',', '').replace('+', '')
                
                # 热度分级
                try:
                    # 移除 + 和 K/M 后缀进行比较
                    traffic_clean = traffic.replace('+', '').replace('K', '000').replace('M', '000000')
                    traffic_num = int(traffic_clean) if traffic_clean.isdigit() else 0
                    
                    if traffic_num > 500000:
                        heat_level = "hot"
                    elif traffic_num > 100000:
                        heat_level = "warm"
                    else:
                        heat_level = "cool"
                except:
                    heat_level = "cool"
                
                trends.append({
                    "name": entry.title,
                    "vol": traffic if hasattr(entry, 'ht_approx_traffic') else "10K+",
                    "heat": heat_level
                })
    except Exception as e:
        pass
    
    # 如果获取失败，使用备用数据
    if not trends:
        trends = [
            {"name": "Global Markets", "vol": "2M+", "heat": "hot"},
            {"name": "AI Technology", "vol": "1M+", "heat": "warm"},
            {"name": "Cryptocurrency", "vol": "800K+", "heat": "warm"},
            {"name": "Climate Change", "vol": "500K+", "heat": "cool"},
            {"name": "Space Exploration", "vol": "300K+", "heat": "cool"}
        ]
    
    return trends

# --- 🔥 C. Crypto Prices (Binance API) ---
@st.cache_data(ttl=60)
def fetch_crypto_prices():
    """获取主流加密货币实时价格（币安API）"""
    symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT", "DOGEUSDT", "AVAXUSDT"]
    crypto_data = []
    
    try:
        url = "https://api.binance.com/api/v3/ticker/24hr"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            all_tickers = response.json()
            
            for ticker in all_tickers:
                if ticker['symbol'] in symbols:
                    symbol_clean = ticker['symbol'].replace('USDT', '')
                    price = float(ticker['lastPrice'])
                    change_24h = float(ticker['priceChangePercent'])
                    volume = float(ticker['volume'])
                    
                    # 格式化价格
                    if price >= 1000:
                        price_str = f"${price:,.0f}"
                    elif price >= 1:
                        price_str = f"${price:,.2f}"
                    else:
                        price_str = f"${price:.4f}"
                    
                    # 格式化交易量
                    if volume >= 1000000:
                        vol_str = f"{volume/1000000:.1f}M"
                    elif volume >= 1000:
                        vol_str = f"{volume/1000:.1f}K"
                    else:
                        vol_str = f"{volume:.0f}"
                    
                    crypto_data.append({
                        "symbol": symbol_clean,
                        "price": price_str,
                        "change": change_24h,
                        "volume": vol_str,
                        "trend": "up" if change_24h > 0 else "down"
                    })
    except:
        # 备用数据
        crypto_data = [
            {"symbol": "BTC", "price": "$94,250", "change": 2.3, "volume": "25.5B", "trend": "up"},
            {"symbol": "ETH", "price": "$3,421", "change": -1.2, "volume": "12.3B", "trend": "down"},
            {"symbol": "BNB", "price": "$612", "change": 0.8, "volume": "1.2B", "trend": "up"},
            {"symbol": "SOL", "price": "$145", "change": 3.5, "volume": "2.1B", "trend": "up"},
        ]
    
    return crypto_data[:8]  # 返回前8个

# --- 🔥 D. Polymarket - 全球排名 + 双列 + 交易量排序 ---
@st.cache_data(ttl=120)
def fetch_top_polymarkets(sort_by="volume", limit=20):
    """获取全球顶级预测市场
    sort_by: 'volume' (交易量) 或 'active' (活跃度)
    """
    try:
        # 获取更多数据以便排序
        url = f"https://gamma-api.polymarket.com/events?limit=100&closed=false"
        resp = requests.get(url, timeout=8).json()
        
        markets = []
        
        if isinstance(resp, list):
            for event in resp:
                try:
                    m = event.get('markets', [])[0]
                    outcomes = json.loads(m.get('outcomes')) if isinstance(m.get('outcomes'), str) else m.get('outcomes')
                    prices = json.loads(m.get('outcomePrices')) if isinstance(m.get('outcomePrices'), str) else m.get('outcomePrices')
                    volume = float(m.get('volume', 0))
                    
                    # 只处理二元市场
                    if len(outcomes) != 2 or len(prices) != 2:
                        continue
                    
                    yes_price = float(prices[0]) * 100
                    no_price = float(prices[1]) * 100
                    
                    # 确保价格合理
                    if yes_price + no_price < 95 or yes_price + no_price > 105:
                        continue
                    
                    markets.append({
                        "title": event.get('title'),
                        "yes": int(yes_price),
                        "no": int(no_price),
                        "slug": event.get('slug'),
                        "volume": volume,
                        "active": event.get('active', True)
                    })
                except:
                    continue
        
        # 排序
        if sort_by == "volume":
            markets.sort(key=lambda x: x['volume'], reverse=True)
        else:
            markets.sort(key=lambda x: x.get('active', 0), reverse=True)
        
        # 格式化交易量
        def format_vol(vol):
            if vol >= 1000000:
                return f"${vol/1000000:.1f}M"
            if vol >= 1000:
                return f"${vol/1000:.0f}K"
            return f"${vol:.0f}"
        
        for m in markets[:limit]:
            m['vol_str'] = format_vol(m['volume'])
        
        return markets[:limit]
    
    except Exception as e:
        return []

# --- D. Search & AI Logic - 恢复分析逻辑 ---
def generate_english_keywords(user_text):
    """生成搜索关键词"""
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        prompt = f"Extract 3-5 concise English keywords for Polymarket search. Input: '{user_text}'. Output: Keywords only, comma-separated."
        resp = model.generate_content(prompt)
        return resp.text.strip()
    except:
        return user_text

def search_polymarket_via_exa(user_text):
    """通过Exa搜索Polymarket相关市场"""
    if not EXA_AVAILABLE or not EXA_API_KEY:
        return [], user_text
    
    keywords = generate_english_keywords(user_text)
    markets = []
    
    try:
        exa = Exa(EXA_API_KEY)
        resp = exa.search(
            f"prediction market about {keywords}",
            num_results=10,
            type="neural",
            include_domains=["polymarket.com"]
        )
        
        seen = set()
        for r in resp.results:
            match = re.search(r'polymarket\.com/(?:event|market)/([^/]+)', r.url)
            if match:
                slug = match.group(1)
                if slug not in seen and slug not in ['profile', 'login', 'activity', 'leaderboard']:
                    try:
                        url = f"https://gamma-api.polymarket.com/events?slug={slug}"
                        data = requests.get(url, timeout=5).json()
                        
                        if data and len(data) > 0:
                            event = data[0]
                            m = event['markets'][0]
                            prices_raw = m['outcomePrices']
                            prices = json.loads(prices_raw) if isinstance(prices_raw, str) else prices_raw
                            
                            markets.append({
                                "title": event.get('title'),
                                "odds": f"Yes: {float(prices[0])*100:.1f}% | No: {float(prices[1])*100:.1f}%",
                                "volume": float(m.get('volume', 0)),
                                "slug": slug,
                                "yes_price": float(prices[0]) * 100,
                                "no_price": float(prices[1]) * 100
                            })
                            seen.add(slug)
                            
                            if len(markets) >= 3:
                                break
                    except:
                        continue
    except:
        pass
    
    return markets, keywords

def analyze_news_with_ai(user_news, market_data=None):
    """AI分析新闻 - 专业预测专家模式"""
    model = genai.GenerativeModel('gemini-2.5-flash')
    current_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M UTC")
    
    market_context = ""
    if market_data:
        market_context = f"""
        📊 RELATED PREDICTION MARKET:
        - Event: {market_data['title']}
        - Current Odds: {market_data['odds']}
        - Trading Volume: ${market_data['volume']:,.0f}
        - Market URL: https://polymarket.com/event/{market_data['slug']}
        
        This represents the "wisdom of crowds" - real money betting on this outcome.
        """
    else:
        market_context = """
        📊 MARKET STATUS: No specific prediction market found for this topic.
        
        You should still analyze this news from a prediction standpoint, estimating probabilities
        based on your understanding of similar events and market dynamics.
        """
    
    system_prompt = f"""
    You are **Be Holmes**, an elite Intelligence Analyst specializing in Reality Checking.
    Current Time: {current_date}
    
    Your mission: Separate NARRATIVE from REALITY.
    
    {market_context}
    
    ANALYSIS FRAMEWORK:
    
    1. **Headline Deconstruction**
       - What is the core claim in this news?
       - What emotional framing is being used? (Fear? Hype? Urgency?)
       - What facts are actually presented vs. speculation?
    
    2. **Market Reality Check**
       {"- How does the prediction market price compare to the news tone?" if market_data else "- What probability would a rational market assign to this?"}
       {"- Is there a gap between media panic and market calm (or vice versa)?" if market_data else "- What would betting odds look like if this market existed?"}
    
    3. **Alpha Signal Detection**
       - Is this news ALREADY priced in?
       - Is the market UNDER-reacting (opportunity) or OVER-reacting (trap)?
       - What would contrarian analysis suggest?
    
    4. **Verdict**
       - Label: [Media Hype | Silent Risk | Consensus Truth | Unknown]
       - Confidence: [High | Medium | Low]
       - Action: What should informed observers watch next?
    
    OUTPUT FORMAT:
    - Write in clear, professional analysis style
    - Use bullet points for key insights
    - End with a JSON block for visualization:
    
    ```json
    {{
        "ai_probability": 0.65,
        "market_probability": {"0.45" if market_data else "null"},
        "gap_text": "Market is underpricing this risk",
        "verdict": "Silent Risk",
        "confidence": "Medium"
    }}
    ```
    
    Be direct. Be analytical. Cut through the noise.
    """
    
    messages = [
        {"role": "user", "parts": [system_prompt]},
        {"role": "user", "parts": [f"Analyze this news:\n\n{user_news}"]}
    ]
    
    try:
        response = model.generate_content(
            messages,
            safety_settings={
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE
            }
        )
        return response.text
    except Exception as e:
        return f"⚠️ Analysis Error: {str(e)}\n\nPlease try again or check API configuration."

# ================= 🖥️ 4. MAIN INTERFACE =================

# --- 4.1 Hero ---
st.markdown("""
<div style="text-align: center;">
    <h1 class="hero-title">Be Holmes</h1>
    <p class="hero-subtitle">Narrative vs. Reality Engine</p>
</div>
""", unsafe_allow_html=True)

# --- 4.1.5 Global Time Clock ---
now_utc = datetime.datetime.now(datetime.timezone.utc)
time_nyc = (now_utc - datetime.timedelta(hours=5)).strftime("%H:%M")
time_lon = now_utc.strftime("%H:%M")
time_abd = (now_utc + datetime.timedelta(hours=4)).strftime("%H:%M")
time_bjs = (now_utc + datetime.timedelta(hours=8)).strftime("%H:%M")

st.markdown(f"""
<div style="
    display: flex; 
    justify-content: center; 
    gap: 20px; 
    margin: 15px auto 25px auto;
    padding: 12px;
    background: rgba(0, 0, 0, 0.4);
    border: 1px solid rgba(220, 38, 38, 0.2);
    border-radius: 10px;
    max-width: 800px;
    flex-wrap: wrap;
">
    <div style="display: flex; flex-direction: column; align-items: center; min-width: 120px;">
        <span style="font-size: 1.2rem; margin-bottom: 3px;">🗽</span>
        <span style="color: #9ca3af; font-size: 0.7rem; margin-bottom: 2px;">New York</span>
        <span style="color: #ef4444; font-size: 1.2rem; font-weight: 700; font-family: 'JetBrains Mono', monospace;">{time_nyc}</span>
    </div>
    
    <div style="display: flex; flex-direction: column; align-items: center; min-width: 120px;">
        <span style="font-size: 1.2rem; margin-bottom: 3px;">🇬🇧</span>
        <span style="color: #9ca3af; font-size: 0.7rem; margin-bottom: 2px;">London</span>
        <span style="color: #fbbf24; font-size: 1.2rem; font-weight: 700; font-family: 'JetBrains Mono', monospace;">{time_lon}</span>
    </div>
    
    <div style="display: flex; flex-direction: column; align-items: center; min-width: 120px;">
        <span style="font-size: 1.2rem; margin-bottom: 3px;">🕌</span>
        <span style="color: #9ca3af; font-size: 0.7rem; margin-bottom: 2px;">Abu Dhabi</span>
        <span style="color: #10b981; font-size: 1.2rem; font-weight: 700; font-family: 'JetBrains Mono', monospace;">{time_abd}</span>
    </div>
    
    <div style="display: flex; flex-direction: column; align-items: center; min-width: 120px;">
        <span style="font-size: 1.2rem; margin-bottom: 3px;">🇨🇳</span>
        <span style="color: #9ca3af; font-size: 0.7rem; margin-bottom: 2px;">Beijing</span>
        <span style="color: #3b82f6; font-size: 1.2rem; font-weight: 700; font-family: 'JetBrains Mono', monospace;">{time_bjs}</span>
    </div>
</div>
""", unsafe_allow_html=True)

# --- 4.2 Search Bar ---
_, s_mid, _ = st.columns([1, 6, 1])
with s_mid:
    input_val = st.session_state.get("user_news_text", "")
    user_query = st.text_area(
        "Analyze News",
        value=input_val,
        height=70,
        placeholder="Paste a headline or news text to reality check...",
        label_visibility="collapsed"
    )
    
    if st.button("⚖️ Reality Check", use_container_width=True):
        if user_query:
            st.session_state.is_processing = True
            st.session_state.user_news_text = user_query
            st.session_state.messages = []
            
            # 搜索相关市场
            with st.spinner("🔍 Searching Polymarket for related predictions..."):
                markets, keywords = search_polymarket_via_exa(user_query)
            
            # 选择最相关的市场
            target_market = markets[0] if markets else None
            st.session_state.current_market = target_market
            
            # AI分析
            with st.spinner("🧠 Analyzing with AI..."):
                analysis = analyze_news_with_ai(user_query, target_market)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": analysis,
                    "searched_markets": markets
                })
            
            st.session_state.is_processing = False
            st.rerun()

# --- 4.3 Dashboard or Analysis Result ---
st.markdown("<br>", unsafe_allow_html=True)

if not st.session_state.messages:
    # === DASHBOARD MODE ===
    col_news, col_markets = st.columns([1, 1], gap="large")
    
    # LEFT: News Feed
    with col_news:
        st.markdown("""
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px; border-bottom:1px solid rgba(220,38,38,0.3); padding-bottom:8px;">
            <div style="font-size:0.9rem; font-weight:700; text-transform:uppercase; letter-spacing:1px;">
                <span style="color:#ef4444">📡 Live News Stream</span>
            </div>
            <div style="font-size:0.7rem; color:#ef4444; animation: pulse 2s infinite;">
                ● 24H ONLY
            </div>
        </div>
        <style>
            @keyframes pulse { 0% {opacity: 1;} 50% {opacity: 0.4;} 100% {opacity: 1;} }
        </style>
        """, unsafe_allow_html=True)
        
        # 全球趋势按钮 (替代 Google Trends)
        st.markdown("""
        <div style="display:flex; align-items:center; justify-content:center; margin:15px 0 10px 0; gap:8px;">
            <span style="font-size:1rem;">🌍</span>
            <span style="font-weight:700; color:#ef4444; letter-spacing:1px; font-size:0.8rem;">GLOBAL TRENDS</span>
        </div>
        """, unsafe_allow_html=True)
        
        trend_links = [
            {"name": "Google Trends", "url": "https://trends.google.com/trending?geo=US", "icon": "🔍"},
            {"name": "Bloomberg", "url": "https://www.bloomberg.com/trending", "icon": "📊"},
            {"name": "Twitter/X", "url": "https://twitter.com/explore", "icon": "🐦"},
            {"name": "Reddit", "url": "https://www.reddit.com/r/all/", "icon": "🤖"},
            {"name": "HackerNews", "url": "https://news.ycombinator.com/", "icon": "🧡"}
        ]
        
        cols = st.columns(5)
        for idx, link in enumerate(trend_links):
            with cols[idx]:
                st.markdown(f"""
                <a href="{link['url']}" target="_blank" style="text-decoration: none;">
                    <div style="
                        background: rgba(220, 38, 38, 0.1);
                        border: 1px solid rgba(220, 38, 38, 0.3);
                        border-radius: 8px;
                        padding: 10px;
                        text-align: center;
                        transition: all 0.3s;
                        cursor: pointer;
                    " onmouseover="this.style.background='rgba(220, 38, 38, 0.2)'; this.style.borderColor='#ef4444';" 
                       onmouseout="this.style.background='rgba(220, 38, 38, 0.1)'; this.style.borderColor='rgba(220, 38, 38, 0.3)';">
                        <div style="font-size: 1.5rem; margin-bottom: 5px;">{link['icon']}</div>
                        <div style="color: #fca5a5; font-size: 0.75rem; font-weight: 600;">{link['name']}</div>
                    </div>
                </a>
                """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Category Tabs - 使用真实的按钮交互
        st.markdown('<div style="text-align: center; margin-bottom: 15px;">', unsafe_allow_html=True)
        cat_cols = st.columns(4)
        categories = ["all", "politics", "web3", "tech"]
        cat_labels = {"all": "🌐 All", "politics": "🏛️ Politics", "web3": "₿ Web3", "tech": "🤖 Tech"}
        
        for idx, cat in enumerate(categories):
            with cat_cols[idx]:
                button_style = "active" if st.session_state.news_category == cat else ""
                if st.button(cat_labels[cat], key=f"cat_btn_{cat}", use_container_width=True):
                    st.session_state.news_category = cat
                    st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Fetch & Display News OR Crypto Prices
        all_news = fetch_categorized_news()
        display_news = []  # 初始化变量
        
        # 特殊处理 Web3 分类 - 显示加密货币价格
        if st.session_state.news_category == "web3":
            st.markdown("""
            <div style="text-align: center; margin: 20px 0 15px 0;">
                <span style="font-size: 1.5rem;">₿</span>
                <span style="color: #ef4444; font-weight: 700; font-size: 1rem; margin-left: 8px;">CRYPTO MARKET LIVE</span>
            </div>
            """, unsafe_allow_html=True)
            
            crypto_prices = fetch_crypto_prices()
            
            if crypto_prices:
                # 双列显示加密货币
                rows = [crypto_prices[i:i+2] for i in range(0, len(crypto_prices), 2)]
                for row in rows:
                    cols = st.columns(2)
                    for idx, crypto in enumerate(row):
                        with cols[idx]:
                            change_color = "#10b981" if crypto['trend'] == "up" else "#ef4444"
                            arrow = "↗" if crypto['trend'] == "up" else "↘"
                            
                            st.markdown(f"""
                            <div style="
                                background: rgba(0, 0, 0, 0.4);
                                border: 1px solid rgba(255, 255, 255, 0.1);
                                border-left: 3px solid {change_color};
                                border-radius: 8px;
                                padding: 15px;
                                margin-bottom: 10px;
                            ">
                                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                                    <span style="color: #e5e7eb; font-size: 1.1rem; font-weight: 700;">{crypto['symbol']}</span>
                                    <span style="color: {change_color}; font-size: 0.9rem; font-weight: 600;">{arrow} {crypto['change']:.2f}%</span>
                                </div>
                                <div style="display: flex; justify-content: space-between; align-items: center;">
                                    <span style="color: #fbbf24; font-size: 1.3rem; font-weight: 700; font-family: 'JetBrains Mono', monospace;">{crypto['price']}</span>
                                    <span style="color: #9ca3af; font-size: 0.75rem;">Vol: {crypto['volume']}</span>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
            else:
                st.info("Loading crypto prices...")
        
        # 其他分类显示新闻
        else:
            if st.session_state.news_category == "all":
                # 从每个分类取更多新闻
                for cat in ["politics", "tech", "general"]:  # 移除 web3
                    display_news.extend(all_news[cat][:10])  # 每个分类10条
            else:
                display_news = all_news[st.session_state.news_category][:30]  # 单个分类30条
            
        if display_news:
            rows = [display_news[i:i+2] for i in range(0, min(len(display_news), 12), 2)]
            for row in rows:
                cols = st.columns(2)
                for i, news in enumerate(row):
                    with cols[i]:
                        st.markdown(f"""
                        <div class="news-grid-card">
                            <div>
                                <div class="news-meta">
                                    <span>{news['source']}</span>
                                    <span style="color:#ef4444">{news['time']}</span>
                                </div>
                                <div class="news-body">{news['title']}</div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # 只保留 Read 按钮
                        st.markdown(f"""
                        <a href="{news['link']}" target="_blank" style="text-decoration:none;">
                            <button style="width:100%; padding:10px; background:rgba(220,38,38,0.2); border:1px solid #ef4444; color:#fca5a5; border-radius:6px; cursor:pointer; font-weight:600; transition:all 0.3s;">
                                🔗 Read Source
                            </button>
                        </a>
                        """, unsafe_allow_html=True)
        else:
            if st.session_state.news_category != "web3":  # 只在非web3时显示"没有新闻"
                st.info("No recent news in this category. Try another category.")
    
    # RIGHT: Polymarket
    with col_markets:
        st.markdown('<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px; border-bottom:1px solid rgba(220,38,38,0.3); padding-bottom:8px;"><span style="font-size:0.9rem; font-weight:700; color:#ef4444; text-transform:uppercase; letter-spacing:1px;">💰 Prediction Markets</span><span style="font-size:0.7rem; color:#9ca3af;">POLYMARKET</span></div>', unsafe_allow_html=True)
        
        # Sort Options - 使用真实按钮
        sort_cols = st.columns(2)
        with sort_cols[0]:
            if st.button("💵 Volume", key="sort_volume", use_container_width=True):
                st.session_state.market_sort = "volume"
                st.rerun()
        with sort_cols[1]:
            if st.button("🔥 Activity", key="sort_activity", use_container_width=True):
                st.session_state.market_sort = "active"
                st.rerun()
        
        st.markdown("<div style='margin-bottom: 15px;'></div>", unsafe_allow_html=True)
        
        # Fetch Markets
        markets = fetch_top_polymarkets(sort_by=st.session_state.market_sort, limit=20)
        
        if markets:
            # 双列显示
            rows = [markets[i:i+2] for i in range(0, len(markets), 2)]
            for row in rows:
                cols = st.columns(2)
                for i, m in enumerate(row):
                    with cols[i]:
                        st.markdown(f"""
                        <a href="https://polymarket.com/event/{m['slug']}" target="_blank" style="text-decoration:none;">
                            <div class="market-card-modern">
                                <div class="market-head">
                                    <div class="market-title-mod">{m['title']}</div>
                                    <div class="market-vol">{m['vol_str']}</div>
                                </div>
                                <div class="outcome-row">
                                    <div class="outcome-box yes">
                                        <span class="outcome-label yes-color">YES</span>
                                        <span class="outcome-price yes-color">{m['yes']}%</span>
                                    </div>
                                    <div class="outcome-box no">
                                        <span class="outcome-label no-color">NO</span>
                                        <span class="outcome-price no-color">{m['no']}%</span>
                                    </div>
                                </div>
                            </div>
                        </a>
                        """, unsafe_allow_html=True)
        else:
            st.info("Loading prediction markets...")

else:
    # === ANALYSIS RESULT MODE ===
    st.markdown("---")
    
    # Show related market if found
    if st.session_state.current_market:
        m = st.session_state.current_market
        st.markdown(f"""
        <div style="background:rgba(20,0,0,0.8); border-left:4px solid #ef4444; padding:15px; border-radius:8px; margin-bottom:20px;">
            <div style="font-size:0.8rem; color:#9ca3af">🎯 MATCHED PREDICTION MARKET</div>
            <div style="font-size:1.1rem; color:#e5e7eb; font-weight:bold; margin-top:5px;">{m['title']}</div>
            <div style="display:flex; justify-content:space-between; margin-top:8px; align-items:center;">
                <div style="color:#ef4444; font-weight:bold; font-family:'JetBrains Mono';">{m['odds']}</div>
                <div style="color:#6b7280; font-size:0.8rem;">Vol: ${m['volume']:,.0f}</div>
            </div>
            <a href="https://polymarket.com/event/{m['slug']}" target="_blank" style="display:inline-block; margin-top:10px; padding:6px 12px; background:rgba(220,38,38,0.2); border:1px solid #ef4444; border-radius:4px; color:#fca5a5; text-decoration:none; font-size:0.8rem;">
                📊 View on Polymarket →
            </a>
        </div>
        """, unsafe_allow_html=True)
    
    # Show all searched markets if multiple found
    if st.session_state.messages and st.session_state.messages[-1].get("searched_markets"):
        searched = st.session_state.messages[-1]["searched_markets"]
        if len(searched) > 1:
            st.markdown("#### 🔗 Other Related Markets")
            for m in searched[1:]:
                st.markdown(f"""
                <div style="background:rgba(0,0,0,0.3); padding:10px; border-radius:6px; margin-bottom:8px; border:1px solid rgba(255,255,255,0.1);">
                    <div style="font-size:0.85rem; color:#e5e7eb;">{m['title']}</div>
                    <div style="display:flex; justify-content:space-between; margin-top:5px;">
                        <span style="color:#9ca3af; font-size:0.75rem;">{m['odds']}</span>
                        <a href="https://polymarket.com/event/{m['slug']}" target="_blank" style="color:#ef4444; font-size:0.75rem; text-decoration:none;">View →</a>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            st.markdown("---")
    
    # Display AI Analysis
    for msg in st.session_state.messages:
        if msg['role'] == 'assistant':
            text = msg['content']
            
            # Extract and remove JSON
            json_match = re.search(r'```json\s*({.*?})\s*```', text, re.DOTALL)
            display_text = re.sub(r'```json.*?```', '', text, flags=re.DOTALL).strip()
            
            st.markdown(f"""
            <div class="analysis-card">
                <div style="font-family:'Inter'; line-height:1.7; color:#d1d5db; white-space:pre-wrap;">
{display_text}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Visualization
            if json_match:
                try:
                    data = json.loads(json_match.group(1))
                    ai_prob = data.get('ai_probability', 0.5)
                    market_prob = data.get('market_probability')
                    gap_text = data.get('gap_text', 'Analysis complete')
                    verdict = data.get('verdict', 'Unknown')
                    confidence = data.get('confidence', 'Medium')
                    
                    if market_prob and market_prob != "null":
                        market_prob = float(market_prob)
                        gap = ai_prob - market_prob
                        color = "#ef4444" if abs(gap) > 0.2 else "#f59e0b"
                        
                        st.markdown(f"""
                        <div style="margin-top:20px; padding:20px; background:rgba(0,0,0,0.4); border-radius:10px; border:1px solid {color};">
                            <div style="text-align:center; margin-bottom:10px;">
                                <span style="font-size:0.9rem; color:#9ca3af;">VERDICT: </span>
                                <span style="font-size:1.1rem; color:{color}; font-weight:bold;">{verdict}</span>
                                <span style="margin-left:15px; font-size:0.8rem; color:#6b7280;">Confidence: {confidence}</span>
                            </div>
                            <div style="display:flex; justify-content:space-between; font-size:0.85rem; margin-bottom:8px;">
                                <span style="color:#9ca3af">Market Reality: {int(market_prob*100)}%</span>
                                <span style="color:{color}; font-weight:bold">GAP: {int(gap*100):+d} pts</span>
                                <span style="color:#3b82f6">AI Estimate: {int(ai_prob*100)}%</span>
                            </div>
                            <div style="height:12px; background:#1f2937; border-radius:6px; position:relative; overflow:hidden;">
                                <div style="position:absolute; left:0; top:0; width:{market_prob*100}%; height:100%; background:linear-gradient(90deg, transparent, #9ca3af);"></div>
                                <div style="position:absolute; left:0; top:0; width:{ai_prob*100}%; height:100%; background:linear-gradient(90deg, transparent, #3b82f6);"></div>
                                <div style="position:absolute; left:{market_prob*100}%; top:0; width:3px; height:100%; background:#fff;" title="Market"></div>
                                <div style="position:absolute; left:{ai_prob*100}%; top:0; width:3px; height:100%; background:#3b82f6;" title="AI"></div>
                            </div>
                            <div style="margin-top:10px; text-align:center; font-size:0.85rem; color:#d1d5db; font-style:italic;">
                                💡 {gap_text}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                        <div style="margin-top:20px; padding:15px; background:rgba(0,0,0,0.4); border-radius:8px; border:1px solid #6b7280;">
                            <div style="text-align:center;">
                                <span style="font-size:0.9rem; color:#9ca3af;">VERDICT: </span>
                                <span style="font-size:1.1rem; color:#fbbf24; font-weight:bold;">{verdict}</span>
                            </div>
                            <div style="margin-top:10px; text-align:center; font-size:0.85rem; color:#d1d5db;">
                                AI Probability Estimate: <span style="color:#3b82f6; font-weight:bold;">{int(ai_prob*100)}%</span>
                            </div>
                            <div style="margin-top:8px; text-align:center; font-size:0.85rem; color:#9ca3af; font-style:italic;">
                                {gap_text}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                except:
                    pass
    
    if st.button("⬅️ Back to Dashboard", use_container_width=True):
        st.session_state.messages = []
        st.session_state.current_market = None
        st.session_state.user_news_text = ""
        st.rerun()

# ================= 🌐 6. FOOTER - Intelligence Hub =================
if not st.session_state.messages:
    st.markdown("---")
    st.markdown('<div style="text-align:center; color:#9ca3af; margin:25px 0; letter-spacing:2px; font-size:0.8rem; font-weight:700;">🌐 GLOBAL INTELLIGENCE HUB</div>', unsafe_allow_html=True)
    
    hub_links = [
        {"name": "Jin10", "url": "https://www.jin10.com/", "icon": "🇨🇳"},
        {"name": "WallStCN", "url": "https://wallstreetcn.com/live/global", "icon": "🇨🇳"},
        {"name": "Zaobao", "url": "https://www.zaobao.com.sg/realtime/world", "icon": "🇸🇬"},
        {"name": "SCMP", "url": "https://www.scmp.com/", "icon": "🇭🇰"},
        {"name": "Nikkei", "url": "https://asia.nikkei.com/", "icon": "🇯🇵"},
        {"name": "Bloomberg", "url": "https://www.bloomberg.com/", "icon": "🇺🇸"},
        {"name": "Reuters", "url": "https://www.reuters.com/", "icon": "🇬🇧"},
        {"name": "TechCrunch", "url": "https://techcrunch.com/", "icon": "🇺🇸"},
        {"name": "CoinDesk", "url": "https://www.coindesk.com/", "icon": "🪙"},
        {"name": "Al Jazeera", "url": "https://www.aljazeera.com/", "icon": "🇶🇦"},
    ]
    
    rows = [hub_links[i:i+5] for i in range(0, len(hub_links), 5)]
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
