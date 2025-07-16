import json
import config
import os
import sys


current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, backend_dir)

# 确保backend目录在Python路径中
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

try:
    from models.agent import Agent
    from models.factory import ChatModelFactory
except ImportError as e:
    print(f"❌ 导入失败: {e}")
    print(f"当前Python路径: {sys.path}")
    print(f"backend目录: {backend_dir}")
    exit(1)

# 加载schema
if not os.path.exists('../cache/schema.json'):
    print("❌ 文件不存在: ../cache/schema.json")
    exit(1)

with open('../cache/schema.json', 'r', encoding='utf-8') as json_file:
    schema = json.load(json_file)

db_table = {}
for t in schema:
    db_name, table_name = t["table_name"].split(".")
    if db_name not in db_table:
        db_table[db_name] = {
            "desc": "",
            "tables": {}
        }
    all_cols = t["all_cols"]
    model = ChatModelFactory.get_default_model()
    
    if model is None:
        print("❌ 模型初始化失败")
        cols_summary = "模型初始化失败"
        token = 0
    else:
        # 构建消息
        from langchain_core.messages import HumanMessage, SystemMessage
        messages = [
            SystemMessage(content='''你善于对数据表的字段信息进行总结，把同类信息归类，比如"联系人电话、联系人传真"等总结为"联系方式如电话、传真等。
输出一段文字，不换行。"'''),
            HumanMessage(content=f"下面是一个数据表的所有表字段，请帮我为这个数据表写一段介绍，把字段信息压缩进去：\n{all_cols}")
        ]
        
        # 调用模型
        try:
            response = model.invoke(messages)
            content = response.content if hasattr(response, 'content') else str(response)
            cols_summary = str(content)  # 确保是字符串类型
            token = len(cols_summary.split())  # 简化的token计算
        except Exception as e:
            print(f"❌ 模型调用失败: {e}")
            cols_summary = f"模型调用失败: {str(e)}"
            token = 0
    
    db_table[db_name]["tables"][table_name] = {
        "desc": t["table_desc"],
        "all_cols": all_cols,
        "cols_summary": cols_summary
    }

for db_name, db in db_table.items():
    db_json = json.dumps(db, ensure_ascii=False)
    model = ChatModelFactory.get_default_model()
    
    if model is None:
        print("❌ 模型初始化失败")
        db_summary = "模型初始化失败"
        token = 0
    else:
        # 构建消息
        messages = [
            SystemMessage(content='''你善于对数据库的表信息进行总结，根据它包含的数据表和字段信息，描述这个数据库，如"本库记录了xxx；涵盖了xxx；方便用户xxx"。
输出一段文字，不换行。"'''),
            HumanMessage(content=f"下面是一个数据库的所有表和字段信息，请帮我为这个数据库写一段介绍，把表和字段信息压缩进去：\n{db_json}")
        ]
        
        # 调用模型
        try:
            response = model.invoke(messages)
            content = response.content if hasattr(response, 'content') else str(response)
            db_summary = str(content)  # 确保是字符串类型
            token = len(db_summary.split())  # 简化的token计算
        except Exception as e:
            print(f"❌ 模型调用失败: {e}")
            db_summary = f"模型调用失败: {str(e)}"
            token = 0
    
    db["desc"] = db_summary

with open("../cache/db_table.json", "w", encoding="utf-8") as f:
    json.dump(db_table, f, ensure_ascii=False, indent=2)