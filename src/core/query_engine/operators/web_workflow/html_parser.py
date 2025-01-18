from bs4 import BeautifulSoup
from langchain.text_splitter import TokenTextSplitter
from src.utils.text_processing import process_text_to_embedding
import logging


class HTML_Parser():
    '''
     HTML Parser for extracting and storing search results in long-term memory.
    '''
    
    def __init__(self, long_memory, search_results):
        '''
        Initialize the HTML Parser.
        :param long_memory: The long-term memory layer to store the search results.
        :param search_results: The search results to process.
        '''
        self.memory = long_memory
        self.search_results = search_results
        self.logger = logging.getLogger(self.__class__.__name__)

    def execute(self):
        '''
        Extract and store search results in long-term memory.
        '''
        try:
            # Initialize the TokenTextSplitter
            splitter = TokenTextSplitter(chunk_size=500)
            split_chunks = []
            # extract chunks from search results
            for search_result in self.search_results:
                page_snippet = search_result['page_snippet']
                html_source = search_result['page_result']
                soup = BeautifulSoup(html_source, "lxml")
                text = soup.get_text(" ", strip=True)  # Use space as a separator, strip whitespaces

                chunks = []            
                # Use LangChain to split text into chunks of 500 tokens
                split_text = splitter.split_text(text)
                split_snippet = splitter.split_text(page_snippet)
                split_chunks.extend(split_text + split_snippet)

            # Filter out empty chunks
            chunks.extend([chunk for chunk in split_chunks if chunk.strip()])

            for chunk in chunks:
                embedding = process_text_to_embedding(chunk)
                self.memory.store(embedding, chunk)
            self.logger.info(f"Loading completed successfully. All chunks are {len(chunks)}")
            
        except Exception as e:
            self.logger.error(f"Error during loading: {str(e)}")
            raise RuntimeError(f"Failed to load long-term memory: {str(e)}")
        
