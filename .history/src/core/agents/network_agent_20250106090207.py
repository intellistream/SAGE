# NetworkAgent Operator
from bs4 import BeautifulSoup

class HTMLParser:
    def __init__(self, page_result):
        self.soup = BeautifulSoup(page_result, 'html.parser')

    def get_title(self):
        title_tag = self.soup.title
        return title_tag.string if title_tag else None

    def get_document(self):
        return self.soup
    
    def get_text(self):
        return self.soup.get_text(separator='\n', strip=True)

# 示例用法
if __name__ == "__main__":
    html_data = """
    <html>
        <head><title>Example Page</title></head>
        <body>
            <h1>Hello, World!</h1>
            <div>
                <p>This is a paragraph.</p>
                <p>This is another paragraph.</p>
                <ul>
                    <li>List item 1</li>
                    <li>List item 2</li>
                </ul>
            </div>
        </body>
    </html>
    """
    parser = HTMLParser(html_data)
    document = parser.get_document()
    print(parser.get_text())