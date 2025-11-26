#!/usr/bin/env python3
"""
Data Preparation Script for Task Planning (Challenge 2)

Generates synthetic task_planning dataset for evaluating multi-step planning capabilities.
Each sample contains:
- sample_id: Unique identifier
- instruction: User task description
- context: Additional context (optional)
- available_tools: List of candidate tools
- ground_truth_steps: Expected plan steps with dependencies

Default output: .sage/benchmark/data/task_planning/

Usage:
    python prepare_planning_data.py
    python prepare_planning_data.py --output /path/to/data --num_samples 300
"""

import argparse
import json
import random
from pathlib import Path
from typing import Any

# Setup paths
SCRIPT_DIR = Path(__file__).resolve().parent
BENCHMARK_AGENT_DIR = SCRIPT_DIR.parent.parent
BENCHMARK_ROOT = BENCHMARK_AGENT_DIR.parent.parent.parent  # sage-benchmark
SAGE_ROOT = BENCHMARK_ROOT.parent.parent  # SAGE repo root

# Default output in .sage/
DEFAULT_OUTPUT_DIR = SAGE_ROOT / ".sage" / "benchmark" / "data" / "task_planning"

# Tool definitions for planning tasks
TOOL_DEFINITIONS = {
    # File operations
    "file_read": {
        "name": "file_read",
        "description": "Read contents from a file",
        "category": "file_operations",
        "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}},
    },
    "file_write": {
        "name": "file_write",
        "description": "Write contents to a file",
        "category": "file_operations",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
        },
    },
    "file_delete": {
        "name": "file_delete",
        "description": "Delete a file",
        "category": "file_operations",
        "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}},
    },
    "file_list": {
        "name": "file_list",
        "description": "List files in a directory",
        "category": "file_operations",
        "input_schema": {"type": "object", "properties": {"directory": {"type": "string"}}},
    },
    "file_copy": {
        "name": "file_copy",
        "description": "Copy a file to another location",
        "category": "file_operations",
        "input_schema": {
            "type": "object",
            "properties": {"source": {"type": "string"}, "destination": {"type": "string"}},
        },
    },
    # Data processing
    "data_parse_json": {
        "name": "data_parse_json",
        "description": "Parse JSON data",
        "category": "data_processing",
        "input_schema": {"type": "object", "properties": {"json_string": {"type": "string"}}},
    },
    "data_transform": {
        "name": "data_transform",
        "description": "Transform data according to a template",
        "category": "data_processing",
        "input_schema": {
            "type": "object",
            "properties": {"data": {"type": "object"}, "template": {"type": "string"}},
        },
    },
    "data_filter": {
        "name": "data_filter",
        "description": "Filter data based on conditions",
        "category": "data_processing",
        "input_schema": {
            "type": "object",
            "properties": {"data": {"type": "array"}, "condition": {"type": "string"}},
        },
    },
    "data_aggregate": {
        "name": "data_aggregate",
        "description": "Aggregate data with specified operation",
        "category": "data_processing",
        "input_schema": {
            "type": "object",
            "properties": {"data": {"type": "array"}, "operation": {"type": "string"}},
        },
    },
    "data_validate": {
        "name": "data_validate",
        "description": "Validate data against schema",
        "category": "data_processing",
        "input_schema": {
            "type": "object",
            "properties": {"data": {"type": "object"}, "schema": {"type": "object"}},
        },
    },
    # Web/API operations
    "http_get": {
        "name": "http_get",
        "description": "Make HTTP GET request",
        "category": "web_operations",
        "input_schema": {
            "type": "object",
            "properties": {"url": {"type": "string"}, "headers": {"type": "object"}},
        },
    },
    "http_post": {
        "name": "http_post",
        "description": "Make HTTP POST request",
        "category": "web_operations",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string"},
                "data": {"type": "object"},
                "headers": {"type": "object"},
            },
        },
    },
    "api_authenticate": {
        "name": "api_authenticate",
        "description": "Authenticate with an API",
        "category": "web_operations",
        "input_schema": {
            "type": "object",
            "properties": {"endpoint": {"type": "string"}, "credentials": {"type": "object"}},
        },
    },
    "web_scrape": {
        "name": "web_scrape",
        "description": "Scrape content from a web page",
        "category": "web_operations",
        "input_schema": {
            "type": "object",
            "properties": {"url": {"type": "string"}, "selector": {"type": "string"}},
        },
    },
    # Database operations
    "db_query": {
        "name": "db_query",
        "description": "Execute database query",
        "category": "database",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}, "params": {"type": "array"}},
        },
    },
    "db_insert": {
        "name": "db_insert",
        "description": "Insert record into database",
        "category": "database",
        "input_schema": {
            "type": "object",
            "properties": {"table": {"type": "string"}, "data": {"type": "object"}},
        },
    },
    "db_update": {
        "name": "db_update",
        "description": "Update records in database",
        "category": "database",
        "input_schema": {
            "type": "object",
            "properties": {
                "table": {"type": "string"},
                "data": {"type": "object"},
                "condition": {"type": "string"},
            },
        },
    },
    "db_delete": {
        "name": "db_delete",
        "description": "Delete records from database",
        "category": "database",
        "input_schema": {
            "type": "object",
            "properties": {"table": {"type": "string"}, "condition": {"type": "string"}},
        },
    },
    "db_connect": {
        "name": "db_connect",
        "description": "Connect to a database",
        "category": "database",
        "input_schema": {
            "type": "object",
            "properties": {"connection_string": {"type": "string"}},
        },
    },
    # Notification/Communication
    "email_send": {
        "name": "email_send",
        "description": "Send an email",
        "category": "communication",
        "input_schema": {
            "type": "object",
            "properties": {
                "to": {"type": "string"},
                "subject": {"type": "string"},
                "body": {"type": "string"},
            },
        },
    },
    "notification_send": {
        "name": "notification_send",
        "description": "Send a notification",
        "category": "communication",
        "input_schema": {
            "type": "object",
            "properties": {"channel": {"type": "string"}, "message": {"type": "string"}},
        },
    },
    "slack_post": {
        "name": "slack_post",
        "description": "Post message to Slack channel",
        "category": "communication",
        "input_schema": {
            "type": "object",
            "properties": {"channel": {"type": "string"}, "message": {"type": "string"}},
        },
    },
    # Analysis/Computation
    "text_analyze": {
        "name": "text_analyze",
        "description": "Analyze text content",
        "category": "analysis",
        "input_schema": {"type": "object", "properties": {"text": {"type": "string"}}},
    },
    "math_calculate": {
        "name": "math_calculate",
        "description": "Perform mathematical calculations",
        "category": "analysis",
        "input_schema": {"type": "object", "properties": {"expression": {"type": "string"}}},
    },
    "stats_compute": {
        "name": "stats_compute",
        "description": "Compute statistics on data",
        "category": "analysis",
        "input_schema": {
            "type": "object",
            "properties": {"data": {"type": "array"}, "metrics": {"type": "array"}},
        },
    },
    "sentiment_analyze": {
        "name": "sentiment_analyze",
        "description": "Analyze sentiment of text",
        "category": "analysis",
        "input_schema": {"type": "object", "properties": {"text": {"type": "string"}}},
    },
    # Format/Conversion
    "format_json": {
        "name": "format_json",
        "description": "Format data as JSON",
        "category": "format",
        "input_schema": {"type": "object", "properties": {"data": {"type": "object"}}},
    },
    "format_csv": {
        "name": "format_csv",
        "description": "Format data as CSV",
        "category": "format",
        "input_schema": {"type": "object", "properties": {"data": {"type": "array"}}},
    },
    "format_html": {
        "name": "format_html",
        "description": "Format data as HTML",
        "category": "format",
        "input_schema": {
            "type": "object",
            "properties": {"data": {"type": "object"}, "template": {"type": "string"}},
        },
    },
    "convert_units": {
        "name": "convert_units",
        "description": "Convert between units",
        "category": "format",
        "input_schema": {
            "type": "object",
            "properties": {
                "value": {"type": "number"},
                "from_unit": {"type": "string"},
                "to_unit": {"type": "string"},
            },
        },
    },
    # Code/Script operations
    "code_execute": {
        "name": "code_execute",
        "description": "Execute code snippet",
        "category": "code",
        "input_schema": {
            "type": "object",
            "properties": {"code": {"type": "string"}, "language": {"type": "string"}},
        },
    },
    "code_lint": {
        "name": "code_lint",
        "description": "Lint code for errors",
        "category": "code",
        "input_schema": {
            "type": "object",
            "properties": {"code": {"type": "string"}, "language": {"type": "string"}},
        },
    },
    "code_format": {
        "name": "code_format",
        "description": "Format code",
        "category": "code",
        "input_schema": {
            "type": "object",
            "properties": {"code": {"type": "string"}, "language": {"type": "string"}},
        },
    },
    # Search operations
    "search_web": {
        "name": "search_web",
        "description": "Search the web",
        "category": "search",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}, "num_results": {"type": "integer"}},
        },
    },
    "search_documents": {
        "name": "search_documents",
        "description": "Search through documents",
        "category": "search",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}, "filters": {"type": "object"}},
        },
    },
    "search_database": {
        "name": "search_database",
        "description": "Search database records",
        "category": "search",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}, "table": {"type": "string"}},
        },
    },
    # Image operations
    "image_resize": {
        "name": "image_resize",
        "description": "Resize an image",
        "category": "image",
        "input_schema": {
            "type": "object",
            "properties": {
                "image_path": {"type": "string"},
                "width": {"type": "integer"},
                "height": {"type": "integer"},
            },
        },
    },
    "image_convert": {
        "name": "image_convert",
        "description": "Convert image format",
        "category": "image",
        "input_schema": {
            "type": "object",
            "properties": {"image_path": {"type": "string"}, "output_format": {"type": "string"}},
        },
    },
    # Scheduling
    "schedule_task": {
        "name": "schedule_task",
        "description": "Schedule a task for later execution",
        "category": "scheduling",
        "input_schema": {
            "type": "object",
            "properties": {
                "task": {"type": "string"},
                "schedule": {"type": "string"},
                "params": {"type": "object"},
            },
        },
    },
    "get_calendar": {
        "name": "get_calendar",
        "description": "Get calendar events",
        "category": "scheduling",
        "input_schema": {
            "type": "object",
            "properties": {"start_date": {"type": "string"}, "end_date": {"type": "string"}},
        },
    },
    # Cache operations
    "cache_get": {
        "name": "cache_get",
        "description": "Get value from cache",
        "category": "cache",
        "input_schema": {"type": "object", "properties": {"key": {"type": "string"}}},
    },
    "cache_set": {
        "name": "cache_set",
        "description": "Set value in cache",
        "category": "cache",
        "input_schema": {
            "type": "object",
            "properties": {
                "key": {"type": "string"},
                "value": {"type": "object"},
                "ttl": {"type": "integer"},
            },
        },
    },
    # Logging/Monitoring
    "log_write": {
        "name": "log_write",
        "description": "Write to log",
        "category": "logging",
        "input_schema": {
            "type": "object",
            "properties": {"level": {"type": "string"}, "message": {"type": "string"}},
        },
    },
    "metrics_record": {
        "name": "metrics_record",
        "description": "Record a metric",
        "category": "logging",
        "input_schema": {
            "type": "object",
            "properties": {
                "metric_name": {"type": "string"},
                "value": {"type": "number"},
                "tags": {"type": "object"},
            },
        },
    },
}


# Task templates with varying complexity (5-10 steps)
TASK_TEMPLATES = [
    # 5-step tasks
    {
        "instruction": "Fetch user data from the API, validate the response format, extract relevant fields, save to a file, and send a notification",
        "steps": [
            {
                "step_id": 0,
                "description": "Authenticate with the API",
                "tool_id": "api_authenticate",
                "depends_on": [],
            },
            {
                "step_id": 1,
                "description": "Fetch user data from the API endpoint",
                "tool_id": "http_get",
                "depends_on": [0],
            },
            {
                "step_id": 2,
                "description": "Validate the response against schema",
                "tool_id": "data_validate",
                "depends_on": [1],
            },
            {
                "step_id": 3,
                "description": "Save data to a file",
                "tool_id": "file_write",
                "depends_on": [2],
            },
            {
                "step_id": 4,
                "description": "Send completion notification",
                "tool_id": "notification_send",
                "depends_on": [3],
            },
        ],
    },
    {
        "instruction": "Read a configuration file, parse the JSON content, connect to database, query records, and format results as CSV",
        "steps": [
            {
                "step_id": 0,
                "description": "Read configuration file",
                "tool_id": "file_read",
                "depends_on": [],
            },
            {
                "step_id": 1,
                "description": "Parse JSON configuration",
                "tool_id": "data_parse_json",
                "depends_on": [0],
            },
            {
                "step_id": 2,
                "description": "Connect to the database",
                "tool_id": "db_connect",
                "depends_on": [1],
            },
            {
                "step_id": 3,
                "description": "Query the database",
                "tool_id": "db_query",
                "depends_on": [2],
            },
            {
                "step_id": 4,
                "description": "Format results as CSV",
                "tool_id": "format_csv",
                "depends_on": [3],
            },
        ],
    },
    {
        "instruction": "Search the web for information, scrape the results, analyze the content, compute statistics, and save a report",
        "steps": [
            {
                "step_id": 0,
                "description": "Search the web for relevant information",
                "tool_id": "search_web",
                "depends_on": [],
            },
            {
                "step_id": 1,
                "description": "Scrape content from search results",
                "tool_id": "web_scrape",
                "depends_on": [0],
            },
            {
                "step_id": 2,
                "description": "Analyze scraped text content",
                "tool_id": "text_analyze",
                "depends_on": [1],
            },
            {
                "step_id": 3,
                "description": "Compute statistics on analysis",
                "tool_id": "stats_compute",
                "depends_on": [2],
            },
            {
                "step_id": 4,
                "description": "Save report to file",
                "tool_id": "file_write",
                "depends_on": [3],
            },
        ],
    },
    # 6-step tasks
    {
        "instruction": "Read data file, filter records, transform to new format, validate results, write to database, and log the operation",
        "steps": [
            {
                "step_id": 0,
                "description": "Read data from source file",
                "tool_id": "file_read",
                "depends_on": [],
            },
            {
                "step_id": 1,
                "description": "Parse the file content",
                "tool_id": "data_parse_json",
                "depends_on": [0],
            },
            {
                "step_id": 2,
                "description": "Filter records based on criteria",
                "tool_id": "data_filter",
                "depends_on": [1],
            },
            {
                "step_id": 3,
                "description": "Transform data to target format",
                "tool_id": "data_transform",
                "depends_on": [2],
            },
            {
                "step_id": 4,
                "description": "Insert transformed data to database",
                "tool_id": "db_insert",
                "depends_on": [3],
            },
            {
                "step_id": 5,
                "description": "Log the operation",
                "tool_id": "log_write",
                "depends_on": [4],
            },
        ],
    },
    {
        "instruction": "Authenticate API, fetch product data, analyze sentiment of reviews, aggregate scores, format as HTML report, and email the results",
        "steps": [
            {
                "step_id": 0,
                "description": "Authenticate with product API",
                "tool_id": "api_authenticate",
                "depends_on": [],
            },
            {
                "step_id": 1,
                "description": "Fetch product review data",
                "tool_id": "http_get",
                "depends_on": [0],
            },
            {
                "step_id": 2,
                "description": "Analyze sentiment of reviews",
                "tool_id": "sentiment_analyze",
                "depends_on": [1],
            },
            {
                "step_id": 3,
                "description": "Aggregate sentiment scores",
                "tool_id": "data_aggregate",
                "depends_on": [2],
            },
            {
                "step_id": 4,
                "description": "Format report as HTML",
                "tool_id": "format_html",
                "depends_on": [3],
            },
            {
                "step_id": 5,
                "description": "Email the report",
                "tool_id": "email_send",
                "depends_on": [4],
            },
        ],
    },
    # 7-step tasks
    {
        "instruction": "List files in directory, read each file, parse content, filter relevant data, aggregate results, format as JSON, and cache the output",
        "steps": [
            {
                "step_id": 0,
                "description": "List files in source directory",
                "tool_id": "file_list",
                "depends_on": [],
            },
            {
                "step_id": 1,
                "description": "Read file contents",
                "tool_id": "file_read",
                "depends_on": [0],
            },
            {
                "step_id": 2,
                "description": "Parse file content as JSON",
                "tool_id": "data_parse_json",
                "depends_on": [1],
            },
            {
                "step_id": 3,
                "description": "Filter relevant data fields",
                "tool_id": "data_filter",
                "depends_on": [2],
            },
            {
                "step_id": 4,
                "description": "Aggregate filtered data",
                "tool_id": "data_aggregate",
                "depends_on": [3],
            },
            {
                "step_id": 5,
                "description": "Format output as JSON",
                "tool_id": "format_json",
                "depends_on": [4],
            },
            {
                "step_id": 6,
                "description": "Cache the results",
                "tool_id": "cache_set",
                "depends_on": [5],
            },
        ],
    },
    {
        "instruction": "Connect to database, query customer records, filter by region, compute purchase statistics, generate report, save to file, and notify stakeholders",
        "steps": [
            {
                "step_id": 0,
                "description": "Connect to the database",
                "tool_id": "db_connect",
                "depends_on": [],
            },
            {
                "step_id": 1,
                "description": "Query customer records",
                "tool_id": "db_query",
                "depends_on": [0],
            },
            {
                "step_id": 2,
                "description": "Filter customers by region",
                "tool_id": "data_filter",
                "depends_on": [1],
            },
            {
                "step_id": 3,
                "description": "Compute purchase statistics",
                "tool_id": "stats_compute",
                "depends_on": [2],
            },
            {
                "step_id": 4,
                "description": "Format report as HTML",
                "tool_id": "format_html",
                "depends_on": [3],
            },
            {
                "step_id": 5,
                "description": "Save report to file",
                "tool_id": "file_write",
                "depends_on": [4],
            },
            {
                "step_id": 6,
                "description": "Post notification to Slack",
                "tool_id": "slack_post",
                "depends_on": [5],
            },
        ],
    },
    # 8-step tasks
    {
        "instruction": "Read config, authenticate API, fetch data, validate schema, transform format, filter records, save to database, record metrics, and send notification",
        "steps": [
            {
                "step_id": 0,
                "description": "Read configuration file",
                "tool_id": "file_read",
                "depends_on": [],
            },
            {
                "step_id": 1,
                "description": "Parse configuration JSON",
                "tool_id": "data_parse_json",
                "depends_on": [0],
            },
            {
                "step_id": 2,
                "description": "Authenticate with API",
                "tool_id": "api_authenticate",
                "depends_on": [1],
            },
            {
                "step_id": 3,
                "description": "Fetch data from API",
                "tool_id": "http_get",
                "depends_on": [2],
            },
            {
                "step_id": 4,
                "description": "Validate data against schema",
                "tool_id": "data_validate",
                "depends_on": [3],
            },
            {
                "step_id": 5,
                "description": "Transform data format",
                "tool_id": "data_transform",
                "depends_on": [4],
            },
            {
                "step_id": 6,
                "description": "Insert data into database",
                "tool_id": "db_insert",
                "depends_on": [5],
            },
            {
                "step_id": 7,
                "description": "Record pipeline metrics",
                "tool_id": "metrics_record",
                "depends_on": [6],
            },
        ],
    },
    # 9-step tasks
    {
        "instruction": "Search documents, read matching files, parse content, analyze text, extract entities, aggregate statistics, format results, save report, cache results, and send email",
        "steps": [
            {
                "step_id": 0,
                "description": "Search for relevant documents",
                "tool_id": "search_documents",
                "depends_on": [],
            },
            {
                "step_id": 1,
                "description": "Read matching document files",
                "tool_id": "file_read",
                "depends_on": [0],
            },
            {
                "step_id": 2,
                "description": "Parse document content",
                "tool_id": "data_parse_json",
                "depends_on": [1],
            },
            {
                "step_id": 3,
                "description": "Analyze document text",
                "tool_id": "text_analyze",
                "depends_on": [2],
            },
            {
                "step_id": 4,
                "description": "Analyze sentiment",
                "tool_id": "sentiment_analyze",
                "depends_on": [3],
            },
            {
                "step_id": 5,
                "description": "Compute statistics",
                "tool_id": "stats_compute",
                "depends_on": [4],
            },
            {
                "step_id": 6,
                "description": "Format results as HTML",
                "tool_id": "format_html",
                "depends_on": [5],
            },
            {
                "step_id": 7,
                "description": "Save report to file",
                "tool_id": "file_write",
                "depends_on": [6],
            },
            {
                "step_id": 8,
                "description": "Send email with report",
                "tool_id": "email_send",
                "depends_on": [7],
            },
        ],
    },
    # 10-step tasks
    {
        "instruction": "Connect DB, query users, fetch API data, validate both datasets, merge records, filter active users, compute metrics, format report, save file, update cache, and notify",
        "steps": [
            {
                "step_id": 0,
                "description": "Connect to database",
                "tool_id": "db_connect",
                "depends_on": [],
            },
            {
                "step_id": 1,
                "description": "Query user records",
                "tool_id": "db_query",
                "depends_on": [0],
            },
            {
                "step_id": 2,
                "description": "Authenticate with external API",
                "tool_id": "api_authenticate",
                "depends_on": [],
            },
            {
                "step_id": 3,
                "description": "Fetch external API data",
                "tool_id": "http_get",
                "depends_on": [2],
            },
            {
                "step_id": 4,
                "description": "Validate all data",
                "tool_id": "data_validate",
                "depends_on": [1, 3],
            },
            {
                "step_id": 5,
                "description": "Transform and merge data",
                "tool_id": "data_transform",
                "depends_on": [4],
            },
            {
                "step_id": 6,
                "description": "Filter active users",
                "tool_id": "data_filter",
                "depends_on": [5],
            },
            {
                "step_id": 7,
                "description": "Compute user metrics",
                "tool_id": "stats_compute",
                "depends_on": [6],
            },
            {
                "step_id": 8,
                "description": "Format as JSON report",
                "tool_id": "format_json",
                "depends_on": [7],
            },
            {
                "step_id": 9,
                "description": "Save and notify",
                "tool_id": "file_write",
                "depends_on": [8],
            },
        ],
    },
    # Additional variety templates
    {
        "instruction": "Download image from URL, resize to thumbnail, convert format to PNG, save to disk, update database record, and log the operation",
        "steps": [
            {
                "step_id": 0,
                "description": "Download image from URL",
                "tool_id": "http_get",
                "depends_on": [],
            },
            {
                "step_id": 1,
                "description": "Resize image to thumbnail",
                "tool_id": "image_resize",
                "depends_on": [0],
            },
            {
                "step_id": 2,
                "description": "Convert to PNG format",
                "tool_id": "image_convert",
                "depends_on": [1],
            },
            {
                "step_id": 3,
                "description": "Save image to disk",
                "tool_id": "file_write",
                "depends_on": [2],
            },
            {
                "step_id": 4,
                "description": "Update database record",
                "tool_id": "db_update",
                "depends_on": [3],
            },
            {
                "step_id": 5,
                "description": "Log the operation",
                "tool_id": "log_write",
                "depends_on": [4],
            },
        ],
    },
    {
        "instruction": "Check cache for data, if missing fetch from API, validate response, transform format, update cache with TTL, and return results",
        "steps": [
            {
                "step_id": 0,
                "description": "Check cache for existing data",
                "tool_id": "cache_get",
                "depends_on": [],
            },
            {
                "step_id": 1,
                "description": "Authenticate with API",
                "tool_id": "api_authenticate",
                "depends_on": [0],
            },
            {
                "step_id": 2,
                "description": "Fetch data from API",
                "tool_id": "http_get",
                "depends_on": [1],
            },
            {
                "step_id": 3,
                "description": "Validate API response",
                "tool_id": "data_validate",
                "depends_on": [2],
            },
            {
                "step_id": 4,
                "description": "Transform data format",
                "tool_id": "data_transform",
                "depends_on": [3],
            },
            {
                "step_id": 5,
                "description": "Update cache with TTL",
                "tool_id": "cache_set",
                "depends_on": [4],
            },
        ],
    },
    {
        "instruction": "Get calendar events, filter upcoming meetings, format as summary, calculate time conflicts, send reminder email",
        "steps": [
            {
                "step_id": 0,
                "description": "Get calendar events",
                "tool_id": "get_calendar",
                "depends_on": [],
            },
            {
                "step_id": 1,
                "description": "Filter upcoming meetings",
                "tool_id": "data_filter",
                "depends_on": [0],
            },
            {
                "step_id": 2,
                "description": "Format meeting summary",
                "tool_id": "format_html",
                "depends_on": [1],
            },
            {
                "step_id": 3,
                "description": "Calculate time conflicts",
                "tool_id": "math_calculate",
                "depends_on": [1],
            },
            {
                "step_id": 4,
                "description": "Send reminder email",
                "tool_id": "email_send",
                "depends_on": [2, 3],
            },
        ],
    },
    {
        "instruction": "Read source code file, lint for errors, format code, save formatted version, copy backup, and record metrics",
        "steps": [
            {
                "step_id": 0,
                "description": "Read source code file",
                "tool_id": "file_read",
                "depends_on": [],
            },
            {
                "step_id": 1,
                "description": "Copy file as backup",
                "tool_id": "file_copy",
                "depends_on": [0],
            },
            {
                "step_id": 2,
                "description": "Lint code for errors",
                "tool_id": "code_lint",
                "depends_on": [0],
            },
            {
                "step_id": 3,
                "description": "Format the code",
                "tool_id": "code_format",
                "depends_on": [2],
            },
            {
                "step_id": 4,
                "description": "Save formatted code",
                "tool_id": "file_write",
                "depends_on": [3],
            },
            {
                "step_id": 5,
                "description": "Record processing metrics",
                "tool_id": "metrics_record",
                "depends_on": [4],
            },
        ],
    },
    {
        "instruction": "Search database for orders, filter by date range, aggregate sales totals, convert currency units, format CSV report, save file, schedule follow-up task",
        "steps": [
            {
                "step_id": 0,
                "description": "Connect to database",
                "tool_id": "db_connect",
                "depends_on": [],
            },
            {
                "step_id": 1,
                "description": "Search for orders",
                "tool_id": "search_database",
                "depends_on": [0],
            },
            {
                "step_id": 2,
                "description": "Filter by date range",
                "tool_id": "data_filter",
                "depends_on": [1],
            },
            {
                "step_id": 3,
                "description": "Aggregate sales totals",
                "tool_id": "data_aggregate",
                "depends_on": [2],
            },
            {
                "step_id": 4,
                "description": "Convert currency units",
                "tool_id": "convert_units",
                "depends_on": [3],
            },
            {
                "step_id": 5,
                "description": "Format as CSV report",
                "tool_id": "format_csv",
                "depends_on": [4],
            },
            {
                "step_id": 6,
                "description": "Save report file",
                "tool_id": "file_write",
                "depends_on": [5],
            },
            {
                "step_id": 7,
                "description": "Schedule follow-up task",
                "tool_id": "schedule_task",
                "depends_on": [6],
            },
        ],
    },
]


def generate_variant(
    template: dict[str, Any], variant_id: int, all_tools: list[str]
) -> dict[str, Any]:
    """
    Generate a variant of a task template with slight modifications.

    Args:
        template: Base task template
        variant_id: Variant identifier
        all_tools: List of all available tool IDs

    Returns:
        Modified task sample
    """
    instruction = template["instruction"]
    steps = [step.copy() for step in template["steps"]]

    # Modify instruction slightly
    prefixes = [
        "Please ",
        "I need you to ",
        "Could you ",
        "Help me to ",
        "Execute the following: ",
        "Perform these operations: ",
        "Run this workflow: ",
    ]
    suffixes = [
        "",
        " efficiently",
        " as quickly as possible",
        " and report the results",
        " following best practices",
    ]

    modified_instruction = random.choice(prefixes) + instruction.lower() + random.choice(suffixes)

    # Get tools used in this task
    task_tools = [step["tool_id"] for step in steps]

    # Add some distractor tools
    unused_tools = [t for t in all_tools if t not in task_tools]
    num_distractors = random.randint(5, 15)
    distractor_tools = random.sample(unused_tools, min(num_distractors, len(unused_tools)))

    available_tools = task_tools + distractor_tools
    random.shuffle(available_tools)

    return {
        "sample_id": f"planning_{variant_id:04d}",
        "instruction": modified_instruction,
        "context": {
            "task_type": "multi_step_planning",
            "complexity": len(steps),
            "variant": variant_id,
        },
        "available_tools": available_tools,
        "ground_truth_steps": steps,
        "tool_sequence": task_tools,
    }


def generate_planning_dataset(num_samples: int, output_dir: Path, seed: int = 42) -> dict[str, Any]:
    """
    Generate the complete planning dataset.

    Args:
        num_samples: Total number of samples to generate
        output_dir: Output directory for data files
        seed: Random seed for reproducibility

    Returns:
        Statistics about generated data
    """
    random.seed(seed)
    output_dir.mkdir(parents=True, exist_ok=True)

    all_tools = list(TOOL_DEFINITIONS.keys())
    samples = []
    stats = {"total": 0, "by_steps": {}, "tools_used": set()}

    # Generate samples by cycling through templates
    for i in range(num_samples):
        template = TASK_TEMPLATES[i % len(TASK_TEMPLATES)]
        sample = generate_variant(template, i, all_tools)
        samples.append(sample)

        # Update stats
        num_steps = len(sample["ground_truth_steps"])
        stats["by_steps"][num_steps] = stats["by_steps"].get(num_steps, 0) + 1
        stats["tools_used"].update(sample["tool_sequence"])
        stats["total"] += 1

    # Shuffle samples
    random.shuffle(samples)

    # Split into train/dev/test (60/20/20)
    n = len(samples)
    train_end = int(n * 0.6)
    dev_end = int(n * 0.8)

    splits = {
        "train": samples[:train_end],
        "dev": samples[train_end:dev_end],
        "test": samples[dev_end:],
    }

    # Save each split
    for split_name, split_samples in splits.items():
        output_file = output_dir / f"{split_name}.jsonl"
        with open(output_file, "w", encoding="utf-8") as f:
            for sample in split_samples:
                f.write(json.dumps(sample, ensure_ascii=False) + "\n")
        print(f"Saved {len(split_samples)} samples to {output_file}")

    # Save tool definitions
    tools_file = output_dir / "tools.json"
    with open(tools_file, "w", encoding="utf-8") as f:
        json.dump(TOOL_DEFINITIONS, f, indent=2, ensure_ascii=False)
    print(f"Saved {len(TOOL_DEFINITIONS)} tool definitions to {tools_file}")

    # Save metadata
    stats["tools_used"] = list(stats["tools_used"])
    stats["splits"] = {k: len(v) for k, v in splits.items()}
    metadata_file = output_dir / "metadata.json"
    with open(metadata_file, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
    print(f"Saved metadata to {metadata_file}")

    return stats


def main():
    parser = argparse.ArgumentParser(description="Prepare task planning dataset")
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help=f"Output directory for data files (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--num_samples",
        type=int,
        default=300,
        help="Total number of samples to generate",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility",
    )

    args = parser.parse_args()

    # Use .sage/benchmark/ by default
    output_dir = Path(args.output) if args.output else DEFAULT_OUTPUT_DIR

    print(f"Generating {args.num_samples} planning samples...")
    print(f"Output directory: {output_dir}")

    stats = generate_planning_dataset(args.num_samples, output_dir, args.seed)

    print("\n" + "=" * 50)
    print("Dataset Generation Complete")
    print("=" * 50)
    print(f"Total samples: {stats['total']}")
    print(f"Splits: {stats['splits']}")
    print(f"Samples by step count: {stats['by_steps']}")
    print(f"Unique tools used: {len(stats['tools_used'])}")


if __name__ == "__main__":
    main()
