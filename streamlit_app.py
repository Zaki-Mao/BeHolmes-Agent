import streamlit as st
import requests
import json
import google.generativeai as genai
import os

# ================= 🕵️‍♂️ 1. 基础配置 (Be Holmes 终极版) =================
st.set_page_config(
    page_title="Be Holmes | AI Market Detective",
    page_icon="🕵️‍♂️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 注入 CSS：英伦侦探暗黑风格 (Gold & Charcoal) - V4.0 UI 修复版
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
    
    /* 按钮样式优化 (Investigations 按钮) */
    div.stButton > button { 
        background-color: #000; color: #D4AF37; border: 1px solid #D4AF37; 
        transition: all 0.3s ease;
    }
    div.stButton > button:hover { 
        background-color: #D4AF37; color: #000; border-color: #D4AF37;
    }
    
    /* 去掉链接下划线 */
    a { text-decoration: none !important; border-bottom: none !important; }
    
    /* 底部执行按钮专属样式 (V4.0 新增) */
    .execute-btn {
        background: linear-gradient(45deg, #D4AF37, #FFD700); /* 渐变金 */
        border: none;
        color: #000; /* 黑色文字 */
        width: 100%;
        padding: 15px;
        font-weight: 800; /* 极粗 */
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

# ================= 📡 3. 数据层：Polymarket (V4.0 稳定版) =================
@st.cache_data(ttl=300) 
def fetch_top_markets():
    """
    获取 Polymarket 上的活跃市场数据
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

                best_market = None
                max_volume = -1
                
                for m in all_markets:
                    if m.get('closed') is True:
                        continue    
                    try:
                        vol = float(m.get('volume', 0))
                        if vol > max_volume:
                            max_volume = vol
                            best_market = m
                    except:
                        continue
                
                if not best_market:
                    best_market = all_markets[0]

                price_str = "N/A"
                try:
                    raw_prices = best_market.get('outcomePrices', [])
                    if isinstance(raw_prices, str):
                        prices = json.loads(raw_prices)
                    else:
                        prices = raw_prices
                    
                    if prices and len(prices) > 0:
                        val = float(prices[0])
                        if val == 0:
                            price_str = "0.0%" 
                        elif val < 0.01:
                            price_str = "<1%"
                        else:
                            price_str = f"{val * 100:.1f}%"
                except:
                    price_str = "N/A"
                
                markets_clean.append({
                    "title": title,
                    "price": price_str,
                    "slug": slug
                })
            return markets_clean
        return []
    except Exception as e:
        return []

# ================= 🧠 4. 智能层：Be Holmes 深度长文推理引擎 (V4.1 修复版) =================

def consult_holmes(user_evidence, market_list, key):
    try:
        genai.configure(api_key=key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        # 限制市场数量
        markets_text = "\n".join([f"- ID:{i} | {m['title']} (Current Odds: {m['price']})" for i, m in enumerate(market_list[:40])])
        
        prompt = f"""
        Role: You are **Be Holmes**, a legendary prediction market detective. 
        Your clients pay you for **deep, comprehensive, and exhaustive analysis**, not quick summaries.
        You must write detailed logical deductions that reveal the "Why" behind the probability.

        Task: Analyze the [Evidence] against the [Market List] to find Alpha.

        [Evidence]: "{user_evidence}"
        [Market Data]: {markets_text}

        **LANGUAGE PROTOCOL:**
        - Input Chinese -> Output CHINESE (Traditional/Simplified based on input).
        - Input English -> Output ENGLISH.

        **ANALYSIS REQUIREMENTS (DEEP DIVE):**
        1. **Go Deep:** Do not be brief. For the "Logic" section, write a comprehensive paragraph (approx 100-150 words) explaining the causal chain.
        2. **Connect the Dots:** Explicitly link the specific keywords in the news to the specific settlement rules of the market.
        3. **No Footer:** Do not output any conversational text like "My investigation found..." at the end. Only output the Cards.

        **OUTPUT FORMAT (Markdown Cards):**

        ---
        ### 🕵️‍♂️ Case File: [Exact Market Title]
        
        **1. 📊 The Verdict (结论)**
        - **Signal:** 🟢 STRONG BUY / 🔴 STRONG SELL / ⚠️ WAIT
        - **Confidence:** **[0-100]%** (Explain briefly why)
        - **Odds Gap:** Market [Current %] ➔ Target [Your Predicted %]
        
        **2. ⛓️ The Deduction (深度逻辑链)**
        > *[Mandatory: Write a detailed analytical paragraph here. Start with the raw evidence, then explain the transmission mechanism (how this affects voter/market psychology), and finally conclude why the current price is wrong. Be thorough and professional.]*
        
        **3. ⏳ Execution (执行计划)**
        - **Timeframe:** [e.g., "Hold for 48h" / "Long term until Q3"]
        - **Exit Strategy:** [e.g., "Sell if odds hit 60%" or "Stop loss if official denial is issued"]
        ---
        """
        
        response = model.generate_content(prompt)
        
        # 修复：移除所有缩进，确保顶格书写，防止被识别为代码块
        btn_html = """
<br>
<a href='https://polymarket.com/' target='_blank' style='text-decoration:none;'>
<button class='execute-btn'>🚀 EXECUTE TRADE ON POLYMARKET</button>
</a>
"""
        return response.text + btn_html

    except Exception as e:
        return f"❌ Deduction Error: {str(e)}"

# ================= 🖥️ 5. 前端交互层 (UI V4.0) =================

with st.sidebar:
    # 侧边栏
    st.markdown("## 💼 DETECTIVE'S TOOLKIT")
    st.markdown("`ENGINE: GEMINI-2.5-FLASH`")
    st.success("🔒 Authorization: Granted")
    
    st.markdown("---")
    st.markdown("### 🔍 Market Surveillance")
    
    with st.spinner("Gathering intel..."):
        top_markets = fetch_top_markets()
    
    if top_markets:
        st.info(f"Monitoring {len(top_markets)} Active Cases")
        for m in top_markets[:5]:
            st.caption(f"📅 {m['title']}")
            st.code(f"Odds: {m['price']}")
    else:
        st.error("⚠️ Network Glitch: Data Unavailable")

# 主标题区
st.title("🕵️‍♂️ Be Holmes")
st.caption("THE ART OF DEDUCTION FOR PREDICTION MARKETS | DEEP CAUSAL INFERENCE") 
st.markdown("---")

col1, col2 = st.columns([3, 1])
with col1:
    st.markdown("### 📁 EVIDENCE LOCKER")
    # 输入框
    user_news = st.text_area(
        "News", 
        height=150, 
        placeholder="Enter evidence here... \n(Input English -> English Report | Input Chinese -> Chinese Report)", 
        label_visibility="collapsed"
    )

with col2:
    st.markdown("<br><br>", unsafe_allow_html=True)
    # 调查按钮
    ignite_btn = st.button("🔍 INVESTIGATE", use_container_width=True)

if ignite_btn:
    if not user_news:
        st.warning("⚠️ No evidence provided. I cannot make bricks without clay.")
    elif not top_markets:
        st.error("⚠️ Market data unavailable.")
    else:
        with st.spinner(">> Deducing outcomes... (Deep Analysis)"):
            result = consult_holmes(user_news, top_markets, api_key)
            st.markdown("---")
            st.markdown("### 📝 INVESTIGATION REPORT")
            # 渲染结果（允许 HTML 以显示自定义按钮）
            st.markdown(result, unsafe_allow_html=True)

