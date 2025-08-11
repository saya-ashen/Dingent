import pandas as pd

from ..database import Database
from ..types_ import Group
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


class ResultStructureHandler(Handler):
    def __init__(self):
        pass

    async def ahandle(self, request: DBRequest):
        source_df: pd.DataFrame = request.data["result"]
        grouping_schema: list[Group] | None = request.data.get("result_grouping")

        # 遍历分组规则
        if not grouping_schema:
            print("信息: 未找到分组规则，启用默认分组 'main_result'。")
            # 将整个DataFrame去重
            deduplicated_df = source_df.drop_duplicates().reset_index(drop=True)
            # 构造成最终的输出格式
            request.data["result"] = {"main_result": deduplicated_df.to_dict(orient="records")}
            return await self._apass_to_next(request)

        final_result_data = {}

        # --- 主要分组逻辑 ---
        for group in grouping_schema:
            group_name, columns_in_group = group.primary_entity_name, group.columns
            # 筛选出在DataFrame中实际存在的列，防止模型幻化出不存在的列名
            existing_columns = [col for col in columns_in_group if col in source_df.columns]

            if not existing_columns:
                print(f"警告: 分组 '{group_name}' 中定义的所有列都不在DataFrame中，已跳过。")
                continue

            # 1. 选择子集: 根据分组规则选择DataFrame的列
            group_df = source_df[existing_columns]

            # 2. 去重: 使用pandas内置的高效方法
            deduplicated_df = group_df.drop_duplicates().reset_index(drop=True)

            # 3. 转换为字典列表并存入最终结果
            final_result_data[group_name] = deduplicated_df.to_dict(orient="records")

        request.data["result"] = final_result_data
        return await self._apass_to_next(request)
