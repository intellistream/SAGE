"""SQL DSL parser for SAGE pipeline definitions."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from .store import OperatorNode, PipelineDefinition


class SQLPipelineDSLParser:
    """Parses SAGE-specific SQL DSL into pipeline definitions."""
    
    def __init__(self):
        self.current_pipeline_id: Optional[str] = None
    
    def parse_statements(self, sql_content: str) -> List[PipelineDefinition]:
        """Parse multiple SQL statements and return pipeline definitions."""
        statements = self._split_statements(sql_content)
        pipelines: Dict[str, PipelineDefinition] = {}
        
        for stmt in statements:
            stmt = stmt.strip()
            if not stmt:
                continue
                
            if stmt.upper().startswith('CREATE PIPELINE'):
                pipeline = self._parse_create_pipeline(stmt)
                pipelines[pipeline.pipeline_id] = pipeline
            elif stmt.upper().startswith('INSERT INTO PIPELINE_EDGE'):
                self._parse_insert_edges(stmt, pipelines)
            elif stmt.upper().startswith('INSERT INTO OPERATOR'):
                self._parse_insert_operators(stmt, pipelines)
            elif stmt.upper().startswith('INSERT INTO PIPELINE'):
                self._parse_insert_pipeline(stmt, pipelines)
        
        return list(pipelines.values())
    
    def _split_statements(self, sql_content: str) -> List[str]:
        """Split SQL content into individual statements."""
        # Simple statement splitting on semicolon (not handling strings properly yet)
        statements = []
        current = []
        
        for line in sql_content.split('\n'):
            line = line.strip()
            if not line or line.startswith('--'):
                continue
            
            current.append(line)
            if line.endswith(';'):
                statements.append(' '.join(current))
                current = []
        
        if current:
            statements.append(' '.join(current))
        
        return statements
    
    def _parse_create_pipeline(self, stmt: str) -> PipelineDefinition:
        """Parse CREATE PIPELINE statement with embedded operator definitions."""
        # Example: CREATE PIPELINE rag_qa (
        #   source = FileSource { data_path: "data/questions.txt" },
        #   retriever = ChromaRetriever { top_k: 5 },
        #   promptor -> generator -> sink
        # );
        
        # Extract pipeline name
        name_match = re.search(r'CREATE PIPELINE\s+(\w+)', stmt, re.IGNORECASE)
        if not name_match:
            raise ValueError("Invalid CREATE PIPELINE syntax")
        
        pipeline_id = name_match.group(1)
        
        # Extract content between parentheses
        content_match = re.search(r'\((.*)\)', stmt, re.DOTALL)
        if not content_match:
            raise ValueError("No operator definitions found")
        
        content = content_match.group(1).strip()
        
        operators = []
        edges = []
        position = 1
        
        # Parse operator definitions and connections
        # First, split into logical sections (handle multi-line definitions)
        sections = []
        current_section = ""
        paren_depth = 0
        
        for char in content:
            if char == '{':
                paren_depth += 1
            elif char == '}':
                paren_depth -= 1
            
            current_section += char
            
            if char == ',' and paren_depth == 0:
                sections.append(current_section[:-1].strip())  # Remove trailing comma
                current_section = ""
        
        if current_section.strip():
            sections.append(current_section.strip())
        
        # Process each section
        for section in sections:
            section = section.strip()
            if not section:
                continue
                
            if '->' in section:
                # This is a connection line: promptor -> generator -> sink
                ops = [op.strip() for op in section.split('->')]
                for i in range(len(ops) - 1):
                    edges.append((ops[i], ops[i + 1]))
            else:
                # This is an operator definition: source = FileSource { config }
                op_match = re.match(r'(\w+)\s*=\s*(\w+)\s*\{\s*([^}]*)\s*\}', section)
                if op_match:
                    op_id, op_type, config_str = op_match.groups()
                    config = self._parse_config_block(config_str)
                    operators.append(OperatorNode(op_id, op_type, position, config))
                    position += 1
                else:
                    # Simple operator without config: sink
                    simple_match = re.match(r'(\w+)$', section)
                    if simple_match:
                        op_id = simple_match.group(1)
                        # Guess operator type from common patterns
                        op_type = self._guess_operator_type(op_id)
                        operators.append(OperatorNode(op_id, op_type, position, {}))
                        position += 1
        
        return PipelineDefinition(
            pipeline_id=pipeline_id,
            name=pipeline_id.replace('_', ' ').title(),
            description=f"Pipeline {pipeline_id} created from SQL DSL",
            mode="batch",
            operators=operators,
            edges=edges
        )
    
    def _parse_insert_pipeline(self, stmt: str, pipelines: Dict[str, PipelineDefinition]) -> None:
        """Parse INSERT INTO pipeline VALUES statement."""
        # Example: INSERT INTO pipeline VALUES ('rag_qa', 'Docs QA', 'Dense retrieval + LLM', 'batch');
        values_match = re.search(r"VALUES\s*\(\s*'([^']+)',\s*'([^']+)',\s*'([^']+)',\s*'([^']+)'\s*\)", stmt)
        if values_match:
            pipeline_id, name, description, mode = values_match.groups()
            pipelines[pipeline_id] = PipelineDefinition(
                pipeline_id=pipeline_id,
                name=name,
                description=description,
                mode=mode,
                operators=[],
                edges=[]
            )
    
    def _parse_insert_operators(self, stmt: str, pipelines: Dict[str, PipelineDefinition]) -> None:
        """Parse INSERT INTO operator VALUES statement."""
        # Example: INSERT INTO operator VALUES
        #   ('rag_qa', 'source', 'FileSource', 1, '{"data_path": "data/questions.txt"}'),
        #   ('rag_qa', 'retriever', 'ChromaRetriever', 2, '{"top_k": 5}');
        
        values_pattern = r"\(\s*'([^']+)',\s*'([^']+)',\s*'([^']+)',\s*(\d+),\s*'([^']+)'\s*\)"
        matches = re.findall(values_pattern, stmt, re.DOTALL)
        
        for pipeline_id, op_id, op_type, position_str, config_json in matches:
            if pipeline_id in pipelines:
                import json
                try:
                    config = json.loads(config_json)
                except json.JSONDecodeError:
                    config = {}
                
                operator = OperatorNode(op_id, op_type, int(position_str), config)
                pipelines[pipeline_id].operators.append(operator)
    
    def _parse_insert_edges(self, stmt: str, pipelines: Dict[str, PipelineDefinition]) -> None:
        """Parse INSERT INTO pipeline_edge VALUES statement."""
        # Example: INSERT INTO pipeline_edge VALUES
        #   ('rag_qa', 'source', 'retriever'),
        #   ('rag_qa', 'retriever', 'promptor');
        
        values_pattern = r"\(\s*'([^']+)',\s*'([^']+)',\s*'([^']+)'\s*\)"
        matches = re.findall(values_pattern, stmt, re.DOTALL)
        
        for pipeline_id, from_op, to_op in matches:
            if pipeline_id in pipelines:
                pipelines[pipeline_id].edges.append((from_op, to_op))
    
    def _parse_config_block(self, config_str: str) -> Dict[str, Any]:
        """Parse configuration block like: data_path: "file.txt", top_k: 5"""
        config = {}
        
        # Simple parsing of key: value pairs
        pairs = [pair.strip() for pair in config_str.split(',') if pair.strip()]
        
        for pair in pairs:
            if ':' in pair:
                key, value = pair.split(':', 1)
                key = key.strip()
                value = value.strip()
                
                # Parse value type
                if value.startswith('"') and value.endswith('"'):
                    config[key] = value[1:-1]  # Remove quotes
                elif value.startswith("'") and value.endswith("'"):
                    config[key] = value[1:-1]  # Remove quotes
                elif value.lower() in ('true', 'false'):
                    config[key] = value.lower() == 'true'
                elif value.isdigit():
                    config[key] = int(value)
                elif '.' in value and value.replace('.', '').isdigit():
                    config[key] = float(value)
                else:
                    config[key] = value
        
        return config
    
    def _guess_operator_type(self, op_id: str) -> str:
        """Guess operator type from operator ID."""
        type_mapping = {
            'source': 'FileSource',
            'retriever': 'ChromaRetriever',
            'promptor': 'QAPromptor',
            'generator': 'OpenAIGenerator',
            'sink': 'TerminalSink',
        }
        return type_mapping.get(op_id, f"{op_id.title()}Operator")


__all__ = ["SQLPipelineDSLParser"]