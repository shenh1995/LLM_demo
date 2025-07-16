import os
import json
import joblib
import numpy as np
import sys
from utils import tokenize_text
from rank_bm25 import BM25Okapi


# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, backend_dir)
from embedding.embedding import HuggingFaceEmbedding


# 尝试导入可选依赖
try:
    import utils
    from utils import show
    SHOW_AVAILABLE = True
except ImportError:
    print("⚠️  utils 模块不可用，使用print替代show函数")
    SHOW_AVAILABLE = False
    def show(obj):
        print(obj)

try:
    from embedding.embedding import ZhipuEmbedding, HuggingFaceEmbedding
    EMBEDDING_AVAILABLE = True
except ImportError:
    print("⚠️  embedding 模块不可用")
    EMBEDDING_AVAILABLE = False
    ZhipuEmbedding = None
    HuggingFaceEmbedding = None

# 设置环境变量
os.environ['ENABLE_TOKENIZER_COUNT'] = '1'

# 检查必要的文件是否存在
if not os.path.exists('../cache/column_questions.json'):
    print(f"❌ 文件不存在: ../cache/column_questions.json")
    exit(1)

# 加载column_questions
with open('../cache/column_questions.json', 'r', encoding='utf-8') as json_file:
    column_questions = json.load(json_file)

# 加载schema
if not os.path.exists('../cache/schema.json'):
    print("❌ 文件不存在: ../cache/schema.json")
    exit(1)

with open('../cache/schema.json', 'r', encoding='utf-8') as json_file:
    schema = json.load(json_file)

texts = []
for t in schema:
    table_name = t['table_name']
    for c in t['columns']:
        key = f"{table_name}.{c['name']}"
        if key in column_questions:
            text = "\n".join([q for q in column_questions[key]])
            texts.append(text)
        else:
            print(f"⚠️  未找到字段的问题: {key}")

show(len(texts))


try:
    embedder = HuggingFaceEmbedding(model="shibing624/text2vec-base-chinese")

    em = embedder.get_embedding(texts)
    vectors = np.array(em)
    np.save("../cache/column_vectors.npy", vectors)
    show(vectors[0])
    
    # 验证保存的向量
    try:
        loaded_vectors = np.load("../cache/column_vectors.npy")
        show(loaded_vectors[0])
        print(f"✅ 成功保存了 {len(loaded_vectors)} 个向量")
    except Exception as e:
        print(f"❌ 加载向量失败: {e}")
        
except Exception as e:
    print(f"❌ 创建embedding失败: {e}")
    exit(1)

texts = []
cols = []
for col, qs in column_questions.items():
    # db_name, table_name, column_name = col.split(".")
    # c = config.column_index[db_name+"."+table_name][column_name]
    cols.append(col)
    texts.append((
        # f"{c['desc']}" +
        # (f": {c['remarks']}\n" if c['remarks'] != "" else "\n") +
        "\n".join(qs)
    ))
corpus = [tokenize_text(doc) for doc in texts]
bm25 = BM25Okapi(corpus)

doc_scores = bm25.get_scores(tokenize_text("股票代码"))
column_question_scores = [(i, text, score) for i, (text, score) in enumerate(zip(texts, doc_scores))]
column_question_scores = sorted(column_question_scores, key=lambda x: x[2], reverse=True)
show(column_question_scores[:3])

joblib.dump(bm25, "../cache/column_bm25.pkl", compress=3)