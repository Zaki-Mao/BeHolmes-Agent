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

# 注入 CSS：黑客终端风格 (Black & Orange Theme)
st.markdown("""
<style>
    /* 全局深色背景 */
    .stApp { background-color: #000000; font-family: 'Courier New', monospace; }
    
    /* 侧边栏 */
    [data-testid="stSidebar"] { background-color: #0a0a0a; border-right: 1px solid #333; }
    
    /* 标题火焰特效 */
    h1 { 
        color: #FF4500 !important; 
        text-shadow: 0 0 10px #FF4500, 0 0 20px #8B0000; 
        border-bottom: 2px solid #FF4500; 
        padding-bottom: 10px;
    }
    
    /* 文本通用颜色 */
    p, label, .stMarkdown, .stText, li, div { color: #e0e0e0 !important; }
    strong { color: #FFD700 !important; } 
    
    /* 输入框样式 */
    .stTextArea textarea { background-color: #111; color: #FFD700; border: 1px solid #333; }
    .stTextArea textarea:focus { border-color: #FF4500; box-shadow: 0 0 10px #FF4500; }
    
    /* 按钮样式 */
    div.stButton > button { 
        background-color: #000; 
        color: #FF4500; 
        border: 1px solid #FF4500; 
        font-weight: bold;
        transition: all 0.3s;
        font-size: 18px;
    }
    div.stButton > button:hover { 
        background-color: #FF4500; 
        color: #000; 
        box-shadow: 0 0 20px #FF4500; 
    }
    
    /* 链接样式 */
    a { color: #FFD700 !important; text-decoration: none; }
</style>
""", unsafe_allow_html=True)

# ================= 🔐 2. 安全层：静默加载密钥 =================

# 尝试从 Secrets 读取 Key
try:
    if "GEMINI_KEY" in st.secrets:
        api_key = st.secrets["GEMINI_KEY"]
    else:
        # 如果本地运行没有 secrets，可以取消下面注释临时用，但不要上传 GitHub
        # api_key = "AIzaSy_你的本地测试Key" 
        st.error("⚠️ SYSTEM ERROR: 密钥未配置 (Missing Secrets)")
        st.stop()
except Exception as e:
    st.error(f"⚠️ SYSTEM ERROR: {e}")
    st.stop()

# ================= 📡 3. 数据层：抓取 Polymarket (修复版) =================

@st.cache_data(ttl=300) # 缓存5分钟，避免频繁请求
def fetch_top_markets():
    """优化版：按流动性抓取，并修复价格显示问题"""
    # 使用 sort=liquidity 确保抓取到的是真正热门、价格有效的市场
    url = "https://gamma-api.polymarket.com/events?limit=20&active=true&closed=false&sort=liquidity"
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
                markets = event.get('markets', [])
                
                # 价格获取逻辑优化
                price_str = "N/A"
                if markets:
                    main_market = markets[0]
                    try:
                        if 'outcomePrices' in main_market:
                            prices = json.loads(main_market['outcomePrices'])
                            # 获取 "Yes" 的价格
                            raw_price = float(prices[0])
                            
                            # 格式化显示：避免出现 0.0%
                            if raw_price < 0.01 and raw_price > 0:
                                price_str = f"{raw_price * 100:.2f}%" 
                            else:
                                price_str = f"{raw_price * 100:.1f}%"
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

# ================= 🧠 4. 智能层：Gemini 2.5 引擎 =================

def ignite_prometheus(user_news, market_list, key):
    """调用 Google Gemini 2.5 进行中文逻辑推演"""
    try:
        genai.configure(api_key=key)
        
        # 锁定 gemini-2.5-flash (免费且最快)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        # 准备数据
        markets_text = "\n".join([f"- ID:{i} | {m['title']} (当前价格: {m['price']})" for i, m in enumerate(market_list)])
        
        # System Prompt (强制中文逻辑)
        prompt = f"""
        角色设定: 你是 Prometheus，一个精通全球宏观经济与 Polymarket 预测市场的顶级分析师。
        
        任务目标: 分析用户输入的【突发新闻】，从【市场列表】中找出最相关的交易机会，并用中文解释逻辑。
        
        [实时市场列表 (Top 20 流动性池)]:
        {markets_text}

        [用户输入的新闻情报]:
        "{user_news}"

        分析指令:
        1. 像华尔街交易员一样思考，寻找新闻背后的二阶效应 (Second-order effects)。
        2. 必须从 [实时市场列表] 中挑选 3 个受影响最大的市场。
        3. 进行语义联想 (例如: "显卡推迟" -> 影响 "OpenAI 模型发布"; "拜登失误" -> 影响 "民主党提名人")。
        4. 给出明确的交易方向建议。

        输出格式 (必须严格遵守 Markdown 格式):
        ### [Market ID] 市场英文标题
        - **交易信号:** 🟢 [买入/做多] 或 🔴 [卖出/做空] (Target Outcome)
        - **逻辑推演:** (这里必须用中文！简练、深刻地解释为什么这个新闻会影响该市场的赔率。不要废话，直击因果。)
        """
        
        response = model.generate_content(prompt)
        return response.text

    except Exception as e:
        return f"❌ AI 连接失败: {str(e)}\n\n(提示: 请检查 API Key 配额或网络状态)"

# ================= 🖥️ 5. 前端交互层 (Frontend) =================

# 侧边栏 (极简模式：无输入框)
with st.sidebar:
    st.markdown("## ⚙️ SYSTEM CONFIG")
    st.markdown("`CORE: GEMINI-2.5-FLASH`")
    st.markdown("`STATUS: ONLINE`")
    
    # 这里不再显示 API Key 输入框，直接显示连接状态
    st.success("🔒 安全连接已建立 (Secure Key Loaded)")
    
    st.markdown("---")
    st.markdown("### 🔥 Top Market Monitor")
    
    with st.spinner("正在同步 Polymarket 数据..."):
        top_markets = fetch_top_markets()
    
    if top_markets:
        st.info(f"已连接: 监控 {len(top_markets)} 个高流动性市场")
        st.markdown("---")
        # 滚动展示前3个市场
        for m in top_markets[:3]:
            st.caption(f"📈 {m['title']}")
            st.code(f"Price: {m['price']}")
    else:
        st.error("⚠️ 无法连接 Polymarket API")

# 主界面
st.title("PROMETHEUS PROTOCOL")
st.caption("THE EVENT-DRIVEN INTELLIGENCE ENGINE | 事件驱动型因果推演引擎")

st.markdown("---")

# 布局
col1, col2 = st.columns([3, 1])

with col1:
    st.markdown("### 📡 INTELLIGENCE INPUT (情报输入)")
    user_news = st.text_area(
        "News Input", 
        height=150, 
        placeholder="在此粘贴突发新闻、推特消息或假设情景...\n支持中文/英文输入。\n例如：'突发：OpenAI 宣布 GPT-5 因安全问题推迟发布'", 
        label_visibility="collapsed"
    )

with col2:
    st.markdown("<br><br>", unsafe_allow_html=True)
    ignite_btn = st.button("🔥 IGNITE\n(开始推演)", use_container_width=True)

# 结果展示
if ignite_btn:
    if not user_news:
        st.warning("⚠️ 请先输入新闻情报！")
    elif not top_markets:
        st.error("⚠️ 市场数据获取失败，请稍后重试。")
    else:
        with st.spinner(">> 正在进行因果链推演 (Powered by Gemini 2.5)..."):
            # 直接使用全局变量 api_key
            result = ignite_prometheus(user_news, top_markets, api_key)
            
            st.markdown("---")
            st.markdown("### 🎯 STRATEGIC OUTPUT (策略分析)")
            st.markdown(result)
            
            # 底部跳转
            st.markdown("""
            <br>
            <a href="https://polymarket.com/" target="_blank">
                <button style="background:transparent; border:1px solid #FFD700; color:#FFD700; padding:12px; cursor:pointer; width:100%; font-family:monospace; font-weight:bold;">
                    🚀 EXECUTE ON POLYMARKET (前往交易)
                </button>
            </a>
            """, unsafe_allow_html=True)
