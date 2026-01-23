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
    page_title="Be Holmes | Research",
    page_icon="🕵️‍♂️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ================= 🧠 2. STATE MANAGEMENT =================
if "messages" not in st.session_state:
    st.session_state.messages = []
if "current_market" not in st.session_state:
    st.session_state.current_market = None
if "first_visit" not in st.session_state:
    st.session_state.first_visit = True

# ================= 🎨 3. UI THEME =================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;900&family=Plus+Jakarta+Sans:wght@400;700&display=swap');

    .stApp {
        background-image: linear-gradient(rgba(0, 0, 0, 0.8), rgba(0, 0, 0, 0.9)), 
                          url('https://upload.cc/i1/2026/01/20/s8pvXA.jpg');
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
        font-family: 'Inter', sans-serif;
    }
    header[data-testid="stHeader"] { background-color: transparent !important; }
    
    .hero-title {
        font-family: 'Inter', sans-serif;
        font-weight: 700;
        font-size: 4.5rem;
        color: #ffffff;
        text-align: center;
        letter-spacing: -2px;
        margin-bottom: 5px;
        padding-top: 5vh;
        text-shadow: 0 0 20px rgba(0,0,0,0.5);
    }
    
    .market-card {
        background: rgba(17, 24, 39, 0.8);
        border: 1px solid #374151;
        border-radius: 12px;
        padding: 20px;
        margin: 20px auto;
        max-width: 800px;
        backdrop-filter: blur(8px);
        box-shadow: 0 4px 20px rgba(0,0,0,0.3);
    }

    /* Top 12 Grid Styles */
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
    @media (max-width: 800px) { .top10-grid { grid-template-columns: 1fr; } }
    
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
    }
    .market-item:hover {
        border-color: #ef4444;
        background: rgba(31, 41, 55, 0.9);
        transform: translateY(-2px);
    }
    .m-title { color: #e5e7eb; font-size: 0.95rem; font-weight: 500; margin-bottom: 12px; line-height: 1.4; }
    .m-odds { display: flex; gap: 8px; font-size: 0.75rem; margin-top: auto; }
    .tag-yes { background: rgba(6, 78, 59, 0.4); color: #4ade80; padding: 2px 8px; border-radius: 4px; }
    .tag-no { background: rgba(127, 29, 29, 0.4); color: #f87171; padding: 2px 8px; border-radius: 4px; }
    
    /* Input & Button */
    .stTextArea textarea {
        background-color: rgba(31, 41, 55, 0.6) !important;
        color: #ffffff !important;
        border: 1px solid #374151 !important;
        border-radius: 16px !important;
    }
    div.stButton > button:first-child {
        background: linear-gradient(90deg, #7f1d1d 0%, #dc2626 50%, #7f1d1d 100%) !important;
        color: white !important;
        border-radius: 50px !important;
        border: none !important;
    }
</style>
""", unsafe_allow_html=True)

# ================= 🧠 4. CORE LOGIC =================

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
        search_response = exa.search(
            f"prediction market about {search_query}",
            num_results=3, type="neural", include_domains=["polymarket.com"]
        )
        for result in search_response.results:
            match = re.search(r'polymarket\.com/(?:event|market)/([^/]+)', result.url)
            if match:
                slug = match.group(1)
                if slug not in seen_ids:
                    data = fetch_poly_details(slug)
                    if data:
                        markets_found.extend(data)
                        seen_ids.add(slug)
    except: pass
    return markets_found, search_query

def fetch_poly_details(slug):
    try:
        url = f"https://gamma-api.polymarket.com/events?slug={slug}"
        resp = requests.get(url, timeout=3).json()
        valid = []
        if isinstance(resp, list) and resp:
            for m in resp[0].get('markets', [])[:2]:
                p = normalize_data(m)
                if p: valid.append(p)
        return valid
    except: return []

def normalize_data(m):
    try:
        if m.get('closed') is True: return None
        outcomes = json.loads(m.get('outcomes')) if isinstance(m.get('outcomes'), str) else m.get('outcomes')
        prices = json.loads(m.get('outcomePrices')) if isinstance(m.get('outcomePrices'), str) else m.get('outcomePrices')
        odds = "N/A"
        if outcomes and prices: odds = f"{outcomes[0]}: {float(prices[0])*100:.1f}%"
        return {"title": m.get('question'), "odds": odds, "volume": float(m.get('volume', 0)), "slug": m.get('slug', '')}
    except: return None

@st.cache_data(ttl=60)
def fetch_top_10_markets():
    try:
        url = "https://gamma-api.polymarket.com/events?limit=12&sort=volume&closed=false"
        resp = requests.get(url, timeout=5).json()
        markets = []
        if isinstance(resp, list):
            for event in resp:
                try:
                    m = event.get('markets', [])[0]
                    outcomes = json.loads(m.get('outcomes')) if isinstance(m.get('outcomes'), str) else m.get('outcomes')
                    prices = json.loads(m.get('outcomePrices')) if isinstance(m.get('outcomePrices'), str) else m.get('outcomePrices')
                    yes = int(float(prices[outcomes.index("Yes")]) * 100) if "Yes" in outcomes else 50
                    markets.append({"title": event.get('title'), "yes": yes, "no": 100-yes, "slug": event.get('slug')})
                except: continue
        return markets
    except: return []

# --- 🕵️‍♂️ Agent Brain: 意图识别与回复 ---
def check_search_intent(user_text):
    """判断用户是否想要搜索新内容"""
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

def stream_holmes_response(messages, market_data=None):
    model = genai.GenerativeModel('gemini-2.5-flash')
    market_context = ""
    if market_data:
        market_context = f"""
        [CURRENT MARKET DATA]
        Event: {market_data['title']}
        Odds: {market_data['odds']}
        Volume: ${market_data['volume']:,.0f}
        """
    
    system_prompt = f"""
    You are **Be Holmes**, a rational Macro Hedge Fund Manager.
    {market_context}
    **INSTRUCTIONS:**
    1. Answer the user's question directly.
    2. If market data is provided, use it to support your analysis.
    3. Be cynical, data-driven, and professional.
    4. If user asks in Chinese, respond in Chinese.
    """
    
    history = [{"role": "user", "parts": [system_prompt]}]
    for msg in messages:
        role = "user" if msg["role"] == "user" else "model"
        history.append({"role": role, "parts": [msg["content"]]})
        
    return model.generate_content(history).text

# ================= 🖥️ 5. INTERFACE LOGIC =================

st.markdown('<h1 class="hero-title">Be Holmes</h1>', unsafe_allow_html=True)

# 搜索框 (总是显示，作为重置入口)
_, mid, _ = st.columns([1, 6, 1])
with mid:
    user_input = st.text_area("Input", height=70, placeholder="Search for a market (e.g., 'Will Trump win?')...", label_visibility="collapsed", key="main_search")

_, btn_col, _ = st.columns([1, 2, 1])
with btn_col:
    if st.button("Decode Alpha", use_container_width=True):
        if not user_input:
            st.warning("Enter a topic first.")
        else:
            # 重置并开启新对话
            st.session_state.messages = [] 
            st.session_state.first_visit = False
            
            with st.spinner("Neural Searching..."):
                matches, keyword = search_with_exa(user_input)
            
            if matches:
                st.session_state.current_market = matches[0]
            else:
                st.session_state.current_market = None
            
            # 存入历史并生成回复
            st.session_state.messages.append({"role": "user", "content": f"Analyze: {user_input}"})
            with st.spinner("Decoding Alpha..."):
                response = stream_holmes_response(st.session_state.messages, st.session_state.current_market)
                st.session_state.messages.append({"role": "assistant", "content": response})
            st.rerun()

# ================= 🗣️ 6. CHAT & CONTENT AREA =================

# A. 如果有对话，显示聊天界面
if st.session_state.messages:
    st.markdown("---")
    
    # 📌 1. 顶部钉住的市场卡片 (Context Anchor)
    if st.session_state.current_market:
        m = st.session_state.current_market
        st.markdown(f"""
        <div class="market-card">
            <div style="font-size:0.9rem; color:#9ca3af; margin-bottom:5px;">TARGET MARKET</div>
            <div style="font-size:1.2rem; color:#e5e7eb; font-weight:bold;">{m['title']}</div>
            <div style="font-size:1.8rem; color:#4ade80; font-weight:700;">{m['odds']} <span style="font-size:0.8rem; color:#9ca3af; font-weight:400;">Implied Probability</span></div>
            <div style="text-align:right; margin-top:10px;"><a href="https://polymarket.com/event/{m['slug']}" target="_blank" style="color:#ef4444; text-decoration:none;">View on Polymarket ↗</a></div>
        </div>
        """, unsafe_allow_html=True)

    # 💬 2. 聊天记录
    for i, msg in enumerate(st.session_state.messages):
        if i == 0: continue 
        with st.chat_message(msg["role"], avatar="🕵️‍♂️" if msg["role"] == "assistant" else "👤"):
            if i == 1: st.markdown(f"<div style='border-left:3px solid #dc2626; padding-left:15px;'>{msg['content']}</div>", unsafe_allow_html=True)
            else: st.write(msg["content"])

    # 🎤 3. 追问输入框 (支持搜索意图识别)
    if prompt := st.chat_input("Ask follow-up or search new topic..."):
        with st.chat_message("user", avatar="👤"):
            st.write(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # --- 🕵️‍♂️ Agent 核心：意图路由 ---
        is_search = check_search_intent(prompt)
        
        if is_search:
            with st.chat_message("assistant", avatar="🕵️‍♂️"):
                st.write(f"🔄 Detected search intent. Scanning prediction markets for: **{prompt}**...")
                with st.spinner("Searching Polymarket..."):
                    matches, _ = search_with_exa(prompt)
                    
                if matches:
                    st.session_state.current_market = matches[0]
                    st.success(f"Found: {matches[0]['title']}")
                    # 搜索完，必须让页面重绘，更新顶部的卡片
                    time.sleep(1) 
                    st.rerun()
                else:
                    st.warning("No specific market found. Proceeding with general analysis.")
        
        # 生成回复
        with st.chat_message("assistant", avatar="🕵️‍♂️"):
            with st.spinner("Thinking..."):
                response = stream_holmes_response(st.session_state.messages, st.session_state.current_market)
                st.write(response)
        st.session_state.messages.append({"role": "assistant", "content": response})

# B. 如果没有对话 (First Visit)，显示 Top 12 榜单
# ✅ 修复：Top 12 回归！
else:
    top10_markets = fetch_top_10_markets()
    if top10_markets:
        cards_html = "".join([f"""
        <a href="https://polymarket.com/event/{m['slug']}" target="_blank" class="market-item">
            <div class="m-title">{m['title']}</div>
            <div class="m-odds"><span class="tag-yes">Yes {m['yes']}¢</span><span class="tag-no">No {m['no']}¢</span></div>
        </a>""" for m in top10_markets])

        st.markdown(f"""
        <div class="top10-container">
            <div class="top10-header">Trending on Polymarket (Top 12)</div>
            <div class="top10-grid">{cards_html}</div>
        </div>
        """, unsafe_allow_html=True)
