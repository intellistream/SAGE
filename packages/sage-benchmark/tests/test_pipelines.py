"""
Tests for benchmark RAG pipelines
"""
import pytest
from pathlib import Path
import importlib.util


class TestPipelineImports:
    """Test that pipeline modules can be imported"""
    
    @pytest.fixture
    def pipelines_dir(self):
        """Get pipelines directory path"""
        return Path(__file__).parent.parent / "src" / "sage" / "benchmark" / "benchmark_rag" / "implementations" / "pipelines"
    
    def test_pipelines_directory_exists(self, pipelines_dir):
        """Verify pipelines directory exists"""
        assert pipelines_dir.exists(), "Pipelines directory should exist"
    
    def test_pipeline_files_present(self, pipelines_dir):
        """Verify expected pipeline files exist"""
        expected_pipelines = [
            "qa_dense_retrieval.py",
            "qa_sparse_retrieval_milvus.py",
            "qa_dense_retrieval_milvus.py",
        ]
        
        for pipeline_file in expected_pipelines:
            pipeline_path = pipelines_dir / pipeline_file
            assert pipeline_path.exists(), f"Pipeline file not found: {pipeline_file}"
    
    def test_dense_retrieval_pipeline_imports(self, pipelines_dir):
        """Test dense retrieval pipeline can be imported"""
        pipeline_path = pipelines_dir / "qa_dense_retrieval.py"
        
        if not pipeline_path.exists():
            pytest.skip("qa_dense_retrieval.py not found")
        
        spec = importlib.util.spec_from_file_location("qa_dense_retrieval", pipeline_path)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            try:
                spec.loader.exec_module(module)
                # Module loaded successfully
                assert True
            except Exception as e:
                pytest.fail(f"Failed to import qa_dense_retrieval.py: {e}")
    
    def test_sparse_retrieval_pipeline_imports(self, pipelines_dir):
        """Test sparse retrieval pipeline can be imported"""
        pipeline_path = pipelines_dir / "qa_sparse_retrieval_milvus.py"
        
        if not pipeline_path.exists():
            pytest.skip("qa_sparse_retrieval_milvus.py not found")
        
        spec = importlib.util.spec_from_file_location("qa_sparse_retrieval_milvus", pipeline_path)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            try:
                spec.loader.exec_module(module)
                # Module loaded successfully
                assert True
            except Exception as e:
                pytest.fail(f"Failed to import qa_sparse_retrieval_milvus.py: {e}")
    
    def test_milvus_retrieval_pipeline_imports(self, pipelines_dir):
        """Test milvus retrieval pipeline can be imported"""
        pipeline_path = pipelines_dir / "qa_dense_retrieval_milvus.py"
        
        if not pipeline_path.exists():
            pytest.skip("qa_dense_retrieval_milvus.py not found")
        
        spec = importlib.util.spec_from_file_location("qa_dense_retrieval_milvus", pipeline_path)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            try:
                spec.loader.exec_module(module)
                # Module loaded successfully
                assert True
            except Exception as e:
                pytest.fail(f"Failed to import qa_dense_retrieval_milvus.py: {e}")


class TestPipelineStructure:
    """Test pipeline code structure"""
    
    @pytest.fixture
    def pipelines_dir(self):
        """Get pipelines directory path"""
        return Path(__file__).parent.parent / "src" / "sage" / "benchmark" / "benchmark_rag" / "implementations" / "pipelines"
    
    def test_pipelines_not_empty(self, pipelines_dir):
        """Verify pipeline files are not empty"""
        python_files = list(pipelines_dir.glob("*.py"))
        python_files = [f for f in python_files if f.name != "__init__.py"]
        
        assert len(python_files) > 0, "Should have at least one pipeline file"
        
        for py_file in python_files:
            content = py_file.read_text()
            assert len(content.strip()) > 0, f"{py_file.name} should not be empty"
    
    def test_pipelines_have_main_or_class(self, pipelines_dir):
        """Verify pipeline files have main function or class definition"""
        python_files = list(pipelines_dir.glob("*.py"))
        python_files = [f for f in python_files if f.name != "__init__.py" and f.name != "README.md"]
        
        for py_file in python_files:
            content = py_file.read_text()
            
            # Check if file has either main() function, class definition, or other common patterns
            has_main = "def main(" in content or "def main (" in content
            has_class = "class " in content
            has_if_name = 'if __name__ == "__main__"' in content
            has_pipeline_run = "def pipeline_run(" in content
            
            assert has_main or has_class or has_if_name or has_pipeline_run, \
                f"{py_file.name} should have main(), class, if __name__, or pipeline_run()"
