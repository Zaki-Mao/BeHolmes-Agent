import streamlit as st
import requests
import json
import google.generativeai as genai
import pandas as pd

# ================= 🕵️‍♂️ 1. SYSTEM CONFIGURATION =================
st.set_page_config(
    page_title="Be Holmes | Brute Force",
    page_icon="🕵️‍♂️",
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

# ================= 🧠 3. THE BRUTE FORCE ENGINE =================

@st.cache_data(ttl=600) # 缓存 10 分钟，避免每次点击都重新请求 API
def fetch_all_active_markets():
    """
    策略：直接拉取全网最热的 1000 个市场到内存里。
    不依赖搜索接口，依赖我们自己的 Python 过滤。
    """
    all_markets = []
    url = "https://gamma-api.polymarket.com/markets"
    
    # 抓取 Volume 最高的 1000 个市场（基本覆盖所有热点）
    params = {
        "limit": 1000, 
        "closed": "false", 
        "sort": "volume"
    }
    
    try:
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            for m in data:
                # 简单清洗
                title = m.get('question', '')
                if not title: continue
                
                # 赔率提取
                odds = "N/A"
                try:
                    outcomes = json.loads(m.get('outcomes', '[]')) if isinstance(m.get('outcomes'), str) else m.get('outcomes')
                    prices = json.loads(m.get('outcomePrices', '[]')) if isinstance(m.get('outcomePrices'), str) else m.get('outcomePrices')
                    if outcomes and prices:
                        odds = f"{outcomes[0]}: {float(prices[0])*100:.1f}%"
                except: pass

                all_markets.append({
                    "title": title,
                    "slug": m.get('market_slug', ''),
                    "volume": float(m.get('volume', 0)),
                    "odds": odds
                })
    except Exception as e:
        st.error(f"API Connection Error: {e}")
        
    return all_markets

def local_search(query, markets):
    """
    Python 本地字符串匹配搜索
    """
    query = query.lower().strip()
    results = []
    
    # 1. 标题精准包含
    for m in markets:
        if query in m['title'].lower():
            results.append(m)
            
    # 2. 如果没结果，尝试拆词匹配 (比如搜 "SpaceX IPO", 只要同时包含 "SpaceX" 和 "IPO")
    if not results:
        keywords = query.split()
        if len(keywords) > 1:
            for m in markets:
                if all(k in m['title'].lower() for k in keywords):
                    results.append(m)
    
    # 按成交量排序
    results.sort(key=lambda x: x['volume'], reverse=True)
    return results[:5] # 只返回前 5 个

# ================= 🤖 4. AI ANALYST =================

def consult_holmes(user_input, market_data, key):
    try:
        genai.configure(api_key=key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        market_context = ""
        if market_data:
            m = market_data[0]
            market_context = f"Found: {m['title']} | Odds: {m['odds']} | Vol: ${m['volume']:,.0f}"
        else:
            market_context = "No direct market found in Top 1000 liquidity pool."
            
        prompt = f"""
        Role: **Be Holmes**, Alpha Hunter.
        User Input: "{user_input}"
        Data Context: {market_context}
        
        Task:
        1. **Match Analysis:** How does the market data relate to the user's query?
        2. **Verdict:** Based on the news, is the market OVERVALUED or UNDERVALUED?
        3. **Strategy:** Buy Yes / Buy No / Wait.
        
        Output in concise Markdown.
        """
        return model.generate_content(prompt).text
    except Exception as e: return f"AI Error: {e}"

# ================= 🖥️ 5. MAIN INTERFACE =================

active_key = None

with st.sidebar:
    st.markdown("## 💼 DETECTIVE'S TOOLKIT")
    with st.expander("🔑 API Key Settings", expanded=True):
        user_api_key = st.text_input("Gemini Key", type="password")
        if user_api_key: active_key = user_api_key
        elif "GEMINI_KEY" in st.secrets: active_key = st.secrets["GEMINI_KEY"]
    
    st.markdown("---")
    
    # 预加载数据
    with st.spinner("🔄 Syncing with Polymarket Chain..."):
        market_db = fetch_all_active_markets()
    
    if market_db:
        st.success(f"✅ Synced **{len(market_db)}** Active Markets")
    else:
        st.error("⚠️ Sync Failed")

st.title("Be Holmes")
st.caption("BRUTE FORCE EDITION | V10.0")
st.markdown("---")

user_news = st.text_area("Input Evidence...", height=100, label_visibility="collapsed", placeholder="e.g. SpaceX")
ignite_btn = st.button("🔍 INVESTIGATE", use_container_width=True)

if ignite_btn:
    if not user_news:
        st.warning("⚠️ Input required.")
    elif not active_key:
        st.error("⚠️ API Key required.")
    else:
        # 1. 本地搜索
        with st.status("🧠 Scanning Memory Banks...", expanded=True) as status:
            st.write(f"Filtering {len(market_db)} markets for '{user_news}'...")
            matches = local_search(user_news, market_db)
            
            if matches:
                st.write(f"✅ Found {len(matches)} matches.")
            else:
                st.warning("⚠️ No matches in Top 1000 markets.")
            
            st.write("⚖️ Holmes Analyzing...")
            report = consult_holmes(user_news, matches, active_key)
            status.update(label="✅ Investigation Complete", state="complete", expanded=False)

        # 2. 结果展示
        if matches:
            st.markdown("### 🎯 Best Matches")
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
            
            slug = matches[0]['slug']
            st.markdown(f"<a href='https://polymarket.com/market/{slug}' target='_blank'><button class='execute-btn'>🚀 TRADE NOW</button></a>", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### 📝 Holmes' Verdict")
        st.info(report)
