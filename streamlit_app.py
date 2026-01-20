import streamlit as st
import requests
import json
import google.generativeai as genai
import re

# ================= 🔐 0. SAFE KEY MANAGEMENT =================
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

# ================= 🛠️ 核心依赖检测 =================
try:
    from exa_py import Exa
    EXA_AVAILABLE = True
except ImportError:
    EXA_AVAILABLE = False

# ================= 🕵️‍♂️ 1. SYSTEM CONFIGURATION =================
st.set_page_config(
    page_title="Be Holmes | Alpha Terminal",
    page_icon="🕵️‍♂️",
    layout="wide",
    initial_sidebar_state="expanded" 
)

# ================= 🎨 2. UI THEME (MOBILE PRO) =================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&family=JetBrains+Mono:wght@400;700&display=swap');
    
    .stApp { background-color: #050505; font-family: 'Inter', sans-serif; }
    
    /* 🔥 关键修复：保留左上角侧边栏开关，只隐藏右上角菜单 */
    [data-testid="stToolbar"] { visibility: hidden; height: 0%; position: fixed; }
    [data-testid="stDecoration"] { visibility: hidden; }
    header[data-testid="stHeader"] { background-color: rgba(0,0,0,0); } /* 顶部透明 */
    footer { visibility: hidden; }
    
    /* 侧边栏 */
    [data-testid="stSidebar"] { background-color: #000000; border-right: 1px solid #222; }
    
    /* 标题 */
    h1 { 
        background: linear-gradient(90deg, #FF4B4B, #FF9F9F); 
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        font-family: 'Inter', sans-serif; font-weight: 900; letter-spacing: -1px;
        border-bottom: 1px solid #222; padding-bottom: 20px;
        font-size: 3.5rem;
    }
    
    /* 状态栏的小字 */
    .status-bar { color: #666; font-size: 0.8rem; font-family: 'JetBrains Mono', monospace; margin-top:-10px; margin-bottom: 20px;}
    
    /* 输入框 */
    .stTextArea textarea { 
        background-color: #0F0F0F !important; color: #E0E0E0 !important; 
        border: 1px solid #333 !important; border-radius: 8px;
    }
    .stTextArea textarea:focus { border-color: #FF4B4B !important; }
    
    /* 主按钮 */
    .stButton button {
        background: linear-gradient(90deg, #D90429, #EF233C) !important;
        color: white !important; border: none !important;
        font-weight: 800 !important; padding: 0.8rem 1rem !important;
        border-radius: 6px !important; text-transform: uppercase; letter-spacing: 1px;
        transition: all 0.3s ease;
    }
    
    /* 侧边栏 Ticker */
    .ticker-item { padding: 12px 0; border-bottom: 1px solid #1A1A1A; font-size: 0.85rem; }
    .ticker-title { color: #CCC; margin-bottom: 4px; display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-weight: 500;}
    .ticker-price { font-family: 'JetBrains Mono', monospace; color: #FF4B4B; font-weight: bold; font-size: 1rem;}

    /* 市场卡片 */
    .market-card {
        background: #0A0A0A; border: 1px solid #222; border-left: 4px solid #D90429;
        border-radius: 8px; padding: 20px; margin-bottom: 20px;
    }
    .card-title { font-size: 1.2rem; font-weight: 700; color: #FFF; margin-bottom: 15px; }
    .card-stat { font-family: 'JetBrains Mono', monospace; color: #FF4B4B; font-size: 1.4rem; font-weight: 700; }
    
    /* 报告盒子 */
    .report-box {
        background-color: #0E0E0E; border: 1px solid #222; padding: 25px;
        border-radius: 12px; margin-top: 20px; color: #CCC; line-height: 1.6;
    }
    
    /* 底部 Expander (Manual) 样式 */
    .streamlit-expanderHeader {
        background-color: #0A0A0A !important; color: #888 !important; border: 1px solid #222 !important;
        border-radius: 6px !important; font-family: 'JetBrains Mono', monospace; font-size: 0.8rem !important;
    }
    
    /* 📱 手机端适配核心代码 */
    @media only screen and (max-width: 768px) {
        h1 { font-size: 2.2rem !important; padding-bottom: 15px !important; }
        .stButton button { width: 100% !important; margin-top: 10px !important; padding: 12px !important; }
        .market-card { padding: 15px !important; }
        .report-box { font-size: 0.9rem !important; padding: 15px !important; }
        /* 强制侧边栏在手机上行为正常 */
        section[data-testid="stSidebar"] { width: 80% !important; } 
    }
</style>
""", unsafe_allow_html=True)

# ================= 🧠 3. LOGIC CORE =================

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
        search_response = exa.search(
            f"prediction market about {search_query}",
            num_results=4, type="neural", include_domains=["polymarket.com"]
        )
        for result in search_response.results:
            match = re.search(r'polymarket\.com/(?:event|market)/([^/]+)', result.url)
            if match:
                slug = match.group(1)
                if slug not in ['profile', 'login', 'leaderboard', 'rewards'] and slug not in seen_ids:
                    market_data = fetch_poly_details(slug)
                    if market_data:
                        markets_found.extend(market_data)
                        seen_ids.add(slug)
    except Exception as e: print(f"Search error: {e}")
    return markets_found, search_query

def fetch_poly_details(slug):
    valid_markets = []
    try:
        url = f"https://gamma-api.polymarket.com/events?slug={slug}"
        resp = requests.get(url, timeout=3).json()
        if isinstance(resp, list) and resp:
            for m in resp[0].get('markets', [])[:2]:
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
        outcomes = json.loads(m.get('outcomes', '[]')) if isinstance(m.get('outcomes'), str) else m.get('outcomes')
        prices = json.loads(m.get('outcomePrices', '[]')) if isinstance(m.get('outcomePrices'), str) else m.get('outcomePrices')
        odds_display = "N/A"
        if outcomes and prices:
            odds_display = f"{outcomes[0]}: {float(prices[0])*100:.1f}%"
        return {
            "title": m.get('question', 'Unknown'),
            "odds": odds_display,
            "volume": float(m.get('volume', 0)),
            "slug": m.get('slug', '') or m.get('market_slug', '')
        }
    except: return None

def consult_holmes(user_input, market_data):
    if not GOOGLE_API_KEY: return "AI Key Missing."
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        lang = detect_language(user_input)
        
        if lang == "CHINESE":
            lang_instruction = "IMPORTANT: Respond in **CHINESE (中文)**."
            role_desc = "你现在是 **Be Holmes**，一位极度理性、只相信数据和博弈论的顶级宏观对冲基金经理。"
        else:
            lang_instruction = "IMPORTANT: Respond in **ENGLISH**."
            role_desc = "You are **Be Holmes**, a legendary Wall Street Macro Hedge Fund Manager. Rational, cynical, and data-driven."

        market_context = ""
        if market_data:
            m = market_data[0]
            market_context = f"Target: {m['title']} | Odds: {m['odds']} | Volume: ${m['volume']:,.0f}"
        else:
            market_context = "No specific prediction market found."

        prompt = f"""
        {role_desc}
        [Intel]: "{user_input}"
        [Market Data]: {market_context}
        {lang_instruction}
        
        **MISSION: DECODE ALPHA.**
        
        **Analysis Framework:**
        1.  **🕵️‍♂️ Priced-in Check:** Is this "Old News"?
        2.  **⚖️ Bluff vs. Reality:** Rhetoric vs Action.
        3.  **🧠 The Verdict:**
            - **🟢 AGGRESSIVE BUY:** Odds < 20% & New Intel.
            - **🟡 CONTRARIAN:** Market Overreaction.
            - **⚪ WAIT:** Priced in.
        
        **Output Format:**
        > One sentence sleek summary.
        ### 🧠 Strategic Analysis
        * **Market Psychology:** ...
        * **Risk/Reward:** ...
        * **Final Call:** [BUY / SELL / WAIT]
        """
        return model.generate_content(prompt).text
    except Exception as e: return f"AI Error: {e}"

# ================= 🖥️ 5. MAIN INTERFACE =================

# --- A. 侧边栏：实时行情 ---
with st.sidebar:
    st.markdown("### 📡 LIVE TICKER")
    if KEYS_LOADED:
        try:
            url = "https://gamma-api.polymarket.com/markets?limit=10&sort=volume&closed=false"
            live_mkts = requests.get(url, timeout=3).json()
            for m in live_mkts:
                p = normalize_data(m)
                if p:
                    st.markdown(f"""
                    <div class="ticker-item">
                        <span class="ticker-title">{p['title']}</span>
                        <span class="ticker-price">{p['odds']}</span>
                        <span style="color:#555; float:right; font-size:0.75rem;">${p['volume']/1000000:.1f}M</span>
                    </div>
                    """, unsafe_allow_html=True)
        except: st.warning("Connecting...")
    else:
        st.error("Keys Missing")
    
    st.markdown("---")
    st.caption("ℹ️ Data from Polymarket Gamma API")

# --- B. 主界面 ---
st.title("Be Holmes")
st.caption("THE GENIUS TRADER | V2.5 MOBILE PRO")

# 状态栏 (提示侧边栏存在)
if KEYS_LOADED:
    st.markdown('<p class="status-bar">🟢 System Online | 📡 <span style="color:#555;">Live Feed in Sidebar (Top Left >)</span></p>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# 输入区
user_news = st.text_area("Intelligence Injection...", height=120, placeholder="Paste Intel here... (e.g. 特朗普宣布2月1日加征关税 / SpaceX IPO)")
ignite_btn = st.button("🔍 DECODE ALPHA", use_container_width=True)

# 执行逻辑
if ignite_btn:
    if not KEYS_LOADED:
        st.error("❌ API Keys not found in Secrets.")
    elif not user_news:
        st.warning("⚠️ Evidence required for analysis.")
    else:
        with st.status("🧠 Holmes is processing...", expanded=True) as status:
            st.write("🛰️ Exa Neural Engine: Semantic Mapping...")
            matches, keyword = search_with_exa(user_news)
            
            if matches:
                st.write(f"✅ Contract Locked: {matches[0]['title']}")
            else:
                st.warning(f"⚠️ No direct asset found for '{keyword}'. Switching to Macro Inference.")
            
            st.write("⚖️ Bayesian Inference Running...")
            report = consult_holmes(user_news, matches)
            status.update(label="✅ Alpha Generated", state="complete", expanded=False)

        if matches:
            m = matches[0]
            st.markdown("### 🎯 Target Asset")
            st.markdown(f"""
            <div class="market-card">
                <div class="card-title">{m['title']}</div>
                <div style="display:flex; justify-content:space-between; align-items:flex-end;">
                    <div>
                        <span class="card-stat">{m['odds']}</span>
                        <div class="card-sub">Implied Probability</div>
                    </div>
                    <div style="text-align:right;">
                        <span style="color:#CCC; font-weight:bold;">${m['volume']:,.0f}</span>
                        <div class="card-sub">24h Volume</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            link = f"https://polymarket.com/event/{m['slug']}"
            st.markdown(f"<a href='{link}' target='_blank'><button class='stButton' style='width:100%; background:#D90429; color:white; padding:12px; border-radius:6px; border:none; font-weight:bold; cursor:pointer;'>🚀 EXECUTE TRADE</button></a>", unsafe_allow_html=True)

        st.markdown("### 🧠 Strategic Report")
        st.markdown(f"<div class='report-box'>{report}</div>", unsafe_allow_html=True)

# --- C. 底部 Manual (不喧宾夺主，专业范) ---
st.markdown("<br><br><br>", unsafe_allow_html=True)
st.markdown("---")

# 使用 Expander 折叠起来，默认不显示，不抢主界面
with st.expander("📘 OPERATIONAL PROTOCOL & CREDIT"):
    
    # 1. Exa.ai 致谢 (专业卡片)
    st.markdown("""
    <div style="background:#0F0F0F; padding:20px; border-radius:8px; border:1px solid #333; margin-bottom:20px;">
        <div style="font-size:0.7rem; color:#666; font-weight:bold; letter-spacing:1px; margin-bottom:5px;">CORE SEMANTIC ENGINE</div>
        <div style="font-size:1.5rem; color:#FF4B4B; font-weight:900; margin-bottom:5px;">POWERED BY Exa.ai</div>
        <div style="font-size:0.85rem; color:#888;">
            Utilizing state-of-the-art Neural Embeddings for cross-lingual intent mapping and entity resolution.
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # 2. 专业协议内容
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### 🇨🇳 协议说明")
        st.markdown("""
        * **系统架构:** 基于 **RAG** 的异构金融数据决策终端。
        * **语义层 (Semantic Layer):** 由 **Exa.ai** 提供支持，将中文模糊非结构化文本实时映射为链上资产实体。
        * **推理层 (Inference Layer):** 集成 **Gemini Pro**，基于贝叶斯博弈论 (Bayesian Game Theory) 计算市场共识预期差。
        * **信号定义:** * 🟢 **Aggressive Buy:** 市场定价偏差 > 30%。
            * ⚪ **Priced-in:** 市场已充分消化该情报。
        """)
    with c2:
        st.markdown("#### 🇺🇸 Protocol Specs")
        st.markdown("""
        * **Architecture:** **RAG-based** Heterogeneous Financial Decision Terminal.
        * **Semantic Layer:** Powered by **Exa.ai**. Maps unstructured intent to on-chain assets via Neural Search.
        * **Inference Layer:** **Gemini Pro** driven. Calculates Consensus Gaps using Bayesian models.
        * **Signals:**
            * 🟢 **Aggressive Buy:** Mispricing > 30%.
            * ⚪ **Priced-in:** Information fully absorbed.
        """)
