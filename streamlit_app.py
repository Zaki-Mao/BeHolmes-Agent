import streamlit as st
import requests
import json
import google.generativeai as genai
import os

# ================= 🔧 1. 基础配置 =================
st.set_page_config(
    page_title="Project Prometheus",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 注入 CSS：黑客终端风格
st.markdown("""
<style>
    .stApp { background-color: #000000; font-family: 'Courier New', monospace; }
    [data-testid="stSidebar"] { background-color: #0a0a0a; border-right: 1px solid #333; }
    h1 { color: #FF4500 !important; text-shadow: 0 0 10px #FF4500; border-bottom: 2px solid #FF4500; padding-bottom: 10px;}
    p, label, .stMarkdown, .stText, li, div { color: #e0e0e0 !important; }
    strong { color: #FFD700 !important; } 
    .stTextArea textarea { background-color: #111; color: #FFD700; border: 1px solid #333; }
    div.stButton > button { background-color: #000; color: #FF4500; border: 1px solid #FF4500; font-weight: bold; }
    div.stButton > button:hover { background-color: #FF4500; color: #000; }
    a { color: #FFD700 !important; text-decoration: none; }
</style>
""", unsafe_allow_html=True)

# ================= 🔐 2. 安全层：静默加载密钥 =================
try:
    if "GEMINI_KEY" in st.secrets:
        api_key = st.secrets["GEMINI_KEY"]
    else:
        st.error("⚠️ SYSTEM ERROR: 密钥未配置 (Missing Secrets)")
        st.stop()
except Exception as e:
    st.error(f"⚠️ SYSTEM ERROR: {e}")
    st.stop()

# ================= 📡 3. 数据层：Polymarket 智能抓取 (V4.0 修正版) =================
@st.cache_data(ttl=300) 
def fetch_top_markets():
    """
    V4.0 修正逻辑: limit=100, 排除 closed, 修复 0.0%
    """
    url = "https://gamma-api.polymarket.com/events?limit=100&active=true&closed=false&sort=volume"
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
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

# ================= 🧠 4. 智能层：Gemini 2.5 操盘手引擎 (Pro Trader Mode) =================

def ignite_prometheus(user_news, market_list, key):
    try:
        genai.configure(api_key=key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        markets_text = "\n".join([f"- ID:{i} | {m['title']} (当前赔率: {m['price']})" for i, m in enumerate(market_list[:40])])
        
        # 🔥 PROMPT 核心重构：从“分析师”转变为“交易员”
        prompt = f"""
        角色设定: 你是 Prometheus，一个冷酷、以结果为导向的 Polymarket 资深交易员。你不需要讲宏观大道理，你只关心【赔率错配】和【短期爆发力】。
        
        任务目标: 分析【新闻情报】，从【市场列表】中寻找具有高盈亏比的交易机会。

        [实时市场列表]:
        {markets_text}

        [突发新闻情报]:
        "{user_news}"

        分析要求 (严格执行):
        1. **拒绝空话:** 不要说“利好行业”这种废话。必须给出新闻与具体合约之间的【硬逻辑】。如果关联度低，直接忽略。
        2. **时间维度:** 明确这是一个【短线消息面博弈】(News Spike) 还是 【长线基本面改变】(Fundamental Shift)。
        3. **出场策略:** 告诉用户什么时候卖。是“吃一波涨幅就跑”还是“拿到结果公布”。
        4. **只选最强:** 只输出 2-3 个最相关的市场。

        输出格式 (Markdown):
        ### [ID] 市场英文标题
        - **交易信号:** 🟢 买入 (Yes) / 🔴 卖出 (No) | **置信度:** [0-100%]
        - **核心逻辑:** (用中文，一针见血地指出为什么新闻会改变这个合约的概率。不要超过3句话。)
        - **交易计划:** - ⏳ **持仓周期:** [例如: 短线/24小时内 / 长线/直到年底]
            - 🎯 **离场条件:** [例如: 价格上涨 10% 即止盈 / 等待官方公告落地 / 纯粹的情绪炒作，快进快出]
        """
        
        response = model.generate_content(prompt)
        return response.text

    except Exception as e:
        return f"❌ AI Error: {str(e)}"

# ================= 🖥️ 5. 前端交互层 =================

with st.sidebar:
    st.markdown("## ⚙️ SYSTEM CONFIG")
    st.markdown("`CORE: GEMINI-2.5-FLASH`")
    st.success("🔒 Secure Key Loaded")
    
    st.markdown("---")
    st.markdown("### 🔥 Top Market Monitor")
    
    with st.spinner("Syncing Polymarket Data..."):
        top_markets = fetch_top_markets()
    
    if top_markets:
        st.info(f"已连接: 监控 {len(top_markets)} 个热门市场")
        for m in top_markets[:5]:
            st.caption(f"📈 {m['title']}")
            st.code(f"Price: {m['price']}")
    else:
        st.error("⚠️ Connection Failed")

st.title("PROMETHEUS PROTOCOL")
st.caption("THE EVENT-DRIVEN INTELLIGENCE ENGINE")
st.markdown("---")

col1, col2 = st.columns([3, 1])
with col1:
    st.markdown("### 📡 INTELLIGENCE INPUT")
    user_news = st.text_area("News", height=150, placeholder="输入情报... (例如: Kraken 宣布因收购案导致现金流紧张)", label_visibility="collapsed")

with col2:
    st.markdown("<br><br>", unsafe_allow_html=True)
    ignite_btn = st.button("🔥 IGNITE", use_container_width=True)

if ignite_btn:
    if not user_news:
        st.warning("⚠️ 请输入情报")
    elif not top_markets:
        st.error("⚠️ 数据流离线")
    else:
        with st.spinner(">> Analyzing Alpha..."):
            result = ignite_prometheus(user_news, top_markets, api_key)
            st.markdown("---")
            st.markdown(result)
            st.markdown("<br><a href='https://polymarket.com/' target='_blank'><button style='background:transparent;border:1px solid #FFD700;color:#FFD700;width:100%;padding:10px;'>🚀 EXECUTE</button></a>", unsafe_allow_html=True)
