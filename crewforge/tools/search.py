"""Web search tool for agents."""

from typing import ClassVar, Optional, Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

try:
    import httpx

    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False


class WebSearchInput(BaseModel):
    """Input schema for web search."""

    query: str = Field(..., description="Search query")
    num_results: int = Field(default=5, description="Number of results to return")


class WebSearchTool(BaseTool):
    """Tool to search the web for information."""

    name: str = "web_search"
    description: str = """Search the web for information. Use this to find:
    - Documentation for libraries/frameworks
    - Solutions to programming problems
    - Best practices and examples
    Returns search results with titles, URLs, and snippets."""
    args_schema: Type[BaseModel] = WebSearchInput

    # Configuration for search API (can be overridden)
    search_api_url: str = "https://api.search.brave.com/res/v1/web/search"
    api_key: Optional[str] = None

    def _run(self, query: str, num_results: int = 5) -> str:
        """Search the web."""
        if not HTTPX_AVAILABLE:
            return "Error: httpx is not installed."

        # If no API key, return a helpful message
        if not self.api_key:
            return self._fallback_search(query)

        try:
            headers = {
                "Accept": "application/json",
                "X-Subscription-Token": self.api_key,
            }
            params = {
                "q": query,
                "count": num_results,
            }

            with httpx.Client() as client:
                response = client.get(
                    self.search_api_url,
                    headers=headers,
                    params=params,
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()

            results = []
            web_results = data.get("web", {}).get("results", [])

            for i, result in enumerate(web_results[:num_results], 1):
                title = result.get("title", "No title")
                url = result.get("url", "")
                description = result.get("description", "No description")
                results.append(f"{i}. {title}\n   URL: {url}\n   {description}\n")

            if not results:
                return f"No results found for: {query}"

            return "\n".join(results)

        except Exception as e:
            return f"Search error: {str(e)}\n\nTrying fallback search..."

    def _fallback_search(self, query: str) -> str:
        """Fallback when no API key is configured."""
        return f"""Web search requires API configuration.

To enable web search:
1. Get a Brave Search API key from https://brave.com/search/api/
2. Set CREWFORGE_SEARCH_API_KEY environment variable

For now, here are some suggested resources for "{query}":
- Stack Overflow: https://stackoverflow.com/search?q={query.replace(' ', '+')}
- GitHub: https://github.com/search?q={query.replace(' ', '+')}
- MDN (for web): https://developer.mozilla.org/en-US/search?q={query.replace(' ', '+')}
- Docs.rs (for Rust): https://docs.rs/releases/search?query={query.replace(' ', '+')}
- PyPI (for Python): https://pypi.org/search/?q={query.replace(' ', '+')}
"""


class CodeSearchInput(BaseModel):
    """Input schema for code search."""

    query: str = Field(..., description="Code search query")
    language: Optional[str] = Field(
        default=None, description="Programming language filter"
    )
    num_results: int = Field(default=5, description="Number of results to return")


class CodeSearchTool(BaseTool):
    """Tool to search for code examples on GitHub."""

    name: str = "code_search"
    description: str = """Search GitHub for code examples.
    Useful for finding implementation patterns and examples."""
    args_schema: Type[BaseModel] = CodeSearchInput

    github_token: Optional[str] = None

    def _run(
        self, query: str, language: Optional[str] = None, num_results: int = 5
    ) -> str:
        """Search for code on GitHub."""
        if not HTTPX_AVAILABLE:
            return "Error: httpx is not installed."

        try:
            headers = {
                "Accept": "application/vnd.github.v3+json",
            }
            if self.github_token:
                headers["Authorization"] = f"token {self.github_token}"

            search_query = query
            if language:
                search_query += f" language:{language}"

            params = {
                "q": search_query,
                "per_page": num_results,
            }

            with httpx.Client() as client:
                response = client.get(
                    "https://api.github.com/search/code",
                    headers=headers,
                    params=params,
                    timeout=30.0,
                )

                if response.status_code == 403:
                    return "GitHub API rate limit exceeded. Set GITHUB_TOKEN for higher limits."

                response.raise_for_status()
                data = response.json()

            results = []
            for item in data.get("items", [])[:num_results]:
                repo = item.get("repository", {}).get("full_name", "unknown")
                path = item.get("path", "")
                url = item.get("html_url", "")
                results.append(f"- {repo}/{path}\n  {url}\n")

            if not results:
                return f"No code found for: {query}"

            return "Found code examples:\n\n" + "\n".join(results)

        except Exception as e:
            return f"Code search error: {str(e)}"


class DocumentationSearchInput(BaseModel):
    """Input schema for documentation search."""

    package: str = Field(..., description="Package/library name")
    language: str = Field(..., description="Programming language (python, javascript, rust, go)")
    topic: Optional[str] = Field(default=None, description="Specific topic to search for")


class DocumentationSearchTool(BaseTool):
    """Tool to search package documentation."""

    name: str = "doc_search"
    description: str = """Search documentation for a specific package/library.
    Supports Python, JavaScript, Rust, and Go packages."""
    args_schema: Type[BaseModel] = DocumentationSearchInput

    DOC_URLS: ClassVar[dict[str, str]] = {
        "python": "https://pypi.org/project/{package}/",
        "javascript": "https://www.npmjs.com/package/{package}",
        "rust": "https://docs.rs/{package}/latest/{package}/",
        "go": "https://pkg.go.dev/{package}",
    }

    def _run(
        self, package: str, language: str, topic: Optional[str] = None
    ) -> str:
        """Search documentation."""
        language = language.lower()

        if language not in self.DOC_URLS:
            return f"Unsupported language: {language}. Supported: python, javascript, rust, go"

        base_url = self.DOC_URLS[language].format(package=package)

        result = f"Documentation for {package} ({language}):\n"
        result += f"URL: {base_url}\n\n"

        if topic:
            result += f"Suggested search: {base_url}?q={topic.replace(' ', '+')}\n"

        # Add common doc patterns
        if language == "python":
            result += f"ReadTheDocs: https://{package}.readthedocs.io/\n"
        elif language == "javascript":
            result += f"API Docs: {base_url}#api\n"
        elif language == "rust":
            result += f"Examples: https://docs.rs/{package}/latest/{package}/#examples\n"

        return result
