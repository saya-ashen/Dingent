from sqlmodel import Field, SQLModel


class Biomarker(SQLModel, table=True):
    __tablename__ = "overview"  # type: ignore
    __table_args__ = (
        {
            "info": {
                "title": "生物标志物",
                "must_queried_columns": [
                    "biomarker_id",
                    "disease_id",
                    "disease_name",
                ],
                "description": "biomarker database",
            }
        },
    )
    ov_id: int | None = Field(
        default=None,
        primary_key=True,
    )

    biomarker_id: int = Field(None)

    disease_id: str | None = Field(None)
    disease_name: str | None = Field(None, alias="疾病名称", description="疾病名称，必须使用英文")
    biomarker_name: str | None = Field(None, alias="生物标志物名称", description="生物标志物名称，必须使用英文")
    biomarker_type: str | None = Field(
        None, alias="生物标志物类型", description="Type or category of the biomarker (e.g., protein, gene)."
    )
    taxon_id: int | None = Field(None)
    taxon_name: str | None = Field(
        None, alias="物种名称", description="Name of the organism (taxon) associated with the biomarker."
    )
    taxon4v_id: int | None = Field(None, description="Identifier related to a taxon version or variant (4V related).")
    taxon4v_name: str | None = Field(None, description="Name of the taxon version or variant (4V related).")
    biomarker_usage: str | None = Field(
        None, description="Description of how the biomarker is used or its application."
    )
    reference: str | None = Field(
        None, description="Reference information (e.g., publication details) related to the biomarker."
    )  # TEXT maps to str
    techs: str | None = Field(
        None, description="Techniques or methodologies used to identify or measure the biomarker."
    )  # TEXT maps to str
    link: str | None = Field(None, description="Link to further information or resources about the biomarker.")


def summarize_data(data: dict[str, list[Biomarker]]) -> str:
    """
    根据 text2sql 的查询结果，总结所有关于生物标志物的信息。

    该函数会生成一个两部分的 Markdown 格式化字符串：
    1.  一个全局摘要，概述查询结果的总体情况。
    2.  一个详细列表，逐一展示每个被检索到的生物标志物的信息。

    Args:
        data (Dict[str, List[SQLModel]]): 输入数据，其中 key 是固定的 "overview"，
                                         value 是一个 Biomarker 对象的列表。
                                         这些对象可能只包含部分被查询的属性。

    Returns:
        str: 一个格式化后的、人类可读的 Markdown 字符串总结。
    """
    detail_limit: int = 5
    # 从输入字典中获取Biomarker对象列表，如果不存在则返回空列表
    biomarkers = data.get("overview", [])

    if len(biomarkers) == 0:
        return "未查询到相关的生物标志物信息。"

    total_count = len(biomarkers)

    # --- 1. 构建全局摘要 (此部分逻辑不变，始终基于全部数据) ---
    summary_parts = ["### 生物标志物查询结果摘要\n"]
    summary_parts.append(f"本次查询共检索到 **{total_count}** 条生物标志物相关记录。")

    unique_diseases = {b.disease_name for b in biomarkers if b.disease_name}
    unique_biomarker_names = {b.biomarker_name for b in biomarkers if b.biomarker_name}
    unique_types = {b.biomarker_type for b in biomarkers if b.biomarker_type}

    if unique_diseases:
        summary_parts.append(f"- **涉及疾病**: {', '.join(sorted(list(unique_diseases)))}")
    if unique_biomarker_names:
        # 如果标志物太多，也对标志物名称列表做个截断
        display_names = sorted(list(unique_biomarker_names))
        if len(display_names) > 10:
            summary_parts.append(f"- **涉及生物标志物**: {', '.join(display_names[:10])} 等")
        else:
            summary_parts.append(f"- **涉及生物标志物**: {', '.join(display_names)}")

    if unique_types:
        summary_parts.append(f"- **标志物类型**: {', '.join(sorted(list(unique_types)))}")

    summary_parts.append("\n---")

    # --- 2. 构建有限长度的详细信息列表 ---
    summary_parts.append(f"### 详细信息列表 (仅展示前 {detail_limit} 条)\n")

    # 只遍历 biomarkers 列表的前 detail_limit 个元素
    for i, biomarker in enumerate(biomarkers[:detail_limit]):
        title = biomarker.biomarker_name or f"记录 {i + 1}"
        summary_parts.append(f"#### {i + 1}. {title}\n")

        details = []
        if biomarker.biomarker_name:
            details.append(f"- **生物标志物名称**: {biomarker.biomarker_name}")
        if biomarker.disease_name:
            details.append(f"- **疾病名称**: {biomarker.disease_name}")
        if biomarker.biomarker_type:
            details.append(f"- **生物标志物类型**: {biomarker.biomarker_type}")
        if biomarker.biomarker_usage:
            details.append(f"- **应用/用途**: {biomarker.biomarker_usage}")
        if biomarker.reference:
            details.append(f"- **参考文献**: {biomarker.reference}")

        if not details:
            details.append("- *未检索到该记录的详细信息。*")

        summary_parts.append("\n".join(details))
        summary_parts.append("")

    # --- 3. 如果数据被截断，添加提示信息 ---
    if total_count > detail_limit:
        remaining_count = total_count - detail_limit
        summary_parts.append(f"\n> ... 另外还有 **{remaining_count}** 条记录未在此处显示。")

    return "\n".join(summary_parts)
