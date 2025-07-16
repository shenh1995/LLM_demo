import json
import jieba

def show(obj):
    """
    打印对象的 JSON 表示。
    """
    if isinstance(obj, dict):
        print(json.dumps(obj, ensure_ascii=False, indent=2))
    elif isinstance(obj, list):
        print(json.dumps(obj, ensure_ascii=False, indent=2))
    elif isinstance(obj, str):
        if str(obj).startswith(('{', '[')):
            try:
                o = json.loads(str(obj))
                print(json.dumps(o, ensure_ascii=False, indent=2))
            except Exception:
                print(obj)
        else:
            print(obj)
    elif isinstance(obj, (int, float)):
        print(obj)
    else:
        print(obj)
    
def tokenize_text(text: str) -> list[str]:
    """
    将文本分词并返回分词结果。
    
    Args:
        text (str): 需要分词的文本
    
    Returns:
        list[str]: 分词结果
    """
    # 分词并过滤停用词
    stop_words = {
        '的', '了', '和', '与', '及', '或', '在', '是', '为', '以', '对', '等', '将', '由',
        # '年', '月', '日', '时', '分', '秒', '个', '名', '无', '前', '后', '上', '下', 
        # '左', '右', '中', '内', '外', '其他', '其它', '什么', '多少'
    }
    return [word for word in jieba.cut(text) if word not in stop_words and word.strip()]
