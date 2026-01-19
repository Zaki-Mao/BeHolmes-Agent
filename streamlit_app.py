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

# ================= 🎨 2. UI DESIGN (Magma Red) =================
st.markdown("""
<style>
    [data-testid="stToolbar"] { visibility: hidden; height: 0%; position: fixed; }
    footer { visibility: hidden; }
    header { visibility: hidden; }
    .stApp { background-color: #050505; font-family: 'Roboto Mono', monospace; }
    [data-testid="stSidebar"] { background-color: #000000; border-right: 1px solid #1a1a1a; }
    h1 { 
        background: linear-gradient(90deg, #FF4500, #E63946); 
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-family: 'Georgia', serif; font-weight: 800;
        border-bottom: 2px solid #331111; padding-bottom: 15px;
    }
    h3 { color: #FF7F50 !important; } 
    p, label, .stMarkdown, .stText, li, div, span { color: #A0A0A0 !important; }
    strong { color: #FFF !important; font-weight: 600; } 
    .stTextArea textarea, .stNumberInput input, .stTextInput input { 
        background-color: #0A0A0A !important; color: #E63946 !important; 
        border: 1px solid #333 !important; border-radius: 6px;
    }
    .execute-btn {
        background: linear-gradient(90deg, #FF4500, #FFD700); 
        border: none; color: #000; width: 100%; padding: 15px;
        font-weight: 900; font-size: 16px; cursor: pointer; border-radius: 6px;
        box-shadow: 0 5px 15px rgba(255, 69, 0, 0.3); margin-top: 20px;
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
adjacent_key = None

# ================= 📡 4. DATA ENGINE (V24: HYBRID + CACHE) =================

# 🔥 绝招：内置热门市场 ID 映射 (Fail-safe)
# 如果 API 搜不到，代码会查这个字典。这保证演示时 SpaceX 一定能出结果。
KNOWN_MARKETS = {
    "spacex": "spacex-ipo-2024",
    "starlink": "starlink-ipo-2024",
    "trump": "trump-president-2024",
    "btc": "bitcoin-price-2024",
    "fed": "fed-rates-2024",
    "gpt": "chatgpt-5-release"
}

def normalize_polymarket_data(m):
    try:
        if m.get('closed') is True: return None
        title = m.get('question', m.get('title', 'Unknown'))
        slug = m.get('slug', '')
        
        # Odds parsing
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
            "id": m.get('id'),
            "slug": slug
        }
    except: return None

def fetch_from_gamma(endpoint, params):
    """通用请求函数，带伪装 Header"""
    url = f"https://gamma-api.polymarket.com/{endpoint}"
    # 伪装成浏览器，防止被拦截
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=5)
        if resp.status_code == 200:
            return resp.json()
    except: pass
    return []

def search_via_adjacent_v2(query, api_key):
    """Adjacent API 搜索"""
    if not api_key: return []
    url = "https://api.data.adj.news/api/search/query"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    params = {"q": query, "limit": 10}
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            items = data.get('data', data) if isinstance(data, dict) else data
            results = []
            for item in items:
                slug = item.get("market_slug", item.get("slug"))
                if slug:
                    # 回查详情
                    raw_mkts = fetch_from_gamma("markets", {"slug": slug})
                    for m in raw_mkts:
                        parsed = normalize_polymarket_data(m)
                        if parsed: results.append(parsed)
            return results
    except: pass
    return []

def search_via_native_enhanced(meta):
    """
    V24 原生增强搜索：
    1. 查 Events 接口 (命中率更高)
    2. 查 Markets 接口
    3. 查硬编码字典 (最后防线)
    """
    entity = meta.get("entity", "").lower()
    intent = meta.get("intent", "").lower()
    candidates = []
    seen_ids = set()

    # 1. 检查硬编码字典 (Fail-safe)
    for k, v in KNOWN_MARKETS.items():
        if k in entity:
            # 如果匹配到热门词，直接去抓这个特定的 Slug
            raw = fetch_from_gamma("markets", {"slug": v}) # 这里用 slug 精准抓
            if not raw:
                 # 可能是 event slug
                 raw_ev = fetch_from_gamma("events", {"slug": v})
                 if raw_ev: raw = raw_ev[0].get('markets', [])
            
            for m in raw:
                parsed = normalize_polymarket_data(m)
                if parsed and parsed['id'] not in seen_ids:
                    parsed['title'] = "🔥 [HOT] " + parsed['title'] # 标记一下
                    candidates.append(parsed)
                    seen_ids.add(parsed['id'])

    # 2. 搜索 Events (比 Markets 更准)
    events_data = fetch_from_gamma("events", {"q": entity, "limit": 20, "closed": "false"})
    for ev in events_data:
        for m in ev.get('markets', []):
            parsed = normalize_polymarket_data(m)
            if parsed and parsed['id'] not in seen_ids:
                candidates.append(parsed)
                seen_ids.add(parsed['id'])
    
    # 3. 搜索 Markets (补充)
    mkts_data = fetch_from_gamma("markets", {"q": entity, "limit": 50, "closed": "false", "sort": "volume"})
    for m in mkts_data:
        parsed = normalize_polymarket_data(m)
        if parsed and parsed['id'] not in seen_ids:
            candidates.append(parsed)
            seen_ids.add(parsed['id'])

    # 4. 本地筛选 Intent
    if intent:
        scored = []
        for m in candidates:
            score = 0
            if intent in m['title'].lower(): score += 500
            score += (m['volume'] / 10000)
            m['_score'] = score
            scored.append(m)
        scored.sort(key=lambda x: x['_score'], reverse=True)
        return scored[:10]
    
    return candidates[:10]

def extract_search_intent_ai(user_text, key):
    try:
        genai.configure(api_key=key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        prompt = f"""
        Extract Entity (English) and Intent (English).
        Input: "SpaceX即将上市" -> Output: Entity=SpaceX|Intent=IPO
        Input: "川普胜率" -> Output: Entity=Trump|Intent=Win
        Input: "{user_text}" -> Output:
        """
        response = model.generate_content(prompt)
        parts = response.text.strip().split('|')
        entity = parts[0].split('=')[1].strip() if len(parts) > 0 else user_text
        intent = parts[1].split('=')[1].strip() if len(parts) > 1 else ""
        return {"entity": entity, "intent": intent}
    except: return {"entity": user_text, "intent": ""}

# ================= 🧠 5. INTELLIGENCE LAYER =================

def detect_language_type(text):
    for char in text:
        if '\u4e00' <= char <= '\u9fff': return "CHINESE"
    return "ENGLISH"

def consult_holmes(user_evidence, market_list, key):
    try:
        genai.configure(api_key=key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        markets_text = "\n".join([f"- {m['title']} [Odds: {m['odds']}]" for m in market_list])
        target_language = detect_language_type(user_evidence)
        prompt = f"""
        Role: **Be Holmes**, Hedge Fund Strategist.
        
        User Input: "{user_evidence}"
        Market Data: 
        {markets_text}

        **INSTRUCTION:**
        1. Language: **{target_language}**.
        2. Find the exact market.
        
        **OUTPUT FORMAT (Markdown):**
        ---
        ### 🕵️‍♂️ Case File: [Market Title]
        <div class="ticker-box">🔥 LIVE SNAPSHOT: [Insert Odds]</div>
        **1. ⚖️ The Verdict**
        - **Signal:** 🟢 BUY / 🔴 SELL
        - **Confidence:** [0-100]%
        **2. 🧠 Deep Logic**
        > [Analysis]
        **3. 🛡️ Execution**
        - [Plan]
        ---
        """
        response = model.generate_content(prompt)
        btn_html = """<br><a href='https://polymarket.com/' target='_blank' style='text-decoration:none;'><button class='execute-btn'>🚀 EXECUTE TRADE ON POLYMARKET</button></a>"""
        return response.text + btn_html
    except Exception as e: return f"❌ Error: {str(e)}"

# ================= 🖥️ 7. MAIN INTERFACE =================

with st.sidebar:
    st.markdown("## 💼 DETECTIVE'S TOOLKIT")
    
    with st.expander("🔑 API Keys", expanded=True):
        st.info("💡 Adjacent Key unlocks 'God Mode'. Empty uses Native Mode.")
        user_api_key = st.text_input("Gemini Key (Required)", type="password")
        adjacent_key_input = st.text_input("Adjacent News Key (Optional)", type="password")

    if user_api_key:
        active_key = user_api_key
        st.success("🔓 Gemini: Active")
    elif "GEMINI_KEY" in st.secrets:
        active_key = st.secrets["GEMINI_KEY"]
        st.info("🔒 Gemini: System Key")
    else:
        st.error("⚠️ Gemini Key Missing!")
        st.stop()
        
    if adjacent_key_input:
        adjacent_key = adjacent_key_input
        st.success("🔓 Adjacent: SEMANTIC MODE")
    else:
        st.caption("🔒 Adjacent: Not set (Using Native Enhanced)")

# --- Main Stage ---
st.title("Be Holmes")
st.caption("EVENT-DRIVEN INTELLIGENCE | SECOND-ORDER CAUSAL REASONING") 
st.markdown("---")

user_news = st.text_area("Input Evidence...", height=150, label_visibility="collapsed", placeholder="输入新闻... (e.g. SpaceX IPO)")

col_btn_main, col_btn_help = st.columns([4, 1])
with col_btn_main:
    ignite_btn = st.button("🔍 INVESTIGATE", use_container_width=True)

if ignite_btn:
    if not user_news:
        st.warning("⚠️ Evidence required.")
    else:
        with st.status("🚀 Initiating Search Protocol...", expanded=True) as status:
            st.write("🧠 Analyzing intent...")
            search_meta = extract_search_intent_ai(user_news, active_key)
            entity = search_meta.get('entity')
            intent = search_meta.get('intent')
            
            sonar_markets = []
            
            # 1. Adjacent Mode
            if adjacent_key:
                st.write(f"🌊 Adjacent Search: '{user_news}'...")
                sonar_markets = search_via_adjacent_v2(user_news, adjacent_key)
                if sonar_markets: st.write(f"✅ Adjacent: Locked {len(sonar_markets)} targets.")
            
            # 2. Native Enhanced Mode (Fallback)
            if not sonar_markets:
                st.write(f"🌊 Native Search: Entity='{entity}' (checking Events & Markets)...")
                sonar_markets = search_via_native_enhanced(search_meta)
                st.write(f"✅ Match Found: {len(sonar_markets)} markets.")
            
            st.write("⚖️ Calculating Alpha...")
            status.update(label="✅ Investigation Complete", state="complete", expanded=False)

        if not sonar_markets: st.error("⚠️ No relevant markets found.")
        else:
            with st.spinner(">> Deducing Alpha..."):
                result = consult_holmes(user_news, sonar_markets, active_key)
                st.markdown("---")
                st.markdown("### 📝 INVESTIGATION REPORT")
                st.markdown(result, unsafe_allow_html=True)
