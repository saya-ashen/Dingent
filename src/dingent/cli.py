import os
import sqlite3
import sys
from pathlib import Path

import click
from cookiecutter.exceptions import RepositoryNotFound
from cookiecutter.main import cookiecutter

PROD_REPO_URL = "https://github.com/saya-ashen/Dingent.git"
DEV_REPO_URL = "/home/saya/Workspace/Dingent"

AVAILABLE_TEMPLATES = ["basic", "with-tools"]
IS_DEV_MODE = os.getenv('DINGENT_DEV')

REPO_URL = DEV_REPO_URL if IS_DEV_MODE else PROD_REPO_URL

@click.group()
def cli():
    """A CLI for the Dingent framework."""
    pass

@cli.command()
@click.argument('project_name')
@click.option(
    '--template', '-t',
    type=click.Choice(AVAILABLE_TEMPLATES, case_sensitive=False),
    default='basic',
    help='The project template to use.'
)
@click.option(
    '--checkout', '-c',
    default=None,
    help='The branch, tag, or commit to checkout.'
)
def init(project_name, template, checkout):
    """Creates a new agent project by pulling a template from the git repo."""
    click.secho(f"🚀 Initializing project from git repository: {REPO_URL}", fg='green')

    template_dir_in_repo = f"templates/{template}"

    try:
        created_project_path = cookiecutter(
            REPO_URL,
            directory=template_dir_in_repo,
            checkout=checkout,
            no_input=False,
            extra_context={'project_slug': project_name},
            output_dir="."
        )

        click.secho("\n✅ Project structure created successfully!", fg='green')

        # --- 步骤 2: 自动将每个 SQL 文件转换为同名的 SQLite 数据库 ---
        click.secho("\n✨ Converting each .sql file to a separate .db database...", fg='cyan')

        project_path = Path(created_project_path)
        sql_dir = project_path / 'mcp' / 'data'

        if not sql_dir.is_dir():
            click.secho(f"⚠️  Warning: SQL data directory not found at '{sql_dir}'. Skipping database creation.", fg='yellow')
        else:
            sql_files = sorted(sql_dir.glob('*.sql'))

            if not sql_files:
                click.secho(f"ℹ️  Info: No .sql files found in '{sql_dir}'. Nothing to do.", fg='blue')
            else:
                # 【关键改动】: 循环处理每个文件，并在循环内部处理数据库逻辑
                click.echo(f"   -> Found {len(sql_files)} SQL file(s).")
                success_count = 0
                error_count = 0

                for sql_file in sql_files:
                    # 使用 with_suffix('.db') 生成同名的数据库文件路径
                    db_path = sql_file.with_suffix('.db')

                    try:
                        click.echo(f"      - Converting '{sql_file.name}'  ->  '{db_path.name}'")

                        # 在循环内连接到特定的数据库文件
                        conn = sqlite3.connect(db_path)
                        cursor = conn.cursor()

                        with open(sql_file, encoding='utf-8') as f:
                            sql_script = f.read()

                        cursor.executescript(sql_script)
                        conn.commit()
                        conn.close()

                        success_count += 1

                    except sqlite3.Error as e:
                        # 如果单个文件转换失败，报告错误并继续处理下一个
                        click.secho(f"        ❌ Error: {e}", fg='red')
                        if db_path.exists():
                            db_path.unlink() # 清理创建失败的空文件
                        error_count += 1

                # 循环结束后提供一个总结
                summary_color = 'green' if error_count == 0 else 'yellow'
                click.secho(f"\n✅ Conversion complete. {success_count} succeeded, {error_count} failed.", fg=summary_color)


        # --- 步骤 3: 显示最终成功信息 ---
        final_project_name = project_path.name
        click.secho("\n✅ Project initialized successfully!", fg='green', bold=True)
        click.echo("\nNext steps:")
        click.echo(f"  1. Navigate to your new project: cd {final_project_name}")
        click.echo("  2. Install dependencies (if any).")
        click.echo("  3. Start building your agent!")

    except RepositoryNotFound:
        click.secho(f"\n❌ Error: Repository not found at {REPO_URL}", fg='red', bold=True)
        click.echo("Please check the URL and your network connection.")
        sys.exit(1)
    except Exception as e:
        click.secho(f"\n❌ An error occurred: {e}", fg='red', bold=True)
        sys.exit(1)
