import google.generativeai as genai
import os

# ================= 🔧 必须配置代理 =================
# 确保端口和你 app.py 里写的一样 (比如 7890 或 10809)
os.environ["HTTP_PROXY"] = "http://127.0.0.1:7890"
os.environ["HTTPS_PROXY"] = "http://127.0.0.1:7890"

# ================= 🔑 填入你的 Key =================
api_key = "AIzaSyCRs8AspX9LJkbWk6WVTIGrq0FFDeqRFCc"  # ⚠️ 把你的 Key 粘贴在这里！
genai.configure(api_key=api_key)

print("正在连接 Google 获取模型列表...")

try:
    # 列出所有可用模型
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"✅ 可用模型: {m.name}")
except Exception as e:
    print(f"❌ 出错啦: {e}")