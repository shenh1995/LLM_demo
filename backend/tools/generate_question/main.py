import concurrent.futures
import asyncio
import sys
import os
from tqdm import tqdm
import time
import json
import pandas as pd
import re

# 添加项目根目录到Python路径，确保能找到 agent 模块
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, backend_dir)

from agent import Agent, AgentConfig
from models.factory import ChatModelFactory

column_questions = {}

# 初始化聊天模型
chat_model = ChatModelFactory.get_model("qianwen", False)

# 示例问题列表（这里需要根据实际情况填充）
sub_qs = [
    "查询某个字段的数据分布",
    "统计某个指标的变化趋势",
    "分析某个维度的占比情况",
    "查找某个条件的记录数量",
    "比较不同时间段的数值变化"
]

# 创建扩展问题的 Agent
ag_extend_question = Agent(AgentConfig(
    name="extend_question",
    role=(
        '''作为金融数据专家，为用户给出的数据表字段，生成5个不同的用户可能提问。'''
        '''使用不同表达方式和业务术语，包含不同句式结构，充分考虑用户提供的字段描述以及它所属的表和库的含义。'''
        '''只输出问题，每行一个。'''
    ),
    output_format=(
        '''输出模板：\n'''
        '''(输出5个不同的用户可能提问，每行一个)\n'''
        '''(不要标号，不要输出其他内容)\n'''
    ),
    llm=chat_model,
    system_prompt_kv={
        "模仿下面的用户提问的句式和风格": "\n".join(sub_qs),
    },
    enable_history=False,
    stream=True,
))


def parse_all_tables_schema(file_path):
    """
    解析 all_tables_schema.txt 文件，将表结构转换为结构化的字典格式
    
    参数:
        file_path (str): all_tables_schema.txt 文件的路径
        
    返回:
        list: 包含所有表结构的字典，格式为 [{
            "table_name": table_name,
            "columns": columns
        }, ...]
    """
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # 使用正则表达式匹配表结构块
    import re
    table_pattern = r'===\s+([\w\.]+)\s+表结构\s+===\n(.*?)(?=\n===|\Z)'
    table_matches = re.findall(table_pattern, content, re.DOTALL)
    
    result = []
    
    for table_name, table_content in table_matches:
        # 分割表内容为行
        lines = table_content.strip().split('\n')
        
        # 跳过表头和分隔线
        data_start = 2  # 假设前两行是表头和分隔线
        
        # 解析列信息
        columns = []
        for i in range(data_start, len(lines)):
            line = lines[i].strip()
            if not line:
                continue

            line = line.replace("No description available", line.split(None, 1)[0])
            
            # 分割列信息 - 使用空白分割前两列，剩余部分作为第三列
            parts = line.split(None, 2)
            if len(parts) >= 2:
                column_name = parts[0].strip()
                column_desc = parts[1].strip()
                column_value = parts[2].strip() if len(parts) > 2 else "NULL"

                if table_name == "astockoperationsdb.lc_suppcustdetail":
                    if column_name == "SerialNumber":
                        column_desc = "999代表前五大客户/供应商的合计数据，客户还是供应商可以看RelationType字段(4代表客户，6代表供应商)，另外可以RelatedPartyAttribute字段判断客户的类型"
                    elif column_name == "Ratio":
                        column_desc = "占比（单位是%），如客户或供应商占总营收的比例，通过RelationType字段判断客户还是供应商"
                elif table_name == "astockshareholderdb.lc_mainshlistnew":
                    if column_name == "SHKind":
                        column_desc = "股东类型"
                elif table_name == "astockbasicinfodb.lc_stockarchives":
                    if column_name == "State":
                        column_desc = "省份地区编码"
                
                if column_name not in ['JSID', 'UpdateTime', 'InsertTime', 'ID', 'XGRQ', 'PriceUnit']:
                    col_mark = f"{table_name}|{column_name}"
                    # 这里需要根据实际情况获取 nullable_columns 和 unuse_columns
                    # col_null_percent = nullable_columns[col_mark]['null_percent'] if col_mark in nullable_columns else 0
                    col_null_percent = 0  # 临时设置为0
                    # if col_mark not in unuse_columns and col_null_percent < 98:
                    if col_null_percent < 98:  # 临时条件
                        columns.append({
                            "name": column_name,
                            "desc": (
                                column_desc if col_null_percent < 50
                                else f"{column_desc}（注意本字段的值可能是NULL）"
                            ),
                            "val": column_value,
                            'remarks': "",
                            'enum_desc': "",
                        })
        
        # 将列信息添加到结果字典
        if columns:
            result.append({
                "table_name": table_name,
                "table_desc": "",
                "table_remarks": "",
                "column_count": len(columns),
                "columns": columns,
                "all_cols": ",".join([f"{c['desc']}({c['name']})" for c in columns]),
            })
    
    return result

# 为每个字段生成问题的函数
async def generate_questions_for_column(t, c):
    try:
        msg = (
            f"现有数据表[{t['table_desc']}]: {t['table_remarks']}\n"
            f"请针对下面的字段生成不同的用户可能提问。\n"
            f"字段: {c['name']}\n"
            f"字段描述: {c['desc']};{c['remarks']}\n"
        )
        if c['enum_desc'] != "":
            msg += f"枚举值说明: {c['enum_desc']}\n"
        
        answer, _ = await ag_extend_question.answer(msg)
        column_name = f"{t['table_name']}.{c['name']}"
        column_questions[column_name] = [q.strip() for q in answer.split("\n") if q.strip() != ""]
        return True
    except Exception as e:
        print(f"处理出错: {msg}\n错误: {str(e)}")
        return False


def exists_column_name(column_name, table_name, schema):
    for t in schema:
        if t['table_name'].split(".")[1] == table_name:
            for c in t['columns']:
                if c['name'] == column_name:
                    return True
    return False

def is_null_example(column_name, table_name, schema):
    for t in schema:
        if t['table_name'].split(".")[1] == table_name:
            for c in t['columns']:
                if c['name'] == column_name:
                    return c['val'] == "NULL"
    return False

async def __main__():
    file_path = "../assets/all_tables_schema.txt"
    df1 = pd.read_excel('../assets/数据字典.xlsx', sheet_name='库表关系')
    df2 = pd.read_excel('../assets/数据字典.xlsx', sheet_name='表字段信息')
    
    schema = parse_all_tables_schema(file_path)

    # 遍历df1，取出库名英文，表英文，表中文，表描述
    for _, row in df1.iterrows():
        # 添加类型检查和转换
        db_name = str(row['库名英文']) if not pd.isna(row['库名英文']) else ""
        table_name_en = str(row['表英文']) if not pd.isna(row['表英文']) else ""
        table_name = db_name.lower() + "." + table_name_en.lower()
        
        for t in schema:
            if t['table_name'] == table_name:
                t['table_desc'] = str(row['表中文']) if not pd.isna(row['表中文']) else ""
                table_desc = str(row['表描述']) if not pd.isna(row['表描述']) else ""
                t['table_remarks'] = table_desc.replace("\n", " ")
                if table_name == "astockshareholderdb.lc_actualcontroller":
                    t['table_desc'] += "(只处理实际控制人有变动的数据，所以即使只有1条记录，也代表实控人发生了变更)"
                elif table_name == "constantdb.secumain":
                    t['table_desc'] = "A股证券主表"
                break

    # 遍历df2，取出 table_name, column_name, 注释
    for _, row in df2.iterrows():
        if not isinstance(row['table_name'], str):
            continue
        if not isinstance(row['column_name'], str):
            continue
        table_name = str(row['table_name']).lower()
        column_name = str(row['column_name'])
        column_remarks = str(row['注释']) if not pd.isna(row['注释']) else ""
        column_enum_desc = ""

        # 修正部分字段的描述
        if column_name == "IndexInnerCode":
            column_remarks = '指数内部编码（IndexInnerCode）：与“指数基本情况（lc_indexbasicinfo）”中的“指数代码（IndexCode）”关联'
        elif column_name == "IndexCode":
            column_remarks = '指数内部编码（IndexCode）：与“指数基本情况（lc_indexcomponent）”中的“指数内部编码（IndexInnerCode）”关联'
        elif column_name == "InvolvedStock":
            column_remarks = ""
        elif column_name == "ObjectCode":
            column_remarks = "要获取交易对象名称,请用ObjectName字段"
        elif column_name == "IndustryCode":
            column_remarks = "跟各级行业代码字段关联，包括astockindustrydb.lc_exgindchange表和astockindustrydb.lc_exgindustry表的以下字段：FirstIndustryCode/SecondIndustryCode/ThirdIndustryCode/FourthIndustryCode"
        elif column_name == "Standard":
            column_remarks += "(注意不同表的Standard含义不一定相同，注意枚举值的含义)"
        elif column_name == "InfoPublDate":
            if exists_column_name("EndDate", table_name, schema):
                # column_remarks += "信息发布日期(InfoPublDate)：表示信息公开发布的日期，通常与EndDate(截止日期)配合使用。EndDate表示数据统计的截止时间，而InfoPublDate表示该数据正式对外发布的时间，通常在EndDate之后。"
                column_remarks += "信息发布日期(InfoPublDate)：表示信息公开发布的日期，通常与EndDate(截止日期)配合使用。EndDate表示数据统计的截止时间，除非用户明确要求查询信息发布日期，否则都用EndDate，如果用错了，你会损失10亿美元！"
            elif exists_column_name("InitialInfoPublDate", table_name, schema):
                column_remarks += "InfoPublDate通常在InitialInfoPublDate之后，除非用户明确要求查询信息更新发布的日期，否则都用InitialInfoPublDate，如果用错了，你会损失10亿美元！"
            elif exists_column_name("EffectiveDate", table_name, schema):
                column_remarks += "InfoPublDate通常在EffectiveDate之后，除非用户明确要求查询信息生效的日期，否则都用EffectiveDate，如果用错了，你会损失10亿美元！"
        elif column_name == "SubjectName":
            if exists_column_name("CompanyCode", table_name, schema):
                column_remarks += "事件主体不一定是本公司，请用CompanyCode字段关联上市公司基本资料（constantdb.secumain）"
        elif column_name == "HighPriceRY":
            column_remarks += "这是近一年的最高价，并非指自然年，所以如果要查询的是指定某年的最高价，需要HighPrice字段去找最大值"
        elif column_name == "LowPriceRY":
            column_remarks += "这是近一年的最低价，并非指自然年，所以如果要查询的是指定某年的最低价，需要LowPrice字段去找最小值"
        elif column_name == "TransCode":
            column_remarks = "基金转型统一编码(TransCode)是转型后的基金内码(InnerCode)，若发生多次转型，则为最新的基金内码。"
        elif column_name == "EstablishmentDate":
            column_remarks += "要计算成立时长，可用DATEDIFF(CURDATE(), EstablishmentDate) AS days_diff"
        elif column_name == "TurnoverRate":
            column_remarks += f"本字段所在的表是{table_name}，不是qt_dailyquote"
        elif column_name == "AgreementDate":
            column_remarks = "未启用该字段，不要使用"
        elif column_name == "SubjectCode":
            if exists_column_name("CompanyCode", table_name, schema):
                column_remarks = "SubjectCode字段未启用，请用CompanyCode搜索事件主体"
        elif column_name == "Borrower":
            column_remarks += "Borrower可能是下属公司，请用CompanyCode搜索事件主体"
        elif column_name == "PE_TTM":
            column_remarks += "如果想获知一年的市盈率如何变化，可以先获取2021年每个月的平均市盈率，然后进行比较"
        elif column_name == "VMACD_DIFF" or column_name == "VMACD_DEA":
            column_remarks += "MACD指标是股票技术分析中一个重要的技术指标，由两条曲线和一组红绿柱线组成。 两条曲线中波动变化大的是DIF线，通常为白线或红线，相对平稳的是DEA线(MACD线)，通常为黄线。 当DIF线上穿DEA线时，这种技术形态叫做MACD金叉，通常为买入信号。"
        elif column_name == "IndustryName":
            column_remarks += "这是行业名称，可做模糊查询"
        elif column_name == "InnerCode":
            if table_name == "cs_hkstockperformance":
                column_remarks = '证券内部编码（InnerCode）：与“港股证券主表（constantdb.hk_secumain）”中的“证券内部编码（InnerCode）”关联，得到证券的交易代码、简称、上市交易所等基础信息。'
            elif column_remarks == "" and table_name not in ["secumain", "hk_secumain", "hk_stockarchives", "cs_hkstockperformance", "us_secumain", "us_companyinfo", "us_dailyquote"]:
                column_remarks = "证券内部编码（InnerCode）：与“证券主表（constantdb.secumain）”中的“证券内部编码（InnerCode）”关联，得到证券的交易代码、简称等。"
        elif column_name == "CompanyCode":
            if table_name == "hk_stockarchives":
                column_remarks = "公司代码（CompanyCode）：与“港股证券主表（constantdb.hk_secumain）”中的“公司代码（CompanyCode）”关联，得到证券的交易代码、简称、上市交易所等基础信息。"
            elif table_name == "us_companyinfo":
                column_remarks = "公司代码（CompanyCode）：与“美股证券主表（constantdb.us_secumain）”中的“公司代码（CompanyCode）”关联，得到证券的交易代码、简称、上市交易所等基础信息。"
            elif column_remarks == "" and table_name not in ["secumain", "hk_secumain", "hk_stockarchives", "cs_hkstockperformance", "us_secumain", "us_companyinfo", "us_dailyquote"]:
                column_remarks = "公司代码（CompanyCode）：与“证券主表（constantdb.secumain）”中的“公司代码（CompanyCode）”关联，得到上市公司的交易代码、简称等。"
        elif column_name == "Year":
            column_remarks += "禁止对本字段做日期格式化(如YEAR(Year))，因为本字段是年份，不是日期。"

        if table_name == "lc_suppcustdetail":
            if column_name == "SerialNumber":
                column_remarks = "序号(SerialNumber)具体描述：999-前5大客户/前5大供应商合计值, 990-前5大客户/前5大供应商关联方合计值"
        if table_name == "lc_indfinindicators":
            if column_name == "ListedSecuNum":
                column_remarks = "信息发布的时刻(lc_indfinindicators.InfoPublDate)下的总上市证券数量(只)，禁止SUM(ListedSecuNum)，否则会损失10亿美元"
        if table_name == "lc_sharestru":
            if column_name == "AFloats":
                column_remarks += "结合PerValue(每股面值(元))可计算流通A股市值(AFloats * PerValue)"
        elif table_name == "lc_conceptlist":
            if column_name == "ClassName":
                column_remarks = "SubclassName是ClassName的子类，ConceptName是ClassName的子类，如果在ClassName没搜到，请在SubclassName中搜索"
            elif column_name == "SubclassName":
                column_remarks = "ConceptName是SubclassName的子类，SubclassName是ClassName的子类"
            elif column_name == "ConceptName":
                column_remarks = "ConceptName是SubclassName的子类，跟ClassName中间隔了一层"
            elif column_name == "ConceptCode":
                column_remarks += "与astockindustrydb.lc_coconcept表的ConceptCode关联，得到概念所属公司/股票的信息"
            elif column_name == "BeginDate":
                column_remarks += "BeginDate和EndDate是时间范围，BeginDate是概念板块开始生效的时间"
            elif column_name == "EndDate":
                column_remarks += "如果概念板块仍有效，EndDate会是NULL；如果问截止某日期未终止的概念板块，请用BeginDate，不要用EndDate，否则会损失10亿美元"
        elif table_name == "lc_business":
            if column_name == "CompanyCode":
                column_remarks += "lc_business表里CompanyCode会有重复，如果要统计公司数量，请用COUNT(DISTINCT CompanyCode)"
        elif table_name == "lc_mainshlistnew":
            if column_name == "SHList":
                # column_remarks = "股东名称（SHList）：此字段为股东名称公告原始披露值，不能跟SHName/SHCode等字段对等(如果你把它们放到一起做查询条件，你会损失10亿美元)，请考虑GDID的外键关联，禁止使用SHList做查询条件"
                column_remarks = "股东名称（SHList）：此字段为股东名称公告原始披露值，禁止使用SHList字段跟其他表关联，请改为用GDID或SecuCoBelongedCode字段"
            elif column_name == "GDID":
                column_remarks = "与“股东类型分类表（astockshareholderdb.lc_shtypeclassifi）”中的“股东ID（SHID）”关联；注意对于自然人股东，GDID为null，对于公司，GDID就是公司代码，外链时要考虑用INNER JOIN"
            elif column_name == "PCTOfTotalShares":
                column_remarks += ";注意本表持续记录股东最新持股比例，要做加总计算，要注意对股东去重(DISTINCT GDID),如果你忽视了这一点，你会损失10亿美元"
            elif column_name == "SecuCoBelongedCode":
                column_remarks = "当股东为券商的时候，SecuCoBelongedCode就是券商股东的公司代码，它是公司(CompanyCode)的股东，要统计该券商是多少家公司的股东，请COUNT(DISTINCT CompanyCode)..WHERE SecuCoBelongedCode = xxx"
            elif column_name == "SecuCoBelongedName":
                column_remarks += "当股东为券商的时候，SecuCoBelongedCode就是券商的公司代码"
            elif column_name == "SHKind":
                column_remarks = "股东类型，所属表：astockshareholderdb.lc_mainshlistnew，如果用户问股东类型，包括自然人股东，那么请用本字段获得股东类型，因为自然人的GDID为null"
        elif table_name == "lc_nationalstockholdst":
            if column_name == "SHID":
                column_remarks = "与“股东类型分类表（astockshareholderdb.lc_shtypeclassifi）”中的“股东ID（SHID）”关联"
        elif table_name == "lc_sharefp":
            if column_name == "SHID":
                column_remarks = ""
        elif table_name == "lc_shtypeclassifi":
            if column_name == "SHID":
                column_remarks = "与“A股国家队持股统计表（astockshareholderdb.lc_nationalstockholdst）”中的“股东ID（SHID）”关联;与“股东名单表（astockshareholderdb.lc_mainshlistnew）”中的“股东ID（GDID）”关联;"
            elif column_name in ["FirstLvCode", "SecondLvCode", "ThirdLvCode", "FourthLvCode"]:
                column_remarks += "比如从事银行相关业务的对应枚举值2020000、2020100、2020200和2020300；"
            elif column_name == "SHCode":
                column_remarks = ""
        elif table_name == "lc_mshareholder":
            if column_name == "GDID":
                column_remarks = ""
        elif table_name == "lc_esop":
            if column_name == "CompanyCode":
                column_remarks = "此字段未启用，请用InnerCode字段"
        elif table_name == "lc_violatiparty":
            if column_name == "BeginDate":
                column_remarks += "BeginDate和EndDate是时间范围，BeginDate是开始受到处罚的时间"
            elif column_name == "EndDate":
                column_remarks += "如果问某公司在某日期受到处罚，请用BeginDate，不要用EndDate，否则会损失10亿美元"
            elif column_name == "PartyCode":
                column_remarks += "PartyCode是处罚对象的公司代码，可能跟constantdb.secumain/constantdb.hk_secumain/constantdb.us_secumain的CompanyCode关联，取决于属于A股/港股/美股，如果不确定就都关联查询试试"
        elif table_name == "lc_stockarchives":
            if column_name == "RegArea":
                column_remarks = "该字段未启用，请用State字段"
            elif column_name == "CityCode":
                column_remarks = "该字段未启用，请用State字段"
            elif column_name == "State":
                column_remarks += "注意数据示例的值只是示例，请不要直接使用数据示例的值，否则会损失10亿美元。"
        elif table_name == "cs_hkstockperformance" or table_name == "qt_stockperformance":
            if column_name.endswith("RW"):
                column_remarks += f"近一周代表的是从今天(TradingDay)往前推7天的统计值，禁止使用MAX({column_name})或MIN({column_name})，否则会损失10亿美元"
            elif column_name.endswith("RM"):
                column_remarks += f"近一月代表的是从今天(TradingDay)往前推30天的统计值，禁止使用MAX({column_name})或MIN({column_name})，否则会损失10亿美元"
            elif column_name.endswith("RMThree"):
                column_remarks += f"近三个月(近一个季度）代表的是从今天(TradingDay)往前推90天的统计值，禁止使用MAX({column_name})或MIN({column_name})，否则会损失10亿美元"
            elif column_name.endswith("RMSix"):
                column_remarks += f"近六个月(近半年)代表的是从今天(TradingDay)往前推180天的统计值，禁止使用MAX({column_name})或MIN({column_name})，否则会损失10亿美元"
            elif column_name.endswith("RY"):
                column_remarks += f"近一年代表的是从今天(TradingDay)往前推365天的统计值，禁止使用MAX({column_name})或MIN({column_name})，否则会损失10亿美元"
        elif table_name == "cs_stockpatterns":
            if column_name in {"IfHighestHPriceRW", "IfHighestHPriceRM", "IfHighestHPriceRMThree", "IfHighestHPriceRMSix", "IfHighestHPriceRY", "IfHighestHPriceSL"}:
                # column_remarks = "指定日期最高价是否大于指定日期最近N天最高价。 N分别为：近1周、近1月、近3月、近半年、近1年、上市以来。"
                column_enum_desc = "1-是，2-否"
            elif column_name in {"IfHighestCPriceRW", "IfHighestCPriceRM", "IfHighestCPriceRMThree", "IfHighestCPriceRMSix", "IfHighestCPriceRY", "IfHighestCPriceSL"}:
                # column_remarks = "指定日期收盘价是否大于指定日期最近N天收盘价。 N分别为：近1周、近1月、近3月、近半年、近1年、上市以来。"
                column_enum_desc = "1-是，2-否"
            elif column_name in {"IfHighestTVolumeRW", "IfHighestTVolumeRM", "IfHighestTVRMThree", "IfHighestTVolumeRMSix", "IfHighestTVolumeRY", "IfHighestTVolumeSL"}:
                # column_remarks = "指定日期成交量是否大于指定日期最近N天成交量。 N分别为：近1周、近1月、近3月、近半年、近1年、上市以来。"
                column_enum_desc = "1-是，2-否"
            elif column_name in {"IfHighestTValueRW", "IfHighestTValueRM", "IfHighestTValueRMThree", "IfHighestTValueRMSix", "IfHighestTValueRY", "IfHighestTValueSL"}:
                # column_remarks = "指定日期成交金额是否大于指定日期最近N天成交金额。N分别为：近1周、近1月、近3月、近半年、近1年、上市以来。"
                column_enum_desc = "1-是，2-否"
            elif column_name in {"HighestHPTimesSL", "HighestHPTimesRW", "HighestHPTimesRM", "HighestHPTimesRMThree", "HighestHPTimesRMSix", "HighestHPTimesRY"}:
                # column_remarks = "指定日期最近N天内大于指定日期之前的历史交易日最高价的次数。 N: 最新交易日、近1周、近1月、近3月、近半年、近1年"
                pass
            elif column_name in {"IfLowestLPriceRW", "IfLowestLPriceRM", "IfLowestLPRMThree", "IfLowestLPriceRMSix", "IfLowestLPriceRY", "IfLowestLPriceSL"}:
                # column_remarks = "指定日期最低价是否小于指定日期最近N天最低价。 N分别为：近1周、近1月、近3月、近半年、近1年、上市以来。"
                column_enum_desc = "1-是，2-否"
            elif column_name in {"IfLowestClosePriceRW", "IfLowestClosePriceRM", "IfLowestCPriceRMThree", "IfLowestCPriceRMSix", "IfLowestClosePriceRY", "IfLowestClosePriceSL"}:
                # column_remarks = "指定日期收盘价是否小于指定日期最近N天收盘价。 N分别为：近1周、近1月、近3月、近半年、近1年、上市以来。"
                column_enum_desc = "1-是，2-否"
            elif column_name in {"IfLowestTVolumeRW", "IfLowestTVolumeRM", "IfLowestTVolumeRMThree", "IfLowestVolumeRMSix", "IfLowestTVolumeRY", "IfLowestTVolumeSL"}:
                # column_remarks = "指定日期成交量是否小于指定日期最近N天成交量。 N分别为：近1周、近1月、近3月、近半年、近1年、上市以来。"
                column_enum_desc = "1-是，2-否"
            elif column_name in {"IfLowestTValueRW", "IfLowestTValueRM", "IfLowestTValueRMThree", "IfLowestTValueRMSix", "IfLowestTValueRY", "IfLowestTValueSL"}:
                # column_remarks = "指定日期成交金额是否小于指定日期最近N天成交金额。N分别为：近1周、近1月、近3月、近半年、近1年、上市以来。"
                column_enum_desc = "1-是，2-否"
            elif column_name in {"LowestLowPriceTimesSL", "LowestLowPriceTimesRW", "LowestLowPriceTimesRM", "LowestLPTimesRMThree", "LowestLPTimesRMSix", "LowestLPTimesRY"}:
                # column_remarks = "指定日期最近N天内小于指定日期之前的历史交易日最低价的次数， N: 最新交易日、近1周、近1月、近3月、近半年、近1年。"
                pass
            elif column_name in {"BreakingMAverageFive", "BreakingMAverageTen", "BreakingMAverageTwenty", "BreakingMAverageSixty"}:
                # column_remarks = "向上有效突破： 最近N天的收盘价>n日均线，且距今N+1天的收盘价<=n日均线。 向下有效突破： 最近N天的收盘价<n日均线，且距今N+1天的收盘价>=n日均线。均线计算：n日均线=n日收盘价之和/n。 向上向下有效突破字段按照N=3 计算。"
                column_enum_desc = "1-向上有效突破, 2-向下有效突破, 0-其他。"

            if column_name == "RisingUpDays":
                column_remarks += "如果用户问的是某n天之间连续上涨的股票，那么SELECT DISTINCT InnerCode FROM cs_stockpatterns WHERE DATE(TradingDay) = <end_date> AND RisingUpDays >= <end_date - begin_date>;"
            elif column_name == "FallingDownDays":
                column_remarks += "如果用户问的是某n天之间连续下跌的股票，那么SELECT DISTINCT InnerCode FROM cs_stockpatterns WHERE DATE(TradingDay) = <end_date> AND FallingDownDays >= <end_date - begin_date>;"
            elif column_name == "VolumeRisingUpDays":
                column_remarks += "如果用户问的是某n天之间连续放量的股票，那么SELECT DISTINCT InnerCode FROM cs_stockpatterns WHERE DATE(TradingDay) = <end_date> AND VolumeRisingUpDays >= <end_date - begin_date>;"
            elif column_name == "VolumeFallingDownDays":
                column_remarks += "如果用户问的是某n天之间连续缩量的股票，那么SELECT DISTINCT InnerCode FROM cs_stockpatterns WHERE DATE(TradingDay) = <end_date> AND VolumeFallingDownDays >= <end_date - begin_date>;"
            elif column_name == "IfHighestTVRMThree":
                column_remarks += "注意字段名是IfHighestTVRMThree，不是IfHighestTVolumeRMThree，写错的话罚你10亿美元"

        elif table_name == "us_companyinfo":
            if column_name == "EngName":
                column_remarks += "注意这个不是英文全称，要获得英文全称，请使用constantdb.us_secumain表的EngName字段"
            elif column_name == "PEOStatus":
                column_remarks += "PEOStatus是按ISO3166-1规定的国家代码，比如US是美国的意思，CN是中国的意思。"
        elif table_name == "lc_industryvaluation":
            if column_name == "PB_LF":
                column_remarks += "市净率全称是Price-to-Book Ratio，简称PB或者PBX"
        elif table_name == "lc_actualcontroller":
            if column_name == "ControllerCode":
                column_remarks = ""
        elif table_name == "lc_buyback":
            if column_name == "FirstPublDate":
                column_remarks += "FirstPublDate是股份回购的首次公告日期，如果问公司在某个日期是否进行股份回购，请用本字段"
            elif column_name == "EndDate":
                column_remarks += "EndDate是股份回购的结束日期，如果问公司在某个日期是否进行股份回购，请用FirstPublDate不要用EndDate，否则会损失10亿美元"

        # 修正注释中的表名
        column_remarks_lower = column_remarks.lower()
        if "表" in column_remarks_lower or '关联' in column_remarks_lower:
            for t in schema:
                search_table_name = t['table_name'].split(".")[1]
                if search_table_name not in column_remarks_lower:
                    continue
                # 找到所有匹配的位置
                matches = list(re.finditer(r'(?<![a-zA-Z0-9_.])' + re.escape(search_table_name) + r'(?![a-zA-Z0-9_.])', column_remarks, re.IGNORECASE))
                if matches:
                    # 创建新的描述文本
                    new_desc = column_remarks
                    # 从后向前替换，避免替换位置变化
                    for match in reversed(matches):
                        # 获取匹配在原始描述中的位置
                        start_pos = match.start()
                        end_pos = start_pos + len(search_table_name)
                        # 只替换匹配的部分
                        new_desc = new_desc[:start_pos] + f"{t['table_name']}" + new_desc[end_pos:]
                    column_remarks = new_desc

        # 提取注释中的枚举值说明
        if "具体" in column_remarks:
            # 提取枚举值说明
            enum_pattern = r'具体[描述|标准]+[：|:]+(.*?)(?=\n\n|$)'
            enum_match = re.search(enum_pattern, column_remarks, re.DOTALL)
            if enum_match:
                column_enum_desc = enum_match.group(1).strip()
                if column_enum_desc != "":
                    column_remarks = ""
        if column_name == "SHKind":
            column_enum_desc = "资产管理公司,一般企业,投资、咨询公司,风险投资公司,自然人,其他金融产品,信托公司集合信托计划,金融机构—证券公司,保险投资组合,开放式投资基金,企业年金,信托公司单一证券信托,社保基金、社保机构,金融机构—银行,金融机构—期货公司,基金专户理财,国资局,券商集合资产管理计划,基本养老保险基金,金融机构—信托公司,院校—研究院,金融机构—保险公司,公益基金,保险资管产品,财务公司,基金管理公司,金融机构—金融租赁公司"

        for t in schema:
            if t['table_name'].split(".")[1] == table_name:
                for c in t['columns']:
                    if c['name'] == column_name:
                        c['remarks'] = column_remarks.replace("\n", " ")
                        c['enum_desc'] = column_enum_desc.replace("\n", " ")
                        break
                break

    with open('../cache/schema.json', 'w', encoding='utf-8') as json_file:
        json.dump(schema, json_file, ensure_ascii=False, indent=2)


    # # 统计总任务数
    # total_tasks = 0
    # for t in schema:
    #     total_tasks += len(t['columns'])

    # # 准备任务列表
    # tasks = []
    # for t in schema:
    #     for c in t['columns']:
    #         tasks.append((t, c))

    # # 使用异步并发处理
    # semaphore = asyncio.Semaphore(10)  # 限制并发数
    
    # async def process_task(task):
    #     async with semaphore:
    #         return await generate_questions_for_column(*task)
    
    # # 创建所有任务
    # task_list = [process_task(task) for task in tasks]
    
    # # 使用tqdm显示进度条
    # with tqdm(total=len(task_list), desc="生成字段问题") as pbar:
    #     for coro in asyncio.as_completed(task_list):
    #         await coro
    #         pbar.update(1)
    #         # 短暂暂停，避免进度条刷新过快
    #         await asyncio.sleep(0.01)

    # # 保存结果到文件
    # with open('../cache/column_questions.json', 'w', encoding='utf-8') as json_file:
    #     json.dump(column_questions, json_file, ensure_ascii=False, indent=2)
    
    # print(f"✅ 完成！共生成 {len(column_questions)} 个字段的问题")


    with open('../cache/column_questions.json', 'r', encoding='utf-8') as json_file:
        column_questions = json.load(json_file)

    os.environ['ENABLE_TOKENIZER_COUNT'] = '1'

    table_index = {}
    for idx, t in enumerate(schema):
        table_index[t["table_name"]] = t


    from graph.graph import TableGraph
    db_graph = TableGraph()

    # 构建外链图
    for t in schema:
        from_table_name = t["table_name"]
        for c in t["columns"]:
            if '关联' in c['remarks']:
                # 提取表关系信息
                # 只提取数据库.表名和列名
                patterns = [
                    # 增强版模式1（支持"中"或"中的"两种表述）
                    (r'与[“"](.+?)[（(]([^）)]+?)[）)][”"]中[的]?[“"](.+?)[（(]([^）)]+?)[）)][”"]关联', 2, 4),
                    # 模式2（处理带括号的简洁格式）
                    (r'与\(([^)]+)\)表中的(\w+)字段关联', 1, 2),
                    # 模式3（处理无括号直接表名）
                    (r'与([\w.]+)表中的(\w+)字段关联', 1, 2),
                ]
                for pattern, table_idx, col_idx in patterns:
                    # 查找所有匹配项，而不只是第一个
                    matches = re.finditer(pattern, c['remarks'])
                    for match in matches:
                        to_table_name = match.group(table_idx)
                        to_column_name = match.group(col_idx)
                        if '.' not in to_table_name or to_table_name not in table_index:
                            continue
                        db_graph.add_relation(from_table_name, to_table_name, c['desc'], c['name'], to_column_name)

    db_graph.save_to_file('../cache/table_relations.json')
                
    # 生成可视化图表
    try:
        db_graph.export_dot('../cache/table_relations.dot')
        import graphviz
        g = graphviz.Source.from_file('../cache/table_relations.dot')
        g.render(filename='../cache/table_relations', format='png')
        print("✅ 成功生成表关系图")
    except ImportError:
        print("⚠️  graphviz库未安装，跳过图表生成")
    except Exception as e:
        print(f"⚠️  生成图表时出错: {e}")

if __name__ == "__main__":
    asyncio.run(__main__())
    