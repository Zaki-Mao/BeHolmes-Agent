# 1. 使用官方 Python 3.12 镜像 (解决 Pydantic 兼容性问题)
FROM python:3.12-slim

# 2. 设置工作目录
WORKDIR /app

# 3. 安装系统基础工具 + Node.js
# Reflex 需要 Node.js 来编译前端页面，这一步至关重要
RUN apt-get update && apt-get install -y \
    curl \
    unzip \
    git \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 4. 复制并安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. 复制项目所有代码
COPY . .

# 6. 构建 Reflex 前端 (生成静态文件到 .web/_static)
# 这一步会将 Python 代码编译成网页文件
RUN reflex export --frontend-only --no-zip

# 7. 暴露两个端口 (3000给网页，8000给后端API)
EXPOSE 3000
EXPOSE 8000

# 8. 启动命令 (魔法在这里)
# 同时启动：
# 1. Reflex 后端 (API服务)
# 2. Python 简易服务器 (托管生成的网页文件)
CMD ["sh", "-c", "reflex run --env prod --backend-only & python3 -m http.server 3000 --directory .web/_static"]
