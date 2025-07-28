# i18n_markers.py

# 这个文件仅用于i18n字符串提取，程序在运行时永远不会导入或执行它。
# 它的唯一目的是给 `pybabel extract` 命令提供一个可以扫描的静态字符串列表。

import gettext

_ = gettext.gettext


def _strings_for_translation_only():
    # --- 从 settings.mcp_servers 中提取的名称 ---

    _("biocode")
    _("bioka")
    _("genebase")
    _("gsa")
    _("idog")
    _("ewas")

    # --- 从 settings.llm_type 中提取的可能值 ---
    _("DeepSeek-V3")

    # --- 从 settings.llm_funcall 中提取的可能值 ---
    _("Llama.cpp")
