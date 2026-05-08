import asyncio

from langchain.chat_models import init_chat_model

from app.config.app_config import app_config

model_name = app_config.llm.model_name
api_key = app_config.llm.api_key
base_url = app_config.llm.base_url
model_provider = app_config.llm.model_provider

# llm = init_chat_model(model=model_name, api_key=api_key, temperature=0)

llm = init_chat_model(
    model=model_name,
    model_provider=model_provider,
    api_key=api_key,
    base_url=base_url,
    temperature=0
    # rate_limiter=rate_limiter,  # 关键步骤
)



if __name__ == '__main__':
    async def test():
        print(await llm.ainvoke("中国的首都是哪里？"))


    print(asyncio.run(test()))
