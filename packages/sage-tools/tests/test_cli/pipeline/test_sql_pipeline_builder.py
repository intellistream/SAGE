"""Tests for SQL-based pipeline builder."""

import json
import tempfile
from pathlib import Path

import pytest

from sage.tools.cli.pipeline_builder.sql import (
    SQLPipelineStore,
    SQLPipelineCompiler,
    SQLPipelineDSLParser,
    OperatorNode,
    PipelineDefinition,
)


class TestSQLPipelineStore:
    """Test SQLPipelineStore functionality."""
    
    def test_store_and_load_pipeline(self):
        """Test storing and loading a pipeline."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_db:
            store = SQLPipelineStore(db_path=tmp_db.name)
            
            # Create test pipeline
            pipeline = PipelineDefinition(
                pipeline_id="test_pipeline",
                name="Test Pipeline",
                description="A test pipeline",
                mode="batch",
                operators=[
                    OperatorNode("source", "FileSource", 1, {"data_path": "test.txt"}),
                    OperatorNode("sink", "TerminalSink", 2, {"format": "json"}),
                ],
                edges=[("source", "sink")]
            )
            
            # Store pipeline
            store.store_pipeline(pipeline)
            
            # Load pipeline
            loaded = store.load_pipeline("test_pipeline")
            
            assert loaded is not None
            assert loaded.pipeline_id == "test_pipeline"
            assert loaded.name == "Test Pipeline"
            assert len(loaded.operators) == 2
            assert len(loaded.edges) == 1
            assert loaded.edges[0] == ("source", "sink")
            
            # Clean up
            Path(tmp_db.name).unlink()
    
    def test_list_pipelines(self):
        """Test listing all pipelines."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_db:
            store = SQLPipelineStore(db_path=tmp_db.name)
            
            # Store multiple pipelines
            for i in range(3):
                pipeline = PipelineDefinition(
                    pipeline_id=f"pipeline_{i}",
                    name=f"Pipeline {i}",
                    description=f"Test pipeline {i}",
                    mode="batch",
                    operators=[],
                    edges=[]
                )
                store.store_pipeline(pipeline)
            
            # List pipelines
            pipelines = store.list_pipelines()
            
            assert len(pipelines) == 3
            assert all(p.pipeline_id.startswith("pipeline_") for p in pipelines)
            
            # Clean up
            Path(tmp_db.name).unlink()
    
    def test_delete_pipeline(self):
        """Test deleting a pipeline."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_db:
            store = SQLPipelineStore(db_path=tmp_db.name)
            
            # Store pipeline
            pipeline = PipelineDefinition(
                pipeline_id="delete_me",
                name="Delete Me",
                description="Will be deleted",
                mode="batch",
                operators=[],
                edges=[]
            )
            store.store_pipeline(pipeline)
            
            # Verify it exists
            assert store.load_pipeline("delete_me") is not None
            
            # Delete it
            store.delete_pipeline("delete_me")
            
            # Verify it's gone
            assert store.load_pipeline("delete_me") is None
            
            # Clean up
            Path(tmp_db.name).unlink()


class TestSQLPipelineCompiler:
    """Test SQLPipelineCompiler functionality."""
    
    def test_compile_to_yaml(self):
        """Test compiling pipeline to YAML format."""
        pipeline = PipelineDefinition(
            pipeline_id="test_yaml",
            name="Test YAML",
            description="Test YAML compilation",
            mode="batch",
            operators=[
                OperatorNode("source", "FileSource", 1, {"data_path": "input.txt"}),
                OperatorNode("sink", "TerminalSink", 2, {"format": "json"}),
            ],
            edges=[("source", "sink")]
        )
        
        compiler = SQLPipelineCompiler()
        yaml_content = compiler.compile_to_yaml(pipeline)
        
        assert "pipeline:" in yaml_content
        assert "source:" in yaml_content
        assert "sink:" in yaml_content
        assert "input.txt" in yaml_content
        assert "format: json" in yaml_content
    
    def test_compile_to_python(self):
        """Test compiling pipeline to Python runner."""
        pipeline = PipelineDefinition(
            pipeline_id="test_python",
            name="Test Python",
            description="Test Python compilation",
            mode="streaming",
            operators=[
                OperatorNode("source", "FileSource", 1, {"data_path": "input.txt"}),
                OperatorNode("generator", "OpenAIGenerator", 2, {"model": "gpt-3.5-turbo"}),
                OperatorNode("sink", "TerminalSink", 3, {"format": "text"}),
            ],
            edges=[("source", "generator"), ("generator", "sink")]
        )
        
        compiler = SQLPipelineCompiler()
        python_content = compiler.compile_to_python(pipeline)
        
        assert "from sage" in python_content
        assert "FileSource" in python_content
        assert "OpenAIGenerator" in python_content
        assert "TerminalSink" in python_content
        assert "def main()" in python_content
        assert "streaming" in python_content or "run_streaming()" in python_content


class TestSQLPipelineDSLParser:
    """Test SQLPipelineDSLParser functionality."""
    
    def test_parse_create_pipeline_inline(self):
        """Test parsing CREATE PIPELINE with inline operators."""
        sql_content = """
        CREATE PIPELINE simple_qa (
          source = FileSource { data_path: "questions.txt", chunk_size: 1000 },
          retriever = ChromaRetriever { top_k: 5 },
          sink = TerminalSink { format: "json" },
          source -> retriever -> sink
        );
        """
        
        parser = SQLPipelineDSLParser()
        pipelines = parser.parse_statements(sql_content)
        
        assert len(pipelines) == 1
        pipeline = pipelines[0]
        
        assert pipeline.pipeline_id == "simple_qa"
        assert len(pipeline.operators) == 3
        assert len(pipeline.edges) == 2
        
        # Check operators
        source_op = next(op for op in pipeline.operators if op.op_id == "source")
        assert source_op.op_type == "FileSource"
        assert source_op.config["data_path"] == "questions.txt"
        assert source_op.config["chunk_size"] == 1000
        
        # Check edges
        assert ("source", "retriever") in pipeline.edges
        assert ("retriever", "sink") in pipeline.edges
    
    def test_parse_traditional_sql_inserts(self):
        """Test parsing traditional SQL INSERT statements."""
        sql_content = """
        INSERT INTO pipeline VALUES ('test_sql', 'Test SQL', 'SQL-based pipeline', 'batch');
        
        INSERT INTO operator VALUES
          ('test_sql', 'source', 'FileSource', 1, '{"data_path": "input.txt"}'),
          ('test_sql', 'sink', 'TerminalSink', 2, '{"format": "json"}');
        
        INSERT INTO pipeline_edge VALUES
          ('test_sql', 'source', 'sink');
        """
        
        parser = SQLPipelineDSLParser()
        pipelines = parser.parse_statements(sql_content)
        
        assert len(pipelines) == 1
        pipeline = pipelines[0]
        
        assert pipeline.pipeline_id == "test_sql"
        assert pipeline.name == "Test SQL"
        assert pipeline.mode == "batch"
        assert len(pipeline.operators) == 2
        assert len(pipeline.edges) == 1
        
        # Check operator configuration
        source_op = next(op for op in pipeline.operators if op.op_id == "source")
        assert source_op.config["data_path"] == "input.txt"
    
    def test_parse_config_block(self):
        """Test parsing configuration blocks."""
        parser = SQLPipelineDSLParser()
        
        # Test various value types
        config = parser._parse_config_block('data_path: "file.txt", top_k: 5, enabled: true, score: 0.95')
        
        assert config["data_path"] == "file.txt"
        assert config["top_k"] == 5
        assert config["enabled"] is True
        assert config["score"] == 0.95


class TestSQLIntegration:
    """Integration tests for the complete SQL pipeline system."""
    
    def test_end_to_end_workflow(self):
        """Test complete workflow: SQL → Store → Compile."""
        sql_content = """
        CREATE PIPELINE e2e_test (
          source = FileSource { data_path: "test.txt" },
          generator = OpenAIGenerator { model: "gpt-3.5-turbo", temperature: 0.1 },
          sink = TerminalSink { format: "text" },
          source -> generator -> sink
        );
        """
        
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_db:
            # Parse SQL
            parser = SQLPipelineDSLParser()
            pipelines = parser.parse_statements(sql_content)
            
            # Store in database
            store = SQLPipelineStore(db_path=tmp_db.name)
            for pipeline in pipelines:
                store.store_pipeline(pipeline)
            
            # Load from database
            loaded_pipeline = store.load_pipeline("e2e_test")
            assert loaded_pipeline is not None
            
            # Compile to YAML and Python
            compiler = SQLPipelineCompiler()
            yaml_content = compiler.compile_to_yaml(loaded_pipeline)
            python_content = compiler.compile_to_python(loaded_pipeline)
            
            # Verify generated content
            assert "source:" in yaml_content
            assert "generator:" in yaml_content
            assert "gpt-3.5-turbo" in yaml_content
            
            assert "def main()" in python_content
            assert "LocalEnvironment" in python_content
            
            # Clean up
            Path(tmp_db.name).unlink()


if __name__ == "__main__":
    pytest.main([__file__])