"""
This module provides a MySQLConnector class for executing SQL queries
and returning results in JSON format.
"""

import json
import datetime
import mysql.connector
import logging
from typing import Optional, Any

logger = logging.getLogger(__name__)

class MySQLConnector:
    """A class to connect to a MySQL database and execute SQL queries."""
    
    _instance: Optional['MySQLConnector'] = None
    _connection: Optional[Any] = None
    
    def __new__(cls, *args, **kwargs):
        """单例模式实现"""
        if cls._instance is None:
            cls._instance = super(MySQLConnector, cls).__new__(cls)
        return cls._instance

    def __init__(self, host: Optional[str] = None, user: Optional[str] = None, 
                 password: Optional[str] = None, database: str = "mysql"):
        """
        初始化MySQL连接器
        
        Args:
            host: 数据库主机地址
            user: 用户名
            password: 密码
            database: 默认数据库名（可选，用于建立连接）
        """
        # 如果已经初始化过，直接返回
        if hasattr(self, '_initialized'):
            return
            
        # 如果没有提供连接参数，使用默认值
        if host is None:
            host = "120.76.202.209"
        if user is None:
            user = "root"
        if password is None:
            password = "123456"
            
        self.host = host
        self.user = user
        self.password = password
        self.database = database
        
        # 初始化连接
        self._initialize_connection()
        self._initialized = True

    def _initialize_connection(self):
        """初始化数据库连接"""
        try:
            self._connection = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database
            )
            logger.info(f"✅ MySQL连接初始化成功: {self.host}:3306/{self.database}")
        except mysql.connector.Error as err:
            logger.error(f"❌ MySQL连接初始化失败: {err}")
            raise

    @classmethod
    def get_instance(cls) -> 'MySQLConnector':
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def initialize_global_connection(cls, host: str = "120.76.202.209", user: str = "root", 
                                   password: str = "123456", database: str = "mysql") -> 'MySQLConnector':
        """
        初始化全局数据库连接
        
        Args:
            host: 数据库主机地址
            user: 用户名
            password: 密码
            database: 默认数据库名
        """
        try:
            instance = cls(host, user, password, database)
            logger.info("✅ 全局MySQL连接初始化完成")
            return instance
        except Exception as e:
            logger.error(f"❌ 全局MySQL连接初始化失败: {e}")
            raise

    def execute_sql_query(self, sql: str) -> str:
        """
        执行SQL查询并返回JSON格式的结果
        
        Args:
            sql: SQL查询语句，可以包含跨数据库的查询
            
        Returns:
            str: JSON格式的查询结果
        """
        sql = sql.replace('\\n', ' ')
        logger.info("\n>>>>> sql:\n%s", sql)
        
        # SQL安全检查：只允许SELECT和SHOW操作
        sql_upper = sql.strip().upper()
        
        # 检查是否以SELECT或SHOW开头
        if not (sql_upper.startswith('SELECT ') or sql_upper.startswith('SHOW ')):
            logger.error(f"❌ 安全警告：不允许执行非查询SQL语句: {sql}")
            return json.dumps({"error": "只允许执行SELECT和SHOW查询语句"})
        
        # 检查是否包含危险操作
        dangerous_keywords = [
            'DELETE', 'DROP', 'TRUNCATE', 'UPDATE', 'INSERT', 'CREATE', 'ALTER', 
            'GRANT', 'REVOKE', 'EXECUTE', 'EXEC', 'CALL', 'PROCEDURE', 'FUNCTION'
        ]
        
        for keyword in dangerous_keywords:
            if keyword in sql_upper:
                logger.error(f"❌ 安全警告：SQL语句包含危险关键字 '{keyword}': {sql}")
                return json.dumps({"error": f"不允许执行包含 '{keyword}' 的SQL语句"})
        
        cursor = None
        try:
            # 检查连接是否有效，如果无效则重新连接
            if self._connection is None or not self._connection.is_connected():
                logger.warning("数据库连接已断开，尝试重新连接...")
                self._initialize_connection()
            
            if self._connection is None:
                logger.error("无法建立数据库连接")
                return json.dumps({"error": "无法建立数据库连接"})
                
            cursor = self._connection.cursor()
            cursor.execute(sql)
            
            # 检查是否有结果集
            if cursor.description is None:
                return json.dumps([])
                
            columns = [column[0] for column in cursor.description]
            result = cursor.fetchall()
            # Convert date objects to strings
            result_dict = [
                {column: (value.isoformat() if isinstance(value, (datetime.date, datetime.datetime)) else value)
                 for column, value in zip(columns, row)}
                for row in result
            ]
            logger.debug("\n>>>>> result_dict:\n%s", result_dict)
            return json.dumps(result_dict, ensure_ascii=False)
        except mysql.connector.Error as err:
            logger.error(f"SQL查询执行失败: {err}")
            return json.dumps({"error": f"SQL查询执行失败: {str(err)}"})
        finally:
            if cursor is not None:
                cursor.close()

    def close_connection(self):
        """关闭数据库连接"""
        if self._connection and self._connection.is_connected():
            self._connection.close()
            logger.info("✅ MySQL连接已关闭")

    def __del__(self):
        """析构函数，确保连接被正确关闭"""
        if hasattr(self, '_connection') and self._connection:
            self.close_connection()

