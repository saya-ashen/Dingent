# arXiv MCP Server

[![MCP Compatible](https://img.shields.io/badge/MCP-Compatible-purple.svg)](https://modelcontextprotocol.io)
[![Python](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![smithery badge](https://smithery.ai/badge/@prashalruchiranga/arxiv-mcp-server)](https://smithery.ai/server/@prashalruchiranga/arxiv-mcp-server)

A Model Context Protocol (MCP) server that enables interacting with the arXiv API using natural language.

## Features
- Retrieve metadata about scholarly articles hosted on arXiv.org
- Download articles in PDF format to the local machine
- Search arXiv database for a particular query
- Retrieve articles and load them into a large language model (LLM) context

## Tools
- **get_article_url**
    - Retrieve the URL of an article hosted on arXiv.org based on its title
        - `title` (String): Article title
- **download_article**
    - Download the article hosted on arXiv.org as a PDF file
        - `title` (String): Article title
- **load_article_to_context**
    - Load the article hosted on arXiv.org into context of a LLM
        - `title` (String): Article title
- **get_details**
    - Retrieve metadata of an article hosted on arXiv.org based on its title
        - `title` (String): Article title
- **search_arxiv**
    - Performs a search query on the arXiv API based on specified parameters and returns matching article metadata
        - `all_fields` (String): General keyword search across all metadata fields
        - `title` (String): Keyword(s) to search for within the titles of articles
        - `author` (String): Author name(s) to filter results by
        - `abstract` (String): Keyword(s) to search for within article abstracts
        - `start` (int): Index of the first result to return

## Setup

### MacOS

Clone the repository
```
git clone https://github.com/prashalruchiranga/arxiv-mcp-server.git
cd arxiv-mcp-server
```
Install `uv` package manager. For more details on installing, visit the [official uv documentation](https://docs.astral.sh/uv/getting-started/installation/).
```
# Using Homebrew
brew install uv

# or
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Create and activate virtual environment.
```
uv venv --python=python3.13
source .venv/bin/activate
```

Install development dependencies.
```
uv sync
```

### Windows

Install `uv` package manager. For more details on installing, visit the [official uv documentation](https://docs.astral.sh/uv/getting-started/installation/).
```
# Use irm to download the script and execute it with iex
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```
Close and reopen the shell, then clone the repository.
```
git clone https://github.com/prashalruchiranga/arxiv-mcp-server.git
cd arxiv-mcp-server
```

Create and activate virtual environment.
```
uv venv --python=python3.13
source .venv\Scripts\activate
```

Install development dependencies.
```
uv sync
```

## Usage with Claude Desktop
To enable this integration, add the server configuration to your `claude_desktop_config.json` file. Make sure to create the file if it doesn’t exist.

On MacOS: `~/Library/Application Support/Claude/claude_desktop_config.json` On Windows: `%APPDATA%/Roaming/Claude/claude_desktop_config.json`

```
{
  "mcpServers": {
    "arxiv-server": {
      "command": "uv",
      "args": [
        "--directory",
        "/ABSOLUTE/PATH/TO/PARENT/FOLDER/arxiv-mcp-server/src/arxiv_server",
        "run",
        "server.py"
      ],
      "env": {
        "DOWNLOAD_PATH": "/ABSOLUTE/PATH/TO/DOWNLOADS/FOLDER"
      }
    }
  }
}
```

You may need to put the full path to the uv executable in the command field. You can get this by running `which uv` on MacOS or `where uv` on Windows.

## Example Prompts
```
Can you get the details of 'Reasoning to Learn from Latent Thoughts' paper?
```
```
Get the papers authored or co-authored by Yann Lecun on convolutional neural networks
```
```
Download the attention is all you need paper
```
```
Can you get the papers by Andrew NG which have 'convolutional neural networks' in title?
```
```
Can you display the paper?
```
```
List the titles of papers by Yann LeCun. Paginate through the API until there are 30 titles
```

## License

Licensed under MIT. See the [LICENSE](https://github.com/prashalruchiranga/arxiv-mcp-server/blob/main/LICENSE).
