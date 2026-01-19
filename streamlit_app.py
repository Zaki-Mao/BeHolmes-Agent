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

# 🔥 FAIL-SAFE: If API fails, these will load
KNOWN_MARKETS = {
    "spacex": ["spacex-ipo-closing-market-cap", "will-spacex-ipo-in-2025"],
    "trump": ["presidential-election-winner-2028"],
    "gpt": ["chatgpt-5-release-in-2025"]
}

# ================= 🎨 2. UI DESIGN (Default English / Magma Red) =================
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

# ================= 🧠 4. LANGUAGE BRAIN =================

def detect_language(text):
    """Detect if input is Chinese or English"""
    for char in text:
        if '\u4e00' <= char <= '\u9fff':
            return "CHINESE"
    return "ENGLISH"

def extract_search_terms_ai(user_text, key):
    """Extract ONE core English keyword (e.g., 'SpaceX') regardless of input language"""
    try:
        genai.configure(api_key=key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        prompt = f"""
        Extract the SINGLE most important search entity (English only).
        Ignore stop words.
        Input: "{user_text}"
        Output (Word only):
        """
        response = model.generate_content(prompt)
        # Clean up
        keyword = response.text.strip().replace('"', '').replace("'", "")
        return keyword
    except: return user_text.split()[0]

# ================= 📡 5. DATA ENGINE (FETCH 500 + LOCAL FILTER) =================

def normalize_market_data(m):
    try:
        if m.get('closed') is True: return None
        title = m.get('question', m.get('title', 'Unknown Market'))
        slug = m.get('slug', m.get('market_slug', ''))
        
        # Odds Logic
        odds_display = "N/A"
        try:
            raw_outcomes = m.get('outcomes', '["Yes", "No"]')
            outcomes = json.loads(raw_outcomes) if isinstance(raw_outcomes, str) else raw_outcomes
            raw_prices = m.get('outcomePrices', '[]')
            prices = json.loads(raw_prices) if isinstance(raw_prices, str) else raw_prices
            
            odds_list = []
            if prices and len(prices) == len(outcomes):
                for o, p in zip(outcomes, prices):
                    val = float(p) * 100
                    odds_list.append(f"{o}: {val:.1f}%")
            odds_display = " | ".join(odds_list)
        except: pass
        
        volume = float(m.get('volume', 0))
        return {"title": title, "odds": odds_display, "slug": slug, "volume": volume, "id": m.get('id')}
    except: return None

def search_polymarket_deep_scan(keyword):
    """
    🔥 STRATEGY: Fetch Top 500 Markets -> Local Python Filter
    This is more robust than the API's fuzzy search.
    """
    results = []
    seen = set()
    
    # 1. API: Fetch Top 500 by Volume (The "Big Net" Approach)
    # We fetch broadly, then filter strictly locally
    url = "https://gamma-api.polymarket.com/markets"
    params = {
        "limit": 500, # Grab a huge chunk
        "closed": "false",
        "sort": "volume"
    }
    
    try:
        resp = requests.get(url, params=params, timeout=8)
        if resp.status_code == 200:
            all_markets = resp.json()
            for m in all_markets:
                p = normalize_market_data(m)
                if p and p['slug'] not in seen:
                    # LOCAL MATCHING: Check if keyword is in title or slug
                    # This avoids API search limitations
                    if keyword.lower() in p['title'].lower() or keyword.lower() in p['slug']:
                        results.append(p)
                        seen.add(p['slug'])
    except Exception as e:
        print(f"Deep Scan Error: {e}")

    # 2. FAIL-SAFE: Check Hardcoded Dictionary (If API missed it)
    if not results:
        for k, slugs in KNOWN_MARKETS.items():
            if k in keyword.lower():
                for slug in slugs:
                    try:
                        r = requests.get(f"https://gamma-api.polymarket.com/markets?slug={slug}").json()
                        for m in r:
                            p = normalize_market_data(m)
                            if p and p['slug'] not in seen:
                                p['title'] = "🔥 [HOT] " + p['title']
                                results.append(p)
                                seen.add(p['slug'])
                    except: pass

    # Sort by volume (liquidity first)
    results.sort(key=lambda x: x['volume'], reverse=True)
    return results

# ================= 🤖 6. AI ANALYST (AUTO-LANGUAGE) =================

def consult_holmes(user_input, market_data, key):
    try:
        genai.configure(api_key=key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        # Detect Language
        lang_mode = detect_language(user_input)
        target_lang_instruction = "Respond in **CHINESE (中文)**." if lang_mode == "CHINESE" else "Respond in **ENGLISH**."
        
        markets_text = "\n".join([f"- {m['title']} [Odds: {m['odds']}]" for m in market_data[:10]])
        
        prompt = f"""
        Role: **Be Holmes**, Senior Hedge Fund Strategist.
        
        [User Input]: "{user_input}"
        [Market Data Found]: 
        {markets_text}
        
        **MANDATORY INSTRUCTION:**
        1. **Language:** {target_lang_instruction}
        2. **Analysis:** Match the input to the specific market data.
        
        **OUTPUT FORMAT (Markdown):**
        ---
        ### 🕵️‍♂️ Case File: [Best Match Title]
        <div class="ticker-box">🔥 LIVE SNAPSHOT: [Insert Odds]</div>
        
        **1. ⚖️ The Verdict**
        - **Signal:** 🟢 BUY / 🔴 SELL / ⚠️ WAIT
        - **Confidence:** [0-100]%
        
        **2. 🧠 Deep Logic**
        > [Detailed analysis of why the odds are mispriced or correct.]
        
        **3. 🛡️ Execution**
        - [Action Plan]
        ---
        """
        response = model.generate_content(prompt)
        
        # Button label adapts slightly or stays English (UI is English)
        btn_label = "🚀 EXECUTE TRADE"
        btn_html = f"""<br><a href='https://polymarket.com/' target='_blank' style='text-decoration:none;'><button class='execute-btn'>{btn_label}</button></a>"""
        return response.text + btn_html
    except Exception as e: return f"❌ Error: {str(e)}"

# ================= 🖥️ 7. MAIN INTERFACE =================

with st.sidebar:
    st.markdown("## 💼 DETECTIVE'S TOOLKIT")
    with st.expander("🔑 API Key Settings", expanded=True):
        user_api_key = st.text_input("Gemini Key", type="password")
        st.markdown("[Get Free Key](https://aistudio.google.com/app/apikey)")
        st.caption("✅ Engine: Deep Scan (Top 500)")

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
    st.caption("🌊 Live Feed (Top 3 Vol)")
    try:
        # Sidebar feed
        r = requests.get("https://gamma-api.polymarket.com/markets?limit=3&closed=false&sort=volume").json()
        for m in r:
            p = normalize_market_data(m)
            if p:
                st.caption(f"📅 {p['title']}")
                st.code(f"{p['odds']}")
    except: st.error("⚠️ Stream Offline")

# --- Main Stage ---
st.title("Be Holmes")
st.caption("EVENT-DRIVEN INTELLIGENCE | V5.0 GLOBAL DETECTIVE") 
st.markdown("---")

user_news = st.text_area("Input Evidence...", height=150, label_visibility="collapsed", placeholder="Input news or rumors... (e.g. SpaceX IPO)")
ignite_btn = st.button("🔍 INVESTIGATE", use_container_width=True)

if ignite_btn:
    if not user_news:
        st.warning("⚠️ Evidence required.")
    else:
        with st.status("🚀 Initiating Investigation...", expanded=True) as status:
            # 1. Keyword Extraction
            st.write("🧠 Extracting core entity...")
            keyword = extract_search_terms_ai(user_news, active_key)
            st.write(f"🔑 Target Entity: '{keyword}'")
            
            # 2. Deep Scan (The "Fetch 500" Strategy)
            st.write(f"🌊 Scanning Top 500 Markets for matches...")
            sonar_markets = search_polymarket_deep_scan(keyword)
            
            if sonar_markets: 
                st.success(f"✅ FOUND: {len(sonar_markets)} active markets.")
            else:
                st.error("⚠️ No direct markets found in Top 500.")
            
            st.write("⚖️ Calculating Alpha...")
            status.update(label="✅ Investigation Complete", state="complete", expanded=False)

        if sonar_markets:
            with st.spinner(">> Deducing Alpha..."):
                # 3. AI Analysis (Language Adaptive)
                result = consult_holmes(user_news, sonar_markets, active_key)
                st.markdown("---")
                st.markdown("### 📝 INVESTIGATION REPORT")
                st.markdown(result, unsafe_allow_html=True)
