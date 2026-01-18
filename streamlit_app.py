import streamlit as st
import requests
import json
import google.generativeai as genai
import time

# ================= 🕵️‍♂️ 1. 基础配置 =================
st.set_page_config(
    page_title="Be Holmes | Alpha Hunter",
    page_icon="🕵️‍♂️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ================= 🎨 2. 五行风水 UI (Magma Red - Pure Edition) =================
st.markdown("""
<style>
    /* --- 全局背景：深邃黑 --- */
    .stApp { background-color: #050505; font-family: 'Roboto Mono', monospace; }
    [data-testid="stSidebar"] { background-color: #000000; border-right: 1px solid #1a1a1a; }
    
    /* --- 标题：熔岩渐变 (Fire Logic) --- */
    h1 { 
        background: linear-gradient(90deg, #FF4500, #E63946); /* 橙红到深红 */
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-family: 'Georgia', serif; 
        font-weight: 800;
        border-bottom: 2px solid #331111; 
        padding-bottom: 15px;
        text-shadow: 0 0 20px rgba(255, 69, 0, 0.3);
    }
    
    /* --- 文本色调 --- */
    h3 { color: #FF7F50 !important; } /* 珊瑚红副标题 */
    p, label, .stMarkdown, .stText, li, div, span { color: #A0A0A0 !important; }
    strong { color: #FFF !important; font-weight: 600; } 
    a { text-decoration: none !important; border-bottom: none !important; }

    /* --- 输入框：黑红科技感 --- */
    .stTextArea textarea, .stNumberInput input, .stTextInput input, .stSelectbox div[data-baseweb="select"] { 
        background-color: #0A0A0A !important; 
        color: #E63946 !important; /* 文字也是红色 */
        border: 1px solid #333 !important; 
        border-radius: 8px;
    }
    .stTextArea textarea:focus, .stTextInput input:focus { 
        border: 1px solid #FF4500 !important; 
        box-shadow: 0 0 15px rgba(255, 69, 0, 0.2); 
    }
    
    /* --- 按钮样式统一 --- */
    .stButton button {
        width: 100%;
        border-radius: 6px;
        font-weight: bold;
        transition: all 0.3s ease;
    }
    
    /* 针对第一个按钮 (调查) - 红色实心 */
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

    /* 针对第二个按钮 (说明书) - 幽灵边框模式 */
    div[data-testid="column"]:nth-of-type(2) div.stButton > button { 
        background-color: transparent; 
        color: #888; 
        border: 1px solid #444; 
    }
    div[data-testid="column"]:nth-of-type(2) div.stButton > button:hover { 
        border-color: #FF4500;
        color: #FF4500;
        background-color: #1a0505;
    }

    /* --- 报告中的执行按钮 (Action) --- */
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

    /* --- 实时盘口框 (HUD) --- */
    .ticker-box {
        background-color: #080808;
        border: 1px solid #222;
        border-left: 4px solid #FF4500; /* 红线 */
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

# ================= 🔐 3. 安全层 =================
try:
    if "GEMINI_KEY" in st.secrets:
        api_key = st.secrets["GEMINI_KEY"]
    else:
        st.error("⚠️ KEY ERROR: Please configure .streamlit/secrets.toml")
        st.stop()
except Exception as e:
    st.error(f"⚠️ SYSTEM ERROR: {e}")
    st.stop()

# ================= 📡 4. 深海声纳系统 (Data Engine) =================

def parse_market_data(data):
    markets_clean = []
    if not data: return []
    for event in data:
        title = event.get('title', 'Unknown')
        slug = event.get('slug', '')
        all_markets = event.get('markets', [])
        if not all_markets: continue

        best_market = None
        max_volume = -1
        for m in all_markets:
            if m.get('closed') is True: continue    
            try:
                vol = float(m.get('volume', 0))
                if vol > max_volume: max_volume = vol; best_market = m
            except: continue
        
        if not best_market: best_market = all_markets[0]

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
    try:
        response = requests.get("https://gamma-api.polymarket.com/events?limit=50&active=true&closed=false&sort=volume", headers={"User-Agent": "BeHolmes/1.0"}, timeout=5)
        return parse_market_data(response.json()) if response.status_code == 200 else []
    except: return []

def deep_sonar_search(keyword):
    if not keyword: return []
    try:
        response = requests.get(f"https://gamma-api.polymarket.com/events?limit=20&active=true&closed=false&q={keyword}", headers={"User-Agent": "BeHolmes/1.0"}, timeout=5)
        return parse_market_data(response.json()) if response.status_code == 200 else []
    except: return []

def extract_keywords_with_ai(user_text, key):
    if not user_text: return None
    try:
        genai.configure(api_key=key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(f"Extract 1-2 most important English keywords for search. Text: '{user_text}'. Output format: keyword1 keyword2")
        return response.text.strip()
    except: return None

# ================= 🧠 5. 推理引擎 =================

def consult_holmes(user_evidence, market_list, key):
    try:
        genai.configure(api_key=key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        markets_text = "\n".join([f"- {m['title']} [Odds: {m['odds']}]" for m in market_list[:50]])
        
        prompt = f"""
        Role: **Be Holmes**, The Prediction Market Detective.
        Goal: Find Alpha by connecting news to market odds.
        
        [Evidence]: "{user_evidence}"
        [Available Markets]: 
        {markets_text}

        **LANGUAGE PROTOCOL:**
        - Input Chinese -> Output CHINESE report.
        - Input English -> Output ENGLISH report.

        **OUTPUT FORMAT (Strict HTML/Markdown):**
        
        ---
        ### 🕵️‍♂️ Case File: [Most Relevant Market Title]
        
        <div class="ticker-box">
        🔥 LIVE SIGNAL: [Insert Odds Here]
        </div>
        
        **1. ⚖️ The Verdict (结论)**
        - **Signal:** 🔴 STRONG BUY / 🧊 AVOID / 🌲 LONG HOLD
        - **Confidence:** **[0-100]%**
        - **Prediction:** Market implies [Current %], I calculate [Target %].
        
        **2. ⛓️ The Deduction (因果推理)**
        > *[Mandatory: Write a deep, 100-word analysis. Start with extracted facts, explain causal chain, and state why current odds are mispriced.]*
        
        **3. ⏳ Strategy (执行)**
        - **Timeframe:** [Duration]
        - **Risk:** [Main Risk]
        ---
        """
        response = model.generate_content(prompt)
        btn_html = """<br><a href='https://polymarket.com/' target='_blank' style='text-decoration:none;'><button class='execute-btn'>🚀 EXECUTE TRADE ON POLYMARKET</button></a>"""
        return response.text + btn_html
    except Exception as e: return f"❌ Error: {str(e)}"

# ================= 📘 6. 使用说明书 (User Manual) =================

@st.dialog("📘 Be Holmes Manual / 使用手册", width="large")
def open_manual():
    # 语言切换
    lang = st.radio("Language / 语言", ["English", "中文"], horizontal=True)
    st.markdown("---")
    
    if lang == "中文":
        st.markdown("""
        ### 🕵️‍♂️ 产品介绍
        **Be Holmes** 是一个基于 **Gemini 2.5** 的预测市场 Alpha 捕获引擎。它不只是阅读新闻，而是进行**二阶因果推理**，帮助你发现被市场低估的赔率。

        ### 🚀 核心功能
        1.  **深海声纳 (Deep Sonar):** 自动提取你输入新闻的关键词，绕过热门榜单，挖掘全网冷门市场。
        2.  **实时推理 (Real-time Logic):** 结合 Polymarket 实时赔率与新闻事实，计算胜率偏差。
        
        ### 🛠️ 使用步骤
        1.  在主界面的文本框输入**任何新闻、传闻或推特链接** (支持中英文)。
        2.  点击红色的 **"🔍 INVESTIGATE"** 按钮。
        3.  系统会自动搜索相关市场，并生成一份包含**买卖信号、置信度、逻辑链**的深度报告。
        """)
    else:
        st.markdown("""
        ### 🕵️‍♂️ Introduction
        **Be Holmes** is an Alpha-capture engine for prediction markets powered by **Gemini 2.5**. It performs **Second-order Causal Reasoning** to identify mispriced odds based on breaking news.

        ### 🚀 Core Features
        1.  **Deep Sonar:** Automatically extracts keywords from your input to search for hidden/niche markets beyond the Top 100.
        2.  **Real-time Logic:** Analyzes the gap between implied market probability and actual event probability.

        ### 🛠️ How to Use
        1.  Enter any **news, rumor, or X link** in the main text box.
        2.  Click the Red **"🔍 INVESTIGATE"** button.
        3.  The agent will scan the markets and generate a report with **Signals, Confidence Scores, and Causal Logic**.
        """)

# ================= 🖥️ 7. 主界面布局 (Main Stage) =================

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

# --- 主区域 ---
st.title("🕵️‍♂️ Be Holmes")
st.caption("EVENT-DRIVEN INTELLIGENCE | SECOND-ORDER CAUSAL REASONING") 
st.markdown("---")

# 1. 证据输入区
st.markdown("### 📁 EVIDENCE INPUT")
user_news = st.text_area(
    "Input News / Rumors / X Links...", 
    height=150, 
    placeholder="Try searching specifically: 'iPhone 18 rumors' or 'Trump tariffs'...", 
    label_visibility="collapsed"
)

# 2. 按钮操作区 (双列布局，紧贴输入框)
col_btn_main, col_btn_help = st.columns([4, 1])

with col_btn_main:
    # 红色核心按钮
    ignite_btn = st.button("🔍 INVESTIGATE / 开始调查", use_container_width=True)

with col_btn_help:
    # 灰色辅助按钮
    help_btn = st.button("📘 Manual", use_container_width=True)

# 3. 逻辑触发
if help_btn:
    open_manual()

if ignite_btn:
    if not user_news:
        st.warning("⚠️ Evidence required to initiate investigation.")
    else:
        with st.status("🚀 Initiating Deep Scan...", expanded=True) as status:
            st.write("🧠 Analyzing intent (Gemini 2.5)...")
            search_keywords = extract_keywords_with_ai(user_news, api_key)
            sonar_markets = []
            if search_keywords:
                st.write(f"🌊 Active Sonar Ping: '{search_keywords}'...")
                sonar_markets = deep_sonar_search(search_keywords)
                st.write(f"✅ Found {len(sonar_markets)} specific markets in the deep web.")
            
            combined_markets = sonar_markets + top_markets
            seen_slugs = set()
            unique_markets = []
            for m in combined_markets:
                if m['slug'] not in seen_slugs: unique_markets.append(m); seen_slugs.add(m['slug'])
            
            st.write("⚖️ Cross-referencing odds data...")
            status.update(label="✅ Investigation Complete", state="complete", expanded=False)

        if not unique_markets: st.error("⚠️ No relevant markets found anywhere.")
        else:
            with st.spinner(">> Deducing Alpha..."):
                result = consult_holmes(user_news, unique_markets, api_key)
                st.markdown("---")
                st.markdown("### 📝 INVESTIGATION REPORT")
                st.markdown(result, unsafe_allow_html=True)
