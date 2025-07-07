import os
import pytest
from embedding import embedding

@pytest.mark.skipif(os.getenv('ZHIPU_API_KEY') is None, reason="需要设置 ZHIPU_API_KEY 环境变量")
def test_get_zhipu_embedding_success():
    text = "测试文本"
    embedding_vec = embedding.get_zhipu_embedding(text)
    assert isinstance(embedding_vec, list)
    assert all(isinstance(x, float) for x in embedding_vec)
    assert len(embedding_vec) > 0

def test_get_zhipu_embedding_no_api_key(monkeypatch):
    monkeypatch.setenv('ZHIPU_API_KEY', '', prepend=False)
    with pytest.raises(embedding.ZhipuEmbeddingError):
        embedding.get_zhipu_embedding("test") 

