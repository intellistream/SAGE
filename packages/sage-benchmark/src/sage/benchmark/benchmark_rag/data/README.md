# RAG Examples - Data Files

This directory contains sample data files for RAG (Retrieval-Augmented Generation) examples.

## Files

### Query Files
- **`queries.jsonl`** - Sample queries for testing RAG pipelines
  - Used by: Dense retrieval, sparse retrieval, QA examples

### Knowledge Base Files
- **`qa_knowledge_base.txt`** - Plain text knowledge base
- **`qa_knowledge_base.pdf`** - PDF format knowledge base
- **`qa_knowledge_base.md`** - Markdown format knowledge base
- **`qa_knowledge_base.docx`** - Word document knowledge base
- **`qa_knowledge_chromaDB.txt`** - ChromaDB specific knowledge
- **`qa_knowledge_rag.md`** - RAG-specific knowledge

### Sample Data
- **`sample/question.txt`** - Single question for quick tests
- **`sample/evaluate.json`** - Evaluation dataset

## Usage

These files are referenced in the configuration files located in `../config/`.

Example configuration:
```yaml
source:
  data_path: "examples/rag/data/queries.jsonl"
  
retriever:
  preload_knowledge_file: "examples/rag/data/qa_knowledge_base.txt"
```

## Custom Data

You can add your own data files here and reference them in your configurations.
