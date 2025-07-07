import os
import requests
from typing import List, Optional
import time
from zhipuai import ZhipuAI
import sys

class Embedding(ABC):
    """Abstract base class for embedding."""

    @abstractmethod
    def get_embedding(self, inputs: List[str]) -> List[List[float]]::
        """Create an embedding for the given text."""


class ZhipuEmbedding():
    """ZhipuAI embedding."""
    def __init__(self, api_key: str, model: str,
                 dimensions: Optional[int] = None):
        self.api_key = api_key
        self.model = model
        # self.dimensions = dimensions
        self.client = ZhipuAI(api_key=api_key)

    def get_embedding(self, inputs: List[str]) -> List[List[float]]:
        """
        调用 zhipu embedding API 获取多个文本的 embedding 向量。
        :param inputs: 输入文本列表
        :return: embedding 向量列表（每个文本一个 embedding 向量）
        """
        max_retries = 3
        for attempt in range(1, max_retries + 1):
            try:
                response = self.client.embeddings.create(
                    model=self.model,  # 可根据实际模型名调整
                    input=inputs
                )
                # 假设返回格式为 { "data": [ { "embedding": [...] }, ... ] }
                embeddings = [item.embedding for item in response.data]
                return embeddings
            except Exception as e:
                if attempt == max_retries:
                    print(f"\nZhipuEmbedding【{self.model}】发生异常：{str(e)}")
                    raise RuntimeError(f"Error creating embeddings: {e}") from e
                time.sleep(1)

class HuggingFaceEmbedding():
    """ZhipuAI embedding."""
    def __init__(self, api_key: str, model: str,
                 dimensions: Optional[int] = None):
        self.api_key = api_key
        self.model = model
        # self.dimensions = dimensions
        self.client = ZhipuAI(api_key=api_key)

if __name__ == "__main__":
    embedder = ZhipuEmbedding("073d217ca5d4443c8a211f5b6501b2fe.w0QrTfnolcSOiY2o", "embedding-3")
    inputs = [
        "美食非常美味，服务员也很友好。",
        "这部电影既刺激又令人兴奋。",
        "阅读书籍是扩展知识的好方法。"
    ]
    try:
        embeddings = embedder.get_embedding(inputs)
        for i, emb in enumerate(embeddings):
            print(f"Embedding for '{inputs[i]}':\n{emb}\n")
    except Exception as e:
        print(f"调用失败: {e}")
