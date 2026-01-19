import streamlit as st
import google.generativeai as genai
import time

# 尝试导入搜索库，如果用户没装，不仅不报错，还自动降级为“知识库模式”
try:
    from duckduckgo_search import DDGS
    SEARCH_AVAILABLE = True
except ImportError:
    SEARCH_AVAILABLE = False

# ================= 🕵️‍♂️ 1. 系统配置 =================
st.set_page_config(
    page_title="Be Holmes | Market Detective",
    page_icon="🕵️‍♂️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ================= 🎨 2. UI 设计 (强制黑字白底) =================
st.markdown("""
<style>
    /* 1. 暴力重置全局背景和文字颜色 */
    .stApp {
        background-color: #F8F9FA !important;
    }
    
    /* 强制所有层级的文字颜色为深灰/黑，覆盖系统深色模式设置 */
    h1, h2, h3, h4, h5, h6, p, div, span, label, li, .stMarkdown {
        color: #212529 !important;
    }

    /* 2. 侧边栏专门修复 */
    section[data-testid="stSidebar"] {
        background-color: #FFFFFF !important;
        border-right: 1px solid #E9ECEF;
    }
    section[data-testid="stSidebar"] * {
        color: #212529 !important;
    }

    /* 3. 输入框文字修复 */
    .stTextInput input {
        background-color: #FFFFFF !important;
        color: #212529 !important; /* 强制输入文字为黑 */
        border: 1px solid #CED4DA !important;
        border-radius: 8px;
    }
    .stTextInput label {
        color: #212529 !important;
    }
    
    /* 4. 标题特别强化 (品牌红) */
    h1 {
        color: #D62828 !important; 
        font-weight: 900 !important;
    }
    
    /* 5. 按钮样式 */
    .stButton button {
        background: linear-gradient(135deg, #D62828 0%, #C1121F 100%) !important;
        color: white !important; /* 按钮文字必须是白 */
        border: none;
        font-weight: bold;
    }
    .stButton button p {
        color: white !important; /* 确保按钮里的文字是白 */
    }
    
    /* 6. 报告卡片 */
    .report-card {
        background-color: white;
        padding: 30px;
        border-radius: 12px;
        border-left: 6px solid #D62828;
        box-shadow: 0 5px 15px rgba(0,0,0,0.08);
        margin-top: 20px;
        color: #333 !important;
    }
    
    /* 隐藏多余元素 */
    header {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ================= 🌐 3. 多语言字典 =================
LANG = {
    "CN": {
        "title": "Be Holmes",
        "subtitle": "海外发行情报侦探 | 竞品分析 & 舆情洞察",
        "sidebar_title": "侦探工具箱",
        "api_label": "Gemini API 密钥",
        "api_help": "必填，用于驱动 AI 大脑分析情报。",
        "input_label_1": "目标产品 / 竞品名称",
        "input_placeholder_1": "例如：原神 (Genshin Impact)",
        "input_label_2": "目标市场 / 国家",
        "input_placeholder_2": "例如：巴西 (Brazil)",
        "btn_start": "🔍 开始全网侦查",
        "btn_manual": "📘 使用手册",
        "status_searching": "正在全网搜集情报...",
        "status_analyzing": "Be Holmes 正在分析市场舆情...",
        "error_no_key": "❌ 请先在左侧输入 Gemini API Key",
        "error_no_input": "⚠️ 请输入完整的产品名和目标市场",
        "manual_title": "📘 使用手册",
        "manual_content": """
        ### 🕵️‍♂️ Be Holmes 是什么？
        这是一个专为**海外发行 PM** 打造的 AI 智能体。它模拟了一位资深市场分析师，能在 30 秒内帮你摸清竞品在海外的底细。
        
        ### 🚀 核心功能
        1. **舆情侦查：** 自动搜索 Reddit、Twitter、App Store 上的真实用户评价。
        2. **痛点挖掘：** 找出竞品在当地被吐槽最惨的地方（也就是你的机会）。
        3. **本地化分析：** 判断产品是否符合当地文化习俗。
        
        ### 🛠️ 如何使用
        1. 在左侧填入 API Key。
        2. 输入你想调研的**竞品**（如：Mobile Legends）。
        3. 输入**目标国家**（如：Indonesia）。
        4. 点击侦查，获取一份专业的全英文/全中文分析报告。
        """,
        "report_title": "📝 侦探档案：",
        "install_hint": "💡 提示：检测到未安装 duckduckgo-search，将使用 AI 知识库模式。建议 pip install duckduckgo-search 以开启联网能力。"
    },
    "EN": {
        "title": "Be Holmes",
        "subtitle": "Global Market Detective | Competitor Intelligence Agent",
        "sidebar_title": "Detective Toolkit",
        "api_label": "Gemini API Key",
        "api_help": "Required to power the AI reasoning engine.",
        "input_label_1": "Product / Competitor Name",
        "input_placeholder_1": "e.g. Genshin Impact",
        "input_label_2": "Target Market / Country",
        "input_placeholder_2": "e.g. Brazil",
        "btn_start": "🔍 Start Investigation",
        "btn_manual": "📘 User Manual",
        "status_searching": "Scouring the web for intelligence...",
        "status_analyzing": "Be Holmes is analyzing market sentiment...",
        "error_no_key": "❌ Please enter Gemini API Key in sidebar",
        "error_no_input": "⚠️ Please provide both Product Name and Market",
        "manual_title": "📘 User Manual",
        "manual_content": """
        ### 🕵️‍♂️ What is Be Holmes?
        An AI agent designed for **Overseas Publishing PMs**. It acts as a senior analyst, uncovering competitor insights in 30 seconds.
        
        ### 🚀 Core Features
        1. **Sentiment Recon:** Scans Reddit, Social Media, and Reviews.
        2. **Pain Point Detection:** Finds what local users hate about your competitor (your opportunity).
        3. **Localization Check:** Analyzes cultural fit and adaptation needs.
        
        ### 🛠️ How to Use
        1. Enter API Key on the left.
        2. Input **Competitor Name** (e.g., PUBG Mobile).
        3. Input **Target Country** (e.g., India).
        4. Click Investigate to get a professional strategy report.
        """,
        "report_title": "📝 Case File:",
        "install_hint": "💡 Note: Web search module missing. Running in Knowledge Mode. Run 'pip install duckduckgo-search' for live data."
    }
}

# ================= 🧠 4. 核心逻辑引擎 =================

def search_web_intelligence(product, market, lang_code):
    """
    搜索引擎：利用 DuckDuckGo 抓取实时网页快照
    """
    if not SEARCH_AVAILABLE:
        return None 
    
    results = []
    queries = [
        f"{product} {market} user reviews reddit",
        f"{product} {market} biggest complaints problems",
        f"{product} {market} marketing strategy analysis",
        f"{product} {market} local cultural adaptation"
    ]
    
    try:
        with DDGS() as ddgs:
            for q in queries:
                r = list(ddgs.text(q, max_results=2))
                if r:
                    for item in r:
                        results.append(f"- Source: {item['title']}\n  Snippet: {item['body']}")
                time.sleep(0.5) 
    except Exception as e:
        print(f"Search Error: {e}")
        return None
        
    return "\n".join(results)

def generate_agent_report(product, market, search_data, api_key, lang_mode):
    """
    AI 大脑：基于搜索结果生成专业报告
    """
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        output_lang = "Chinese (Professional Business Tone)" if lang_mode == "CN" else "English (Professional Business Tone)"
        
        context_prompt = ""
        if search_data:
            context_prompt = f"Here is the collected LIVE WEB INTELLIGENCE:\n{search_data}\n"
        else:
            context_prompt = "Note: Live search is unavailable. Use your internal knowledge base to analyze this product deeply."

        prompt = f"""
        Role: You are **Be Holmes**, a Senior Strategy Consultant for Tencent Games/Apps Overseas Publishing.
        
        Task: Analyze the competitor **'{product}'** in the **'{market}'** market.
        
        {context_prompt}
        
        **Objective:**
        Produce a strategic "Competitor Analysis Report" in **{output_lang}**.
        
        **Report Structure (Strictly follow this Markdown format):**
        
        ## 🕵️‍♂️ Executive Summary (一句话核心结论)
        [Summarize the product's status in this market in 2 sentences.]
        
        ---
        
        ### 1. 📉 User Pain Points (致命弱点 - 我们的机会)
        * [Point 1]: [Detail based on Reddit/Review sentiment]
        * [Point 2]: [Detail]
        * [Point 3]: [Detail]
        
        ### 2. ❤️ Why They Succeed (竞品优势)
        * [Analysis of their localization or marketing strength]
        
        ### 3. 🗺️ Cultural & Localization Insights (本地化洞察)
        * [Cultural Fit Analysis]
        * [Payment/Device/Network constraints in {market}]
        
        ### 4. 💡 Strategic Advice for Us (给发行团队的建议)
        > [Actionable advice for a PM entering this market. Be specific.]
        """
        
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"❌ Analysis Failed: {str(e)}"

# ================= 🖥️ 5. 主界面布局 =================

# --- 侧边栏 ---
with st.sidebar:
    lang_choice = st.radio("Language / 语言", ["CN", "EN"], horizontal=True)
    L = LANG[lang_choice] 
    
    st.markdown(f"## {L['sidebar_title']}")
    
    with st.expander(f"🔑 {L['api_label']}", expanded=True):
        st.caption(L['api_help'])
        user_api_key = st.text_input("Gemini Key", type="password")
        if not SEARCH_AVAILABLE:
            st.warning(L['install_hint'])
    
    st.markdown("---")
    st.markdown("### 🌟 About")
    st.caption("Powered by Gemini 2.5 & DuckDuckGo")
    st.caption("Designed for Global Publishing PMs")

# --- 主舞台 ---
c1, c2 = st.columns([3, 1])
with c1:
    st.title(L['title'])
    st.markdown(f"**{L['subtitle']}**")

with c2:
    if st.button(L['btn_manual']):
        @st.dialog(L['manual_title'])
        def show_manual():
            st.markdown(L['manual_content'])
        show_manual()

st.markdown("---")

# 输入表单
with st.container():
    col1, col2 = st.columns(2)
    with col1:
        product_name = st.text_input(L['input_label_1'], placeholder=L['input_placeholder_1'])
    with col2:
        target_market = st.text_input(L['input_label_2'], placeholder=L['input_placeholder_2'])

    start_btn = st.button(L['btn_start'], use_container_width=True)

if start_btn:
    if not user_api_key:
        st.error(L['error_no_key'])
    elif not product_name or not target_market:
        st.warning(L['error_no_input'])
    else:
        with st.status(L['status_searching'], expanded=True) as status:
            st.write(f"🌐 Scouring the web for: {product_name} + {target_market}...")
            
            search_results = search_web_intelligence(product_name, target_market, lang_choice)
            
            if search_results:
                st.success("✅ Intelligence Acquired from Web.")
            else:
                if not SEARCH_AVAILABLE:
                    st.info("⚡ Using AI Internal Knowledge (Fast Mode).")
                else:
                    st.warning("⚠️ Web search timed out, relying on AI memory.")
            
            st.write("🧠 Holmes is connecting the dots...")
            report = generate_agent_report(product_name, target_market, search_results, user_api_key, lang_choice)
            
            status.update(label="✅ Investigation Complete", state="complete", expanded=False)

        st.markdown(f"### {L['report_title']} {product_name} @ {target_market}")
        st.markdown(f"""<div class="report-card">{report}</div>""", unsafe_allow_html=True)
