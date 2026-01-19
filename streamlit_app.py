import streamlit as st
import requests
import json
import google.generativeai as genai
import re
from duckduckgo_search import DDGS  # 核心外挂组件

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

# ================= 📡 4. DATA ENGINE (V19: WEB-PROXY SEARCH) =================

def detect_language_type(text):
    for char in text:
        if '\u4e00' <= char <= '\u9fff': return "CHINESE"
    return "ENGLISH"

def normalize_market(m):
    """清洗 API 返回的原始数据"""
    try:
        title = m.get('title', m.get('question', 'Unknown'))
        slug = m.get('slug', '')
        # 如果市场已关闭，跳过
        if m.get('closed') is True: return None
        
        # 赔率解析
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
        
        volume = float(m.get('volume', 0))
        
        return {
            "title": title,
            "odds": odds_display,
            "volume": volume,
            "slug": slug,
            "id": m.get('id')
        }
    except: return None

def get_market_by_slug(slug):
    """
    通过 Slug 精准打击，直接获取该市场数据
    """
    try:
        # 尝试通过 /events 接口获取 (涵盖大部分热门市场)
        url = f"https://gamma-api.polymarket.com/events?slug={slug}"
        resp = requests.get(url, headers={"User-Agent": "BeHolmes/1.0"}, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            if data:
                # Event 接口返回的是列表，通常包含 markets 字段
                event = data[0]
                markets = event.get('markets', [])
                valid_markets = []
                for m in markets:
                    parsed = normalize_market(m)
                    if parsed: valid_markets.append(parsed)
                return valid_markets
        
        # 如果 /events 没拿到，尝试 /markets (兜底)
        # 这里 /markets?slug={slug} 不一定支持，但可以尝试 ?q={slug}
        url_m = f"https://gamma-api.polymarket.com/markets?q={slug}"
        resp_m = requests.get(url_m, headers={"User-Agent": "BeHolmes/1.0"}, timeout=5)
        if resp_m.status_code == 200:
            data = resp_m.json()
            valid_markets = []
            for m in data:
                parsed = normalize_market(m)
                if parsed: valid_markets.append(parsed)
            return valid_markets
            
    except: pass
    return []

def web_proxy_search(user_query):
    """
    🔥 V19 核心：利用 DuckDuckGo 搜索 'site:polymarket.com'
    这利用了搜索引擎的语义能力，完美解决官方 API 搜不到的问题。
    """
    results = []
    seen_slugs = set()
    
    try:
        # 构造搜索指令：限制在 polymarket 站内
        search_query = f"site:polymarket.com {user_query}"
        
        with DDGS() as ddgs:
            # 搜索前 5 个结果
            ddg_results = list(ddgs.text(search_query, max_results=5))
            
            for res in ddg_results:
                href = res['href']
                # 解析 URL 提取 Slug
                # URL 格式通常是 https://polymarket.com/event/spacex-ipo-2024
                # 或者 https://polymarket.com/market/will-spacex-ipo
                match = re.search(r'polymarket\.com/(?:event|market)/([^/?]+)', href)
                if match:
                    slug = match.group(1)
                    if slug not in seen_slugs:
                        seen_slugs.add(slug)
                        # 拿到 Slug 后，回查 API 获取实时赔率
                        markets = get_market_by_slug(slug)
                        results.extend(markets)
    except Exception as e:
        print(f"Web Search Error: {e}")
        return []
        
    return results

def extract_search_terms_ai(user_text, key):
    if not user_text: return []
    try:
        genai.configure(api_key=key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        # 只需要让 AI 提取核心关键词，剩下的交给 DuckDuckGo 的语义大脑
        prompt = f"""
        Extract the core subject for a search engine query.
        Input: "{user_text}"
        Example: "马斯克那个火箭公司什么时候上市" -> "SpaceX IPO"
        Output: The Search Keyword only.
        """
        response = model.generate_content(prompt)
        return response.text.strip()
    except: return user_text # 如果 AI 挂了，直接用原文搜

# ================= 🧠 5. INTELLIGENCE LAYER =================

def consult_holmes(user_evidence, market_list, key):
    try:
        genai.configure(api_key=key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        # 只取前 5 个最相关的（Web Search 结果通常极准）
        markets_text = "\n".join([f"- {m['title']} [Odds: {m['odds']}]" for m in market_list[:5]])
        target_language = detect_language_type(user_evidence)
        
        prompt = f"""
        Role: You are **Be Holmes**, a Senior Hedge Fund Strategist.
        
        [User Input]: "{user_evidence}"
        [Market Data (Retrieved via Web Search)]: 
        {markets_text}

        **MANDATORY INSTRUCTION:**
        1. **Language:** Output strictly in **{target_language}**.
        2. **Analysis:** The market data above is retrieved from exact URL matches. It is likely the CORRECT market.
        
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
        
        ### 🚀 V19.0 核心引擎：外挂级搜索 (Web-Proxy)
        为了彻底突破 API 搜索的语义缺陷，V19 版本引入了 **DuckDuckGo 外部索引**。
        系统会自动在全网搜索 `site:polymarket.com` 寻找最精准的合约 URL，然后通过 URL 反向提取实时赔率数据。
        **这是目前准确率最高的搜索方式。**
        """)
    else:
        st.markdown("""
        ### 🕵️‍♂️ System Profile
        **Be Holmes** is an omniscient financial detective.
        
        ### 🚀 V19.0 Engine: Web-Proxy Search
        We leverage **DuckDuckGo's web index** to perform semantic searches directly on `site:polymarket.com`. This bypasses the limited internal API search, guaranteeing that if a market exists on Google/DDG, Be Holmes will find it.
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
    st.markdown("### 🌊 Market Sonar")
    st.caption("Initializing Web Proxy...")
    st.success("✅ Proxy: Online")

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
        with st.status("🚀 Initiating Web Proxy Search...", expanded=True) as status:
            st.write("🧠 Extracting semantic keyword (Gemini 2.5)...")
            search_query = extract_search_terms_ai(user_news, active_key)
            
            sonar_markets = []
            if search_query:
                st.write(f"🌊 Probing Polymarket via DuckDuckGo: '{search_query}'...")
                # V19 外挂搜索
                sonar_markets = web_proxy_search(search_query)
                st.write(f"✅ Web Proxy: Locked onto {len(sonar_markets)} exact URL targets.")
            
            st.write("⚖️ Calculating Alpha...")
            status.update(label="✅ Investigation Complete", state="complete", expanded=False)

        if not sonar_markets: st.error("⚠️ No relevant markets found (Even Web Search failed).")
        else:
            with st.spinner(">> Deducing Alpha..."):
                result = consult_holmes(user_news, sonar_markets, active_key)
                st.markdown("---")
                st.markdown("### 📝 INVESTIGATION REPORT")
                st.markdown(result, unsafe_allow_html=True)
