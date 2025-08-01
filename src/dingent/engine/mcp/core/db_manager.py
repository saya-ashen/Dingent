import enum
import importlib
import importlib.util
import inspect
import os
import sys
import types
import typing
from typing import Any, cast

import pandas as pd
from anyio import Path
from loguru import logger
from sqlalchemy import inspect as table_inspect
from sqlalchemy.engine.url import make_url
from sqlmodel import Session, SQLModel, create_engine, select, text

from .settings import DatabaseSettings


def pydantic_to_dict(obj: SQLModel, queried_columns: list | None = None, ignore_empty=False) -> dict[str, Any] | None:
    """
    Converts a SQLModel object to a dictionary.
    Relationship fields are converted to the main_key value(s) of the related object(s).
    """
    logger.debug(f"input objs: {obj.model_dump(by_alias=True)}")
    fields_info = obj.__class__.model_fields

    fields_to_include = {field_name for field_name, field_info in fields_info.items() if field_info.alias}
    if queried_columns:
        fields_to_include = set(queried_columns) & fields_to_include
    fields_to_include = list(fields_to_include)

    # add computed fields if they are not None
    for key in obj.__class__.model_computed_fields.keys():
        if not ignore_empty or getattr(obj, key):
            fields_to_include.append(key)

    # 判断是否有有效的显示列
    has_vaild_show_column = False
    for field_name in fields_to_include:
        if getattr(obj, field_name) is not None:
            has_vaild_show_column = True
            break
    if not has_vaild_show_column:
        return None
    dumped_json = obj.model_dump(mode="json", by_alias=True, include=fields_to_include)
    for key in list(dumped_json.keys()):
        dumped_json[key] = dumped_json.pop(key)
    logger.debug(f"dumped_json: {dumped_json};fields_to_include:{fields_to_include}")
    return dumped_json


def is_enum_field_flexible(model: type[SQLModel], field_name: str) -> tuple[bool, list | None]:
    """
    Checks if a field in a SQLModel is an Enum (including within Union/Optional)
    and returns its possible values.

    Args:
        model: The SQLModel class.
        field_name: The name of the field to check.

    Returns:
        A tuple containing a boolean (is_enum) and a list of possible values (or None).
    """
    if not hasattr(model, "__annotations__") or field_name not in model.__annotations__:
        return False, None

    field_type = model.__annotations__[field_name]

    # Handle Union types (like Type | None)
    if type(field_type) is types.UnionType:
        union_args = typing.get_args(field_type)
        for arg in union_args:
            # Check if the argument is an Enum class and not NoneType
            if isinstance(arg, type) and issubclass(arg, enum.Enum):
                # Get the possible values from this Enum class
                possible_values = [member.value for member in arg]
                return True, possible_values
    # Handle simple types
    elif isinstance(field_type, type) and issubclass(field_type, enum.Enum):
        possible_values = [member.value for member in field_type]
        return True, possible_values

    # If not an enum or union containing an enum
    return False, None


def find_definitions_from_file(
    file_path: str, base_class: type | None = None, target_name: str | None = None, force_reload: bool = False
) -> list[Any]:
    """
    动态导入一个 Python 文件，并根据指定条件查找其中定义的类或对象。
    此函数会缓存加载的模块，以避免在重复调用时重新执行模块代码引发错误。

    Args:
        file_path (str): 用户定义的 .py 文件的路径。
        base_class (Optional[Type]):
            要查找的基类。函数将返回所有该基类的子类。
        target_name (Optional[str]):
            要查找的定义（类、函数等）的精确名称。
        force_reload (bool):
            如果为 True，即使模块已被加载，也会强制重新加载并执行模块代码。
            警告：对于像 SQLAlchemy 模型这样具有副作用的定义，
            这可能会再次引发 'already defined' 错误。
            默认为 False。

    Returns:
        List[Any]: 一个包含所有符合条件的已找到定义的列表。
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"文件未找到: {file_path}")

    if base_class is None and target_name is None:
        raise ValueError("必须提供 'base_class' 或 'target_name' 至少一个参数。")

    module_name = os.path.splitext(os.path.basename(file_path))[0]

    module = None
    try:
        # 步骤 1: 检查模块是否已经被加载
        if module_name in sys.modules and not force_reload:
            module = sys.modules[module_name]
            # print(f"模块 '{module_name}' 已缓存，直接使用。")
        # 步骤 2: 如果需要，强制重载模块
        elif module_name in sys.modules and force_reload:
            # print(f"模块 '{module_name}' 已存在，强制重载。")
            module = importlib.reload(sys.modules[module_name])
        # 步骤 3: 如果模块从未加载过，则正常加载
        else:
            # print(f"首次加载模块 '{module_name}'。")
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            if spec is None or spec.loader is None:
                raise ImportError(f"无法为 {file_path} 创建模块规范或加载器")

            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module  # 必须在执行前添加到 sys.modules
            spec.loader.exec_module(module)

    except Exception as e:
        print(f"从文件 '{file_path}' 加载或重载模块时出错: {e}")
        raise e

    # 步骤 4: 在加载好的模块中查找定义
    found_definitions = []
    for name, obj in inspect.getmembers(module):
        # 检查对象是否直接定义在该模块中
        if hasattr(obj, "__module__") and obj.__module__ != module_name:
            continue

        match = True
        if target_name is not None and name != target_name:
            match = False
        if match and base_class is not None:
            if not (inspect.isclass(obj) and issubclass(obj, base_class) and obj is not base_class):
                match = False
        if match:
            found_definitions.append(obj)

    return found_definitions


class Database:
    def __init__(self, uri: str, db_name: str, schemas_path: str | None = None,dialect: str|None=None):
        self.uri = uri
        self.db_name = db_name
        if schemas_path:
            self._tables = self._get_tables(schemas_path)
            self.summarizer = self._get_summarizer(schemas_path)
        else:
            self._tables = []
        self.db = create_engine(uri)
        url_object = make_url(uri)
        self.dialect = dialect or url_object.get_dialect().name


    @property
    def tables(self) -> list[type[SQLModel]]:
        return getattr(self, "_tables", [])

    def run(self, query: str):
        with Session(self.db) as session:
            statement = text(query)
            results = session.exec(statement).all()
            df = pd.DataFrame(results, dtype=object)
        return {"data": df, "metadata": {}}

    def _get_tables(self, schemas_path) -> list[type[SQLModel]]:
        all_tables: list[type[SQLModel]] = find_definitions_from_file(schemas_path, base_class=SQLModel)
        # Valite the tables' definition
        for table in all_tables:
            try:
                inspector = table_inspect(table)
                relationships = inspector.relationships
            except Exception as e:
                raise e
        return all_tables

    def _get_summarizer(self, schemas_path):
        def default_summarizer(data: dict[str, list[dict]]) -> str:
            summary = ""
            for table_name, instances in data.items():
                if not instances:
                    continue
                instance_10 = instances[:10]
                summary += f"Table: {table_name}\n"
                summary += f"Sample Data: {', '.join(str(instance) for instance in instance_10)}\n"
            return summary

        try:
            summarizer = find_definitions_from_file(schemas_path, target_name="summarize_data")[0]
        except IndexError:
            logger.warning("没有找到名为 'summarize_data' 的函数。使用默认方法")
            return default_summarizer

        assert callable(summarizer), f"Summarizer in {self.db_name} module is not callable"
        return summarizer

    def _describe(self, model: type[SQLModel]):
        info = model.model_json_schema()
        description = {}
        description["description"] = model.__table__.info.get("description", "")  # type: ignore
        description["columns"] = {}
        for key, value in info["properties"].items():
            column_desc = value.get("description")
            if not column_desc:
                continue
            description["columns"][key] = {}
            is_enum_field, possible_values = is_enum_field_flexible(model, key)
            if column_desc:
                description["columns"][key]["description"] = column_desc

            if is_enum_field:
                description["columns"][key]["type"] = "enum"
                description["columns"][key]["possible_values"] = possible_values
        return description

    def read_all(self):
        all_data: dict[str, list[str]] = {}
        with Session(self.db) as session:
            for table in self.tables:
                if table.__table__.info.get("title") is None:  # type: ignore
                    continue
                statement = select(table)
                results = session.exec(statement)
                _ins: list[str] = []
                for instance in results:
                    instance = table.model_validate(instance.model_dump(mode="json", by_alias=False))
                    _d = pydantic_to_dict(instance)
                    _ins.append(str(_d))
                all_data[cast(str, table.__tablename__)] = _ins
        return all_data

    def get_tables_info(self):
        tables_info = {}
        for table in self.tables:
            tables_info[table.__tablename__] = self._describe(table)
        return tables_info


class DBManager:
    """
    管理和维护所有数据库实例的类。

    它根据配置文件按需创建和缓存数据库连接实例。
    """

    def __init__(self, db_configs: list[DatabaseSettings]):
        """
        初始化数据库管理器。

        :param db_configs: 来自于 config.yaml 的 'databases' 部分。
                           e.g., [{'name': 'sales_db', 'type': 'sqlite', 'uri': '...'}]
        """
        self._configs: dict[str, DatabaseSettings] = {config.name: config for config in db_configs}
        self._connections: dict[str, Database] = {}
        logger.info(f"DBManager 已使用 {len(self._configs)} 个数据库配置进行初始化。")

    async def get_connection(self, name: str) -> Database | None:
        """
        获取一个指定名称的数据库实例。

        如果实例已在缓存中，则直接返回。否则创建新实例。

        :param name: 在配置文件中定义的数据库的唯一名称。
        :return: 一个 Database 实例或在失败时返回 None。
        :raises ValueError: 如果请求的名称在配置中不存在。
        """
        if name in self._connections:
            logger.debug(f"返回缓存的数据库连接: {name}")
            return self._connections[name]

        if name not in self._configs:
            raise ValueError(f"数据库 '{name}' 在配置中未找到。")

        logger.info(f"正在为 '{name}' 创建新的数据库连接...")
        config = self._configs[name]
        schemas_relative_path = config.schemas_file

        try:
            schemas_path = await Path(schemas_relative_path).resolve()
            # 使用我们上面定义的 Database 包装类
            instance = Database(db_name=config.name, uri=config.uri, schemas_path=str(schemas_path))
            self._connections[name] = instance
            logger.info(f"Database connection '{name}' created and cached.")
            return instance
        except Exception as e:
            logger.error(f"Failed to create database connection '{name}': {e}")
            raise e
            # 创建失败时，不在缓存中存储任何内容
            return None

    def list_available_databases(self) -> list[str]:
        """返回所有已配置的数据库名称列表。"""
        return list(self._configs.keys())
