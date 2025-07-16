import os
import requests
from typing import List, Optional
import time
import sys
from abc import ABC, abstractmethod
from zhipuai import ZhipuAI
from transformers import AutoTokenizer, AutoModel
import torch


class Embedding(ABC):
    """Abstract base class for embedding."""

    @abstractmethod
    def get_embedding(self, inputs: List[str]) -> List[List[float]]:
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
        # 这行代码永远不会执行，但为了满足类型检查
        return []

class HuggingFaceEmbedding():
    """HuggingFace embedding."""
    def __init__(self, model: str,
                 dimensions: Optional[int] = None):
        self.model = model
        # self.dimensions = dimensions
        
        # 初始化tokenizer和model
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(model)
            self.model = AutoModel.from_pretrained(model)
            # 设置为评估模式
            self.model.eval()
        except Exception as e:
            raise RuntimeError(f"Failed to load model {model}: {e}")

    def get_embedding(self, inputs: List[str]) -> List[List[float]]:
        """
        使用 HuggingFace 模型获取多个文本的 embedding 向量。
        :param inputs: 输入文本列表
        :return: embedding 向量列表（每个文本一个 embedding 向量）
        """
        embeddings = []
        
        with torch.no_grad():  # 不计算梯度
            for text in inputs:
                try:
                    # 对文本进行编码
                    inputs_tensor = self.tokenizer(
                        text, 
                        return_tensors="pt", 
                        padding=True, 
                        truncation=True, 
                        max_length=512
                    )
                    
                    # 获取模型输出
                    outputs = self.model(**inputs_tensor)
                    
                    # 使用最后一层的隐藏状态的平均值作为embedding
                    # 通常使用[CLS] token的输出或者所有token的平均值
                    if hasattr(outputs, 'last_hidden_state'):
                        # 使用所有token的平均值
                        embedding = outputs.last_hidden_state.mean(dim=1).squeeze()
                    else:
                        # 如果没有last_hidden_state，尝试其他属性
                        embedding = outputs.pooler_output.squeeze()
                    
                    # 转换为Python列表
                    embedding_list = embedding.cpu().numpy().tolist()
                    embeddings.append(embedding_list)
                    
                except Exception as e:
                    print(f"处理文本时出错: {text[:50]}... - {e}")
                    # 返回零向量作为fallback
                    embedding_size = self.model.config.hidden_size if hasattr(self.model.config, 'hidden_size') else 768
                    embeddings.append([0.0] * embedding_size)
        
        # 确保返回的列表不为空
        if not embeddings:
            print("警告: 没有生成任何 embedding，返回默认向量")
            embedding_size = self.model.config.hidden_size if hasattr(self.model.config, 'hidden_size') else 768
            embeddings = [[0.0] * embedding_size] * len(inputs)
        
        return embeddings

# 帮我

if __name__ == "__main__":        
    # 测试ZhipuAI embedding
    try:
        embedder = ZhipuEmbedding("073d217ca5d4443c8a211f5b6501b2fe.w0QrTfnolcSOiY2o", "embedding-3")
        inputs = [
            "美食非常美味，服务员也很友好。",
            "这部电影既刺激又令人兴奋。",
            "阅读书籍是扩展知识的好方法。"
        ]
        embeddings = embedder.get_embedding(inputs)
        for i, emb in enumerate(embeddings):
            print(f"ZhipuAI Embedding for '{inputs[i]}':\n{emb[:5]}...\n")
    except Exception as e:
        print(f"ZhipuAI调用失败: {e}")

    # 测试HuggingFace embedding
    try:
        embedder = HuggingFaceEmbedding(model="shibing624/text2vec-base-chinese")
        inputs = [
            "美食非常美味，服务员也很友好。",
            "这部电影既刺激又令人兴奋。",
            "阅读书籍是扩展知识的好方法。"
        ]
        embeddings = embedder.get_embedding(inputs)
        for i, emb in enumerate(embeddings):
            print(f"HuggingFace Embedding for '{inputs[i]}':\n{emb[:5]}...\n")
    except Exception as e:
        print(f"HuggingFace调用失败: {e}")

