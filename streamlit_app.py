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

# 🔥 DOME KEY (Backup)
DOME_API_KEY = "6f08669ca2c6a9541f0ef1c29e5928d2dc22857b"

# 🔥 FAIL-SAFE DICTIONARY
KNOWN_SLUGS = {
    "spacex": ["spacex-ipo-closing-market-cap", "will-spacex-ipo-in-2025"],
    "trump": ["presidential-election-winner-2028"],
    "gpt": ["chatgpt-5-release-in-2025"],
    "rate": ["fed-interest-rates-nov-2024"]
}

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
    /* 报告卡片样式 */
    .report-card {
        background-color: #111; border: 1px solid #333; 
        border-left: 5px solid #FF4500; padding: 20px; margin-bottom: 20px;
    }
    .market-card {
        background-color: #080808; border: 1px solid #222;
        padding: 15px; margin-bottom: 10px; border-radius: 5px;
    }
    .execute-btn {
        background: linear-gradient(90deg, #FF4500, #FFD700); 
        border: none; color: #000; width: 100%; padding: 15px;
        font-weight: 900; font-size: 16px; cursor: pointer; border-radius: 6px;
        text-transform: uppercase; letter-spacing: 2px; margin-top: 20px;
    }
</style>
""", unsafe_allow_html=True)

# ================= 🔐 3. KEY MANAGEMENT =================
active_key = None

# ================= 🧠 4. CORE LOGIC: ANALYSIS FIRST =================

def generate_alpha_report(news, key):
    """
    Step 1: 纯 AI 逻辑推理 (不依赖 Polymarket)
    生成一份专业的宏观/事件驱动分析报告。
    """
    try:
        genai.configure(api_key=key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        prompt = f"""
        Role: You are **Be Holmes**, a legendary Global Macro Strategist & Alpha Hunter.
        You have a sharp nose for 2nd & 3rd order effects.
        
        Input News: "{news}"
        
        Task: Analyze this news and provide an investment thesis.
        
        **OUTPUT FORMAT (Markdown):**
        
        ### 🧠 Holmes' Strategic Thesis
        
        **1. The Signal (信号判读)**
        > [One sentence summary: Bullish/Bearish/Neutral for what asset?]
        
        **2. The Ripple Effect (二阶推演)**
        * [Direct Impact]: e.g., SpaceX IPO -> TSLA stock up.
        * [Hidden Impact]: e.g., Competitors (Boeing) down.
        
        **3. Actionable Advice (投资建议)**
        * **Long (做多):** [Assets]
        * **Short (做空):** [Assets]
        * **Prediction Market Strategy:** What specific "Yes/No" bet would you look for? (e.g., "Bet YES on SpaceX IPO before Dec")
        """
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"❌ Analysis Failed: {str(e)}"

def extract_search_keyword(news, key):
    """提取一个最核心的搜索词"""
    try:
        genai.configure(api_key=key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(f"Extract ONE core English entity keyword from: '{news}'. Output only the word.")
        return response.text.strip()
    except: return news.split()[0]

# ================= 📡 5. DATA LOGIC: SEARCH SECOND =================

def normalize_market_data(m):
    try:
        if m.get('closed') is True: return None
        title = m.get('question', m.get('title', 'Unknown'))
        slug = m.get('slug', m.get('market_slug', ''))
        odds = "N/A"
        try:
            outcomes = json.loads(m.get('outcomes', '[]')) if isinstance(m.get('outcomes'), str) else m.get('outcomes')
            prices = json.loads(m.get('outcomePrices', '[]')) if isinstance(m.get('outcomePrices'), str) else m.get('outcomePrices')
            if outcomes and prices:
                odds = " | ".join([f"{o}: {float(p)*100:.1f}%" for o, p in zip(outcomes, prices)])
        except: pass
        return {"title": title, "odds": odds, "slug": slug, "volume": float(m.get('volume', 0))}
    except: return None

def search_polymarket(keyword):
    """V3.0 搜索逻辑：Gamma API + Dome + Failsafe"""
    results = []
    seen = set()
    
    # 1. Gamma Search API
    try:
        url = "https://gamma-api.polymarket.com/search"
        resp = requests.get(url, params={"query": keyword, "limit": 20}, headers={"User-Agent": "BeHolmes/4.0"}, timeout=4)
        if resp.status_code == 200:
            data = resp.json()
            for m in data.get("markets", []):
                p = normalize_market_data(m)
                if p and p['slug'] not in seen:
                    results.append(p)
                    seen.add(p['slug'])
    except: pass
    
    # 2. Hardcoded Failsafe (If API fails)
    if not results:
        for k, slugs in KNOWN_SLUGS.items():
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
                    
    results.sort(key=lambda x: x['volume'], reverse=True)
    return results

# ================= 🖥️ 6. MAIN INTERFACE =================

with st.sidebar:
    st.markdown("## 💼 DETECTIVE'S TOOLKIT")
    with st.expander("🔑 API Key Settings", expanded=True):
        user_api_key = st.text_input("Gemini Key", type="password")
        st.markdown("[Get Free Key](https://aistudio.google.com/app/apikey)")
        st.caption("✅ Mode: Analyst First")

    if user_api_key:
        active_key = user_api_key
        st.success("🔓 Gemini: Active")
    elif "GEMINI_KEY" in st.secrets:
        active_key = st.secrets["GEMINI_KEY"]
        st.info("🔒 System Key Active")
    else:
        st.error("⚠️ Gemini Key Missing!")
        st.stop()

# --- Main Stage ---
st.title("Be Holmes")
st.caption("EVENT-DRIVEN INTELLIGENCE | V4.0 OPINION FIRST") 
st.markdown("---")

user_news = st.text_area("Input Evidence...", height=150, label_visibility="collapsed", placeholder="Input news... (e.g. SpaceX IPO rumors)")
ignite_btn = st.button("🔍 INVESTIGATE", use_container_width=True)

if ignite_btn:
    if not user_news:
        st.warning("⚠️ Evidence required.")
    else:
        # === PHASE 1: THE ANALYSIS (100% Guaranteed) ===
        with st.status("🧠 Phase 1: Holmes is Thinking...", expanded=True) as status:
            st.write("Generating macro thesis & investment strategy...")
            report = generate_alpha_report(user_news, active_key)
            status.update(label="✅ Phase 1 Complete: Thesis Generated", state="complete", expanded=False)
        
        # Display Report
        st.markdown(f"""<div class="report-card">{report}</div>""", unsafe_allow_html=True)
        
        # === PHASE 2: THE HUNT (Search) ===
        st.markdown("---")
        st.subheader("🌊 Phase 2: Polymarket Verification")
        
        with st.spinner("Searching for relevant prediction markets..."):
            keyword = extract_search_keyword(user_news, active_key)
            st.caption(f"Searching for: '{keyword}'")
            markets = search_polymarket(keyword)
            
            if markets:
                st.success(f"✅ Found {len(markets)} active markets matching the thesis.")
                for m in markets[:3]: # Show top 3
                    st.markdown(f"""
                    <div class="market-card">
                        <div style="font-size:1.1em; color:#FFD700; margin-bottom:5px;">{m['title']}</div>
                        <div style="font-family:monospace; color:#E63946;">⚡ ODDS: {m['odds']}</div>
                        <div style="font-size:0.8em; color:#666;">Vol: ${m['volume']:,.0f}</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Execution Button
                st.markdown(f"""<a href='https://polymarket.com/?q={keyword}' target='_blank' style='text-decoration:none;'><button class='execute-btn'>🚀 TRADE THIS VIEW</button></a>""", unsafe_allow_html=True)
            else:
                st.info("⚠️ No direct prediction markets found currently.")
                st.markdown("> **Holmes' Note:** While no specific betting market exists yet, the investment advice in Phase 1 remains valid for traditional markets (Stocks/Crypto).")
