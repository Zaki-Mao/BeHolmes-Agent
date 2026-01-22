import reflex as rx
import requests
import json
import google.generativeai as genai
import re
import os
from exa_py import Exa

# ================= 🔐 0. KEY CONFIG =================
EXA_API_KEY = os.getenv("EXA_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if GOOGLE_API_KEY:
    try:
        genai.configure(api_key=GOOGLE_API_KEY)
    except Exception as e:
        print(f"⚠️ Google AI Config Warning: {e}")

# ================= 🧠 1. STATE MANAGEMENT =================
class State(rx.State):
    user_news: str = ""
    analysis_result: str = ""
    is_loading: bool = False
    
    market_data: dict = {}
    top_markets: list[dict] = []
    
    ticker_text: str = "Market Intelligence System Online /// Welcome to Be Holmes ///"

    # --- 核心修复：伪装成浏览器的请求头 ---
    _headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Referer": "https://polymarket.com/"
    }

    def on_load(self):
        print("🚀 系统启动：正在获取 Top 10 市场数据...")
        self.fetch_top_10_markets()

    async def run_analysis(self):
        if not self.user_news:
            return
        
        self.is_loading = True
        self.analysis_result = ""
        self.market_data = {}
        yield 

        print(f"🔍 开始搜索 Exa: {self.user_news}")
        matches, query = self._search_with_exa(self.user_news)
        
        if matches:
            self.market_data = matches[0]
        
        print("🧠 开始 AI 分析...")
        self.analysis_result = self._consult_holmes(self.user_news, matches)
        
        self.is_loading = False
        print("✅ 分析完成")

    # --- 内部函数 ---

    def _generate_english_keywords(self, text):
        try:
            model = genai.GenerativeModel('gemini-2.5-flash')
            prompt = f"""Task: Extract English search keywords for Polymarket. Input: "{text}". Output: Keywords only."""
            resp = model.generate_content(prompt)
            return resp.text.strip()
        except: return text

    def _search_with_exa(self, query):
        if not EXA_API_KEY: return [], query
        try:
            search_query = self._generate_english_keywords(query)
            exa = Exa(EXA_API_KEY)
            search_response = exa.search(
                f"prediction market about {search_query}",
                num_results=4, type="neural", include_domains=["polymarket.com"]
            )
            markets_found = []
            seen_ids = set()
            if search_response and search_response.results:
                for result in search_response.results:
                    match = re.search(r'polymarket\.com/(?:event|market)/([^/]+)', result.url)
                    if match:
                        slug = match.group(1)
                        if slug not in seen_ids:
                            # 传递请求头
                            data = self._fetch_poly_details(slug)
                            if data:
                                markets_found.extend(data)
                                seen_ids.add(slug)
            return markets_found, search_query
        except Exception as e:
            print(f"Exa Error: {e}")
            return [], query

    def _fetch_poly_details(self, slug):
        try:
            url = f"https://gamma-api.polymarket.com/events?slug={slug}"
            # ✅ 修复点：加入 headers
            resp = requests.get(url, headers=self._headers, timeout=5).json()
            valid = []
            if isinstance(resp, list) and resp:
                for m in resp[0].get('markets', [])[:2]:
                    p = self._normalize_data(m)
                    if p: valid.append(p)
            return valid
        except Exception as e: 
            print(f"Details Fetch Error: {e}")
            return []

    def _normalize_data(self, m):
        try:
            if m.get('closed') is True: return None
            outcomes = json.loads(m.get('outcomes')) if isinstance(m.get('outcomes'), str) else m.get('outcomes')
            prices = json.loads(m.get('outcomePrices')) if isinstance(m.get('outcomePrices'), str) else m.get('outcomePrices')
            
            odds_display = "N/A"
            if outcomes and prices:
                odds_display = f"{outcomes[0]}: {float(prices[0])*100:.1f}%"
                
            return {
                "title": m.get('question', 'Unknown'),
                "odds": odds_display,
                "volume": float(m.get('volume', 0)),
                "slug": m.get('slug', '') or m.get('market_slug', '')
            }
        except: return None

    def _consult_holmes(self, user_input, market_data):
        if not GOOGLE_API_KEY: return "AI Key Missing."
        try:
            model = genai.GenerativeModel('gemini-2.5-flash')
            lang_instruction = "Respond in CHINESE" if any('\u4e00' <= char <= '\u9fff' for char in user_input) else "Respond in ENGLISH"
            
            market_context = f"Target: {market_data[0]['title']} | Odds: {market_data[0]['odds']}" if market_data else "No specific market."
            
            prompt = f"""
            You are **Be Holmes**, a rational Macro Hedge Fund Manager.
            [Intel]: "{user_input}"
            [Market Data]: {market_context}
            {lang_instruction}
            **MISSION: DECODE ALPHA.**
            Analysis Framework: 1. Priced-in Check 2. Bluff vs Reality 3. Verdict.
            Output as a concise professional briefing.
            """
            return model.generate_content(prompt).text
        except Exception as e: return f"AI Error: {e}"

    def fetch_top_10_markets(self):
        try:
            url = "https://gamma-api.polymarket.com/events?limit=12&sort=volume&closed=false"
            # ✅ 修复点：加入 headers 和 打印日志
            print("⚡ 正在请求 Polymarket API...")
            resp = requests.get(url, headers=self._headers, timeout=10).json()
            
            markets = []
            if isinstance(resp, list):
                for event in resp:
                    try:
                        markets_raw = event.get('markets', [])
                        if not markets_raw: continue
                        m = markets_raw[0] 
                        outcomes = json.loads(m.get('outcomes')) if isinstance(m.get('outcomes'), str) else m.get('outcomes')
                        prices = json.loads(m.get('outcomePrices')) if isinstance(m.get('outcomePrices'), str) else m.get('outcomePrices')
                        
                        yes_price = 50
                        no_price = 50
                        if outcomes and "Yes" in outcomes:
                            idx = outcomes.index("Yes")
                            yes_price = int(float(prices[idx]) * 100)
                            no_price = 100 - yes_price
                        
                        markets.append({
                            "title": event.get('title'),
                            "yes": yes_price,
                            "no": no_price,
                            "slug": event.get('slug')
                        })
                    except: continue
            self.top_markets = markets
            print(f"✅ 成功加载 {len(markets)} 个市场")
        except Exception as e: 
            print(f"❌ Top 10 加载失败: {e}")
            pass

# ================= 🎨 2. UI COMPONENTS =================

def hero_section():
    return rx.vstack(
        rx.heading("Be Holmes", size="9", color="white", letter_spacing="-2px", text_align="center"),
        rx.text("Explore the world's prediction markets with neural search.", color="#9ca3af", font_size="1.1rem"),
        padding_top="8vh",
        margin_bottom="50px",
        align="center"
    )

def search_section():
    return rx.vstack(
        rx.text_area(
            placeholder="Search for a market, region or event...",
            value=State.user_news,
            on_change=State.set_user_news,
            bg="rgba(31, 41, 55, 0.6)",
            color="white",
            border="1px solid #374151",
            border_radius="16px",
            min_height="100px",
            width="100%",
            max_width="800px",
            _focus={"border_color": "#ef4444", "box_shadow": "0 0 15px rgba(220, 38, 38, 0.3)"},
        ),
        rx.button(
            "Decode Alpha",
            on_click=State.run_analysis,
            loading=State.is_loading,
            bg="linear-gradient(90deg, #7f1d1d 0%, #dc2626 50%, #7f1d1d 100%)",
            color="white",
            border_radius="50px",
            padding="20px 50px",
            font_weight="600",
            _hover={"transform": "scale(1.05)", "cursor": "pointer"},
            margin_top="20px"
        ),
        align="center",
        width="100%"
    )

def result_card():
    return rx.cond(
        State.market_data,
        rx.box(
            rx.vstack(
                rx.text(State.market_data["title"], font_size="1.2rem", color="#e5e7eb", font_weight="bold"),
                rx.hstack(
                    rx.vstack(
                        rx.text(State.market_data["odds"], font_size="1.8rem", color="#4ade80", font_weight="bold"),
                        rx.text("Implied Probability", font_size="0.8rem", color="#9ca3af"),
                        align="start"
                    ),
                    rx.spacer(),
                    rx.vstack(
                        rx.text(f"${State.market_data['volume']}", font_size="1.2rem", color="#e5e7eb"),
                        rx.text("Volume", font_size="0.8rem", color="#9ca3af"),
                        align="end"
                    ),
                    width="100%"
                ),
                width="100%"
            ),
            bg="rgba(17, 24, 39, 0.7)",
            border="1px solid #374151",
            border_radius="12px",
            padding="20px",
            margin_y="20px",
            max_width="800px",
            backdrop_filter="blur(8px)"
        )
    )

def analysis_report():
    return rx.cond(
        State.analysis_result,
        rx.box(
            rx.markdown(State.analysis_result),
            bg="transparent",
            border_left="3px solid #dc2626",
            padding="15px 20px",
            color="#d1d5db",
            line_height="1.6",
            margin_y="20px",
            max_width="800px"
        )
    )

def market_grid():
    return rx.vstack(
        rx.text("TRENDING ON POLYMARKET (Top 12)", color="#9ca3af", font_size="0.9rem", border_left="3px solid #dc2626", padding_left="10px"),
        rx.grid(
            rx.foreach(
                State.top_markets,
                lambda m: rx.link(
                    rx.box(
                        rx.text(m["title"], class_name="m-title", color="#e5e7eb", font_weight="500", no_of_lines=2),
                        rx.hstack(
                            rx.text(f"Yes {m['yes']}¢", bg="rgba(6, 78, 59, 0.4)", color="#4ade80", padding="2px 8px", border_radius="4px"),
                            rx.text(f"No {m['no']}¢", bg="rgba(127, 29, 29, 0.4)", color="#f87171", padding="2px 8px", border_radius="4px"),
                            margin_top="auto"
                        ),
                        bg="rgba(17, 24, 39, 0.6)",
                        border="1px solid #374151",
                        border_radius="8px",
                        padding="15px",
                        height="120px",
                        display="flex",
                        flex_direction="column",
                        justify_content="space-between",
                        backdrop_filter="blur(5px)",
                        _hover={"border_color": "#ef4444", "bg": "rgba(31, 41, 55, 0.9)", "transform": "translateY(-2px)"},
                        transition="all 0.2s"
                    ),
                    href=f"https://polymarket.com/event/{m['slug']}",
                    is_external=True,
                    text_decoration="none"
                )
            ),
            columns="3",
            spacing="4",
            width="100%"
        ),
        width="100%",
        max_width="1200px",
        margin_top="60px",
        padding_x="20px"
    )

def ticker_bar():
    return rx.box(
        rx.box(
            rx.text(State.ticker_text, class_name="ticker-text"),
            class_name="ticker-wrap"
        ),
        position="fixed",
        bottom="0",
        left="0",
        width="100%",
        bg="#0f172a",
        border_top="1px solid #dc2626",
        color="#e2e8f0",
        padding="8px 0",
        z_index="9999",
        overflow="hidden",
        white_space="nowrap"
    )

def index():
    return rx.box(
        rx.box(
            rx.vstack(
                hero_section(),
                search_section(),
                result_card(),
                analysis_report(),
                market_grid(),
                rx.box(height="100px"),
                align="center",
                width="100%",
                padding_bottom="50px"
            ),
            bg="rgba(0, 0, 0, 0.8)", 
            min_height="100vh",
            width="100%",
            padding_top="20px"
        ),
        ticker_bar(),
        bg_image="url('https://upload.cc/i1/2026/01/20/s8pvXA.jpg')",
        bg_size="cover",
        bg_position="center",
        bg_attachment="fixed",
        min_height="100vh"
    )

style = """
.ticker-wrap { width: 100%; overflow: hidden; }
.ticker-text { display: inline-block; white-space: nowrap; animation: ticker 120s linear infinite; padding-left: 100%; }
@keyframes ticker { 0% { transform: translate3d(0, 0, 0); } 100% { transform: translate3d(-100%, 0, 0); } }
"""

app = rx.App(style={})
app.add_page(index, on_load=State.on_load)
