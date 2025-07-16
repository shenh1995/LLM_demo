import json
import logging
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import os
import sys

# 添加 backend 目录到 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.agent import Agent, AgentConfig
from models.factory import ChatModelFactory
from utils import utils
from config import config


# 配置日志为终端输出
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()  # 输出到终端
    ]
)

# 配置日志
logger = logging.getLogger(__name__)

# 常量定义
COLUMN_LIST_MARK = "表字段信息"

def extract_last_json(text: str) -> Optional[str]:
    """从文本中提取最后一个JSON字符串"""
    import re
    # 查找最后一个JSON对象
    logger.debug(f"🔄 开始提取JSON: {text}")
    json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
    matches = re.findall(json_pattern, text)
    logger.info(f"🔄 提取JSON结果: {matches}")
    if matches:
        return matches[-1]
    return None

class VectorSearch:
    """向量搜索类"""
    
    def __init__(self, 
                 agent_decode_question=None,
                 agent_column_selector=None,
                 agent_fix_column_selection=None,
                 enable_vector_search=True,
                 get_relevant_table_columns=None,
                 print_table_column=None,
                 name="VectorSearch"):
        """
        初始化向量搜索
        
        Args:
            agent_decode_question: 问题解码代理
            agent_column_selector: 字段选择代理
            agent_fix_column_selection: 字段选择修复代理
            enable_vector_search: 是否启用向量搜索
            name: 搜索器名称
        """
        self.agent_decode_question = agent_decode_question
        self.agent_column_selector = agent_column_selector
        self.agent_fix_column_selection = agent_fix_column_selection
        self.enable_vector_search = enable_vector_search
        self.name = name
        self.get_relevant_table_columns = get_relevant_table_columns
        self.print_table_column = print_table_column
        
        # 初始化向量相关组件
        self.column_vectors = None
        self.column_vector_names = []
        self.column_bm25 = None
        
    def load_vectors(self, cache_dir: str):
        """加载向量数据"""
        try:
            # 加载列向量
            if os.path.exists(f"{cache_dir}/column_vectors.npy"):
                self.column_vectors = np.load(f"{cache_dir}/column_vectors.npy")
                
            # 加载列向量名称
            if os.path.exists(f"{cache_dir}/column_vector_names.json"):
                with open(f"{cache_dir}/column_vector_names.json", 'r', encoding='utf-8') as f:
                    self.column_vector_names = json.load(f)
                    
            # 加载BM25模型
            if os.path.exists(f"{cache_dir}/column_bm25.pkl"):
                import joblib
                self.column_bm25 = joblib.load(f"{cache_dir}/column_bm25.pkl")
                
        except Exception as e:
            logger.warning(f"加载向量数据失败: {e}")
    
    
    def validate_column_filter(self, column_filter: Dict[str, Any]) -> str:
        """
        验证字段过滤器
        
        Args:
            column_filter: 字段过滤器
            
        Returns:
            错误信息，如果验证通过返回空字符串
        """
        if not isinstance(column_filter, dict):
            return "字段过滤器必须是字典格式"
        
        # 这里可以添加更多的验证逻辑
        return ""
    
    def vector_search(self, messages: List[Dict[str, Any]], first_user_msg: str) -> Tuple[Dict[str, Any], int]:
        """
        向量+词频搜索
        
        Args:
            messages: 消息列表
            first_user_msg: 第一个用户消息
            
        Returns:
            (字段过滤器, 使用的token数)
        """
        local_usage_tokens = 0
        column_filter = {}
        
        if not self.enable_vector_search:
            return column_filter, local_usage_tokens

        # 解码问题
        # 将问题拆分为子问题
        if self.agent_decode_question and messages:
            answer, tk_cnt = self.agent_decode_question.answer("提问:\n" + messages[-1]["content"])
            #拆分成功
            question_list = [q.strip() for q in answer.split("\n") if q.strip() != ""]
            local_usage_tokens += tk_cnt
        else:
            question_list = [first_user_msg]
        
        # 搜索数据字段
        if self.get_relevant_table_columns is None:
            logger.warning("get_relevant_table_columns 函数未设置，跳过向量搜索")
            return column_filter, local_usage_tokens

        logger.info(f"✅ 搜索数据字段: {question_list}")
        table_columns = self.get_relevant_table_columns(question_list)
        table_columns_str = (
            f"已取得可用的{COLUMN_LIST_MARK}:\n" +
            "\n---\n".join([self.print_table_column(table_column) for table_column in table_columns]) +
            "\n"
        )

        # 筛选字段
        error_msgs = []
        org_answer = ""
        
        for _ in range(5):
            try:
                if len(error_msgs) == 0 or len(column_filter) == 0:
                    if self.agent_column_selector:
                        answer, tk_cnt = self.agent_column_selector.answer((
                            table_columns_str +
                            f"\n用户问题:\n<{first_user_msg}>" +
                            ("\n请注意:\n" + "\n".join(error_msgs) if len(error_msgs) > 0 else "") +
                            "\n请从已知的表字段信息中选择column，确保正确地表字段关系，确保JSON格式正确。"
                        ))
                        org_answer = answer
                        local_usage_tokens += tk_cnt
                    else:
                        break
                else:
                    if self.agent_fix_column_selection:
                        answer, tk_cnt = self.agent_fix_column_selection.answer((
                            table_columns_str +
                            f"\n用户问题:\n<{first_user_msg}>\n" +
                            f"原agent的输出:\n'''\n{org_answer}\n'''\n" +
                            ("\n请注意:\n" + "\n".join(error_msgs) if len(error_msgs) > 0 else "") +
                            "\n请修正，确保正确的表字段关系，确保JSON格式正确。"
                        ))
                        local_usage_tokens += tk_cnt
                    else:
                        break
                
                args_json = extract_last_json(answer)
                if args_json is not None:
                    try:
                        tmp_column_filter = json.loads(args_json)
                        column_filter = tmp_column_filter
                        error_msg = self.validate_column_filter(column_filter)
                        if error_msg != "":
                            raise Exception(error_msg)
                        break
                    except json.JSONDecodeError as e:
                        raise Exception(f"JSON解析失败: {e}")
                        
            except Exception as e:
                error_msgs.append(str(e))
                print(f"\n用户问题:\n<{first_user_msg}>\nWorkflow【{self.name}】agent_column_selector 遇到问题: {str(e)}, 现在重试...\n")
                logger.debug("\n用户问题:\n<%s>\nWorkflow【%s】agent_column_selector 遇到问题: %s, 现在重试...\n", 
                           first_user_msg, self.name, str(e))
        
        return column_filter, local_usage_tokens
    
    def search(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        执行向量搜索
        
        Args:
            query: 查询文本
            top_k: 返回结果数量
            
        Returns:
            搜索结果列表
        """
        if self.column_vectors is None or self.column_bm25 is None:
            logger.warning("向量数据未加载，无法执行搜索")
            return []
        
        try:
            # 使用 HuggingFaceEmbedding 进行查询
            from embedding.embedding import HuggingFaceEmbedding
            import numpy as np
            from sklearn.metrics.pairwise import cosine_similarity
            
            # 初始化 embedding 模型
            embedder = HuggingFaceEmbedding(model="shibing624/text2vec-base-chinese")
            
            # 获取查询文本的 embedding
            query_embedding = embedder.get_embedding([query])[0]
            query_vector = np.array(query_embedding).reshape(1, -1)
            
            logger.info(f"✅ 查询文本的 embedding: {query_vector}")
            logger.info(f"✅ 查询文本的 embedding: {len(self.column_vectors)}")
            # 计算与所有存储向量的余弦相似度
            similarities = cosine_similarity(query_vector, self.column_vectors)
            
            # 获取最相似的 top_k 个结果
            top_indices = np.argsort(similarities[0])[::-1][:top_k]
            
            # 构建结果
            results = []
            for idx in top_indices:
                similarity_score = similarities[0][idx]
                column_name = self.column_vector_names[idx]
                
                # 解析表名和字段名
                if '.' in column_name:
                    table_name, field_name = column_name.split('.', 1)
                else:
                    table_name, field_name = column_name, ''
                
                results.append({
                    'column_name': column_name,
                    'table_name': table_name,
                    'field_name': field_name,
                    'similarity_score': float(similarity_score),
                    'rank': len(results) + 1
                })
            
            logger.info(f"✅ 向量搜索完成，找到 {len(results)} 个相关结果")
            return results
            
        except Exception as e:
            logger.error(f"❌ 向量搜索失败: {e}")
            return []


def main():
    """测试VectorSearch类的主函数"""
    print("🚀 开始测试 VectorSearch 类...")
    
    # VectorSearch实例
    vector_search = VectorSearch(
        get_relevant_table_columns=utils.get_relevant_table_columns,
        print_table_column=utils.print_table_column,
        agent_decode_question=Agent(AgentConfig(
            name = "decode_question",
            role = (
                '''你是金融行业的数据专家，善于理解用户的问题，从已知的数据表中定位到最相关的数据表。\n'''
                '''将原问题拆成多个子问题，每个子问题对应一个数据表。\n'''
                '''子问题应该遵循原问题的语境，子问题获取到的信息应该与原问题相关。\n'''
                '''原问题中的格式要求可以不用写到子问题中。\n'''
                '''如果原问题中包含专业术语的缩写和全称和中文翻译，请在子问题中把专业术语的缩写和全称和中文翻译都写上。\n'''
            ),
            output_format=(
                '''输出模板：\n'''
                '''(换行顺序输出子问题，不要有标号,直接输出一行一条子问题，直到覆盖完原问题为止)\n'''
                '''(不要输出其他内容)\n'''
            ),
            system_prompt_kv={
                "举例": (
                    '''原问题：交易日在2021-10-01到2021-10-31之间，近一月换手率超过10%的港股中股价下跌最多的公司是哪家？请回答公司中文简称。\n'''
                    '''输出:\n'''
                    '''交易日在2021-10-01到2021-10-31之间的港股有哪些\n'''
                    '''近一月换手率超过10%的港股有哪些\n'''
                    '''港股股价下跌最多的公司有哪些\n'''
                    '''这些港股公司的中文简称是什么\n'''
                    # '''原问题：截至2021-12-31，这个概念有多少只股票（不包含已经调出的）？调出了多少只股票？\n'''
                    # '''输出:\n'''
                    # '''截至2021-12-31，这个概念有多少只股票（不包含已经调出的）\n'''
                    # '''截止2021-12-31，这个概念调出了多少只股票\n'''
                    '''原问题：中南传媒在2019年度的前五大客户中，各类型客户占总营收的比例分别是多少？（答案需要包含两位小数）\n'''
                    '''输出:\n'''
                    '''中南传媒在2019年度的前五大客户有哪些\n'''
                    '''前五大客户的类型有哪些\n'''
                    '''各类型客户占总营收的比例是多少\n'''
                ),
            },
            model_name="qianwen",
            knowledge=config.table_snippet,
            enable_history=False,
            # stream=False,
        )),
        agent_column_selector=Agent(AgentConfig(
            name = "Check_db_structure.columns_selector",
            model_name="qianwen",
            role = (
                '''你是一个数据分析专家，从已知的数据表字段中，根据用户的问题，找出所有相关的字段名。'''
                '''请不要有遗漏!'''
                '''要善于利用历史对话信息和历史SQL查询记录来洞察字段间的关系。'''
            ),
            output_format = (
                '''输出模板示例:\n'''

                '''【思维链】\n'''
                '''(think step by step, 分析用户的问题，结合用户提供的可用数据字段，思考用哪些字段获得什么数据，有更好的字段就选更好的字段，逐步推理直至可以回答用户的问题)\n'''
                '''(可以用sql模拟一下，看流程是否合理)\n'''
                # '''(例如: \n'''
                # '''用户问: 2021年末，交通运输一级行业中有几个股票？\n'''
                # '''思维链：\n'''
                # '''用户问的是交通运输一级行业，可以用lc_exgindchange表的FirstIndustryName字段可以找到交通运输一级行业的行业代码FirstIndustryCode;\n'''
                # '''用户需要获取该行业有几个股票，在lc_indfinindicators表通过IndustryCode字段和Standard字段搜索到交通运输一级行业的信息,'''
                # '''其中lc_indfinindicators表的ListedSecuNum字段就是上市证券数量，\n'''
                # '''由于用户问的是2021年末，所以我需要用lc_indfinindicators表的InfoPublDate字段排序获得2021年末最后一组数据)\n'''

                '''【选中的字段的清单】\n'''
                '''(上述提到的字段都选上)\n'''
                '''(把同一个表的字段聚合在这个表名[database_name.table_name]下面)\n'''
                '''(注意表名和字段名都是英文的)\n'''
                '''```json\n'''
                '''{"database_name.table_name": ["column_name", "column_name"],"database_name.table_name": ["column_name", "column_name"]}\n'''
                '''```\n'''
            ),
            enable_history=False,
            # temperature=0.8,
            # stream=False,
        )),
        agent_fix_column_selection=Agent(AgentConfig(
            name = "fix_column_selection",
            model_name="qianwen",
            role = (
                '''你是金融数据库专家，负责审核和修正其他agent选择的数据表和字段。\n'''
                '''你的主要任务是确保所有表名和字段名的准确性，以及它们之间的正确关联。\n'''
                '''你需要仔细检查以下几点：\n'''
                '''1. 字段名是否拼写正确 - 如果发现错误，请提供正确的字段名\n'''
                '''2. 表名与字段名的关联是否正确 - 确保字段确实属于指定的表\n'''
                '''3. 表之间的关联键是否正确 - 检查JOIN条件中使用的字段是否合适\n'''
                '''4. 数据类型是否匹配 - 确保查询条件中的数据类型与字段类型一致\n'''
                '''5. 是否遗漏了重要的表或字段 - 根据用户问题补充可能有用的信息\n'''
                '''请基于已知的数据库结构信息，对其他agent的选择进行修正，确保最终使用的表和字段能够准确回答用户的问题。\n'''
                '''如果发现多个可能的修正方案，请选择最可能正确的一个，并简要说明理由。\n'''
            ),
            output_format = (
                '''输出模板示例:\n'''
                '''【选中的字段的清单】\n'''
                '''(把同一个表的字段聚合在这个表名[database_name.table_name]下面)\n'''
                '''(注意表名和字段名都是英文的)\n'''
                '''```json\n'''
                '''{"database_name.table_name": ["column_name", "column_name"],"database_name.table_name": ["column_name", "column_name"]}\n'''
                '''```\n'''
            ),
            enable_history=False,
            # stream=False,
        )),
        enable_vector_search=True,
        name="TestVectorSearch"
    )
    
    # 测试向量搜索
    print("\n🔍 测试向量搜索:")
    messages = [
        {"role": "user", "content": "天士力在2020年的最大担保金额是多少？答案需要包含1位小数"}
    ]
    first_user_msg = "查询用户信息"
    
    try:
        column_filter, usage_tokens = vector_search.vector_search(messages, first_user_msg)
        print(f"✅ 向量搜索完成")
        print(f"📊 使用的token数: {usage_tokens}")
        print(f"📋 字段过滤器: {column_filter}")
    except Exception as e:
        print(f"❌ 向量搜索失败: {e}")
    
    print("\n✅ VectorSearch 测试完成!")

if __name__ == "__main__":
    main()