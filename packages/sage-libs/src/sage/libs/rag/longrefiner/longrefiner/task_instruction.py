SYSTEM_PROMPT_STEP1 = """\nYou are an assistant that performs step-by-step analysis of user queries."""
USER_PROMPT_STEP1 = """\n{question}"""

SYSTEM_PROMPT_STEP2 = "Divide the following long text into well-structured, appropriately sized chapters."
USER_PROMPT_STEP2 = "{doc_content}"

SYSTEM_PROMPT_STEP3 = """You will be provided with three inputs:
1. An user question that may need a long-form detail answer.
2. The abstract of a document
3. Outline of the document, contains titles of section and subsections in the document.

Your task is to understand the article based on its abstract and outline, and select all the parts that are helpful for answering questions (provide corresponding titles, or `abstract`).
"""

USER_PROMPT_STEP3 = (
    "**Document abstract**: {abstract}\n**Document outline**: {outline}\n**Question**:{question}\nOutput:"
)