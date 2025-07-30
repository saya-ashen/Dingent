from typing import cast, override

from loguru import logger
import pandas as pd
from danticsql import DanticSQL

from dingent.engine.mcp.core.db_manager import Database, pydantic_to_dict

from .base import DBRequest, Handler


class ResultGetHandler(Handler):
    def __init__(self, db):
        super().__init__()
        self.db: Database = db

    async def ahandle(self, request):
        query = request.data["query"]
        raw_result = self.db.run(query)
        request.data["result"] = raw_result["data"]
        request.data["str_result"] = ""
        request.data["data_to_show"] = {}
        request.data["total_items"] = raw_result.get("metadata", {}).get("total_items")

        return await self._apass_to_next(request)


class ContextBuilder(Handler):
    def __init__(self, db, max_length: int = 5):
        super().__init__()
        self.max_length = max_length
        self.summarizer = db.summarizer

    async def ahandle(self, request: DBRequest):
        result = request.data["result"]
        if isinstance(result, dict) and self.summarizer is not None:
            summary = self.summarizer(result)
            request.data["str_result"] += summary
        elif isinstance(result, pd.DataFrame):
            length = len(result)
            if length > self.max_length:
                result = result.iloc[: self.max_length]
                str_result = f"The content of the first {self.max_length} data entries is as follows:"
                str_result += str(result.to_dict(orient="records"))
            elif length == 0:
                str_result = "SQL query result is empty."
            else:
                str_result = "Content is as follows:"
                str_result += str(result.to_dict(orient="records"))
            request.data["str_result"] += str_result
        else:
            raise ValueError("Unsupported result type for summarization.")
        return await self._apass_to_next(request)


class ResultPydanticHandler(Handler):
    def __init__(self, db):
        self.db = db

    async def ahandle(self, request: DBRequest):
        result: pd.DataFrame = request.data["result"]
        cte = request.data["cte"]
        logger.debug(f"sql query result: {result}")
        logger.debug(f"sql mapping: {cte.mapping}")

        queried_columns = result.columns.to_list()

        helper = DanticSQL(self.db.tables, cast(list[str], queried_columns),cte.mapping)
        helper.process_df(result)

        pydantic_results = helper.instances
        logger.debug(f"All pydanitc instances: {len(pydantic_results)}")
        if len(pydantic_results) > 0:
            request.data["result"] = pydantic_results
        request.data["queried_columns"] = queried_columns
        return await self._apass_to_next(request)


class ResultToShowHandler(Handler):
    def __init__(self, db: Database):
        super().__init__()
        self.db = db

    @override
    async def ahandle(self, request: DBRequest) -> DBRequest:
        result = request.data["result"]
        lang = request.metadata.get("lang", "en-US")
        data_to_show: dict[str, dict] = {}
        queried_columns = request.metadata.get("queried_columns", [])
        if isinstance(result, dict):
            for __, items in result.items():
                if not items:
                    continue
                table_title = items[0].__table__.info.get("title")  # type: ignore
                if not table_title:
                    continue
                table_title = table_title

                model_fields = items[0].__class__.model_fields
                model_computed_fields = items[0].__class__.model_computed_fields
                all_fields = model_fields | model_computed_fields
                all_alias = []
                for field in all_fields.values():
                    if field.alias:
                        all_alias.append(field.alias)
                columns = []
                parsed_item_0 = pydantic_to_dict(items[0], queried_columns, lang=lang)

                if not parsed_item_0:
                    continue
                for field in all_alias:
                    if field in parsed_item_0.keys():
                        columns.append(field)

                data_to_show[table_title] = {"rows": [], "columns": columns}

                for item in items:
                    parsed_item = pydantic_to_dict(item, queried_columns, ignore_empty=True, lang=lang)
                    if parsed_item:
                        data_to_show[table_title]["rows"].append(parsed_item)
            request.data["data_to_show"] = data_to_show
        elif isinstance(result, pd.DataFrame):
            request.data["data_to_show"] = result
        return request
