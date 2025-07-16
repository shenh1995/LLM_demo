import json
import logging
from typing import Dict, Any, Tuple, Callable, Optional
import os
import sys
import re

# 添加 backend 目录到 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.agent import Agent, AgentConfig
from models.factory import ChatModelFactory
from utils import utils

# 添加 backend 目录到 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.agent import Agent, AgentConfig

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class ModelSearch:
    """模型搜索类"""
    
    def __init__(self, 
                 agent_db_selector=None,
                 agent_table_selector=None,
                 agent_column_selector=None,
                 agent_fix_column_selection=None,
                 enable_search=True,
                 get_table_list: Optional[Callable[[list], str]] = None,
                 get_db_info: Optional[Callable[[], str]] = None,
                 get_column_list: Optional[Callable[[list], str]] = None,
                 validate_column_filter: Optional[Callable[[dict], str]] = None,
                 name="ModelSearch"):
        """
        初始化模型搜索
        
        Args:
            agent_db_selector: 数据库选择代理
            agent_table_selector: 表选择代理
            agent_column_selector: 字段选择代理
            agent_fix_column_selection: 字段选择修复代理
            enable_search: 是否启用LLM搜索
            name: 搜索器名称
        """
        self.agent_db_selector = agent_db_selector
        self.agent_table_selector = agent_table_selector
        self.agent_column_selector = agent_column_selector
        self.agent_fix_column_selection = agent_fix_column_selection
        self.enable_search = enable_search
        self.get_table_list = get_table_list
        self.get_db_info = get_db_info
        self.get_column_list = get_column_list
        self.validate_column_filter = validate_column_filter
        self.extract_last_json = utils.extract_last_json
       

        self.name = name
        


    def search(self, first_user_msg: str) -> Tuple[Dict[str, Any], int]:
        """
        全自动逐层搜索
        
        Args:
            first_user_msg: 用户消息
            
        Returns:
            (字段过滤器, 使用的token数)
        """
        local_usage_tokens = 0
        column_filter_result = {}
        if not self.enable_search:
            return column_filter_result, local_usage_tokens
            
        # 检查代理是否已初始化
        if not self.agent_db_selector:
            logger.warning("agent_db_selector 未初始化，跳过数据库选择")
            return column_filter_result, local_usage_tokens
            
        # 选择数据库
        args_json = None
        table_list = ""
        error_msg = "\n请选择db，确保JSON格式正确。"
        for _ in range(5):
            try:
                answer, tk_cnt = self.agent_db_selector.answer(f"用户问题:\n<{first_user_msg}>\n{error_msg}")
                local_usage_tokens += tk_cnt
                args_json = self.extract_last_json(answer)
                if args_json is not None:
                    dbs = json.loads(args_json)
                    table_list = self.get_table_list(dbs=dbs)
                    break
            except Exception as e:
                error_msg = f"\n注意: {str(e)}。请选择db，确保JSON格式正确。"
                print(f"\n用户问题:\n<{first_user_msg}>\nWorkflow【{self.name}】agent_db_selector 遇到问题: {str(e)}, 现在重试...\n")
                logger.debug("\n用户问题:\n<%s>\nWorkflow【%s】agent_db_selector 遇到问题: %s, 现在重试...\n", first_user_msg, self.name, str(e))
        if table_list != "":
            # 选择数据表
            if not self.agent_table_selector:
                logger.warning("agent_table_selector 未初始化，跳过表选择")
                return column_filter_result, local_usage_tokens
                
            column_list = ""
            error_msg = "\n请选择table，确保JSON格式正确。"
            for _ in range(5):
                try:
                    answer, tk_cnt = self.agent_table_selector.answer(f"{table_list}\n用户问题:\n<{first_user_msg}>\n{error_msg}")
                    local_usage_tokens += tk_cnt
                    args_json = self.extract_last_json(answer)
                    if args_json is not None:
                        tables = json.loads(args_json)
                        column_list = self.get_column_list(tables=tables)
                        break
                except Exception as e:
                    error_msg = f"\n注意: {str(e)}。请选择table，确保JSON格式正确。"
                    print(f"\n用户问题:\n<{first_user_msg}>\nWorkflow【{self.name}】agent_table_selector 遇到问题: {str(e)}, 现在重试...\n")
                    logger.debug("\n用户问题:\n<%s>\nWorkflow【%s】agent_table_selector 遇到问题: %s, 现在重试...\n", first_user_msg, self.name, str(e))
            if column_list != "":
                # 筛选字段
                if not self.agent_column_selector:
                    logger.warning("agent_column_selector_old 未初始化，跳过字段选择")
                    return column_filter_result, local_usage_tokens
                    
                error_msgs = []
                org_answer = ""
                for _ in range(5):
                    try:
                        if len(error_msgs) == 0 or len(column_filter_result) == 0:
                            answer, tk_cnt = self.agent_column_selector.answer((
                                f"{column_list}\n用户问题:\n<{first_user_msg}>" +
                                ("\n请注意:\n" + "\n".join(error_msgs) if len(error_msgs) > 0 else "") +
                                "\n请从已知的表字段信息中选择column，确保正确地表字段关系，确保JSON格式正确。"
                            ))
                            org_answer = answer
                        else:
                            if not self.agent_fix_column_selection:
                                logger.warning("agent_fix_column_selection 未初始化，跳过字段修复")
                                break
                            answer, tk_cnt = self.agent_fix_column_selection.answer((
                                f"{column_list}\n用户问题:\n<{first_user_msg}>\n" +
                                f"原agent的输出:\n'''\n{org_answer}\n'''\n" +
                                ("\n请注意:\n" + "\n".join(error_msgs) if len(error_msgs) > 0 else "") +
                                "\n请修正，确保正确的表字段关系，确保JSON格式正确。"
                            ))
                        local_usage_tokens += tk_cnt
                        args_json = self.extract_last_json(answer)
                        if args_json is not None:
                            tmp_column_filter = json.loads(args_json)
                            column_filter_result = tmp_column_filter
                            error_msg = self.validate_column_filter(column_filter_result)
                            if error_msg != "":
                                raise Exception(error_msg)
                            break
                    except Exception as e:
                        error_msgs.append(str(e))
                        print(f"\n用户问题:\n<{first_user_msg}>\nWorkflow【{self.name}】agent_column_selector_old 遇到问题: {str(e)}, 现在重试...\n")
                        logger.debug("\n用户问题:\n<%s>\nWorkflow【%s】agent_column_selector_old 遇到问题: %s, 现在重试...\n", first_user_msg, self.name, str(e))
            else:
                logger.debug("\n Fail to get column_list, Skip\n")
        else:
            logger.debug("\n Fail to get table_list, Skip\n")
        
        return column_filter_result, local_usage_tokens


def main():
    """测试ModelSearch类的主函数"""
    print("🚀 开始测试 ModelSearch 类...")
    
    # 创建代理实例
    agent_db_selector = Agent(AgentConfig(
            name="db_selector",
            model_name="qianwen",
            role = (
                '''你是一个数据分析专家。根据用户的提问，从已知的数据库中，选出一个或多个数据库名，'''
                '''判断可以从这些库中获取到用户所需要的信息。'''
                '''请选择能最快获取到用户所需信息的数据库名，不要舍近求远。只需要说明思考过程并给出数据库名即可。'''
            ),
            output_format = (
                '''输出模板示例:\n'''
                '''【分析】\n'''
                '''分析用户的提问\n'''
                '''【选中的数据库】\n'''
                '''（选出必要的数据库，不是越多越好）\n'''
                '''- database_name: 这个数据库包含哪些会被用到的信息\n'''
                '''【选中的数据库的清单】\n'''
                '''```json\n'''
                '''["database_name", "database_name"]\n'''
                '''```\n'''
            ),
            enable_history=False,
            knowledge=utils.get_db_info(),
            # stream=False,
        ))
    
    agent_table_selector = Agent(AgentConfig(
            name = "table_selector",
            model_name="qianwen",
            role = (
                '''你是一个数据分析专家，从已知的数据表中，根据需要选出一个或多个表名。'''
                '''请尽可能选择能最合适的表名。'''
            ),
            output_format = (
                '''输出模板示例:\n'''
                '''【分析】\n'''
                '''分析用户的提问\n'''
                '''【选中的数据表】\n'''
                '''（选出必要的数据表，不是越多越好）\n'''
                '''- database_name.table_name: 这个数据表包含哪些会被用到的信息\n'''
                '''【选中的数据库表的清单】\n'''
                '''```json\n'''
                '''["database_name.table_name", "database_name.table.name"]\n'''
                '''```\n'''
                '''给出的表名应该是库名和表名的组合(database_name.table_name)'''
            ),
            enable_history=False,
            # stream=False,
        ))
    
    agent_column_selector = Agent(AgentConfig(
            name = "columns_selector",
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
        ))
    
    agent_fix_column_selection = Agent(AgentConfig(
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
        ))

    # ModelSearch实例
    model_search = ModelSearch(
        agent_db_selector=agent_db_selector,
        agent_table_selector=agent_table_selector,
        agent_column_selector=agent_column_selector,
        agent_fix_column_selection=agent_fix_column_selection,
        get_table_list=utils.get_table_list,
        get_column_list=utils.get_column_list,
        validate_column_filter=utils.validate_column_filter,
        enable_search=True,
        name="TestModelSearch"
    )
    
    # 测试LLM搜索
    print("\n🔍 测试LLM搜索:")
    first_user_msg = "天士力在2020年的最大担保金额是多少？答案需要包含1位小数"
    
    try:
        column_filter, usage_tokens = model_search.search(first_user_msg)
        print(f"✅ LLM搜索完成")
        print(f"📊 使用的token数: {usage_tokens}")
        print(f"📋 字段过滤器: {column_filter}")
    except Exception as e:
        print(f"❌ LLM搜索失败: {e}")
    
    print("\n✅ ModelSearch 测试完成!")


if __name__ == "__main__":
    main()