config = rx.Config(
    app_name="be_holmes",
    cors_allowed_origins=["*"],
    # 🌟 核心：大脑在 8000 端口
    api_url="https://beholmes-backend.zeabur.app", 
    # 🌟 核心：脸面在 3000 端口
    deploy_url="https://beholmes.zeabur.app",
)
