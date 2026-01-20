import streamlit as st
import requests
import json
import google.generativeai as genai
import re

# ================= 🔐 0. KEY MANAGEMENT =================
try:
    EXA_API_KEY = st.secrets["EXA_API_KEY"]
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
    KEYS_LOADED = True
except FileNotFoundError:
    EXA_API_KEY = None
    GOOGLE_API_KEY = None
    KEYS_LOADED = False
except KeyError:
    EXA_API_KEY = st.secrets.get("EXA_API_KEY", None)
    GOOGLE_API_KEY = st.secrets.get("GOOGLE_API_KEY", None)
    KEYS_LOADED = bool(EXA_API_KEY and GOOGLE_API_KEY)

if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

# ================= 🛠️ DEPENDENCY CHECK =================
try:
    from exa_py import Exa
    EXA_AVAILABLE = True
except ImportError:
    EXA_AVAILABLE = False

# ================= 🕵️‍♂️ 1. SYSTEM CONFIGURATION =================
st.set_page_config(
    page_title="Be Holmes | Research",
    page_icon="🕵️‍♂️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ================= 🎨 2. UI THEME (UPDATED FOR CLICKABLE CARDS) =================
st.markdown("""
<style>
    /* Import Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;900&family=Plus+Jakarta+Sans:wght@400;700&display=swap');

    /* 1. Global Background */
    .stApp {
        background-image: linear-gradient(rgba(0, 0, 0, 0.8), rgba(0, 0, 0, 0.9)), 
                          url('https://images.unsplash.com/photo-1451187580459-43490279c0fa?q=80&w=2072&auto=format&fit=crop');
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
        font-family: 'Inter', sans-serif;
    }

    /* Transparent Header */
    header[data-testid="stHeader"] { background-color: transparent !important; }
    [data-testid="stToolbar"] { visibility: hidden; }
    [data-testid="stDecoration"] { visibility: hidden; }

    /* Hero Title */
    .hero-title {
        font-family: 'Inter', sans-serif;
        font-weight: 700;
        font-size: 4.5rem;
        color: #ffffff;
        text-align: center;
        letter-spacing: -2px;
        margin-bottom: 5px;
        padding-top: 8vh;
        text-shadow: 0 0 20px rgba(0,0,0,0.5);
    }
    
    .hero-subtitle {
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 1.1rem;
        color: #9ca3af; 
        text-align: center;
        margin-bottom: 50px;
        font-weight: 400;
    }

    /* 4. Input Field Styling (已修复：左对齐 + 字体优化) */
    div[data-testid="stVerticalBlock"] > div {
        display: flex;
        flex-direction: column;
        align-items: center;
    }
    .stTextArea { width: 100% !important; max-width: 800px !important; }
    
    .stTextArea textarea {
        background-color: rgba(31, 41, 55, 0.6) !important;
        color: #ffffff !important;
        border: 1px solid #374151 !important;
        border-radius: 16px !important;
        
        /* 修改点在这里：左对齐，调整内边距，调整字号 */
        padding: 15px 20px !important; 
        font-size: 1rem !important; /* 从 1.1rem 改为 1rem */
        text-align: left !important; /* 从 center 改为 left */
        line-height: 1.6 !important; /* 增加行高，让中文更易读 */
        
        backdrop-filter: blur(10px);
        transition: all 0.3s ease;
    }
    
    /* Input Focus - Red Glow */
    .stTextArea textarea:focus {
        border-color: rgba(239, 68, 68, 0.8) !important;
        box-shadow: 0 0 15px rgba(220, 38, 38, 0.3) !important;
        background-color: rgba(31, 41, 55, 0.9) !important;
    }

    /* 3. Button Styling: Red Gradient */
    div.stButton > button:first-child {
        background: linear-gradient(90deg, #7f1d1d 0%, #dc2626 50%, #7f1d1d 100%) !important;
        background-size: 200% auto !important;
        color: #ffffff !important;
        border: 1px solid rgba(239, 68, 68, 0.5) !important;
        border-radius: 50px !important;
        padding: 12px 50px !important;
        font-weight: 600 !important;
        font-size: 1.1rem !important;
        margin-top: 10px !important;
        transition: 0.5s !important;
        box-shadow: 0 0 20px rgba(0,0,0,0.5) !important;
    }
    
    div.stButton > button:first-child:hover {
        background-position: right center !important;
        transform: scale(1.05) !important;
        box-shadow: 0 0 30px rgba(220, 38, 38, 0.6) !important;
        border-color: #fca5a5 !important;
    }
    
    div.stButton > button:first-child:active {
        transform: scale(0.98) !important;
    }

    /* Result Card */
    .market-card {
        background: rgba(17, 24, 39, 0.7);
        border: 1px solid #374151;
        border-radius: 12px;
        padding: 20px;
        margin: 20px auto;
        max-width: 800px;
        backdrop-filter: blur(8px);
    }

    /* Bottom Grid Styling */
    .top10-container {
        width: 100%;
        max-width: 1200px;
        margin: 60px auto 20px auto;
        padding: 0 20px;
    }
    .top10-header {
        font-size: 0.9rem;
        color: #9ca3af;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 20px;
        border-left: 3px solid #dc2626;
        padding-left: 10px;
    }
    
    .top10-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 15px;
    }

    @media (max-width: 1000px) { .top10-grid { grid-template-columns: repeat(2, 1fr); } }
    @media (max-width: 600px) { .top10-grid { grid-template-columns: 1fr; } }

    .market-item {
        background: rgba(17, 24, 39, 0.6);
        border: 1px solid #374151;
        border-radius: 8px;
        padding: 15px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        transition: all 0.2s;
        backdrop-filter: blur(5px);
        min-height: 110px;
        
        text-decoration: none !important;
        color: inherit !important;
        cursor: pointer;
    }
    .market-item:hover {
        border-color: #ef4444;
        background: rgba(31, 41, 55, 0.9);
        transform: translateY(-2px);
    }
    .m-title {
        color: #e5e7eb;
        font-size: 0.95rem;
        font-weight: 500;
        margin-bottom: 12px;
        line-height: 1.4;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }
    .m-odds {
        display: flex;
        gap: 8px;
        font-family: 'Inter', monospace;
        font-size: 0.75rem;
        margin-top: auto;
    }
    .tag-yes {
        background: rgba(6, 78, 59, 0.4);
        color: #4ade80;
        border: 1px solid rgba(34, 197, 94, 0.3);
        padding: 2px 8px;
        border-radius: 4px;
        font-weight: 600;
    }
    .tag-no {
        background: rgba(127, 29, 29, 0.4);
        color: #f87171;
        border: 1px solid rgba(239, 68, 68, 0.3);
        padding: 2px 8px;
        border-radius: 4px;
        font-weight: 600;
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
    except Exception as e: print(f"Search error: {e}")
    return markets_found, search_query

# Cache Top 12 Data
@st.cache_data(ttl=60)
def fetch_top_10_markets():
    try:
        url = "https://gamma-api.polymarket.com/events?limit=12&sort=volume&closed=false"
        resp = requests.get(url, timeout=5).json()
        
        markets = []
        
        if isinstance(resp, list):
            for event in resp:
                try:
                    title = event.get('title', 'Unknown Event')
                    event_markets = event.get('markets', [])
                    if not event_markets or not isinstance(event_markets, list):
                        continue

                    m = event_markets[0]
                    
                    outcomes = m.get('outcomes')
                    if isinstance(outcomes, str): outcomes = json.loads(outcomes)
                        
                    prices = m.get('outcomePrices')
                    if isinstance(prices, str): prices = json.loads(prices)
                    
                    if not outcomes or not prices: continue

                    yes_price = 0
                    no_price = 0
                    
                    if len(prices) >= 2:
                        yes_price = int(float(prices[0]) * 100)
                        no_price = int(float(prices[1]) * 100)
                    elif len(prices) == 1:
                        yes_price = int(float(prices[0]) * 100)
                        no_price = 100 - yes_price

                    markets.append({
                        "title": title,
                        "yes": yes_price,
                        "no": no_price,
                        "slug": event.get('slug', '')
                    })
                except Exception:
                    continue
        return markets
    except Exception:
        return []

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
        outcomes = m.get('outcomes')
        if isinstance(outcomes, str): outcomes = json.loads(outcomes)
        
        prices = m.get('outcomePrices')
        if isinstance(prices, str): prices = json.loads(prices)
        
        odds_display = "N/A"
        if outcomes and prices and len(outcomes) > 0 and len(prices) > 0:
            odds_display = f"{outcomes[0]}: {float(prices[0])*100:.1f}%"
            
        return {
            "title": m.get('question', 'Unknown'),
            "odds": odds_display,
            "volume": float(m.get('volume', 0)),
            "slug": m.get('slug', '') or m.get('market_slug', '')
        }
    except: return None

def consult_holmes(user_input, market_data):
    if not GOOGLE_API_KEY: return "AI Key Missing."
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        lang = detect_language(user_input)
        if lang == "CHINESE":
            lang_instruction = "IMPORTANT: Respond in **CHINESE (中文)**."
            role_desc = "你现在是 **Be Holmes**，一位极度理性、只相信数据和博弈论的顶级宏观对冲基金经理。"
        else:
            lang_instruction = "IMPORTANT: Respond in **ENGLISH**."
            role_desc = "You are **Be Holmes**, a legendary Wall Street Macro Hedge Fund Manager. Rational, cynical, and data-driven."

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
        1. **Priced-in Check**
        2. **Bluff vs Reality**
        3. **Verdict**
        
        Output as a concise professional briefing.
        """
        return model.generate_content(prompt).text
    except Exception as e: return f"AI Error: {e}"

# ================= 🖥️ 4. MAIN INTERFACE =================

# 4.1 Hero Section
st.markdown('<h1 class="hero-title">Be Holmes</h1>', unsafe_allow_html=True)
st.markdown('<p class="hero-subtitle">Explore the world\'s prediction markets with neural search.</p>', unsafe_allow_html=True)

# 4.2 Search Section
_, mid, _ = st.columns([1, 6, 1])
with mid:
    user_news = st.text_area("Input", height=70, placeholder="Search for a market, region or event...", label_visibility="collapsed")

# 4.3 Button Section
_, btn_col, _ = st.columns([1, 2, 1])
with btn_col:
    ignite_btn = st.button("Decode Alpha", use_container_width=True)

# 4.4 Execution Logic
if ignite_btn:
    if not KEYS_LOADED:
        st.error("🔑 API Keys not found in Secrets.")
    elif not user_news:
        st.warning("Please enter intelligence to analyze.")
    else:
        with st.container():
            st.markdown("---")
            with st.status("Running Neural Analysis...", expanded=True) as status:
                st.write("Mapping Semantics...")
                matches, keyword = search_with_exa(user_news)
                st.write("Calculating Probabilities...")
                report = consult_holmes(user_news, matches)
                status.update(label="Analysis Complete", state="complete", expanded=False)

            if matches:
                m = matches[0]
                st.markdown(f"""
                <div class="market-card">
                    <div style="font-size:1.2rem; color:#e5e7eb; margin-bottom:10px;">{m['title']}</div>
                    <div style="display:flex; justify-content:space-between; align-items:flex-end;">
                        <div>
                            <div style="font-family:'Plus Jakarta Sans'; color:#4ade80; font-size:1.8rem; font-weight:700;">{m['odds']}</div>
                            <div style="color:#9ca3af; font-size:0.8rem;">Implied Probability</div>
                        </div>
                        <div style="text-align:right;">
                            <div style="color:#e5e7eb; font-weight:600; font-size:1.2rem;">${m['volume']:,.0f}</div>
                            <div style="color:#9ca3af; font-size:0.8rem;">Volume</div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
            st.markdown(f"<div style='background:transparent; border-left:3px solid #dc2626; padding:15px 20px; color:#d1d5db; line-height:1.6;'>{report}</div>", unsafe_allow_html=True)

# ================= 📉 5. BOTTOM SECTION: TOP 12 MARKETS =================

top10_markets = fetch_top_10_markets()

if top10_markets:
    # UPDATED: Use <a> tag instead of <div> for the card wrapper
    # Added href linking to Polymarket event page
    cards_html = "".join([f"""
    <a href="https://polymarket.com/event/{m['slug']}" target="_blank" class="market-item">
        <div class="m-title" title="{m['title']}">{m['title']}</div>
        <div class="m-odds">
            <span class="tag-yes">Yes {m['yes']}¢</span>
            <span class="tag-no">No {m['no']}¢</span>
        </div>
    </a>""" for m in top10_markets])

    final_html = f"""
    <div class="top10-container">
        <div class="top10-header">Trending on Polymarket (Top 12)</div>
        <div class="top10-grid">{cards_html}</div>
    </div>
    """
    
    st.markdown(final_html, unsafe_allow_html=True)
else:
    st.markdown("""
    <div style="text-align:center; margin-top:50px; color:#666;">
        Connecting to Prediction Markets...
    </div>
    """, unsafe_allow_html=True)

# Footer
st.markdown("<br>", unsafe_allow_html=True)
with st.expander("Explore Protocol & Credits"):
    st.markdown("""
    <div style="text-align:center; color:#6b7280; font-size:0.9rem;">
        Powered by <b>Exa.ai</b> & <b>Google Gemini</b><br>
        Data source: Polymarket Gamma API
    </div>
    """, unsafe_allow_html=True)

