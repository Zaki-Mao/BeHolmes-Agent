import streamlit as st
import requests
import json
import google.generativeai as genai
import time

# ================= 🕵️‍♂️ 1. SYSTEM CONFIGURATION =================
st.set_page_config(
    page_title="Be Holmes | Alpha Hunter",
    page_icon="🕵️‍♂️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ================= 🎨 2. UI DESIGN (Magma Red - Professional) =================
st.markdown("""
<style>
    /* --- HIDE STREAMLIT SYSTEM ELEMENTS (CLEAN MODE) --- */
    /* 隐藏右上角 Hamburger Menu, Share, Edit, Star */
    [data-testid="stToolbar"] {
        visibility: hidden;
        height: 0%;
        position: fixed;
    }
    /* 隐藏底部的 "Made with Streamlit" */
    footer {
        visibility: hidden;
    }
    /* 隐藏顶部的彩色线条装饰 */
    header {
        visibility: hidden;
    }

    /* --- Global Background: Void Black --- */
    .stApp { background-color: #050505; font-family: 'Roboto Mono', monospace; }
    [data-testid="stSidebar"] { background-color: #000000; border-right: 1px solid #1a1a1a; }
    
    /* --- Typography: Magma Gradient --- */
    h1 { 
        background: linear-gradient(90deg, #FF4500, #E63946); 
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-family: 'Georgia', serif; 
        font-weight: 800;
        border-bottom: 2px solid #331111; 
        padding-bottom: 15px;
        text-shadow: 0 0 20px rgba(255, 69, 0, 0.2);
    }
    
    /* --- Text Colors --- */
    h3 { color: #FF7F50 !important; } 
    p, label, .stMarkdown, .stText, li, div, span { color: #A0A0A0 !important; }
    strong { color: #FFF !important; font-weight: 600; } 
    a { text-decoration: none !important; border-bottom: none !important; }

    /* --- Input Fields: High Contrast --- */
    .stTextArea textarea, .stNumberInput input, .stTextInput input, .stSelectbox div[data-baseweb="select"] { 
        background-color: #0A0A0A !important; 
        color: #E63946 !important; 
        border: 1px solid #333 !important; 
        border-radius: 6px;
    }
    .stTextArea textarea:focus, .stTextInput input:focus { 
        border: 1px solid #FF4500 !important; 
        box-shadow: 0 0 15px rgba(255, 69, 0, 0.2); 
    }
    
    /* --- Button Styles --- */
    .stButton button {
        width: 100%;
        border-radius: 6px;
        font-weight: bold;
        transition: all 0.3s ease;
    }
    
    /* Primary Action Button (Red) */
    div[data-testid="column"]:nth-of-type(1) div.stButton > button { 
        background: linear-gradient(90deg, #8B0000, #FF4500); 
        color: #FFF; 
        border: none;
        box-shadow: 0 4px 15px rgba(255, 69, 0, 0.3);
    }
    div[data-testid="column"]:nth-of-type(1) div.stButton > button:hover { 
        box-shadow: 0 6px 25px rgba(255, 69, 0, 0.6);
        transform: translateY(-2px);
    }

    /* Secondary Button (Ghost) */
    div[data-testid="column"]:nth-of-type(2) div.stButton > button { 
        background-color: transparent; 
        color: #666; 
        border: 1px solid #333; 
    }
    div[data-testid="column"]:nth-of-type(2) div.stButton > button:hover { 
        border-color: #FF4500;
        color: #FF4500;
        background-color: #1a0505;
    }

    /* --- Report: Execution Button --- */
    .execute-btn {
        background: linear-gradient(90deg, #FF4500, #FFD700); 
        border: none;
        color: #000;
        width: 100%;
        padding: 15px;
        font-weight: 900;
        font-size: 16px;
        cursor: pointer;
        border-radius: 6px;
        text-transform: uppercase;
        letter-spacing: 2px;
        box-shadow: 0 5px 15px rgba(255, 69, 0, 0.3);
        margin-top: 20px;
    }
    .execute-btn:hover { transform: scale(1.02); box-shadow: 0 8px 25px rgba(255, 69, 0, 0.5); }

    /* --- Report: Live Ticker HUD --- */
    .ticker-box {
        background-color: #080808;
        border: 1px solid #222;
        border-left: 4px solid #FF4500;
        color: #FF4500;
        font-family: 'Courier New', monospace;
        padding: 15px;
        margin: 15px 0;
        font-size: 1.05em;
        font-weight: bold;
        display: flex;
        align-items: center;
    }
</style>
""", unsafe_allow_html=True)

# ================= 🔐 3. SECURITY LAYER =================
try:
    if "GEMINI_KEY" in st.secrets:
        api_key = st.secrets["GEMINI_KEY"]
    else:
        st.error("⚠️ KEY ERROR: Please configure .streamlit/secrets.toml")
        st.stop()
except Exception as e:
    st.error(f"⚠️ SYSTEM ERROR: {e}")
    st.stop()

# ================= 📡 4. DATA ENGINE (DEEP SONAR) =================

def parse_market_data(data):
    """Parses raw API JSON into clean market objects."""
    markets_clean = []
    if not data: return []
    for event in data:
        title = event.get('title', 'Unknown')
        slug = event.get('slug', '')
        all_markets = event.get('markets', [])
        if not all_markets: continue

        # Find liquid market
        best_market = None
        max_volume = -1
        for m in all_markets:
            if m.get('closed') is True: continue    
            try:
                vol = float(m.get('volume', 0))
                if vol > max_volume: max_volume = vol; best_market = m
            except: continue
        
        if not best_market: best_market = all_markets[0]

        # Parse Odds
        odds_display = "N/A"
        try:
            raw_outcomes = best_market.get('outcomes', '["Yes", "No"]')
            outcomes = json.loads(raw_outcomes) if isinstance(raw_outcomes, str) else raw_outcomes
            raw_prices = best_market.get('outcomePrices', '[]')
            prices = json.loads(raw_prices) if isinstance(raw_prices, str) else raw_prices

            odds_list = []
            if prices and len(prices) == len(outcomes):
                for o, p in zip(outcomes, prices):
                    val = float(p) * 100
                    if val > 0.5: odds_list.append(f"{o}: {val:.1f}%")
                odds_display = " | ".join(odds_list)
            else: odds_display = f"Price: {float(prices[0])*100:.1f}%"
        except: odds_display = "No Data"
        
        markets_clean.append({"title": title, "odds": odds_display, "slug": slug, "volume": max_volume})
    return markets_clean

@st.cache_data(ttl=300) 
def fetch_top_markets():
    """Baseline: Fetch top volume markets."""
    try:
        response = requests.get("https://gamma-api.polymarket.com/events?limit=50&active=true&closed=false&sort=volume", headers={"User-Agent": "BeHolmes/1.0"}, timeout=5)
        return parse_market_data(response.json()) if response.status_code == 200 else []
    except: return []

def deep_sonar_search(keyword):
    """Active Sonar: Search entire database by keyword."""
    if not keyword: return []
    try:
        # 'q' parameter searches title, description, and tags
        response = requests.get(f"https://gamma-api.polymarket.com/events?limit=20&active=true&closed=false&q={keyword}", headers={"User-Agent": "BeHolmes/1.0"}, timeout=5)
        return parse_market_data(response.json()) if response.status_code == 200 else []
    except: return []

def extract_keywords_with_ai(user_text, key):
    """Uses Gemini to distill user input into search queries."""
    if not user_text: return None
    try:
        genai.configure(api_key=key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        # Prompt to extract English keywords regardless of input language
        response = model.generate_content(f"Extract 1-2 most important English keywords for a search engine from this text. Text: '{user_text}'. Output strictly format: keyword1 keyword2")
        return response.text.strip()
    except: return None

# ================= 🧠 5. INTELLIGENCE LAYER (The Expert) =================

def consult_holmes(user_evidence, market_list, key):
    try:
        genai.configure(api_key=key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        markets_text = "\n".join([f"- {m['title']} [Odds: {m['odds']}]" for m in market_list[:50]])
        
        prompt = f"""
        Role: You are **Be Holmes**, an omniscient financial intelligence agent specializing in prediction markets.
        Your goal is to perform a deep-dive analysis, connecting news events to market probabilities with surgical precision.

        [Evidence / Lead]: "{user_evidence}"
        [Market Data Scan]: 
        {markets_text}

        **PROTOCOL:**
        1. **Language Detection:** - IF input is Chinese -> Output strictly in CHINESE.
           - ELSE -> Output strictly in ENGLISH.
        
        2. **Analysis Framework:**
           - Identify the specific market closest to the evidence.
           - Analyze the "Probability Gap": Difference between market odds and actual event probability.
           - Provide a clear Trading Strategy (Buy/Sell/Hold) with specific entry/exit points.

        **OUTPUT FORMAT (Strict Markdown):**
        
        ---
        ### 🕵️‍♂️ Case File: [Exact Market Title]
        
        <div class="ticker-box">
        🔥 LIVE SNAPSHOT: [Insert Live Odds Here]
        </div>
        
        **1. ⚖️ The Verdict**
        - **Signal:** 🟢 STRONG BUY / 🔴 SELL / ⚠️ WATCH
        - **Confidence Score:** **[0-100]%**
        - **Suggested Holding Period:** [e.g., Intraday, 48 Hours, Until Official Filing]
        
        **2. 🧠 Deep Logic (The "Why")**
        > *[Mandatory: Write a detailed paragraph. Explain the causal link. Why is the market wrong? What information are other traders missing? Use second-order thinking.]*
        
        **3. 🛡️ Risk & Execution**
        - **The Trap:** [What could go wrong? e.g., Ambiguous wording, Delay]
        - **Exit Strategy:** [When to take profit or cut loss]
        ---
        """
        response = model.generate_content(prompt)
        
        # Inject the Execution Button
        btn_html = """
        <br>
        <a href='https://polymarket.com/' target='_blank' style='text-decoration:none;'>
        <button class='execute-btn'>🚀 EXECUTE TRADE ON POLYMARKET</button>
        </a>
        """
        return response.text + btn_html
    except Exception as e: return f"❌ Intelligence Error: {str(e)}"

# ================= 📘 6. MANUAL MODULE =================

@st.dialog("📘 Be Holmes Manual", width="large")
def open_manual():
    lang = st.radio("Language / 语言", ["English", "中文"], horizontal=True)
    st.markdown("---")
    
    if lang == "中文":
        st.markdown("""
        ### 🕵️‍♂️ 系统简介
        **Be Holmes** 是基于 Gemini 2.5 的全知全能金融侦探。它具备"深海声纳"能力，能从数千个预测市场中精准定位与你输入新闻相关的标的。

        ### 🚀 核心工作流
        1.  **关键词萃取:** 系统自动理解你的自然语言输入（新闻/传闻）。
        2.  **全域遍历:** 绕过热门榜单，扫描 Polymarket 全数据库。
        3.  **Alpha 推理:** 结合实时赔率与事件逻辑，输出交易胜率分析。
        
        ### 🛠️ 操作指南
        - **输入:** 在主文本框粘贴新闻链接或文字。
        - **调查:** 点击红色 **INVESTIGATE** 按钮。
        - **决策:** 阅读生成的深度报告，根据置信度执行交易。
        """)
    else:
        st.markdown("""
        ### 🕵️‍♂️ System Profile
        **Be Holmes** is an omniscient financial detective powered by Gemini 2.5. It features "Deep Sonar" capability to pinpoint prediction markets relevant to your intel from thousands of active contracts.

        ### 🚀 Core Workflow
        1.  **Keyword Extraction:** Distills your natural language input into search vectors.
        2.  **Deep Traversal:** Scans the entire Polymarket database (bypassing Top 100).
        3.  **Alpha Reasoning:** Synthesizes real-time odds with causal logic to find mispriced assets.

        ### 🛠️ User Guide
        - **Input:** Paste news, rumors, or X links in the main text box.
        - **Investigate:** Click the Red **INVESTIGATE** button.
        - **Execute:** Review the deep logic report and trade based on the confidence score.
        """)

# ================= 🖥️ 7. MAIN INTERFACE =================

# --- Sidebar ---
with st.sidebar:
    st.markdown("## 💼 DETECTIVE'S TOOLKIT")
    st.markdown("`CORE: GEMINI-2.5-FLASH`")
    st.success("🔒 System: Online")
    st.markdown("---")
    st.markdown("### 🌊 Market Sonar (Top 5)")
    with st.spinner("Initializing Sonar..."):
        top_markets = fetch_top_markets()
    if top_markets:
        for m in top_markets[:5]:
            st.caption(f"📅 {m['title']}")
            st.code(f"{m['odds']}") 
    else: st.error("⚠️ Data Stream Offline")

# --- Main Stage ---
st.title("Be Holmes")
st.caption("EVENT-DRIVEN INTELLIGENCE | SECOND-ORDER CAUSAL REASONING") 
st.markdown("---")

# 1. Evidence Input
st.markdown("### 📁 EVIDENCE INPUT")
user_news = st.text_area(
    "Input News / Rumors / X Links...", 
    height=150, 
    placeholder="Paste detailed intel here... (e.g., 'Rumors that iPhone 18 will remove all buttons')", 
    label_visibility="collapsed"
)

# 2. Action Zone (Aligned Buttons)
col_btn_main, col_btn_help = st.columns([4, 1])

with col_btn_main:
    ignite_btn = st.button("🔍 INVESTIGATE", use_container_width=True)

with col_btn_help:
    help_btn = st.button("📘 Manual", use_container_width=True)

# 3. Logic Trigger
if help_btn:
    open_manual()

if ignite_btn:
    if not user_news:
        st.warning("⚠️ Evidence required to initiate investigation.")
    else:
        # --- LOGIC: DEEP SONAR & ANALYSIS ---
        with st.status("🚀 Initiating Deep Scan...", expanded=True) as status:
            st.write("🧠 Extracting semantic keywords (Gemini 2.5)...")
            search_keywords = extract_keywords_with_ai(user_news, api_key)
            
            sonar_markets = []
            if search_keywords:
                st.write(f"🌊 Active Sonar Ping: '{search_keywords}'...")
                sonar_markets = deep_sonar_search(search_keywords)
                st.write(f"✅ Found {len(sonar_markets)} specific markets in deep storage.")
            
            # Merge & Deduplicate
            combined_markets = sonar_markets + top_markets
            seen_slugs = set()
            unique_markets = []
            for m in combined_markets:
                if m['slug'] not in seen_slugs: unique_markets.append(m); seen_slugs.add(m['slug'])
            
            st.write("⚖️ Analyzing Probability Gap...")
            status.update(label="✅ Investigation Complete", state="complete", expanded=False)

        if not unique_markets: st.error("⚠️ No relevant markets found in the database.")
        else:
            with st.spinner(">> Deducing Alpha..."):
                result = consult_holmes(user_news, unique_markets, api_key)
                st.markdown("---")
                st.markdown("### 📝 INVESTIGATION REPORT")
                st.markdown(result, unsafe_allow_html=True)
