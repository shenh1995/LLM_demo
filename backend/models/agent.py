import os
import logging
from typing import Optional, Dict, Any, List,Callable,Tuple
import copy
from dataclasses import dataclass, field
from dotenv import load_dotenv
# from Factory import ChatModelFactory
from .factory import ChatModelFactory

# 加载环境变量
load_dotenv()

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
DEBUG_OPTION_PRINT_TOOL_CALL_RESULT = "print_tool_call_result"

@dataclass
class AgentConfig:
    """Configuration settings for the Agent class."""
    model_name: str
    name: str
    role: str
    constraint: Optional[str] = None
    output_format: Optional[str] = None
    knowledge: Optional[str] = None
    tools: Optional[List[Dict]] = None
    funcs: Optional[List[Callable]] = None
    retry_limit: int = 5
    enable_history: bool = True
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    stream: Optional[bool] = None
    debug_tool_call_result: bool = True
    system_prompt_kv: Optional[Dict] = field(default_factory=dict)
    pre_process: Optional[Callable[['Agent', List[Dict[str, str]]], None]] = None
    post_process: Optional[Callable[[str], str]] = None
    max_history_num: int = 30

    def deepcopy(self):
        """Custom deepcopy method to handle non-deepcopyable attributes."""
        new_config = copy.copy(self)  # Start with a shallow copy
        new_config.system_prompt_kv = copy.deepcopy(self.system_prompt_kv)
        return new_config

class Agent:
    """基础代理类"""
    

    def __init__(self, config: AgentConfig):
        self.cfg = config.deepcopy()
        if self.cfg.system_prompt_kv is None:
            self.cfg.system_prompt_kv = {}
        self.cfg.pre_process = config.pre_process
        self.cfg.post_process = config.post_process
        self.cfg.knowledge = config.knowledge
        self.history = []
        self.usage_tokens = 0 # 总共使用的token数量
        self.options = {}
        if config.temperature is not None:
            self.options["temperature"] = config.temperature
        if config.top_p is not None:
            self.options["top_p"] = config.top_p
        if config.funcs is not None:
            self.funcs = {func.__name__: func for func in config.funcs}
        else:
            self.funcs = None
        self.model_name = config.model_name
        
        # 初始化模型
        self._init_model()
    
    def _init_model(self):
        """初始化模型"""
        try:
            self.model = ChatModelFactory.get_model(self.model_name)
            if self.model is None:
                logger.error(f"❌ 模型初始化失败: ChatModelFactory.get_model('{self.model_name}') 返回 None")
                raise Exception(f"模型 '{self.model_name}' 未在 Factory 中定义")
        except Exception as e:
            logger.error(f"❌ 初始化模型失败: {e}")
            self.model = None

    def _call_model(self, system_prompt: str, messages: List[Dict[str, str]], tools=None, funcs=None, options=None, stream=None, debug_options=None):
        """统一调用模型的接口"""
        if self.model is None:
            raise Exception("模型未初始化")
        
        # 构建 LangChain 格式的消息
        from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
        
        formatted_messages = []
        if system_prompt:
            formatted_messages.append(SystemMessage(content=system_prompt))
        
        for msg in messages:
            if msg["role"] == "user":
                formatted_messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                formatted_messages.append(AIMessage(content=msg["content"]))
        
        # 调用模型
        try:
            response = self.model.invoke(formatted_messages)
            content = response.content if hasattr(response, 'content') else str(response)
            # 确保返回字符串类型
            content_str = str(content)
            # 这里简化处理，实际应该从响应中获取 token 数量
            token_count = len(content_str.split())  # 简化的 token 计算
            return content_str, token_count, True
        except Exception as e:
            logger.error(f"模型调用失败: {e}")
            return str(e), 0, False

    def clone(self) -> 'Agent':
        """Creates a clone of the current agent instance."""
        return Agent(config=self.cfg)

    def clear_history(self):
        """Clears the agent's conversation history and resets token counts."""
        self.history = []
        self.usage_tokens = 0

    def add_system_prompt_kv(self, kv: dict):
        """Sets the system prompt key-value pairs for the agent."""
        for k, v in kv.items():
            self.cfg.system_prompt_kv[k] = v

    def del_system_prompt_kv(self, key: str):
        """Deletes the specified key from the system prompt key-value pairs for the agent."""
        if key in self.cfg.system_prompt_kv:
            del self.cfg.system_prompt_kv[key]

    def clear_system_prompt_kv(self):
        """
        Clear the agent's additional system prompt settings
        """
        self.cfg.system_prompt_kv = {}

    def get_system_prompt(self):
        """Generates and returns the system prompt based on the agent's attributes."""
        system_prompt = f"## 角色描述\n{self.cfg.role}"
        if self.cfg.constraint is not None:
            system_prompt += f"\n\n## 约束要求\n{self.cfg.constraint}"
        if self.cfg.output_format is not None:
            system_prompt += f"\n\n## 输出格式\n{self.cfg.output_format}"
        if self.cfg.knowledge is not None:
            system_prompt += f"\n\n## 知识库\n{self.cfg.knowledge}"
        if self.cfg.system_prompt_kv:
            for key, value in self.cfg.system_prompt_kv.items():
                system_prompt += f"\n\n## {key}\n{value}"
        return system_prompt

    def answer(self, message: str) -> Tuple[str, int]:
        """Generates a response to a user's message using the agent's history.
        return:
            - str: assistant's answer
            - int: usage_tokens
        """
        messages = self.history + [{"role": "user", "content": message}]
        return self.chat(messages = messages)


    def chat(self, messages: List[Dict[str, str]]) -> Tuple[str, int]:
        """Attempts to generate a response from the language model, retrying if necessary.
        return:
            - str: assistant's answer
            - int: usage_tokens
        """
        debug_mode = os.getenv("DEBUG", "0") == "1"
        show_llm_input_msg = os.getenv("SHOW_LLM_INPUT_MSG", "0") == "1"
        logger = logging.getLogger(__name__)

        if self.cfg.pre_process is not None:
            self.cfg.pre_process(self, messages)
        usage_tokens = 0
        is_exception_from_llm = False
        for attempt in range(self.cfg.retry_limit):
            if attempt > 0:
                if debug_mode:
                    print(f"\n重试第 {attempt} 次...\n")
                logger.info("\n重试第 %d 次...\n", attempt)
            response = ""
            try:
                msgs = (
                    messages if attempt == 0
                    else messages + [
                        {"role": "assistant", "content": response},
                        {"role": "user", "content": "请修正后重试"}
                    ] if not is_exception_from_llm else messages
                )
                if show_llm_input_msg:
                    if debug_mode:
                        print("\n\n>>>>> 【" + msgs[-1]["role"] + "】 Said:\n" + msgs[-1]["content"])
                    logger.debug("\n\n>>>>> 【%s】 Said:\n%s", msgs[-1]["role"], msgs[-1]["content"])
                if debug_mode:
                    print(f"\n\n>>>>> Agent【{self.cfg.name}】 Said:")
                logger.debug("\n\n>>>>> Agent【%s】 Said:\n", self.cfg.name)
                is_exception_from_llm = True
                # logger.info(f"🔄 开始调用模型: {self.get_system_prompt()}")
                response, token_count, ok = self._call_model(
                    system_prompt=self.get_system_prompt(),
                    messages=msgs,
                    tools=self.cfg.tools,
                    funcs=self.funcs,
                    options=self.options,
                    stream=self.cfg.stream,
                    debug_options={DEBUG_OPTION_PRINT_TOOL_CALL_RESULT: self.cfg.debug_tool_call_result},
                )
                is_exception_from_llm = False
                usage_tokens += token_count
                self.usage_tokens += token_count
                if ok and self.cfg.post_process is not None:
                    response = self.cfg.post_process(response)
            except Exception as e:
                print(f"\nAgent【{self.cfg.name}】chat发生异常：{str(e)}")
                logger.debug("\nAgent【%s】chat发生异常：%s", self.cfg.name, str(e))
                ok = False
                response += f"\n发生异常：{str(e)}"
            if ok:  # 如果生成成功，退出重试
                break
        else:
            response, token_count = f"发生异常：{response}", 0  # 如果所有尝试都失败，返回默认值
            return response, token_count

        if self.cfg.enable_history:
            self.history = messages + [{"role": "assistant", "content": response}]
            if len(self.history) > self.cfg.max_history_num:
                half = len(self.history) // 2 + 1
                # 浓缩一半的history
                if debug_mode:
                    print(f"\n\n>>>>> Agent【{self.cfg.name}】 Compress History:")
                logger.debug("\n\n>>>>> Agent【%s】 Compress History:\n", self.cfg.name)
                try:
                    compressed_msg, token_count, ok = self._call_model(
                        system_prompt="请你把所有历史对话浓缩成一段话，必须保留重要的信息，不要换行，不要有任何markdown格式",
                        messages=self.history[:half],
                        stream=self.cfg.stream,
                    )
                    usage_tokens += token_count
                    self.usage_tokens += token_count
                    if ok:
                        self.history = [{"role": "assistant", "content": compressed_msg}] +\
                            self.history[half:]
                except Exception as e:
                    print(f"\nAgent【{self.cfg.name}】压缩history发生异常：{str(e)}")
                    logger.debug("\nAgent【%s】压缩history发生异常：%s", self.cfg.name, str(e))
        return response, usage_tokens


def main():
    """测试函数"""
    print("🚀 开始测试 Agent 类...")
    
    # 测试基础代理
    print("\n📋 测试基础代理:")
    try:
        agent = Agent(AgentConfig(
            model_name="qianwen",
            name="test_agent",
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
                    '''原问题：中南传媒在2019年度的前五大客户中，各类型客户占总营收的比例分别是多少？（答案需要包含两位小数）\n'''
                    '''输出:\n'''
                    '''中南传媒在2019年度的前五大客户有哪些\n'''
                    '''前五大客户的类型有哪些\n'''
                    '''各类型客户占总营收的比例是多少\n'''
                ),
            },
        ))
        answer, tokens = agent.answer("天士力在2020年的最大担保金额是多少？答案需要包含1位小数")
        print(f"✅ 回答: {answer[:100]}...")
        print(f"📊 使用tokens: {tokens}")
    except Exception as e:
        print(f"❌ 基础代理测试失败: {e}")

    print("\n✅ Agent 测试完成!")


if __name__ == "__main__":
    main() 