import streamlit as st
import requests
import json
import google.generativeai as genai
import pandas as pd
import numpy as np

# ================= 🛠️ 0. 核心依赖检测 =================
try:
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity
    AI_SEARCH_AVAILABLE = True
except ImportError:
    AI_SEARCH_AVAILABLE = False

# ================= 🕵️‍♂️ 1. SYSTEM CONFIGURATION =================
st.set_page_config(
    page_title="Be Holmes | Neural Search",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 🔥 DOME KEY (虽然这次主要用本地计算，但Key留着备用)
DOME_API_KEY = "6f08669ca2c6a9541f0ef1c29e5928d2dc22857b"

# ================= 🎨 2. UI DESIGN (V1.0 CLASSIC RED/BLACK) =================
st.markdown("""
<style>
    /* 隐藏顶部和底部 */
    [data-testid="stToolbar"] { visibility: hidden; height: 0%; position: fixed; }
    footer { visibility: hidden; }
    header { visibility: hidden; }
    
    /* 全局黑底 */
    .stApp { background-color: #050505; font-family: 'Roboto Mono', monospace; }
    
    /* 侧边栏 */
    [data-testid="stSidebar"] { background-color: #000000; border-right: 1px solid #1a1a1a; }
    
    /* 标题红黑渐变 */
    h1 { 
        background: linear-gradient(90deg, #FF4500, #E63946); 
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        font-family: 'Georgia', serif; font-weight: 800;
        border-bottom: 2px solid #331111; padding-bottom: 15px;
    }
    
    /* 文字颜色 */
    h3, h4, label { color: #FF4500 !important; } 
    p, .stMarkdown, .stText, li, div, span { color: #A0A0A0 !important; }
    strong { color: #FFF !important; font-weight: 600; } 
    
    /* 输入框黑红风 */
    .stTextArea textarea, .stTextInput input { 
        background-color: #0A0A0A !important; color: #E63946 !important; 
        border: 1px solid #333 !important; border-radius: 6px;
    }
    .stTextInput input:focus { border-color: #FF4500 !important; }
    
    /* 按钮特效 */
    .execute-btn {
        background: linear-gradient(90deg, #FF4500, #8B0000); 
        border: none; color: white; width: 100%; padding: 15px;
        font-weight: 900; font-size: 16px; cursor: pointer; border-radius: 6px;
        text-transform: uppercase; letter-spacing: 2px; margin-top: 10px;
    }
    
    /* 市场卡片 */
    .market-card {
        background-color: #080808; border: 1px solid #222; border-left: 4px solid #FF4500;
        padding: 15px; margin: 10px 0; transition: all 0.3s;
    }
    .market-card:hover { border-color: #FF4500; box-shadow: 0 0 10px rgba(255, 69, 0, 0.2); }
    
    /* Streamlit 按钮覆盖 */
    .stButton button {
        background: linear-gradient(90deg, #FF4500, #B22222) !important;
        color: white !important;
        border: none !important;
    }
</style>
""", unsafe_allow_html=True)

# ================= 🧠 3. NEURAL ENGINE (本地向量大脑) =================

@st.cache_resource
def load_model():
    """Step 1: 加载 AI 模型 (只运行一次)"""
    if not AI_SEARCH_AVAILABLE: return None
    # 使用轻量级模型，下载约 80MB
    return SentenceTransformer('all-MiniLM-L6-v2')

@st.cache_data(ttl=3600)
def build_vector_index():
    """Step 2: 拉取全量市场并向量化 (每小时刷新一次)"""
    markets = []
    
    # 尝试拉取 Top 2000 活跃市场 (这基本上覆盖了所有有效赌局)
    # 使用 Gamma API，它比 Dome 更全
    url = "https://gamma-api.polymarket.com/markets"
    
    # 分页拉取或一次性拉取 (这里演示拉取 Top 1000 以保证速度)
    params = {"limit": 1000, "closed": "false", "sort": "volume"}
    
    try:
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            for m in data:
                title = m.get('question', '')
                if title:
                    # 解析赔率
                    odds_display = "N/A"
                    try:
                        outcomes = json.loads(m.get('outcomes', '[]')) if isinstance(m.get('outcomes'), str) else m.get('outcomes')
                        prices = json.loads(m.get('outcomePrices', '[]')) if isinstance(m.get('outcomePrices'), str) else m.get('outcomePrices')
                        if outcomes and prices:
                            odds_display = f"{outcomes[0]}: {float(prices[0])*100:.1f}%"
                    except: pass

                    markets.append({
                        "title": title,
                        "slug": m.get('market_slug', m.get('slug', '')),
                        "volume": float(m.get('volume', 0)),
                        "odds": odds_display,
                        "id": m.get('id')
                    })
    except Exception as e:
        print(f"Index Build Error: {e}")
    
    return pd.DataFrame(markets)

def neural_search(query, model, df, top_k=3):
    """Step 3: 向量相似度搜索"""
    if df.empty or not model: return []
    
    # 1. 向量化用户输入
    query_vec = model.encode([query])
    
    # 2. 向量化所有市场标题 (为了演示，这里实时计算，1000条数据其实很快)
    # *进阶: 生产环境应把 embeddings 存在 df 里缓存起来*
    if 'embedding' not in df.columns:
        df['embedding'] = list(model.encode(df['title'].tolist()))
    
    # 3. 计算余弦相似度
    # 将 list 转为 numpy array
    market_vecs = np.array(df['embedding'].tolist())
    similarities = cosine_similarity(query_vec, market_vecs)[0]
    
    # 4. 获取 Top K
    # 设定一个阈值，太不相关的不要 (比如 0.25)
    top_indices = np.argsort(similarities)[-top_k:][::-1]
    
    results = []
    for idx in top_indices:
        score = similarities[idx]
        if score > 0.3: # 语义相似度阈值
            row = df.iloc[idx]
            results.append({
                "title": row['title'],
                "slug": row['slug'],
                "odds": row['odds'],
                "volume": row['volume'],
                "score": score
            })
            
    return results

# ================= 🤖 4. AI ANALYST =================

def consult_holmes(user_input, market_data, key):
    try:
        genai.configure(api_key=key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        market_context = ""
        if market_data:
            m = market_data[0] # 取最匹配的一个
            market_context = f"Market: {m['title']} | Current Odds: {m['odds']} | Volume: ${m['volume']:,.0f}"
        else:
            market_context = "No direct prediction market found."
            
        prompt = f"""
        Role: **Be Holmes**, Alpha Hunter.
        
        User Input: "{user_input}"
        Semantic Match: {market_context}
        
        Task:
        1. **Semantic Connection:** If a market was found, explain *why* it matches the user's input (connect the dots).
        2. **Alpha Signal:** Based on the news/input, is the current market odds OVERVALUED or UNDERVALUED?
        3. **Verdict:** BUY / SELL / WAIT.
        
        Output in concise, professional Markdown.
        """
        return model.generate_content(prompt).text
    except Exception as e: return f"AI Analysis Error: {e}"

# ================= 🖥️ 5. MAIN INTERFACE =================

# --- 初始化资源 ---
if AI_SEARCH_AVAILABLE:
    with st.spinner("🧠 Initializing Neural Core (Loading Model & Indexing Markets)..."):
        model = load_model()
        market_index = build_vector_index()
else:
    st.error("⚠️ Library Missing. Please run: `pip install sentence-transformers scikit-learn`")
    model = None
    market_index = pd.DataFrame()

active_key = None

with st.sidebar:
    st.markdown("## 💼 DETECTIVE'S TOOLKIT")
    with st.expander("🔑 API Key Settings", expanded=True):
        user_api_key = st.text_input("Gemini Key", type="password")
        st.caption("✅ Engine: Local Vector Search")
        
        if not user_api_key and "GEMINI_KEY" in st.secrets:
            active_key = st.secrets["GEMINI_KEY"]
            st.success("🔒 System Key Loaded")
        elif user_api_key:
            active_key = user_api_key
            st.success("🔓 User Key Loaded")
    
    st.markdown("---")
    if not market_index.empty:
        st.success(f"📚 Indexed **{len(market_index)}** Active Markets")
    else:
        st.warning("⚠️ Index Empty (Check Network)")

# --- 主舞台 ---
st.title("Be Holmes")
st.caption("NEURAL SEARCH CORE | V8.0")
st.markdown("---")

user_news = st.text_area("Input Evidence / News...", height=100, label_visibility="collapsed", placeholder="Enter news, rumors, or vague ideas... (e.g. 'Elon's big rocket')")
ignite_btn = st.button("🔍 NEURAL INVESTIGATE", use_container_width=True)

if ignite_btn:
    if not user_news:
        st.warning("⚠️ Evidence required.")
    elif not active_key:
        st.error("⚠️ Please provide Gemini API Key.")
    else:
        # 1. 向量搜索
        with st.status("🧠 Neural Search Running...", expanded=True) as status:
            st.write("🌌 Vectorizing Query...")
            matches = neural_search(user_news, model, market_index)
            
            target_market = None
            if matches:
                target_market = matches[0]
                st.write(f"✅ **Semantic Match:** {target_market['title']} (Score: {target_market['score']:.2f})")
            else:
                st.warning("⚠️ No semantic match found in index.")
            
            st.write("⚖️ Calculating Alpha...")
            # 2. AI 分析
            report = consult_holmes(user_news, matches, active_key)
            status.update(label="✅ Investigation Complete", state="complete", expanded=False)

        # 3. 结果展示
        if matches:
            st.markdown("### 🎯 Top Semantic Matches")
            for m in matches:
                st.markdown(f"""
                <div class="market-card">
                    <div style="font-size:1.1em; font-weight:bold; color:#E63946;">{m['title']}</div>
                    <div style="display:flex; justify-content:space-between; margin-top:5px;">
                        <span style="color:#FF4500;">⚡ {m['odds']}</span>
                        <span style="color:#666;">Vol: ${m['volume']:,.0f}</span>
                        <span style="color:#888;">Similarity: {m['score']:.2f}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
            st.markdown(f"<a href='https://polymarket.com/market/{matches[0]['slug']}' target='_blank'><button class='execute-btn'>🚀 TRADE BEST MATCH</button></a>", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### 📝 Holmes' Verdict")
        st.info(report)
