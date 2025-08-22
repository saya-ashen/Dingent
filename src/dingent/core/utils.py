from pathlib import Path


def find_project_root(marker: str = "dingent.toml") -> Path | None:
    """
    从当前目录开始向上查找项目根目录。
    项目根目录由标记文件 (如 'dingent.toml') 的存在来标识。

    :param marker: 标记文件的名称。
    :return: 项目根目录的Path对象，如果未找到则返回None。
    """
    current_dir = Path.cwd().resolve()

    while current_dir != current_dir.parent:  # 循环直到文件系统的根目录
        if (current_dir / marker).exists():
            return current_dir
        current_dir = current_dir.parent

    # 检查最后一级的根目录 (例如 /)
    if (current_dir / marker).exists():
        return current_dir

    return current_dir
