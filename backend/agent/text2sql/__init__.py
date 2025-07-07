"""
Text2SQL Agent Package

这个包提供了将自然语言转换为SQL查询的智能代理功能。
"""

from .agent import Text2SQLAgent
from .chat_handler import ChatHandler

__all__ = ['Text2SQLAgent', 'ChatHandler'] 