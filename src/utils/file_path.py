import os

# Project root directory (assuming this file is in src/utils)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))

# Define paths
DATA_DIR = os.path.join(BASE_DIR, "data")
RAW_DOCS_DIR = os.path.join(DATA_DIR, "raw_docs")
RAW_FILE_DCM = os.path.join(RAW_DOCS_DIR, "raw_dcm")
RAW_FILE_LTM = os.path.join(RAW_DOCS_DIR, "raw_ltm")
TEST_DOCS_DIR = os.path.join(DATA_DIR, "test_docs")
TEST_FILE = os.path.join(TEST_DOCS_DIR, "test")
CORPUS_DIR = os.path.join(DATA_DIR, "corpus")
CORPUS_FILE = os.path.join(CORPUS_DIR, "clapnq.jsonl")
QUERY_DIR = os.path.join(DATA_DIR, "query")
QUERY_FILE = os.path.join(QUERY_DIR, "reference.jsonl")

# Define paths
SRC_DIR = os.path.join(BASE_DIR, "src")
CORE_DIR = os.path.join(SRC_DIR, "core")
PROMPTS_DIR = os.path.join(CORE_DIR, "prompts")
QAPROMPT_TEMPLATE = os.path.join(PROMPTS_DIR, "question_answer_template.txt")
REORGANIZE_TEMPLATE = os.path.join(PROMPTS_DIR, "reorganize_template.txt")
SUMMARIZATION_PROMPT_TEMPLATE = os.path.join(PROMPTS_DIR, "summarization_template.txt")

