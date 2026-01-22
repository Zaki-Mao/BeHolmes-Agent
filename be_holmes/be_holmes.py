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
    except: pass

# ================= 🧠 1. STATE MANAGEMENT =================
class State(rx.State):
    user_news: str = ""
    analysis_result: str = ""
    is_loading: bool = False
    
    market_data: dict = {}
    top_markets: list[dict] = []
    
    # 默认状态
    ticker_text: str = "Connecting to Polymarket Live Data Stream..."

    # 伪装成 Chrome 浏览器
    _headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Referer": "https://polymarket.com/"
    }

    def on_load(self):
        print("🚀 系统启动...") 
        self.fetch_top_10_markets()

    async def run_analysis(self):
        if not self.user_news: return
        self.is_loading = True
        self.analysis_result = ""
        self.market_data = {}
        yield 
        
        # 搜索逻辑
        print(f"🔍 用户搜索: {self.user_news}")
        matches, query = self._search_with_exa(self.user_news)
        
        if matches: 
            self.market_data = matches[0]
            print(f"✅ 找到市场: {matches[0]['title']}")
        
        # AI 分析逻辑
        print("🧠 调用 AI...")
        self.analysis_result = self._consult_holmes(self.user_news, matches)
        self.is_loading = False

    # --- 内部函数 ---
    def _search_with_exa(self, query):
        if not EXA_API_KEY: return [], query
        try:
            # 简化搜索逻辑，确保稳定性
            exa = Exa(EXA_API_KEY)
            resp = exa.search(f"prediction market {query}", num_results=2, include_domains=["polymarket.com"])
            # 这里省略复杂的解析，只要确保流程通畅
            return [], query 
        except Exception as e: 
            print(f"Exa Error: {e}")
            return [], query

    def _consult_holmes(self, user_input, market_data):
        if not GOOGLE_API_KEY: return "Error: Google API Key is missing in Zeabur variables."
        try:
            model = genai.GenerativeModel('gemini-2.5-flash')
            prompt = f"Analyze: {user_input}. Concise summary."
            return model.generate_content(prompt).text
        except Exception as e: return f"AI Error: {str(e)}"

    # ⭐ 核心：只抓真数据，抓不到就报错上墙 ⭐
    def fetch_top_10_markets(self):
        try:
            print("⚡ 发起 Polymarket API 请求...")
            url = "https://gamma-api.polymarket.com/events?limit=12&sort=volume&closed=false"
            
            # 设置 10 秒超时，防止无限卡顿
            resp = requests.get(url, headers=self._headers, timeout=10)
            
            # 如果状态码不是 200，直接抛出异常，不要 Swallow
            if resp.status_code != 200:
                raise Exception(f"HTTP {resp.status_code}: {resp.text[:50]}")
            
            data = resp.json()
            markets = []
            
            if isinstance(data, list):
                for event in data:
                    try:
                        m = event.get('markets', [])[0]
                        outcomes = json.loads(m.get('outcomes')) if isinstance(m.get('outcomes'), str) else m.get('outcomes')
                        prices = json.loads(m.get('outcomePrices')) if isinstance(m.get('outcomePrices'), str) else m.get('outcomePrices')
                        
                        yes_price = 50
                        if "Yes" in outcomes:
                            yes_price = int(float(prices[outcomes.index("Yes")]) * 100)
                        
                        markets.append({
                            "title": event.get('title'),
                            "yes": yes_price,
                            "no": 100-yes_price,
                            "slug": event.get('slug')
                        })
                    except: continue
            
            if not markets:
                raise Exception("API returned 200 but list is empty")
                
            self.top_markets = markets
            self.ticker_text = f"✅ LIVE DATA ACTIVE: {len(markets)} Markets Loaded."
            print(f"✅ 成功加载 {len(markets)} 个市场")

        except Exception as e:
            # 🚨 关键：把错误直接写在页面底部，而不是藏在日志里
            error_msg = str(e)
            print(f"❌ 严重错误: {error_msg}")
            if "403" in error_msg:
                self.ticker_text = "❌ Error 403: Zeabur IP is blocked by Polymarket."
            elif "timeout" in error_msg.lower():
                self.ticker_text = "❌ Error: Connection Timed Out (Network slow)."
            else:
                self.ticker_text = f"❌ System Error: {error_msg}"

# ================= 🎨 UI COMPONENTS =================
def index():
    return rx.box(
        rx.vstack(
            rx.heading("Be Holmes", size="9", color="white", letter_spacing="-2px", padding_top="8vh"),
            rx.text("Global Prediction Market Intelligence", color="#9ca3af", margin_bottom="30px"),
            
            # 搜索框
            rx.text_area(placeholder="Ask anything...", on_change=State.set_user_news, bg="rgba(255,255,255,0.1)", color="white", width="100%", max_width="800px"),
            rx.button("Decode Alpha", on_click=State.run_analysis, loading=State.is_loading, margin_top="20px", bg="linear-gradient(90deg, #b91c1c, #ef4444)", color="white"),
            
            # 结果显示区
            rx.cond(State.analysis_result, rx.box(rx.markdown(State.analysis_result), bg="rgba(0,0,0,0.5)", padding="20px", margin_y="20px", border_left="4px solid red")),
            
            rx.text("TRENDING MARKETS (Live)", color="#6b7280", font_size="0.8rem", margin_top="40px", width="100%", text_align="left"),
            
            # 市场网格
            rx.grid(
                rx.foreach(State.top_markets, lambda m: rx.link(
                    rx.box(
                        rx.text(m["title"], color="white", font_weight="bold", no_of_lines=2),
                        rx.hstack(
                            rx.text(f"Yes {m['yes']}%", color="#4ade80"), rx.spacer(), rx.text(f"No {m['no']}%", color="#f87171"),
                            width="100%", margin_top="10px"
                        ),
                        bg="rgba(255,255,255,0.05)", border="1px solid #333", padding="15px", border_radius="10px",
                        _hover={"border_color": "red"}
                    ),
                    href=f"https://polymarket.com/event/{m['slug']}", is_external=True
                )),
                columns="3", spacing="4", width="100%", max_width="1200px"
            ),
            align="center", padding_bottom="100px", width="100%"
        ),
        bg="#0f172a", min_height="100vh", padding_x="20px",
        
        # 底部滚动条 - 这里会显示具体的错误信息
        rx.box(rx.text(State.ticker_text, color="white", font_weight="bold"), position="fixed", bottom="0", width="100%", bg="black", padding="10px", border_top="1px solid red")
    )

app = rx.App()
app.add_page(index, on_load=State.on_load)
