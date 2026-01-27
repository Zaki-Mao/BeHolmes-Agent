import streamlit as st
import requests
import json
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import re
import time
import datetime
import feedparser
import urllib.parse
import html

# ================= 🔐 0. KEY MANAGEMENT =================
try:
    EXA_API_KEY = st.secrets.get("EXA_API_KEY", None)
    GOOGLE_API_KEY = st.secrets.get("GOOGLE_API_KEY", None)
    NEWS_API_KEY = st.secrets.get("NEWS_API_KEY", None)
    KEYS_LOADED = True
except:
    EXA_API_KEY = None
    GOOGLE_API_KEY = None
    NEWS_API_KEY = None
    KEYS_LOADED = False

if GOOGLE_API_KEY:
    try:
        genai.configure(api_key=GOOGLE_API_KEY)
        GEMINI_AVAILABLE = True
    except:
        GEMINI_AVAILABLE = False
else:
    GEMINI_AVAILABLE = False

# ================= 🕵️‍♂️ 1. SYSTEM CONFIGURATION =================
st.set_page_config(
    page_title="Be Holmes | Reality Check",
    page_icon="🕵️‍♂️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ================= 🧠 1.1 STATE MANAGEMENT =================
if "news_category" not in st.session_state:
    st.session_state.news_category = "All"
if "messages" not in st.session_state:
    st.session_state.messages = []
if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None

# ================= 🎨 2. UI THEME (修复乱码) =================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;900&family=JetBrains+Mono:wght@400;700&display=swap');

    /* Global Background */
    .stApp {
        background-image: linear-gradient(rgba(0, 0, 0, 0.92), rgba(20, 0, 0, 0.98));
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
        font-family: 'Inter', sans-serif;
        color: white;
    }
    
    /* Headers */
    .hero-title {
        font-family: 'Inter', sans-serif;
        font-weight: 800;
        font-size: 3rem; 
        color: #ffffff;
        text-align: center;
        letter-spacing: -2px;
        text-shadow: 0 0 40px rgba(220, 38, 38, 0.8);
        margin-top: 20px;
    }
    
    .hero-subtitle {
        text-align: center;
        color: #9ca3af;
        font-size: 1rem;
        margin-bottom: 30px;
        letter-spacing: 3px;
    }
    
    .section-header {
        font-size: 0.85rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        margin-bottom: 15px;
        padding-bottom: 8px;
        border-bottom: 1px solid rgba(220, 38, 38, 0.3);
        display: flex;
        align-items: center;
        gap: 8px;
        color: #ef4444;
    }

    /* 🔥 Google Trends Tags (Gradient) */
    .trend-container {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
        margin-bottom: 20px;
    }
    
    .trend-tag {
        padding: 5px 12px;
        border-radius: 4px;
        font-size: 0.8rem;
        font-weight: 600;
        color: white !important;
        text-decoration: none !important;
        transition: transform 0.2s;
        display: flex;
        align-items: center;
        gap: 6px;
    }
    
    .trend-tag:hover { 
        transform: scale(1.05); 
        box-shadow: 0 0 10px rgba(255,255,255,0.2); 
    }
    
    .t-grad-1 { 
        background: linear-gradient(135deg, #ef4444, #b91c1c); 
    }
    
    .t-grad-2 { 
        background: linear-gradient(135deg, #ec4899, #be185d); 
    }
    
    .t-grad-3 { 
        background: linear-gradient(135deg, #8b5cf6, #6d28d9); 
    }
    
    .trend-vol { 
        font-size: 0.65rem; 
        opacity: 0.8; 
        background: rgba(0,0,0,0.3); 
        padding: 1px 4px; 
        border-radius: 3px; 
    }

    /* 📰 News Cards */
    .news-card {
        background: rgba(255, 255, 255, 0.03);
        border-left: 2px solid #444;
        border-radius: 0 6px 6px 0;
        padding: 12px;
        height: 100%;
        min-height: 120px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        transition: all 0.3s;
    }
    
    .news-card:hover {
        background: rgba(255, 255, 255, 0.06);
        border-left-color: #ef4444;
    }
    
    .news-meta { 
        font-size: 0.7rem; 
        color: #9ca3af; 
        display: flex; 
        justify-content: space-between; 
        margin-bottom: 6px; 
    }
    
    .news-title { 
        font-size: 0.9rem; 
        font-weight: 500; 
        color: #e5e7eb; 
        line-height: 1.4; 
    }
    
    .news-link-btn {
        display: block;
        margin-top: 10px;
        text-align: right;
        font-size: 0.75rem;
        color: #ef4444;
        text-decoration: none;
        font-weight: 600;
    }
    
    .news-link-btn:hover { 
        text-decoration: underline; 
        color: #fca5a5; 
    }

    /* 💰 Polymarket Cards (Compact) */
    .poly-card {
        background: rgba(20, 20, 20, 0.6);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 0px;
        height: 100%;
        transition: all 0.2s;
    }
    
    .poly-card:hover {
        border-color: #ef4444;
        background: rgba(40, 10, 10, 0.4);
    }
    
    .poly-head {
        display: flex;
        justify-content: space-between;
        margin-bottom: 8px;
        font-size: 0.7rem;
        color: #6b7280;
    }
    
    .poly-title {
        font-size: 0.85rem;
        font-weight: 600;
        color: #f3f4f6;
        line-height: 1.3;
        margin-bottom: 12px;
        height: 2.6em;
        overflow: hidden;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
    }
    
    .poly-bar {
        display: flex;
        height: 24px;
        border-radius: 4px;
        overflow: hidden;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.75rem;
        font-weight: 700;
    }
    
    .bar-yes {
        background: rgba(16, 185, 129, 0.2);
        color: #34d399;
        display: flex;
        align-items: center;
        padding-left: 6px;
        border-right: 1px solid rgba(0,0,0,0.5);
    }
    
    .bar-no {
        background: rgba(239, 68, 68, 0.2);
        color: #f87171;
        display: flex;
        align-items: center;
        justify-content: flex-end;
        padding-right: 6px;
        flex-grow: 1;
    }
    
    /* Analysis Results */
    .analysis-box {
        background: rgba(0, 0, 0, 0.5);
        border-left: 3px solid #ef4444;
        border-radius: 5px;
        padding: 15px;
        margin: 20px 0;
    }
    
    .analysis-header {
        color: #ef4444;
        font-weight: 700;
        font-size: 1rem;
        margin-bottom: 10px;
    }
    
    .analysis-content {
        color: #e5e7eb;
        line-height: 1.6;
    }
    
    /* Footer Hub */
    .hub-grid { 
        display: grid; 
        grid-template-columns: repeat(5, 1fr); 
        gap: 10px; 
    }
    
    .hub-btn {
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.05);
        border-radius: 8px;
        padding: 10px;
        text-align: center;
        text-decoration: none;
        color: #9ca3af !important;
        transition: all 0.3s;
        display: flex;
        flex-direction: column;
        align-items: center;
    }
    
    .hub-btn:hover {
        background: rgba(255,255,255,0.08);
        border-color: #ef4444;
        color: white !important;
        transform: translateY(-2px);
    }
    
    .hub-emoji { 
        font-size: 1.2rem; 
        margin-bottom: 4px; 
    }
    
    .hub-text { 
        font-size: 0.7rem; 
        font-weight: 600; 
        text-transform: uppercase; 
    }

    /* Input & Button Overrides */
    .stTextArea textarea { 
        background: rgba(0,0,0,0.5) !important; 
        border: 1px solid #333 !important; 
        color: white !important; 
    }
    
    .stTextArea textarea:focus { 
        border-color: #ef4444 !important; 
    }
    
    div.stButton > button {
        background: #b91c1c !important;
        color: white !important;
        border: none !important;
        width: 100%;
    }
    
    div.stButton > button:hover { 
        background: #dc2626 !important; 
    }
    
    /* Chat messages */
    .stChatMessage {
        background: rgba(0, 0, 0, 0.3);
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# ================= 🧠 3. DATA FETCHING LOGIC =================

# --- 🔥 A. Real-Time Google Trends (with fallback) ---
@st.cache_data(ttl=3600)
def fetch_google_trends():
    url = "https://trends.google.com/trends/trendingsearches/daily/rss?geo=US"
    trends = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        resp = requests.get(url, headers=headers, timeout=5)
        if resp.status_code == 200:
            feed = feedparser.parse(resp.content)
            for entry in feed.entries[:8]:
                traffic = "Hot"
                if hasattr(entry, 'ht_approx_traffic'):
                    traffic = entry.ht_approx_traffic
                # 清理标题，移除HTML实体
                title = html.unescape(entry.title)
                trends.append({"name": title, "vol": traffic})
    except Exception as e:
        st.error(f"Google Trends error: {e}")
    
    # Fallback if empty
    if not trends:
        trends = [
            {"name": "Bitcoin", "vol": "500K+"},
            {"name": "AI", "vol": "200K+"},
            {"name": "Nvidia", "vol": "100K+"},
            {"name": "Ethereum", "vol": "80K+"},
            {"name": "Trump", "vol": "150K+"},
            {"name": "Election", "vol": "120K+"}
        ]
    return trends

# --- 🔥 B. News Fetcher (Category + Time Filter) ---
@st.cache_data(ttl=900)
def fetch_news_by_category(category):
    news_items = []
    
    params = {
        "language": "en",
        "pageSize": 60,
        "apiKey": NEWS_API_KEY
    }
    
    if category == "Web3":
        url = "https://newsapi.org/v2/everything"
        params["q"] = "crypto OR bitcoin OR ethereum OR blockchain"
        params["sortBy"] = "publishedAt"
    elif category == "Politics":
        url = "https://newsapi.org/v2/everything"
        params["q"] = "politics OR election OR government"
        params["sortBy"] = "publishedAt"
    elif category == "Tech":
        url = "https://newsapi.org/v2/everything"
        params["q"] = "technology OR AI OR software"
        params["sortBy"] = "publishedAt"
    else:
        url = "https://newsapi.org/v2/top-headlines"
        params["country"] = "us"

    if NEWS_API_KEY:
        try:
            resp = requests.get(url, params=params, timeout=10)
            data = resp.json()
            if data.get("status") == "ok":
                for art in data.get("articles", []):
                    if art['title'] == "[Removed]" or not art['title']:
                        continue
                    
                    pub_str = art.get("publishedAt")
                    time_ago = "Recent"
                    
                    if pub_str:
                        try:
                            pub_dt = datetime.datetime.strptime(pub_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)
                            now_dt = datetime.datetime.now(datetime.timezone.utc)
                            diff = now_dt - pub_dt
                            hours = diff.total_seconds() / 3600
                            
                            if hours > 24:
                                continue
                            elif hours < 1:
                                time_ago = f"{int(diff.total_seconds()/60)}m ago"
                            else:
                                time_ago = f"{int(hours)}h ago"
                        except:
                            pass
                    
                    # 清理HTML实体
                    title = html.unescape(art['title'])
                    news_items.append({
                        "title": title,
                        "source": art['source']['name'],
                        "link": art['url'],
                        "time": time_ago
                    })
        except Exception as e:
            st.error(f"News API error: {e}")

    # Fallback to RSS
    if not news_items:
        rss_map = {
            "Web3": "https://cointelegraph.com/rss",
            "Tech": "https://techcrunch.com/feed/",
            "Politics": "https://feeds.bbci.co.uk/news/politics/rss.xml",
            "All": "http://feeds.bbci.co.uk/news/rss.xml"
        }
        try:
            feed_url = rss_map.get(category, rss_map["All"])
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:20]:
                title = html.unescape(entry.title)
                news_items.append({
                    "title": title,
                    "source": entry.get("source", {}).get("title", "RSS Feed"),
                    "link": entry.link,
                    "time": "Recent"
                })
        except Exception as e:
            st.error(f"RSS error: {e}")
            
    return news_items[:20]

# --- 🔥 C. Polymarket Global Top Volume (修复API) ---
@st.cache_data(ttl=60)
def fetch_top_polymarkets():
    # 使用新的API端点
    url = "https://strapi-matic.poly.market/markets?limit=20&sort=volume24h:desc"
    markets = []
    
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            for item in data.get("data", []):
                try:
                    attributes = item.get("attributes", {})
                    title = attributes.get("question", "")
                    
                    # 获取交易量
                    volume_24h = attributes.get("volume24h", 0)
                    if isinstance(volume_24h, str):
                        volume_24h = float(volume_24h)
                    
                    # 格式化交易量
                    if volume_24h > 1000000:
                        vol_str = f"${volume_24h/1000000:.1f}M"
                    elif volume_24h > 1000:
                        vol_str = f"${volume_24h/1000:.0f}K"
                    else:
                        vol_str = f"${volume_24h:.0f}"
                    
                    # 获取价格数据
                    outcomes = attributes.get("outcomes", [])
                    if len(outcomes) >= 2:
                        yes_price = outcomes[0].get("price", 50) * 100
                        no_price = outcomes[1].get("price", 50) * 100
                        
                        # 确保价格是整数且合理
                        yes_price = int(max(0, min(100, yes_price)))
                        no_price = int(max(0, min(100, 100 - yes_price)))
                        
                        markets.append({
                            "title": html.unescape(title),
                            "vol_str": vol_str,
                            "vol_raw": volume_24h,
                            "yes": yes_price,
                            "no": no_price,
                            "slug": attributes.get("slug", "")
                        })
                except Exception as e:
                    continue
    except Exception as e:
        st.error(f"Polymarket API error: {e}")
    
    # 按交易量排序
    markets.sort(key=lambda x: x['vol_raw'], reverse=True)
    return markets[:10]

# --- 🔥 D. AI 分析推理功能 ---
def analyze_with_gemini(news_text, polymarket_data):
    """使用Gemini AI分析新闻和Polymarket数据"""
    if not GEMINI_AVAILABLE or not GOOGLE_API_KEY:
        return "⚠️ Gemini API不可用。请检查API密钥配置。"
    
    try:
        # 配置安全设置
        safety_settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }
        
        # 准备Polymarket数据摘要
        poly_summary = ""
        if polymarket_data:
            poly_summary = "相关预测市场数据：\n"
            for market in polymarket_data[:5]:
                poly_summary += f"- {market['title']}: Yes {market['yes']}% | No {market['no']}% | 交易量: {market['vol_str']}\n"
        
        # 构造提示词
        prompt = f"""
        你是一个专业的市场分析师和新闻事实核查员。请分析以下新闻内容，并结合预测市场数据进行推理分析。
        
        新闻内容：{news_text}
        
        {poly_summary}
        
        请从以下角度进行分析：
        1. 事实核查：这条新闻的可信度如何？是否有已知的事实错误或偏见？
        2. 市场影响：这条新闻对相关市场（加密货币、股票、政治等）可能产生什么影响？
        3. 预测市场验证：预测市场的赔率如何反映市场对这条新闻的看法？
        4. 推演分析：基于这条新闻，未来24-72小时可能发生什么？
        5. 建议：投资者或关注者应该注意什么？
        
        请用中文回答，保持专业、客观。
        """
        
        # 调用Gemini API
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(
            prompt,
            safety_settings=safety_settings,
            generation_config={
                "temperature": 0.7,
                "top_p": 0.8,
                "top_k": 40,
                "max_output_tokens": 2048,
            }
        )
        
        return response.text
    except Exception as e:
        return f"分析过程中出现错误：{str(e)}"

# ================= 🖥️ 4. MAIN LAYOUT =================

# --- Header ---
st.markdown('<div class="hero-title">Be Holmes</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-subtitle">Narrative vs. Reality Engine</div>', unsafe_allow_html=True)

# --- Search Bar (Centered) ---
_, s_col, _ = st.columns([1, 6, 1])
with s_col:
    user_query = st.text_area("Analyze News", height=70, placeholder="Paste a headline to check reality...", label_visibility="collapsed")
    
    if st.button("⚖️ REALITY CHECK", key="reality_check"):
        if user_query:
            with st.spinner("🔍 Holmes正在分析中..."):
                # 获取当前Polymarket数据
                polymarket_data = fetch_top_polymarkets()
                
                # 使用AI进行分析
                analysis_result = analyze_with_gemini(user_query, polymarket_data)
                
                # 保存结果到session state
                st.session_state.analysis_result = analysis_result
                st.session_state.messages.append({
                    "role": "user", 
                    "content": user_query
                })
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": analysis_result
                })
                
                # 显示成功消息
                st.success("✅ 分析完成！")
        else:
            st.warning("请输入要分析的新闻内容")

# --- 显示分析结果 ---
if st.session_state.analysis_result:
    st.markdown('<div class="analysis-box">', unsafe_allow_html=True)
    st.markdown('<div class="analysis-header">🕵️‍♂️ HOLMES 分析报告</div>', unsafe_allow_html=True)
    st.markdown(st.session_state.analysis_result)
    st.markdown('</div>', unsafe_allow_html=True)

# --- 显示聊天历史 ---
if st.session_state.messages:
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

st.markdown("<br>", unsafe_allow_html=True)

# --- Main Split Layout ---
col_left, col_right = st.columns([1, 1], gap="large")

# ================= 👈 LEFT COLUMN: TRENDS + NEWS =================
with col_left:
    # 1. Google Trends (Top)
    st.markdown('<div class="section-header">📈 LIVE SEARCH TRENDS</div>', unsafe_allow_html=True)
    trends = fetch_google_trends()
    
    # Use HTML for colorful tags with links
    trend_html = '<div class="trend-container">'
    gradients = ["t-grad-1", "t-grad-2", "t-grad-3"]
    
    for i, t in enumerate(trends):
        color_class = gradients[i % 3]
        safe_q = urllib.parse.quote(t['name'])
        trend_html += f"""
        <a href="https://www.google.com/search?q={safe_q}" target="_blank" class="trend-tag {color_class}">
            {t['name']} <span class="trend-vol">{t['vol']}</span>
        </a>
        """
    trend_html += '</div>'
    st.markdown(trend_html, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)

    # 2. News Feed Header & Filters
    c1, c2 = st.columns([1, 1])
    with c1:
        st.markdown('<div class="section-header" style="margin-bottom:0;">📡 GLOBAL WIRE (24H)</div>', unsafe_allow_html=True)
    with c2:
        # Category Filter Pills
        cat = st.radio("Category", ["All", "Web3", "Tech", "Politics"], 
                      horizontal=True, 
                      label_visibility="collapsed",
                      key="news_filter")
        if cat != st.session_state.news_category:
            st.session_state.news_category = cat

    # 3. News Grid (Dual Column)
    news_items = fetch_news_by_category(st.session_state.news_category)
    
    if not news_items:
        st.info("📡 Scanning frequencies...")
    else:
        # Create 2-column layout for news cards
        for i in range(0, len(news_items), 2):
            row_cols = st.columns(2)
            # Card 1
            if i < len(news_items):
                with row_cols[0]:
                    item = news_items[i]
                    st.markdown(f"""
                    <div class="news-card">
                        <div class="news-meta">
                            <span>{item['source']}</span>
                            <span style="color:#ef4444">{item['time']}</span>
                        </div>
                        <div class="news-title">{item['title']}</div>
                        <a href="{item['link']}" target="_blank" class="news-link-btn">🔗 READ SOURCE</a>
                    </div>
                    """, unsafe_allow_html=True)
            
            # Card 2 (if exists)
            if i + 1 < len(news_items):
                with row_cols[1]:
                    item = news_items[i+1]
                    st.markdown(f"""
                    <div class="news-card">
                        <div class="news-meta">
                            <span>{item['source']}</span>
                            <span style="color:#ef4444">{item['time']}</span>
                        </div>
                        <div class="news-title">{item['title']}</div>
                        <a href="{item['link']}" target="_blank" class="news-link-btn">🔗 READ SOURCE</a>
                    </div>
                    """, unsafe_allow_html=True)
            
            st.markdown("<div style='margin-bottom:10px'></div>", unsafe_allow_html=True)

# ================= 👉 RIGHT COLUMN: POLYMARKET TOP VOL =================
with col_right:
    st.markdown('<div class="section-header">💰 GLOBAL PREDICTION MARKETS (BY VOLUME)</div>', unsafe_allow_html=True)
    
    top_markets = fetch_top_polymarkets()
    
    if not top_markets:
        st.info("🔌 Connecting to Polymarket...")
    else:
        # Create 2-column layout for markets
        for i in range(0, len(top_markets), 2):
            m_cols = st.columns(2)
            
            # Left Market Card
            if i < len(top_markets):
                with m_cols[0]:
                    m = top_markets[i]
                    # 清理URL
                    slug = m.get('slug', '')
                    if not slug.startswith('https://'):
                        slug = f"https://polymarket.com/event/{slug}"
                    
                    st.markdown(f"""
                    <a href="{slug}" target="_blank" style="text-decoration:none;">
                        <div class="poly-card">
                            <div class="poly-head">
                                <span>🔥 HOT</span>
                                <span style="color:#e5e7eb; font-weight:bold;">Vol: {m['vol_str']}</span>
                            </div>
                            <div class="poly-title">{m['title']}</div>
                            <div class="poly-bar">
                                <div class="bar-yes" style="width:{m['yes']}%">Yes {m['yes']}%</div>
                                <div class="bar-no" style="width:{m['no']}%">{m['no']}% No</div>
                            </div>
                        </div>
                    </a>
                    """, unsafe_allow_html=True)
                
            # Right Market Card (if exists)
            if i + 1 < len(top_markets):
                with m_cols[1]:
                    m = top_markets[i+1]
                    slug = m.get('slug', '')
                    if not slug.startswith('https://'):
                        slug = f"https://polymarket.com/event/{slug}"
                    
                    st.markdown(f"""
                    <a href="{slug}" target="_blank" style="text-decoration:none;">
                        <div class="poly-card">
                            <div class="poly-head">
                                <span>🔥 HOT</span>
                                <span style="color:#e5e7eb; font-weight:bold;">Vol: {m['vol_str']}</span>
                            </div>
                            <div class="poly-title">{m['title']}</div>
                            <div class="poly-bar">
                                <div class="bar-yes" style="width:{m['yes']}%">Yes {m['yes']}%</div>
                                <div class="bar-no" style="width:{m['no']}%">{m['no']}% No</div>
                            </div>
                        </div>
                    </a>
                    """, unsafe_allow_html=True)
            
            st.markdown("<div style='margin-bottom:10px'></div>", unsafe_allow_html=True)

# ================= 🌐 FOOTER: INTELLIGENCE HUB =================
st.markdown("---")
st.markdown('<div style="text-align:center; color:#6b7280; font-size:0.8rem; margin-bottom:20px; letter-spacing:2px;">🌐 GLOBAL INTELLIGENCE HUB</div>', unsafe_allow_html=True)

hub_data = [
    {"name": "Jin10", "icon": "🇨🇳", "url": "https://www.jin10.com/"},
    {"name": "WallStCN", "icon": "🇨🇳", "url": "https://wallstreetcn.com/live/global"},
    {"name": "Zaobao", "icon": "🇸🇬", "url": "https://www.zaobao.com.sg/realtime/world"},
    {"name": "SCMP", "icon": "🇭🇰", "url": "https://www.scmp.com/"},
    {"name": "Nikkei", "icon": "🇯🇵", "url": "https://asia.nikkei.com/"},
    {"name": "Bloomberg", "icon": "🇺🇸", "url": "https://www.bloomberg.com/"},
    {"name": "Reuters", "icon": "🇬🇧", "url": "https://www.reuters.com/"},
    {"name": "CoinDesk", "icon": "🪙", "url": "https://www.coindesk.com/"},
    {"name": "TechCrunch", "icon": "⚡", "url": "https://techcrunch.com/"},
    {"name": "Al Jazeera", "icon": "🇶🇦", "url": "https://www.aljazeera.com/"},
]

rows = [hub_data[i:i+5] for i in range(0, len(hub_data), 5)]
for row in rows:
    cols = st.columns(5)
    for i, item in enumerate(row):
        with cols[i]:
            st.markdown(f"""
            <a href="{item['url']}" target="_blank" class="hub-btn">
                <div class="hub-content">
                    <span class="hub-emoji">{item['icon']}</span>
                    <span class="hub-text">{item['name']}</span>
                </div>
            </a>
            """, unsafe_allow_html=True)

st.markdown("<br><br>", unsafe_allow_html=True)
