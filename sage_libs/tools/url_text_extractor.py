from .base.base_tool import BaseTool
import requests
import os

from bs4 import BeautifulSoup

class URL_text_extractor(BaseTool):
    def __init__(self):
        super().__init__(
            tool_name="url_text_extractor",
            tool_description="A tool that can extract text from a URL",
            tool_version="1.0.0",
            input_types={"url": "str"},
            output_type="str",
            demo_commands=[
                {"command": 'execution = tool.execute(url="https://www.example.com")',
                    "description": "Extract text from a URL"},
                {"command": 'execution = tool.execute(url="https://www.baidu.com", depth=2)',
                    "description": "Extract text from a URL"}
            ],
            user_metadata={
                "limitation": "The URL_text_extractor_Tool provides general text extraction from a URL but has limitations: 1) May not extract all the text from the URL. 2) Might not extract the text in the correct format. 3) Performance varies with the complexity of the URL. 4) Struggles with culturally specific or domain-specific content. 5) May overlook details or misinterpret object relationships. For precise descriptions, consider: using it with other tools for context/verification, as an initial step before refinement, or in multi-step processes for ambiguity resolution. Verify critical information with specialized tools or human expertise when necessary."
            }
        )

    def extract_text(self, url: str):
        """
        Extract text from a URL
        """
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        return soup.get_text()

    def execute(self, url: str):
        try:
            return self.extract_text(url)
        except Exception as e:
            print(f"Error in URL_text_extractor: {e}")
            return None

        