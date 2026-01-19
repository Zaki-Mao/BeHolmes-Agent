import streamlit as st
import requests
import json
import google.generativeai as genai
import re

# ================= 🔑 0. API KEY CONFIG (HARDCODED) =================
# 你提供的 Exa Key 已内置
EXA_API_KEY = "2b15f3e3-0787-4bdc-99c9-9e17aade05c2"

# ================= 🛠️ 核心依赖检测 =================
try:
    from exa_py import Exa
    EXA_AVAILABLE = True
except ImportError:
    EXA_AVAILABLE = False

# ================= 🕵️‍♂️ 1. SYSTEM CONFIGURATION =================
st.set_page_config(
    page_title="Be Holmes | Exa Sniper",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ================= 🎨 2. UI DESIGN (V1.0 CLASSIC RED/BLACK) =================
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
    
    h3, h4, label { color: #FF4500 !important; } 
    p, .stMarkdown, .stText, li, div, span { color: #A0A0A0 !important; }
    strong { color: #FFF !important; font-weight: 600; } 
    
    .stTextArea textarea, .stTextInput input { 
        background-color: #0A0A0A !important; color: #E63946 !important; 
        border: 1px solid #333 !important; border-radius: 6px;
    }
    .stTextInput input:focus { border-color: #FF4500 !important; }
    
    .execute-btn {
        background: linear-gradient(90deg, #FF4500, #8B0000); 
        border: none; color: white; width: 100%; padding: 15px;
        font-weight: 900; font-size: 16px; cursor: pointer; border-radius: 6px;
        text-transform: uppercase; letter-spacing: 2px; margin-top: 10px;
    }
    
    .market-card {
        background-color: #080808; border: 1px solid #222; border-left: 4px solid #FF4500;
        padding: 20px; margin: 15px 0; transition: all 0.3s;
    }
    .market-card:hover { border-color: #FF4500; box-shadow: 0 0 15px rgba(255, 69, 0, 0.2); }
    
    .stButton button {
        background: linear-gradient(90deg, #FF4500, #B22222) !important;
        color: white !important; border: none !important;
    }
</style>
""", unsafe_allow_html=True)

# ================= 🧠 3. EXA SEARCH ENGINE =================

def search_with_exa(query):
    """
    使用内置 Key 进行 Exa 搜索
    """
    if not EXA_AVAILABLE:
        st.error("❌ 'exa_py' library missing. Check requirements.txt")
        return []

    markets_found = []
    seen_ids = set()
    
    try:
        # 初始化 Exa
        exa = Exa(EXA_API_KEY)
        
        # 核心搜索逻辑
        # 1. include_domains: 锁定官网
        # 2. neural: 开启语义理解
        search_response = exa.search(
            f"prediction market about {query}",
            num_results=5,
            type="neural",
            include_domains=["polymarket.com"],
            use_autoprompt=True
        )
        
        for result in search_response.results:
            url = result.url
            # 正则提取 Slug (支持 event 和 market 两种 URL 结构)
            match = re.search(r'polymarket\.com/(?:event|market)/([^/]+)', url)
            
            if match:
                slug = match.group(1)
                # 过滤无效页面
                if slug not in ['profile', 'login', 'leaderboard', 'rewards'] and slug not in seen_ids:
                    
                    # 拿 Slug 去换数据
                    market_data = fetch_poly_details(slug)
                    if market_data:
                        markets_found.extend(market_data)
                        seen_ids.add(slug)
                        
    except Exception as e:
        st.error(f"Exa Search Error: {e}")
        
    return markets_found

def fetch_poly_details(slug):
    """去 Polymarket 官方 API 获取实时数据"""
    valid_markets = []
    
    # 策略 A: 查 Event (聚合页)
    try:
        url = f"https://gamma-api.polymarket.com/events?slug={slug}"
        resp = requests.get(url, timeout=4)
        if resp.status_code == 200:
            data = resp.json()
            if data and isinstance(data, list):
                # Event 下通常有多个 Market，取前 2 个最有代表性的
                for m in data[0].get('markets', [])[:2]:
                    p = normalize_data(m)
                    if p: valid_markets.append(p)
                return valid_markets
    except: pass
    
    # 策略 B: 查 Market (独立页)
    try:
        url = f"https://gamma-api.polymarket.com/markets?slug={slug}"
        resp = requests.get(url, timeout=4)
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, list):
                for m in data:
                    p = normalize_data(m)
                    if p: valid_markets.append(p)
            elif isinstance(data, dict):
                p = normalize_data(data)
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
            # 格式化赔率：Yes: 45.2%
            odds_display = f"{outcomes[0]}: {float(prices[0])*100:.1f}%"
            
        return {
            "title": m.get('question', 'Unknown'),
            "odds": odds_display,
            "volume": float(m.get('volume', 0)),
            "slug": m.get('slug', '') or m.get('market_slug', '')
        }
    except: return None

# ================= 🤖 4. AI ANALYST =================

def consult_holmes(user_input, market_data, key):
    try:
        genai.configure(api_key=key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        market_context = ""
        if market_data:
            m = market_data[0]
            market_context = f"Found Market: {m['title']} | Odds: {m['odds']} | Vol: ${m['volume']:,.0f}"
        else:
            market_context = "No direct market found."
            
        prompt = f"""
        Role: **Be Holmes**, The Semantic Sniper.
        User Input: "{user_input}"
        Exa Evidence: {market_context}
        
        Task:
        1. **Semantic Link:** Explain the connection between the user's input and the market found.
        2. **Verdict:** Based on the news, is the market Odds OVERVALUED or UNDERVALUED?
        3. **Strategy:** Buy Yes / Buy No / Wait.
        
        Output in concise Markdown.
        """
        return model.generate_content(prompt).text
    except Exception as e: return f"AI Error: {e}"

# ================= 🖥️ 5. MAIN INTERFACE =================

active_gemini_key = None

with st.sidebar:
    st.markdown("## 💼 DETECTIVE'S TOOLKIT")
    
    # 只需输入 Gemini Key，Exa Key 已内置
    with st.expander("🔑 Gemini Key (Required)", expanded=True):
        gemini_input = st.text_input("Gemini Key", type="password")
        if gemini_input: active_gemini_key = gemini_input
        elif "GEMINI_KEY" in st.secrets: active_gemini_key = st.secrets["GEMINI_KEY"]
            
    st.markdown("---")
    
    if EXA_AVAILABLE:
        st.success(f"✅ Exa Sniper: Active")
    else:
        st.error("❌ 'exa_py' Missing")

st.title("Be Holmes")
st.caption("EXA SNIPER EDITION | V12.0")
st.markdown("---")

user_news = st.text_area("Input Evidence...", height=100, label_visibility="collapsed", placeholder="e.g. Will Musk launch Starship soon?")
ignite_btn = st.button("🔍 EXA SEARCH", use_container_width=True)

if ignite_btn:
    if not user_news:
        st.warning("⚠️ Evidence required.")
    elif not active_gemini_key:
        st.error("⚠️ Gemini API Key required.")
    else:
        # 1. Exa Search
        with st.status("🎯 Exa Sniper Locking Target...", expanded=True) as status:
            st.write(f"Scanning polymarket.com via Exa.ai for '{user_news}'...")
            
            # 使用硬编码的 Key 进行搜索
            matches = search_with_exa(user_news)
            
            if matches:
                st.write(f"✅ Hit! Found {len(matches)} markets.")
            else:
                st.warning("⚠️ No markets found via Exa.")
            
            st.write("⚖️ Holmes Analyzing...")
            report = consult_holmes(user_news, matches, active_gemini_key)
            status.update(label="✅ Mission Complete", state="complete", expanded=False)

        # 2. Results
        if matches:
            st.markdown("### 🎯 Sniper Hits")
            for m in matches:
                st.markdown(f"""
                <div class="market-card">
                    <div style="font-size:1.1em; color:#E63946; font-weight:bold;">{m['title']}</div>
                    <div style="margin-top:5px; font-family:monospace;">
                        <span style="color:#FF4500;">⚡ {m['odds']}</span>
                        <span style="color:#666; margin-left:15px;">Vol: ${m['volume']:,.0f}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            # 按钮跳转
            slug = matches[0]['slug']
            link = f"https://polymarket.com/event/{slug}" 
            st.markdown(f"<a href='{link}' target='_blank'><button class='execute-btn'>🚀 EXECUTE TRADE</button></a>", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### 📝 Holmes' Verdict")
        st.info(report)
