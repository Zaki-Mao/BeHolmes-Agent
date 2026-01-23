import streamlit as st
import requests
import json
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import re
import time
import datetime

# ================= 🔐 0. KEY MANAGEMENT =================
try:
    EXA_API_KEY = st.secrets["EXA_API_KEY"]
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
    KEYS_LOADED = True
except:
    EXA_API_KEY = None
    GOOGLE_API_KEY = None
    KEYS_LOADED = False

if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

# ================= 🛠️ DEPENDENCY CHECK =================
try:
    from exa_py import Exa
    EXA_AVAILABLE = True
except ImportError:
    EXA_AVAILABLE = False

# ================= 🕵️‍♂️ 1. SYSTEM CONFIGURATION =================
st.set_page_config(
    page_title="Be Holmes | Research",
    page_icon="🕵️‍♂️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ================= 🧠 1.1 STATE MANAGEMENT =================
if "messages" not in st.session_state:
    st.session_state.messages = []  
if "current_market" not in st.session_state:
    st.session_state.current_market = None 
if "first_visit" not in st.session_state:
    st.session_state.first_visit = True 
if "last_search_query" not in st.session_state:
    st.session_state.last_search_query = ""
if "chat_history_context" not in st.session_state:
    st.session_state.chat_history_context = []
if "search_results" not in st.session_state:
    st.session_state.search_results = []  
if "show_market_selection" not in st.session_state:
    st.session_state.show_market_selection = False  
if "selected_market_index" not in st.session_state:
    st.session_state.selected_market_index = -1  

# ================= 🎨 2. UI THEME (保持原版不动) =================
st.markdown("""
<style>
    /* Import Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;900&family=Plus+Jakarta+Sans:wght@400;700&display=swap');

    /* 1. Global Background */
    .stApp {
        background-image: linear-gradient(rgba(0, 0, 0, 0.8), rgba(0, 0, 0, 0.9)), 
                          url('https://upload.cc/i1/2026/01/20/s8pvXA.jpg');
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
        font-family: 'Inter', sans-serif;
    }

    /* Transparent Header */
    header[data-testid="stHeader"] { background-color: transparent !important; }
    [data-testid="stToolbar"] { visibility: hidden; }
    [data-testid="stDecoration"] { visibility: hidden; }

    /* Hero Title */
    .hero-title {
        font-family: 'Inter', sans-serif;
        font-weight: 700;
        font-size: 4.5rem;
        color: #ffffff;
        text-align: center;
        letter-spacing: -2px;
        margin-bottom: 5px;
        padding-top: 8vh;
        text-shadow: 0 0 20px rgba(0,0,0,0.5);
    }
    
    .hero-subtitle {
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 1.1rem;
        color: #9ca3af; 
        text-align: center;
        margin-bottom: 50px;
        font-weight: 400;
    }

    /* 4. Input Field Styling */
    div[data-testid="stVerticalBlock"] > div {
        display: flex;
        flex-direction: column;
        align-items: center;
    }
    .stTextArea { width: 100% !important; max-width: 800px !important; }
    
    .stTextArea textarea {
        background-color: rgba(31, 41, 55, 0.6) !important;
        color: #ffffff !important;
        border: 1px solid #374151 !important;
        border-radius: 16px !important;
        padding: 15px 20px !important; 
        font-size: 1rem !important;
        text-align: left !important;
        line-height: 1.6 !important;
        backdrop-filter: blur(10px);
        transition: all 0.3s ease;
    }
    
    .stTextArea textarea:focus {
        border-color: rgba(239, 68, 68, 0.8) !important;
        box-shadow: 0 0 15px rgba(220, 38, 38, 0.3) !important;
        background-color: rgba(31, 41, 55, 0.9) !important;
    }

    /* 3. Button Styling */
    div.stButton > button:first-child {
        background: linear-gradient(90deg, #7f1d1d 0%, #dc2626 50%, #7f1d1d 100%) !important;
        background-size: 200% auto !important;
        color: #ffffff !important;
        border: 1px solid rgba(239, 68, 68, 0.5) !important;
        border-radius: 50px !important;
        padding: 12px 50px !important;
        font-weight: 600 !important;
        font-size: 1.1rem !important;
        margin-top: 10px !important;
        transition: 0.5s !important;
        box-shadow: 0 0 20px rgba(0,0,0,0.5) !important;
    }
    
    div.stButton > button:first-child:hover {
        background-position: right center !important;
        transform: scale(1.05) !important;
        box-shadow: 0 0 30px rgba(220, 38, 38, 0.6) !important;
        border-color: #fca5a5 !important;
    }
    
    div.stButton > button:first-child:active {
        transform: scale(0.98) !important;
    }

    /* Result Card */
    .market-card {
        background: rgba(17, 24, 39, 0.8);
        border: 1px solid #374151;
        border-radius: 12px;
        padding: 20px;
        margin: 20px auto;
        max-width: 800px;
        backdrop-filter: blur(8px);
        box-shadow: 0 4px 20px rgba(0,0,0,0.3);
    }
    
    /* Market Selection Card */
    .market-selection-card {
        background: rgba(17, 24, 39, 0.7);
        border: 1px solid #374151;
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
        transition: all 0.3s ease;
        backdrop-filter: blur(5px);
    }
    
    .market-selection-card:hover {
        border-color: #ef4444;
        background: rgba(31, 41, 55, 0.9);
        transform: translateY(-2px);
    }
    
    .market-selection-card.selected {
        border: 2px solid #ef4444;
        background: rgba(31, 41, 55, 0.95);
        box-shadow: 0 0 15px rgba(239, 68, 68, 0.3);
    }
    
    .select-market-btn {
        background: linear-gradient(90deg, #7f1d1d 0%, #dc2626 100%) !important;
        color: white !important;
        border: none !important;
        padding: 8px 20px !important;
        border-radius: 6px !important;
        font-size: 0.9rem !important;
        font-weight: 600 !important;
        transition: all 0.3s !important;
    }
    
    .select-market-btn:hover {
        transform: scale(1.05) !important;
        box-shadow: 0 0 10px rgba(220, 38, 38, 0.5) !important;
    }

    /* Top 12 Grid Styles */
    .top10-container {
        width: 100%;
        max-width: 1200px;
        margin: 60px auto 20px auto;
        padding: 0 20px;
    }
    .top10-header {
        font-size: 0.9rem;
        color: #9ca3af;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 20px;
        border-left: 3px solid #dc2626;
        padding-left: 10px;
    }
    .top10-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 15px;
    }
    @media (max-width: 800px) { .top10-grid { grid-template-columns: 1fr; } }
    
    .market-item {
        background: rgba(17, 24, 39, 0.6);
        border: 1px solid #374151;
        border-radius: 8px;
        padding: 15px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        transition: all 0.2s;
        backdrop-filter: blur(5px);
        min-height: 110px;
        text-decoration: none !important;
        color: inherit !important;
        cursor: pointer;
    }
    .market-item:hover {
        border-color: #ef4444;
        background: rgba(31, 41, 55, 0.9);
        transform: translateY(-2px);
    }
    .m-title {
        color: #e5e7eb;
        font-size: 0.95rem;
        font-weight: 500;
        margin-bottom: 12px;
        line-height: 1.4;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }
    .m-odds { display: flex; gap: 8px; font-size: 0.75rem; margin-top: auto; }
    .tag-yes { background: rgba(6, 78, 59, 0.4); color: #4ade80; padding: 2px 8px; border-radius: 4px; font-weight: bold;}
    .tag-no { background: rgba(127, 29, 29, 0.4); color: #f87171; padding: 2px 8px; border-radius: 4px; font-weight: bold;}
    
    .stChatMessage {
        background: rgba(31, 41, 55, 0.4);
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 12px;
        margin-bottom: 10px;
    }
    
    /* Market Selection Container */
    .selection-container {
        background: rgba(17, 24, 39, 0.6);
        border: 1px solid #374151;
        border-radius: 12px;
        padding: 25px;
        margin: 30px auto;
        max-width: 900px;
        backdrop-filter: blur(8px);
    }
    
    /* Relevance Indicator */
    .relevance-badge {
        display: inline-block;
        padding: 3px 8px;
        border-radius: 12px;
        font-size: 0.7rem;
        font-weight: 600;
        margin-left: 10px;
    }
    .relevance-high {
        background: rgba(6, 78, 59, 0.4);
        color: #4ade80;
        border: 1px solid rgba(6, 78, 59, 0.6);
    }
    .relevance-medium {
        background: rgba(146, 64, 14, 0.4);
        color: #fdba74;
        border: 1px solid rgba(146, 64, 14, 0.6);
    }
    .relevance-low {
        background: rgba(127, 29, 29, 0.4);
        color: #f87171;
        border: 1px solid rgba(127, 29, 29, 0.6);
    }
</style>
""", unsafe_allow_html=True)

# ================= 🧠 3. LOGIC CORE =================

def extract_entities_and_keywords(user_text):
    """使用Gemini提取新闻中的核心实体和关键词，优先排序"""
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        prompt = f"""
        分析以下新闻，提取用于搜索预测市场的关键词。请按重要性排序：
        
        新闻原文："{user_text}"
        
        要求：
        1. 识别核心主体（公司、人物、产品）：如Tesla, Elon Musk, FSD等
        2. 识别核心事件/主题：如regulatory approval, launch, earnings等
        3. 识别次要信息：如地点、时间等
        4. 按以下格式输出：
        
        核心实体: [实体1], [实体2], [实体3]
        事件关键词: [关键词1], [关键词2], [关键词3]
        搜索优先级: 
        1. [最高优先级搜索词]
        2. [中优先级搜索词]
        3. [低优先级搜索词]
        
        示例输入："苹果将在2024年发布新款iPhone"
        输出：
        核心实体: Apple, iPhone
        事件关键词: launch, release, new product
        搜索优先级: 
        1. Apple iPhone launch prediction market
        2. Apple new product release market
        3. Apple 2024 product prediction
        """
        
        resp = model.generate_content(prompt)
        text = resp.text.strip()
        
        # 解析响应
        entities = []
        events = []
        search_queries = []
        
        lines = text.split('\n')
        for line in lines:
            if line.startswith('核心实体:'):
                entities = [e.strip() for e in line.replace('核心实体:', '').split(',')]
            elif line.startswith('事件关键词:'):
                events = [e.strip() for e in line.replace('事件关键词:', '').split(',')]
            elif line.startswith('1.'):
                search_queries.append(line.split('. ', 1)[1].strip())
            elif line.startswith('2.'):
                search_queries.append(line.split('. ', 1)[1].strip())
            elif line.startswith('3.'):
                search_queries.append(line.split('. ', 1)[1].strip())
        
        # 如果没有提取到搜索查询，使用备用策略
        if not search_queries:
            # 组合实体和事件
            if entities and events:
                search_queries = [
                    f"{entities[0]} {events[0]} prediction market",
                    f"{' '.join(entities[:2])} market",
                    f"{' '.join(entities)} Polymarket"
                ]
            else:
                # 最后备选：简单清理文本
                cleaned = re.sub(r'[^a-zA-Z0-9\s]', ' ', user_text)
                words = cleaned.lower().split()
                stop_words = ["the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by", "is", "are", "was", "were", "be", "been", "being"]
                keywords = [w for w in words if w not in stop_words][:6]
                search_queries = [' '.join(keywords)]
        
        return {
            'entities': entities,
            'events': events,
            'search_queries': search_queries
        }
        
    except Exception as e:
        print(f"Entity extraction error: {e}")
        # 回退策略
        cleaned = re.sub(r'[^a-zA-Z0-9\s]', ' ', user_text)
        return {
            'entities': [],
            'events': [],
            'search_queries': [cleaned[:100]]
        }

def calculate_relevance_score(market_title, entities, events):
    """计算市场标题与新闻的相关性分数"""
    title_lower = market_title.lower()
    
    # 初始化分数
    score = 0
    
    # 检查核心实体
    for entity in entities:
        entity_lower = entity.lower()
        if entity_lower in title_lower:
            score += 10  # 核心实体匹配高分
            # 如果实体在开头，额外加分
            if title_lower.startswith(entity_lower):
                score += 5
    
    # 检查事件关键词
    for event in events:
        event_lower = event.lower()
        if event_lower in title_lower:
            score += 5  # 事件匹配中分
    
    # 特殊关键词加分
    special_keywords = ['tesla', 'elon', 'musk', 'fsd', 'full self-driving', 'autonomous']
    for keyword in special_keywords:
        if keyword in title_lower:
            score += 3
    
    # 减分项：过度强调中国（如果核心实体不是中国公司）
    if 'china' in title_lower or 'chinese' in title_lower:
        if not any(e.lower() in ['alibaba', 'tencent', 'baidu', 'xiaomi'] for e in entities):
            score -= 2  # 如果不是中国公司，中国相关减分
    
    return score

def search_with_exa_optimized(user_text):
    """优化的语义搜索，聚焦核心实体"""
    if not EXA_AVAILABLE or not EXA_API_KEY: 
        return [], []
    
    # 提取实体和搜索查询
    extraction_result = extract_entities_and_keywords(user_text)
    entities = extraction_result['entities']
    events = extraction_result['events']
    search_queries = extraction_result['search_queries']
    
    print(f"提取的实体: {entities}")
    print(f"提取的事件: {events}")
    print(f"搜索查询: {search_queries}")
    
    markets_found = []
    seen_titles = set()
    
    try:
        exa = Exa(EXA_API_KEY)
        
        # 按优先级顺序尝试搜索
        for query in search_queries:
            if len(markets_found) >= 15:  # 最多收集15个结果
                break
                
            try:
                # 尝试不同的搜索格式
                search_formats = [
                    f"{query} prediction market Polymarket",
                    f"Polymarket market {query}",
                    f"{query} market odds",
                    f"prediction market {query}"
                ]
                
                for search_str in search_formats:
                    print(f"尝试搜索: {search_str}")
                    
                    search_response = exa.search(
                        search_str,
                        num_results=8, 
                        type="neural",
                        include_domains=["polymarket.com"]
                    )
                    
                    for result in search_response.results:
                        match = re.search(r'polymarket\.com/(?:event|market)/([^/]+)', result.url)
                        if match:
                            slug = match.group(1)
                            # 过滤无关页面
                            if slug not in ['profile', 'login', 'leaderboard', 'rewards', 'orders', 'activity']:
                                market_data = fetch_poly_details(slug)
                                if market_data:
                                    for market in market_data:
                                        title = market.get('title', '')
                                        
                                        # 去重
                                        if title and title not in seen_titles:
                                            # 计算相关性分数
                                            relevance = calculate_relevance_score(title, entities, events)
                                            market['relevance_score'] = relevance
                                            market['slug'] = slug
                                            markets_found.append(market)
                                            seen_titles.add(title)
                                            
            except Exception as e:
                print(f"搜索查询 '{query}' 错误: {e}")
                continue
                        
    except Exception as e: 
        print(f"搜索主错误: {e}")
    
    # 按相关性排序
    markets_found.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
    
    # 过滤掉相关性太低的结果
    filtered_markets = [m for m in markets_found if m.get('relevance_score', 0) > 5]
    
    return filtered_markets[:10], search_queries[0] if search_queries else ""

@st.cache_data(ttl=60)
def fetch_top_10_markets():
    try:
        url = "https://gamma-api.polymarket.com/events?limit=12&sort=volume&closed=false"
        resp = requests.get(url, timeout=5).json()
        markets = []
        if isinstance(resp, list):
            for event in resp:
                try:
                    title = event.get('title', 'Unknown Event')
                    event_markets = event.get('markets', [])
                    if not event_markets or not isinstance(event_markets, list): continue
                    
                    active_markets = []
                    for m in event_markets:
                        if m.get('closed') is True: continue
                        if not m.get('outcomePrices'): continue
                        active_markets.append(m)
                    if not active_markets: continue

                    active_markets.sort(key=lambda x: float(x.get('volume', 0) or 0), reverse=True)
                    m = active_markets[0]

                    outcomes = m.get('outcomes')
                    if isinstance(outcomes, str): outcomes = json.loads(outcomes)
                    prices = m.get('outcomePrices')
                    if isinstance(prices, str): prices = json.loads(prices)
                    if not outcomes or not prices or len(prices) != len(outcomes): continue

                    yes_price = 0
                    no_price = 0
                    
                    if "Yes" in outcomes and "No" in outcomes:
                        try:
                            yes_index = outcomes.index("Yes")
                            yes_raw = float(prices[yes_index])
                            yes_price = int(yes_raw * 100)
                            no_price = 100 - yes_price
                        except:
                            yes_price = int(float(prices[0]) * 100)
                            no_price = 100 - yes_price
                    else:
                        float_prices = [float(p) for p in prices]
                        max_price = max(float_prices)
                        yes_price = int(max_price * 100)
                        no_price = 100 - yes_price

                    markets.append({
                        "title": title,
                        "yes": yes_price,
                        "no": no_price,
                        "slug": event.get('slug', '')
                    })
                except Exception: continue
        return markets
    except Exception: return []

def fetch_poly_details(slug):
    valid_markets = []
    try:
        url = f"https://gamma-api.polymarket.com/events?slug={slug}"
        resp = requests.get(url, timeout=3).json()
        if isinstance(resp, list) and resp:
            for m in resp[0].get('markets', [])[:1]: 
                p = normalize_data(m)
                if p: valid_markets.append(p)
        return valid_markets
    except: pass
    try:
        url = f"https://gamma-api.polymarket.com/markets?slug={slug}"
        resp = requests.get(url, timeout=3).json()
        if isinstance(resp, list):
            for m in resp:
                p = normalize_data(m)
                if p: valid_markets.append(p)
        elif isinstance(resp, dict):
            p = normalize_data(resp)
            if p: valid_markets.append(p)
        return valid_markets
    except: pass
    return []

def normalize_data(m):
    try:
        if m.get('closed') is True: return None
        outcomes = m.get('outcomes')
        if isinstance(outcomes, str): outcomes = json.loads(outcomes)
        prices = m.get('outcomePrices')
        if isinstance(prices, str): prices = json.loads(prices)
        
        if not outcomes or not prices: return None

        display_label = ""
        if "Yes" in outcomes:
            idx = outcomes.index("Yes")
            price = float(prices[idx])
            display_label = f"Yes: {price*100:.1f}%"
        else:
            float_prices = [float(p) for p in prices]
            max_p = max(float_prices)
            max_idx = float_prices.index(max_p)
            top_name = outcomes[max_idx]
            display_label = f"{top_name}: {max_p*100:.1f}%"

        return {
            "title": m.get('question', 'Unknown'),
            "odds": display_label,
            "volume": float(m.get('volume', 0)),
            "slug": m.get('slug', '') or m.get('market_slug', '')
        }
    except: return None

# ================= 🧠 3.1 AGENT BRAIN =================

safety_config = {
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
}

def check_search_intent(user_text, current_market=None):
    """判断用户是否想要搜索新主题"""
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        context = {
            'current_market': current_market['title'] if current_market else None,
            'last_search': st.session_state.last_search_query,
            'is_follow_up': len(st.session_state.messages) > 1
        }
        
        prompt = f"""
        Analyze if the user wants to search for a NEW prediction market topic.
        
        CONTEXT:
        - Current topic: {context['current_market']}
        - Last search: {context['last_search']}
        - Is follow-up conversation: {context['is_follow_up']}
        
        USER INPUT: "{user_text}"
        
        Output only "YES" or "NO".
        """
        
        resp = model.generate_content(prompt, safety_settings=safety_config)
        result = resp.text.strip().upper()
        
        if "YES" in result:
            return True
        elif "NO" in result:
            return False
        else:
            search_triggers = ["search", "find", "look for", "show me", "new", "different"]
            if any(trigger in user_text.lower() for trigger in search_triggers):
                return True
            if current_market and len(user_text.split()) <= 3:
                return False
            return False
            
    except Exception as e:
        print(f"Intent check error: {e}")
        return False

def stream_chat_response(messages, market_data=None, user_query=""):
    """生成分析响应"""
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    current_date = datetime.datetime.now().strftime("%Y-%m-%d")
    
    recent_history = "\n".join([
        f"{'User' if msg['role']=='user' else 'Assistant'}: {msg['content'][:100]}..."
        for msg in messages[-3:]
    ]) if len(messages) > 0 else "No previous conversation."
    
    market_context = ""
    if market_data:
        market_context = f"""
        SELECTED MARKET DATA:
        - Event/Question: "{market_data['title']}"
        - Current Odds: {market_data['odds']}
        - Trading Volume: ${market_data['volume']:,.0f}
        - Relevance Score: {market_data.get('relevance_score', 'N/A')}
        """
    
    user_intel = user_query if user_query else "the provided intelligence"
    
    system_prompt = f"""
    You are Be Holmes, a cynical but rational Macro Hedge Fund Manager specializing in prediction markets.
    Current Date: {current_date}
    
    USER'S INTELLIGENCE/QUERY: {user_intel}
    
    {market_context}
    
    RECENT CONVERSATION:
    {recent_history}
    
    ANALYSIS FRAMEWORK:
    1. **Market Context**: Explain what this prediction market is about
    2. **Current Sentiment**: Analyze the current odds and what they imply
    3. **News Impact**: How does the user's intelligence/news affect this market?
    4. **Market Inefficiencies**: Identify any mispricings or opportunities
    5. **Risk Assessment**: What are the key risks?
    6. **Trading Recommendation**: Clear buy/sell/hold recommendation with reasoning
    
    CRITICAL REQUIREMENTS:
    - Be data-driven and quantitative where possible
    - Maintain a skeptical, contrarian mindset
    - Provide specific probability estimates if relevant
    - Suggest position sizing if making a recommendation
    - Highlight both upside and downside scenarios
    - Match the user's language (Chinese/English)
    
    FORMAT:
    Start with a brief executive summary, then detailed analysis.
    """
    
    history = [{"role": "user", "parts": [system_prompt]}]
    for msg in messages:
        role = "user" if msg["role"] == "user" else "model"
        history.append({"role": role, "parts": [msg["content"]]})
    
    try:
        response = model.generate_content(history, safety_settings=safety_config)
        return response.text
    except ValueError:
        return "⚠️ Safety filter triggered. Please rephrase your query."
    except Exception as e:
        return f"⚠️ Error: {str(e)}"

def analyze_selected_market(market_index, user_query):
    """分析用户选择的市场"""
    if 0 <= market_index < len(st.session_state.search_results):
        selected_market = st.session_state.search_results[market_index]
        st.session_state.current_market = selected_market
        st.session_state.selected_market_index = market_index
        
        st.session_state.messages = []
        st.session_state.messages.append({"role": "user", "content": f"Analyze this intel in relation to the selected market: {user_query}"})
        
        with st.spinner("🧠 Decoding Alpha..."):
            response = stream_chat_response(
                st.session_state.messages, 
                selected_market,
                user_query
            )
            st.session_state.messages.append({"role": "assistant", "content": response})
        
        st.session_state.show_market_selection = False
        return True
    return False

# ================= 🖥️ 4. MAIN INTERFACE =================

# 4.1 Hero Section
st.markdown('<h1 class="hero-title">Be Holmes</h1>', unsafe_allow_html=True)
st.markdown('<p class="hero-subtitle">Explore the world\'s prediction markets with neural search.</p>', unsafe_allow_html=True)

# 4.2 Search Section
_, mid, _ = st.columns([1, 6, 1])
with mid:
    user_news = st.text_area("Input", height=100, placeholder="Enter news, event, or intelligence to analyze...", label_visibility="collapsed", key="main_search_input")

# 4.3 Button Section
_, btn_col, _ = st.columns([1, 2, 1])
with btn_col:
    ignite_btn = st.button("🔍 Search Markets", use_container_width=True)

# 4.4 触发搜索逻辑
if ignite_btn:
    if not KEYS_LOADED:
        st.error("🔑 API Keys not found in Secrets.")
    elif not user_news:
        st.warning("Please enter intelligence to analyze.")
    else:
        st.session_state.messages = []
        st.session_state.current_market = None
        st.session_state.selected_market_index = -1
        
        with st.spinner("🔍 Analyzing news and searching Polymarket..."):
            matches, keyword = search_with_exa_optimized(user_news)
        
        st.session_state.last_search_query = keyword
        st.session_state.search_results = matches
        
        if matches:
            st.session_state.show_market_selection = True
            st.rerun()
        else:
            st.error("❌ No relevant prediction markets found. Try a different query.")
            st.session_state.show_market_selection = False

# ================= 🗳️ 5. MARKET SELECTION INTERFACE =================

if st.session_state.show_market_selection and st.session_state.search_results:
    st.markdown("---")
    
    # 显示搜索摘要
    with st.expander("🔎 Search Summary", expanded=True):
        st.info(f"""
        **Search Query:** {st.session_state.last_search_query}
        
        **Found Markets:** {len(st.session_state.search_results)} relevant prediction markets
        
        **Relevance Scoring:**
        - 🟢 High (>15): Directly related to core entities
        - 🟡 Medium (10-15): Partially related
        - 🔴 Low (5-10): Weakly related
        """)
    
    st.markdown(f"""
    <div class="selection-container">
        <h3 style="color: #e5e7eb; margin-bottom: 5px;">📊 Select a Market for Analysis</h3>
        <p style="color: #9ca3af; margin-bottom: 25px;">Markets sorted by relevance to your news:</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 显示市场列表
    for idx, market in enumerate(st.session_state.search_results):
        relevance_score = market.get('relevance_score', 0)
        
        # 确定相关性标签
        if relevance_score > 15:
            relevance_class = "relevance-high"
            relevance_label = "🟢 High"
        elif relevance_score > 10:
            relevance_class = "relevance-medium"
            relevance_label = "🟡 Medium"
        else:
            relevance_class = "relevance-low"
            relevance_label = "🔴 Low"
        
        col1, col2 = st.columns([4, 1])
        
        with col1:
            is_selected = (st.session_state.selected_market_index == idx)
            card_class = "market-selection-card selected" if is_selected else "market-selection-card"
            
            st.markdown(f"""
            <div class="{card_class}">
                <div style="font-size: 1.1rem; color: #e5e7eb; font-weight: 500; margin-bottom: 8px;">
                    {market['title']}
                    <span class="relevance-badge {relevance_class}">{relevance_label}</span>
                </div>
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <span style="color: #4ade80; font-weight: 600;">{market['odds']}</span>
                        <span style="color: #9ca3af; margin-left: 15px;">Volume: ${market['volume']:,.0f}</span>
                        <span style="color: #9ca3af; margin-left: 15px;">Score: {relevance_score}</span>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            if st.button(f"Select", key=f"select_{idx}", use_container_width=True):
                analyze_selected_market(idx, user_news)
                st.rerun()
    
    # 如果没有找到想要的市场
    st.markdown("""
    <div style="text-align: center; margin-top: 30px; padding: 20px; background: rgba(255,255,255,0.03); border-radius: 10px;">
        <p style="color: #9ca3af; margin-bottom: 10px;">Don't see the market you're looking for?</p>
        <p style="color: #ef4444; font-size: 0.9rem;">Try refining your search query or check the trending markets below.</p>
    </div>
    """, unsafe_allow_html=True)

# ================= 🗣️ 6. CHAT INTERFACE =================

if not st.session_state.show_market_selection and st.session_state.messages:
    st.markdown("---")
    
    if st.session_state.current_market:
        m = st.session_state.current_market
        relevance_score = m.get('relevance_score', 0)
        
        # 相关性指示器
        if relevance_score > 15:
            relevance_indicator = "🟢 Highly Relevant"
        elif relevance_score > 10:
            relevance_indicator = "🟡 Moderately Relevant"
        else:
            relevance_indicator = "🔴 Weakly Relevant"
        
        st.markdown(f"""
        <div class="market-card">
            <div style="font-size:0.9rem; color:#9ca3af; margin-bottom:5px;">SELECTED MARKET • {relevance_indicator}</div>
            <div style="font-size:1.2rem; color:#e5e7eb; margin-bottom:10px; font-weight:bold;">{m['title']}</div>
            <div style="display:flex; justify-content:space-between; align-items:flex-end;">
                <div>
                    <div style="font-family:'Plus Jakarta Sans'; color:#4ade80; font-size:1.8rem; font-weight:700;">{m['odds']}</div>
                    <div style="color:#9ca3af; font-size:0.8rem;">Implied Probability</div>
                </div>
                <div style="text-align:right;">
                    <div style="color:#e5e7eb; font-weight:600; font-size:1.2rem;">${m['volume']:,.0f}</div>
                    <div style="color:#9ca3af; font-size:0.8rem;">Volume</div>
                </div>
            </div>
            <div style="margin-top:10px; padding-top:10px; border-top:1px solid #374151; font-size:0.8rem; text-align:right;">
                <a href="https://polymarket.com/event/{m['slug']}" target="_blank" style="color:#ef4444; text-decoration:none;">View on Polymarket ↗</a>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    for i, msg in enumerate(st.session_state.messages):
        if i == 0: continue 
        
        with st.chat_message(msg["role"], avatar="🕵️‍♂️" if msg["role"] == "assistant" else "👤"):
            if i == 1:
                st.markdown(f"<div style='border-left:3px solid #dc2626; padding-left:15px;'>{msg['content']}</div>", unsafe_allow_html=True)
            else:
                st.write(msg["content"])

    if prompt := st.chat_input("Ask a follow-up question or search for a new topic..."):
        with st.chat_message("user", avatar="👤"):
            st.write(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        is_search = check_search_intent(prompt, st.session_state.current_market)
        
        if is_search:
            st.session_state.show_market_selection = False
            st.session_state.current_market = None
            st.session_state.messages = []
            
            with st.chat_message("assistant", avatar="🕵️‍♂️"):
                st.write(f"🔍 Searching for new markets related to: **{prompt}**")
                
                with st.spinner("Scanning Polymarket..."):
                    matches, keyword = search_with_exa_optimized(prompt)
                
                if matches:
                    st.session_state.search_results = matches
                    st.session_state.last_search_query = keyword
                    st.session_state.show_market_selection = True
                    st.success(f"Found {len(matches)} markets. Please select one to analyze.")
                else:
                    st.warning("No markets found. Try a different search query.")
                    
            st.rerun()
            
        else:
            with st.chat_message("assistant", avatar="🕵️‍♂️"):
                with st.spinner("Analyzing follow-up..."):
                    response = stream_chat_response(
                        st.session_state.messages, 
                        st.session_state.current_market,
                        prompt
                    )
                    st.write(response)
            st.session_state.messages.append({"role": "assistant", "content": response})
        
        st.rerun()

# ================= 📉 7. BOTTOM SECTION: TOP 12 MARKETS =================

st.markdown("---")
top10_markets = fetch_top_10_markets()

if top10_markets:
    cards_html = "".join([f"""
    <a href="https://polymarket.com/event/{m['slug']}" target="_blank" class="market-item">
        <div class="m-title" title="{m['title']}">{m['title']}</div>
        <div class="m-odds">
            <span class="tag-yes">Yes {m['yes']}¢</span>
            <span class="tag-no">No {m['no']}¢</span>
        </div>
    </a>""" for m in top10_markets])

    final_html = f"""
    <div class="top10-container">
        <div class="top10-header">Trending on Polymarket (Top 12)</div>
        <div class="top10-grid">{cards_html}</div>
    </div>
    """
    
    st.markdown(final_html, unsafe_allow_html=True)
else:
    st.markdown("""
    <div style="text-align:center; margin-top:50px; color:#666;">
        Connecting to Prediction Markets...
    </div>
    """, unsafe_allow_html=True)

# ================= 👇 8. 底部协议与说明 =================
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown("""
<style>
    div.row-widget.stRadio > div { justify-content: center; }
    .protocol-container {
        font-family: 'Inter', sans-serif;
        color: #cbd5e1; font-size: 0.95rem; line-height: 1.8;
        margin-top: 20px; text-align: center; display: flex; flex-direction: column; align-items: center;
    }
    .protocol-step {
        margin-bottom: 25px; padding: 15px 20px; border-radius: 12px;
        background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.05);
        max-width: 700px; width: 100%; transition: all 0.3s;
    }
    .protocol-step:hover { background: rgba(255, 255, 255, 0.05); border-color: rgba(255, 255, 255, 0.1); }
    .protocol-title {
        font-weight: 700; color: #ef4444; font-size: 1rem; letter-spacing: 0.5px;
        text-transform: uppercase; display: block; margin-bottom: 8px;
    }
    .credits-section {
        text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #334155;
        color: #64748b; font-size: 0.85rem; font-family: monospace;
    }
    .credits-highlight { color: #94a3b8; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

with st.expander("Operational Protocol & System Architecture"):
    lang_mode = st.radio("Language", ["EN", "CN"], horizontal=True, label_visibility="collapsed")
    st.markdown("<br>", unsafe_allow_html=True)
    if lang_mode == "EN":
        st.markdown("""
        <div class="protocol-container">
            <div class="protocol-step"><span class="protocol-title">1. Entity Extraction (Intelligence)</span>Gemini extracts core entities (Tesla, Musk, FSD) and ranks by importance.</div>
            <div class="protocol-step"><span class="protocol-title">2. Semantic Search (Mapping)</span>Exa.ai searches with prioritized queries based on entity relevance.</div>
            <div class="protocol-step"><span class="protocol-title">3. Relevance Scoring (Filtering)</span>Markets are scored by entity match and sorted for optimal selection.</div>
        </div>""", unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="protocol-container">
            <div class="protocol-step"><span class="protocol-title">1. 实体提取 (Entity Extraction)</span>Gemini提取核心实体（特斯拉、马斯克、FSD）并按重要性排序。</div>
            <div class="protocol-step"><span class="protocol-title">2. 语义搜索 (Semantic Search)</span>Exa.ai根据实体相关性使用优先级查询进行搜索。</div>
            <div class="protocol-step"><span class="protocol-title">3. 相关性评分 (Relevance Scoring)</span>根据实体匹配度对市场进行评分和排序。</div>
        </div>""", unsafe_allow_html=True)
    st.markdown("""
    <div class="credits-section">
        ENHANCED SEMANTIC SEARCH POWERED BY<br>
        <span class="credits-highlight">Gemini Entity Extraction</span> & <span class="credits-highlight">Exa.ai Neural Search</span><br><br>
        Data Stream: Polymarket Gamma API
    </div>""", unsafe_allow_html=True)
