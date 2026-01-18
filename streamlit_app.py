import streamlit as st
import requests
import json
import google.generativeai as genai
import re
from collections import Counter

# ================= 🕵️‍♂️ 1. SYSTEM CONFIGURATION =================
st.set_page_config(
    page_title="Be Holmes | Alpha Hunter",
    page_icon="🕵️‍♂️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ================= 🎨 2. UI DESIGN (Magma Red) =================
st.markdown("""
<style>
    /* --- HIDE SYSTEM ELEMENTS --- */
    [data-testid="stToolbar"] { visibility: hidden; height: 0%; position: fixed; }
    footer { visibility: hidden; }
    header { visibility: hidden; }

    /* --- Global Background --- */
    .stApp { background-color: #050505; font-family: 'Roboto Mono', monospace; }
    [data-testid="stSidebar"] { background-color: #000000; border-right: 1px solid #1a1a1a; }
    
    /* --- Typography --- */
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
    
    h3 { color: #FF7F50 !important; } 
    p, label, .stMarkdown, .stText, li, div, span { color: #A0A0A0 !important; }
    strong { color: #FFF !important; font-weight: 600; } 
    a { text-decoration: none !important; border-bottom: none !important; }

    /* --- Inputs --- */
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
    
    /* --- Buttons --- */
    .stButton button { width: 100%; border-radius: 6px; font-weight: bold; transition: all 0.3s ease; }
    
    div[data-testid="column"]:nth-of-type(1) div.stButton > button { 
        background: linear-gradient(90deg, #8B0000, #FF4500); 
        color: #FFF; border: none; box-shadow: 0 4px 15px rgba(255, 69, 0, 0.3);
    }
    div[data-testid="column"]:nth-of-type(1) div.stButton > button:hover { 
        box-shadow: 0 6px 25px rgba(255, 69, 0, 0.6); transform: translateY(-2px);
    }

    div[data-testid="column"]:nth-of-type(2) div.stButton > button { 
        background-color: transparent; color: #666; border: 1px solid #333; 
    }
    div[data-testid="column"]:nth-of-type(2) div.stButton > button:hover { 
        border-color: #FF4500; color: #FF4500; background-color: #1a0505;
    }

    /* --- Report Elements --- */
    .execute-btn {
        background: linear-gradient(90deg, #FF4500, #FFD700); 
        border: none; color: #000; width: 100%; padding: 15px;
        font-weight: 900; font-size: 16px; cursor: pointer; border-radius: 6px;
        text-transform: uppercase; letter-spacing: 2px;
        box-shadow: 0 5px 15px rgba(255, 69, 0, 0.3); margin-top: 20px;
    }
    .execute-btn:hover { transform: scale(1.02); box-shadow: 0 8px 25px rgba(255, 69, 0, 0.5); }

    .ticker-box {
        background-color: #080808; border: 1px solid #222; border-left: 4px solid #FF4500;
        color: #FF4500; font-family: 'Courier New', monospace; padding: 15px; margin: 15px 0;
        font-size: 1.05em; font-weight: bold; display: flex; align-items: center;
    }
</style>
""", unsafe_allow_html=True)

# ================= 🔐 3. KEY MANAGEMENT =================
active_key = None

# ================= 📡 4. DATA ENGINE (SMART RERANKING V14.0) =================

def detect_language_type(text):
    for char in text:
        if '\u4e00' <= char <= '\u9fff':
            return "CHINESE"
    return "ENGLISH"

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

def smart_search(keywords_list):
    """
    🔥 智能重排逻辑：
    1. 不管 API 怎么排序，我们只要包含关键词的市场。
    2. 如果一个市场的标题同时包含多个关键词，它的权重无限大。
    """
    all_candidates = []
    seen_slugs = set()
    
    # 1. 广撒网 (Broad Search)
    for kw in keywords_list:
        if not kw: continue
        # 强制抓取前 100 个
        url = f"https://gamma-api.polymarket.com/events?limit=100&active=true&closed=false&q={kw}"
        try:
            response = requests.get(url, headers={"User-Agent": "BeHolmes/1.0"}, timeout=6)
            if response.status_code == 200:
                data = parse_market_data(response.json())
                for m in data:
                    if m['slug'] not in seen_slugs:
                        all_candidates.append(m)
                        seen_slugs.add(m['slug'])
        except: continue
    
    # 2. 本地重评分 (Local Scoring)
    # 目标：把 "SpaceX IPO" 顶到第一位，把 "Kraken IPO" 踩下去
    scored_markets = []
    
    # 简单的关键词打分
    search_terms_lower = [k.lower() for k in keywords_list]
    
    for m in all_candidates:
        score = 0
        title_lower = m['title'].lower()
        
        # 规则1：包含完整关键词组 (e.g. "spacex ipo") -> +100分
        for term in search_terms_lower:
            if term in title_lower:
                score += 10
            # 拆分单词再匹配 (防止 API 没匹配上)
            for word in term.split():
                if word in title_lower:
                    score += 2
                    
        # 规则2：成交量加权 (微量，防止死盘干扰)
        if m['volume'] > 1000: score += 1
        
        m['score'] = score
        scored_markets.append(m)
    
    # 3. 按分数倒序排列
    scored_markets.sort(key=lambda x: x['score'], reverse=True)
    
    # 返回前 20 个最强匹配
    return scored_markets[:20]

def extract_search_terms_ai(user_text, key):
    if not user_text: return []
    try:
        genai.configure(api_key=key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        # 🔥 策略：提取 Entity 和 Event 分开搜，确保覆盖面
        prompt = f"""
        Analyze the text and extract 3 search queries for a database.
        1. Full intent (e.g. "SpaceX IPO")
        2. Main Entity (e.g. "SpaceX")
        3. Alternative Entity (e.g. "Starlink" if SpaceX is mentioned, or "Musk")
        
        Input: "{user_text}"
        Output: Keyword1, Keyword2, Keyword3 (comma separated)
        """
        response = model.generate_content(prompt)
        raw_text = response.text.strip()
        keywords = [k.strip() for k in raw_text.split(',')]
        return keywords[:3] 
    except: return []

# ================= 🧠 5. INTELLIGENCE LAYER =================

def consult_holmes(user_evidence, market_list, key):
    try:
        genai.configure(api_key=key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        # 把经过本地重排后的最强 20 个结果给 AI
        markets_text = "\n".join([f"- {m['title']} [Odds: {m['odds']}]" for m in market_list])
        target_language = detect_language_type(user_evidence)
        
        prompt = f"""
        Role: You are **Be Holmes**, a Senior Hedge Fund Strategist.
        
        [User Input]: "{user_evidence}"
        [Top 20 Matches]: 
        {markets_text}

        **MANDATORY INSTRUCTION:**
        **1. LANGUAGE:** Output strictly in **{target_language}**.
        
        **2. MATCHING PROTOCOL:**
        - The list above is ranked by relevance. **The first item is likely the exact match.**
        - Look at Item #1, #2, #3 carefully.
        - If the user asks about "SpaceX IPO", do NOT analyze "Kraken" unless SpaceX is completely missing.
        
        **OUTPUT FORMAT (Strict Markdown):**
        
        ---
        ### 🕵️‍♂️ Case File: [Exact Market Title]
        
        <div class="ticker-box">
        🔥 LIVE SNAPSHOT: [Insert Odds]
        </div>
        
        **1. ⚖️ The Verdict (交易指令)**
        - **Signal:** 🟢 BUY / 🔴 SELL / ⚠️ WAIT
        - **Confidence:** **[0-100]%**
        - **Valuation:** Market: [X%], Model: [Y%].
        
        **2. 🧠 Deep Logic (深度推演)**
        > *[Analysis in {target_language}. Explain why this specific market is the opportunity.]*
        
        **3. 🛡️ Execution Protocol (执行方案)**
        - **Action:** [Instruction]
        - **Timeframe:** [Duration]
        - **Exit:** [Condition]
        ---
        """
        response = model.generate_content(prompt)
        
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
        2.  **本地重排 (Smart Reranking):** 强制抓取全网数据，并在本地进行相关性打分，确保精准命中目标。
        3.  **Alpha 推理:** 结合实时赔率与事件逻辑，输出交易胜率分析。
        """)
    else:
        st.markdown("""
        ### 🕵️‍♂️ System Profile
        **Be Holmes** is an omniscient financial detective. It features "Deep Sonar" capability to pinpoint prediction markets.

        ### 🚀 Core Workflow
        1.  **Keyword Extraction:** Distills input into search vectors.
        2.  **Smart Reranking:** Fetches raw data and re-scores it locally to find the exact needle in the haystack.
        3.  **Alpha Reasoning:** Synthesizes real-time odds with causal logic.
        """)

# ================= 🖥️ 7. MAIN INTERFACE =================

with st.sidebar:
    st.markdown("## 💼 DETECTIVE'S TOOLKIT")
    with st.expander("🔑 API Key Settings", expanded=False):
        st.caption("Rate limited? Enter your own Google AI Key.")
        user_api_key = st.text_input("Gemini Key", type="password")
        st.markdown("[Get Free Key](https://aistudio.google.com/app/apikey)")

    if user_api_key:
        active_key = user_api_key
        st.success("🔓 User Key Active")
    elif "GEMINI_KEY" in st.secrets:
        active_key = st.secrets["GEMINI_KEY"]
        st.info("🔒 System Key Active")
    else:
        st.error("⚠️ No API Key found!")
        st.stop()

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

st.markdown("### 📁 EVIDENCE INPUT")
user_news = st.text_area(
    "Input News / Rumors / X Links...", 
    height=150, 
    placeholder="Paste detailed intel here... (e.g., 'Rumors that iPhone 18 will remove all buttons')", 
    label_visibility="collapsed"
)

col_btn_main, col_btn_help = st.columns([4, 1])
with col_btn_main:
    ignite_btn = st.button("🔍 INVESTIGATE", use_container_width=True)
with col_btn_help:
    help_btn = st.button("📘 Manual", use_container_width=True)

if help_btn: open_manual()

if ignite_btn:
    if not user_news:
        st.warning("⚠️ Evidence required to initiate investigation.")
    else:
        with st.status("🚀 Initiating Smart Scan...", expanded=True) as status:
            st.write("🧠 Extracting entities (Gemini 2.5)...")
            search_keywords = extract_search_terms_ai(user_news, active_key)
            
            top_matches = []
            if search_keywords:
                st.write(f"🌊 Dragnet Search: {search_keywords}...")
                # 使用本地重排算法
                top_matches = smart_search(search_keywords)
                st.write(f"✅ Filtered down to {len(top_matches)} highly relevant markets.")
            
            # 如果没搜到，再用 Top Markets 兜底
            if not top_matches:
                top_matches = fetch_top_markets()
            
            st.write("⚖️ Calculating Alpha...")
            status.update(label="✅ Investigation Complete", state="complete", expanded=False)

        if not top_matches: st.error("⚠️ No relevant markets found in the database.")
        else:
            with st.spinner(">> Deducing Alpha..."):
                result = consult_holmes(user_news, top_matches, active_key)
                st.markdown("---")
                st.markdown("### 📝 INVESTIGATION REPORT")
                st.markdown(result, unsafe_allow_html=True)
