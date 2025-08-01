import numpy as np
import json
import os
import sys

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, backend_dir)

# 先导入config，确保utils可以找到它
from config import config

# 现在导入utils
from utils import find_similar_texts
from embedding.embedding import HuggingFaceEmbedding


collections = [
    [
        "天士力在2020年最新的担保事件是什么？答案包括事件内容、担保方、被担保方、担保金额和日期信息",
        "SELECT lw.EventContent, lw.GuarantorCompany, lw.ObjectName, ROUND(lw.LatestGuaranteeSum, 1) AS LatestGuaranteeSum, DATE_FORMAT(lw.InitialInfoPublDate, '%Y年%m月%d日') AS DateInfo FROM astockeventsdb.lc_warrant AS lw WHERE lw.CompanyCode = 1474 AND YEAR(lw.InitialInfoPublDate) = 2020 ORDER BY lw.InitialInfoPublDate DESC LIMIT 1;"
    ],
    [
        "2021年末，按新版申万行业分类，现在韵达股份属于什么申万一级行业？",
        "SELECT a.FirstIndustryName, FirstIndustryCode FROM astockindustrydb.lc_exgindustry AS a WHERE a.CompanyCode = 4090 AND a.Standard = 38 AND YEAR(a.InfoPublDate) = '2021' ORDER BY a.InfoPublDate DESC LIMIT 1;"
    ],
    [
        "2021年末，该一级行业中有几个股票？",
        "SELECT ListedSecuNum FROM astockindustrydb.lc_indfinindicators AS a WHERE a.Standard = 41 AND a.IndustryCode = '420000' AND YEAR(a.EndDate) = '2021' ORDER BY a.InfoPublDate DESC LIMIT 1;"
    ],
    [
        "2021年末，韵达股份的A股流通市值是多少？",
        "SELECT c.NegotiableMV FROM astockmarketquotesdb.qt_stockperformance AS c WHERE c.InnerCode = 4990 AND YEAR(c.TradingDay) = '2021' ORDER BY c.TradingDay DESC LIMIT 1;"
    ],
    [
        "2021年末，该一级行业的A股流通市值是多少？",
        "SELECT a.NegotiableMV FROM astockindustrydb.lc_industryvaluation AS a WHERE a.Standard = 41 AND a.IndustryCode = '420000' AND YEAR(a.TradingDay) = '2021' ORDER BY a.TradingDay DESC LIMIT 1;"
    ],
    [
        "上海证券交易所录入的322家公司所在指数有多少种采用新申万行业分类的？",
        "SELECT COUNT(DISTINCT i.IndexCode) AS IndexCount FROM constantdb.secumain s JOIN indexdb.lc_indexcomponent c ON s.InnerCode = c.SecuInnerCode JOIN indexdb.lc_indexbasicinfo i ON c.IndexInnerCode = i.IndexCode WHERE s.SecuMarket = 83 AND i.IndustryStandard = 38;"
    ],
    [
        "2019到2020这两年在研发上的投入总额分别是多少？研发投入占主营收入的比例分别是多少？",
        "SELECT a.TotalRDInput AS TotalRDInput2019, a.RDInputRatio AS RDInputRatio2019, b.TotalRDInput AS TotalRDInput2020, b.RDInputRatio AS RDInputRatio2020 FROM (SELECT TotalRDInput, RDInputRatio FROM astockfinancedb.lc_intassetsdetail WHERE InnerCode = 12064 AND YEAR(EndDate) = 2019 ORDER BY InfoPublDate DESC LIMIT 1) AS a, (SELECT TotalRDInput, RDInputRatio FROM astockfinancedb.lc_intassetsdetail WHERE InnerCode = 12064 AND YEAR(EndDate) = 2020 ORDER BY InfoPublDate DESC LIMIT 1) AS b;"
    ],
    [
        "欣旺达电子在2020年的分红金额是多少？",
        "SELECT SUM(a.TotalCashDiviComRMB) AS TotalDividend FROM astockfinancedb.lc_dividend AS a WHERE a.InnerCode in (12972, 7123895) AND YEAR(a.EndDate) = 2020 AND a.IfDividend = 1;"
    ],
    [
        "欣旺达电子2021年分红公告发布前1个交易日和公告发布后的收盘价分别是多少？公告发布当天的涨跌幅为多少？",
        "SELECT c.ClosePrice AS PreAnnouncementClosePrice, d.ClosePrice AS PostAnnouncementClosePrice, (d.ClosePrice - c.ClosePrice) / c.ClosePrice * 100 AS PriceChangePercentage, DATE(a.DividendImplementDate) AS AnnouncementDate FROM astockfinancedb.lc_dividend AS a JOIN astockmarketquotesdb.qt_dailyquote AS c ON a.InnerCode = c.InnerCode AND DATE(c.TradingDay) = DATE_SUB(a.DividendImplementDate, INTERVAL 1 DAY) JOIN astockmarketquotesdb.qt_dailyquote AS d ON a.InnerCode = d.InnerCode AND DATE(d.TradingDay) = DATE(a.DividendImplementDate) WHERE a.InnerCode in (12972, 7123895) AND YEAR(a.DividendImplementDate) = 2021 ORDER BY a.EndDate DESC LIMIT 1;"
    ],
    [
        "欣旺达电子2021年属于什么行业？",
        "SELECT Industry FROM astockindustrydb.lc_exgindustry AS g WHERE g.CompanyCode = 119611 AND YEAR(g.InfoPublDate) = 2021 ORDER BY g.InfoPublDate DESC LIMIT 1;"
    ],
    [
        "欣旺达电子2021年同一行业其他公司的分红金额是多少？",
        "SELECT a.InnerCode, SUM(a.TotalCashDiviComRMB) AS TotalDividend FROM astockfinancedb.lc_dividend AS a JOIN constantdb.secumain AS c ON a.InnerCode = c.InnerCode JOIN astockindustrydb.lc_exgindustry AS b ON c.CompanyCode = b.CompanyCode WHERE b.Industry = ( SELECT Industry FROM astockindustrydb.lc_exgindustry WHERE CompanyCode = 119611 AND YEAR(InfoPublDate) = 2021 ORDER BY InfoPublDate DESC LIMIT 1 ) AND YEAR(a.EndDate) = 2021 AND a.IfDividend = 1 GROUP BY a.InnerCode;"
    ],
    [
        "最新更新的2020半年报中，机构持有无限售流通A股数量合计最多的公司中文简称是？在这份报告中，机构持有无限售流通A股比例合计是多少？前十大股东持股比例合计是多少？",
        "SELECT b.ChiNameAbbr, a.InstitutionsHoldPropT, a.Top10StockholdersProp FROM astockshareholderdb.lc_stockholdingst AS a JOIN constantdb.secumain AS b ON a.InnerCode = b.InnerCode WHERE DATE(a.EndDate) = '2020-06-30' ORDER BY a.InstitutionsHoldings DESC LIMIT 1;"
    ],
    [
        "华夏基金管理有限公司在19年成立了多少支基金？",
        "SELECT COUNT(*) AS FundCount FROM publicfunddb.mf_fundarchives AS a JOIN publicfunddb.mf_investadvisoroutline AS b ON a.InvestAdvisorCode = b.InvestAdvisorCode WHERE b.InvestAdvisorName = '华夏基金管理有限公司' AND YEAR(a.EstablishmentDate) = 2019;"
    ],
    [
        "华夏基金管理有限公司在19年成立的基金中哪支基金的规模最大？",
        "SELECT b.InnerCode, b.SecuCode, b.FoundedSize, c.ChiName FROM publicfunddb.mf_investadvisoroutline AS a JOIN publicfunddb.mf_fundarchives AS b ON a.InvestAdvisorCode = b.InvestAdvisorCode JOIN constantdb.secumain AS c ON b.InnerCode = c.InnerCode WHERE a.InvestAdvisorName = '华夏基金管理有限公司' AND YEAR(b.EstablishmentDate) = 2019 ORDER BY b.FoundedSize DESC LIMIT 1;"
    ],
    [
        "这支基金20年最后一次分红派现比例多少？",
        "SELECT d.ActualRatioAfterTax, d.DividendRatioBeforeTax FROM publicfunddb.mf_dividend AS d WHERE d.InnerCode = 264422 AND YEAR(d.EndDate) = 2020 AND d.IfDistributed = 1 ORDER BY d.EndDate DESC LIMIT 1;"
    ],
    [
        "天顺风能在2020到2021这两年间的股票平均收益率是百分之多少？",
        "SELECT ROUND(AVG(a.MarketIndexRORGeomMean), 4) AS AvgROR FROM astockmarketquotesdb.qt_stockperformance AS a WHERE a.InnerCode = 12064 AND YEAR(a.TradingDay) BETWEEN 2020 AND 2021;"
    ],
    [
        "天顺风能在2019到2021这三年间的分红金额总计是多少？",
        "SELECT SUM(a.TotalCashDiviComRMB) AS TotalDividend FROM astockfinancedb.lc_dividend AS a WHERE a.InnerCode = 12064 AND YEAR(a.EndDate) BETWEEN 2019 AND 2021 AND a.IfDividend = 1;"
    ],
    [
        "天顺风能的第一大股东在2019到2021年这三年间持股比例变化趋势如何？",
        "SELECT YEAR(c.EndDate) AS Year, AVG(c.PCTOfTotalShares) AS AvgHoldRatio FROM astockshareholderdb.lc_mainshlistnew AS c WHERE c.CompanyCode = 81722 AND c.InfoTypeCode = 1 AND c.SHNo = 1 AND YEAR(c.EndDate) BETWEEN 2019 AND 2021 GROUP BY YEAR(c.EndDate) ORDER BY YEAR(c.EndDate);"
    ],
    [
        "新科技的概念代码是什么？",
        "SELECT ClassCode FROM astockindustrydb.lc_conceptlist WHERE ClassName = '新科技' LIMIT 1;\nSELECT SubclassCode FROM astockindustrydb.lc_conceptlist WHERE SubclassName = '新科技' LIMIT 1;\nSELECT ConceptCode FROM astockindustrydb.lc_conceptlist WHERE ConceptName = '新科技' LIMIT 1;"
    ],
    [
        "000778公司2021年主营业务产品有哪些？",
        "SELECT DISTINCT m.Project FROM astockfinancedb.lc_mainoperincome AS m JOIN constantdb.secumain AS s ON m.CompanyCode = s.CompanyCode WHERE s.SecuCode = '000778' AND DATE(m.EndDate) = '2021-12-31';"
    ],
    [
        "交易日在2021-10-01到2021-10-31之间，近一月换手率超过10%的港股中股价下跌最多的公司是？",
        "SELECT subquery.SecuAbbr FROM (SELECT a.SecuAbbr, MIN(b.ChangePCTRM) AS MinChangePCT FROM constantdb.hk_secumain a JOIN hkstockdb.cs_hkstockperformance b ON a.InnerCode = b.InnerCode WHERE DATE(b.TradingDay) BETWEEN '2021-10-01' AND '2021-10-31' AND b.TurnoverRateRM > 10 GROUP BY a.SecuAbbr) AS subquery ORDER BY subquery.MinChangePCT ASC LIMIT 1;"
    ],
    [
        "交易日在2021-10-01到2021-10-31之间，近一月换手率超过10%的港股中成交额最多的公司是哪家？",
        "SELECT subquery.ChiName FROM (SELECT a.ChiName, SUM(b.TurnoverValueRM) AS TotalTurnoverValue FROM constantdb.hk_secumain a JOIN hkstockdb.cs_hkstockperformance b ON a.InnerCode = b.InnerCode WHERE DATE(b.TradingDay) BETWEEN '2021-10-01' AND '2021-10-31' AND b.TurnoverRateRM > 10 GROUP BY a.ChiName) AS subquery ORDER BY subquery.TotalTurnoverValue DESC LIMIT 1;"
    ],
    [
        "交易日在2021-10-01到2021-10-31之间，近一月换手率超过10%的港股中平均涨跌幅最高的是哪家公司？",
        "SELECT subquery.ChiName FROM (SELECT a.ChiName, AVG(b.ChangePCTRM) AS AvgChangePCT FROM constantdb.hk_secumain a JOIN hkstockdb.cs_hkstockperformance b ON a.InnerCode = b.InnerCode WHERE DATE(b.TradingDay) BETWEEN '2021-10-01' AND '2021-10-31' AND b.TurnoverRateRM > 10 GROUP BY a.ChiName) AS subquery ORDER BY subquery.AvgChangePCT DESC LIMIT 1;"
    ],
    [
        "请根据双良节能在2020年Q4季度的研发人员数量和占比推算公司总人数（计算方式：总人数 = 研发人员数量 ÷ (研发人员占比 ÷ 100)，结果取整）。",
        "SELECT ROUND(RDStaffNum / (RDStaffNumRatio / 100)) AS TotalStaffNum FROM astockfinancedb.lc_intassetsdetail WHERE DATE(EndDate) BETWEEN '2020-10-01' AND '2020-12-31' AND InnerCode = 1626;"
    ],
    [
        "嘉实致元42个月定期债券基金的InnerCode是什么？",
        "SELECT DISTINCT InnerCode, DisclName FROM publicfunddb.mf_fundprodname WHERE DisclName LIKE '%嘉实致元42个月定期债券%';"
    ],
    [
        "该基金公司管理的基金里，哪只基金20年最后一次分红的税前分红最高，有多少？",
        "SELECT d.InnerCode, d.DividendRatioBeforeTax FROM publicfunddb.mf_dividend d JOIN ( SELECT InnerCode, MAX(EndDate) AS LastEndDate FROM publicfunddb.mf_dividend WHERE YEAR(EndDate) = 2020 AND InnerCode IN ( SELECT DISTINCT InnerCode FROM publicfunddb.mf_fundarchives WHERE InvestAdvisorCode = ( SELECT InvestAdvisorCode FROM publicfunddb.mf_fundarchives WHERE InnerCode = 239107 ) ) GROUP BY InnerCode ) latest ON d.InnerCode = latest.InnerCode AND d.EndDate = latest.LastEndDate ORDER BY d.DividendRatioBeforeTax DESC LIMIT 1;"
    ],
    [
        "该公司2019年的前五大客户中，各类型客户占总营收比例多少？",
        "SELECT RelatedPartyAttribute, ROUND(SUM(Ratio), 2) AS TotalRatio FROM astockoperationsdb.lc_suppcustdetail WHERE CompanyCode = 80194 AND YEAR(EndDate) = 2019 AND SerialNumber = 999 AND RelationType = 4 AND InfoSourceCode = 110101 GROUP BY RelatedPartyAttribute;"
    ],
    [
        "博时中债1-3年国开行债券在2019到2021年这三年间总共分红几次？",
        "SELECT COUNT(*) AS TotalDividends FROM publicfunddb.mf_dividend AS d WHERE d.InnerCode = 222408 AND YEAR(d.EndDate) BETWEEN 2019 AND 2021;"
    ],
    [
        "请统计在大于1亿份规模区间内基金的平均分红金额。",
        "SELECT AVG(d.DividendSumYTD) AS AvgDividendSum FROM publicfunddb.mf_fundarchives f JOIN publicfunddb.mf_dividend d ON f.InnerCode = d.InnerCode WHERE f.FoundedSize > 100000000;"
    ],
    [
        "重大诉讼仲裁公告发布后的30天窗口内，公司股价日波动率最高为多少？",
        "SELECT MAX((HighPrice - LowPrice) / LowPrice) AS MaxDailyVolatility FROM ( SELECT a.CompanyCode, b.InnerCode, c.TradingDay, c.HighPrice, c.LowPrice FROM astockeventsdb.lc_suitarbitration a JOIN constantdb.secumain b ON a.CompanyCode = b.CompanyCode JOIN astockmarketquotesdb.qt_dailyquote c ON b.InnerCode = c.InnerCode WHERE c.TradingDay BETWEEN DATE(a.InitialInfoPublDate) AND DATE_ADD(DATE(a.InitialInfoPublDate), INTERVAL 30 DAY) ) AS derived_table;"
    ],
    [
        "2019上市的股票型基金一共有多少支？",
        "SELECT COUNT(*) AS FundCount FROM publicfunddb.mf_fundarchives AS f WHERE YEAR(f.ListedDate) = 2019 AND f.FundTypeCode = '1101';"
    ],
    [
        "09年最后一次基金设立规模最大的是哪只？（回答基金代码）",
        "SELECT f.SecurityCode, f.FoundedSize, DATE(f.EstablishmentDate) FROM publicfunddb.mf_fundarchives AS f WHERE YEAR(f.EstablishmentDate) = 2019 AND f.FundTypeCode = '1101' ORDER BY f.EstablishmentDate DESC, f.FoundedSize DESC LIMIT 1;"
    ],
    [
        "2019年职工总数超过10000人的公司一共有多少家？",
        "SELECT COUNT(DISTINCT a.CompanyCode) AS CompanyCount FROM astockoperationsdb.lc_staff a WHERE a.ClassfiedMethod = 9000 AND YEAR(a.EndDate) = 2019 AND a.EmployeeSum > 10000;"
    ],
    [
        "该公司2019年的前十大股东中，主要从事'银行'相关业务的股东数量有多少个？",
        "SELECT COUNT(DISTINCT c.SHList) FROM astockshareholderdb.lc_mainshlistnew AS c WHERE c.CompanyCode = 72579 AND c.InfoTypeCode = 1 AND c.SHKind LIKE '%银行%' AND DATE(c.EndDate) = '2019-12-31';"
    ],
    [
        "该公司2019年的前十大股东的持股比例合计是多少？",
        "SELECT st.Top10StockholdersProp FROM astockshareholderdb.lc_stockholdingst st WHERE st.CompanyCode = 72579 AND DATE(st.EndDate) = '2019-12-31' AND st.Top10StockholdersProp IS NOT NULL ORDER BY st.StatDate DESC LIMIT 1;"
    ],
    [
        "该公司2019年的前十大股东中，除去从事'银行'相关业务的股东，其他类股东的持股比例之和是多少？",
        "SELECT SUM(c.PCTOfTotalShares) AS other_share_ratio FROM astockshareholderdb.lc_mainshlistnew AS c WHERE c.CompanyCode = 72579 AND c.InfoTypeCode = 1 AND c.SHKind not LIKE '%银行%' AND DATE(c.EndDate) = '2019-12-31'"
    ],
    [
        "海油发展在2019年召开了多少次股东大会？",
        "SELECT COUNT(DISTINCT a.Series) AS total_meetings_2019 FROM astockshareholderdb.lc_smattendinfo AS a WHERE a.CompanyCode = 72579 AND YEAR(a.MeetingDate) = 2019 AND a.IfEffected = 1 ORDER BY MeetingDate DESC"
    ],
    [
        "该公司2021年年报中主营业务收入合计是多少？",
        "SELECT MainOperIncome FROM astockfinancedb.lc_mainoperincome WHERE CompanyCode = 515 AND YEAR(EndDate) = 2021 AND Level = 0 ORDER BY EndDate DESC LIMIT 1;"
    ],
    [
        "波司登国际控股有限公司在2021年第一季度末(3月31日)的员工数量是多少？相比2020年底增加还是减少了多少人？",
        "SELECT QuaAfterChange, QuaAfterChange - QuaBeforeChange AS QuaChange FROM hkstockdb.hk_employeechange AS e JOIN constantdb.hk_secumain AS s ON e.InnerCode = s.InnerCode WHERE s.CompanyCode = 1006818 AND DATE(e.EffectiveDate) = '2021-03-31' AND e.IfEffected = 1;"
    ],
    [
        "波司登国际控股有限公司在2020年底的员工数量是多少？",
        "SELECT QuaAfterChange FROM hkstockdb.hk_employeechange AS e JOIN constantdb.hk_secumain AS s ON e.InnerCode = s.InnerCode WHERE s.CompanyCode = 1006818 AND YEAR(e.EffectiveDate) = '2020' AND e.IfEffected = 1 ORDER BY e.EffectiveDate DESC LIMIT 1;"
    ],
    [
        "该公司在2021年第一季度(1-3月)的股票最高价是多少港元？平均换手率是多少？",
        "SELECT MAX(HighPrice) AS MaxHighPrice, AVG(TurnoverRate) AS AvgTurnoverRate FROM hkstockdb.cs_hkstockperformance AS p JOIN constantdb.hk_secumain AS s ON p.InnerCode = s.InnerCode WHERE s.CompanyCode = 1006818 AND DATE(p.TradingDay) BETWEEN '2021-01-01' AND '2021-03-31';"
    ],
    [
        "在2021年第一季度（1-3月），波司登国际控股有限公司的股票振幅超过3%的天数有多少天？这些天的平均成交金额是多少港元？",
        "SELECT COUNT(*) AS DaysWithHighRange, AVG(TurnoverValue) AS AvgTurnoverValue FROM hkstockdb.cs_hkstockperformance AS p JOIN constantdb.hk_secumain AS s ON p.InnerCode = s.InnerCode WHERE s.CompanyCode = 1006818 AND DATE(p.TradingDay) BETWEEN '2021-01-01' AND '2021-03-31' AND p.RangePCT > 3;"
    ],
    [
        "陕西省的地区内部编码是多少？",
        "SELECT AreaInnerCode, AreaChiName FROM constantdb.lc_areacode WHERE AreaChiName LIKE '%陕西%';"
    ],
    [
        "截止到目前，陕西省共有多少家上市公司？",
        "SELECT COUNT(DISTINCT sm.CompanyCode) FROM constantdb.secumain AS sm JOIN astockbasicinfodb.lc_stockarchives AS sa ON sm.CompanyCode = sa.CompanyCode WHERE sa.State = ( SELECT AreaInnerCode FROM constantdb.lc_areacode WHERE AreaChiName LIKE '%陕西%' ) AND sm.ListedState = 1;"
    ],
    [
        "截止目前，陕西省的上市公司中，2020年总市值超过百亿的有多少家？",
        "SELECT COUNT(DISTINCT a.InnerCode) FROM astockmarketquotesdb.qt_stockperformance as a WHERE a.InnerCode IN ( SELECT DISTINCT sm.InnerCode FROM constantdb.secumain AS sm JOIN astockbasicinfodb.lc_stockarchives AS sa ON sm.CompanyCode = sa.CompanyCode WHERE sa.State = 144370000 AND sm.ListedState = 1 ) AND a.TotalMV > 100000000000 AND YEAR(a.TradingDay) = 2020;"
    ],
    [
        "在证券市场和证券类别相同的公司的员工持股计划的数量",
        "SELECT COUNT(*) AS PlanCount FROM astockshareholderdb.lc_esop WHERE InnerCode IN ( SELECT DISTINCT InnerCode FROM constantdb.secumain WHERE SecuMarket = ( SELECT SecuMarket FROM constantdb.secumain WHERE InnerCode = 9995 ) AND SecuCategory = ( SELECT SecuCategory FROM constantdb.secumain WHERE InnerCode = 9995 ) );"
    ],
    [
        "2020年10月27日哪家证券公司受到了处罚",
        "SELECT PartyName FROM creditdb.lc_violatiparty WHERE DATE(BeginDate) = '2020-10-27' AND PartyType = '2';"
    ],
    [
        "中信证券股份有限公司是多少家公司的股东？",
        "SELECT COUNT(DISTINCT a.CompanyCode) AS ShareholderCount FROM astockshareholderdb.lc_mainshlistnew AS a WHERE a.SHList = '中信证券股份有限公司';"
    ],
    [
        "中信证券股份有限公司作为股东的公司中，哪家（需回答公司全称）2020年的借贷最多，共计多少？",
        "SELECT b.ChiName AS CompanyFullName, SUM(c.FirstLoanSum) AS TotalLoanAmount FROM astockeventsdb.lc_credit AS c LEFT JOIN constantdb.secumain AS b ON c.CompanyCode = b.CompanyCode LEFT JOIN constantdb.us_secumain AS d ON c.CompanyCode = d.CompanyCode LEFT JOIN constantdb.hk_secumain AS e ON c.CompanyCode = e.CompanyCode WHERE YEAR(c.InitialInfoPublDate) = 2020 AND c.CompanyCode in (SELECT DISTINCT a.CompanyCode FROM astockshareholderdb.lc_mainshlistnew AS a WHERE a.SHList = '中信证券股份有限公司') GROUP BY c.CompanyCode, b.ChiName ORDER BY TotalLoanAmount DESC LIMIT 1;"
    ],
    [
        "2022年之间进行公司名称全称变更的公司代码是什么？",
        "SELECT DISTINCT CompanyCode FROM astockbasicinfodb.lc_namechange WHERE DATE(ChangeDate) BETWEEN '2022-01-01' AND '2022-12-31';"
    ],
    [
        "该股票的境内自然人持股和境外自然人持股分别是多少？",
        "SELECT DNaturalPersonHolding, FNaturalPersonHolding FROM astockshareholderdb.lc_sharestru AS a WHERE DATE(EndDate) = '2021-12-31' AND CompanyCode = 489;"
    ],
    [
        "卧龙电气驱动集团股份有限公司的注册地在哪个省份？",
        "SELECT a.State, b.AreaChiName FROM astockbasicinfodb.lc_stockarchives AS a JOIN constantdb.lc_areacode AS b ON a.State = b.AreaInnerCode WHERE a.CompanyCode = 1513;"
    ],
    [
        "该公司2019年年度报告中，未调整的合并资产负债表中提到的资产总计是多少？",
        "SELECT ROUND(TotalAssets, 1) AS TotalAssets FROM astockfinancedb.lc_balancesheetall WHERE CompanyCode = 1513 AND DATE(EndDate) = '2019-12-31' AND IfAdjusted = 2 AND IfMerged = 1;"
    ],
    [
        "最近一次非公开增发的数量是多少？",
        "SELECT ROUND(IssueVol, 1) AS IssueVol FROM astockfinancedb.lc_ashareseasonednewissue WHERE InnerCode = '1551' AND IssueType = '21' ORDER BY NewShareListDate DESC LIMIT 1;"
    ],
    [
        "截至2021年12月31日，欣旺达电子前十大股东名单及持股比例分别是多少？",
        "SELECT SHList, ROUND(PCTOfTotalShares, 6) AS PCTOfTotalShares FROM astockshareholderdb.lc_mainshlistnew WHERE DATE(EndDate) = '2021-12-31' AND InfoTypeCode = 1 AND CompanyCode = 119611 ORDER BY PCTOfTotalShares DESC;"
    ],
    [
        "截止2023-12-3，该2级概念下一共有几个未终止的概念板块？",
        "SELECT COUNT(*) FROM astockindustrydb.lc_conceptlist AS a WHERE a.SubclassName = '制造2025' AND a.ConceptState = 1 AND DATE(a.BeginDate) <= '2023-12-03';"
    ],
    [
        "芯片概念概念板块的英文名称是什么？",
        "SELECT ConceptEngName,ConceptName FROM astockindustrydb.lc_conceptlist AS a WHERE a.ConceptName = '芯片概念';"
    ],
    [
        "哪三个一级行业在2021年1月股价波动性最高？",
        "SELECT e.FirstIndustryName, AVG(p.RangePCT) AS AvgRangePCT FROM astockmarketquotesdb.qt_stockperformance p JOIN constantdb.secumain s ON p.InnerCode = s.InnerCode JOIN astockindustrydb.lc_exgindustry e ON s.CompanyCode = e.CompanyCode WHERE DATE(p.TradingDay) BETWEEN '2021-01-01' AND '2021-01-31' GROUP BY e.FirstIndustryName ORDER BY AvgRangePCT DESC LIMIT 3;"
    ],
    [
        "截至2021-12-31，岩山科技的股份回购总金额是多少？",
        "SELECT SUM(BuybackMoney) AS TotalBuybackMoney FROM astockshareholderdb.lc_buyback WHERE CompanyCode = 73222 AND DATE(EndDate) <= '2021-12-31';"
    ],
    [
        "截至2021年12月31日，居然之家股本变动发生变化的原因分别是什么？",
        "SELECT ChangeType, ChangeReason, ROUND(TotalShares, 4) AS TotalShares FROM astockshareholderdb.lc_sharestru WHERE CompanyCode = 385 AND DATE(EndDate) <= '2021-12-31' AND ChangeType IS NOT NULL AND ChangeReason IS NOT NULL;"
    ],
    [
        "居然之家在这五天股价波动的幅度是多少？",
        "SELECT AVG(RangePCT) AS AvgRangePCT FROM astockmarketquotesdb.qt_stockperformance WHERE InnerCode = 442 AND DATE(TradingDay) BETWEEN '2019-12-20' AND '2019-12-24';"
    ],
    [
        "该年度前十大股东的持股比例变成了多少？",
        " SELECT Top10StockholdersProp, EndDate FROM astockshareholderdb.lc_stockholdingst WHERE CompanyCode = 1606 AND YEAR(EndDate) = 2019 AND Top10StockholdersProp IS NOT NULL ORDER BY EndDate DESC LIMIT 1;"
    ],
    [
        "2019年公司的技术与生产人员一共有多少人？",
        "SELECT SUM(EmployeeSum) AS TotalTechProdStaff FROM astockoperationsdb.lc_staff WHERE CompanyCode = 1606 AND DATE(EndDate) = '2019-12-31' AND ClassfiedMethod = 3000 AND ( TypeCode = 3035 OR TypeCode = 3031 );"
    ],
    [
        "当日哪家公司（需回答公司全称）收盘价最高，最高价是多少？",
        "SELECT b.ChiName, MAX(c.ClosePrice) AS HighestClosePrice FROM astockmarketquotesdb.qt_dailyquote AS c JOIN constantdb.secumain AS b ON c.InnerCode = b.InnerCode WHERE DATE(c.TradingDay) = '2020-02-07' GROUP BY b.ChiName ORDER BY HighestClosePrice DESC LIMIT 1;"
    ],
    [
        "2021年第三季报中，该公司的国有股东持股总和是多少？",
        "SELECT ROUND(SUM(b.HoldSum), 1) AS TotalHoldSum FROM constantdb.secumain AS a JOIN astockshareholderdb.lc_mainshlistnew AS b ON a.CompanyCode = b.CompanyCode WHERE a.CompanyCode = 1500 AND DATE(b.EndDate) = '2021-09-30' AND b.SHKind = '国资局' AND b.InfoTypeCode = 1;"
    ],
    [
        "腾讯控股这家港股公司2020年年报发布当天的收盘价是多少？",
        "SELECT a.ClosePrice FROM hkstockdb.cs_hkstockperformance AS a JOIN constantdb.hk_secumain AS b ON a.InnerCode = b.InnerCode WHERE b.CompanyCode = 1000546 AND DATE(TradingDay) = ( SELECT DATE(InfoPublDate) AS InfoPublDate FROM hkstockdb.hk_employeechange AS e JOIN constantdb.hk_secumain AS s ON e.InnerCode = s.InnerCode WHERE s.CompanyCode = 1000546 AND YEAR(e.EffectiveDate) = 2020 AND e.IfEffected = 1 ORDER BY e.EffectiveDate DESC LIMIT 1 );"
    ],
    [
        "截至2021-12-3，利亚德光电的职工总人数是多少？",
        "SELECT a.EmployeeSum FROM astockoperationsdb.lc_staff AS a WHERE a.CompanyCode = 169848 AND DATE(a.EndDate) <= '2021-12-03' AND a.ClassfiedMethod = 9000 ORDER BY a.EndDate DESC LIMIT 1;"
    ],
    [
        "2021年一级行业「银行」内上市公司的数量是多少？",
        "SELECT a.ListedSecuNum FROM astockindustrydb.lc_indfinindicators AS a WHERE a.IndustryName = '银行' AND YEAR(a.EndDate) = 2021 ORDER BY a.InfoPublDate DESC LIMIT 1;"
    ],
    [
        "一级行业“银行”在2021年的市盈率如何变化？",
        "SELECT MONTH(a.TradingDay) AS Month, ROUND(AVG(a.PE_TTM), 2) AS Avg_PE_TTM FROM astockindustrydb.lc_industryvaluation AS a WHERE a.IndustryName = '银行' AND YEAR(a.TradingDay) = 2021 GROUP BY MONTH(a.TradingDay) ORDER BY Month;"
    ],
    [
        "上海市锦天城律师事务所2020年见证多少家公司的年度股东大会？",
        "SELECT COUNT(DISTINCT CompanyCode) FROM astockshareholderdb.lc_smattendinfo WHERE YEAR = 2020 AND MeetingType = 1 AND TestmonyLawOffice LIKE '%上海市锦天城律师事务所%';"
    ],
    [
        "上海市锦天城律师事务所2020年见证年度股东大会的公司中有哪些当年股东减持了的？",
        "SELECT DISTINCT c.ChiName FROM astockshareholderdb.lc_transferplan AS a JOIN astockshareholderdb.lc_smattendinfo AS b ON a.CompanyCode = b.CompanyCode JOIN constantdb.secumain AS c ON a.CompanyCode = c.CompanyCode WHERE b.YEAR = 2020 AND b.MeetingType = 1 AND b.TestmonyLawOffice LIKE '%上海市锦天城律师事务所%' AND YEAR(a.InitialInfoPublDate) = 2020 AND ( a.TransferPlanType = 127 OR a.TransferPlanType = 128 );"
    ],
    [
        "上海市锦天城律师事务所2020年见证年度股东大会的公司中哪家公司的涨幅最大（公司全称），达到了多少？",
        "SELECT b.ChiName, MAX(c.ChangePCTYTD) AS MaxChangePCT FROM astockshareholderdb.lc_smattendinfo AS a JOIN constantdb.secumain AS b ON a.CompanyCode = b.CompanyCode JOIN astockmarketquotesdb.qt_stockperformance AS c ON b.InnerCode= c.InnerCode WHERE a.Year = 2020 AND a.MeetingType = 1 AND a.TestmonyLawOffice LIKE '%上海市锦天城律师事务所%' AND YEAR(c.TradingDay) = 2020 GROUP BY b.ChiName ORDER BY MaxChangePCT DESC LIMIT 1;"
    ],
    [
        "请你比较一下分红公告后5个自然日内股价波动率与公告前5日的股价波动率。列出波动率差异最大的三家公司",
        "SELECT b.InnerCode, s.ChiName, ROUND((b.AvgRangePCTAfter - a.AvgRangePCTBefore), 2) AS VolatilityDifference FROM ( SELECT p.InnerCode, AVG(p.RangePCT) AS AvgRangePCTBefore FROM astockmarketquotesdb.qt_stockperformance p JOIN astockfinancedb.lc_dividend d ON p.InnerCode = d.InnerCode WHERE d.DividendImplementDate IS NOT NULL AND p.TradingDay BETWEEN DATE_SUB(d.DividendImplementDate, INTERVAL 5 DAY) AND DATE_SUB(d.DividendImplementDate, INTERVAL 1 DAY) GROUP BY p.InnerCode ) AS a JOIN ( SELECT p.InnerCode, AVG(p.RangePCT) AS AvgRangePCTAfter FROM astockmarketquotesdb.qt_stockperformance p JOIN astockfinancedb.lc_dividend d ON p.InnerCode = d.InnerCode WHERE d.DividendImplementDate IS NOT NULL AND p.TradingDay BETWEEN DATE_ADD(d.DividendImplementDate, INTERVAL 1 DAY) AND DATE_ADD(d.DividendImplementDate, INTERVAL 5 DAY) GROUP BY p.InnerCode ) AS b ON a.InnerCode = b.InnerCode JOIN constantdb.secumain AS s ON b.InnerCode = s.InnerCode ORDER BY VolatilityDifference DESC LIMIT 3;"
    ],
    [
        "请你列出含有分红公告后半年内累计涨幅超过15%的公司最多的前十个一级行业",
        "SELECT i.FirstIndustryName, COUNT(DISTINCT d.InnerCode) AS CompanyCount FROM astockfinancedb.lc_dividend d JOIN astockmarketquotesdb.qt_stockperformance q ON d.InnerCode = q.InnerCode JOIN constantdb.secumain s ON d.InnerCode = s.InnerCode JOIN astockindustrydb.lc_exgindustry i ON s.CompanyCode = i.CompanyCode WHERE d.DividendImplementDate IS NOT NULL AND DATE(q.TradingDay) = DATE_ADD(d.DividendImplementDate, INTERVAL 6 MONTH) AND q.ChangePCTRMSix > 15 GROUP BY i.FirstIndustryName ORDER BY CompanyCount DESC LIMIT 10;"
    ],
    [
        "凤凰新媒体这家公司电话是多少？",
        "SELECT PEOTel FROM usstockdb.us_companyinfo WHERE CompanyCode = 7003994;"
    ],
    [
        "2020年5月涨幅前10的港股股票有哪些?",
        "SELECT b.ChiName, b.SecuCode, MAX(a.ChangePCTTM) AS MaxChangePCTTM FROM hkstockdb.cs_hkstockperformance AS a JOIN constantdb.hk_secumain AS b ON a.InnerCode = b.InnerCode WHERE DATE(a.TradingDay) BETWEEN '2020-05-01' AND '2020-05-31' GROUP BY b.ChiName, b.SecuCode ORDER BY MaxChangePCTTM DESC LIMIT 10;"
    ],
    [
        "在2019年至2021年期间，国家队在A股上市公司中持股数量增加最多的前五个一级行业是？",
        "SELECT c.FirstIndustryName, SUM(a.HoldASumChange) AS TotalIncrease FROM astockshareholderdb.lc_nationalstockholdst AS a JOIN constantdb.secumain AS b ON a.InnerCode = b.InnerCode JOIN astockindustrydb.lc_exgindustry AS c ON b.CompanyCode = c.CompanyCode WHERE DATE(a.EndDate) BETWEEN '2019-01-01' AND '2021-12-31' GROUP BY c.FirstIndustryName ORDER BY TotalIncrease DESC LIMIT 5;"
    ],
    [
        "2021-04-12到2021-04-16之间MACD指标形成金叉的股票有多少支？",
        "SELECT COUNT(DISTINCT InnerCode) AS MACD_Golden_Cross_Count FROM astockmarketquotesdb.cs_turnovervoltecindex WHERE DATE(TradingDay) BETWEEN '2021-04-12' AND '2021-04-16' AND VMACD_DIFF > VMACD_DEA;"
    ],
    [
        "2021-04-12到2021-04-16之间收盘价连续上涨的股票各有多少支？",
        "SELECT COUNT(DISTINCT InnerCode) AS Rising_Up_Count FROM astockmarketquotesdb.cs_stockpatterns WHERE DATE(TradingDay) = '2021-04-16' AND RisingUpDays >= 5;"
    ],
    [
        "筛选出2021-04-12到2021-04-16之间（日期格式为YYYY-MM-DD）同时符合MACD指标形成金叉和收盘价连续上涨条件的股票列表",
        "SELECT DISTINCT a.InnerCode, c.SecuAbbr, c.SecuCode FROM astockmarketquotesdb.cs_turnovervoltecindex a JOIN astockmarketquotesdb.cs_stockpatterns b ON a.InnerCode = b.InnerCode JOIN constantdb.secumain c ON a.InnerCode = c.InnerCode WHERE DATE(a.TradingDay) BETWEEN '2021-04-12' AND '2021-04-16' AND a.VMACD_DIFF > a.VMACD_DEA AND DATE(b.TradingDay) = '2021-04-16' AND b.RisingUpDays >= 5;"
    ],
    [
        "2019年到2021年这三年间，单个客户占比 > 30% 且客户交易金额超过1亿元的公司有多少家？",
        "SELECT COUNT(DISTINCT CompanyCode) FROM astockoperationsdb.lc_suppcustdetail WHERE DATE(EndDate) BETWEEN '2019-01-01' AND '2021-12-31' AND RelationType = 4 AND Ratio > 30 AND TradingValue > 100000000;"
    ],
    [
        "2019年12月17日上涨和下跌的证券数量分别是多少？",
        "SELECT (SELECT COUNT(*) FROM astockmarketquotesdb.qt_dailyquote WHERE DATE(TradingDay) = '2019-12-17' AND ClosePrice > OpenPrice) AS NumUp, (SELECT COUNT(*) FROM astockmarketquotesdb.qt_dailyquote WHERE DATE(TradingDay) = '2019-12-17' AND ClosePrice < OpenPrice) AS NumDown;"
    ],
    [
        "大唐国际发电股份有限公司在2019年的半年度报告中未调整的合并报表净利润是多少？",
        "SELECT ROUND(NetProfit, 1) AS NetProfit FROM astockfinancedb.lc_incomestatementall WHERE CompanyCode = (SELECT CompanyCode FROM astockbasicinfodb.lc_stockarchives WHERE ChiName LIKE '%大唐国际发电股份有限公司%') AND DATE(EndDate) = '2019-06-30' AND IfMerged = 1 AND IfAdjusted = 2;"
    ],
    [
        "拓维信息截止日期在2021年12月内的累计股权冻结质押股数及占总股本比例是多少？",
        "SELECT AccuFPShares, AccuProportion FROM astockshareholderdb.lc_sharefpsta WHERE CompanyCode = 13845 AND DATE(EndDate) BETWEEN '2021-01-01' AND '2021-12-31' ORDER BY EndDate DESC LIMIT 1;"
    ],
    [
        "公司2019年股权质押的总股数是多少股？",
        "SELECT SUM(InvolvedSum) AS TotalPledgedShares FROM astockshareholderdb.lc_sharefp WHERE CompanyCode = 74744 AND YEAR(EndDate) = 2019;"
    ],
    [
        "该公司2019年因重大事项停牌的次数有多少次？平均每次停牌多少个交易日？",
        "SELECT COUNT(*) AS SuspendTimes, ROUND(AVG(DATEDIFF(DATE(ResumptionDate), DATE(SuspendDate))), 2) AS AvgSuspendDays FROM astockmarketquotesdb.lc_suspendresumption WHERE InnerCode = 6828 AND SuspendStatement = 103 AND YEAR(DATE(SuspendDate)) = 2019;"
    ]
]

with open("../cache/sql_template.json", "w", encoding="utf-8") as f:
    json.dump(collections, f, ensure_ascii=False, indent=2)

texts = []
for collection in collections:
    texts.append(collection[0])
embedder = HuggingFaceEmbedding(model="shibing624/text2vec-base-chinese")
em = embedder.get_embedding(texts)
vectors = np.array(em)
np.save("../cache/sql_template_vectors.npy", vectors)
print(vectors[0])

loaded_vectors = np.load("../cache/sql_template_vectors.npy")
print(loaded_vectors[0])

search_query = "新科技纳入过多少个子类概念？"
print(search_query)
similarities, sim_texts = find_similar_texts(search_query, loaded_vectors, texts, top_p=-1, threshold=0.60)
print(similarities)
print(similarities)
print(sim_texts)