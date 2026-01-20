import streamlit as st
import requests
import json
import google.generativeai as genai
import re

# ================= 🔐 0. SAFE KEY MANAGEMENT =================
# 自动从 Streamlit Secrets 读取 Key，防止 GitHub 泄露
try:
    EXA_API_KEY = st.secrets["EXA_API_KEY"]
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
    KEYS_LOADED = True
except FileNotFoundError:
    EXA_API_KEY = None
    GOOGLE_API_KEY = None
    KEYS_LOADED = False
except KeyError:
    # 处理 secrets 存在但 key 缺失的情况
    EXA_API_KEY = st.secrets.get("EXA_API_KEY", None)
    GOOGLE_API_KEY = st.secrets.get("GOOGLE_API_KEY", None)
    KEYS_LOADED = bool(EXA_API_KEY and GOOGLE_API_KEY)

# 配置 Gemini
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

# ================= 🎨 2. UI THEME (MOBILE OPTIMIZED) =================
st.markdown("""
<style>
    /* 1. 全局基础 */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&family=JetBrains+Mono:wght@400;700&display=swap');
    
    .stApp { 
        background-color: #050505; 
        font-family: 'Inter', sans-serif;
    }
    
    /* 隐藏杂项 */
    [data-testid="stToolbar"] { visibility: hidden; height: 0%; position: fixed; }
    header { visibility: hidden; }
    footer { visibility: hidden; }
    
    /* 2. 侧边栏 */
    [data-testid="stSidebar"] { 
        background-color: #000000; 
        border-right: 1px solid #222; 
    }
    
    /* 3. 标题体系 (Desktop 默认) */
    h1 { 
        background: linear-gradient(90deg, #FF4B4B, #FF9F9F); 
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        font-family: 'Inter', sans-serif; font-weight: 900; letter-spacing: -1px;
        border-bottom: 2px solid #222; padding-bottom: 20px;
        font-size: 3rem; /* 电脑端大字体 */
    }
    h3 { color: #FF4B4B !important; font-weight: 700; }
    
    /* 4. 输入框 */
    .stTextArea textarea { 
        background-color: #0F0F0F !important; 
        color: #E0E0E0 !important; 
        border: 1px solid #333 !important; 
        border-radius: 8px;
        font-family: 'Inter', sans-serif;
    }
    .stTextArea textarea:focus { border-color: #FF4B4B !important; box-shadow: 0 0 10px rgba(255, 75, 75, 0.2); }
    
    /* 5. 按钮 (Red Neon) */
    .stButton button {
        background: linear-gradient(90deg, #D90429, #EF233C) !important;
        color: white !important; 
        border: none !important;
        font-weight: 800 !important;
        padding: 0.6rem 1rem !important;
        border-radius: 6px !important;
        text-transform: uppercase;
        letter-spacing: 1px;
        transition: all 0.3s ease;
    }
    
    /* 6. 市场卡片 */
    .market-card {
        background: #0A0A0A;
        border: 1px solid #222;
        border-left: 4px solid #D90429;
        border-radius: 8px;
        padding: 20px;
        margin-bottom: 20px;
        transition: all 0.3s ease;
    }
    .card-title { font-size: 1.2rem; font-weight: 700; color: #FFF; margin-bottom: 15px; line-height: 1.4; }
    .card-stat { font-family: 'JetBrains Mono', monospace; color: #FF4B4B; font-size: 1.4rem; font-weight: 700; }
    .card-sub { color: #666; font-size: 0.85rem; }

    /* 7. 报告盒子 */
    .report-box {
        background-color: #0E0E0E; 
        border: 1px solid #222; 
        padding: 25px;
        border-radius: 12px; 
        margin-top: 20px;
        color: #CCC;
        line-height: 1.6;
        font-size: 0.95rem;
    }
    
    /* 8. Ticker */
    .ticker-item {
        padding: 12px 0;
        border-bottom: 1px solid #1A1A1A;
        font-size: 0.85rem;
    }
    .ticker-title { color: #CCC; margin-bottom: 4px; display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-weight: 500;}
    .ticker-price { font-family: 'JetBrains Mono', monospace; color: #FF4B4B; font-weight: bold; font-size: 1rem;}
    .ticker-vol { color: #555; float: right; font-size: 0.75rem; margin-top: 2px;}

    /* ========== 📱 MOBILE RESPONSIVE TWEAKS (手机端优化核心) ========== */
    @media only screen and (max-width: 768px) {
        /* 缩小标题，防止换行过于夸张 */
        h1 { font-size: 2rem !important; padding-bottom: 10px !important; }
        
        /* 调整卡片内边距，节省屏幕空间 */
        .market-card { padding: 15px !important; }
        
        /* 字体调整 */
        .card-title { font-size: 1.1rem !important; }
        .card-stat { font-size: 1.2rem !important; }
        
        /* 按钮全宽，方便手指点击 */
        .stButton button { width: 100% !important; margin-top: 5px !important; }
        
        /* 报告文字稍微调小 */
        .report-box { padding: 15px !important; font-size: 0.9rem !important; }
        
        /* 顶部布局优化：让 Manual 按钮不那么突兀 */
        div[data-testid="column"] { width: 100% !important; flex: 1 1 auto !important; min-width: 0px !important; }
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
    except Exception as e:
        print(f"Search error: {e}")
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

# ================= 🌟 4. GENIUS ANALYST PROMPT =================

def consult_holmes(user_input, market_data):
    if not GOOGLE_API_KEY: return "AI Key Missing."
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        lang = detect_language(user_input)
        
        if lang == "CHINESE":
            lang_instruction = "IMPORTANT: Respond in **CHINESE (中文)**."
            role_desc = "你现在是 **Be Holmes**，一位拥有 20 年经验的华尔街顶级宏观对冲基金经理，也是预测市场套利天才。你的性格极度理性，甚至有点愤世嫉俗，你只相信利益和概率，不相信政客的嘴炮。"
        else:
            lang_instruction = "IMPORTANT: Respond in **ENGLISH**."
            role_desc = "You are **Be Holmes**, a legendary Wall Street Macro Hedge Fund Manager and Prediction Market Genius. You are hyper-rational and cynical."

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
        1.  **🕵️‍♂️ Priced-in Check:** Is this "Old News"? If Trump tweeted 3 days ago, the market already knows. Don't be a sucker.
        2.  **⚖️ Bluff vs. Reality:** For political events, distinguish "Rhetoric" (Threats) from "Action" (Executive Orders).
        3.  **🧠 The Verdict:**
            - **🟢 AGGRESSIVE BUY:** If market is asleep (Odds < 20%) and news is NEW/REAL.
            - **🟡 CONTRARIAN:** If market is overreacting to fake news.
            - **⚪ WAIT:** If news is priced in.
        
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

# --- A. 侧边栏 ---
with st.sidebar:
    st.markdown("### 📡 LIVE FEED")
    st.caption("Top 10 Active Markets")
    
    if KEYS_LOADED:
        try:
            url = "https://gamma-api.polymarket.com/markets?limit=10&sort=volume&closed=false"
            live_mkts = requests.get(url, timeout=3).json()
            for m in live_mkts:
                p = normalize_data(m)
                if p:
                    st.markdown(f"""
                    <div class="ticker-item">
                        <span class="ticker-title" title="{p['title']}">{p['title']}</span>
                        <span class="ticker-price">{p['odds']}</span>
                        <span class="ticker-vol">${p['volume']/1000000:.1f}M</span>
                    </div>
                    """, unsafe_allow_html=True)
        except:
            st.warning("⚠️ Connection slow...")
    else:
        st.error("🔒 Keys Missing")
        st.caption("Add Keys to Secrets.")

    st.markdown("---")
    if KEYS_LOADED:
        st.success("🟢 System: **Online**")
    else:
        st.error("🔴 System: **Offline**")

# --- B. 顶部：标题 & 手册按钮 (移动端优化布局) ---
# 在移动端，columns 会自动堆叠。我们通过 CSS 优化了间距。
c1, c2 = st.columns([5, 2])
with c1:
    st.title("Be Holmes")
    st.caption("THE GENIUS TRADER | V2.1 MOBILE")

with c2:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("📘 Manual"):
        @st.dialog("User Manual")
        def show_manual():
            lang_mode = st.radio("Language / 语言", ["English", "中文"], horizontal=True)
            st.markdown("---")
            if lang_mode == "中文":
                st.markdown("""
                ### 🕵️‍♂️ Be Holmes 使用指南
                **核心功能：** 双语语义搜索 + 贝叶斯博弈分析。
                **如何使用：** 输入任意新闻（中英文皆可），AI自动寻找预测市场合约并给出交易建议。
                **免责声明：** 仅供参考，不构成投资建议。
                """)
            else:
                st.markdown("""
                ### 🕵️‍♂️ User Guide
                **Core:** Neural Search + Game Theory Analysis.
                **How-to:** Input any news. AI finds the contract and gives alpha strategy.
                **Disclaimer:** Not financial advice.
                """)
        show_manual()

st.markdown("---")

# --- C. 核心交互区 ---
user_news = st.text_area("Input Intel / News...", height=120, placeholder="Paste news here... (e.g. 特朗普宣布2月1日加征关税 / SpaceX IPO)")
ignite_btn = st.button("🔍 DECODE ALPHA", use_container_width=True)

if ignite_btn:
    if not KEYS_LOADED:
        st.error("❌ API Keys not found in Secrets.")
    elif not user_news:
        st.warning("⚠️ Please input intel first.")
    else:
        with st.status("🧠 Holmes is thinking...", expanded=True) as status:
            st.write("🛰️ Exa Sniper: Scanning Polymarket...")
            matches, keyword = search_with_exa(user_news)
            
            if matches:
                st.write(f"✅ Target Locked: {matches[0]['title']}")
            else:
                st.warning(f"⚠️ No direct contract found for '{keyword}'. Switching to Macro Mode.")
            
            st.write("⚖️ Calculating Bayesian Probabilities...")
            report = consult_holmes(user_news, matches)
            status.update(label="✅ Strategy Ready", state="complete", expanded=False)

        if matches:
            m = matches[0]
            st.markdown("### 🎯 Target Contract")
            st.markdown(f"""
            <div class="market-card">
                <div class="card-title">{m['title']}</div>
                <div style="display:flex; justify-content:space-between; align-items:flex-end;">
                    <div>
                        <span class="card-stat">{m['odds']}</span>
                        <div class="card-sub">Current Probability</div>
                    </div>
                    <div style="text-align:right;">
                        <span style="color:#CCC; font-weight:bold;">${m['volume']:,.0f}</span>
                        <div class="card-sub">Volume</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            link = f"https://polymarket.com/event/{m['slug']}"
            st.markdown(f"<a href='{link}' target='_blank'><button class='stButton' style='width:100%; border-radius:8px; background:#D90429; color:white; padding:12px; border:none; font-weight:bold; cursor:pointer; font-size:1rem;'>🚀 TRADE ON POLYMARKET</button></a>", unsafe_allow_html=True)

        st.markdown("### 🧠 Strategic Report")
        st.markdown(f"<div class='report-box'>{report}</div>", unsafe_allow_html=True)
