-- Example SAGE Pipeline Definitions in SQL DSL
-- This demonstrates the flexible SQL-based approach for defining pipelines

-- Method 1: Inline definition with CREATE PIPELINE (most concise)
CREATE PIPELINE simple_qa (
  source = FileSource { data_path: "data/questions.txt", chunk_size: 1000 },
  retriever = ChromaRetriever { top_k: 5, collection_name: "documents" },
  promptor = QAPromptor { template: "Answer based on context: {context}" },
  generator = OpenAIGenerator { model: "gpt-3.5-turbo", temperature: 0.1 },
  sink = TerminalSink { format: "json" },
  source -> retriever -> promptor -> generator -> sink
);

-- Method 2: Traditional SQL table inserts (more verbose but flexible)
INSERT INTO pipeline VALUES 
  ('advanced_rag', 'Advanced RAG Pipeline', 'Multi-step retrieval with reranking', 'streaming');

INSERT INTO operator VALUES
  ('advanced_rag', 'source', 'FileSource', 1, '{"data_path": "data/corpus", "file_pattern": "*.txt"}'),
  ('advanced_rag', 'dense_retriever', 'ChromaRetriever', 2, '{"top_k": 20, "collection_name": "dense_embeddings"}'),
  ('advanced_rag', 'sparse_retriever', 'BM25Retriever', 3, '{"top_k": 20, "index_path": "data/bm25_index"}'),
  ('advanced_rag', 'reranker', 'CrossEncoderReranker', 4, '{"model": "cross-encoder/ms-marco-MiniLM", "top_k": 5}'),
  ('advanced_rag', 'promptor', 'QAPromptor', 5, '{"template": "Context: {context}\\nQuestion: {question}\\nAnswer:"}'),
  ('advanced_rag', 'generator', 'OpenAIGenerator', 6, '{"model": "gpt-4", "temperature": 0.2, "max_tokens": 500}'),
  ('advanced_rag', 'sink', 'StreamingSink', 7, '{"output_format": "markdown"}');

INSERT INTO pipeline_edge VALUES
  ('advanced_rag', 'source', 'dense_retriever'),
  ('advanced_rag', 'source', 'sparse_retriever'),
  ('advanced_rag', 'dense_retriever', 'reranker'),
  ('advanced_rag', 'sparse_retriever', 'reranker'),
  ('advanced_rag', 'reranker', 'promptor'),
  ('advanced_rag', 'promptor', 'generator'),
  ('advanced_rag', 'generator', 'sink');

-- Method 3: Mixed approach - define structure with CREATE, customize with INSERT
CREATE PIPELINE summarization (
  source = FileSource { data_path: "data/articles" },
  chunker = TextChunker { chunk_size: 2000, overlap: 200 },
  summarizer = OpenAIGenerator { model: "gpt-3.5-turbo" },
  sink = FileSink { output_path: "output/summaries.txt" },
  source -> chunker -> summarizer -> sink
);

-- Customize the summarizer with more specific configuration
UPDATE operator 
SET config = '{"model": "gpt-4", "temperature": 0.3, "system_prompt": "Summarize the following text in 2-3 sentences, focusing on key insights and actionable information."}'
WHERE pipeline_id = 'summarization' AND operator_id = 'summarizer';

-- Example of a complex multi-modal pipeline
CREATE PIPELINE multimodal_analysis (
  image_source = ImageSource { data_path: "data/images", formats: ["jpg", "png"] },
  text_source = FileSource { data_path: "data/descriptions.txt" },
  image_processor = VisionProcessor { model: "clip-vit-base-patch32" },
  text_processor = TextEmbedder { model: "sentence-transformers/all-MiniLM-L6-v2" },
  fusion = MultiModalFusion { strategy: "concatenate" },
  classifier = MLClassifier { model_path: "models/multimodal_classifier.pkl" },
  sink = CSVSink { output_path: "output/classifications.csv" },
  
  image_source -> image_processor -> fusion,
  text_source -> text_processor -> fusion,
  fusion -> classifier -> sink
);