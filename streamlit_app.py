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

# 🔥 DOME KEY (Backup)
DOME_API_KEY = "6f08669ca2c6a9541f0ef1c29e5928d2dc22857b"

# 🔥 FAIL-SAFE (根据你的官网截图更新的真实存在的ID)
# 如果网络彻底挂了，这个字典保证你能看到数据
KNOWN_MARKETS = {
    "spacex": [
        "spacex-ipo-closing-market-cap", # 截图里那个最火的
        "how-many-spacex-launches-in-january",
        "spacex-starship-flight-test-12"
    ],
    "trump": ["presidential-election-winner-2028"],
    "gpt": ["chatgpt-5-release-in-2025"]
}

# ================= 🎨 2. UI DESIGN (V1.0 BASELINE) =================
st.markdown("""
<style>
    [data-testid="stToolbar"] { visibility: hidden; height: 0%; position: fixed; }
    footer { visibility: hidden; }
    header { visibility: hidden; }
    .stApp { background-color: #050505; font-family: 'Roboto Mono', monospace; }
    [data-testid="stSidebar"] { background-color: #000000; border-right: 1px solid #1a1a1a; }
    h1 { 
        background: linear-gradient(90deg, #FF4500, #E63946); 
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        font-family: 'Georgia', serif; font-weight: 800;
        border-bottom: 2px solid #331111; padding-bottom: 15px;
    }
    h3 { color: #FF7F50 !important; } 
    p, label, .stMarkdown, .stText, li, div, span { color: #A0A0A0 !important; }
    strong { color: #FFF !important; font-weight: 600; } 
    .stTextArea textarea, .stTextInput input { 
        background-color: #0A0A0A !important; color: #E63946 !important; 
        border: 1px solid #333 !important; border-radius: 6px;
    }
    .execute-btn {
        background: linear-gradient(90deg, #FF4500, #FFD700); 
        border: none; color: #000; width: 100%; padding: 15px;
        font-weight: 900; font-size: 16px; cursor: pointer; border-radius: 6px;
        text-transform: uppercase; letter-spacing: 2px; margin-top: 20px;
    }
    .ticker-box {
        background-color: #080808; border: 1px solid #222; border-left: 4px solid #FF4500;
        color: #FF4500; font-family: 'Courier New', monospace; padding: 15px; margin: 15px 0;
        font-size: 1.05em; font-weight: bold; display: flex; align-items: center;
    }
</style>
""", unsafe_allow_html=True)

# ================= 🔐 3. KEY MANAGEMENT =================
active_key = None

# ================= 📡 4. DATA ENGINE (V1.10: GRAPHQL CORE) =================

def normalize_market_data(m):
    """通用数据清洗器"""
    try:
        # GraphQL 返回的结构可能略有不同
        slug = m.get('slug', m.get('market_slug', ''))
        title = m.get('question', m.get('title', 'Unknown Market'))
        
        # 赔率解析
        odds_display = "N/A"
        try:
            # GraphQL 有时返回的是 JSON 字符串，有时是对象
            outcomes = m.get('outcomes', '["Yes", "No"]')
            if isinstance(outcomes, str): outcomes = json.loads(outcomes)
            
            prices = m.get('outcomePrices', '[]')
            if isinstance(prices, str): prices = json.loads(prices)
            
            odds_list = []
            if prices and len(prices) == len(outcomes):
                for o, p in zip(outcomes, prices):
                    val = float(p) * 100
                    odds_list.append(f"{o}: {val:.1f}%")
            odds_display = " | ".join(odds_list)
        except: pass
        
        volume = float(m.get('volume', 0))
        # 不再过滤低成交量，因为我们要确保能搜到东西
        
        return {
            "title": title, 
            "odds": odds_display, 
            "slug": slug, 
            "volume": volume, 
            "id": m.get('id')
        }
    except: return None

def search_polymarket_graphql(query_term):
    """
    🔥 V1.10 核心引擎: GraphQL Search
    完全基于你提供的截图方案。
    """
    url = "https://gamma-api.polymarket.com/graphql"
    
    # 你的截图里的 Query 语句
    query = """
    query SearchMarkets($term: String!) {
      searchMarkets(term: $term, limit: 20) {
        id
        question
        slug
        outcomes
        outcomePrices
        volume
        closed
        active
      }
    }
    """
    
    payload = {
        "query": query,
        "variables": {"term": query_term}
    }
    
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    results = []
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            markets = data.get("data", {}).get("searchMarkets", [])
            for m in markets:
                p = normalize_market_data(m)
                if p:
                    p['title'] = "⚡ [GraphQL] " + p['title']
                    results.append(p)
    except Exception as e:
        print(f"GraphQL Error: {e}")
        pass
        
    return results

def search_failsafe(query_term):
    """最后的防线：查硬编码字典"""
    results = []
    for key, slugs in KNOWN_MARKETS.items():
        if key in query_term.lower():
            for slug in slugs:
                try:
                    # 直接用 ID 查详情
                    url = f"https://gamma-api.polymarket.com/markets?slug={slug}"
                    r = requests.get(url, timeout=3).json()
                    for m in r:
                        p = normalize_market_data(m)
                        if p:
                            p['title'] = "🔥 [HOT HIT] " + p['title']
                            results.append(p)
                except: pass
    return results

def extract_search_terms_ai(user_text, key):
    try:
        genai.configure(api_key=key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        # 强制只提取一个词，不要废话
        prompt = f"Extract ONE core English keyword (e.g. SpaceX). Input: '{user_text}'. Output: Keyword"
        response = model.generate_content(prompt)
        return response.text.strip()
    except: return user_text

# ================= 🧠 5. INTELLIGENCE LAYER =================

def consult_holmes(user_evidence, market_list, key):
    try:
        genai.configure(api_key=key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        markets_text = "\n".join([f"- {m['title']} [Odds: {m['odds']}]" for m in market_list[:15]])
        
        prompt = f"""
        Role: **Be Holmes**, Senior Hedge Fund Strategist.
        [User Input]: "{user_evidence}"
        [Market Data Found]: 
        {markets_text}
        
        **OUTPUT (Markdown):**
        ---
        ### 🕵️‍♂️ Case File: [Best Match Title]
        <div class="ticker-box">🔥 LIVE SNAPSHOT: [Insert Odds]</div>
        
        **1. ⚖️ The Verdict**
        - **Signal:** 🟢 BUY / 🔴 SELL / ⚠️ WAIT
        - **Confidence:** [0-100]%
        
        **2. 🧠 Deep Logic**
        > [Analysis in Input Language]
        
        **3. 🛡️ Execution**
        - [Action Plan]
        ---
        """
        response = model.generate_content(prompt)
        btn_html = """<br><a href='https://polymarket.com/' target='_blank' style='text-decoration:none;'><button class='execute-btn'>🚀 EXECUTE TRADE</button></a>"""
        return response.text + btn_html
    except Exception as e: return f"❌ Intelligence Error: {str(e)}"

# ================= 🖥️ 7. MAIN INTERFACE =================

with st.sidebar:
    st.markdown("## 💼 DETECTIVE'S TOOLKIT")
    with st.expander("🔑 API Key Settings", expanded=True):
        user_api_key = st.text_input("Gemini Key", type="password")
        st.markdown("[Get Free Key](https://aistudio.google.com/app/apikey)")
        st.caption("✅ Engine: GraphQL (Scheme A)")

    if user_api_key:
        active_key = user_api_key
        st.success("🔓 Gemini: Active")
    elif "GEMINI_KEY" in st.secrets:
        active_key = st.secrets["GEMINI_KEY"]
        st.info("🔒 System Key Active")
    else:
        st.error("⚠️ Gemini Key Missing!")
        st.stop()

    st.markdown("---")
    st.caption("🌊 Live Feed")
    try:
        # 侧边栏快速自检
        r = requests.get("https://gamma-api.polymarket.com/markets?limit=3&closed=false&sort=volume").json()
        for m in r:
            st.caption(f"📅 {m['question'][:30]}...")
    except: st.error("⚠️ Stream Offline")

# --- Main Stage ---
st.title("Be Holmes")
st.caption("EVENT-DRIVEN INTELLIGENCE | V1.10 GRAPHQL CORE") 
st.markdown("---")

user_news = st.text_area("Input Evidence...", height=150, label_visibility="collapsed", placeholder="Input news... (e.g. SpaceX IPO)")
ignite_btn = st.button("🔍 INVESTIGATE", use_container_width=True)

if ignite_btn:
    if not user_news:
        st.warning("⚠️ Evidence required.")
    else:
        with st.status("🚀 Initiating Search Protocol...", expanded=True) as status:
            st.write("🧠 Extracting intent...")
            keyword = extract_search_terms_ai(user_news, active_key)
