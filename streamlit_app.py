import streamlit as st
import requests
import json
import google.generativeai as genai
import os

# ================= 🕵️‍♂️ 1. 基础配置 (侦探事务所风格) =================
st.set_page_config(
    page_title="Be Holmes | AI Market Detective",
    page_icon="🕵️‍♂️",  # 侦探图标
    layout="wide",
    initial_sidebar_state="expanded"
)

# 注入 CSS：英伦侦探暗黑风格 (Gold & Charcoal)
st.markdown("""
<style>
    /* 全局背景：深灰黑色，比纯黑更有质感 */
    .stApp { background-color: #0E1117; font-family: 'Roboto Mono', monospace; }
    
    /* 侧边栏：更深的灰 */
    [data-testid="stSidebar"] { background-color: #050505; border-right: 1px solid #333; }
    
    /* 标题 H1: 侦探金 */
    h1 { color: #D4AF37 !important; font-family: 'Georgia', serif; text-shadow: 0 0 5px #443300; border-bottom: 1px solid #D4AF37; padding-bottom: 15px;}
    
    /* 副标题 & 普通文本 */
    h3 { color: #E0C097 !important; }
    p, label, .stMarkdown, .stText, li, div { color: #B0B0B0 !important; }
    
    /* 强调文字 */
    strong { color: #FFF !important; font-weight: 600; } 
    
    /* 输入框 */
    .stTextArea textarea { background-color: #1A1A1A; color: #D4AF37; border: 1px solid #555; font-family: 'Courier New', monospace; }
    .stTextArea textarea:focus { border: 1px solid #D4AF37; box-shadow: 0 0 5px #D4AF37; }
    
    /* 按钮：金色边框，悬停变金 */
    div.stButton > button { 
        background-color: #000; 
        color: #D4AF37; 
        border: 1px solid #D4AF37; 
        font-weight: bold; 
        letter-spacing: 2px;
        transition: all 0.3s ease;
    }
    div.stButton > button:hover { 
        background-color: #D4AF37; 
        color: #000; 
        border-color: #FFF;
    }
    
    /* 代码块/数据展示 */
    .stCode { background-color: #111 !important; border-left: 3px solid #D4AF37; }
    
    /* 链接 */
    a { color: #D4AF37 !important; text-decoration: none; border-bottom: 1px dotted #D4AF37; }
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

# ================= 📡 3. 数据层：Polymarket (保持 V4.0 逻辑) =================
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

# ================= 🧠 4. 智能层：Be Holmes 深度推理引擎 (V3.0 Hardcore Mode) =================

def consult_holmes(user_evidence, market_list, key):
    try:
        genai.configure(api_key=key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        # 限制市场数量，确保 AI 聚焦
        markets_text = "\n".join([f"- ID:{i} | {m['title']} (Current Odds: {m['price']})" for i, m in enumerate(market_list[:40])])
        
        prompt = f"""
        Role: You are **Be Holmes**, a ruthless prediction market strategist. 
        You DO NOT write stories. You output **structured, actionable trading intelligence**.

        Task: Analyze the [Evidence] against the [Market List]. Find Alpha.

        [Evidence / Lead]:
        "{user_evidence}"

        [Market Data]:
        {markets_text}

        **LANGUAGE PROTOCOL (STRICT):**
        - If input is Chinese -> Output CHINESE.
        - If input is English -> Output ENGLISH.

        **ANALYSIS FRAMEWORK (The "Sherlock" Method):**
        For each relevant market, you must perform a "Causal Chain Analysis":
        1. **Signal Extraction:** What exactly is the news?
        2. **Transmission Mechanism:** How does this specific news affect the settlement criteria of the market?
        3. **Probability Calibration:** Why is the current market price wrong?

        **OUTPUT FORMAT (Markdown Cards):**
        Output 1 to 3 "Investigation Cards". Do not merge them. Do not add intro/outro text.

        ---
        ### 🕵️‍♂️ Case File: [Exact Market Title]
        
        **1. 📊 The Verdict (结论)**
        - **Action:** 🟢 BUY YES / 🔴 BUY NO / ⚠️ WATCH (Select one)
        - **Confidence Score:** [0-100%] (How sure are you?)
        - **Odds Delta:** Market [Current %] ➔ Target [Your Predicted %]
        
        **2. ⛓️ Causal Logic (深度逻辑链)**
        * **Step 1 (Fact):** [Briefly state the hard evidence]
        * **Step 2 (Inference):** [Explain the direct impact on the event's outcome]
        * **Step 3 (Conclusion):** [Why the market is mispriced right now]
        
        **3. ⏳ Execution Plan (交易计划)**
        - **Timeframe:** [Specific duration, e.g., "Intraday / 24 Hours" or "Hold until official filing"]
        - **Exit Condition:** [When to sell? e.g., "Take profit at 60%" or "Sell immediately if news is denied"]
        ---
        """
        
        response = model.generate_content(prompt)
        return response.text

    except Exception as e:
        return f"❌ Deduction Error: {str(e)}"
        
# ================= 🖥️ 5. 前端交互层 (UI Upgrade) =================

with st.sidebar:
    # 使用 Streamlit 专属 Logo (可选)
    # st.image("logo.png") 
    
    st.markdown("## 💼 DETECTIVE'S TOOLKIT")
    st.markdown("`ENGINE: GEMINI-2.5`")
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
st.caption("THE ART OF DEDUCTION FOR PREDICTION MARKETS") 
st.markdown("---")

col1, col2 = st.columns([3, 1])
with col1:
    st.markdown("### 📁 EVIDENCE LOCKER")
    # 输入框提示词
    user_news = st.text_area(
        "News", 
        height=150, 
        placeholder="Enter the news or rumor here... \n(Input English for English response, Chinese for Chinese response)", 
        label_visibility="collapsed"
    )

with col2:
    st.markdown("<br><br>", unsafe_allow_html=True)
    # 按钮文案变更
    ignite_btn = st.button("🔍 INVESTIGATE", use_container_width=True)

if ignite_btn:
    if not user_news:
        st.warning("⚠️ No evidence provided. I cannot make bricks without clay.")
    elif not top_markets:
        st.error("⚠️ Market data unavailable.")
    else:
        with st.spinner(">> Deducing outcomes..."):
            result = consult_holmes(user_news, top_markets, api_key)
            st.markdown("---")
            st.markdown("### 📝 INVESTIGATION REPORT")
            st.markdown(result)
            # 底部按钮链接
            st.markdown("<br><a href='https://polymarket.com/' target='_blank'><button style='background:transparent;border:1px solid #D4AF37;color:#D4AF37;width:100%;padding:10px;font-family:monospace;cursor:pointer;'>🚀 EXECUTE TRADE</button></a>", unsafe_allow_html=True)


