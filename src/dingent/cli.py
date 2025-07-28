import sys

import click
from cookiecutter.exceptions import RepositoryNotFound
from cookiecutter.main import cookiecutter

REPO_URL = "https://github.com/saya-ashen/Dingent.git"

AVAILABLE_TEMPLATES = ["basic", "with-tools"]

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

    # 构造在仓库内的模板子目录路径
    template_dir_in_repo = f"templates/{template}"

    try:
        cookiecutter(
            REPO_URL,                      # 1. 传入整个仓库的 URL
            directory=template_dir_in_repo, # 2. 指定要使用的子目录
            checkout=checkout,             # 3. (可选) 指定分支/tag
            no_input=False,
            extra_context={'project_slug': project_name},
            output_dir="."
        )

        click.secho("\n✅ Project created successfully!", fg='green', bold=True)
        # ... (后续指引信息)

    except RepositoryNotFound:
        click.secho(f"\n❌ Error: Repository not found at {REPO_URL}", fg='red', bold=True)
        click.echo("Please check the URL and your network connection.")
        sys.exit(1)
    except Exception as e:
        click.secho(f"\n❌ An error occurred: {e}", fg='red', bold=True)
        sys.exit(1)

