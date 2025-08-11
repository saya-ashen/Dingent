import difflib
import json
import os
import re

import feedparser
import fitz
import httpx
from mcp.server.fastmcp import Context, FastMCP

mcp = FastMCP("arxiv-server")

USER_AGENT = "arxiv-app/1.0"
ARXIV_API_BASE = "https://export.arxiv.org/api"
DOWNLOAD_PATH = os.getenv("DOWNLOAD_PATH")


async def make_api_call(url: str, params: dict[str, str]) -> str | None:
    """Make a request to the arXiv API."""
    headers = {"User-Agent": USER_AGENT, "Accept": "application/atom+xml"}
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, params=params, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.text
        except Exception:
            return None


async def get_pdf(url: str) -> bytes | None:
    """Get PDF document as bytes from arXiv.org."""
    headers = {"User-Agent": USER_AGENT, "Accept": "application/pdf"}
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.content
        except Exception:
            return None


def find_best_match(target_title: str, entries: list, threshold: float = 0.8):
    """Find the entry whose title best matches the target title."""
    target_title_lower = target_title.lower()
    best_entry = None
    best_score = 0.0
    for entry in entries:
        entry_title_lower = entry.title.lower()
        score = difflib.SequenceMatcher(None, target_title_lower, entry_title_lower).ratio()
        if score > best_score:
            best_score = score
            best_entry = entry
    if best_score >= threshold:
        return best_entry
    return None


async def fetch_information(title: str):
    """Get information about the article."""
    formatted_title = format_text(title)
    url = f"{ARXIV_API_BASE}/query"
    params = {"search_query": f"ti:{formatted_title}", "start": 0, "max_results": 25}
    data = await make_api_call(url, params=params)
    if data is None:
        return "Unable to retrieve data from arXiv.org."
    feed = feedparser.parse(data)
    error_msg = (
        "Unable to extract information for the provided title. This issue may stem from an incorrect or incomplete title, or because the work has not been published on arXiv."
    )
    if not feed.entries:
        return error_msg
    best_match = find_best_match(target_title=formatted_title, entries=feed.entries)
    if best_match is None:
        return str(error_msg)
    return best_match


async def get_url_and_arxiv_id(title: str) -> tuple[str, str] | str:
    """Get URL of the article hosted on arXiv.org."""
    info = await fetch_information(title)
    if isinstance(info, str):
        return info
    arxiv_id = info.id.split("/abs/")[-1]
    direct_pdf_url = f"https://arxiv.org/pdf/{arxiv_id}"
    return (direct_pdf_url, arxiv_id)


def format_text(text: str) -> str:
    """Clean a given text string by removing escape sequences and leading and trailing whitespaces."""
    # Remove common escape sequences
    text_without_escapes = re.sub(r"\\[ntr]", " ", text)
    # Replace colon with space
    text_without_colon = text_without_escapes.replace(":", " ")
    # Remove both single quotes and double quotes
    text_without_quotes = re.sub(r'[\'"]', "", text_without_colon)
    # Collapse multiple spaces into one
    text_single_spaced = re.sub(r"\s+", " ", text_without_quotes)
    # Trim leading and trailing spaces
    cleaned_text = text_single_spaced.strip()
    return cleaned_text


@mcp.tool()
async def get_article_url(title: str) -> str:
    """
    Retrieve the URL of an article hosted on arXiv.org based on its title. Use this tool only
    for retrieving the URL. This tool searches for the article based on its title, and then
    fetches the corresponding URL from arXiv.org.

    Args:
        title: Article title.

    Returns:
        URL that can be used to retrieve the article.
    """
    result = await get_url_and_arxiv_id(title)
    if isinstance(result, str):
        return result
    article_url, _ = result
    return article_url


@mcp.tool()
async def download_article(title: str) -> str:
    """
    Download the article hosted on arXiv.org as a PDF file. This tool searches for the article based on its
    title, retrieves the article's PDF, and saves it to a specified download location using the arXiv ID as
    the filename.

    Args:
        title: Article title.

    Returns:
        Success or error message.
    """
    result = await get_url_and_arxiv_id(title)
    if isinstance(result, str):
        return result
    article_url, arxiv_id = result
    pdf_doc = await get_pdf(article_url)
    if pdf_doc is None:
        return "Unable to retrieve the article from arXiv.org."
    file_path = os.path.join(DOWNLOAD_PATH, f"{arxiv_id}.pdf")
    try:
        with open(file_path, "wb") as file:
            file.write(pdf_doc)
        return f"Download successful. Find the PDF at {DOWNLOAD_PATH}"
    except Exception:
        return "Unable to save the article to local directory."


@mcp.tool()
async def load_article_to_context(title: str) -> str:
    """
    Load the article hosted on arXiv.org into context. This tool searches for the article based on its
    title, retrieves the article content, and loads text content into LLM context.

    Args:
        title: Article title.

    Returns:
        Article as a text string or error message.
    """
    result = await get_url_and_arxiv_id(title)
    if isinstance(result, str):
        return result
    article_url, _ = result
    pdf_doc = await get_pdf(article_url)
    if pdf_doc is None:
        return "Unable to retrieve the article from arXiv.org."
    pymupdf_doc = fitz.open(stream=pdf_doc, filetype="pdf")
    content = ""
    for page in pymupdf_doc:
        content += page.get_text()
    return content


@mcp.tool()
async def get_details(title: str) -> str:
    """
    Retrieve information of an article hosted on arXiv.org based on its title. This tool searches for the article
    based on its title and retrieves arXiv ID, title, authors, link, direct PDF URL, published timestamp, last
    updated timestamp, and summary.

    Args:
        title: Article title.

    Returns:
        A JSON-formatted string containing article details if retrieval is successful;
        otherwise, a plain error message string.
    """
    info = await fetch_information(title)
    if isinstance(info, str):
        return info
    id = info.id
    link = info.link
    article_title = info.title
    authors = [author["name"] for author in info.authors]
    arxiv_id = id.split("/abs/")[-1]
    direct_pdf_url = f"https://arxiv.org/pdf/{arxiv_id}"
    updated = getattr(info, "updated", "Unknown")
    published = getattr(info, "published", "Unknown")
    summary = getattr(info, "summary", "Unknown")
    info_dict = {
        "arXiv ID": arxiv_id,
        "Title": article_title,
        "Authors": authors,
        "Link": link,
        "Direct PDF URL": direct_pdf_url,
        "Published": published,
        "Updated": updated,
        "Summary": summary,
    }
    return json.dumps(info_dict)


@mcp.tool()
async def search_arxiv(
    ctx: Context,
    all_fields: str | None = None,
    title: str | None = None,
    author: str | None = None,
    abstract: str | None = None,
    start: int = 0,
):
    """
    Performs a search query on the arXiv API based on specified parameters and returns matching article metadata.
    This function allows for flexible querying of the arXiv database. Only parameters that are explicitly provided
    will be included in the final search query. Results are returned in a JSON-formatted string with article titles
    as keys and their corresponding arXiv IDs as values.

    Args:
        all_fields: General keyword search across all metadata fields including title, abstract, authors, comments, and categories.
        title: Keyword(s) to search for within the titles of articles.
        author: Author name(s) to filter results by.
        abstract: Keyword(s) to search for within article abstracts.
        start: Index of the first result to return; used for paginating through search results. Defaults to 0.

    Returns:
        A JSON-formatted string containing article titles and their associated arXiv IDs;
        otherwise, a plain error message string.
    """

    prefixed_params = []
    if author:
        author = format_text(author)
        prefixed_params.append(f"au:{author}")
    if all_fields:
        all_fields = format_text(all_fields)
        prefixed_params.append(f"all:{all_fields}")
    if title:
        title = format_text(title)
        prefixed_params.append(f"ti:{title}")
    if abstract:
        abstract = format_text(abstract)
        prefixed_params.append(f"abs:{abstract}")
    # Construct search query
    search_query = " AND ".join(prefixed_params)
    params = {"search_query": search_query, "start": start, "max_results": 10}
    await ctx.info("Calling the API")
    response = await make_api_call(f"{ARXIV_API_BASE}/query", params=params)
    if response is None:
        return "Unable to retrieve data from arXiv.org."
    feed = feedparser.parse(response)
    error_msg = "Unable to extract information for your query. This issue may stem from an incorrect search query."
    if not feed.entries:
        return error_msg
    entries = {}
    await ctx.info("Extracting information")
    for entry in feed.entries:
        id = entry.id
        article_title = entry.title
        arxiv_id = id.split("/abs/")[-1]
        authors = [author["name"] for author in entry.authors]
        entries[article_title] = {"arXiv ID": arxiv_id, "Authors": authors}
    return entries


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
