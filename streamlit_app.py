import streamlit as st
import requests
import json
import google.generativeai as genai
import re
from supabase import create_client, Client

# ================= 🔐 0. KEY MANAGEMENT =================
try:
    EXA_API_KEY = st.secrets["EXA_API_KEY"]
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
    KEYS_LOADED = True
except (FileNotFoundError, KeyError):
    EXA_API_KEY = None
    GOOGLE_API_KEY = None
    KEYS_LOADED = False

try:
    SUPABASE_URL = st.secrets["supabase"]["url"]
    SUPABASE_KEY = st.secrets["supabase"]["key"]
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    AUTH_LOADED = True
except (FileNotFoundError, KeyError):
    AUTH_LOADED = False
    st.error("⚠️ Supabase Secrets Missing. Please check secrets.toml")

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

# ================= 🔐 AUTHENTICATION LOGIC (Hardened) =================
def handle_auth():
    """
    处理登录回调。
    增加了防抖逻辑：如果 session 已经存在，就不再处理 code，防止死循环。
    """
    if 'user' not in st.session_state:
        st.session_state.user = None

    # 如果已经登录，直接返回，不做任何 URL 处理，防止刷新循环
    if st.session_state.user:
        return

    try:
        query_params = st.query_params
        # 只有在 URL 里有 code 且 当前未登录 时才执行交换
        if "code" in query_params:
            res = supabase.auth.exchange_code_for_session({"auth_code": query_params["code"]})
            st.session_state.user = res.user
            # 登录成功后，清除 URL 参数并强制刷新一次，彻底进入“已登录”状态
            st.query_params.clear()
            st.rerun()
    except Exception as e:
        st.error(f"Auth Error: {e}")

if AUTH_LOADED:
    handle_auth()

# ================= 🎨 2. UI THEME =================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;900&family=Plus+Jakarta+Sans:wght@400;700&display=swap');

    .stApp {
        background-image: linear-gradient(rgba(0, 0, 0, 0.8), rgba(0, 0, 0, 0.9)), 
                          url('https://upload.cc/i1/2026/01/20/s8pvXA.jpg');
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
        font-family: 'Inter', sans-serif;
    }
    header[data-testid="stHeader"] { background-color: transparent !important; }
    [data-testid="stToolbar"] { visibility: hidden; }
    [data-testid="stDecoration"] { visibility: hidden; }

    .hero-title {
        font-family: 'Inter', sans-serif;
        font-weight: 700;
        font-size: 3.5rem; /* 稍微调小一点以免太占地 */
        color: #ffffff;
        text-align: center;
        letter-spacing: -2px;
        margin-bottom: 5px;
        padding-top: 5vh;
        text-shadow: 0 0 20px rgba(0,0,0,0.5);
    }
    .hero-subtitle {
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 1.1rem;
        color: #9ca3af; 
        text-align: center;
        margin-bottom: 30px;
        font-weight: 400;
    }

    /* Tab Styling */
    .stTabs [data-baseweb="tab-list"] {
        justify-content: center;
        background-color: transparent;
        border-bottom: 1px solid #374151;
    }
    .stTabs [data-baseweb="tab"] {
        color: #9ca3af;
        font-size: 1rem;
        padding: 10px 20px;
    }
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        color: #ffffff;
        border-bottom: 2px solid #dc2626;
    }

    /* Card & Textarea Styles (Keep Existing) */
    .stTextArea textarea {
        background-color: rgba(31, 41, 55, 0.6) !important;
        color: #ffffff !important;
        border: 1px solid #374151 !important;
        border-radius: 16px !important;
        padding: 15px 20px !important; 
        font-size: 1rem !important;
        line-height: 1.6 !important;
        backdrop-filter: blur(10px);
    }
    .market-card {
        background: rgba(17, 24, 39, 0.7);
        border: 1px solid #374151;
        border-radius: 12px;
        padding: 20px;
        margin: 20px auto;
        max-width: 800px;
        backdrop-filter: blur(8px);
    }
    
    /* Login Button */
    a[href^="https://accounts.google.com"], a[href*="supabase.co"] {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        background-color: white !important;
        color: #333 !important;
        font-weight: 600 !important;
        padding: 12px 30px !important;
        border-radius: 50px !important;
        text-decoration: none !important;
        transition: all 0.3s ease !important;
        border: 1px solid #ddd !important;
        margin-top: 10px;
    }
    a[href*="supabase.co"]:hover {
        transform: scale(1.05);
        box-shadow: 0 0 15px rgba(255, 255, 255, 0.3);
    }
    
    /* Profile Card */
    .profile-card {
        background: rgba(31, 41, 55, 0.5);
        border: 1px solid #4b5563;
        border-radius: 16px;
        padding: 30px;
        text-align: center;
        max-width: 500px;
        margin: 40px auto;
    }
</style>
""", unsafe_allow_html=True)

# ================= 🧠 3. LOGIC CORE (Keep Existing) =================
# ... (这里省略了中间没有变动的 search_with_exa, fetch_top_10, consult_holmes 函数，
# ...  为了节省篇幅，请保持原本这些函数的代码不变，逻辑完全一致)
# ...  👇 必须把原本的 helper functions 放在这里 👇

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
    if not EXA_AVAILABLE or not EXA_API_KEY: 
        st.warning("⚠️ Exa API Key missing. Skipping neural search.")
        return [], query
    search_query = generate_english_keywords(query)
    markets_found, seen_ids = [], set()
    try:
        exa = Exa(EXA_API_KEY)
        search_response = exa.search(
            f"prediction market about {search_query}",
            num_results=4, type="neural", include_domains=["polymarket.com"]
        )
        if search_response and search_response.results:
            for result in search_response.results:
                match = re.search(r'polymarket\.com/(?:event|market)/([^/]+)', result.url)
                if match:
                    slug = match.group(1)
                    if slug not in ['profile', 'login', 'leaderboard', 'rewards'] and slug not in seen_ids:
                        market_data = fetch_poly_details(slug)
                        if market_data:
                            markets_found.extend(market_data)
                            seen_ids.add(slug)
    except Exception: pass
    return markets_found, search_query

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
                    if not event_markets or not isinstance(event_markets, list): continue
                    active_markets = []
                    for m in event_markets:
                        if m.get('closed') is True: continue
                        if not m.get('outcomePrices'): continue
                        active_markets.append(m)
                    if not active_markets: continue
                    active_markets.sort(key=lambda x: float(x.get('volume', 0) or 0), reverse=True)
                    m = active_markets[0]
                    outcomes = m.get('outcomes')
                    if isinstance(outcomes, str): outcomes = json.loads(outcomes)
                    prices = m.get('outcomePrices')
                    if isinstance(prices, str): prices = json.loads(prices)
                    if not outcomes or not prices or len(prices) != len(outcomes): continue
                    yes_price, no_price = 0, 0
                    if "Yes" in outcomes and "No" in outcomes:
                        try:
                            yes_index = outcomes.index("Yes")
                            yes_raw = float(prices[yes_index])
                            yes_price = int(yes_raw * 100)
                            no_price = 100 - yes_price
                        except:
                            yes_price = int(float(prices[0]) * 100)
                            no_price = 100 - yes_price
                    else:
                        max_price = max([float(p) for p in prices])
                        yes_price = int(max_price * 100)
                        no_price = 100 - yes_price
                    markets.append({"title": title, "yes": yes_price, "no": no_price, "slug": event.get('slug', '')})
                except: continue
        return markets
    except: return []

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
        return {"title": m.get('question', 'Unknown'), "odds": odds_display, "volume": float(m.get('volume', 0)), "slug": m.get('slug', '') or m.get('market_slug', '')}
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

# ================= 🖥️ 4. MAIN INTERFACE (UI重构) =================

st.markdown('<h1 class="hero-title">Be Holmes</h1>', unsafe_allow_html=True)

# 🌟 状态判断：已登录 vs 未登录
if st.session_state.user:
    # ====== 已登录界面 (Tab 结构) ======
    st.markdown(f'<p class="hero-subtitle">Welcome back, {st.session_state.user.email}</p>', unsafe_allow_html=True)
    
    # 定义两个标签页：情报台 & 个人中心
    tab_research, tab_profile = st.tabs(["🔍 Decode Alpha", "👤 My Profile"])
    
    # --- Tab 1: 研究主页 (原来的功能) ---
    with tab_research:
        st.markdown("<br>", unsafe_allow_html=True)
        _, mid, _ = st.columns([1, 6, 1])
        with mid:
            user_news = st.text_area("Input", height=70, placeholder="Search for a market, region or event...", label_visibility="collapsed")
            
            _, btn_col, _ = st.columns([1, 2, 1])
            with btn_col:
                ignite_btn = st.button("Decode Alpha", use_container_width=True)

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

    # --- Tab 2: 个人中心 (新增) ---
    with tab_profile:
        st.markdown(f"""
        <div class="profile-card">
            <h3>👤 User Profile</h3>
            <p style="color:#9ca3af; margin-bottom:20px;">{st.session_state.user.email}</p>
            <p style="color:#6b7280; font-size:0.8rem;">ID: {st.session_state.user.id}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # 退出登录按钮放在这里
        _, logout_col, _ = st.columns([1, 1, 1])
        with logout_col:
            if st.button("Sign Out", use_container_width=True):
                supabase.auth.sign_out()
                st.session_state.user = None
                st.rerun()

    # --- 底部市场推荐 (仅在登录后显示) ---
    st.markdown("<br><hr style='border-color:#374151'><br>", unsafe_allow_html=True)
    top10_markets = fetch_top_10_markets()
    if top10_markets:
        cards_html = "".join([f"""
        <a href="https://polymarket.com/event/{m['slug']}" target="_blank" class="market-item">
            <div class="m-title" title="{m['title']}">{m['title']}</div>
            <div class="m-odds">
                <span class="tag-yes">Yes {m['yes']}¢</span>
                <span class="tag-no">No {m['no']}¢</span>
            </div>
        </a>""" for m in top10_markets])
        st.markdown(f"""<div class="top10-container"><div class="top10-header">Trending on Polymarket</div><div class="top10-grid">{cards_html}</div></div>""", unsafe_allow_html=True)

else:
    # ====== 未登录界面 (只显示 Login 按钮) ======
    st.markdown('<p class="hero-subtitle">Login to access neural prediction market analysis.</p>', unsafe_allow_html=True)
    
    if AUTH_LOADED:
        try:
            # 务必替换这里的 URL 为你真实的 Streamlit URL
            auth_resp = supabase.auth.sign_in_with_oauth({
                "provider": "google",
                "options": {
                    "redirectTo": "https://be-holmes.streamlit.app" 
                }
            })
            st.markdown(f"""
            <div style="text-align: center; margin-top: 40px;">
                <a href="{auth_resp.url}" target="_blank">
                    Login with Google to Decode Alpha
                </a>
            </div>
            """, unsafe_allow_html=True)
        except Exception as e:
            st.error(f"Login Config Error: {e}")
    else:
        st.error("Authentication Service Unavailable.")

    # 底部协议 (未登录时也显示)
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    with st.expander("Operational Protocol"):
        st.write("System requires authentication for alpha decoding.")
