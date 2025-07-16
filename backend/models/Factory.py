import os

from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEmbeddings

from langchain_openai import ChatOpenAI, OpenAIEmbeddings, AzureChatOpenAI, AzureOpenAIEmbeddings

load_dotenv()


class ChatModelFactory:
    model_params = {
        "temperature": 0,
        "seed": 42,
    }

    @classmethod
    def get_model(cls, model_name: str, use_azure: bool = False):
        if "gpt" in model_name:
            if not use_azure:
                return ChatOpenAI(model=model_name, **cls.model_params)
            else:
                return AzureChatOpenAI(
                    azure_deployment=model_name,
                    api_version="2024-05-01-preview",
                    **cls.model_params
                )
        elif model_name == "deepseek":
            # 换成开源模型试试
            # https://siliconflow.cn/
            # 一个 Model-as-a-Service 平台
            # 可以通过与 OpenAI API 兼容的方式调用各种开源语言模型。
            return ChatOpenAI(
                model="deepseek-ai/DeepSeek-V3",  # 模型名称
                openai_api_key=os.getenv("SILICONFLOW_API_KEY"),  # 在平台注册账号后获取
                openai_api_base="https://api.siliconflow.cn/v1",  # 平台 API 地址
                **cls.model_params,
            )
        elif model_name in ["qianwen", "qwen"]:
            return ChatOpenAI(
                api_key="sk-3d0b712661134d72991a4166262cbcea",
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
                model="qwen-plus",  # 此处以qwen-plus为例，您可按需更换模型名称。模型列表：https://help.aliyun.com/zh/model-studio/getting-started/models
                **cls.model_params,
                # other params...
                )
        elif model_name == "zhipu":
            return None  # 暂时返回 None，等待实现
        else:
            # 默认使用 qianwen
            return ChatOpenAI(
                api_key="sk-3d0b712661134d72991a4166262cbcea",
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
                model="qwen-plus",
                **cls.model_params,
            )


    @classmethod
    def get_default_model(cls):
        return cls.get_model("qianwen")

