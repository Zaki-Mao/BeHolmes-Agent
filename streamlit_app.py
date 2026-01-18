import streamlit as st
import requests
import json
import google.generativeai as genai
import re

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

# ================= 📡 4. DATA ENGINE (DUAL-TRACK V17.0) =================

def detect_language_type(text):
    for char in text:
        if '\u4e00' <= char <= '\u9fff': return "CHINESE"
    return "ENGLISH"

def normalize_market_object(m, source_type="market"):
    """
    统一清洗逻辑：把来自 Event 和 Market 两个不同接口的数据统一格式
    """
    try:
        # 排除已关闭的市场 (V17: 本地过滤，而非 API 过滤)
        if m.get('closed') is True: return None
        
        # 提取标题
        if source_type == "event":
            # Event 接口通常包含 markets 列表，我们只取第一个或遍历
            # 这里假设 m 已经是 Event 里的一个具体 market
            title = m.get('question', m.get('title', 'Unknown'))
        else:
            title = m.get('question', m.get('title', 'Unknown'))

        slug = m.get('slug', '')
        m_id = m.get('id', '')
        
        # 解析赔率
        odds_display = "N/A"
        raw_outcomes = m.get('outcomes', '["Yes", "No"]')
        outcomes = json.loads(raw_outcomes) if isinstance(raw_outcomes, str) else raw_outcomes
        raw_prices = m.get('outcomePrices', '[]')
        prices = json.loads(raw_prices) if isinstance(raw_prices, str) else raw_prices
        
        odds_list = []
        if prices and len(prices) == len(outcomes):
            for o, p in zip(outcomes, prices):
                try:
                    val = float(p) * 100
                    if val > 0.1: odds_list.append(f"{o}: {val:.1f}%")
                except: continue
            odds_display = " | ".join(odds_list)
        
        # 必须有流动性或成交量
        volume = float(m.get('volume', 0))
        liquidity = float(m.get('liquidity', 0))
        
        # V17: 放宽过滤条件，有些新市场 volume 低但 liquidity 高
        if volume < 10 and liquidity < 10: return None 
        
        return {
            "title": title, 
            "odds": odds_display, 
            "slug": slug, 
            "volume": volume, 
            "liquidity": liquidity,
            "id": m_id
        }
    except: return None

@st.cache_data(ttl=300) 
def fetch_sidebar_markets():
    try:
        url = "https://gamma-api.polymarket.com/markets?limit=20&closed=false&sort=volume"
        response = requests.get(url, headers={"User-Agent": "BeHolmes/1.0"}, timeout=5)
        if response.status_code == 200:
            raw = response.json()
            cleaned = []
            for m in raw:
                parsed = normalize_market_object(m, "market")
                if parsed: cleaned.append(parsed)
            return cleaned
        return []
    except: return []

def dual_track_search(keywords):
    """
    🔥 V17 核心：双轨搜索
    同时搜 /events 和 /markets 两个接口，确保无死角。
    """
    all_results = []
    seen_ids = set()
    
    for kw in keywords:
        if not kw: continue
        
        # --- Track 1: Search Events (Search Groups) ---
        # 很多大热门像 SpaceX IPO 其实是一个 Event Group
        try:
            url_events = f"https://gamma-api.polymarket.com/events?q={kw}&limit=20"
            resp_ev = requests.get(url_events, headers={"User-Agent": "BeHolmes/1.0"}, timeout=4)
            if resp_ev.status_code == 200:
                events = resp_ev.json()
                for ev in events:
                    # 提取 Event 里面的 markets
                    markets_in_event = ev.get('markets', [])
                    for m in markets_in_event:
                        parsed = normalize_market_object(m, "event")
                        if parsed and parsed['id'] not in seen_ids:
                            all_results.append(parsed)
                            seen_ids.add(parsed['id'])
        except: pass

        # --- Track 2: Search Markets (Direct Contracts) ---
        # 搜具体的合约标题
        try:
            url_mkts = f"https://gamma-api.polymarket.com/markets?q={kw}&limit=50"
            resp_mk = requests.get(url_mkts, headers={"User-Agent": "BeHolmes/1.0"}, timeout=4)
            if resp_mk.status_code == 200:
                markets = resp_mk.json()
                for m in markets:
                    parsed = normalize_market_object(m, "market")
                    if parsed and parsed['id'] not in seen_ids:
                        all_results.append(parsed)
                        seen_ids.add(parsed['id'])
        except: pass

    # --- Phase 3: Reranking ---
    # 根据相关性排序：如果标题里包含关键词，权重极高；其次看 Volume
    ranked_results = []
    search_str = " ".join(keywords).lower()
    
    for item in all_results:
        score = 0
        title_lower = item['title'].lower()
        
        # 包含关键词加分
        if any(k.lower() in title_lower for k in keywords):
            score += 100
        
        # Volume 加分 (归一化)
        score += (item['volume'] / 10000) 
        
        item['_score'] = score
        ranked_results.append(item)
        
    # 按分数降序
    ranked_results.sort(key=lambda x: x['_score'], reverse=True)
    
    return ranked_results[:30] # 只取前30个最相关的

def extract_search_terms_ai(user_text, key):
    if not user_text: return []
    try:
        genai.configure(api_key=key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        prompt = f"""
        Extract 2 distinct English search keywords for a database.
        1. Specific Entity+Event (e.g. "SpaceX IPO")
        2. Broad Entity (e.g. "SpaceX")
        Input: "{user_text}"
        Output: Keyword1, Keyword2 (comma separated)
        """
        response = model.generate_content(prompt)
        raw_text = response.text.strip()
        keywords = [k.strip() for k in raw_text.split(',')]
        return keywords[:2]
    except: return []

# ================= 🧠 5. INTELLIGENCE LAYER =================

def consult_holmes(user_evidence, market_list, key):
    try:
        genai.configure(api_key=key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        markets_text = "\n".join([f"- {m['title']} [Odds: {m['odds']}]" for m in market_list])
        target_language = detect_language_type(user_evidence)
        
        prompt = f"""
        Role: You are **Be Holmes**, a Senior Hedge Fund Strategist.
        
        [User Input]: "{user_evidence}"
        [Market Data Scanned]: 
        {markets_text}

        **MANDATORY INSTRUCTION:**
        1. **Language:** Output strictly in **{target_language}**.
        2. **Matching:** Find the market that matches the user's intent. 
           - If user asks "SpaceX IPO", look for "SpaceX IPO". 
           - DO NOT Hallucinate. If the specific market is missing from the list above, say "Target market not found" and analyze the closest proxy (like SpaceX general performance).
        
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
        > *[Analysis in {target_language}. 200 words.]*
        
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
        **Be Holmes** 是基于 Gemini 2.5 的全知全能金融侦探。
        
        ### 🚀 V17.0 核心引擎：双轨深潜 (Dual-Track)
        我们同时接入 Polymarket 的 `/events` (事件组) 和 `/markets` (独立合约) 接口。无论目标市场是被打包在事件集中，还是作为独立合约存在，双轨引擎都能将其召回。
        
        ### 🛠️ 操作指南
        - **输入:** 粘贴新闻或关键词。
        - **调查:** 点击红色 **INVESTIGATE**。
        """)
    else:
        st.markdown("""
        ### 🕵️‍♂️ System Profile
        **Be Holmes** is an omniscient financial detective.
        
        ### 🚀 V17.0 Engine: Dual-Track Search
        We now query both `/events` and `/markets` endpoints simultaneously to ensure zero-blind-spot retrieval of both grouped and standalone contracts.
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
        top_markets = fetch_sidebar_markets()
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
        with st.status("🚀 Initiating Dual-Track Search...", expanded=True) as status:
            st.write("🧠 Extracting intent (Gemini 2.5)...")
            search_keywords = extract_search_terms_ai(user_news, active_key)
            
            sonar_markets = []
            if search_keywords:
                st.write(f"🌊 Scanning Events & Markets for: {search_keywords}...")
                # V17 双轨搜索
                sonar_markets = dual_track_search(search_keywords)
                st.write(f"✅ Dual-Track Result: Found {len(sonar_markets)} relevant markets.")
            
            # 如果真的没搜到，再用 Top 市场兜底
            if not sonar_markets:
                st.write("⚠️ Deep scan empty. Falling back to global top markets.")
                sonar_markets = top_markets
            
            st.write("⚖️ Calculating Alpha...")
            status.update(label="✅ Investigation Complete", state="complete", expanded=False)

        if not sonar_markets: st.error("⚠️ No relevant markets found in the database.")
        else:
            with st.spinner(">> Deducing Alpha..."):
                result = consult_holmes(user_news, sonar_markets, active_key)
                st.markdown("---")
                st.markdown("### 📝 INVESTIGATION REPORT")
                st.markdown(result, unsafe_allow_html=True)
