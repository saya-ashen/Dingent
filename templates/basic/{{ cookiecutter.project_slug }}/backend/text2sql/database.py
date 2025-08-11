import enum
import importlib
import importlib.util
import inspect
import os
import sys
import types
import typing
from pathlib import Path
from typing import Any

import pandas as pd
from loguru import logger
from sqlalchemy import inspect as table_inspect
from sqlalchemy.engine.url import make_url
from sqlmodel import Session, SQLModel, create_engine, text

from .settings import DatabaseSettings


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


def find_definitions_from_file(file_path: str, base_class: type | None = None, target_name: str | None = None, force_reload: bool = False) -> list[Any]:
    """
    Dynamically import a Python file, and find all classes or objects definied in it.
    Then cached these classes and objects.

    Args:
        file_path (str): Path to the user-defined .py file.
        base_class (Optional[Type]):
            The base class to search for. The function will return all subclasses of this base class.
        target_name (Optional[str]):
            The function will return all definitions that match this name.
        force_reload (bool):
            If True, the module will be reloaded even if it has already been loaded.

    Returns:
        List[Any]: List of definitions found in the file that match the criteria.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    if base_class is None and target_name is None:
        raise ValueError("At least one of 'base_class' or 'target_name' must be provided.")

    module_name = os.path.splitext(os.path.basename(file_path))[0]

    module = None
    try:
        if module_name in sys.modules and not force_reload:
            module = sys.modules[module_name]
        elif module_name in sys.modules and force_reload:
            module = importlib.reload(sys.modules[module_name])
        else:
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            if spec is None or spec.loader is None:
                raise ImportError(f"Can't create module spec or loader for {file_path}")

            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

    except Exception as e:
        logger.error(f"Load module {module_name} from {file_path} failed. Error: {e}")
        raise e

    found_definitions = []
    for name, obj in inspect.getmembers(module):
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
    def __init__(self, uri: str, name: str, schemas_path: str | None = None, dialect: str | None = None, **kwargs):
        self.uri = uri
        self.db_name = name
        self.summarizer = self._get_summarizer(schemas_path)
        if schemas_path:
            self._tables = self._get_tables(schemas_path)
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
                table_inspect(table)
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
                summary += f"The first 10 records retrieved: {', '.join(str(instance) for instance in instance_10)}\n"
            return summary

        if not schemas_path:
            return default_summarizer

        try:
            summarizer = find_definitions_from_file(schemas_path, target_name="summarize_data")[0]
        except IndexError:
            logger.warning("function 'summarize_data' not found。Use default summarizer instead.")
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

    def get_tables_info(self):
        if not self.tables:
            return
        tables_info = {}
        for table in self.tables:
            tables_info[table.__tablename__] = self._describe(table)
        return tables_info


class DBManager:
    """
    A class to manage and maintain all database instances.
    It creates and caches database connection instances on demand based on the configuration file.
    """

    def __init__(self, db_configs: list[DatabaseSettings]):
        """
        Initializes the database manager with a list of database configurations.
        """
        self._configs: dict[str, DatabaseSettings] = {config.name: config for config in db_configs}
        self._connections: dict[str, Database] = {}
        logger.info(f"DBManager initialized with {len(self._configs)} databases.")

    async def get_connection(self, name: str) -> Database | None:
        """
        Get a database instance by its name.
        If there is an instance cached, return it directly.
        """
        if name in self._connections:
            logger.debug(f"Retrieving cached database connection: {name}")
            return self._connections[name]

        if name not in self._configs:
            logger.error(f"Database '{name}' not found in configuration.")
            raise ValueError(f"Database '{name}' not found in configuration.")

        logger.debug(f"Creating a new connection for database '{name}'...")
        config = self._configs[name]
        schemas_relative_path = config.schemas_file

        try:
            if schemas_relative_path:
                schemas_path = await Path(schemas_relative_path).resolve()
                instance = Database(db_name=config.name, uri=config.uri, schemas_path=str(schemas_path))
            else:
                instance = Database(db_name=config.name, uri=config.uri)
            self._connections[name] = instance
            logger.info(f"Database connection '{name}' created and cached.")
            return instance
        except Exception as e:
            logger.error(f"Failed to create database connection '{name}': {e}")
            return None

    def list_available_databases(self) -> list[str]:
        return list(self._configs.keys())
