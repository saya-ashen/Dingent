import os
import shutil
import sqlite3
import subprocess
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


def is_uv_installed():
    """Checks if 'uv' is available in the system's PATH."""
    return shutil.which('uv') is not None

def get_frontend_installer():
    """
    Determines the available frontend package manager.
    Prefers 'bun', falls back to 'npm'.
    Returns a tuple: (tool_name, install_command_list) or (None, None).
    """
    if shutil.which('bun'):
        return 'bun', ['bun', 'install']
    if shutil.which('npm'):
        return 'npm', ['npm', 'install']
    return None, None

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

        # --- 步骤 3: 使用 uv sync 安装依赖 ---
        click.secho("\n📦 Installing project dependencies with 'uv sync'...", fg='cyan')

        if not is_uv_installed():
            click.secho("⚠️ Warning: 'uv' command not found. Skipping dependency installation.", fg='yellow')
            click.echo("Please install uv (https://github.com/astral-sh/uv) and run 'uv sync' in the 'mcp' and 'backend' directories manually.")
        else:
            dirs_to_install = ['mcp', 'backend']
            install_errors = False

            for subdir_name in dirs_to_install:
                target_dir = project_path / subdir_name
                # 检查目标目录和 pyproject.toml 文件是否存在
                if target_dir.is_dir() and (target_dir / 'pyproject.toml').is_file():
                    click.echo(f"   -> Found 'pyproject.toml' in '{subdir_name}'. Running 'uv sync'...")

                    try:
                        # 在目标目录中执行 uv sync 命令
                        result = subprocess.run(
                            ['uv', 'sync'],
                            cwd=str(target_dir), # 设置命令执行的工作目录
                            capture_output=True, # 捕获标准输出和标准错误
                            text=True,           # 以文本模式处理输出
                            check=False          # 我们自己检查返回码，不让它自动抛出异常
                        )

                        if result.returncode == 0:
                            click.secho(f"     ✅ Successfully installed dependencies in '{subdir_name}'.", fg='green')
                        else:
                            # 如果命令失败，打印错误信息
                            install_errors = True
                            click.secho(f"     ❌ Error installing dependencies in '{subdir_name}'.", fg='red')
                            click.echo("     --- UV Error Output ---")
                            click.echo(result.stderr)
                            click.echo("     -----------------------")

                    except Exception as e:
                        install_errors = True
                        click.secho(f"     ❌ An unexpected error occurred while running uv in '{subdir_name}': {e}", fg='red')
                else:
                    click.secho(f"   -> Skipping '{subdir_name}', directory or 'pyproject.toml' not found.", fg='blue')

            if not install_errors:
                 click.secho("\n✅ All dependencies installed successfully!", fg='green')
            else:
                 click.secho("\n⚠️  Some dependencies failed to install. Please check the errors above.", fg='yellow')

        # --- 步骤 4: 安装前端依赖 (bun install 或 npm install) ---
        click.secho("\n🌐 Installing frontend dependencies...", fg='cyan')

        tool_name, install_command = get_frontend_installer()

        if not tool_name:
            click.secho("⚠️ Warning: Neither 'bun' nor 'npm' found. Skipping frontend dependency installation.", fg='yellow')
            click.echo("   Please install Bun or Node.js and run the install command in the 'frontend' directory manually.")
        else:
            frontend_dir_name = 'frontend' # 假设你的前端目录名为 'frontend'
            frontend_dir = project_path / frontend_dir_name

            if frontend_dir.is_dir() and (frontend_dir / 'package.json').is_file():
                click.echo(f"   -> Found 'package.json' in '{frontend_dir_name}'. Running '{' '.join(install_command)}'...")

                try:
                    result = subprocess.run(
                        install_command,
                        cwd=str(frontend_dir),
                        capture_output=True,
                        text=True,
                        check=False
                    )
                    if result.returncode == 0:
                        click.secho(f"     ✅ Successfully installed frontend dependencies using {tool_name}.", fg='green')
                    else:
                        click.secho(f"     ❌ Error installing frontend dependencies with {tool_name}.", fg='red')
                        click.echo("     --- Installer Error Output ---")
                        click.echo(result.stderr)
                        click.echo("     ----------------------------")

                except Exception as e:
                    click.secho(f"     ❌ An unexpected error occurred while running {tool_name}: {e}", fg='red')
            else:
                 click.secho(f"   -> Skipping '{frontend_dir_name}', directory or 'package.json' not found.", fg='blue')
        # <--- 新增前端部分结束 --->


        # --- 步骤 5: 显示最终成功信息 ---
        final_project_name = project_path.name
        click.secho("\n✅ Project initialized successfully!", fg='green', bold=True)
        click.echo("\nNext steps:")
        click.echo(f"  1. Navigate to your new project: cd {final_project_name}")
        click.echo("  2. Dependencies for backend, mcp, and frontend have been installed.") # <--- 修改了这里的提示
        click.echo("  3. Start building your amazing agent!")

    except RepositoryNotFound:
        click.secho(f"\n❌ Error: Repository not found at {REPO_URL}", fg='red', bold=True)
        click.echo("Please check the URL and your network connection.")
        sys.exit(1)
    except Exception as e:
        click.secho(f"\n❌ An error occurred: {e}", fg='red', bold=True)
        sys.exit(1)
