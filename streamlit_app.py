import streamlit as st
import requests
import json
import google.generativeai as genai
import re

# ================= 🔑 0. API KEYS (HARDCODED) =================
EXA_API_KEY = "2b15f3e3-0787-4bdc-99c9-9e17aade05c2"
GOOGLE_API_KEY = "AIzaSyA7_zfVYaujlKudJPw9U8YnS5GA-yDpR5I"

genai.configure(api_key=GOOGLE_API_KEY)

# ================= 🛠️ 核心依赖检测 =================
try:
    from exa_py import Exa
    EXA_AVAILABLE = True
except ImportError:
    EXA_AVAILABLE = False

# ================= 🕵️‍♂️ 1. SYSTEM CONFIGURATION =================
st.set_page_config(
    page_title="Be Holmes | Genius Core",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ================= 🎨 2. UI DESIGN (Black & Gold Premium) =================
st.markdown("""
<style>
    [data-testid="stToolbar"] { visibility: hidden; height: 0%; position: fixed; }
    footer { visibility: hidden; }
    header { visibility: hidden; }
    
    .stApp { background-color: #050505; font-family: 'Roboto Mono', monospace; }
    [data-testid="stSidebar"] { background-color: #000000; border-right: 1px solid #1a1a1a; }
    
    /* 标题升级为金红渐变，体现尊贵与激进 */
    h1 { 
        background: linear-gradient(90deg, #FFD700, #FF4500); 
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        font-family: 'Georgia', serif; font-weight: 800;
        border-bottom: 2px solid #331111; padding-bottom: 15px;
    }
    
    h3, h4, label { color: #FFD700 !important; } /* 金色强调 */
    p, .stMarkdown, .stText, li, div, span { color: #B0B0B0 !important; }
    strong { color: #FFF !important; font-weight: 600; } 
    
    .stTextArea textarea, .stTextInput input { 
        background-color: #0A0A0A !important; color: #FFD700 !important; 
        border: 1px solid #333 !important; border-radius: 6px;
    }
    
    .execute-btn {
        background: linear-gradient(90deg, #FFD700, #DAA520); 
        border: none; color: black; width: 100%; padding: 15px;
        font-weight: 900; font-size: 16px; cursor: pointer; border-radius: 6px;
        text-transform: uppercase; letter-spacing: 2px; margin-top: 10px;
    }
    
    .market-card {
        background-color: #080808; border: 1px solid #333; border-left: 4px solid #FFD700;
        padding: 20px; margin: 15px 0; transition: all 0.3s;
    }
    .market-card:hover { border-color: #FFD700; box-shadow: 0 0 20px rgba(255, 215, 0, 0.1); }
    
    .report-box {
        background-color: #0F0F0F; border: 1px solid #333; padding: 25px;
        border-radius: 8px; margin-top: 20px;
        font-family: 'Georgia', serif; /* 报告使用衬线体，更显专业 */
    }
    
    .stButton button {
        background: linear-gradient(90deg, #FF4500, #B22222) !important;
        color: white !important; border: none !important;
    }
</style>
""", unsafe_allow_html=True)

# ================= 🧠 3. CORE LOGIC & TRANSLATION =================

def detect_language(text):
    for char in text:
        if '\u4e00' <= char <= '\u9fff':
            return "CHINESE"
    return "ENGLISH"

def generate_english_keywords(user_text):
    """智能提炼关键词 (Bilingual Bridge)"""
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        prompt = f"""
        Task: Extract English search keywords for Polymarket.
        Input: "{user_text}"
        Output: Concise English keywords only (e.g. Trump Greenland Tariffs).
        """
        resp = model.generate_content(prompt)
        return resp.text.strip()
    except: return user_text

def search_with_exa(query):
    if not EXA_AVAILABLE: return [], query
    
    search_query = generate_english_keywords(query)
    markets_found, seen_ids = [], set()
    
    try:
        exa = Exa(EXA_API_KEY)
        # Neural Search
        search_response = exa.search(
            f"prediction market about {search_query}",
            num_results=4,
            type="neural",
            include_domains=["polymarket.com"]
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
    except Exception as e: print(f"Search Error: {e}")
        
    return markets_found, search_query

def fetch_poly_details(slug):
    valid_markets = []
    # Try Event
    try:
        url = f"https://gamma-api.polymarket.com/events?slug={slug}"
        resp = requests.get(url, timeout=3).json()
        if isinstance(resp, list) and resp:
            for m in resp[0].get('markets', [])[:2]:
                p = normalize_data(m)
                if p: valid_markets.append(p)
            return valid_markets
    except: pass
    # Try Market
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
        outcomes = json.loads(m.get('outcomes', '[]')) if isinstance(m.get('outcomes'), str) else m.get('outcomes')
        prices = json.loads(m.get('outcomePrices', '[]')) if isinstance(m.get('outcomePrices'), str) else m.get('outcomePrices')
        
        odds_display = "N/A"
        if outcomes and prices:
            odds_display = f"{outcomes[0]}: {float(prices[0])*100:.1f}%"
            
        return {
            "title": m.get('question', 'Unknown'),
            "odds": odds_display,
            "volume": float(m.get('volume', 0)),
            "slug": m.get('slug', '') or m.get('market_slug', '')
        }
    except: return None

# ================= 🌟 4. THE GENIUS SOUL (PROMPT ENGINEERING) =================

def consult_holmes(user_input, market_data):
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        # 语言与角色设定
        lang = detect_language(user_input)
        if lang == "CHINESE":
            lang_instruction = "IMPORTANT: Respond in **CHINESE (中文)**."
            role_desc = """
            你现在是 **Be Holmes**，一位拥有 20 年经验的华尔街顶级宏观对冲基金经理，也是预测市场套利天才。
            你的性格：极度理性、甚至有点愤世嫉俗、不仅看新闻，更看透新闻背后的博弈和定价效率。
            你不相信简单的线性逻辑（比如“他说要加税就一定会加税”），你懂得“政治作秀”和“市场定价”的区别。
            """
        else:
            lang_instruction = "IMPORTANT: Respond in **ENGLISH**."
            role_desc = """
            You are **Be Holmes**, a legendary Wall Street Macro Hedge Fund Manager and Prediction Market Genius.
            Your personality: Hyper-rational, cynical, seeing through the noise.
            You do not believe in linear logic (e.g., "Trump tweeted it, so it happens"). You understand "Priced-in" and "Political Bluffing".
            """

        market_context = ""
        if market_data:
            m = market_data[0]
            market_context = f"Target Market: {m['title']}\nCurrent Market Odds (Price): {m['odds']}\nVolume: ${m['volume']:,.0f}"
        else:
            market_context = "No specific prediction market found. Provide Macro Strategy only."

        # 🔥 天才的 Prompt 逻辑 🔥
        prompt = f"""
        {role_desc}
        
        [User Intel]: "{user_input}"
        [Market Data]: 
        {market_context}
        
        {lang_instruction}
        
        **YOUR MISSION: DECODE THE ALPHA.**
        Analyze the situation like a PRO TRADER. Do not act like a naive summary bot.
        
        **Analysis Framework:**
        
        1.  **🕵️‍♂️ Priced-in Check (市场是否已知悉？):** - Look at the User Intel. Is this "Breaking News" (minutes ago) or "Old News" (hours/days ago)?
            - If it's old news, and the odds are still low/high, ask WHY? (e.g., "If Trump tweeted yesterday, why is the market still only 40%? The market doubts him.")
            
        2.  **⚖️ The Bluff vs. Reality (博弈分析):**
            - For political events (Trump, Tariffs, Wars): Distinguish between "Rhetoric" (Tweets/Threats) and "Execution" (Laws/Orders).
            - Consider the timeline. Is there enough time to execute before the deadline?
            
        3.  **🧠 The Verdict (交易决策):**
            - **🟢 AGGRESSIVE BUY:** If the market is asleep (Odds < 20%) and the news is REAL/NEW.
            - **🟡 CONTRARIAN BET:** If the market is overreacting (Odds > 80%) to fake news.
            - **⚪ WAIT / NEUTRAL:** If the news is already priced in (the odds fairly reflect the risk).
        
        **Output Format (Markdown):**
        > "Here is the truth behind the noise..."
        
        ### 🧠 Holmes' Strategic Analysis
        * **Market Psychology:** [Explain what the crowd is thinking vs. reality]
        * **Risk/Reward:** [Is the payoff worth the risk?]
        * **Final Call:** [BUY YES / BUY NO / DO NOTHING]
        """
        return model.generate_content(prompt).text
    except Exception as e: return f"AI Error: {e}"

# ================= 🖥️ 5. MAIN INTERFACE =================

with st.sidebar:
    st.markdown("## 💼 DETECTIVE'S TOOLKIT")
    st.success("✅ Genius Core: Online")
    st.caption("Engine: Exa Neural + Gemini Pro")
    
    st.markdown("---")
    st.markdown("### 🌊 Live Alpha Stream")
    try:
        url = "https://gamma-api.polymarket.com/markets?limit=3&sort=volume&closed=false"
        live_mkts = requests.get(url, timeout=3).json()
        for m in live_mkts:
            p = normalize_data(m)
            if p:
                st.markdown(f"**{p['title'][:25]}...**")
                st.code(f"{p['odds']}")
                st.caption(f"Vol: ${p['volume']:,.0f}")
                st.markdown("---")
    except:
        st.warning("Feed Offline")

c1, c2 = st.columns([5, 1])
with c1:
    st.title("Be Holmes")
    st.caption("THE GENIUS TRADER | V15.0")
with c2:
    if st.button("📘 Manual"):
        @st.dialog("User Manual")
        def manual():
            st.markdown("""
            ### 🧠 How to think like Holmes
            1. **Input:** News/Rumors (e.g., "Trump tariffs").
            2. **Processing:** Holmes checks if this news is **"Priced In"**.
            3. **Output:** A contrarian or aggressive trading strategy, not just a summary.
            """)
        manual()

st.markdown("---")

user_news = st.text_area("Input Intel / News...", height=100, label_visibility="collapsed", placeholder="输入情报... (e.g. 特朗普2月1日加征关税)")
ignite_btn = st.button("🔍 DECODE ALPHA", use_container_width=True)

if ignite_btn:
    if not user_news:
        st.warning("⚠️ Input required.")
    else:
        with st.status("🧠 Analyzing Market Psychology...", expanded=True) as status:
            # 1. 搜索
            st.write("🛰️ Exa Sniper: Locating Contract...")
            matches, keyword = search_with_exa(user_news)
            
            if matches:
                st.write(f"✅ Target Locked: '{matches[0]['title']}'")
            else:
                st.warning(f"⚠️ No direct contract found for '{keyword}'. Switching to Macro Analysis.")
            
            # 2. 灵魂分析
            st.write("⚖️ Calculating Bayseian Probability...")
            report = consult_holmes(user_news, matches)
            status.update(label="✅ Strategy Generated", state="complete", expanded=False)

        # 3. 结果展示
        if matches:
            st.markdown("### 🎯 Target Contract")
            m = matches[0] 
            st.markdown(f"""
            <div class="market-card">
                <div style="font-size:1.3em; color:#FFD700; font-weight:bold;">{m['title']}</div>
                <div style="margin-top:10px; font-family:monospace; display:flex; justify-content:space-between; align-items:center;">
                    <span style="color:#FF4500; font-size:1.6em; font-weight:900;">⚡ {m['odds']}</span>
                    <span style="color:#888;">Vol: ${m['volume']:,.0f}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            link = f"https://polymarket.com/event/{m['slug']}" 
            st.markdown(f"<a href='{link}' target='_blank'><button class='execute-btn'>🚀 EXECUTE ON POLYMARKET</button></a>", unsafe_allow_html=True)

        st.markdown("### 🧠 Holmes' Strategic Report")
        st.markdown(f"<div class='report-box'>{report}</div>", unsafe_allow_html=True)
