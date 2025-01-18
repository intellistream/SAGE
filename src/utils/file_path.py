import os

# Project root directory (assuming this file is in src/utils)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))

# Define paths
DATA_DIR = os.path.join(BASE_DIR, "data")
RAW_DOCS_DIR = os.path.join(DATA_DIR, "raw_docs")
RAW_FILE = os.path.join(RAW_DOCS_DIR, "raw")
TEST_DOCS_DIR = os.path.join(DATA_DIR, "test_docs")
TEST_FILE = os.path.join(TEST_DOCS_DIR, "test")

# Define paths
SRC_DIR = os.path.join(BASE_DIR, "src")
CORE_DIR = os.path.join(SRC_DIR, "core")
PROMPTS_DIR = os.path.join(CORE_DIR, "prompts")
FUNCTION_DIR = os.path.join(PROMPTS_DIR, "functions")
QAPROMPT_TEMPLATE = os.path.join(PROMPTS_DIR, "question_answer_template.txt")
SUMMARIZATION_PROMPT_TEMPLATE = os.path.join(PROMPTS_DIR, "summarization_template.txt")

QA_SELF_EVAL_PROMPT_TEMPLATE = os.path.join(PROMPTS_DIR, "qa_self_eval_template.txt")
QA_DOMAIN_CLASSIFICATION_TEMPLATE = os.path.join(PROMPTS_DIR, "qa_domain_classification_template.txt")
QA_MUSIC_FUNCTION_TEMPLATE = os.path.join(FUNCTION_DIR, "qa_music_function_call_template.txt")
QA_MOVIE_FUNCTION_TEMPLATE = os.path.join(FUNCTION_DIR, "qa_movie_function_call_template.txt")
QA_FINANCE_FUNCTION_TEMPLATE = os.path.join(FUNCTION_DIR, "qa_finance_function_call_template.txt")
QA_SPORT_FUNCTION_TEMPLATE = os.path.join(FUNCTION_DIR, "qa_sport_function_call_template.txt")
QA_OPEN_FUNCTION_TEMPLATE = os.path.join(FUNCTION_DIR, "qa_open_function_call_template.txt")

KG_DOCS_DIR = os.path.join(DATA_DIR, "kg_docs")
KG_RESULTS_FILE = os.path.join(KG_DOCS_DIR, "kg_results.txt")
