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
# 务必在 Streamlit secrets 中配置 NEWS_API_KEY
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
    "last_user_input": ""
}

for key, value in default_state.items():
    if key not in st.session_state:
        st.session_state[key] = value

# --- 🟢 处理点击新闻的回调函数 ---
def trigger_analysis(news_title):
    st.session_state.user_news_text = news_title
    st.session_state.show_market_selection = False
    st.session_state.current_market = None
    st.session_state.is_processing = False 

# ================= 🎨 2. UI THEME (RED THEME) =================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;900&family=Plus+Jakarta+Sans:wght@400;700&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap');

    /* Global Background - Dark Red Tint */
    .stApp {
        background-image: linear-gradient(rgba(0, 0, 0, 0.9), rgba(20, 0, 0, 0.95)), 
                          url('https://upload.cc/i1/2026/01/20/s8pvXA.jpg');
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
        font-family: 'Inter', sans-serif;
    }
    
    /* Hero Title */
    .hero-title {
        font-family: 'Inter', sans-serif;
        font-weight: 700;
        font-size: 3.5rem; 
        color: #ffffff;
        text-align: center;
        letter-spacing: -2px;
        margin-bottom: 5px;
        padding-top: 2vh;
        text-shadow: 0 0 30px rgba(220, 38, 38, 0.6); /* Red Glow */
    }
    .hero-subtitle {
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 1rem;
        color: #9ca3af; 
        text-align: center;
        margin-bottom: 30px;
        font-weight: 400;
    }

    /* World Clock Styles */
    .world-clock-bar {
        display: flex; 
        justify-content: space-between; 
        background: rgba(0,0,0,0.5); 
        padding: 8px 12px; 
        border-radius: 6px; 
        margin-bottom: 15px;
        border: 1px solid rgba(220, 38, 38, 0.2); /* Red Border */
        font-family: 'JetBrains Mono', monospace;
    }
    .clock-item { font-size: 0.75rem; color: #9ca3af; display: flex; align-items: center; gap: 6px; }
    .clock-item b { color: #e5e7eb; font-weight: 700; }
    .clock-time { color: #f87171; } /* Red Time */

    /* News Feed Grid Cards */
    .news-grid-card {
        background: rgba(20, 0, 0, 0.6);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-left: 3px solid #dc2626; /* Strong Red Border */
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
    
    /* 🔥 New Polymarket Card Style */
    .market-card-modern {
        background: rgba(255, 255, 255, 0.02);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 10px;
        transition: all 0.2s;
    }
    .market-card-modern:hover {
        border-color: #ef4444;
        background: rgba(40, 0, 0, 0.3);
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
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
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

    /* RED BUTTONS - Global Override */
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
    
    /* Analysis Result Card */
    .analysis-card {
        background: rgba(20, 0, 0, 0.8);
        border: 1px solid #7f1d1d;
        border-radius: 12px;
        padding: 20px;
        margin-top: 20px;
    }
    
    /* Rotation Progress Bar */
    .rotation-bar {
        height: 2px;
        background: rgba(255,255,255,0.05);
        margin-bottom: 10px;
        overflow: hidden;
        border-radius: 2px;
    }
    .rotation-fill {
        height: 100%;
        background: #ef4444; /* RED Fill */
        transition: width 1s linear;
        box-shadow: 0 0 10px #ef4444;
    }

    /* Hub Button Styles */
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
        box-shadow: 0 5px 15px rgba(220, 38, 38, 0.3); /* RED Glow */
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

    /* Trending Tags (Red Theme) - Clickable */
    .trend-container {
        display: flex;
        flex-wrap: wrap;
        gap: 12px;
        justify-content: center;
        margin-top: 15px;
    }
    .trend-tag {
        background: rgba(20, 0, 0, 0.4);
        border: 1px solid rgba(220, 38, 38, 0.3);
        color: #fca5a5;
        padding: 6px 14px;
        border-radius: 4px;
        font-size: 0.85rem;
        font-family: 'JetBrains Mono', monospace;
        cursor: pointer;
        transition: all 0.3s;
        display: flex;
        align-items: center;
        text-decoration: none; /* For anchor tag */
    }
    .trend-tag:hover {
        background: rgba(220, 38, 38, 0.2);
        border-color: #ef4444;
        box-shadow: 0 0 10px rgba(220, 38, 38, 0.3);
        transform: scale(1.05);
        color: white;
    }
    .trend-vol {
        font-size: 0.7rem;
        color: #9ca3af;
        margin-left: 8px;
        padding-left: 8px;
        border-left: 1px solid rgba(220, 38, 38, 0.3);
    }
</style>
""", unsafe_allow_html=True)

# ================= 🧠 3. LOGIC CORE =================

# --- 🔥 A. News Logic (NewsAPI + Google News Fallback) ---
# 缓存设为 1200秒 (20分钟)
@st.cache_data(ttl=1200) 
def fetch_news():
    news_items = []
    
    # 1. 尝试使用 NewsAPI (如果 Key 存在)
    if NEWS_API_KEY:
        try:
            # 使用更广泛的参数: general category, language en, no country restricted
            url = f"https://newsapi.org/v2/top-headlines?category=general&language=en&pageSize=40&apiKey={NEWS_API_KEY}"
            response = requests.get(url, timeout=10)
            data = response.json()
            
            if data.get("status") == "ok":
                for article in data.get("articles", []):
                    if article['title'] == "[Removed]" or not article['title'] or not article['url']: continue
                    
                    # 时间计算 (统一使用 UTC)
                    time_display = "LIVE"
                    pub_time = article.get('publishedAt')
                    if pub_time:
                        try:
                            dt = datetime.datetime.strptime(pub_time, "%Y-%m-%dT%H:%M:%SZ")
                            # dt 是 naive 的 UTC 时间，设定为 UTC tzinfo
                            dt = dt.replace(tzinfo=datetime.timezone.utc)
                            diff = datetime.datetime.now(datetime.timezone.utc) - dt
                            
                            if diff.total_seconds() < 3600:
                                time_display = f"{int(diff.total_seconds()/60)}m ago"
                            else:
                                time_display = f"{int(diff.total_seconds()/3600)}h ago"
                        except: pass

                    news_items.append({
                        "title": article['title'],
                        "source": article['source']['name'] or "NewsAPI",
                        "link": article['url'],
                        "time": time_display
                    })
        except Exception as e:
            # API 调用失败，准备 fallback
            pass

    # 2. 如果 NewsAPI 失败或没 Key，使用 Google News RSS (绝对实时)
    if not news_items:
        # Google News RSS (Global English)
        rss_url = "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en"
        try:
            feed = feedparser.parse(rss_url)
            for entry in feed.entries[:40]:
                # 解析时间
                time_display = "LIVE"
                if hasattr(entry, 'published_parsed'):
                    try:
                        # published_parsed 是 UTC 时间元组
                        dt_utc = datetime.datetime.fromtimestamp(time.mktime(entry.published_parsed), datetime.timezone.utc)
                        now_utc = datetime.datetime.now(datetime.timezone.utc)
                        diff = now_utc - dt_utc
                        
                        if diff.total_seconds() < 3600:
                            time_display = f"{int(diff.total_seconds()/60)}m ago"
                        else:
                            time_display = f"{int(diff.total_seconds()/3600)}h ago"
                    except: pass
                
                news_items.append({
                    "title": entry.title,
                    "source": entry.source.title if hasattr(entry, 'source') else "Google News",
                    "link": entry.link,
                    "time": time_display
                })
        except: pass
        
    return news_items[:40]

# --- 🔥 B. Real-Time Trends (Google Trends Fix) ---
@st.cache_data(ttl=3600) 
def fetch_real_trends():
    url = "https://trends.google.com/trends/trendingsearches/daily/rss?geo=US"
    trends = []
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            feed = feedparser.parse(response.content)
            for entry in feed.entries[:10]: 
                traffic = "Hot"
                if hasattr(entry, 'ht_approx_traffic'):
                    traffic = entry.ht_approx_traffic
                trends.append({"name": entry.title, "vol": traffic})
    except:
        pass
        
    if not trends:
        trends = [{"name": "Market", "vol": "2M+"}, {"name": "Tech", "vol": "1M+"}]
    return trends

# --- 🔥 C. Market Logic (New Card Data Fetching) ---
@st.cache_data(ttl=60)
def fetch_categorized_markets():
    try:
        url = "https://gamma-api.polymarket.com/events?limit=30&sort=volume&closed=false"
        resp = requests.get(url, timeout=5).json()
        
        categories = {"consensus": [], "battleground": []}
        
        if isinstance(resp, list):
            for event in resp:
                try:
                    m = event.get('markets', [])[0]
                    outcomes = json.loads(m.get('outcomes')) if isinstance(m.get('outcomes'), str) else m.get('outcomes')
                    prices = json.loads(m.get('outcomePrices')) if isinstance(m.get('outcomePrices'), str) else m.get('outcomePrices')
                    volume = float(m.get('volume', 0))
                    
                    yes_price = 0
                    no_price = 0
                    
                    # 尝试找到 Yes 和 No 的价格
                    if "Yes" in outcomes and "No" in outcomes:
                        yes_idx = outcomes.index("Yes")
                        no_idx = outcomes.index("No")
                        yes_price = float(prices[yes_idx]) * 100
                        no_price = float(prices[no_idx]) * 100
                    elif len(outcomes) == 2 and len(prices) == 2:
                        # 对于只有两个选项的市场，假设第一个是 Yes/Long，第二个是 No/Short
                        yes_price = float(prices[0]) * 100
                        no_price = float(prices[1]) * 100
                    else:
                        # 跳过多选项市场，保持界面简洁
                        continue

                    market_obj = {
                        "title": event.get('title'),
                        "yes": int(yes_price),
                        "no": int(no_price),
                        "slug": event.get('slug'),
                        "volume": volume
                    }
                    
                    # 分类逻辑
                    if yes_price >= 80 or yes_price <= 20:
                        categories["consensus"].append(market_obj)
                    elif 40 <= yes_price <= 60 and volume > 10000: # 只展示有一定交易量的战场
                        categories["battleground"].append(market_obj)
                        
                except: continue
        
        # 格式化交易量显示
        def format_vol(vol):
            if vol >= 1000000: return f"${vol/1000000:.1f}M"
            if vol >= 1000: return f"${vol/1000:.0f}K"
            return f"${vol:.0f}"
            
        for cat in categories:
            for m in categories[cat]:
                m['vol_str'] = format_vol(m['volume'])

        return {
            "consensus": categories["consensus"][:5], 
            "battleground": categories["battleground"][:5]
        }
    except: return {"consensus": [], "battleground": []}

# --- D. Search & AI Logic ---
def generate_english_keywords(user_text):
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        prompt = f"Extract English search keywords for Polymarket. Input: '{user_text}'. Output: Keywords only."
        resp = model.generate_content(prompt)
        return resp.text.strip()
    except: return user_text

def search_with_exa_optimized(user_text):
    if not EXA_AVAILABLE or not EXA_API_KEY: return [], user_text
    keywords = generate_english_keywords(user_text)
    markets = []
    try:
        exa = Exa(EXA_API_KEY)
        resp = exa.search(f"prediction market about {keywords}", num_results=10, type="neural", include_domains=["polymarket.com"])
        seen = set()
        for r in resp.results:
            match = re.search(r'polymarket\.com/(?:event|market)/([^/]+)', r.url)
            if match:
                slug = match.group(1)
                if slug not in seen and slug not in ['profile', 'login', 'activity']:
                    url = f"https://gamma-api.polymarket.com/events?slug={slug}"
                    data = requests.get(url).json()
                    if data:
                        m = data[0]['markets'][0]
                        prices_raw = m['outcomePrices']
                        prices = json.loads(prices_raw) if isinstance(prices_raw, str) else prices_raw
                        
                        markets.append({
                            "title": data[0]['title'],
                            "odds": f"Yes: {float(prices[0])*100:.1f}%",
                            "volume": float(m.get('volume',0)),
                            "slug": slug
                        })
                        seen.add(slug)
                        if len(markets) >= 3: break
    except: pass
    return markets, keywords

def stream_chat_response(messages, market_data=None):
    model = genai.GenerativeModel('gemini-2.5-flash')
    current_date = datetime.datetime.now().strftime("%Y-%m-%d")
    
    market_info = ""
    if market_data:
        market_info = f"""
        REAL-TIME MARKET DATA (The "Truth"):
        - Event: {market_data['title']}
        - Odds: {market_data['odds']}
        - Volume: ${market_data['volume']:,.0f}
        """
    else:
        market_info = "NOTE: No specific prediction market found. Analyze based on general knowledge."

    system_prompt = f"""
    You are **Be Holmes**, an Intelligence Analyst specializing in "Alternative Data".
    Current Date: {current_date}
    
    YOUR GOAL: Debunk media noise using market reality.
    
    {market_info}
    
    INSTRUCTIONS:
    1. Compare the User's News (Narrative) vs. Market Data (Reality).
    2. Calculate the "Alpha Gap": Is the market under-reacting or over-reacting compared to the news tone?
    3. If Market Odds are low but News is panic-inducing -> Label as "Media Hype".
    4. If Market Odds are high and News is quiet -> Label as "Silent Risk".
    5. Output a JSON at the end for the visualizer:
    ```json
    {{ "ai_probability": 0.8, "gap_text": "Market is sleeping on this" }}
    ```
    """
    
    history = [{"role": "user", "parts": [system_prompt]}]
    for msg in messages:
        role = "user" if msg["role"] == "user" else "model"
        history.append({"role": role, "parts": [msg["content"]]})
        
    try:
        response = model.generate_content(history, safety_settings={
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE
        })
        return response.text
    except Exception as e: return f"System Error: {str(e)}"

# ================= 🖥️ 4. MAIN INTERFACE LAYOUT =================

# --- 4.1 Hero Title (With Animation) ---
st.markdown("""
<div style="text-align: center;">
    <h1 class="hero-title" id="decrypt-title" data-value="Be Holmes">Be Holmes</h1>
    <p class="hero-subtitle">Narrative vs. Reality Engine</p>
</div>
<script>
    const letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
    const element = document.getElementById("decrypt-title");
    const originalText = element.dataset.value;
    let iteration = 0;
    const interval = setInterval(() => {
        element.innerText = originalText.split("").map((letter, index) => {
            if(index < iteration) return originalText[index];
            return letters[Math.floor(Math.random() * 26)];
        }).join("");
        if(iteration >= originalText.length) clearInterval(interval);
        iteration += 1 / 3;
    }, 40);
</script>
""", unsafe_allow_html=True)

# --- 4.2 Main Search Bar (The Core Interaction) ---
_, s_mid, _ = st.columns([1, 6, 1])
with s_mid:
    input_val = st.session_state.get("user_news_text", "")
    user_query = st.text_area("Analyze News", value=input_val, height=70, placeholder="Paste a headline or click a news item below to reality check...", label_visibility="collapsed")
    
    if st.button("⚖️ Reality Check", use_container_width=True):
        if user_query:
            st.session_state.is_processing = True
            st.session_state.user_news_text = user_query # Sync
            st.session_state.messages = [] # Reset chat
            
            # 1. Search
            with st.spinner("Connecting to Exa Neural Search..."):
                markets, kw = search_with_exa_optimized(user_query)
            
            # 2. Analyze
            target_market = markets[0] if markets else None
            st.session_state.current_market = target_market
            
            st.session_state.messages.append({"role": "user", "content": f"Analyze: {user_query}"})
            with st.spinner("Calculating Alpha Gap..."):
                resp = stream_chat_response(st.session_state.messages, target_market)
                st.session_state.messages.append({"role": "assistant", "content": resp})
            
            st.session_state.is_processing = False
            st.rerun()

# --- 4.3 The "Dashboard" Split View (News vs Markets) ---
st.markdown("<br>", unsafe_allow_html=True)

# 只有在没有进行深度分析对话时才显示仪表盘
if not st.session_state.messages:
    col_news, col_markets = st.columns([1, 1], gap="large")

    # === LEFT: Live Noise Stream (Auto-Refreshing) ===
    with col_news:
        # 顶部标题栏
        st.markdown("""
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:5px; border-bottom:1px solid rgba(220,38,38,0.3); padding-bottom:8px;">
            <div style="font-size:0.9rem; font-weight:700; text-transform:uppercase; letter-spacing:1px;">
                <span style="color:#ef4444">📡 Live Narrative Stream</span>
            </div>
            <div style="font-size:0.7rem; color:#ef4444; animation: pulse 2s infinite;">
                ● LIVE
            </div>
        </div>
        <style>
            @keyframes pulse { 0% {opacity: 1;} 50% {opacity: 0.4;} 100% {opacity: 1;} }
        </style>
        """, unsafe_allow_html=True)

        # 🔥 核心修改：使用 st.fragment 实现局部自动刷新
        @st.fragment(run_every=1)
        def render_news_feed():
            # 1. 渲染全球时间
            now_utc = datetime.datetime.now(datetime.timezone.utc)
            times = {
                "NYC": (now_utc - datetime.timedelta(hours=5)).strftime("%H:%M"),
                "LON": now_utc.strftime("%H:%M"),
                "ABD": (now_utc + datetime.timedelta(hours=4)).strftime("%H:%M"),
                "BJS": (now_utc + datetime.timedelta(hours=8)).strftime("%H:%M"),
            }
            
            st.markdown(f"""
            <div class="world-clock-bar">
                <span class="clock-item"><b>NYC</b> <span class="clock-time">{times['NYC']}</span></span>
                <span class="clock-item"><b>LON</b> <span class="clock-time">{times['LON']}</span></span>
                <span class="clock-item"><b>ABD</b> <span class="clock-time">{times['ABD']}</span></span>
                <span class="clock-item"><b>BJS</b> <span class="clock-time" style="color:#ef4444">{times['BJS']}</span></span>
            </div>
            """, unsafe_allow_html=True)

            # 2. 倒计时逻辑
            # 计算 20分钟 (1200s) 的倒计时
            seconds_left = 1200 - (int(time.time()) % 1200)
            mins, secs = divmod(seconds_left, 60)
            timer_str = f"{mins:02d}:{secs:02d}"
            
            st.markdown(f"""
            <div style="display:flex; justify-content:flex-end; font-family:'JetBrains Mono'; font-size:0.7rem; color:#ef4444; margin-bottom:5px;">
                NEXT SYNC IN: {timer_str}
            </div>
            """, unsafe_allow_html=True)

            # 3. 获取新闻 (使用升级后的 fetch_news)
            all_news = fetch_news()
            
            # 4. 轮播逻辑
            rotation_interval = 15
            current_timestamp = int(time.time())
            
            if not all_news:
                st.info("Initializing intelligence stream...")
                return

            items_per_page = 6
            total_items = len(all_news)
            batch_index = (current_timestamp // rotation_interval) % (total_items // items_per_page + 1)
            start_idx = batch_index * items_per_page
            end_idx = start_idx + items_per_page
            
            visible_news = all_news[start_idx:end_idx]
            if not visible_news:
                visible_news = all_news[:items_per_page]

            # 5. 轮播进度条
            seconds_in_cycle = current_timestamp % rotation_interval
            progress_pct = (seconds_in_cycle / rotation_interval) * 100
            
            st.markdown(f"""
            <div class="rotation-bar">
                <div class="rotation-fill" style="width: {progress_pct}%;"></div>
            </div>
            """, unsafe_allow_html=True)

            # 6. 渲染双列新闻网格
            rows = [visible_news[i:i+2] for i in range(0, len(visible_news), 2)]
            
            for row in rows:
                cols = st.columns(2)
                for i, news in enumerate(row):
                    with cols[i]:
                        with st.container():
                            st.markdown(f"""
                            <div class="news-grid-card">
                                <div>
                                    <div class="news-meta">
                                        <span>{news['source']}</span>
                                        <span style="color:#ef4444">{news['time']}</span>
                                    </div>
                                    <div class="news-body">
                                        {news['title']}
                                    </div>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            # Read Link
                            st.markdown(f"""
                            <a href="{news['link']}" target="_blank" style="text-decoration:none;">
                                <div style="
                                    background:rgba(255,255,255,0.05); 
                                    padding:8px; 
                                    text-align:center; 
                                    border-radius:4px; 
                                    font-size:0.8rem;
                                    color:#ef4444; 
                                    font-weight:600;
                                    border:1px solid rgba(220,38,38,0.2);
                                    transition:all 0.2s;">
                                    🔗 Read Source
                                </div>
                            </a>
                            """, unsafe_allow_html=True)

        render_news_feed()

    # === RIGHT: The Truth Spectrum (NEW DESIGN) ===
    with col_markets:
        st.markdown('<div class="section-header"><span style="color:#ef4444">💰 Market Consensus</span> <span style="font-size:0.7rem; opacity:0.7">POLYMARKET</span></div>', unsafe_allow_html=True)
        
        market_cats = fetch_categorized_markets()
        
        # 1. Consensus Area
        st.caption("🏛️ High Certainty (Consensus)")
        if market_cats['consensus']:
            for m in market_cats['consensus']:
                st.markdown(f"""
                <a href="https://polymarket.com/event/{m['slug']}" target="_blank" style="text-decoration:none;">
                    <div class="market-card-modern">
                        <div class="market-head">
                            <div class="market-title-mod">{m['title']}</div>
                            <div class="market-vol">Vol: {m['vol_str']}</div>
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
            st.info("No strong consensus markets right now.")
            
        st.markdown("<br>", unsafe_allow_html=True)
        
        # 2. Battleground Area
        st.caption("⚡ Active Battleground (Uncertain)")
        if market_cats['battleground']:
            for m in market_cats['battleground']:
                st.markdown(f"""
                <a href="https://polymarket.com/event/{m['slug']}" target="_blank" style="text-decoration:none;">
                    <div class="market-card-modern">
                        <div class="market-head">
                            <div class="market-title-mod">{m['title']}</div>
                            <div class="market-vol">Vol: {m['vol_str']}</div>
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
            st.info("Markets are relatively calm.")

# ================= 📊 5. ANALYSIS RESULT VIEW =================
if st.session_state.messages:
    st.markdown("---")
    
    if st.session_state.current_market:
        m = st.session_state.current_market
        st.markdown(f"""
        <div style="background:rgba(20,0,0,0.8); border-left:4px solid #ef4444; padding:15px; border-radius:8px; margin-bottom:20px;">
            <div style="font-size:0.8rem; color:#9ca3af">BENCHMARK MARKET</div>
            <div style="font-size:1.1rem; color:#e5e7eb; font-weight:bold">{m['title']}</div>
            <div style="display:flex; justify-content:space-between; margin-top:5px;">
                <div style="color:#ef4444; font-weight:bold">{m['odds']}</div>
                <div style="color:#6b7280; font-size:0.8rem">Vol: ${m['volume']:,.0f}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    for msg in st.session_state.messages:
        if msg['role'] == 'assistant':
            text = msg['content']
            display_text = re.sub(r'```json.*?```', '', text, flags=re.DOTALL)
            st.markdown(f"""
            <div class="analysis-card">
                <div style="font-family:'Inter'; line-height:1.6; color:#d1d5db;">
                    {display_text}
                </div>
            </div>
            """, unsafe_allow_html=True)
            try:
                json_match = re.search(r'```json\s*({.*?})\s*```', text, re.DOTALL)
                if json_match and st.session_state.current_market:
                    data = json.loads(json_match.group(1))
                    ai_prob = data.get('ai_probability', 0.5)
                    m_prob_str = st.session_state.current_market['odds'].split(':')[-1].replace('%','').strip()
                    m_prob = float(m_prob_str)/100
                    gap = ai_prob - m_prob
                    color = "#ef4444" if abs(gap) > 0.2 else "#f59e0b"
                    st.markdown(f"""
                    <div style="margin-top:15px; padding:15px; background:rgba(0,0,0,0.3); border-radius:8px; border:1px solid {color};">
                        <div style="display:flex; justify-content:space-between; font-size:0.9rem; margin-bottom:5px;">
                            <span style="color:#9ca3af">Market: {int(m_prob*100)}%</span>
                            <span style="color:{color}; font-weight:bold">GAP: {int(gap*100)}pts</span>
                            <span style="color:#3b82f6">AI Model: {int(ai_prob*100)}%</span>
                        </div>
                        <div style="height:8px; background:#374151; border-radius:4px; position:relative;">
                            <div style="position:absolute; left:{m_prob*100}%; top:-3px; width:4px; height:14px; background:#fff;" title="Market"></div>
                            <div style="position:absolute; left:{ai_prob*100}%; top:-3px; width:4px; height:14px; background:#3b82f6;" title="AI"></div>
                            <div style="position:absolute; left:{min(m_prob,ai_prob)*100}%; top:3px; width:{abs(gap)*100}%; height:2px; background:{color};"></div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            except: pass

    if st.button("⬅️ Back to Dashboard"):
        st.session_state.messages = []
        st.rerun()

# ================= 🌐 6. GLOBAL INTELLIGENCE FOOTER (FIXED) =================
if not st.session_state.messages:
    st.markdown("---")
    
    # 6.1 Real-Time Google Trends
    st.markdown("""
    <div style="display:flex; align-items:center; justify-content:center; margin-bottom:15px; gap:8px;">
        <span style="font-size:1.2rem;">📈</span>
        <span style="font-weight:700; color:#ef4444; letter-spacing:1px; font-size:0.9rem;">GLOBAL SEARCH TRENDS (LIVE)</span>
    </div>
    """, unsafe_allow_html=True)
    
    real_trends = fetch_real_trends()
    
    trend_html = '<div class="trend-container">'
    for t in real_trends:
        encoded_query = urllib.parse.quote(t['name'])
        trend_html += f"""
        <a href="https://www.google.com/search?q={encoded_query}" target="_blank" class="trend-tag">
            {t['name']}
            <span class="trend-vol">{t['vol']}</span>
        </a>
        """
    trend_html += '</div>'
    
    st.markdown(trend_html, unsafe_allow_html=True)
    st.markdown("<br><br>", unsafe_allow_html=True)

    # 6.2 Global Intelligence Hub
    st.markdown('<div style="text-align:center; color:#9ca3af; margin-bottom:25px; letter-spacing:2px; font-size:0.8rem; font-weight:700;">🌐 GLOBAL INTELLIGENCE HUB</div>', unsafe_allow_html=True)
    
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
    
    st.markdown("<br><br>", unsafe_allow_html=True)
