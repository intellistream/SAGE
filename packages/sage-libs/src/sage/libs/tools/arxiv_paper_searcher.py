import re
import requests
from bs4 import BeautifulSoup
from bs4.element import Tag
from .base.base_tool import BaseTool
import logging


class _Searcher_Tool(BaseTool):
    def __init__(self):
        super().__init__(
            tool_name="_Searcher_Tool",
            tool_description="A tool that searches arXiv for papers based on a given query.",
            tool_version="1.0.0",
            input_types={
                "query": "str - The search query for arXiv papers.",
                "size": "int - The number of results per page (25, 50, 100, or 200). If None, use 25.",
                "max_results": "int - The maximum number of papers to return (default: 25). Should be less than or equal to 100."
            },
            output_type="list - A list of dictionaries containing paper information.",
            demo_commands=[
                {
                    "command": 'execution = tool.execute(query="tool agents with large language models")',
                    "description": "Search for papers about tool agents with large language models."
                },
                {
                    "command": 'execution = tool.execute(query="quantum computing", size=100, max_results=50)',
                    "description": "Search for quantum computing papers, with 100 results per page, returning a maximum of 50 papers."
                },
                {
                    "command": 'execution = tool.execute(query="machine learning", max_results=75)',
                    "description": "Search for machine learning papers, returning a maximum of 75 papers."
                },
            ],
            user_metadata={
                "valid_sizes": [25, 50, 100, 200],
                "base_url": "https://arxiv.org/search/"
            }
        )

    def build_tool(self):
        """
        No specific build required for this tool.
        """
        pass

    def execute(self, query, size=None, max_results=25):
        """
        Executes the arXiv search tool to find papers based on the given query.

        Parameters:
            query (str): The search query for arXiv papers.
            size (int): The number of results per page.
            max_results (int): The maximum number of papers to return.

        Returns:
            list: A list of dictionaries containing paper information.
        """
        self.user_metadata = self.user_metadata or {}
        valid_sizes = self.user_metadata.get("valid_sizes", [25, 50, 100, 200])
        base_url = self.user_metadata.get("base_url", "https://arxiv.org/search/")

        if size is None:
            size = 25
        elif size not in valid_sizes:
            size = min(valid_sizes, key=lambda x: abs(x - size))

        results = []
        start = 0

        max_results = min(max_results, 100) # NOTE: For traffic reasons, limit to 100 results

        while len(results) < max_results:
            params = {
                "searchtype": "all",
                "query": query,
                "abstracts": "show",
                "order": "",
                "size": str(size),
                "start": str(start)
            }

            try:
                response = requests.get(base_url, params=params)
                soup = BeautifulSoup(response.content, 'html.parser')

                papers = soup.find_all("li", class_="arxiv-result")  # type: ignore
                if not papers:
                    break

                for paper in papers:
                    if len(results) >= max_results:
                        break

                    title_elem = paper.find("p", class_="title")  # type: ignore
                    title = title_elem.text.strip() if title_elem else "No title found"

                    authors_elem = paper.find("p", class_="authors")  # type: ignore
                    authors = authors_elem.text.strip() if authors_elem else "No authors found"
                    authors = re.sub(r'^Authors:\s*', '', authors)
                    authors = re.sub(r'\s+', ' ', authors).strip()

                    abstract_elem = paper.find("span", class_="abstract-full")  # type: ignore
                    abstract = abstract_elem.text.strip() if abstract_elem else "No abstract available"
                    abstract = abstract.replace("△ Less", "").strip()

                    link_elem = paper.find("p", class_="list-title")  # type: ignore
                    link_tag = link_elem.find("a") if isinstance(link_elem, Tag) else None  # type: ignore
                    link = link_tag["href"] if isinstance(link_tag, Tag) and link_tag.has_attr("href") else "No link found"

                    results.append({
                        "title": title,
                        "authors": authors,
                        "abstract": abstract,
                        "link": link
                    })

                start += size

            except Exception as e:
                logging.error(f"Error searching arXiv: {e}")
                break

        return results[:max_results]

    def get_metadata(self):
        """
        Returns the metadata for the _Searcher_Tool.

        Returns:
            dict: A dictionary containing the tool's metadata.
        """
        metadata = super().get_metadata()
        return metadata

if __name__ == "__main__":

    import json

    print("ArXiv Search Tool Test")

    # Example usage of the _Searcher_Tool
    tool = _Searcher_Tool()

    # Get tool metadata
    metadata = tool.get_metadata()
    print("Tool Metadata:")
    print(metadata)

    # Sample query for searching arXiv
    query = ""
    # Execute the tool
    try:
        execution = tool.execute(query=query, size=50, max_results=10)
        print("\n==>> Execution:")
        print(json.dumps(execution, indent=4))  # Pretty print JSON
        print("\n==>> Search Results:")
        for i, paper in enumerate(execution, 1):
            print(f"{i}. {paper['title']}")
            print(f"   Authors: {paper['authors']}")
            print(f"   Abstract: {paper['abstract'][:2000]}")
            print(f"   Link: {paper['link']}")
            print()
    except Exception as e:
        print(f"Execution failed: {e}")

    print("Done!")