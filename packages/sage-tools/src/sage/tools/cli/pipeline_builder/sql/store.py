"""SQL-based pipeline definition system for SAGE."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..builder import PipelineBuilder


@dataclass
class OperatorNode:
    """Represents a single operator in the pipeline."""
    
    op_id: str
    op_type: str
    position: int
    config: Dict[str, Any]


@dataclass
class PipelineDefinition:
    """Complete pipeline definition from SQL storage."""
    
    pipeline_id: str
    name: str
    description: str
    mode: str
    operators: List[OperatorNode]
    edges: List[Tuple[str, str]]  # (from_op, to_op)


class SQLPipelineStore:
    """Manages pipeline definitions in SQLite database."""
    
    def __init__(self, db_path: Optional[str] = None):
        if db_path:
            self.db_path = Path(db_path)
        else:
            self.db_path = Path.home() / ".sage" / "pipelines.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()
    
    def _init_schema(self):
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
            CREATE TABLE IF NOT EXISTS pipeline (
                pipeline_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                mode TEXT CHECK (mode IN ('batch', 'streaming')) DEFAULT 'batch',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS operator (
                pipeline_id TEXT REFERENCES pipeline(pipeline_id) ON DELETE CASCADE,
                op_id TEXT NOT NULL,
                op_type TEXT NOT NULL,
                position INTEGER NOT NULL,
                config TEXT NOT NULL DEFAULT '{}',
                PRIMARY KEY (pipeline_id, op_id)
            );
            
            CREATE TABLE IF NOT EXISTS pipeline_edge (
                pipeline_id TEXT REFERENCES pipeline(pipeline_id) ON DELETE CASCADE,
                from_op TEXT NOT NULL,
                to_op TEXT NOT NULL,
                PRIMARY KEY (pipeline_id, from_op, to_op)
            );
            
            CREATE INDEX IF NOT EXISTS idx_operator_position 
            ON operator(pipeline_id, position);
            """)
    
    def store_pipeline(self, definition: PipelineDefinition) -> None:
        """Store a complete pipeline definition."""
        with sqlite3.connect(self.db_path) as conn:
            # Insert pipeline metadata
            conn.execute("""
                INSERT OR REPLACE INTO pipeline (pipeline_id, name, description, mode)
                VALUES (?, ?, ?, ?)
            """, (definition.pipeline_id, definition.name, definition.description, definition.mode))
            
            # Clear existing operators and edges
            conn.execute("DELETE FROM operator WHERE pipeline_id = ?", (definition.pipeline_id,))
            conn.execute("DELETE FROM pipeline_edge WHERE pipeline_id = ?", (definition.pipeline_id,))
            
            # Insert operators
            for op in definition.operators:
                conn.execute("""
                    INSERT INTO operator (pipeline_id, op_id, op_type, position, config)
                    VALUES (?, ?, ?, ?, ?)
                """, (definition.pipeline_id, op.op_id, op.op_type, op.position, json.dumps(op.config)))
            
            # Insert edges
            for from_op, to_op in definition.edges:
                conn.execute("""
                    INSERT INTO pipeline_edge (pipeline_id, from_op, to_op)
                    VALUES (?, ?, ?)
                """, (definition.pipeline_id, from_op, to_op))
    
    def load_pipeline(self, pipeline_id: str) -> Optional[PipelineDefinition]:
        """Load a complete pipeline definition."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Load pipeline metadata
            pipeline_row = conn.execute("""
                SELECT * FROM pipeline WHERE pipeline_id = ?
            """, (pipeline_id,)).fetchone()
            
            if not pipeline_row:
                return None
            
            # Load operators
            operator_rows = conn.execute("""
                SELECT * FROM operator WHERE pipeline_id = ? ORDER BY position
            """, (pipeline_id,)).fetchall()
            
            operators = []
            for row in operator_rows:
                operators.append(OperatorNode(
                    op_id=row['op_id'],
                    op_type=row['op_type'],
                    position=row['position'],
                    config=json.loads(row['config'])
                ))
            
            # Load edges
            edge_rows = conn.execute("""
                SELECT from_op, to_op FROM pipeline_edge WHERE pipeline_id = ?
            """, (pipeline_id,)).fetchall()
            
            edges = [(row['from_op'], row['to_op']) for row in edge_rows]
            
            return PipelineDefinition(
                pipeline_id=pipeline_row['pipeline_id'],
                name=pipeline_row['name'],
                description=pipeline_row['description'],
                mode=pipeline_row['mode'],
                operators=operators,
                edges=edges
            )
    
    def list_pipelines(self) -> List[PipelineDefinition]:
        """List all stored pipelines with basic information."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT pipeline_id, name, description, mode FROM pipeline ORDER BY name
            """).fetchall()
            
            pipelines = []
            for row in rows:
                pipelines.append(PipelineDefinition(
                    pipeline_id=row['pipeline_id'],
                    name=row['name'],
                    description=row['description'],
                    mode=row['mode'],
                    operators=[],  # Load operators separately if needed
                    edges=[]       # Load edges separately if needed
                ))
            return pipelines
    
    def delete_pipeline(self, pipeline_id: str) -> bool:
        """Delete a pipeline and all its components."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                DELETE FROM pipeline WHERE pipeline_id = ?
            """, (pipeline_id,))
            return cursor.rowcount > 0


class SQLPipelineCompiler:
    """Compiles SQL pipeline definitions to SAGE YAML configs and Python runners."""
    
    def __init__(self, store: Optional[SQLPipelineStore] = None):
        self.store = store
        self.builder = PipelineBuilder()
    
    def compile_to_config(self, definition: PipelineDefinition) -> Dict[str, Any]:
        """Compile pipeline definition to SAGE config format."""
        config = {
            "pipeline": {
                "name": definition.name,
                "description": definition.description,
                "version": "1.0.0",
                "type": "local",
                "mode": definition.mode,
            }
        }
        
        # Add operator configs
        for op in definition.operators:
            # Map common operator types to config sections
            section_name = self._get_config_section(op.op_type)
            if section_name:
                config[section_name] = op.config
        
        return config
    
    def compile_to_yaml(self, definition: PipelineDefinition) -> str:
        """Generate YAML configuration for the pipeline."""
        config = self.compile_to_config(definition)
        import yaml
        return yaml.dump(config, default_flow_style=False)
    
    def compile_to_python(self, definition: PipelineDefinition) -> str:
        """Generate Python runner code for the pipeline."""
        
        # Build operator chain
        operators_by_id = {op.op_id: op for op in definition.operators}
        chain_parts = []
        
        # Find source operator (no incoming edges)
        incoming = {to_op for _, to_op in definition.edges}
        source_ops = [op for op in definition.operators if op.op_id not in incoming]
        
        if not source_ops:
            raise ValueError("No source operator found")
        
        current_op = source_ops[0]  # Start with first source
        chain_parts.append(f"env.from_source({current_op.op_type}, config[\"{self._get_config_section(current_op.op_type)}\"])")
        
        # Follow the chain
        visited = {current_op.op_id}
        while True:
            # Find next operator
            next_ops = [to_op for from_op, to_op in definition.edges if from_op == current_op.op_id]
            if not next_ops:
                break
            
            next_op_id = next_ops[0]  # Take first (assuming linear chain for now)
            if next_op_id in visited:
                break
            
            next_op = operators_by_id[next_op_id]
            visited.add(next_op_id)
            
            if next_op.op_type.endswith('Sink'):
                chain_parts.append(f".sink({next_op.op_type}, config[\"{self._get_config_section(next_op.op_type)}\"])")
            else:
                chain_parts.append(f".map({next_op.op_type}, config[\"{self._get_config_section(next_op.op_type)}\"])")
            
            current_op = next_op
        
        # Generate complete Python code
        imports = self._generate_imports(definition.operators)
        pipeline_chain = "\n        ".join(["("] + [f"    {part}" for part in chain_parts] + [")"])
        
        code = f'''"""Auto-generated SAGE pipeline from SQL definition.

Pipeline: {definition.name}
Description: {definition.description}
Mode: {definition.mode}
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Tuple

from sage.common.utils.config.loader import load_config
from sage.core.api.local_environment import LocalEnvironment
{imports}


def build_pipeline(config: dict) -> Tuple[LocalEnvironment, object]:
    """Create the streaming pipeline for the provided configuration."""
    
    env = LocalEnvironment(config["pipeline"]["name"])
    
    query_stream = {pipeline_chain}
    
    return env, query_stream


def run_pipeline(config_path: Path, *, streaming: bool = False) -> None:
    """Load configuration and execute the pipeline."""
    
    config = load_config(str(config_path))
    env, _ = build_pipeline(config)
    
    try:
        env.submit()
        if streaming or config["pipeline"].get("mode") == "streaming":
            env.run_streaming()
        else:
            env.run_once()
    finally:
        env.stop()
        env.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the generated SAGE pipeline")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path(__file__).with_name("pipeline_config.yaml"),
        help="Path to the pipeline configuration file.",
    )
    parser.add_argument(
        "--streaming",
        action="store_true",
        help="Force streaming mode regardless of config.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging output for debugging.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.verbose:
        logging.basicConfig(level=logging.INFO)
    
    logging.getLogger(__name__).info("Starting pipeline: %s", args.config)
    run_pipeline(args.config, streaming=args.streaming)


if __name__ == "__main__":
    main()
'''
        return code
    
    def _get_config_section(self, op_type: str) -> str:
        """Map operator type to config section name."""
        type_mapping = {
            'FileSource': 'source',
            'ChromaRetriever': 'retriever',
            'DenseRetriever': 'retriever',
            'QAPromptor': 'promptor',
            'OpenAIGenerator': 'generator',
            'HFGenerator': 'generator',
            'TerminalSink': 'sink',
            'FileSink': 'sink',
        }
        return type_mapping.get(op_type, op_type.lower())
    
    def _generate_imports(self, operators: List[OperatorNode]) -> str:
        """Generate import statements for the operators."""
        import_map = {
            'FileSource': 'from sage.libs.io_utils.source import FileSource',
            'ChromaRetriever': 'from sage.libs.rag.retriever import ChromaRetriever',
            'DenseRetriever': 'from sage.libs.rag.retriever import DenseRetriever',
            'QAPromptor': 'from sage.libs.rag.promptor import QAPromptor',
            'OpenAIGenerator': 'from sage.libs.rag.generator import OpenAIGenerator',
            'HFGenerator': 'from sage.libs.rag.generator import HFGenerator',
            'TerminalSink': 'from sage.libs.io_utils.sink import TerminalSink',
            'FileSink': 'from sage.libs.io_utils.sink import FileSink',
        }
        
        imports = set()
        for op in operators:
            if op.op_type in import_map:
                imports.add(import_map[op.op_type])
        
        return '\n'.join(sorted(imports))


__all__ = [
    "OperatorNode",
    "PipelineDefinition", 
    "SQLPipelineStore",
    "SQLPipelineCompiler",
]