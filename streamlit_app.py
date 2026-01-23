import streamlit as st
import requests
import json
import google.generativeai as genai
import re
import time

# ================= 🔐 0. KEY MANAGEMENT =================
try:
    EXA_API_KEY = st.secrets["EXA_API_KEY"]
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
    KEYS_LOADED = True
except FileNotFoundError:
    EXA_API_KEY = None
    GOOGLE_API_KEY = None
    KEYS_LOADED = False
except KeyError:
    EXA_API_KEY = st.secrets.get("EXA_API_KEY", None)
    GOOGLE_API_KEY = st.secrets.get("GOOGLE_API_KEY", None)
    KEYS_LOADED = bool(EXA_API_KEY and GOOGLE_API_KEY)

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
    page_title="Be Holmes | Research",
    page_icon="🕵️‍♂️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ================= 🧠 1.1 STATE MANAGEMENT =================
if "messages" not in st.session_state:
    st.session_state.messages = []  
if "current_market" not in st.session_state:
    st.session_state.current_market = None 
if "first_visit" not in st.session_state:
    st.session_state.first_visit = True 

# ================= 🎨 2. UI THEME =================
st.markdown("""
<style>
    /* Import Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;900&family=Plus+Jakarta+Sans:wght@400;700&display=swap');

    /* 1. Global Background */
    .stApp {
        background-image: linear-gradient(rgba(0, 0, 0, 0.8), rgba(0, 0, 0, 0.9)), 
                          url('https://upload.cc/i1/2026/01/20/s8pvXA.jpg');
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
        font-family: 'Inter', sans-serif;
    }

    /* Transparent Header */
    header[data-testid="stHeader"] { background-color: transparent !important; }
    [data-testid="stToolbar"] { visibility: hidden; }
    [data-testid="stDecoration"] { visibility: hidden; }

    /* Hero Title */
    .hero-title {
        font-family: 'Inter', sans-serif;
        font-weight: 700;
        font-size: 4.5rem;
        color: #ffffff;
        text-align: center;
        letter-spacing: -2px;
        margin-bottom: 5px;
        padding-top: 8vh;
        text-shadow: 0 0 20px rgba(0,0,0,0.5);
    }
    
    .hero-subtitle {
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 1.1rem;
        color: #9ca3af; 
        text-align: center;
        margin-bottom: 50px;
        font-weight: 400;
    }

    /* 4. Input Field Styling */
    div[data-testid="stVerticalBlock"] > div {
        display: flex;
        flex-direction: column;
        align-items: center;
    }
    .stTextArea { width: 100% !important; max-width: 800px !important; }
    
    .stTextArea textarea {
        background-color: rgba(31, 41, 55, 0.6) !important;
        color: #ffffff !important;
        border: 1px solid #374151 !important;
        border-radius: 16px !important;
        padding: 15px 20px !important; 
        font-size: 1rem !important;
        text-align: left !important;
        line-height: 1.6 !important;
        backdrop-filter: blur(10px);
        transition: all 0.3s ease;
    }
    
    .stTextArea textarea:focus {
        border-color: rgba(239, 68, 68, 0.8) !important;
        box-shadow: 0 0 15px rgba(220, 38, 38, 0.3) !important;
        background-color: rgba(31, 41, 55, 0.9) !important;
    }

    /* 3. Button Styling */
    div.stButton > button:first-child {
        background: linear-gradient(90deg, #7f1d1d 0%, #dc2626 50%, #7f1d1d 100%) !important;
        background-size: 200% auto !important;
        color: #ffffff !important;
        border: 1px solid rgba(239, 68, 68, 0.5) !important;
        border-radius: 50px !important;
        padding: 12px 50px !important;
        font-weight: 600 !important;
        font-size: 1.1rem !important;
        margin-top: 10px !important;
        transition: 0.5s !important;
        box-shadow: 0 0 20px rgba(0,0,0,0.5) !important;
    }
    
    div.stButton > button:first-child:hover {
        background-position: right center !important;
        transform: scale(1.05) !important;
        box-shadow: 0 0 30px rgba(220, 38, 38, 0.6) !important;
        border-color: #fca5a5 !important;
    }
    
    div.stButton > button:first-child:active {
        transform: scale(0.98) !important;
    }

    /* Result Card */
    .market-card {
        background: rgba(17, 24, 39, 0.7);
        border: 1px solid #374151;
        border-radius: 12px;
        padding: 20px;
        margin: 20px auto;
        max-width: 800px;
        backdrop-filter: blur(8px);
    }

    /* Bottom Grid Styling */
    .top10-container {
        width: 100%;
        max-width: 1200px;
        margin: 60px auto 20px auto;
        padding: 0 20px;
    }
    .top10-header {
        font-size: 0.9rem;
        color: #9ca3af;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 20px;
        border-left: 3px solid #dc2626;
        padding-left: 10px;
    }
    
    .top10-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 15px;
    }

    @media (max-width: 1000px) { .top10-grid { grid-template-columns: repeat(2, 1fr); } }
    @media (max-width: 600px) { .top10-grid { grid-template-columns: 1fr; } }

    .market-item {
        background: rgba(17, 24, 39, 0.6);
        border: 1px solid #374151;
        border-radius: 8px;
        padding: 15px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        transition: all 0.2s;
        backdrop-filter: blur(5px);
        min-height: 110px;
        text-decoration: none !important;
        color: inherit !important;
        cursor: pointer;
    }
    .market-item:hover {
        border-color: #ef4444;
        background: rgba(31, 41, 55, 0.9);
        transform: translateY(-2px);
    }
    .m-title {
        color: #e5e7eb;
        font-size: 0.95rem;
        font-weight: 500;
        margin-bottom: 12px;
        line-height: 1.4;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }
    .m-odds {
        display: flex;
        gap: 8px;
        font-family: 'Inter', monospace;
        font-size: 0.75rem;
        margin-top: auto;
    }
    .tag-yes {
        background: rgba(6, 78, 59, 0.4);
        color: #4ade80;
        border: 1px solid rgba(34, 197, 94, 0.3);
        padding: 2px 8px;
        border-radius: 4px;
        font-weight: 600;
    }
    .tag-no {
        background: rgba(127, 29, 29, 0.4);
        color: #f87171;
        border: 1px solid rgba(239, 68, 68, 0.3);
        padding: 2px 8px;
        border-radius: 4px;
        font-weight: 600;
    }
    
    /* Chat Message Styling */
    .stChatMessage {
        background: rgba(31, 41, 55, 0.4);
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 12px;
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

# ================= 🧠 3. LOGIC CORE (恢复稳定版逻辑 + 适度扩容) =================

def detect_language(text):
    for char in text:
        if '\u4e00' <= char <= '\u9fff': return "CHINESE"
    return "ENGLISH"

def generate_english_keywords(user_text):
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        prompt = f"""Task: Extract English search keywords for Polymarket. Input: "{user_text}". Output: Keywords only."""
        resp = model.generate_content(prompt)
        return resp.text.strip()
    except: return user_text

def search_with_exa(query):
    if not EXA_AVAILABLE or not EXA_API_KEY: return [], query
    search_query = generate_english_keywords(query)
    markets_found, seen_ids = [], set()
    try:
        exa = Exa(EXA_API_KEY)
        # 🟢 修正点：
        # 1. 恢复 "prediction market about..." 前缀，这是语义锚点。
        # 2. 将 num_results 提高到 15 (之前是4)，增加抓取 DeepSeek 等尾部内容的概率。
        # 3. 去掉 use_autoprompt=True，防止联想跑偏。
        search_response = exa.search(
            f"prediction market about {search_query}",
            num_results=15, 
            type="neural", 
            include_domains=["polymarket.com"]
        )
        
        for result in search_response.results:
            match = re.search(r'polymarket\.com/(?:event|market)/([^/]+)', result.url)
            if match:
                slug = match.group(1)
                # 过滤掉无用的个人页等
                if slug not in ['profile', 'login', 'leaderboard', 'rewards', 'orders', 'activity'] and slug not in seen_ids:
                    market_data = fetch_poly_details(slug)
                    if market_data:
                        markets_found.extend(market_data)
                        seen_ids.add(slug)
                        # 找到 5 个有效结果就停止，防止 API 请求过多导致卡顿
                        if len(markets_found) >= 5: break
                        
    except Exception as e: print(f"Search error: {e}")
    return markets_found, search_query

@st.cache_data(ttl=60)
def fetch_top_10_markets():
    try:
        url = "https://gamma-api.polymarket.com/events?limit=12&sort=volume&closed=false"
        resp = requests.get(url, timeout=5).json()
        markets = []
        if isinstance(resp, list):
            for event in resp:
                try:
                    title = event.get('title', 'Unknown Event')
                    event_markets = event.get('markets', [])
                    if not event_markets or not isinstance(event_markets, list): continue
                    
                    active_markets = []
                    for m in event_markets:
                        if m.get('closed') is True: continue
                        if not m.get('outcomePrices'): continue
                        active_markets.append(m)
                    if not active_markets: continue

                    active_markets.sort(key=lambda x: float(x.get('volume', 0) or 0), reverse=True)
                    m = active_markets[0]

                    outcomes = m.get('outcomes')
                    if isinstance(outcomes, str): outcomes = json.loads(outcomes)
                    prices = m.get('outcomePrices')
                    if isinstance(prices, str): prices = json.loads(prices)
                    if not outcomes or not prices or len(prices) != len(outcomes): continue

                    # 🌟 修复：智能识别 Yes 价格
                    yes_price = 0
                    no_price = 0
                    
                    if "Yes" in outcomes and "No" in outcomes:
                        try:
                            yes_index = outcomes.index("Yes")
                            yes_raw = float(prices[yes_index])
                            yes_price = int(yes_raw * 100)
                            no_price = 100 - yes_price
                        except:
                            yes_price = int(float(prices[0]) * 100)
                            no_price = 100 - yes_price
                    else:
                        # 多选项市场，找最大的
                        max_price = max([float(p) for p in prices])
                        yes_price = int(max_price * 100)
                        no_price = 100 - yes_price

                    markets.append({
                        "title": title,
                        "yes": yes_price,
                        "no": no_price,
                        "slug": event.get('slug', '')
                    })
                except Exception: continue
        return markets
    except Exception: return []

def fetch_poly_details(slug):
    valid_markets = []
    try:
        url = f"https://gamma-api.polymarket.com/events?slug={slug}"
        resp = requests.get(url, timeout=3).json()
        if isinstance(resp, list) and resp:
            for m in resp[0].get('markets', [])[:1]: # 只取最核心的一个
                p = normalize_data(m)
                if p: valid_markets.append(p)
        return valid_markets
    except: pass
    try:
        url = f"https://gamma-api.polymarket.com/markets?slug={slug}"
        resp = requests.get(url, timeout=3).json()
        if isinstance(resp, list):
            for m in resp:
                p = normalize_data(m)
                if p: valid_markets.append(p)
        elif isinstance(resp, dict):
            p = normalize_data(resp)
            if p: valid_markets.append(p)
        return valid_markets
    except: pass
    return []

def normalize_data(m):
    try:
        if m.get('closed') is True: return None
        outcomes = m.get('outcomes')
        if isinstance(outcomes, str): outcomes = json.loads(outcomes)
        prices = m.get('outcomePrices')
        if isinstance(prices, str): prices = json.loads(prices)
        
        if not outcomes or not prices: return None

        # 智能价格展示
        display_label = ""
        if "Yes" in outcomes:
            idx = outcomes.index("Yes")
            price = float(prices[idx])
            display_label = f"Yes: {price*100:.1f}%"
        else:
            # 多选市场：找概率最高的
            float_prices = [float(p) for p in prices]
            max_p = max(float_prices)
            max_idx = float_prices.index(max_p)
            display_label = f"{outcomes[max_idx]}: {max_p*100:.1f}%"

        return {
            "title": m.get('question', 'Unknown'),
            "odds": display_label,
            "volume": float(m.get('volume', 0)),
            "slug": m.get('slug', '') or m.get('market_slug', '')
        }
    except: return None

# ================= 🧠 3.1 AGENT BRAIN =================

def check_search_intent(user_text):
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        prompt = f"""
        User Input: "{user_text}"
        Does this user explicitly ask to FIND, SEARCH, or LOOK UP a *new* prediction market topic? 
        Answer only YES or NO.
        """
        resp = model.generate_content(prompt)
        return "YES" in resp.text.upper()
    except: return False

def stream_chat_response(messages, market_data=None):
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    market_context = ""
    if market_data:
        market_context = f"""
        [LOCKED TARGET MARKET DATA]
        Title: {market_data['title']}
        Current Odds: {market_data['odds']}
        Volume: ${market_data['volume']:,.0f}
        """
    else:
        # 如果没搜到，也强行让 AI 回答，不要闭嘴
        market_context = "[SYSTEM NOTE: No specific betting market found directly. Use your general knowledge to analyze the topic.]"
    
    system_prompt = f"""
    You are **Be Holmes**, a rational Macro Hedge Fund Manager.
    
    {market_context}
    
    **INSTRUCTIONS:**
    1. If market data is found, use it to give a verdict (Priced-in vs Opportunity).
    2. If NO market data is found, analyze the topic broadly using your internal knowledge. Discuss why a market might not exist yet or what the implications are if it did.
    3. Be cynical, data-driven, and professional.
    4. Automatically detect language: If user asks in Chinese, answer in Chinese.
    """
    
    history = [{"role": "user", "parts": [system_prompt]}]
    for msg in messages:
        role = "user" if msg["role"] == "user" else "model"
        history.append({"role": role, "parts": [msg["content"]]})
        
    return model.generate_content(history).text

# ================= 🖥️ 4. MAIN INTERFACE =================

# 4.1 Hero Section
st.markdown('<h1 class="hero-title">Be Holmes</h1>', unsafe_allow_html=True)
st.markdown('<p class="hero-subtitle">Explore the world\'s prediction markets with neural search.</p>', unsafe_allow_html=True)

# 4.2 Search Section
_, mid, _ = st.columns([1, 6, 1])
with mid:
    user_news = st.text_area("Input", height=70, placeholder="Search for a market, region or event...", label_visibility="collapsed", key="main_search_input")

# 4.3 Button Section
_, btn_col, _ = st.columns([1, 2, 1])
with btn_col:
    ignite_btn = st.button("Decode Alpha", use_container_width=True)

# 4.4 触发逻辑
if ignite_btn:
    if not KEYS_LOADED:
        st.error("🔑 API Keys not found in Secrets.")
    elif not user_news:
        st.warning("Please enter intelligence to analyze.")
    else:
        st.session_state.messages = []
        st.session_state.current_market = None
        st.session_state.first_visit = False
        
        with st.spinner("Neural Searching..."):
            matches, keyword = search_with_exa(user_news)
        
        if matches:
            st.session_state.current_market = matches[0]
        else:
            st.session_state.current_market = None
            
        st.session_state.messages.append({"role": "user", "content": f"Analyze this intel: {user_news}"})
        
        with st.spinner("Decoding Alpha..."):
            response = stream_chat_response(st.session_state.messages, st.session_state.current_market)
            st.session_state.messages.append({"role": "assistant", "content": response})
        
        st.rerun()

# ================= 🗣️ 5. CHAT INTERFACE =================

if st.session_state.messages:
    st.markdown("---")
    
    if st.session_state.current_market:
        m = st.session_state.current_market
        st.markdown(f"""
        <div class="market-card">
            <div style="font-size:0.9rem; color:#9ca3af; margin-bottom:5px;">TARGET MARKET</div>
            <div style="font-size:1.2rem; color:#e5e7eb; margin-bottom:10px; font-weight:bold;">{m['title']}</div>
            <div style="display:flex; justify-content:space-between; align-items:flex-end;">
                <div>
                    <div style="font-family:'Plus Jakarta Sans'; color:#4ade80; font-size:1.8rem; font-weight:700;">{m['odds']}</div>
                    <div style="color:#9ca3af; font-size:0.8rem;">Implied Probability</div>
                </div>
                <div style="text-align:right;">
                    <div style="color:#e5e7eb; font-weight:600; font-size:1.2rem;">${m['volume']:,.0f}</div>
                    <div style="color:#9ca3af; font-size:0.8rem;">Volume</div>
                </div>
            </div>
             <div style="margin-top:10px; padding-top:10px; border-top:1px solid #374151; font-size:0.8rem; text-align:right;">
                <a href="https://polymarket.com/event/{m['slug']}" target="_blank" style="color:#ef4444; text-decoration:none;">View on Polymarket ↗</a>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="text-align:center; padding:10px; color:#9ca3af; font-size:0.9rem; background:rgba(255,255,255,0.05); border-radius:8px; margin-bottom:20px;">
            ⚠️ No specific market found. Analyzing based on general intelligence.
        </div>
        """, unsafe_allow_html=True)

    for i, msg in enumerate(st.session_state.messages):
        if i == 0: continue 
        
        with st.chat_message(msg["role"], avatar="🕵️‍♂️" if msg["role"] == "assistant" else "👤"):
            if i == 1:
                st.markdown(f"<div style='border-left:3px solid #dc2626; padding-left:15px;'>{msg['content']}</div>", unsafe_allow_html=True)
            else:
                st.write(msg["content"])

    if prompt := st.chat_input("Ask a follow-up or search for a new topic..."):
        with st.chat_message("user", avatar="👤"):
            st.write(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        is_search = check_search_intent(prompt)
        
        if is_search:
            with st.chat_message("assistant", avatar="🕵️‍♂️"):
                st.write(f"🔄 Detected search intent. Scanning prediction markets for: **{prompt}**...")
                with st.spinner("Searching Polymarket..."):
                    matches, _ = search_with_exa(prompt)
                
                if matches:
                    st.session_state.current_market = matches[0] 
                    st.success(f"Found: {matches[0]['title']}")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.session_state.current_market = None
                    st.warning("No market found. Analyzing generally...")
                    
        with st.chat_message("assistant", avatar="🕵️‍♂️"):
            with st.spinner("Thinking..."):
                response = stream_chat_response(st.session_state.messages, st.session_state.current_market)
                st.write(response)
        st.session_state.messages.append({"role": "assistant", "content": response})

# ================= 📉 6. BOTTOM SECTION: TOP 12 MARKETS =================

st.markdown("---")
top10_markets = fetch_top_10_markets()

if top10_markets:
    cards_html = "".join([f"""
    <a href="https://polymarket.com/event/{m['slug']}" target="_blank" class="market-item">
        <div class="m-title" title="{m['title']}">{m['title']}</div>
        <div class="m-odds">
            <span class="tag-yes">Yes {m['yes']}¢</span>
            <span class="tag-no">No {m['no']}¢</span>
        </div>
    </a>""" for m in top10_markets])

    final_html = f"""
    <div class="top10-container">
        <div class="top10-header">Trending on Polymarket (Top 12)</div>
        <div class="top10-grid">{cards_html}</div>
    </div>
    """
    
    st.markdown(final_html, unsafe_allow_html=True)
else:
    st.markdown("""
    <div style="text-align:center; margin-top:50px; color:#666;">
        Connecting to Prediction Markets...
    </div>
    """, unsafe_allow_html=True)

# ================= 👇 7. 底部协议与说明 =================
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown("""
<style>
    div.row-widget.stRadio > div { justify-content: center; }
    .protocol-container {
        font-family: 'Inter', sans-serif;
        color: #cbd5e1; font-size: 0.95rem; line-height: 1.8;
        margin-top: 20px; text-align: center; display: flex; flex-direction: column; align-items: center;
    }
    .protocol-step {
        margin-bottom: 25px; padding: 15px 20px; border-radius: 12px;
        background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.05);
        max-width: 700px; width: 100%; transition: all 0.3s;
    }
    .protocol-step:hover { background: rgba(255, 255, 255, 0.05); border-color: rgba(255, 255, 255, 0.1); }
    .protocol-title {
        font-weight: 700; color: #ef4444; font-size: 1rem; letter-spacing: 0.5px;
        text-transform: uppercase; display: block; margin-bottom: 8px;
    }
    .credits-section {
        text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #334155;
        color: #64748b; font-size: 0.85rem; font-family: monospace;
    }
    .credits-highlight { color: #94a3b8; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

with st.expander("Operational Protocol & System Architecture"):
    lang_mode = st.radio("Language", ["EN", "CN"], horizontal=True, label_visibility="collapsed")
    st.markdown("<br>", unsafe_allow_html=True)
    if lang_mode == "EN":
        st.markdown("""
        <div class="protocol-container">
            <div class="protocol-step"><span class="protocol-title">1. Intelligence Injection (Input)</span>User inputs unstructured natural language data.</div>
            <div class="protocol-step"><span class="protocol-title">2. Neural Semantic Mapping (Processing)</span>Powered by <b>Exa.ai</b>, converting semantics into vector embeddings.</div>
            <div class="protocol-step"><span class="protocol-title">3. Bayesian Alpha Decoding (Analysis)</span><b>Google Gemini</b> synthesizes market odds with input intelligence.</div>
        </div>""", unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="protocol-container">
            <div class="protocol-step"><span class="protocol-title">1. 情报注入 (Intelligence Injection)</span>用户输入非结构化数据，系统解析语义核心。</div>
            <div class="protocol-step"><span class="protocol-title">2. 神经语义映射 (Neural Mapping)</span>由 <b>Exa.ai</b> 驱动，精准定位预测市场。</div>
            <div class="protocol-step"><span class="protocol-title">3. 贝叶斯阿尔法解码 (Alpha Decoding)</span><b>Google Gemini</b> 计算“预期差”，判断套利空间。</div>
        </div>""", unsafe_allow_html=True)
    st.markdown("""
    <div class="credits-section">
        SYSTEM ARCHITECTURE POWERED BY<br>
        <span class="credits-highlight">Exa.ai (Neural Search)</span> & <span class="credits-highlight">Google Gemini (Cognitive Core)</span><br><br>
        Data Stream: Polymarket Gamma API
    </div>""", unsafe_allow_html=True)
