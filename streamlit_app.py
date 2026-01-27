import streamlit as st
import requests
import json
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import re
import time
import datetime
import feedparser

# ================= 🔐 0. KEY MANAGEMENT =================
try:
    EXA_API_KEY = st.secrets["EXA_API_KEY"]
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
    KEYS_LOADED = True
except:
    EXA_API_KEY = None
    GOOGLE_API_KEY = None
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

# ================= 🎨 2. UI THEME (CSS) =================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;900&family=Plus+Jakarta+Sans:wght@400;700&display=swap');

    .stApp {
        background-image: linear-gradient(rgba(0, 0, 0, 0.85), rgba(0, 0, 0, 0.95)), 
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
        text-shadow: 0 0 20px rgba(0,0,0,0.5);
    }
    .hero-subtitle {
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 1rem;
        color: #9ca3af; 
        text-align: center;
        margin-bottom: 30px;
        font-weight: 400;
        min-height: 1.5em;
    }

    /* Section Headers */
    .section-header {
        font-size: 0.9rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 15px;
        padding-bottom: 8px;
        border-bottom: 1px solid rgba(255,255,255,0.1);
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    /* World Clock Styles */
    .world-clock-bar {
        display: flex; 
        justify-content: space-between; 
        background: rgba(0,0,0,0.3); 
        padding: 8px 12px; 
        border-radius: 6px; 
        margin-bottom: 15px;
        border: 1px solid rgba(255,255,255,0.08);
        font-family: 'Courier New', monospace;
    }
    .clock-item {
        font-size: 0.75rem;
        color: #9ca3af;
        display: flex;
        align-items: center;
        gap: 5px;
    }
    .clock-item b { color: #e5e7eb; font-weight: 700; }
    .clock-time { color: #10b981; }

    /* News Feed Grid Cards */
    .news-grid-card {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 8px;
        padding: 15px;
        height: 100%;
        min-height: 140px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        transition: all 0.5s ease-in-out; /* 增加过渡动画 */
    }
    .news-grid-card:hover {
        background: rgba(255, 255, 255, 0.08);
        border-color: rgba(255, 255, 255, 0.1);
        transform: translateY(-2px);
    }
    .news-meta {
        font-size: 0.7rem;
        color: #ef4444;
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
    
    /* Market Spectrum Styles */
    .market-mini-card {
        padding: 10px;
        margin-bottom: 8px;
        background: rgba(16, 185, 129, 0.05); /* Greenish tint */
        border: 1px solid rgba(16, 185, 129, 0.1);
        border-radius: 6px;
        transition: all 0.2s;
    }
    .market-mini-card.battleground {
        background: rgba(245, 158, 11, 0.05); /* Orange tint */
        border: 1px solid rgba(245, 158, 11, 0.2);
    }
    .market-title { font-size: 0.85rem; color: #e5e7eb; margin-bottom: 5px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .market-bar-bg { height: 6px; background: rgba(255,255,255,0.1); border-radius: 3px; overflow: hidden; }
    .market-bar-fill { height: 100%; border-radius: 3px; }
    .market-meta { display: flex; justify-content: space-between; font-size: 0.75rem; margin-top: 4px; color: #9ca3af; }

    /* Input Area */
    .stTextArea textarea {
        background-color: rgba(31, 41, 55, 0.8) !important;
        border: 1px solid #374151 !important;
        color: white !important;
        border-radius: 12px !important;
        font-size: 1rem !important;
    }
    div.stButton > button:first-child {
        background: linear-gradient(90deg, #2563eb 0%, #1d4ed8 100%) !important; /* Blue for "Analyze" */
        color: white !important;
        border-radius: 8px !important;
        border: none !important;
        font-weight: 600 !important;
    }
    
    /* Analysis Result Card */
    .analysis-card {
        background: rgba(17, 24, 39, 0.9);
        border: 1px solid #374151;
        border-radius: 12px;
        padding: 20px;
        margin-top: 20px;
    }
    
    /* Rotation Progress Bar */
    .rotation-bar {
        height: 2px;
        background: rgba(255,255,255,0.1);
        margin-bottom: 10px;
        overflow: hidden;
    }
    .rotation-fill {
        height: 100%;
        background: #ef4444;
        transition: width 1s linear;
    }
</style>
""", unsafe_allow_html=True)

# ================= 🧠 3. LOGIC CORE =================

# --- A. News Logic (缓存 5 分钟) ---
@st.cache_data(ttl=300)
def fetch_rss_news():
    rss_urls = [
        "https://feeds.reuters.com/reuters/worldNews",
        "https://techcrunch.com/feed/",
        "https://www.coindesk.com/arc/outboundfeeds/rss/"
    ]
    news = []
    try:
        for url in rss_urls:
            feed = feedparser.parse(url)
            # 🔥 抓取更多：每个源抓 10 条，保证有足够内容轮播
            for entry in feed.entries[:10]: 
                news.append({
                    "title": entry.title,
                    "source": feed.feed.title if 'title' in feed.feed else "News",
                    "link": entry.link
                })
    except: pass
    # 返回最多 30 条混合新闻
    return news[:30] 

# --- B. Market Logic (Categorized) ---
@st.cache_data(ttl=60)
def fetch_categorized_markets():
    try:
        url = "https://gamma-api.polymarket.com/events?limit=20&sort=volume&closed=false"
        resp = requests.get(url, timeout=5).json()
        
        categories = {"consensus": [], "battleground": []}
        
        if isinstance(resp, list):
            for event in resp:
                try:
                    m = event.get('markets', [])[0]
                    outcomes = json.loads(m.get('outcomes')) if isinstance(m.get('outcomes'), str) else m.get('outcomes')
                    prices = json.loads(m.get('outcomePrices')) if isinstance(m.get('outcomePrices'), str) else m.get('outcomePrices')
                    
                    yes_price = 0
                    if "Yes" in outcomes:
                        yes_price = float(prices[outcomes.index("Yes")]) * 100
                    else:
                        yes_price = float(max([float(x) for x in prices])) * 100 
                    
                    market_obj = {
                        "title": event.get('title'),
                        "yes": int(yes_price),
                        "slug": event.get('slug')
                    }
                    
                    if yes_price >= 75 or yes_price <= 25:
                        categories["consensus"].append(market_obj)
                    elif 40 <= yes_price <= 60:
                        categories["battleground"].append(market_obj)
                        
                except: continue
        return {
            "consensus": categories["consensus"][:4], 
            "battleground": categories["battleground"][:4]
        }
    except: return {"consensus": [], "battleground": []}

# --- C. Search & AI Logic ---
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

    # === LEFT: Live Noise Stream (Auto-Refreshing + Rotating) ===
    with col_news:
        # 顶部标题栏
        st.markdown("""
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:5px; border-bottom:1px solid rgba(255,255,255,0.1); padding-bottom:8px;">
            <div style="font-size:0.9rem; font-weight:700; text-transform:uppercase; letter-spacing:1px;">
                <span style="color:#ef4444">📡 Live Narrative Stream</span>
            </div>
            <div style="font-size:0.7rem; color:#ef4444; animation: pulse 2s infinite;">
                ● LIVE
            </div>
        </div>
        <div style="font-size:0.7rem; color:#6b7280; margin-bottom:15px; font-style:italic;">
            Sources: Reuters • TechCrunch • CoinDesk
        </div>
        <style>
            @keyframes pulse { 0% {opacity: 1;} 50% {opacity: 0.4;} 100% {opacity: 1;} }
        </style>
        """, unsafe_allow_html=True)

        # 🔥 核心修改：每 1 秒刷新UI
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

            # 2. 获取新闻 (缓存300s，含30条数据)
            all_news = fetch_rss_news()
            
            # 3. 🔥 轮播逻辑 (Carousel)
            # 每 15 秒轮换一次
            rotation_interval = 15
            current_timestamp = int(time.time())
            
            # 计算当前是第几批
            # 假设每页显示 6 条 (3行 x 2列)
            items_per_page = 6
            total_items = len(all_news)
            
            if total_items == 0:
                st.info("Scanning global feeds...")
                return

            # 使用取模运算实现无限循环轮播
            batch_index = (current_timestamp // rotation_interval) % (total_items // items_per_page + 1)
            start_idx = batch_index * items_per_page
            end_idx = start_idx + items_per_page
            
            # 截取当前需要显示的新闻
            visible_news = all_news[start_idx:end_idx]
            
            # 如果截取为空(刚好到底)，重置回第一批
            if not visible_news:
                visible_news = all_news[:items_per_page]

            # 4. 轮播倒计时条 (Visual Progress Bar)
            seconds_in_cycle = current_timestamp % rotation_interval
            progress_pct = (seconds_in_cycle / rotation_interval) * 100
            
            st.markdown(f"""
            <div style="display:flex; justify-content:space-between; align-items:flex-end; margin-bottom:5px;">
                <span style="font-size:0.7rem; color:#6b7280;">Auto-rotating feed ({start_idx+1}-{min(end_idx, total_items)} of {total_items})</span>
            </div>
            <div class="rotation-bar">
                <div class="rotation-fill" style="width: {progress_pct}%;"></div>
            </div>
            """, unsafe_allow_html=True)

            # 5. 渲染新闻卡片 Grid
            # 将 visible_news 分成每行2个
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
                                        <span style="color:#6b7280">LIVE</span>
                                    </div>
                                    <div class="news-body">
                                        {news['title']}
                                    </div>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                            st.link_button("🔗 Read Source", news['link'], use_container_width=True)

        render_news_feed()

    # === RIGHT: The Truth Spectrum ===
    with col_markets:
        st.markdown('<div class="section-header"><span style="color:#10b981">💰 Market Consensus</span> <span style="font-size:0.7rem; opacity:0.7">POLYMARKET</span></div>', unsafe_allow_html=True)
        
        market_cats = fetch_categorized_markets()
        
        # 1. Consensus Area (Green)
        st.caption("🏛️ High Certainty (Market Consensus)")
        if market_cats['consensus']:
            for m in market_cats['consensus']:
                st.markdown(f"""
                <a href="https://polymarket.com/event/{m['slug']}" target="_blank" style="text-decoration:none;">
                    <div class="market-mini-card">
                        <div class="market-title">{m['title']}</div>
                        <div class="market-bar-bg"><div class="market-bar-fill" style="width:{m['yes']}%; background:#10b981;"></div></div>
                        <div class="market-meta"><span>Likelihood</span> <span>{m['yes']}%</span></div>
                    </div>
                </a>
                """, unsafe_allow_html=True)
        else:
            st.info("No strong consensus markets right now.")
            
        st.markdown("<br>", unsafe_allow_html=True)
        
        # 2. Battleground Area (Yellow/Orange)
        st.caption("⚡ Active Battleground (High Uncertainty)")
        if market_cats['battleground']:
            for m in market_cats['battleground']:
                st.markdown(f"""
                <a href="https://polymarket.com/event/{m['slug']}" target="_blank" style="text-decoration:none;">
                    <div class="market-mini-card battleground">
                        <div class="market-title">{m['title']}</div>
                        <div class="market-bar-bg"><div class="market-bar-fill" style="width:{m['yes']}%; background:#f59e0b;"></div></div>
                        <div class="market-meta"><span>Likelihood</span> <span>{m['yes']}%</span></div>
                    </div>
                </a>
                """, unsafe_allow_html=True)
        else:
            st.info("Markets are relatively calm.")

# ================= 📊 5. ANALYSIS RESULT VIEW =================
if st.session_state.messages:
    st.markdown("---")
    
    # 顶部：Show context card if available
    if st.session_state.current_market:
        m = st.session_state.current_market
        st.markdown(f"""
        <div style="background:rgba(255,255,255,0.05); border-left:4px solid #10b981; padding:15px; border-radius:8px; margin-bottom:20px;">
            <div style="font-size:0.8rem; color:#9ca3af">BENCHMARK MARKET</div>
            <div style="font-size:1.1rem; color:#e5e7eb; font-weight:bold">{m['title']}</div>
            <div style="display:flex; justify-content:space-between; margin-top:5px;">
                <div style="color:#10b981; font-weight:bold">{m['odds']}</div>
                <div style="color:#6b7280; font-size:0.8rem">Vol: ${m['volume']:,.0f}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # 显示 AI 回复
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

# ================= 🌐 6. GLOBAL NEWS FOOTER =================
if not st.session_state.messages:
    st.markdown("---")
    st.markdown('<div style="text-align:center; color:#9ca3af; margin-bottom:20px; letter-spacing:1px;">🌐 GLOBAL INTELLIGENCE HUB</div>', unsafe_allow_html=True)
    
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1: st.link_button("🇨🇳 Jin10 (金十)", "https://www.jin10.com/", use_container_width=True)
    with c2: st.link_button("🇨🇳 WallstreetCN", "https://wallstreetcn.com/live/global", use_container_width=True)
    with c3: st.link_button("🇸🇬 Zaobao", "https://www.zaobao.com.sg/realtime/world", use_container_width=True)
    with c4: st.link_button("🇭🇰 SCMP", "https://www.scmp.com/", use_container_width=True)
    with c5: st.link_button("🇯🇵 Nikkei Asia", "https://asia.nikkei.com/", use_container_width=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    d1, d2, d3, d4, d5 = st.columns(5)
    with d1: st.link_button("🇺🇸 Bloomberg", "https://www.bloomberg.com/", use_container_width=True)
    with d2: st.link_button("🇬🇧 Reuters", "https://www.reuters.com/", use_container_width=True)
    with d3: st.link_button("🇺🇸 TechCrunch", "https://techcrunch.com/", use_container_width=True)
    with d4: st.link_button("🪙 CoinDesk", "https://www.coindesk.com/", use_container_width=True)
    with d5: st.link_button("🇶🇦 Al Jazeera", "https://www.aljazeera.com/", use_container_width=True)
    
    st.markdown("<br><br>", unsafe_allow_html=True)
