import streamlit as st
import requests
import json
import google.generativeai as genai
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import time

# ================= 🕵️‍♂️ 1. SYSTEM CONFIGURATION =================
st.set_page_config(
    page_title="Be Holmes | Reasoning Console",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize Session State for Router
if 'mode' not in st.session_state:
    st.session_state.mode = 'Lobby'

# ================= 🎨 2. GLOBAL STYLES =================
st.markdown("""
<style>
    /* 全局深色背景 */
    .stApp { background-color: #0E1117; font-family: 'Inter', sans-serif; }
    
    /* 隐藏默认头部 */
    header, footer { visibility: hidden; }
    
    /* 标题样式 - 动态渐变 */
    h1 { 
        background: linear-gradient(90deg, #E2E2E2, #9CA3AF); 
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        font-weight: 800; letter-spacing: -1px;
    }
    
    /* 大厅卡片样式 */
    .mode-card {
        background: linear-gradient(145deg, #1F2937, #111827);
        border: 1px solid #374151;
        border-radius: 16px;
        padding: 30px;
        text-align: center;
        transition: all 0.3s ease;
        height: 220px;
        cursor: pointer;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
    }
    .mode-card:hover {
        transform: translateY(-8px);
        border-color: #60A5FA;
        box-shadow: 0 10px 30px rgba(0,0,0,0.5);
    }
    .card-icon { font-size: 3rem; margin-bottom: 15px; }
    .card-title { font-size: 1.2rem; font-weight: bold; color: white; margin-bottom: 10px; }
    .card-desc { font-size: 0.9rem; color: #9CA3AF; }
    
    /* 模式专属配色 */
    .theme-truth { border-left: 5px solid #3B82F6; }   /* Blue */
    .theme-macro { border-left: 5px solid #F59E0B; }   /* Amber */
    .theme-web3 { border-left: 5px solid #10B981; }    /* Emerald */
    .theme-life { border-left: 5px solid #EC4899; }    /* Pink */
    
    /* 按钮样式 */
    .stButton button {
        border-radius: 8px; font-weight: bold; width: 100%;
    }
</style>
""", unsafe_allow_html=True)

# ================= 🔐 3. SHARED UTILS =================
active_key = None

def get_gemini_response(prompt, key, model_name='gemini-2.5-flash'):
    if not key: return "⚠️ Please setup API Key."
    try:
        genai.configure(api_key=key)
        model = genai.GenerativeModel(model_name)
        return model.generate_content(prompt).text
    except Exception as e: return f"AI Error: {str(e)}"

# ================= 🚪 4. THE LOBBY (Router) =================
def render_lobby():
    st.markdown("<h1 style='text-align: center; margin-bottom: 10px;'>Be Holmes</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #666; margin-bottom: 50px;'>The Ultimate Reasoning Console</p>", unsafe_allow_html=True)
    
    c1, c2, c3, c4 = st.columns(4)
    
    with c1:
        st.markdown("""
        <div class="mode-card theme-truth">
            <div class="card-icon">🔎</div>
            <div class="card-title">Truth Lens</div>
            <div class="card-desc">Fact Check & Logic Forensics</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Enter Truth Mode"): st.session_state.mode = 'Truth'
            
    with c2:
        st.markdown("""
        <div class="mode-card theme-macro">
            <div class="card-icon">🦋</div>
            <div class="card-title">Butterfly Effect</div>
            <div class="card-desc">Macro News & 2nd Order Thinking</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Enter Macro Mode"): st.session_state.mode = 'Macro'

    with c3:
        st.markdown("""
        <div class="mode-card theme-web3">
            <div class="card-icon">👁️</div>
            <div class="card-title">PolySeer</div>
            <div class="card-desc">Crypto & Prediction Markets</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Enter Web3 Mode"): st.session_state.mode = 'Web3'

    with c4:
        st.markdown("""
        <div class="mode-card theme-life">
            <div class="card-icon">♟️</div>
            <div class="card-title">Life Strategy</div>
            <div class="card-desc">Game Theory & Career Decisions</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Enter Life Mode"): st.session_state.mode = 'Life'

# ================= 🔎 5. MODE A: TRUTH LENS =================
def render_truth_mode():
    st.markdown("## 🔎 Truth Lens: Logic Forensics")
    st.caption("Submit rumors, screenshots (OCR text), or arguments for logical dissection.")
    
    user_input = st.text_area("Evidence Input...", height=150, placeholder="Paste a rumor, a chat log, or a logical puzzle here...")
    
    if st.button("🔍 Analyze Veracity"):
        with st.spinner("Holmes is checking facts..."):
            prompt = f"""
            Role: **Sherlock Holmes (Logician)**.
            Task: Analyze the veracity and logic of the input.
            Input: "{user_input}"
            
            **Analysis Protocol:**
            1. **Fact Check:** Identify verifiable claims vs. opinions.
            2. **Logic Check:** Identify logical fallacies (Ad Hominem, Slippery Slope, etc.).
            3. **Source Analysis:** Evaluate potential bias.
            
            Output: A "Forensic Report" with a Truth Score (0-100%).
            """
            result = get_gemini_response(prompt, active_key)
            st.info(result)

# ================= 🦋 6. MODE B: BUTTERFLY EFFECT (Adj.News Style) =================
def render_macro_mode():
    st.markdown("## 🦋 Butterfly Effect: 2nd Order Thinking")
    st.caption("Input a news headline. Holmes will predict the ripple effects across the globe.")
    
    # 这里我们模拟 Adjacent News 的逻辑：新闻 -> 市场
    col1, col2 = st.columns([3, 1])
    with col1:
        news_input = st.text_input("News Headline", placeholder="e.g. Fed cuts interest rates by 50bps")
    with col2:
        sector = st.selectbox("Focus Sector", ["Global Markets", "Geopolitics", "Tech Industry", "Commodities"])
        
    if st.button("🦋 Simulate Ripples"):
        with st.spinner("Simulating global consequences..."):
            prompt = f"""
            Role: **Global Macro Strategist**.
            Task: Perform a 2nd and 3rd order effect analysis.
            News: "{news_input}"
            Focus: {sector}
            
            **Output Format:**
            1. **Direct Impact (First Order):** Immediate consequences.
            2. **Ripple Effect (Second Order):** Who reacts next? (e.g. Competitors, Supply Chain).
            3. **The Unseen (Third Order):** Long-term societal or structural shifts.
            4. **Black Swan Risk:** Low probability, high impact scenario.
            """
            result = get_gemini_response(prompt, active_key)
            st.warning(result)

# ================= 👁️ 7. MODE C: POLYSEER (Web3) =================
# 复刻之前的 V6.3 核心逻辑，精简版
def render_web3_mode():
    st.markdown("## 👁️ PolySeer: Prediction Markets")
    
    # 模拟数据函数 (复用之前的逻辑)
    def fetch_simulated_market(q):
        # 实际开发时这里换回 requests.get(gamma-api...)
        return {"title": f"{q} Prediction", "price": 0.45, "volume": 1200000}

    col1, col2 = st.columns([3, 1])
    with col1:
        query = st.text_input("Asset / Event", placeholder="e.g. Trump, BTC, SpaceX")
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        btn = st.button("🚀 Scan Alpha")

    if btn and query:
        with st.status("Scanning Liquidity Pools...", expanded=True):
            time.sleep(1)
            st.write("✅ Found Market Data")
            st.write("🧠 Applying Bayesian Update...")
            
            prompt = f"""
            Role: **PolySeer AI**.
            Task: Analyze prediction market alpha for '{query}'.
            Current Price: 0.45 (Implied Probability 45%).
            
            Output:
            1. **Market Mispricing:** Is the market overreacting?
            2. **Bayesian Signal:** Buy Yes/Buy No/Wait.
            """
            result = get_gemini_response(prompt, active_key)
            st.success("Complete")
            
        st.markdown(f"<div style='background:#111; padding:20px; border-left:4px solid #10B981;'>{result}</div>", unsafe_allow_html=True)

# ================= ♟️ 8. MODE D: LIFE STRATEGY =================
def render_life_mode():
    st.markdown("## ♟️ Life Strategy: The Consigliere")
    st.caption("Game Theory for your career and personal decisions.")
    
    dilemma = st.text_area("Your Dilemma...", height=100, placeholder="e.g. Should I join a Big Tech co or a Crypto Startup?")
    
    c1, c2 = st.columns(2)
    with c1:
        opt_a = st.text_input("Option A", placeholder="Big Tech")
    with c2:
        opt_b = st.text_input("Option B", placeholder="Crypto Startup")
        
    if st.button("⚖️ Run Game Theory Model"):
        with st.spinner("Calculating payoffs..."):
            prompt = f"""
            Role: **Game Theory Expert & Career Coach**.
            Dilemma: {dilemma}
            Option A: {opt_a}
            Option B: {opt_b}
            
            Task:
            1. **Payoff Matrix:** Compare Risk vs. Reward (Upside/Downside).
            2. **Regret Minimization:** Which option will you regret less in 5 years?
            3. **The Strategic Play:** Holmes' recommendation.
            """
            result = get_gemini_response(prompt, active_key)
            st.error(result)

# ================= 🎮 9. MAIN APP CONTROLLER =================

# Sidebar: Global Settings & Navigation
with st.sidebar:
    st.markdown("### 🎛️ Settings")
    
    # Return to Lobby
    if st.session_state.mode != 'Lobby':
        if st.button("⬅️ Back to Lobby"):
            st.session_state.mode = 'Lobby'
            st.rerun()
            
    st.markdown("---")
    with st.expander("🔑 API Key", expanded=True):
        key_input = st.text_input("Gemini Key", type="password", value=active_key if active_key else "")
        if key_input: active_key = key_input
    
    st.markdown("---")
    st.caption(f"Current Mode: **{st.session_state.mode}**")

# Router Logic
if st.session_state.mode == 'Lobby':
    render_lobby()
elif st.session_state.mode == 'Truth':
    render_truth_mode()
elif st.session_state.mode == 'Macro':
    render_macro_mode()
elif st.session_state.mode == 'Web3':
    render_web3_mode()
elif st.session_state.mode == 'Life':
    render_life_mode()
