# from langchain_huggingface import HuggingFaceEndpointEmbeddings
#
# from app.config.app_config import EmbeddingConfig, app_config
#
#
# class EmbeddingClientManager:
#     def __init__(self, config: EmbeddingConfig):
#         self.config = config
#         self.client: HuggingFaceEndpointEmbeddings | None = None
#
#     def init(self):
#         self.client = HuggingFaceEndpointEmbeddings(model=f"http://{self.config.host}:{self.config.port}")
#
#
# embedding_client_manager = EmbeddingClientManager(app_config.embedding)
#
# if __name__ == '__main__':
#     client = EmbeddingClientManager(app_config.embedding)
#     client.init()
#     query = client.client.embed_query("hello world")
#     print(len(query))
#     print(query)




import httpx

from app.config.app_config import EmbeddingConfig, app_config


class TEIEmbeddings:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        response = httpx.post(
            f"{self.base_url}/embed",
            json={"inputs": texts},
            timeout=120,
        )
        response.raise_for_status()
        return response.json()

    def embed_query(self, text: str) -> list[float]:
        vectors = self.embed_documents([text])
        return vectors[0]

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                f"{self.base_url}/embed",
                json={"inputs": texts},
            )
            response.raise_for_status()
            return response.json()

    async def aembed_query(self, text: str) -> list[float]:
        vectors = await self.aembed_documents([text])
        return vectors[0]


class EmbeddingClientManager:
    def __init__(self, config: EmbeddingConfig):
        self.config = config
        self.client: TEIEmbeddings | None = None

    def init(self):
        self.client = TEIEmbeddings(
            base_url=f"http://{self.config.host}:{self.config.port}"
        )


embedding_client_manager = EmbeddingClientManager(app_config.embedding)


if __name__ == "__main__":
    client = EmbeddingClientManager(app_config.embedding)
    client.init()

    if client.client is None:
        raise RuntimeError("Embedding client has not been initialized")

    query = client.client.embed_query("hello world")
    print(len(query))
    print(query[:10])