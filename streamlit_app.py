import streamlit as st
import requests
import json
import google.generativeai as genai
import os

# ================= 🎨 2. 界面风格配置 (UI Config) =================
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
    p, label, .stMarkdown, .stText, li { color: #e0e0e0 !important; }
    strong { color: #FFD700 !important; } /* 加粗字体显示金黄色 */
    
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

# ================= 📡 3. 数据层：抓取 Polymarket 热门池 =================

@st.cache_data(ttl=300) # 缓存5分钟
def fetch_top_markets():
    """实时抓取 Polymarket 交易量最大的 Top 100 市场"""
    url = "https://gamma-api.polymarket.com/events?limit=100&active=true&closed=false&sort=volume"
    try:
        response = requests.get(url, timeout=10) # 增加超时限制
        if response.status_code == 200:
            data = response.json()
            markets_clean = []
            for event in data:
                title = event.get('title', 'Unknown')
                slug = event.get('slug', '')
                
                # 获取价格
                price_str = "N/A"
                markets = event.get('markets', [])
                if markets:
                    try:
                        if 'outcomePrices' in markets[0]:
                            prices = json.loads(markets[0]['outcomePrices'])
                            # 取第一个选项的价格 (通常是 Yes)
                            price_str = f"{float(prices[0]) * 100:.1f}%"
                    except: pass
                
                markets_clean.append({
                    "title": title,
                    "price": price_str,
                    "slug": slug
                })
            return markets_clean
        return []
    except Exception as e:
        return []

# ================= 🧠 4. 智能层：Gemini 2.5 语义推理引擎 =================

def ignite_prometheus(user_news, market_list, api_key):
    """调用 Google Gemini 2.5 进行中文逻辑推演"""
    if not api_key:
        return "❌ 错误: 请先在左侧输入 Google API Key"
    
    try:
        # 配置 API
        genai.configure(api_key=api_key)
        
        # 🔥 关键修改：锁定 gemini-2.5-flash 模型 (你账号里最强且免费的)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        # 准备数据给 AI
        markets_text = "\n".join([f"- ID:{i} | {m['title']} (当前价格: {m['price']})" for i, m in enumerate(market_list)])
        
        # 🔥 关键修改：System Prompt 强制中文输出
        prompt = f"""
        角色设定: 你是 Prometheus，一个精通全球宏观经济与 Polymarket 预测市场的顶级分析师。
        
        任务目标: 分析用户输入的【突发新闻】，从【市场列表】中找出最相关的交易机会，并用中文解释逻辑。
        
        [实时市场列表 (Top 100 流动性池)]:
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
        
        # 发送请求
        response = model.generate_content(prompt)
        return response.text

    except Exception as e:
        return f"❌ AI 连接失败: {str(e)}\n\n(提示: 请检查 API Key 是否正确，或尝试更新 google-generativeai 库)"

# ================= 🖥️ 5. 前端交互层 (Frontend) =================

# 侧边栏
with st.sidebar:
    st.markdown("## ⚙️ SYSTEM CONFIG")
    st.markdown("`CORE: GEMINI-2.5-FLASH`") # 显示当前核心
    st.markdown("`STATUS: ONLINE`")
    
    # Key 输入框
    api_key = st.text_input("💎 Google Gemini Key", type="password", placeholder="AIzaSy... (粘贴你的Key)")
    
    st.markdown("---")
    st.markdown("### 🔥 Top Market Monitor")
    
    with st.spinner("正在连接 Polymarket 数据流..."):
        top_markets = fetch_top_markets()
    
    if top_markets:
        st.success(f"已连接: 监控 {len(top_markets)} 个热门市场")
        st.markdown("---")
        # 滚动展示前3个市场
        for m in top_markets[:3]:
            st.caption(f"📈 {m['title']}")
            st.code(f"Price: {m['price']}")
    else:
        st.error("⚠️ 无法连接 Polymarket API (请检查梯子)")

# 主界面
st.title("PROMETHEUS PROTOCOL")
st.caption("THE EVENT-DRIVEN INTELLIGENCE ENGINE | 事件驱动型因果推演引擎")

st.markdown("---")

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
    # 按钮点击
    ignite_btn = st.button("🔥 IGNITE\n(开始推演)", use_container_width=True)

# 结果展示
if ignite_btn:
    if not user_news:
        st.warning("⚠️ 请先输入新闻情报！")
    elif not api_key:
        st.error("⚠️ 请在左侧侧边栏输入 Google API Key！")
    elif not top_markets:
        st.error("⚠️ 网络错误：无法获取市场列表，请检查代理设置。")
    else:
        with st.spinner(">> 正在进行因果链推演 (Powered by Gemini 2.5)..."):
            # 调用核心函数
            result = ignite_prometheus(user_news, top_markets, api_key)
            
            st.markdown("---")
            st.markdown("### 🎯 STRATEGIC OUTPUT (策略分析)")
            st.markdown(result)
            
            # 底部跳转按钮
            st.markdown("""
            <br>
            <a href="https://polymarket.com/" target="_blank">
                <button style="background:transparent; border:1px solid #FFD700; color:#FFD700; padding:12px; cursor:pointer; width:100%; font-family:monospace; font-weight:bold;">
                    🚀 EXECUTE ON POLYMARKET (前往交易)
                </button>
            </a>
            """, unsafe_allow_html=True)