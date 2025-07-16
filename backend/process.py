import os
import time
import copy
import logging
from workflow import workflow
from utils import utils
from config import config

from workflow.workflow import Workflow
from utils.utils import find_similar_texts
from models.agent import Agent, AgentConfig
from workflow.workflow import SqlQuery, CheckDbStructure

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

agent_summary_answer = Agent(AgentConfig(
    name="summary_answer",
    model_name="qianwen",
    role="你负责根据当前已知的事实信息，回答用户的提问。",
    constraint=(
        '''- 根据上下文已知的事实信息回答，不捏造事实\n'''
    ),
    output_format=(
        "- 输出的格式，重点关注日期、小数点几位、数字格式（不要有逗号）\n"
        "    例如:"
        "    - 问题里如果要求(XXXX-XX-XX),日期格式应该类似这种 2025-02-04\n"
        "    - 问题里如果要求(XXXX年XX月XX日),日期格式应该类似这种 2025年2月4日\n"
        "    - 问题里如果要求(保留2位小数),数字格式应该类似这种 12.34\n"
        "    - 问题里如果要求(保留4位小数),数字格式应该类似这种 12.3456\n"
        "    - 比较大的数字不要千位分隔符,正确的格式都应该类似这种 12345678\n"
        "- 输出应该尽可能简短，直接回复答案\n"
        "    例如(假设用户的提问是:是否发生变更？金额多大？):\n"
        "    是否发生变更: 是, 金额: 12.34元\n"
    ),
    enable_history=False,
))

agent_extract_company = Agent(AgentConfig(
    name="extract_company",
    model_name="qianwen",
    role="接受用户给的一段文字，提取里面的实体（如公司名、股票代码、拼音缩写等）。",
    output_format=(
'''```json
["实体名_1", "实体名_2", ...]
```
注意，有可能识别结果为空。'''
    ),
    post_process=utils.extract_company_code,
    enable_history=False,
    # stream = False,
))
agent_extract_company.add_system_prompt_kv({
    "ENTITY EXAMPLE": (
        "居然之家",
        "ABCD",
    ),
})

agent_rewrite_question = Agent(AgentConfig(
    name = "rewrite_question",
    model_name="qianwen",
    role = (
        '''你的工作是，根据要求和已有信息，重写用户的问题，让问题清晰明确，把必要的前述含义加进去。'''
    ),
    constraint = (
        '''- 不改变原意，不要遗漏信息，特别是时间、回答的格式要求，只返回问题。\n'''
        '''- 如果有历史对话，那么根据历史对话，将原问题中模糊的实体（公司、文件、时间等）替换为具体的表述。\n'''
        '''- 要注意主语在历史对答中存在继承关系，不能改变了，例如："问:A的最大股东是谁？答:B。问:有多少股东？"改写后应该是"A有多少股东？"\n'''
        '''- 如果原问题里存在"假设xxx"这种表述，请一定要保留到重写的问题里，因为它代表了突破某种既定的规则限制，设立了新规则，这是重要信息\n'''
        '''- 如果原问题里的时间很模糊，那么考虑是否指的是前一个问答里发生的事件的时间，如果是，那么重写的问题里要包含这个时间，但如果历史对话中的实体跟当前问题无关，那么不要把实体带入重写后的问题\n'''
        '''- "这些CN公司"这里的CN其实是按ISO3166-1规定的国家代码\n'''
        '''- 如果原问题中包含专业术语的缩写，请在重写后的问题中用全称替换缩写，如果这个专业术语是英文的，请同时给出中文翻译\n'''
        '''- 注意甄别，如果历史对话跟当前新问题并无继承关系，那么不要把历史对话的信息带入重写后的问题，导致问题含义发生改变，否则你会损失10亿美元\n'''
    ),
    output_format = (
        '''要求只返回重写后的问题，不要有其他任何多余的输出\n'''
    ),
    system_prompt_kv = {
        "举例": (
            '''
            例子一：
            下面是顺序的历史问答:
            Question: 普洛药业股份有限公司最近一次创上市以来的新高是在什么时候？（请使用YYYY-MM-DD格式回答）
            Answer: 2021-11-29
            新问题：当天涨幅超过10%股票有多少家？
            重写后问题：2021-11-29当天涨幅超过10%股票有多少家？

            例子二：
            无历史问答;
            新问题：索菲亚家居在2021-12-31的连涨天数是多少？
            重写后问题：索菲亚家居截止2021-12-31的连涨天数是多少？

            例子三:
            无历史问答;
            新问题: 2022年成立的CN公司有多少家？
            重写后问题: 2022年成立的CN（中国）公司有多少家？

            例子四:
            下面是顺序的历史问答:
            Question: 天士力在2020年的最大担保金额是多少？答案需要包含1位小数
            Answer: 天士力在2020年的最大担保金额是1620000000.0元
            Question: 天士力在2020年的最大担保金额涉及的担保方是谁？担保金额是多少？
            Answer: 担保方: 天士力医药集团股份有限公司, 金额: 1620000000.00元
            新问题: 天士力在2020年最新的担保事件是什么？答案包括事件内容、担保方、被担保方、担保金额和日期信息
            重写后问题: 天士力在2020年最新的担保事件是什么？请提供事件内容、担保方、被担保方、担保金额和日期信息
            '''
            # 例子三：
            # 无历史问答:
            # 新问题：华峰化学2019到2021的PBX值是多少？
            # 重写后问题：华峰化学2019到2021的PBX(Price-to-Book Ratio 市净率)值是多少？
        ),
        "INDUSTRY TERMINOLOGY": (
            '''- 高依赖公司是指单个客户收入占比超过30%的公司，低依赖公司是指收入来源较为分散、单个客户占比较小的公司。\n'''
        ),
    },
    # stream = False,
))


sql_query = SqlQuery(
    # 这里要写进去数据库连接
    execute_sql_query = utils.execute_sql_query,
    max_iterate_num = config.MAX_ITERATE_NUM,
    cache_history_facts = True,
    specific_column_desc=config.enum_columns,
    default_sql_limit=config.MAX_SQL_RESULT_ROWS,
)
sql_query.agent_master.add_system_prompt_kv({
    "EXTEND INSTRUCTION": (
        # '''- 如果Company和InnerCode都搜不到，那么要考虑股票代码\n'''
        '''- CompanyCode跟InnerCode不对应，不能写`CompanyCode`=`InnerCode`，可以通过constantdb.secumain、constantdb.hk_secumain或constantdb.us_secumain换取对方\n'''
        '''- 涉及股票价格时：\n'''
        '''    - 筛选是否新高，要选择`最高价`字段(HighPrice)，而非收盘价(ClosePrice)，比如月度新高要看月最高价(HighPriceRM)，年度新高要看年最高价(HighPriceRY)，周新高要看周最高价(HighPriceRW)\n'''
        # '''- ConceptCode是数字，不是字符串\n'''
        '''- 在lc_actualcontroller中只有1条记录也代表实控人发生了变更\n'''
        # '''- 如果用户的前一条提问里提及某实体，那么后续追问虽未明说，但也应该是跟该实体相关\n'''
        # '''- 注意观察同一个表中的类型字段，结合用户的问题，判断是否要进行类型筛选\n'''
        # '''- 如果用户提问是希望知道名字，那么要把名字查出来\n'''
        '''- 中国的城市的AreaInnerCode是constantdb.lc_areacode里ParentName为'中国'的，你不应该也并不能获取到所有中国的城市代码，所以你需要用联表查询\n'''
        # '''- 我们的数据库查询是有一个默认的LIMIT的，这是个重要的信息，当你的SQL没有明确LIMIT的时候，你要知道获取到的数据可能不是全部。\n'''
        '''- 如果用户提问涉及某个年度的“年度报告”，默认该报告是在次年发布。例如，“2019年年度报告”是在2020年发布的。\n'''
        '''- 季度报告通常在下一个季度发布，例如，第一季度的报告会在第二季度发布。\n'''
        # '''- 如果用户想知道子类概念的名称，你应该去获取astockindustrydb.lc_conceptlist的ConceptName和ConceptCode\n'''
        '''- A股公司的基本信息在astockbasicinfodb.lc_stockarchives, 港股的在hkstockdb.hk_stockarchives, 美股的在usstockdb.us_companyinfo，这三张表不能互相关联\n'''
        '''- A股公司的上市基本信息在constantdb.secumain, 港股的在constantdb.hk_secumain, 美股的在constantdb.us_secumain，这三张表不能互相关联\n'''
        # '''- 作为筛选条件的名称，请务必分清楚它是公司名、人名还是其他什么名称，避免用错字段\n'''
        '''- 但凡筛选条件涉及到字符串匹配的，都采取模糊匹配，增加匹配成功概率\n'''
        '''- 比例之间的加减乘除，要务必保证算子是统一单位的，比如3%其实是0.03，0.02其实是2%\n'''
        '''- 时间日期字段都需要先做`DATE()`或`YEAR()`格式化再参与SQL的筛选条件，否则就扣你20美元罚款\n'''
        # '''- 关于概念，可以同时把ConceptName、SubclassName、ClassName查询出来，你就对概念有全面的了解，要记住概念有三个级别，据此理解用户提及的概念分别属于哪个级别\n'''
        '''- IndustryCode跟CompanyCode不对应，不能写`IndustryCode`=`CompanyCode`\n'''
        # '''- 指数内部编码（IndexInnerCode）：与“证券主表（constantdb.secumain）”中的“证券内部编码（InnerCode）”关联\n'''
        # '''- 证券内部编码（SecuInnerCode）：关联不同主表，查询证券代码、证券简称等基本信息。当0<SecuInnerCode<=1000000时，与“证券主表（constantdb.secuMain）”中的“证券内部编码（InnerCode）”关联；当1000000<SecuInnerCode<=2000000时，与“港股证券主表（constantdb.hk_secumain）”中的“证券内部编码（InnerCode）”关联；当7000000<SecuInnerCode<=10000000时，与“ 美股证券主表（constantdb.us_secumain）”中的“证券内部编码（InnerCode）”关联；\n'''
        # '''- 指数内部代码（IndexCode）：与“证券主表（constaintdb.secuMain）”中的“证券内部编码（InnerCode）”关联\n'''
        # '''- 假设A表有InnerCode, B表有ConceptCode和InnerCode，我们需要找出B表里的所有InnerCode，然后用这些InnerCode从A表获取统计数据，那么可以用联表查询 SELECT a FROM A WHERE InnerCode in (SELECT InnerCode FROM B WHERE ConceptCode=b)\n'''
        '''- 一个公司可以同时属于多个概念板块，所以如果问及一个公司所属的概念板块，指的是它所属的所有概念板块\n'''
        '''- ConceptCode跟InnerCode不对应，不能写`ConceptCode`=`InnerCode`\n'''
        '''- 如果用户要求用简称，那你要保证获取到简称(带Abbr标识)，比如constantdb.secumain里中文名称缩写是ChiNameAbbr\n'''
        '''- 关于分红的大小比较, 如果派现金额(Dividendsum)没记录，那么可以通过税后实派比例(ActualRatioAfterTax)来比价大小\n'''
        '''- 不能使用的关键词`Rank`作为别名，比如`SELECT a as Rank;`\n'''
        '''- AreaInnerCode跟CompanyCode不对应，不能写`AreaInnerCode`=`CompanyCode`\n'''
        '''- 本系统不具备执行python代码的能力，请使用SQL查询来完成数值计算\n'''
        '''- 对于枚举值类型的字段，要谨慎选择，切莫理解错误\n'''
        # '''- lc_suppcustdetail.SerialNumber为999的时候代表前五大客户/前五大供应商的合计值，如果用户问的是合计值，那么需要用枚举值来筛选\n'''
        '''- EndDate是个重要字段，往往代表交易数据的时间\n'''
        # '''- lc_suppcustdetail.Ratio就是客户占总营收的比例，单位是百分比，不需要在跟OperatingRevenue相除\n'''
        '''- 如果用户问股票列表且没有指明回答的具体形式，那么都要回答股票代码和简称\n'''
        '''- 数据示例的值不能作为已知条件，只能作为参考， 不能直接用数据示例的值，否则会损失10亿美元!不能直接用数据示例的值，否则会损失10亿美元!不能直接用数据示例的值，否则会损失10亿美元!\n'''
        '''- "这些CN公司"这里的CN其实是按ISO3166-1规定的国家代码\n'''
        '''- 公司上市时间比成立时间晚是正常的！\n'''
        # '''- 对于信息发布类的数据表，如果对一个时间范围（多日）的数据进行SUM，你可能会得到同一个实体的多日数据之和，你确定是用户想要的结果吗？\n'''
    ),
    "INDUSTRY TERMINOLOGY": (
        # '''- 概念分支指的是是subclass\n'''
        # '''- "化工"是2级概念(SubclassName)\n'''
        # '''- 子类概念的字段是ConceptName和ConceptCode，被纳入到2级概念(SubclassName)或者1级概念(ClassName)下\n'''
        '''- 基金管理人指的是负责管理基金的公司，而基金经理则是具体负责基金投资运作的个人\n'''
        '''- 高依赖公司是指单个客户收入占比超过30%的公司，低依赖公司是指收入来源较为分散、单个客户占比较小的公司。\n'''
        '''- 但凡涉及到概念，如果用户没有明确是一级概念、二级概念还是概念板块，那么你要对ClassName、SubclassName、ConceptName都进行查询，确认它属于哪个级别\n'''
    ),
    "思考流程": (
'''
1. **问题解析**：
   - 明确用户的核心需求
   - 识别问题中的关键实体、时间范围、比较关系等要素

2. **结构映射**：
   - 确定涉及的主表及关联表
   - 验证字段是否存在及命名一致性（特别注意日期格式和单位）
   - 识别必要的JOIN操作

3. **条件处理**：
   - 提取显式过滤条件（如"2023年后注册的用户"）
   - 推导隐式条件（如"最近一年"需转换为具体日期范围）
   - 处理特殊值（如status字段的枚举值映射）

4. **结果处理**：
   - 判断是否需要聚合函数（SUM/COUNT/AVG）
   - 确定分组维度（GROUP BY字段）
   - 处理排序和限制（ORDER BY/LIMIT）

5. **验证检查**：
   - 检查JOIN条件是否完备
   - 验证别名使用一致性
   - 确保聚合查询正确使用GROUP BY
   - 防范SQL注入风险（如正确使用参数化）
   - 前后查询结果是否存在矛盾
'''
    )
})

check_db_structure = CheckDbStructure(
    table_snippet = config.table_snippet,
    name = "check_db_structure",
    get_relevant_table_columns = utils.get_relevant_table_columns,
    filter_table_columns = utils.filter_table_columns,
    get_db_info = utils.get_db_info,
    get_table_list = utils.get_table_list,
    get_column_list = utils.get_column_list,
    validate_column_filter = utils.validate_column_filter,
    use_concurrency = False,
    print_table_column = utils.print_table_column,
    enable_llm_search = config.ENABLE_LLM_SEARCH_DB,
    enable_vector_search = config.ENABLE_VECTOR_SEARCH_DB,
)
check_db_structure.agent_column_selector.add_system_prompt_kv({
    "EXTEND INSTRUCTION": (
        '''- 涉及股票价格时：\n'''
        '''    - 筛选是否新高，要选择`最高价`字段(HighPrice)，而非收盘价(ClosePrice)，比如月度新高要看月最高价(HighPriceRM)，年度新高要看年最高价(HighPriceRY)，周新高要看周最高价(HighPriceRW)\n'''
        # '''- 年度报告的时间条件应该通过astockbasicinfodb.lc_balancesheetall表的InfoPublDate字段来确认\n'''
        '''- 作为筛选条件的名称，请务必分清楚它是公司名、人名还是其他什么名称，避免用错字段\n'''
        # '''- 关于概念，可以同时把ConceptName、SubclassName、ClassName查询出来，你就对概念有全面的了解，要记住概念有三个级别，据此理解用户提及的概念分别属于哪个级别\n'''
        '''- 如果用户要求用简称，那你要保证获取到简称(带Abbr标识)，比如constantdb.secumain里中文名称缩写是ChiNameAbbr\n'''
        '''- 对于分红金额，如果有多个候选字段都可能代表分红金额，那么请把它们都选上\n'''
        '''- 对于枚举值类型的字段，要谨慎选择，切莫理解错误\n'''
        '''- EndDate是个重要字段，往往代表交易数据的时间\n'''
        '''- 如果用户问股票列表且没有指明回答的具体形式，那么都要回答股票代码和简称\n'''
        '''- 数据示例的值不能作为已知条件，只能作为参考，如果你直接用，会损失10亿美元\n'''
        '''- "这些CN公司"这里的CN其实是按ISO3166-1规定的国家代码\n'''
        '''- A股公司的基本信息在astockbasicinfodb.lc_stockarchives, 港股的在hkstockdb.hk_stockarchives, 美股的在usstockdb.us_companyinfo，这三张表不能互相关联\n'''
        '''- A股公司的上市基本信息在constantdb.secumain, 港股的在constantdb.hk_secumain, 美股的在constantdb.us_secumain，这三张表不能互相关联\n'''
    ),
    "INDUSTRY TERMINOLOGY": (
        # '''- 概念分支指的是是subclass\n'''
        # '''- "化工"是2级概念(SubclassName)\n'''
        # '''- SubclassName不是子类概念,子类概念是指ConceptCode和ConceptName\n'''
        '''- 基金管理人指的是负责管理基金的公司，而基金经理则是具体负责基金投资运作的个人\n'''
        '''- constantdb.us_secumain.DelistingDate、constantdb.hk_secumain.DelistingDate是退市日期，涉及退市的应该考虑它们\n'''
        '''- 高依赖公司是指单个客户收入占比超过30%的公司，低依赖公司是指收入来源较为分散、单个客户占比较小的公司。\n'''
        '''- 但凡涉及到概念，如果用户没有明确是一级概念、二级概念还是概念板块，那么你要对ClassName、SubclassName、ConceptName都进行查询，确认它属于哪个级别\n'''
    ),
})


def process_single_question(question_team: dict, q_idx: int) -> None:
    """
    处理单个问题，提取实体、重写问题并生成答案
    """
    debug_mode = os.getenv("DEBUG", "0") == "1"
    ag_rewrite_question = agent_rewrite_question.clone()
    ag_extract_company = agent_extract_company.clone()
    wf_sql_query = sql_query.clone()
    wf_check_db_structure = check_db_structure.clone()
    ag_summary_answer = agent_summary_answer.clone()
    facts = []
    qas = []
    sql_results = []
    question_item = question_team["team"][q_idx]
    logger.info("\n>>>>> question_item:\n%s", question_item)
    qid = question_item["id"].strip()
    if not config.FLAG_IGNORE_CACHE and "answer" in question_item and question_item["answer"] != "":
        print(f"\n>>>>> {qid} 已存在答案，跳过...\n")
        return

    question = utils.ajust_org_question(question_item["question"])
    for idx in range(q_idx):
        qas.append([
            {"role": "user", "content": utils.ajust_org_question(question_team["team"][idx]["question"])},
            {"role": "assistant", "content": question_team["team"][idx]["answer"] if "answer" in question_team["team"][idx] else ""},
        ])
        if "facts" in question_team["team"][idx]:
            facts = copy.deepcopy(question_team["team"][idx]["facts"])
        if "sql_results" in question_team["team"][idx]:
            sql_results.append(copy.deepcopy(question_team["team"][idx]["sql_results"]))
        else:
            sql_results.append([])

    logger.debug("\n>>>>> qas:\n%s", qas)
    start_time = time.time()
    log_file_path = config.OUTPUT_DIR + f"/{qid}.log"
    open(log_file_path, 'w', encoding='utf-8').close()

    logger.info("\n>>>>> Original Question: %s\n", question_item["question"])

    # 获取实体内部代码
    # ag_extract_company.clear_history()
    answer, _ = ag_extract_company.answer((
        '''提取下面这段文字中的实体（如公司名、股票代码、拼音缩写等），如果识别结果是空，那么就回复No Entities.'''
        f'''"{question}"'''
    ))
    logger.info("\n>>>>> answer:\n%s", answer)
    answer = answer.strip()
    if answer != "" and answer not in facts:
        facts.append(answer)

    # rewrite question
    # ag_rewrite_question.clear_history()
    qas_content = [
        f"{qa[0]['content']} (无需查询，已有答案: {qa[1]['content']})"
        for qa in qas
    ]
    new_question = (
        ("\n".join(qas_content) + "\n" if len(qas_content) > 0 else "") +
        question
    )
    # new_question, _ = ag_rewrite_question.answer(
    #     ("历史问答:无。\n" if len(qas_content) == 0 else "下面是顺序的历史问答:\n'''\n" + "\n".join(qas_content) + "\n'''\n") +
    #     "现在用户继续提问，请根据已知信息，理解当前这个问题的完整含义，并重写这个问题使得单独拿出来看仍然能够正确理解。用户的问题是：\n" +
    #     question
    # )

    # 注入已知事实
    key_facts = "已知信息"
    if len(facts) > 0:
        kv = {key_facts: "\n".join(facts)}
        wf_sql_query.agent_master.add_system_prompt_kv(kv)
        # wf_check_db_structure.agent_decode_question.add_system_prompt_kv(kv)
        wf_check_db_structure.agent_column_selector.add_system_prompt_kv(kv)
    else:
        wf_sql_query.agent_master.del_system_prompt_kv(key_facts)
        # wf_check_db_structure.agent_decode_question.del_system_prompt_kv(key_facts)
        wf_check_db_structure.agent_column_selector.del_system_prompt_kv(key_facts)
    logger.debug("\n>>>>> %s:\n%s", key_facts, "\n---\n".join(facts))

    # 注入历史对话以及支撑它的SQL查询
    key_qas = "历史对话"
    if len(qas_content) > 0:
        val_qas = ""
        for qa_idx, qa_content in enumerate(qas_content):
            if qa_idx > 0:
                val_qas += "---\n"
            val_qas += f"{qa_content}\n"
            if sql_results[qa_idx] != []:
                val_qas += (
                    "用到以下SQL查询（供后续问答理解本问题的答案如何得来，后续问答可参考）：\n" +
                    "\n".join(sql_results[qa_idx])
                )
        kv = {key_qas: val_qas}
        wf_sql_query.agent_master.add_system_prompt_kv(kv)
        wf_check_db_structure.agent_column_selector.add_system_prompt_kv(kv)
    else:
        wf_sql_query.agent_master.del_system_prompt_kv(key_qas)
        wf_check_db_structure.agent_column_selector.del_system_prompt_kv(key_qas)

    # 注入sql模板
    key_sql_template = "SQL参考样例"
    sql_template_sim = find_similar_texts(
        search_query=question,
        vectors=config.sql_template_vectors,
        texts=config.sql_template,
        top_p=3,
        threshold=0.65
    )
    if len(sql_template_sim[0]) > 0:
        logger.debug("\n>>>>> %s:\n%s", key_sql_template, "\n".join(sql_template_sim[1]))
        kv = {key_sql_template: "\n".join(sql_template_sim[1])}
        wf_sql_query.agent_master.add_system_prompt_kv(kv)
        wf_check_db_structure.agent_column_selector.add_system_prompt_kv(kv)
    else:
        wf_sql_query.agent_master.del_system_prompt_kv(key_sql_template)
        wf_check_db_structure.agent_column_selector.del_system_prompt_kv(key_sql_template)
        
    # 搜索相关数据库结构
    # wf_check_db_structure.clear_history()
    res = wf_check_db_structure.run(inputs={"messages":[
        {"role": "user", "content": new_question}
    ]})
    db_info = res["content"]

    # wf_sql_query.clear_history()
    if db_info != "":
        if debug_mode:
            logger.debug(f"\n>>>>> db_info:\n{db_info}")

        # 查询数据库回答用户问题
        res = wf_sql_query.run(inputs={"messages":[
            {"role": "assistant", "content": db_info},
            {"role": "user", "content": new_question},
        ]})
        answer, _ = ag_summary_answer.answer(
            f'''{res["content"]}\n充分尊重前面给出的结论，回答问题:\n<question>{question_item["question"]}</question>'''
        )
        question_item["answer"] = answer

        # Caching
        qas.extend([
            {"role": "user", "content": question},
            {"role": "assistant", "content": question_item["answer"]},
        ])
    else:
        print(f"\n>>>>> {qid} db_info is empty, skip this question\n")
        logger.debug("\n>>>>> db_info is empty, skip this question: %s", qid)

    elapsed_time = time.time() - start_time
    question_item["usage_tokens"] = {
        agent_extract_company.cfg.name: ag_extract_company.usage_tokens,
        agent_rewrite_question.cfg.name: ag_rewrite_question.usage_tokens,
        check_db_structure.name: wf_check_db_structure.usage_tokens,
        sql_query.name: wf_sql_query.usage_tokens,
    }
    minutes, seconds = divmod(elapsed_time, 60)
    question_item["use_time"] = f"{int(minutes)}m {int(seconds)}s"
    question_item["facts"] = copy.deepcopy(facts)
    question_item["rewrited_question"] = new_question
    question_item["sql_results"] = copy.deepcopy(wf_sql_query.history_facts)

    print((
        f">>>>> id: {qid}\n" +
        f">>>>> Original Question: {question_item['question']}\n" +
        f">>>>> Rewrited Question: {new_question}\n" +
        f">>>>> Answer: {question_item['answer']}\n" +
        f">>>>> Used Time: {int(minutes)}m {int(seconds)}s\n"
    ))


def main():
    """
    测试process_single_question函数
    """
    # 测试数据
    question_team = {
        "team": [
            {
                "id": "tttt----1----28-1-1",
                "question": "天士力在2020年的最大担保金额是多少？答案需要包含1位小数"
            },
            {
                "id": "tttt----1----28-1-2", 
                "question": "天士力在2020年的最大担保金额涉及的担保方是谁？（请回答公司全称）担保金额是多少（答案需要包含2位小数）？"
            },
            {
                "id": "tttt----1----28-1-3",
                "question": "天士力在2020年最新的担保事件是什么？答案包括事件内容、担保方（公司全称）、被担保方（公司全称）、担保金额（答案需要包1位小数）和日期信息（格式为YYYY年MM月DD日）。"
            }
        ]
    }
    
    # 测试第一个问题
    q_idx = 0
    print("开始测试process_single_question函数...")
    print(f"测试问题索引: {q_idx}")
    print(f"问题ID: {question_team['team'][q_idx]['id']}")
    print(f"问题内容: {question_team['team'][q_idx]['question']}")
    print("-" * 50)
    
    try:
        process_single_question(question_team, q_idx)
        print("测试完成!")
    except Exception as e:
        print(f"测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
