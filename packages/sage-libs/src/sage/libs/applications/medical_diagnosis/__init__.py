"""
Medical Diagnosis Application - Lumbar Spine MRI Analysis

A complete medical diagnosis system for analyzing lumbar spine MRI images
and generating diagnostic reports using multi-agent collaboration.

Quick Start:
    >>> from sage.libs.applications.medical_diagnosis import DiagnosticAgent
    >>>
    >>> agent = DiagnosticAgent()
    >>> result = agent.diagnose(
    ...     image_path="path/to/mri.jpg",
    ...     patient_info={"age": 45, "gender": "male", "symptoms": "back pain"}
    ... )
    >>> print(result.report)

Components:
    - DiagnosticAgent: Main coordinator agent
    - ImageAnalyzer: MRI image analysis agent
    - ReportGenerator: Diagnostic report generation agent
    - MedicalKnowledgeBase: Medical knowledge retrieval

For full documentation, see README.md in this directory.
"""

from .agents.diagnostic_agent import DiagnosisResult, DiagnosticAgent
from .agents.image_analyzer import ImageAnalyzer, ImageFeatures
from .agents.report_generator import DiagnosisReport, ReportGenerator
from .tools.knowledge_base import MedicalKnowledgeBase

__all__ = [
    # Main Agent
    "DiagnosticAgent",
    "DiagnosisResult",
    # Sub Agents
    "ImageAnalyzer",
    "ImageFeatures",
    "ReportGenerator",
    "DiagnosisReport",
    # Tools
    "MedicalKnowledgeBase",
]

__version__ = "1.0.0"
