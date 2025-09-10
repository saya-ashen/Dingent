import requests
from typing import List, Dict, Union, Any

BASE_API_URL = "http://hn.algolia.com/api/v1"
DEFAULT_NUM_STORIES = 10

# TODO(maybe): Update this to be user/claude configurable
DEFAULT_NUM_COMMENTS = 10
DEFAULT_COMMENT_DEPTH = 2

def _validate_comments_is_list_of_dicts(comments: List[Any]) -> bool:
    """
    Validates if the comments list contains dictionaries or just IDs.

    Args:
        comments: List of comments to validate

    Returns:
        bool: False if comments contains IDs that need to be fetched, True if comments are already dictionaries

    This is used to determine if we need to fetch the full story info to get comment details.
    """
    return not isinstance(comments[0], int)

def _get_story_info(story_id: int) -> Dict:
    """
    Fetches detailed information about a Hacker News story.

    Args:
        story_id: The ID of the story to fetch

    Returns:
        Dict: Raw story data from the HN API including title, author, points, url and comments

    Raises:
        requests.exceptions.RequestException: If the API request fails
    """
    url = f"{BASE_API_URL}/items/{story_id}"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()

def _format_story_details(story: Union[Dict, int], basic: bool = True) -> Dict:
    """
    Formats a story's details into a standardized dictionary structure.

    Args:
        story: Either a story ID or dictionary containing story data
        basic: If True, excludes comments. If False, includes formatted comments to depth of 2

    Returns:
        Dict with the following structure:
        {
            "id": int,          # Story ID
            "title": str,       # Story title if present
            "url": str,         # Story URL if present
            "author": str,      # Author username
            "points": int,      # Points (may be null)
            "comments": list    # List of comment dicts (only if basic=False)
        }

    The function handles both raw story IDs and story dictionaries, fetching additional
    data if needed. For non-basic requests, it ensures comments are properly formatted.
    """
    if isinstance(story, int):
        story = _get_story_info(story)
    output = {
        "id": story["story_id"],
        "author": story["author"],
    }
    if "title" in story:
        output["title"] = story["title"]
    if "points" in story:
        output["points"] = story["points"]
    if "url" in story:
        output["url"] = story["url"]
    if not basic:
        if story["children"] and _validate_comments_is_list_of_dicts(story["children"]):
            story = _get_story_info(story["story_id"])
        output["comments"] = [
            _format_comment_details(child) for child in story["children"]
        ]
    return output

def _format_comment_details(comment: Dict, depth: int = DEFAULT_COMMENT_DEPTH, num_comments: int = DEFAULT_NUM_COMMENTS) -> Dict:
    """
    Formats a comment and its replies into a standardized structure.

    Args:
        comment: Raw comment dictionary from the API
        depth: How many levels of nested comments to include (default: 2)
        num_comments: Maximum number of child comments to include per level (default: 10)

    Returns:
        Dict with the following structure:
        {
            "author": str,      # Comment author's username
            "text": str,        # Comment text content
            "comments": list    # List of nested comment dicts (only if depth > 1)
        }

    The function recursively formats nested comments up to the specified depth,
    limiting the number of child comments at each level to num_comments.
    """
    output = {
        "author": comment["author"],
        "text": comment["text"],
    }
    if depth > 1 and len(comment["children"]) > 0:
        output["comments"] = [
            _format_comment_details(child, depth - 1, num_comments) for child in comment["children"][:num_comments]
        ]
    return output

def get_stories(story_type: str, num_stories: int = DEFAULT_NUM_STORIES):
    """
    Fetches and formats a list of Hacker News stories of the specified type.

    Args:
        story_type: Category of stories to fetch. Must be one of:
                   - "top": Front page stories
                   - "new": Most recent stories
                   - "ask_hn": Ask HN posts
                   - "show_hn": Show HN posts
        num_stories: Number of stories to return (default: 10)

    Returns:
        List[Dict]: List of story dictionaries, each containing:
        {
            "id": int,          # Story ID
            "title": str,       # Story title
            "url": str,         # Story URL
            "author": str,      # Author username
            "points": int,      # Points (may be null)
        }

    Raises:
        ValueError: If story_type is not one of the valid options
        requests.exceptions.RequestException: If the API request fails
    """
    story_type = story_type.lower().strip()
    if story_type not in ["top", "new", "ask_hn", "show_hn"]:
        raise ValueError("story_type must be one of: top, new, ask_hn, show_hn")

    # Map story type to appropriate API parameters
    api_params = {
        "top": {"endpoint": "search", "tags": "front_page"},
        "new": {"endpoint": "search_by_date", "tags": "story"},
        "ask_hn": {"endpoint": "search", "tags": "ask_hn"},
        "show_hn": {"endpoint": "search", "tags": "show_hn"}
    }

    params = api_params[story_type]
    url = f"{BASE_API_URL}/{params['endpoint']}?tags={params['tags']}&hitsPerPage={num_stories}"
    response = requests.get(url)
    response.raise_for_status()
    return [_format_story_details(story) for story in response.json()["hits"]]

def search_stories(query: str, num_results: int = DEFAULT_NUM_STORIES, search_by_date: bool = False):
    """
    Searches Hacker News stories using a query string.

    Args:
        query: Search terms to find in stories
        num_results: Number of results to return (default: 10)
        search_by_date: If True, sorts by date. If False, sorts by relevance/points/comments (default: False)

    Returns:
        List[Dict]: List of matching story dictionaries, each containing:
        {
            "id": int,          # Story ID
            "title": str,       # Story title
            "url": str,         # Story URL
            "author": str,      # Author username
            "points": int,      # Points (may be null)
        }

    Raises:
        requests.exceptions.RequestException: If the API request fails
    """
    if search_by_date:
        url = f"{BASE_API_URL}/search_by_date?query={query}&hitsPerPage={num_results}&tags=story"
    else:
        url = f"{BASE_API_URL}/search?query={query}&hitsPerPage={num_results}&tags=story"
    print(url)
    response = requests.get(url)
    response.raise_for_status()
    return [_format_story_details(story) for story in response.json()["hits"]]

def get_story_info(story_id: int) -> Dict:
    """
    Fetches detailed information about a specific story including comments.

    Args:
        story_id: The ID of the story to fetch

    Returns:
        Dict containing full story details:
        {
            "id": int,          # Story ID
            "title": str,       # Story title
            "url": str,         # Story URL (may be null for text posts)
            "author": str,      # Author username
            "points": int,      # Points (may be null)
            "comments": list    # Nested list of comment dictionaries
        }

    Raises:
        requests.exceptions.RequestException: If the API request fails
    """
    story = _get_story_info(story_id)
    return _format_story_details(story, basic=False)

def _get_user_stories(user_name: str, num_stories: int = DEFAULT_NUM_STORIES) -> List[Dict]:
    """
    Fetches stories submitted by a specific user.

    Args:
        user_name: Username whose stories to fetch
        num_stories: Number of stories to return (default: 10)

    Returns:
        List[Dict]: List of story dictionaries authored by the user

    Raises:
        requests.exceptions.RequestException: If the API request fails
    """
    url = f"{BASE_API_URL}/search?tags=author_{user_name},story&hitsPerPage={num_stories}"
    response = requests.get(url)
    response.raise_for_status()
    return [_format_story_details(story) for story in response.json()["hits"]]

def get_user_info(user_name: str, num_stories: int = DEFAULT_NUM_STORIES) -> Dict:
    """
    Fetches information about a Hacker News user and their recent submissions.

    Args:
        user_name: Username to fetch information for
        num_stories: Number of user's stories to include (default: 10)

    Returns:
        Dict containing user information and recent stories:
        {
            "id": str,          # Username
            "created_at": str,  # Account creation timestamp
            "karma": int,       # User's karma points
            "about": str,       # User's about text (may be null)
            "stories": list     # List of user's recent story dictionaries
        }

    Raises:
        requests.exceptions.RequestException: If the API request fails
    """
    url = f"{BASE_API_URL}/users/{user_name}"
    response = requests.get(url)
    response.raise_for_status()
    response = response.json()
    response["stories"] = _get_user_stories(user_name, num_stories)
    return response
