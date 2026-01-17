import streamlit as st
import requests
import json
import google.generativeai as genai
import os

# ================= 🕵️‍♂️ 1. 基础配置 (Be Holmes V5.0) =================
st.set_page_config(
    page_title="Be Holmes | AI Market Detective",
    page_icon="🕵️‍♂️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 注入 CSS：英伦侦探暗黑风格 (Gold & Charcoal)
st.markdown("""
<style>
    /* 全局背景 */
    .stApp { background-color: #0E1117; font-family: 'Roboto Mono', monospace; }
    
    /* 侧边栏 */
    [data-testid="stSidebar"] { background-color: #050505; border-right: 1px solid #333; }
    
    /* 标题 H1 */
    h1 { color: #D4AF37 !important; font-family: 'Georgia', serif; text-shadow: 0 0 5px #443300; border-bottom: 1px solid #D4AF37; padding-bottom: 15px;}
    
    /* 副标题 & 文本 */
    h3 { color: #E0C097 !important; }
    p, label, .stMarkdown, .stText, li, div { color: #B0B0B0 !important; }
    strong { color: #FFF !important; font-weight: 600; } 
    
    /* 输入框优化 */
    .stTextArea textarea { background-color: #151515; color: #D4AF37; border: 1px solid #444; }
    .stTextArea textarea:focus { border: 1px solid #D4AF37; box-shadow: 0 0 10px rgba(212, 175, 55, 0.2); }
    
    /* 按钮样式优化 */
    div.stButton > button { 
        background-color: #000; color: #D4AF37; border: 1px solid #D4AF37; 
        transition: all 0.3s ease;
    }
    div.stButton > button:hover { 
        background-color: #D4AF37; color: #000; border-color: #D4AF37;
    }
    
    /* 去掉链接下划线 */
    a { text-decoration: none !important; border-bottom: none !important; }
    
    /* 底部执行按钮专属样式 */
    .execute-btn {
        background: linear-gradient(45deg, #D4AF37, #FFD700);
        border: none;
        color: #000;
        width: 100%;
        padding: 15px;
        font-weight: 800;
        font-size: 16px;
        cursor: pointer;
        border-radius: 4px;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        box-shadow: 0 4px 15px rgba(212, 175, 55, 0.3);
        margin-top: 20px;
    }
    .execute-btn:hover { 
        transform: translateY(-2px); 
        box-shadow: 0 6px 20px rgba(212, 175, 55, 0.6); 
    }
</style>
""", unsafe_allow_html=True)

# ================= 🔐 2. 安全层 =================
try:
    if "GEMINI_KEY" in st.secrets:
        api_key = st.secrets["GEMINI_KEY"]
    else:
        st.error("⚠️ MISSING KEY: The detective cannot work without his tools.")
        st.stop()
except Exception as e:
    st.error(f"⚠️ SYSTEM ERROR: {e}")
    st.stop()

# ================= 📡 3. 数据层：Polymarket (V5.0 双边赔率增强版) =================
@st.cache_data(ttl=300) 
def fetch_top_markets():
    """
    获取 Polymarket 数据，并解析出完整的 Yes/No 赔率
    """
    url = "https://gamma-api.polymarket.com/events?limit=100&active=true&closed=false&sort=volume"
    try:
        headers = {
            "User-Agent": "BeHolmes-Agent/1.0"
        }
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            markets_clean = []
            
            for event in data:
                title = event.get('title', 'Unknown')
                slug = event.get('slug', '')
                all_markets = event.get('markets', [])
                
                if not all_markets:
                    continue

                # 找到成交量最大的 Market
                best_market = None
                max_volume = -1
                for m in all_markets:
                    if m.get('closed') is True: continue    
                    try:
                        vol = float(m.get('volume', 0))
                        if vol > max_volume:
                            max_volume = vol
                            best_market = m
                    except: continue
                
                if not best_market: best_market = all_markets[0]

                # === V5.0 新增: 解析所有结果的赔率 (Yes/No) ===
                odds_display = "N/A"
                try:
                    # 获取结果名称 (如 ["Yes", "No"])
                    raw_outcomes = best_market.get('outcomes', '["Yes", "No"]')
                    outcomes = json.loads(raw_outcomes) if isinstance(raw_outcomes, str) else raw_outcomes
                    
                    # 获取结果价格 (如 ["0.22", "0.78"])
                    raw_prices = best_market.get('outcomePrices', '[]')
                    prices = json.loads(raw_prices) if isinstance(raw_prices, str) else raw_prices

                    # 拼接成字符串 "Yes: 22.0% | No: 78.0%"
                    odds_list = []
                    if prices and len(prices) == len(outcomes):
                        for o, p in zip(outcomes, prices):
                            val = float(p) * 100
                            odds_list.append(f"{o}: {val:.1f}%")
                        odds_display = " | ".join(odds_list)
                    else:
                        # 兜底逻辑
                        val = float(prices[0]) * 100
                        odds_display = f"Price: {val:.1f}%"
                except:
                    odds_display = "Odds Unavailable"
                
                markets_clean.append({
                    "title": title,
                    "odds": odds_display, # 这里存的是详细的 "Yes: xx | No: xx"
                    "slug": slug
                })
            return markets_clean
        return []
    except Exception as e:
        return []

# ================= 🧠 4. 智能层：Be Holmes 深度推理引擎 (V5.1 LED Ticker Style) =================

def consult_holmes(user_evidence, market_list, key):
    try:
        genai.configure(api_key=key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        # 将详细的赔率数据传给 AI
        markets_text = "\n".join([f"- ID:{i} | {m['title']} [Live Odds: {m['odds']}]" for i, m in enumerate(market_list[:40])])
        
        prompt = f"""
        Role: You are **Be Holmes**, a legendary prediction market detective. 
        
        Task: Analyze the [Evidence] against the [Market List].

        [Evidence]: "{user_evidence}"
        [Market Data]: {markets_text}

        **LANGUAGE PROTOCOL:**
        - Input Chinese -> Output CHINESE report.
        - Input English -> Output ENGLISH report.

        **OUTPUT FORMAT (Markdown + HTML):**
        
        You must structure the output strictly as follows. 
        For the "Market Ticker", just provide the raw odds string, I will format it.

        ---
        ### 🕵️‍♂️ Case File: [Exact Market Title]
        
        <div class="ticker-box">
        📡 SNAPSHOT: [Insert Odds Here, e.g., Yes: 22.5% | No: 77.5%]
        </div>
        
        **1. ⚖️ The Verdict (结论)**
        - **Signal:** 🟢 STRONG BUY / 🔴 STRONG SELL / ⚠️ WATCH
        - **Confidence:** **[0-100]%**
        - **Target:** Market [Current %] ➔ I Predict [Target %]
        
        **2. ⛓️ The Deduction (深度逻辑链)**
        > *[Mandatory: Detailed analysis paragraph (100+ words). Explain the causal chain clearly.]*
        
        **3. ⏳ Execution (执行计划)**
        - **Timeframe:** [Duration]
        - **Exit:** [Condition]
        ---
        """
        
        response = model.generate_content(prompt)
        
        # 注入 LED 样式和 底部按钮
        # 这里的 CSS .ticker-box 就是控制那个框样子的
        custom_html = """
<style>
.ticker-box {
    background-color: #000;
    border: 1px solid #333;
    border-left: 5px solid #D4AF37; /* 金色左边框 */
    color: #00FF00; /* 骇客绿数字 */
    font-family: 'Courier New', monospace;
    padding: 15px;
    margin: 10px 0;
    font-size: 1.1em;
    font-weight: bold;
    box-shadow: 0 0 10px rgba(0, 255, 0, 0.1);
    letter-spacing: 1px;
}
</style>

<br>
<a href='https://polymarket.com/' target='_blank' style='text-decoration:none;'>
<button class='execute-btn'>🚀 EXECUTE TRADE ON POLYMARKET</button>
</a>
"""
        return response.text + custom_html

    except Exception as e:
        return f"❌ Deduction Error: {str(e)}"

# ================= 🖥️ 5. 前端交互层 (UI V5.0) =================

with st.sidebar:
    st.markdown("## 💼 DETECTIVE'S TOOLKIT")
    st.markdown("`ENGINE: GEMINI-2.5-FLASH`")
    st.success("🔒 Authorization: Granted")
    
    st.markdown("---")
    st.markdown("### 🔍 Market Surveillance")
    
    with st.spinner("Scanning real-time tickers..."):
        top_markets = fetch_top_markets()
    
    if top_markets:
        st.info(f"Monitoring {len(top_markets)} Active Cases")
        for m in top_markets[:5]:
            st.caption(f"📅 {m['title']}")
            st.code(f"{m['odds']}") # 侧边栏也显示详细赔率
    else:
        st.error("⚠️ Network Glitch: Data Unavailable")

# 主标题区
st.title("🕵️‍♂️ Be Holmes")
st.caption("THE ART OF DEDUCTION FOR PREDICTION MARKETS | DEEP CAUSAL INFERENCE") 
st.markdown("---")

col1, col2 = st.columns([3, 1])
with col1:
    st.markdown("### 📁 EVIDENCE LOCKER")
    user_news = st.text_area(
        "News", 
        height=150, 
        placeholder="Enter evidence here... \n(Input English -> English Report | Input Chinese -> Chinese Report)", 
        label_visibility="collapsed"
    )

with col2:
    st.markdown("<br><br>", unsafe_allow_html=True)
    ignite_btn = st.button("🔍 INVESTIGATE", use_container_width=True)

if ignite_btn:
    if not user_news:
        st.warning("⚠️ No evidence provided. I cannot make bricks without clay.")
    elif not top_markets:
        st.error("⚠️ Market data unavailable.")
    else:
        with st.spinner(">> Analyzing real-time odds & causality..."):
            result = consult_holmes(user_news, top_markets, api_key)
            st.markdown("---")
            st.markdown("### 📝 INVESTIGATION REPORT")
            st.markdown(result, unsafe_allow_html=True)


