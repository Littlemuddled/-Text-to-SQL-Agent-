from fastapi import FastAPI

from app.api.routers.chat_router import chat_router
from app.core.lifespan import lifespan
from app.core.middleware import RequestIDMiddleware
import app.core.logging  # 初始化日志

app = FastAPI(lifespan=lifespan)

app.add_middleware(RequestIDMiddleware)
app.include_router(chat_router)


