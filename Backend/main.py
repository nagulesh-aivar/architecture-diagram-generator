"""
FastAPI Backend Server for Architecture Diagram Generator
Handles PDF upload, extraction, summarization, and diagram generation
"""

import sys
import shutil
import subprocess
import json
import re
import time
from pathlib import Path
from typing import Optional, Dict, List
import uuid
from datetime import datetime
import io

from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse, Response
import asyncio
from pydantic import BaseModel
import uvicorn
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

# Add parent directory to path to import pdf_extractor
sys.path.insert(0, str(Path(__file__).parent.parent))
from pdf_extractor import extract_pdf, summarize_with_bedrock

app = FastAPI(title="Architecture Diagram Generator API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create uploads directory if it doesn't exist
UPLOAD_DIR = Path(__file__).parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

# Create outputs directory for diagrams
OUTPUT_DIR = Path(__file__).parent / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

# S3 Configuration
S3_BUCKET_NAME = "architecture-diagrams-dump"
S3_REGION = "us-east-1"
S3_PREFIX = "diagrams/"

# Initialize S3 client
try:
    s3_client = boto3.client('s3', region_name=S3_REGION)
    print(f"S3 client initialized for bucket: {S3_BUCKET_NAME}")
except Exception as e:
    print(f"Warning: S3 client initialization failed: {e}")
    s3_client = None


class DiagramRequest(BaseModel):
    aws_region: Optional[str] = "us-east-1"
    bedrock_model_id: Optional[str] = "anthropic.claude-3-sonnet-20240229-v1:0"


def convert_markdown_to_readable_text(markdown_text: str) -> str:
    """
    Convert markdown-formatted summary text into plain, human-readable text
    suitable for diagram generation prompts.
    
    Args:
        markdown_text: Markdown-formatted text with headers, tables, code blocks, etc.
    
    Returns:
        Plain text description of the architecture
    """
    text = markdown_text
    
    # Remove code blocks but extract their content as descriptions
    code_block_pattern = r'```[\w]*\n(.*?)```'
    def replace_code_block(match):
        code_content = match.group(1).strip()
        # Convert code blocks to descriptive text
        if 'flowchart' in code_content.lower() or 'graph' in code_content.lower():
            return "The architecture follows a workflow pattern."
        elif '┌' in code_content or '│' in code_content:
            return "The system has a structured architecture layout."
        else:
            return f"The system includes: {code_content[:100]}"
    
    text = re.sub(code_block_pattern, replace_code_block, text, flags=re.DOTALL)
    
    # Convert markdown headers to plain text sections
    text = re.sub(r'^#{1,6}\s+(.+)$', r'\1:', text, flags=re.MULTILINE)
    
    # Convert markdown tables to readable text
    lines = text.split('\n')
    result_lines = []
    in_table = False
    table_headers = []
    table_rows = []
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Check if this is a table row
        if '|' in line and line.strip().startswith('|'):
            # Extract cells from table row
            cells = [cell.strip() for cell in line.split('|')[1:-1]]  # Remove first/last empty cells
            
            # Check if this is a separator row
            if all(cell.replace('-', '').replace(':', '').replace(' ', '') == '' for cell in cells):
                in_table = True
                i += 1
                continue
            
            if in_table:
                if not table_headers:
                    # First row after separator is headers
                    table_headers = cells
                else:
                    # Data row
                    table_rows.append(cells)
            else:
                # Start of a new table
                table_headers = cells
                in_table = True
            i += 1
            continue
        else:
            # Not a table row - process accumulated table data
            if in_table and table_headers:
                # Convert table to readable text
                for row in table_rows:
                    if len(row) == len(table_headers):
                        # Create readable pairs
                        pairs = []
                        for j in range(len(table_headers)):
                            if j < len(row) and row[j].strip():
                                pairs.append(f"{table_headers[j]}: {row[j]}")
                        if pairs:
                            result_lines.append(". ".join(pairs) + ".")
                    elif len(row) > 0:
                        # Just list the values
                        result_lines.append(". ".join([cell for cell in row if cell.strip()]) + ".")
                
                table_headers = []
                table_rows = []
                in_table = False
            
            result_lines.append(line)
            i += 1
    
    # Handle any remaining table data
    if in_table and table_headers:
        for row in table_rows:
            if len(row) == len(table_headers):
                pairs = []
                for j in range(len(table_headers)):
                    if j < len(row) and row[j].strip():
                        pairs.append(f"{table_headers[j]}: {row[j]}")
                if pairs:
                    result_lines.append(". ".join(pairs) + ".")
    
    text = '\n'.join(result_lines)
    
    # Remove markdown table separators
    text = re.sub(r'^\|[\s\-\|:]+\|$', '', text, flags=re.MULTILINE)
    
    # Remove markdown formatting but keep content
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)  # Bold
    text = re.sub(r'\*(.+?)\*', r'\1', text)  # Italic
    text = re.sub(r'`(.+?)`', r'\1', text)  # Inline code
    text = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', text)  # Links
    
    # Convert bullet points to sentences
    text = re.sub(r'^[\s]*[-*+]\s+(.+)$', r'\1.', text, flags=re.MULTILINE)
    
    # Convert numbered lists to sentences
    text = re.sub(r'^\d+\.\s+(.+)$', r'\1.', text, flags=re.MULTILINE)
    
    # Clean up multiple blank lines
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Remove ASCII art boxes
    text = re.sub(r'┌[─┐└┘│├┤┬┴┼]+┐', '', text)
    text = re.sub(r'└[─┐└┘│├┤┬┴┼]+┘', '', text)
    text = re.sub(r'│[^│\n]*│', '', text)
    text = re.sub(r'├[─┐└┘│├┤┬┴┼]+┤', '', text)
    
    # Clean up remaining markdown artifacts
    text = re.sub(r'^---+$', '', text, flags=re.MULTILINE)
    text = re.sub(r'^===+$', '', text, flags=re.MULTILINE)
    
    # Remove empty lines at start/end
    text = text.strip()
    
    # Ensure sentences end properly
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        line = line.strip()
        if not line:
            cleaned_lines.append('')
            continue
        
        # Add period if line doesn't end with punctuation and is not a header
        if not line.endswith(('.', ':', '!', '?', ';')) and not line.endswith(':'):
            line += '.'
        
        cleaned_lines.append(line)
    
    text = '\n'.join(cleaned_lines)
    
    # Final cleanup - remove excessive whitespace
    text = re.sub(r' +', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text.strip()


def find_uvx_command() -> Optional[str]:
    """Find uvx command in PATH or common installation locations."""
    # First try PATH
    uvx_path = shutil.which("uvx")
    if uvx_path:
        return uvx_path
    
    # Try common installation locations
    home = Path.home()
    common_paths = [
        home / ".local" / "bin" / "uvx",
        home / ".cargo" / "bin" / "uvx",
        Path("/usr/local/bin/uvx"),
        Path("/opt/homebrew/bin/uvx"),
    ]
    
    for path in common_paths:
        if path.exists() and path.is_file():
            return str(path)
    
    return None


def generate_diagram_with_strands(summary_text: str, output_path: Path, diagram_prompt: Optional[str] = None) -> Optional[str]:
    """
    Generate architecture diagram using strands and MCP (if available).
    Returns path to generated diagram image or None if failed.
    
    KNOWN LIMITATION: The AWS Diagram MCP Server (awslabs.aws-diagram-mcp-server) uses
    AWS standard diagram conventions which include colored fills:
    - Light green (#F2F6E8) for Public Subnets
    - Light cyan (#E6F6F7) for Private Subnets
    - Light blue tints for Availability Zones
    
    These defaults may be hardcoded in the MCP server and cannot be overridden via prompt.
    The prompt explicitly requests white backgrounds, but the tool may ignore these instructions
    due to its default behavior matching AWS official diagram standards.
    
    Potential workarounds:
    1. Post-process the generated PNG to remove colored fills
    2. Use a different diagram generation tool that supports fill color control
    3. Modify the MCP server configuration if it supports customization
    """
    # Find uvx command
    uvx_path = find_uvx_command()
    if not uvx_path:
        print("Diagram generation skipped: 'uvx' command not found. Install uv: https://astral.sh/uv")
        return None
    
    print(f"Using uvx at: {uvx_path}")
    
    try:
        # Import diagram generator components
        from dotenv import load_dotenv
        load_dotenv()
        
        from mcp import stdio_client, StdioServerParameters
        from strands import Agent
        from strands.tools.mcp import MCPClient
        
        # Create prompt for diagram generation - clean and concise
        absolute_output_path = output_path.resolve()
        
        # CRITICAL: Tell the MCP server the EXACT filename to use
        output_filename = output_path.name  # e.g., "20251223_162757_uuid_diagram.png"
        
        # Use provided prompt or generate default with detailed component structure
        if diagram_prompt:
            # Use custom prompt and replace placeholders with actual summary
            readable_summary = convert_markdown_to_readable_text(summary_text)
            final_prompt = diagram_prompt.replace('{readable_summary}', readable_summary).replace('{summary_text}', summary_text)
            # Add explicit layout and save instructions at the beginning AND end
            layout_prefix = """
=== CRITICAL LAYOUT REQUIREMENTS (READ FIRST) ===
ASPECT RATIO: 16:9 HORIZONTAL LANDSCAPE (width MUST be 1.78x height)
CANVAS SIZE: Minimum 3840 pixels WIDTH × 2160 pixels HEIGHT
ORIENTATION: HORIZONTAL (wider than tall) - NEVER VERTICAL
FLOW DIRECTION: LEFT → RIGHT (not top → bottom)
ARRANGEMENT: Components spread HORIZONTALLY across the width, grouped in 4-5 COLUMNS
RANKDIR: LR (Left-to-Right) if using Graphviz
LAYOUT: Use 'landscape' mode, horizontal orientation

"""
            layout_suffix = f"""

=== CRITICAL REMINDERS (ENFORCE THESE) ===
1. HORIZONTAL LANDSCAPE ONLY: Width MUST be greater than height
2. 16:9 ASPECT RATIO: 3840×2160 or 1920×1080 or any 16:9 ratio
3. LEFT-TO-RIGHT FLOW: Arrange components in horizontal columns, not vertical rows
4. GRAPHVIZ RANKDIR: If using DOT format, set rankdir=LR (left-to-right)
5. CANVAS ORIENTATION: landscape="true" or orientation="landscape"
6. NO VERTICAL STACKING: Spread components horizontally
7. Save to: {absolute_output_path}
8. Filename: {output_filename}
"""
            final_prompt = layout_prefix + final_prompt + layout_suffix
        else:
            # Generate detailed structured prompt with EXTREME emphasis on horizontal layout
            final_prompt = f"""
=== CRITICAL: HORIZONTAL LANDSCAPE LAYOUT (16:9) ===
YOU MUST CREATE A HORIZONTAL LANDSCAPE DIAGRAM.
- Canvas: 3840 pixels WIDE × 2160 pixels TALL (16:9 aspect ratio)
- Orientation: LANDSCAPE (wider than tall)
- Flow: LEFT-TO-RIGHT (not top-to-bottom)
- Graphviz rankdir: LR (if using DOT format)
- Layout mode: landscape="true"

Create a comprehensive AWS architecture diagram based on the following summary.

ARCHITECTURE SUMMARY:
{summary_text}

Extract all components from the summary and organize them into HORIZONTAL COLUMNS (not vertical rows):

HORIZONTAL COLUMN LAYOUT (LEFT → RIGHT):
┌─────────────┬─────────────┬─────────────┬─────────────┬─────────────┐
│  COLUMN 1   │  COLUMN 2   │  COLUMN 3   │  COLUMN 4   │  COLUMN 5   │
│  (LEFT)     │             │  (CENTER)   │             │  (RIGHT)    │
├─────────────┼─────────────┼─────────────┼─────────────┼─────────────┤
│ External    │ Ingestion & │ Processing  │ Storage &   │ Monitoring  │
│ Sources     │ Events      │ & Compute   │ Security    │ & External  │
│             │             │             │             │ Integration │
└─────────────┴─────────────┴─────────────┴─────────────┴─────────────┘

COLUMN 1 - EXTERNAL & INGESTION (LEFT, 20% width):
   - External users (Shippers/Carriers)
   - Data sources
   - Email ingestion (Amazon SES)
   - S3 Input Bucket

COLUMN 2 - EVENT TRIGGERS & ROUTING (LEFT-CENTER, 20% width):
   - S3 Event Notifications
   - Lambda Functions (triggers)
   - EventBridge Rules
   - SQS Queues
   - SNS Topics

COLUMN 3 - CORE PROCESSING (CENTER, 30% width):
   - Lambda Functions (processors)
   - EC2 Instances
   - ECS/EKS Services
   - SageMaker Jobs/Pipelines
   - Batch Jobs
   - AI/ML Services (Bedrock, Textract)

COLUMN 4 - DATA & SECURITY (RIGHT-CENTER, 20% width):
   - S3 Output Buckets
   - DynamoDB Tables
   - RDS Databases
   - ECR Repositories
   - KMS Keys
   - Secrets Manager
   - IAM Roles

COLUMN 5 - MONITORING & OUTPUT (RIGHT, 10% width):
   - CloudWatch Logs/Metrics
   - X-Ray Tracing
   - CloudTrail
   - External API Integration
   - Notifications

DATA FLOW (LEFT → RIGHT):
1. External sources → Ingestion (Column 1 → Column 2)
2. Ingestion → Event triggers (Column 2)
3. Events → Processing (Column 2 → Column 3)
4. Processing ↔ AI/ML services (within Column 3)
5. Processing → Storage (Column 3 → Column 4)
6. Storage → Monitoring (Column 4 → Column 5)
7. Processing → External APIs (Column 3 → Column 5)

STYLING REQUIREMENTS (CRITICAL):
- NO COLORS: Use black, white, and gray ONLY
- NO colored fills, NO colored backgrounds, NO colored borders
- Use official AWS service icons in GRAYSCALE/BLACK-WHITE
- White background for entire canvas
- Black or dark gray borders for containers
- Simple, clean, professional monochrome appearance

LAYOUT REQUIREMENTS (MANDATORY):
1. HORIZONTAL LANDSCAPE: Width MUST be greater than height
2. ASPECT RATIO: 16:9 (e.g., 3840×2160, 1920×1080)
3. FLOW DIRECTION: LEFT-TO-RIGHT across the width
4. COLUMN ARRANGEMENT: Components in 5 horizontal columns
5. NO VERTICAL STACKING: Arrange horizontally
6. GRAPHVIZ RANKDIR: LR (if using DOT/Graphviz)
7. CANVAS WIDTH: At least 3840 pixels
8. CANVAS HEIGHT: At most 2160 pixels (width should be ~1.78x height)

CONTAINER HIERARCHY (HORIZONTAL LAYOUT):
- AWS Cloud (outermost, full width 3840px)
- Region (inside AWS Cloud, ~3600px width)
- VPC (inside Region, ~3400px width)
- Availability Zones: Place SIDE-BY-SIDE horizontally, NOT stacked vertically

FORBIDDEN PATTERNS (DO NOT DO THIS):
❌ NO vertical top-to-bottom flow
❌ NO portrait orientation (taller than wide)
❌ NO stacking major components vertically
❌ NO colors (stay monochrome/grayscale)
❌ NO aspect ratio less than 16:9

OUTPUT SPECIFICATIONS:
- Format: PNG image
- Dimensions: 3840×2160 pixels (width × height)
- Resolution: 300 DPI
- Color: Grayscale/Black-White only
- Save to: {absolute_output_path}

=== FINAL REMINDER ===
The diagram MUST be HORIZONTAL LANDSCAPE (16:9 ratio).
Width MUST be ~1.78 times the height.
Components flow LEFT → RIGHT.
Use 'rankdir=LR' if generating Graphviz DOT format.
"""
        
        diagram_prompt = final_prompt

        # Initialize MCP client and agent
        # Suppress sarif module warnings by setting environment variable
        import os
        original_env = os.environ.copy()
        # Suppress Python warnings about missing optional modules
        os.environ['PYTHONWARNINGS'] = 'ignore::UserWarning'
        
        try:
            mcp_client = MCPClient(lambda: stdio_client(
            StdioServerParameters(
                command=uvx_path,
                args=["awslabs.aws-diagram-mcp-server"]
            )
            ))
        finally:
            # Restore original environment
            os.environ.clear()
            os.environ.update(original_env)
        
        with mcp_client:
            tools = mcp_client.list_tools_sync()
            # Try to print tool info safely
            try:
                tool_info = []
                for tool in tools:
                    if hasattr(tool, 'name'):
                        tool_info.append(tool.name)
                    elif hasattr(tool, '__name__'):
                        tool_info.append(tool.__name__)
                    else:
                        tool_info.append(str(type(tool).__name__))
                print(f"Available MCP tools ({len(tools)}): {tool_info}")
            except Exception as e:
                print(f"Available MCP tools: {len(tools)} tools loaded (couldn't list names: {e})")
            
            agent = Agent(tools=tools)
            
            # Generate diagram (stderr warnings from MCP server are suppressed via environment variable)
            print(f"Sending prompt to agent (length: {len(diagram_prompt)} chars)")
            response = agent(diagram_prompt)
            print(f"Agent response received: {str(response)[:500]}...")
            
            # Check if diagram was generated at the expected path
            if output_path.exists():
                print(f"Diagram found at expected path: {output_path}")
                return str(output_path)
            
            # Check for DOT files (Graphviz format) - the MCP server might generate these
            output_dir = output_path.parent
            # Check if we're already in generated-diagrams, or need to check it
            if output_dir.name == "generated-diagrams":
                generated_diagrams_dir = output_dir
                parent_output_dir = output_dir.parent
            else:
                generated_diagrams_dir = output_dir / "generated-diagrams"
                parent_output_dir = output_dir
            
            dot_files = []
            
            # Check output directory and generated-diagrams subdirectory
            search_dirs = [output_dir]
            if generated_diagrams_dir.exists() and generated_diagrams_dir != output_dir:
                search_dirs.append(generated_diagrams_dir)
            
            # Check parent directory (where files might be created)
            parent_dir = Path(__file__).parent.parent
            search_dirs.append(parent_dir)
            
            # Look for DOT files only (exclude Python files and other non-DOT files)
            for search_dir in search_dirs:
                for pattern in ["*.dot"]:
                    dot_files.extend([f for f in search_dir.glob(pattern) if f.is_file()])
            
            # Filter out Python files and the expected PNG path
            dot_files = [
                f for f in dot_files 
                if f != output_path 
                and f.suffix in ['.dot', '']  # Only DOT files or files without extension that might be DOT
                and f.suffix != '.py'  # Exclude Python files
                and not f.name.endswith('.py')  # Extra check for Python files
            ]
            
            if dot_files:
                # Find the most recently created DOT file
                latest_dot = max(dot_files, key=lambda p: p.stat().st_mtime)
                print(f"Found DOT file: {latest_dot}")
                
                # Post-process DOT file to force horizontal layout
                try:
                    with open(latest_dot, 'r') as f:
                        dot_content = f.read()
                    
                    # Force horizontal layout by modifying DOT attributes
                    modified = False
                    
                    # If rankdir is not set or is TB/BT, change to LR
                    if 'rankdir=' in dot_content:
                        if 'rankdir=TB' in dot_content or 'rankdir=BT' in dot_content or 'rankdir="TB"' in dot_content or 'rankdir="BT"' in dot_content:
                            dot_content = dot_content.replace('rankdir=TB', 'rankdir=LR')
                            dot_content = dot_content.replace('rankdir=BT', 'rankdir=LR')
                            dot_content = dot_content.replace('rankdir="TB"', 'rankdir="LR"')
                            dot_content = dot_content.replace('rankdir="BT"', 'rankdir="LR"')
                            modified = True
                            print("Modified rankdir from TB/BT to LR (horizontal)")
                    else:
                        # Add rankdir=LR if not present
                        # Insert after the opening digraph/graph line
                        lines = dot_content.split('\n')
                        for i, line in enumerate(lines):
                            if ('digraph' in line or 'graph' in line) and '{' in line:
                                lines.insert(i + 1, '  rankdir=LR;  // Force horizontal layout')
                                lines.insert(i + 2, '  size="38.4,21.6!";  // 16:9 aspect ratio in inches (300 DPI)')
                                lines.insert(i + 3, '  ratio="fill";')
                                dot_content = '\n'.join(lines)
                                modified = True
                                print("Added rankdir=LR and size constraints to DOT file")
                                break
                    
                    # Write back modified content
                    if modified:
                        with open(latest_dot, 'w') as f:
                            f.write(dot_content)
                        print(f"Modified DOT file to force horizontal layout: {latest_dot}")
                except Exception as e:
                    print(f"Warning: Could not modify DOT file for horizontal layout: {e}")
                
                # Try to convert DOT to PNG if Graphviz is available
                dot_path = shutil.which("dot")
                if dot_path:
                    try:
                        # Convert DOT to PNG with explicit size and ratio parameters
                        png_output = output_path
                        subprocess.run(
                            [dot_path, "-Tpng", "-Gsize=38.4,21.6!", "-Gratio=fill", "-Grankdir=LR", 
                             str(latest_dot), "-o", str(png_output)],
                            check=True,
                            capture_output=True,
                            timeout=30
                        )
                        if png_output.exists():
                            print(f"Converted DOT to PNG with horizontal layout: {png_output}")
                            return str(png_output)
                    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
                        print(f"Failed to convert DOT to PNG: {e}")
                
                # If conversion failed, check if we can return SVG or use the DOT file
                # For now, return None and let the API return the summary
                print("DOT file found but PNG conversion unavailable. Install Graphviz: brew install graphviz")
            
            # Check for image files (PNG, JPG, SVG) - ONLY in outputs/generated-diagrams/
            image_files = []
            # Extract UUID request ID from filename (format: YYYYMMDD_HHMMSS_UUID_diagram.png)
            filename_parts = output_path.stem.split('_')
            # The UUID is typically the 3rd part (after timestamp and time)
            if len(filename_parts) >= 3:
                request_id = filename_parts[2]  # Just the UUID
            else:
                request_id = output_path.stem.replace('_diagram', '')  # Fallback
            
            print(f"Looking for diagram files matching request ID: {request_id}")
            print(f"Expected output path: {output_path}")
            print(f"Searching ONLY in: {output_dir}")
            
            # Search ONLY in the outputs/generated-diagrams/ directory
            # Also check nested generated-diagrams/generated-diagrams/ and move files if found
            search_dirs = [output_dir]
            nested_dir = output_dir / "generated-diagrams"
            if nested_dir.exists():
                search_dirs.append(nested_dir)
            
            # Search for files in the correct directory
            for search_dir in search_dirs:
                for pattern in ["*.png", "*.jpg", "*.jpeg", "*.svg"]:
                    image_files.extend([f for f in search_dir.glob(pattern) if f.is_file()])
            
            # Also search for files saved outside outputs/ and move them
            # Check Backend directory and parent directories for misplaced files
            misplaced_locations = [
                Path(__file__).parent,  # Backend directory
                Path(__file__).parent.parent,  # Project root
            ]
            
            for misplaced_dir in misplaced_locations:
                for pattern in ["*.png", "*.jpg", "*.jpeg", "*.svg"]:
                    misplaced_files = list(misplaced_dir.glob(pattern))
                    for misplaced_file in misplaced_files:
                        # Check if it's a diagram file (contains timestamp pattern or UUID)
                        if request_id in misplaced_file.stem or "_diagram" in misplaced_file.name:
                            target_path = output_dir / misplaced_file.name
                            if not target_path.exists():
                                try:
                                    print(f"Moving misplaced file from {misplaced_file.parent} to {output_dir}")
                                    shutil.move(str(misplaced_file), str(target_path))
                                    image_files.append(target_path)
                                except Exception as e:
                                    print(f"Failed to move misplaced file: {e}")
            
            print(f"Found {len(image_files)} total image files in outputs/generated-diagrams/")
            
            if image_files:
                # Filter to find files matching the request ID first
                matching_files = [f for f in image_files if request_id in f.stem]
                
                print(f"Files matching request ID '{request_id}': {len(matching_files)}")
                if matching_files:
                    for mf in matching_files:
                        print(f"  - {mf.name} (modified: {mf.stat().st_mtime})")
                
                if matching_files:
                    # If we have files matching the request ID, use the most recent one
                    latest_image = max(matching_files, key=lambda p: p.stat().st_mtime)
                    print(f"Found matching image file for request {request_id}: {latest_image}")
                    
                    # ALWAYS move file to outputs/generated-diagrams/ if it's not already there
                    if latest_image.parent != output_dir:
                        target_path = output_dir / latest_image.name
                        # Handle name conflicts
                        if target_path.exists():
                            # Add timestamp to avoid overwriting
                            target_path = output_dir / f"{latest_image.stem}_moved{latest_image.suffix}"
                        print(f"Moving file from {latest_image.parent} to {output_dir}")
                        try:
                            shutil.move(str(latest_image), str(target_path))
                            return str(target_path)
                        except Exception as e:
                            print(f"Failed to move file: {e}")
                            return str(latest_image)
                    
                    return str(latest_image)
                else:
                    # Fallback: MCP server created a file with generic name instead of our timestamped name
                    # Find the most recently modified file (within last 60 seconds)
                    now = time.time()
                    recent_files = [f for f in image_files if (now - f.stat().st_mtime) < 60]
                    
                    if recent_files:
                        latest_image = max(recent_files, key=lambda p: p.stat().st_mtime)
                        file_age = now - latest_image.stat().st_mtime
                        print(f"Found recently created file (no request ID match): {latest_image} (age: {file_age:.1f}s)")
                        
                        # CRITICAL: Copy this file to our expected output path to avoid reusing same file
                        if latest_image != output_path:
                            try:
                                shutil.copy2(str(latest_image), str(output_path))
                                print(f"Copied {latest_image.name} → {output_path.name}")
                                return str(output_path)
                            except Exception as e:
                                print(f"Failed to copy file: {e}")
                                return str(latest_image)
                        else:
                            return str(latest_image)
                    else:
                        print(f"No recently created files found (all files older than 60 seconds)")
                        return None
            
            print("No diagram file found after generation")
            return None
            
    except ImportError:
        # strands/mcp not installed
        print("Diagram generation skipped: strands/mcp packages not installed")
        return None
    except Exception as e:
        # Silently fail - diagram generation is optional
        print(f"Diagram generation unavailable: {str(e)[:100]}")
        return None


def generate_diagram_with_bedrock(
    summary_text: str,
    output_path: Path,
    aws_region: str = "us-east-1",
    bedrock_model_id: str = "anthropic.claude-3-sonnet-20240229-v1:0",
    diagram_prompt: Optional[str] = None
) -> Optional[str]:
    """
    This method is deprecated - Mermaid flowchart is not suitable for AWS architecture diagrams.
    Use strands/MCP method instead which generates proper AWS architecture diagrams.
    """
    print("Skipping Bedrock/Mermaid method - not suitable for AWS architecture diagrams")
    return None
    """
    Generate architecture diagram using AWS Bedrock with high-end models (Claude 3.5 Sonnet/Opus).
    Uses Mermaid diagram code generation with full prompt control for white backgrounds.
    
    This method provides COMPLETE CONTROL over the prompt and styling, ensuring:
    - Pure white (#FFFFFF) backgrounds for all containers
    - No colored fills inside boxes
    - Professional AWS-standard diagram appearance
    - Horizontal 16:9 layout
    
    Args:
        summary_text: Architecture summary text
        output_path: Path to save the diagram PNG locally (before S3 upload)
        aws_region: AWS region for Bedrock
        bedrock_model_id: High-end Bedrock model ID (default: Claude 3.5 Sonnet)
    
    Returns:
        Path to generated diagram image or None if failed.
    """
    try:
        bedrock_runtime = boto3.client('bedrock-runtime', region_name=aws_region)
    except NoCredentialsError:
        print("AWS credentials not configured for Bedrock")
        return None
    except Exception as e:
        print(f"Failed to initialize Bedrock client: {e}")
        return None
    
    absolute_output_path = output_path.resolve()
    
    # Use provided diagram prompt or generate default
    if diagram_prompt:
        # Use the provided prompt directly (it should already contain the summary)
        readable_summary = convert_markdown_to_readable_text(summary_text)
        # Replace placeholders if they exist in the prompt
        diagram_code_prompt = diagram_prompt.replace(
            '{readable_summary}',
            readable_summary
        ).replace(
            '{summary_text}',
            readable_summary
        )
        # If prompt doesn't have placeholders, it's already complete
    else:
        # Convert markdown summary to human-readable text for better diagram generation
        readable_summary = convert_markdown_to_readable_text(summary_text)
        
        # Clean, concise prompt for Mermaid diagram generation with landscape emphasis
        diagram_code_prompt = f"""Generate Mermaid flowchart code for a horizontal AWS architecture diagram in LANDSCAPE mode.

ARCHITECTURE SUMMARY:
{readable_summary}

REQUIREMENTS:
- MANDATORY: Horizontal 16:9 LANDSCAPE layout (left-to-right flow, NOT top-to-bottom)
- Canvas MUST be wider than tall (3840×2160 or 1920×1080)
- Hierarchy: AWS Cloud → Region → VPC → Availability Zones (side-by-side horizontally) → Subnets
- Include all AWS services from summary
- Minimal arrows (only essential flows: Users→Edge→App→Database)
- Rectangular shapes with sharp corners

STYLING:
- All containers: fill:#FFFFFF (white backgrounds)
- Borders: AWS Cloud (#232F3E), Region (#00A4A6 dashed), VPC (#8C4FFF), AZ (#147EBA dashed), Public Subnet (#7AA116), Private Subnet (#00A4A6)
- Layout: Horizontal LANDSCAPE - components flow left to right across width
- Canvas: 3840×2160 (16:9 landscape, wider than tall)

EXAMPLE:
\`\`\`mermaid
flowchart LR
    subgraph AWS["AWS Cloud"]
        style AWS fill:#FFFFFF,stroke:#232F3E,stroke-width:3px
        subgraph Region["Region"]
            style Region fill:#FFFFFF,stroke:#00A4A6,stroke-width:2px,stroke-dasharray: 5 5
            subgraph VPC["VPC"]
                style VPC fill:#FFFFFF,stroke:#8C4FFF,stroke-width:3px
                subgraph AZ1["AZ 1a"]
                    style AZ1 fill:#FFFFFF,stroke:#147EBA,stroke-width:2px,stroke-dasharray: 5 5
                    subgraph Pub1["Public"]
                        style Pub1 fill:#FFFFFF,stroke:#7AA116,stroke-width:2px
                        ALB[ALB]
                    end
                    subgraph Priv1["Private"]
                        style Priv1 fill:#FFFFFF,stroke:#00A4A6,stroke-width:2px
                        EC2[EC2]
                        RDS[(RDS)]
                    end
                end
            end
        end
    end
    ALB --> EC2
    EC2 --> RDS
\`\`\`

Return ONLY the Mermaid code block. Use flowchart LR for horizontal layout. Every subgraph MUST have fill:#FFFFFF."""

    try:
        print(f"Generating diagram code with Bedrock model: {bedrock_model_id}")
        
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 12000,
            "temperature": 0.3,
            "messages": [
                {
                    "role": "user",
                    "content": diagram_code_prompt
                }
            ]
        }
        
        response = bedrock_runtime.invoke_model(
            modelId=bedrock_model_id,
            body=json.dumps(body)
        )
        
        response_body = json.loads(response['body'].read())
        
        # Extract Mermaid code from response
        mermaid_code = None
        if 'content' in response_body:
            for block in response_body['content']:
                if block.get('type') == 'text':
                    text = block.get('text', '')
                    if '```mermaid' in text.lower():
                        start_idx = text.lower().find('```mermaid')
                        remaining = text[start_idx + len('```mermaid'):]
                        end_idx = remaining.find('```')
                        if end_idx != -1:
                            mermaid_code = remaining[:end_idx].strip()
                            break
                    elif 'flowchart' in text.lower() or 'graph' in text.lower():
                        lines = text.split('\n')
                        start_found = False
                        code_lines = []
                        for line in lines:
                            if 'flowchart' in line.lower() or 'graph' in line.lower():
                                start_found = True
                            if start_found:
                                if line.strip().startswith('```'):
                                    continue
                                code_lines.append(line)
                                if line.strip() == '```' and len(code_lines) > 5:
                                    code_lines.pop()
                                    break
                        if code_lines:
                            mermaid_code = '\n'.join(code_lines).strip()
                            mermaid_code = mermaid_code.replace('```mermaid', '').replace('```', '').strip()
                            break
        
        if not mermaid_code:
            print("No Mermaid code found in Bedrock response")
            print(f"Response preview: {str(response_body)[:500]}")
            return None
        
        print(f"Generated Mermaid code ({len(mermaid_code)} chars)")
        
        # Save prompt to text file
        prompt_file = output_path.parent / f"{output_path.stem}_prompt.txt"
        with open(prompt_file, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("DIAGRAM GENERATION PROMPT\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n")
            f.write(f"Model: {bedrock_model_id}\n")
            f.write(f"Output Path: {absolute_output_path}\n\n")
            f.write("=" * 80 + "\n")
            f.write("PROMPT TEXT\n")
            f.write("=" * 80 + "\n\n")
            f.write(diagram_code_prompt)
        print(f"Prompt saved to: {prompt_file}")
        
        # Save Mermaid code temporarily
        mermaid_file = output_path.parent / f"{output_path.stem}.mmd"
        with open(mermaid_file, 'w') as f:
            f.write(mermaid_code)
        print(f"Mermaid code saved to: {mermaid_file}")
        
        # Try to render Mermaid to PNG using mermaid-cli (mmdc)
        mmdc_path = shutil.which("mmdc")
        if mmdc_path:
            try:
                cmd = [
                    mmdc_path,
                    "-i", str(mermaid_file),
                    "-o", str(output_path),
                    "-w", "3840",
                    "-H", "2160",
                    "-b", "white",
                    "-s", "2",
                    "-t", "default",
                    "--puppeteerConfigFile", "none"
                ]
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                if result.returncode == 0 and output_path.exists():
                    mermaid_file.unlink()
                    file_size = output_path.stat().st_size
                    print(f"✓ Diagram generated successfully: {output_path} ({file_size:,} bytes)")
                    return str(output_path)
                else:
                    print(f"Mermaid rendering failed: {result.stderr}")
            except subprocess.TimeoutExpired:
                print("Mermaid rendering timed out")
            except Exception as e:
                print(f"Failed to render Mermaid: {e}")
        else:
            print("Mermaid CLI (mmdc) not found. Install with: npm install -g @mermaid-js/mermaid-cli")
            return None
        
        return None
        
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', '')
        error_message = e.response.get('Error', {}).get('Message', str(e))
        print(f"AWS Bedrock error ({error_code}): {error_message}")
        
        # Try fallback to available models if requested model is not available
        if error_code == 'ValidationException' or 'not available' in error_message.lower() or 'isn\'t supported' in error_message.lower():
            print(f"Model {bedrock_model_id} not available, attempting fallback...")
            # Try Claude 3 Sonnet first
            if 'claude-3-sonnet' not in bedrock_model_id:
                fallback_model = "anthropic.claude-3-sonnet-20240229-v1:0"
                print(f"Attempting fallback to {fallback_model}...")
                return generate_diagram_with_bedrock(
                    summary_text, output_path, aws_region, fallback_model
                )
            # If Sonnet also fails, try Haiku
            elif 'claude-3-haiku' not in bedrock_model_id:
                fallback_model = "anthropic.claude-3-haiku-20240307-v1:0"
                print(f"Attempting fallback to {fallback_model}...")
                return generate_diagram_with_bedrock(
                    summary_text, output_path, aws_region, fallback_model
                )
        return None
    except Exception as e:
        print(f"Error generating diagram with Bedrock: {e}")
        import traceback
        traceback.print_exc()
        return None


def upload_to_s3(file_path: Path, s3_key: str) -> Optional[str]:
    """
    Upload a file to S3 bucket.
    
    Args:
        file_path: Local file path to upload
        s3_key: S3 object key (path in bucket)
    
    Returns:
        S3 URL if successful, None otherwise
    """
    if not s3_client:
        print("S3 client not available")
        return None
    
    try:
        s3_client.upload_file(
            str(file_path),
            S3_BUCKET_NAME,
            s3_key,
            ExtraArgs={'ContentType': 'image/png'}
        )
        s3_url = f"https://{S3_BUCKET_NAME}.s3.{S3_REGION}.amazonaws.com/{s3_key}"
        print(f"✓ Uploaded to S3: {s3_url}")
        return s3_url
    except Exception as e:
        print(f"Failed to upload to S3: {e}")
        return None


def download_from_s3(s3_key: str) -> Optional[bytes]:
    """
    Download a file from S3 bucket.
    
    Args:
        s3_key: S3 object key (path in bucket)
    
    Returns:
        File content as bytes if successful, None otherwise
    """
    if not s3_client:
        return None
    
    try:
        response = s3_client.get_object(Bucket=S3_BUCKET_NAME, Key=s3_key)
        return response['Body'].read()
    except Exception as e:
        print(f"Failed to download from S3: {e}")
        return None


def list_s3_diagrams() -> List[Dict]:
    """
    List all diagrams in S3 bucket.
    
    Returns:
        List of diagram metadata dictionaries
    """
    if not s3_client:
        return []
    
    try:
        diagrams = []
        paginator = s3_client.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=S3_BUCKET_NAME, Prefix=S3_PREFIX)
        
        for page in pages:
            if 'Contents' in page:
                for obj in page['Contents']:
                    key = obj['Key']
                    if key.endswith('.png'):
                        diagrams.append({
                            "filename": Path(key).name,
                            "s3_key": key,
                            "size": obj['Size'],
                            "created": obj['LastModified'].timestamp(),
                            "modified": obj['LastModified'].timestamp(),
                            "url": f"/api/s3-diagram/{Path(key).name}"
                        })
        
        # Sort by creation time (newest first)
        diagrams.sort(key=lambda x: x["created"], reverse=True)
        return diagrams
    except Exception as e:
        print(f"Failed to list S3 diagrams: {e}")
        return []


def generate_diagram(summary_text: str, output_path: Path, aws_region: str = "us-east-1", bedrock_model_id: str = "anthropic.claude-3-sonnet-20240229-v1:0", diagram_prompt: Optional[str] = None) -> Optional[str]:
    """
    Generate architecture diagram using strands/MCP (only method).
    Returns path to generated diagram image or None if failed.
    
    Uses AWS Diagram MCP Server which generates proper AWS architecture diagrams
    with official icons and proper layout.
    """
    # Use strands/MCP method only (Bedrock/Mermaid not suitable for architecture diagrams)
    print("Generating diagram with strands/MCP method (AWS Diagram MCP Server)...")
    return generate_diagram_with_strands(summary_text, output_path, diagram_prompt)


@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "Architecture Diagram Generator API", "status": "running"}


def send_progress_event(message: str, progress: Optional[int] = None, status: str = "info"):
    """Helper function to format SSE events"""
    data = {
        "message": message,
        "status": status,
        "timestamp": datetime.now().isoformat()
    }
    if progress is not None:
        data["progress"] = progress
    return f"data: {json.dumps(data)}\n\n"


@app.post("/api/generate-summary")
async def generate_summary_for_approval(
    file: UploadFile = File(...),
    aws_region: Optional[str] = Form("us-east-1"),
    bedrock_model_id: Optional[str] = Form("arn:aws:bedrock:us-east-1:302263040839:inference-profile/us.anthropic.claude-haiku-4-5-20251001-v1:0")
):
    """
    Generate architecture summary using high-end model for user approval/editing.
    Returns summary text that user can review and edit before diagram generation.
    """
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    request_id = str(uuid.uuid4())
    temp_pdf_path = UPLOAD_DIR / f"{request_id}_{file.filename}"
    
    try:
        # Save uploaded PDF
        with open(temp_pdf_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Extract content from PDF
        content = extract_pdf(
            pdf_path=str(temp_pdf_path),
            method='pdfplumber'
        )
        
        # Generate summary using high-end model
        summary = summarize_with_bedrock(
            text=content.get('text', ''),
            aws_region=aws_region,
            model_id=bedrock_model_id,
            summary_type='architecture'
        )
        
        summary_text = summary.get('summary', '')
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "summary": summary_text,
                "request_id": request_id,
                "model_id": bedrock_model_id,
                "summary_length": len(summary_text)
            }
        )
    except Exception as e:
        print(f"Error generating summary: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating summary: {str(e)}")
    finally:
        # Clean up temporary PDF file
        if temp_pdf_path.exists():
            temp_pdf_path.unlink()


@app.post("/api/generate-diagram-stream")
async def generate_architecture_diagram_stream(
    file: UploadFile = File(...),
    aws_region: Optional[str] = Form("us-east-1"),
    bedrock_model_id: Optional[str] = Form("anthropic.claude-3-sonnet-20240229-v1:0")
):
    """
    Generate architecture diagram with SSE progress updates from PDF file.
    """
    if not file.filename.endswith('.pdf'):
        async def error_stream():
            yield await send_progress_event("Error: File must be a PDF", status="error")
        return StreamingResponse(error_stream(), media_type="text/event-stream")


@app.post("/api/generate-diagram-from-summary")
async def generate_architecture_diagram_from_summary_stream(
    summary_text: str = Form(...),
    diagram_prompt: Optional[str] = Form(None),
    aws_region: Optional[str] = Form("us-east-1"),
    bedrock_model_id: Optional[str] = Form("anthropic.claude-3-sonnet-20240229-v1:0")
):
    """
    Generate architecture diagram with SSE progress updates from approved summary text.
    """
    async def generate_with_progress():
        request_id = str(uuid.uuid4())
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        generated_diagrams_dir = OUTPUT_DIR / "generated-diagrams"
        generated_diagrams_dir.mkdir(exist_ok=True)
        output_diagram_path = generated_diagrams_dir / f"{timestamp}_{request_id}_diagram.png"
        
        try:
            yield send_progress_event("✓ Using approved summary", 60, "success")
            await asyncio.sleep(0.1)
            
            # Generate diagram code
            yield send_progress_event("🎨 Generating diagram code with Bedrock...", 70, "info")
            diagram_path = generate_diagram(
                summary_text,
                output_diagram_path,
                aws_region=aws_region,
                bedrock_model_id=bedrock_model_id,
                diagram_prompt=diagram_prompt
            )
            
            if not diagram_path or not Path(diagram_path).exists():
                yield send_progress_event(
                    "⚠️ Diagram generation failed. Check logs for details.",
                    0,
                    "error"
                )
                yield send_progress_event(
                    f"Architecture Summary: {summary_text[:200]}...",
                    0,
                    "info"
                )
                return
            
            yield send_progress_event("✓ Diagram code generated", 80, "success")
            await asyncio.sleep(0.1)
            
            # Validate diagram file
            diagram_file = Path(diagram_path)
            if not diagram_file.is_file():
                yield send_progress_event("❌ Diagram file is invalid", 0, "error")
                return
            
            file_size = diagram_file.stat().st_size
            if file_size == 0:
                yield send_progress_event("❌ Diagram file is empty", 0, "error")
                return
            
            yield send_progress_event(f"✓ Diagram rendered ({file_size:,} bytes)", 90, "success")
            await asyncio.sleep(0.1)
            
            # Upload to S3
            yield send_progress_event("☁️ Uploading to S3...", 95, "info")
            s3_key = f"{S3_PREFIX}{timestamp}_{request_id}_diagram.png"
            s3_url = upload_to_s3(diagram_file, s3_key)
            
            if s3_url:
                yield send_progress_event("✓ Uploaded to S3 successfully", 100, "success")
                await asyncio.sleep(0.1)
                
                # Read image data
                with open(diagram_file, 'rb') as f:
                    image_data = f.read()
                
                # Send final event with image data (base64 encoded)
                import base64
                image_base64 = base64.b64encode(image_data).decode('utf-8')
                final_data = {
                    "message": "✓ Diagram ready!",
                    "status": "complete",
                    "progress": 100,
                    "request_id": request_id,
                    "filename": diagram_file.name,
                    "file_size": file_size,
                    "s3_url": s3_url,
                    "s3_key": s3_key,
                    "image_data": image_base64,
                    "timestamp": datetime.now().isoformat()
                }
                yield f"data: {json.dumps(final_data)}\n\n"
            else:
                yield send_progress_event("⚠️ S3 upload failed, using local storage", 100, "warning")
                await asyncio.sleep(0.1)
                
                # Read image data
                with open(diagram_file, 'rb') as f:
                    image_data = f.read()
                
                import base64
                image_base64 = base64.b64encode(image_data).decode('utf-8')
                final_data = {
                    "message": "✓ Diagram ready (local storage)",
                    "status": "complete",
                    "progress": 100,
                    "request_id": request_id,
                    "filename": diagram_file.name,
                    "file_size": file_size,
                    "image_data": image_base64,
                    "timestamp": datetime.now().isoformat()
                }
                yield f"data: {json.dumps(final_data)}\n\n"
            
        except Exception as e:
            error_msg = f"❌ Error: {str(e)}"
            print(f"Error processing request: {str(e)}")
            yield send_progress_event(error_msg, 0, "error")
            import traceback
            traceback.print_exc()
    
    return StreamingResponse(
        generate_with_progress(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.post("/api/generate-diagram-stream")
async def generate_architecture_diagram_stream(
    file: UploadFile = File(...),
    aws_region: Optional[str] = Form("us-east-1"),
    bedrock_model_id: Optional[str] = Form("anthropic.claude-3-sonnet-20240229-v1:0")
):
    """
    Generate architecture diagram with SSE progress updates from PDF file.
    """
    if not file.filename.endswith('.pdf'):
        async def error_stream():
            yield await send_progress_event("Error: File must be a PDF", status="error")
        return StreamingResponse(error_stream(), media_type="text/event-stream")
    
    async def generate_with_progress():
        request_id = str(uuid.uuid4())
        temp_pdf_path = UPLOAD_DIR / f"{request_id}_{file.filename}"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        generated_diagrams_dir = OUTPUT_DIR / "generated-diagrams"
        generated_diagrams_dir.mkdir(exist_ok=True)
        output_diagram_path = generated_diagrams_dir / f"{timestamp}_{request_id}_diagram.png"
        
        try:
            # Step 1: Save uploaded PDF
            yield send_progress_event("📄 Uploading PDF file...", 10, "info")
            with open(temp_pdf_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            yield send_progress_event("✓ PDF uploaded successfully", 20, "success")
            await asyncio.sleep(0.1)
            
            # Step 2: Extract content from PDF
            yield send_progress_event("📖 Extracting content from PDF...", 30, "info")
            content = extract_pdf(
                pdf_path=str(temp_pdf_path),
                method='pdfplumber'
            )
            yield send_progress_event(f"✓ Extracted {len(content.get('text', ''))} characters", 40, "success")
            await asyncio.sleep(0.1)
            
            # Step 3: Summarize for architecture
            yield send_progress_event("🤖 Analyzing architecture with AI...", 50, "info")
            summary = summarize_with_bedrock(
                text=content.get('text', ''),
                aws_region=aws_region,
                model_id=bedrock_model_id,
                summary_type='architecture'
            )
            final_summary = summary.get('summary', '')
            yield send_progress_event("✓ Architecture analysis complete", 60, "success")
            await asyncio.sleep(0.1)
            
            # Step 4: Generate diagram code
            yield send_progress_event("🎨 Generating diagram code with Bedrock...", 70, "info")
            diagram_path = generate_diagram(
                final_summary,
                output_diagram_path,
                aws_region=aws_region,
                bedrock_model_id=bedrock_model_id
            )
            
            if not diagram_path or not Path(diagram_path).exists():
                yield send_progress_event(
                    "⚠️ Diagram generation failed. Check logs for details.",
                    0,
                    "error"
                )
                yield send_progress_event(
                    f"Architecture Summary: {final_summary[:200]}...",
                    0,
                    "info"
                )
                return
            
            yield send_progress_event("✓ Diagram code generated", 80, "success")
            await asyncio.sleep(0.1)
            
            # Step 5: Validate diagram file
            diagram_file = Path(diagram_path)
            if not diagram_file.is_file():
                yield send_progress_event("❌ Diagram file is invalid", 0, "error")
                return
            
            file_size = diagram_file.stat().st_size
            if file_size == 0:
                yield send_progress_event("❌ Diagram file is empty", 0, "error")
                return
            
            yield send_progress_event(f"✓ Diagram rendered ({file_size:,} bytes)", 90, "success")
            await asyncio.sleep(0.1)
            
            # Step 6: Upload to S3
            yield send_progress_event("☁️ Uploading to S3...", 95, "info")
            s3_key = f"{S3_PREFIX}{timestamp}_{request_id}_diagram.png"
            s3_url = upload_to_s3(diagram_file, s3_key)
            
            if s3_url:
                yield send_progress_event("✓ Uploaded to S3 successfully", 100, "success")
                await asyncio.sleep(0.1)
                
                # Read image data
                with open(diagram_file, 'rb') as f:
                    image_data = f.read()
                
                # Send final event with image data (base64 encoded)
                import base64
                image_base64 = base64.b64encode(image_data).decode('utf-8')
                final_data = {
                    "message": "✓ Diagram ready!",
                    "status": "complete",
                    "progress": 100,
                    "request_id": request_id,
                    "filename": diagram_file.name,
                    "file_size": file_size,
                    "s3_url": s3_url,
                    "s3_key": s3_key,
                    "image_data": image_base64,
                    "timestamp": datetime.now().isoformat()
                }
                yield f"data: {json.dumps(final_data)}\n\n"
            else:
                yield send_progress_event("⚠️ S3 upload failed, using local storage", 100, "warning")
                await asyncio.sleep(0.1)
                
                # Read image data
                with open(diagram_file, 'rb') as f:
                    image_data = f.read()
                
                import base64
                image_base64 = base64.b64encode(image_data).decode('utf-8')
                final_data = {
                    "message": "✓ Diagram ready (local storage)",
                    "status": "complete",
                    "progress": 100,
                    "request_id": request_id,
                    "filename": diagram_file.name,
                    "file_size": file_size,
                    "image_data": image_base64,
                    "timestamp": datetime.now().isoformat()
                }
                yield f"data: {json.dumps(final_data)}\n\n"
            
        except Exception as e:
            error_msg = f"❌ Error: {str(e)}"
            print(f"Error processing request: {str(e)}")
            yield send_progress_event(error_msg, 0, "error")
            import traceback
            traceback.print_exc()
        finally:
            # Clean up temporary PDF file
            if temp_pdf_path.exists():
                temp_pdf_path.unlink()
    
    return StreamingResponse(
        generate_with_progress(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.post("/api/generate-diagram")
async def generate_architecture_diagram(
    file: UploadFile = File(...),
    aws_region: Optional[str] = Form("us-east-1"),
    bedrock_model_id: Optional[str] = Form("anthropic.claude-3-sonnet-20240229-v1:0")
):
    """
    Upload PDF, extract content, summarize, and generate architecture diagram
    (Legacy endpoint - use /api/generate-diagram-stream for progress updates)
    """
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    # Generate unique ID for this request
    request_id = str(uuid.uuid4())
    temp_pdf_path = UPLOAD_DIR / f"{request_id}_{file.filename}"
    
    # Use generated-diagrams subdirectory with timestamp for better organization
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    generated_diagrams_dir = OUTPUT_DIR / "generated-diagrams"
    generated_diagrams_dir.mkdir(exist_ok=True)
    output_diagram_path = generated_diagrams_dir / f"{timestamp}_{request_id}_diagram.png"
    
    try:
        # Save uploaded PDF
        with open(temp_pdf_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Step 1: Extract content from PDF
        print(f"Extracting content from PDF: {temp_pdf_path}")
        content = extract_pdf(
            pdf_path=str(temp_pdf_path),
            method='pdfplumber'
        )
        
        # Step 2: Summarize for architecture
        print(f"Summarizing content for architecture diagram...")
        summary = summarize_with_bedrock(
            text=content.get('text', ''),
            aws_region=aws_region,
            model_id=bedrock_model_id,
            summary_type='architecture'
        )
        
        summary_text = summary.get('summary', '')
        
        # Step 3: Generate diagram using high-end Bedrock models
        print(f"Generating architecture diagram with Bedrock...")
        diagram_path = generate_diagram(
            summary_text,
            output_diagram_path,
            aws_region=aws_region,
            bedrock_model_id=bedrock_model_id
        )
        
        if not diagram_path or not Path(diagram_path).exists():
            # If diagram generation failed, return summary as JSON
            print(f"Diagram generation failed or file not found: {diagram_path}")
            return JSONResponse(
                status_code=200,
                content={
                    "success": False,
                    "message": "Diagram generation unavailable. Architecture summary generated successfully.",
                    "summary": summary_text,
                    "diagram_path": None,
                    "note": "To enable diagram generation, ensure AWS credentials are configured and mermaid-cli is installed (npm install -g @mermaid-js/mermaid-cli)."
                }
            )
        
        # Validate the diagram file
        diagram_file = Path(diagram_path)
        if not diagram_file.is_file():
            print(f"Diagram path is not a file: {diagram_path}")
            return JSONResponse(
                status_code=200,
                content={
                    "success": False,
                    "message": "Diagram file is invalid.",
                    "summary": summary_text,
                    "diagram_path": None
                }
            )
        
        # Check file size (should be > 0)
        file_size = diagram_file.stat().st_size
        if file_size == 0:
            print(f"Diagram file is empty: {diagram_path}")
            return JSONResponse(
                status_code=200,
                content={
                    "success": False,
                    "message": "Diagram file is empty.",
                    "summary": summary_text,
                    "diagram_path": None
                }
            )
        
        # Upload to S3
        s3_key = f"{S3_PREFIX}{timestamp}_{request_id}_diagram.png"
        s3_url = upload_to_s3(diagram_file, s3_key)
        
        if s3_url:
            print(f"✓ Diagram uploaded to S3: {s3_url}")
            # Return S3 URL via JSON response with image data
            # Read the file to return it immediately
            with open(diagram_file, 'rb') as f:
                image_data = f.read()
            
            return Response(
                content=image_data,
                media_type="image/png",
                headers={
                    "X-Summary-Length": str(len(summary_text)),
                    "X-Request-ID": request_id,
                    "X-File-Size": str(file_size),
                    "X-S3-URL": s3_url,
                    "X-S3-Key": s3_key,
                    "Cache-Control": "no-cache, no-store, must-revalidate",
                    "Pragma": "no-cache",
                    "Expires": "0",
                    "X-Filename": diagram_file.name
                }
            )
        else:
            # Fallback: return local file if S3 upload failed
            print(f"Warning: S3 upload failed, returning local file: {diagram_path}")
            return FileResponse(
                diagram_path,
                media_type="image/png",
                headers={
                    "X-Summary-Length": str(len(summary_text)),
                    "X-Request-ID": request_id,
                    "X-File-Size": str(file_size),
                    "Cache-Control": "no-cache, no-store, must-revalidate",
                    "Pragma": "no-cache",
                    "Expires": "0",
                    "X-Filename": diagram_file.name
                },
                filename=diagram_file.name
            )
        
    except Exception as e:
        print(f"Error processing request: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")
    
    finally:
        # Clean up temporary PDF file
        if temp_pdf_path.exists():
            temp_pdf_path.unlink()


@app.get("/api/diagrams")
async def list_diagrams():
    """List all generated diagrams with metadata from S3 (primary) and local (fallback)"""
    try:
        # Primary: List from S3
        s3_diagrams = list_s3_diagrams()
        
        # Fallback: Also check local directory
        generated_diagrams_dir = OUTPUT_DIR / "generated-diagrams"
        generated_diagrams_dir.mkdir(exist_ok=True)
        
        local_diagrams = []
        for file_path in generated_diagrams_dir.glob("*.png"):
            if file_path.is_file():
                stat_info = file_path.stat()
                # Only add if not already in S3 list
                if not any(d['filename'] == file_path.name for d in s3_diagrams):
                    local_diagrams.append({
                    "filename": file_path.name,
                    "size": stat_info.st_size,
                    "created": stat_info.st_ctime,
                    "modified": stat_info.st_mtime,
                    "url": f"/api/diagram-file/{file_path.name}"
                })
        
        # Combine S3 and local diagrams
        all_diagrams = s3_diagrams + local_diagrams
        
        # Sort by creation time (newest first)
        all_diagrams.sort(key=lambda x: x["created"], reverse=True)
        
        return {"diagrams": all_diagrams, "count": len(all_diagrams)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing diagrams: {str(e)}")


@app.get("/api/diagram-file/{filename}")
async def get_diagram_file(filename: str):
    """Retrieve a specific diagram file by filename from S3 (primary) or local (fallback)"""
    # Try S3 first
    s3_key = f"{S3_PREFIX}{filename}"
    s3_data = download_from_s3(s3_key)
    
    if s3_data:
        return Response(
            content=s3_data,
            media_type="image/png",
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )
    
    # Fallback to local file
    diagram_path = OUTPUT_DIR / "generated-diagrams" / filename
    
    if not diagram_path.exists() or not diagram_path.is_file():
        raise HTTPException(status_code=404, detail="Diagram not found")
    
    return FileResponse(
        diagram_path,
        media_type="image/png",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        },
        filename=filename
    )


@app.get("/api/s3-diagram/{filename}")
async def get_s3_diagram(filename: str):
    """Retrieve a diagram directly from S3 by filename"""
    s3_key = f"{S3_PREFIX}{filename}"
    s3_data = download_from_s3(s3_key)
    
    if not s3_data:
        raise HTTPException(status_code=404, detail="Diagram not found in S3")
    
    return Response(
        content=s3_data,
        media_type="image/png",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )


@app.get("/api/diagram/{request_id}")
async def get_diagram(request_id: str):
    """Retrieve a previously generated diagram by request ID"""
    diagram_path = OUTPUT_DIR / f"{request_id}_diagram.png"
    
    if not diagram_path.exists():
        raise HTTPException(status_code=404, detail="Diagram not found")
    
    return FileResponse(diagram_path, media_type="image/png")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

