import sqlite3

from click.testing import CliRunner
from cookiecutter.exceptions import RepositoryNotFound

from dingent.cli import cli

COOKIEPATH = "dingent.cli.cookiecutter"


class TestDingentCli:

    def test_init_success_flow(self, mocker, tmp_path):
        """
        测试 'init' 命令的完整成功流程。
        """
        # 1. Arrange (准备)
        runner = CliRunner()
        # 使用 mocker 来模拟 cookiecutter 函数
        mock_cookiecutter = mocker.patch(COOKIEPATH)

        # 定义 cookiecutter 将要“创建”的项目路径
        project_path = tmp_path / "my-awesome-agent"
        # 让模拟的 cookiecutter 函数返回这个路径
        mock_cookiecutter.return_value = str(project_path)

        # 在这个虚拟的项目路径下，创建 SQL 文件所需的目录结构
        sql_dir = project_path / "mcp" / "data"
        sql_dir.mkdir(parents=True)

        # 创建一个有效的 SQL 文件
        sql_file = sql_dir / "chinook.sql"
        sql_content = """
        CREATE TABLE artists (ArtistId INTEGER PRIMARY KEY, Name TEXT);
        INSERT INTO artists (ArtistId, Name) VALUES (1, 'AC/DC');
        """
        sql_file.write_text(sql_content, encoding='utf-8')

        result = runner.invoke(cli, ['init', 'my-awesome-agent', '--template', 'basic'])

        # 3. Assert (断言)
        assert result.exit_code == 0
        assert "Project initialized successfully!" in result.output
        assert "Converting each .sql file" in result.output
        assert "Conversion complete. 1 succeeded, 0 failed." in result.output

        # 验证 mock 对象是否被正确调用
        mock_cookiecutter.assert_called_once()
        call_args = mock_cookiecutter.call_args[1]
        assert call_args['extra_context'] == {'project_slug': 'my-awesome-agent'}
        assert call_args['directory'] == 'templates/basic'

        # 验证数据库文件是否已创建和内容是否正确
        db_path = sql_dir / "chinook.db"
        assert db_path.exists()

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT Name FROM artists WHERE ArtistId = 1;")
        artist_name = cursor.fetchone()[0]
        conn.close()
        assert artist_name == 'AC/DC'

    def test_init_cookiecutter_repo_not_found(self, mocker):
        """测试当 cookiecutter 找不到仓库时，是否能优雅地处理异常。"""
        # Arrange
        runner = CliRunner()
        # 使用 mocker.patch 并设置 side_effect 来模拟异常抛出
        mocker.patch(COOKIEPATH, side_effect=RepositoryNotFound("Repo not found"))

        # Act
        result = runner.invoke(cli, ['init', 'any-project'])

        # Assert
        assert result.exit_code == 1
        assert "Error: Repository not found" in result.output
