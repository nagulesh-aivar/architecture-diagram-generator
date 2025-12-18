"""
FastAPI Backend Server for Architecture Diagram Generator
Handles PDF upload, extraction, summarization, and diagram generation
"""

import sys
import shutil
import subprocess
import json
from pathlib import Path
from typing import Optional
import uuid

from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import uvicorn

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


class DiagramRequest(BaseModel):
    aws_region: Optional[str] = "us-east-1"
    bedrock_model_id: Optional[str] = "anthropic.claude-3-sonnet-20240229-v1:0"


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


def generate_diagram_with_strands(summary_text: str, output_path: Path) -> Optional[str]:
    """
    Generate architecture diagram using strands and MCP (if available).
    Returns path to generated diagram image or None if failed.
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
        from strands.models.bedrock import BedrockModel
        import boto3
        from botocore.config import Config
        
        # Create prompt for diagram generation
        absolute_output_path = output_path.resolve()
        # diagram_prompt = f"""Based on the following architecture summary, create a comprehensive AWS architecture diagram and save it as a PNG image file.

        # Architecture Summary:
        # {summary_text}

        # Requirements:
        # - Generate a detailed AWS architecture diagram showing all system components and services
        # - Show data flows and connections between components
        # - Include all AWS services mentioned
        # - Show integration points
        # - Include storage and database components
        # - Show network architecture

        # IMPORTANT: Save the diagram as a PNG image file at this exact path: {absolute_output_path}
        # The file must be saved as a PNG image, not a DOT file or any other format."""
        
        
#         diagram_prompt = f"""You are an expert AWS Solutions Architect. Create a professional, production-ready AWS architecture diagram based on the following summary.

# ARCHITECTURE SUMMARY:
# {summary_text}

# REQUIREMENTS FOR THE DIAGRAM:

# 1. COMPREHENSIVE COVERAGE:
#    - Include ALL AWS services, components, and resources mentioned in the summary
#    - Show complete data flow from entry points to storage
#    - Include all integration points and external systems
#    - Display security layers, networking, and access controls

# 2. PROFESSIONAL LAYOUT:
#    - Use a clear hierarchical structure (top-to-bottom or left-to-right)
#    - Group components by function: Presentation Layer → Application Layer → Data Layer
#    - Use visual grouping with labeled containers (VPCs, Availability Zones, Subnets)
#    - Maintain consistent spacing and alignment
#    - Use color coding to distinguish: Public (blue), Private (green), Data (orange), Security (red)

# 3. NETWORK ARCHITECTURE:
#    - Show VPC structure with public and private subnets
#    - Display Internet Gateway, NAT Gateway, and Route Tables
#    - Include Load Balancers (ALB/NLB) and their placement
#    - Show Security Groups and Network ACLs where relevant
#    - Indicate Availability Zones and multi-AZ deployments

# 4. COMPUTE & SERVICES:
#    - EC2 instances with instance types if specified
#    - Container services (ECS, EKS, Fargate)
#    - Serverless functions (Lambda)
#    - Auto Scaling Groups
#    - API Gateway and service endpoints

# 5. DATA & STORAGE:
#    - Databases (RDS, DynamoDB, DocumentDB, etc.)
#    - Caching layers (ElastiCache, CloudFront)
#    - Object storage (S3 buckets with lifecycle policies if mentioned)
#    - Data transfer and backup mechanisms

# 6. INTEGRATIONS & EXTERNAL:
#    - Third-party APIs and services
#    - On-premises connections (VPN, Direct Connect)
#    - External users and clients
#    - SaaS integrations

# 7. SECURITY & MONITORING:
#    - IAM roles and policies
#    - AWS WAF, Shield, GuardDuty
#    - CloudWatch, CloudTrail, X-Ray
#    - Secrets Manager, KMS

# 8. DATA FLOW:
#    - Use directional arrows showing request/response flows
#    - Label connections with protocols (HTTPS, gRPC, MQTT, etc.)
#    - Show data transformation points
#    - Indicate synchronous vs asynchronous flows

# 9. VISUAL QUALITY:
#    - Use official AWS service icons
#    - High resolution (minimum 1920x1080)
#    - Clear, readable labels (minimum 12pt font)
#    - Professional color scheme
#    - Include a legend if using custom symbols

# 10. OUTPUT FORMAT:
#     - Generate as a high-quality PNG image file
#     - Save directly to: {absolute_output_path}
#     - The file MUST be a valid PNG image (not DOT, not code, not text)
#     - Ensure the diagram is immediately usable in presentations and documentation

# CRITICAL: Create the actual PNG image file at the specified path. Do not generate code, DOT files, or text descriptions. The output must be a rendered diagram image."""

        

        diagram_prompt = f"""You are an expert AWS Solutions Architect creating a COMPREHENSIVE, DETAILED, enterprise-grade architecture diagram. Follow AWS official diagramming standards strictly. The diagram must be complete, detailed, and immediately usable in presentations.

CRITICAL REQUIREMENTS:
1. COMPREHENSIVE COVERAGE: Include EVERY service, component, and resource mentioned in the architecture summary. Do NOT create a simple 3-5 component diagram. This must be a FULL, DETAILED architecture showing all layers, services, and connections.
2. CLEAN DESIGN: NO emojis, NO decorative elements, NO clutter. Use simple text labels only.
3. MULTI-LAYER ARCHITECTURE: Show complete infrastructure with multiple tiers, subnets, availability zones, and all services.

ARCHITECTURE SUMMARY TO DIAGRAM:
{summary_text}

MANDATORY: Analyze the summary above and identify ALL AWS services, components, and resources mentioned. Create a COMPREHENSIVE diagram that includes EVERYTHING. Do NOT simplify or omit components. This must be a complete, production-ready architecture diagram with all layers visible.

=== DIAGRAM STRUCTURE & HIERARCHY - HORIZONTAL LAYOUT (LEFT TO RIGHT) ===

CRITICAL LAYOUT REQUIREMENT: The entire diagram must flow HORIZONTALLY from LEFT to RIGHT, not vertically. All major sections should be arranged in columns from left to right.

BACKGROUND: Pure white (#FFFFFF) - the entire diagram background must be white.

1. LEFT COLUMN - External/Edge Services:
   - Place on the far LEFT side of the diagram
   - Label: "External/Edge Services" (simple text, NO emojis)
   - Include: Users/End Users, CloudFront, Route 53, AWS WAF, API Gateway
   - Use official AWS service icons (64x64px)
   - Background: Pure white (#FFFFFF)
   - Border: Create a CLEAR BOX with dark gray border (2px solid, #666666)
   - Layout: Stack services vertically within the box
   - Labels: Service name below icon, 11pt font, simple text only
   - Box must have visible border and clear label at the top

2. SECOND COLUMN - AWS Region Container (CRITICAL: MUST HAVE CLEAR BOX):
   - Place to the RIGHT of External/Edge Services
   - Create a LARGE, CLEARLY DEFINED BOX with visible border
   - Border: Dark gray (#333333), 3px solid border - MUST be clearly visible
   - Background: Pure white (#FFFFFF)
   - Label at top of box: "AWS Region: [region-name]" (e.g., "AWS Region: us-east-1")
   - Label must be bold, 16pt, dark gray (#2D3436), centered at top of box
   - This box contains the VPC and all regional services

3. INSIDE AWS REGION BOX - VPC Container (CRITICAL: MUST HAVE CLEAR BOX):
   - Create a SECOND BOX inside the AWS Region box
   - Border: Medium gray (#666666), 2px solid border - MUST be clearly visible
   - Background: Very light gray (#F9F9F9) - subtle tint to distinguish from Region box
   - Label at top: "VPC: [vpc-name or CIDR]" (e.g., "VPC: 10.0.0.0/16")
   - Label must be bold, 14pt, dark gray (#2D3436)
   - VPC box should take up most of the Region box space
   - Show CIDR block notation if mentioned in summary

4. INSIDE VPC BOX - Multi-AZ Architecture (CRITICAL: MUST HAVE CLEAR BOXES):
   - Draw exactly TWO Availability Zones side by side (HORIZONTALLY, equal width)
   - Each AZ MUST be in its own CLEARLY DEFINED BOX
   - AZ Box Border: Light gray (#CCCCCC), 2px dashed border - MUST be clearly visible
   - AZ Box Background: Pure white (#FFFFFF)
   - Label each AZ box clearly at the top: "Availability Zone 1 (us-east-1a)" and "Availability Zone 2 (us-east-1b)" - NO emojis
   - Labels must be bold, 12pt, dark gray (#2D3436)
   - AZ boxes should be arranged HORIZONTALLY (side by side) within the VPC
   - In EACH Availability Zone box, create THREE distinct subnet tiers (stacked VERTICALLY within each AZ box):

   A. PUBLIC SUBNET (Top tier in each AZ):
      - Label: "Public Subnet (10.0.1.0/24)" - simple text, NO emojis
      - Place: Internet Gateway (IGW) - one per VPC, connected to VPC boundary
      - Place: NAT Gateway(s) - one per AZ in public subnet, clearly labeled
      - Place: Bastion Hosts (if mentioned) - show as EC2 icon
      - Place: Load Balancer nodes (if ALB/NLB is used)
      - Background: Very light green (#E8F5E9) - 10% opacity, subtle tint
      - Border: Green (#4CAF50), 2px solid line - MUST be clearly visible
      - Spacing: 20px padding inside subnet

   B. PRIVATE APPLICATION SUBNET (Middle tier in each AZ):
      - Label: "Private Subnet - Application (10.0.11.0/24)" - simple text, NO emojis
      - Place: EC2 instances (show instance types if specified, e.g., "t3.medium")
      - Place: ECS/EKS clusters and nodes (show as container icons)
      - Place: Lambda functions (if applicable) - show as Lambda icons
      - Place: Auto Scaling Groups (show ASG icon if mentioned)
      - Place: Application Load Balancer (if internal)
      - Background: Very light yellow (#FFF9C4) - 10% opacity, subtle tint
      - Border: Orange (#FF9800), 2px solid line - MUST be clearly visible
      - Show Security Groups as subtle boxes around resource groups (light gray border, 1px)
      - Spacing: 20px padding inside subnet, 20px between components

   C. DATABASE/STORAGE SUBNET (Bottom tier in each AZ):
      - Label: "Private Subnet - Database (10.0.21.0/24)" - simple text, NO emojis
      - Place: RDS instances (show Multi-AZ if mentioned, label primary/standby)
      - Place: DynamoDB (show as global service or regional)
      - Place: ElastiCache/Redis clusters (show primary and replica)
      - Place: DocumentDB, Neptune, or other databases
      - Place: EFS or FSx file systems
      - Background: Very light orange (#FFE0B2) - 10% opacity, subtle tint
      - Border: Red (#F44336), 2px solid line - MUST be clearly visible
      - Show Database Security Groups as subtle boxes
      - Spacing: 20px padding inside subnet, 20px between database components

5. RIGHT COLUMN - Additional Services (Storage, Event Platform, ML Platform, etc.):
   - Place to the RIGHT of the AWS Region box
   - Group related services in CLEARLY DEFINED BOXES
   - Each service group (Storage, Events, ML, etc.) should have its own box
   - Box Border: Medium gray (#666666), 2px solid border - MUST be clearly visible
   - Box Background: Pure white (#FFFFFF)
   - Label each box at the top (e.g., "Storage Services", "Event Platform", "ML Platform")
   - Labels must be bold, 14pt, dark gray (#2D3436)

=== NETWORKING & CONNECTIVITY ===

- Internet Gateway: One per VPC, connect to public subnets with solid line
- NAT Gateway: One per AZ in public subnet, connect to private subnets with arrow
- Route Tables: Show routing paths with labeled arrows
- VPC Peering: If mentioned, show with dashed line between VPCs
- VPN Connection: Show with labeled connection line
- Direct Connect: Show with dedicated connection line
- Security Groups: Show as boxes around resource groups, label with SG names
- Network ACLs: Show at subnet level if mentioned

=== DATA FLOW & CONNECTIONS ===

Use directional arrows with specific conventions:
- Solid green arrows: HTTPS/HTTP traffic (public-facing)
- Solid blue arrows: Internal API calls
- Dashed orange arrows: Database queries
- Dashed purple arrows: Message queue/event flows
- Solid red arrows: Authentication/authorization flows
- Label each arrow with:
  * Protocol (HTTPS, gRPC, MQTT, etc.)
  * Port numbers if critical (443, 80, 3306, etc.)
  * Data type if relevant (API calls, file uploads, etc.)

Flow patterns to show:
- User → CloudFront → WAF → ALB → Application → Database
- External System → API Gateway → Lambda → DynamoDB
- Application → SQS → Lambda → SNS → Application
- Application → ElastiCache (read path)
- Application → RDS (write path)

=== COMPUTE LAYER DETAILS ===

EC2 Instances:
- Show instance icons with type labels (t3.medium, m5.large, etc.)
- Group by Auto Scaling Group if applicable
- Show Launch Templates if mentioned
- Indicate spot instances vs on-demand if specified

Containers (ECS/EKS):
- Show ECS Cluster or EKS Cluster as container
- Show individual service/task definitions
- Show Fargate if serverless containers
- Show ECR (Elastic Container Registry) connection

Lambda Functions:
- Show as serverless function icons
- Group related functions
- Show event sources (API Gateway, S3, SQS, etc.)
- Show VPC configuration if Lambda is in VPC

=== STORAGE & DATABASE DETAILS ===

S3 Buckets:
- Show as storage icons
- Label bucket names if mentioned
- Show lifecycle policies if relevant
- Show cross-region replication if mentioned
- Connect to applications with upload/download arrows

RDS:
- Show primary and standby instances in different AZs
- Show read replicas if mentioned
- Label database engine (PostgreSQL, MySQL, etc.)
- Show connection to application layer

DynamoDB:
- Show as global service or regional
- Show Global Tables if multi-region
- Show DynamoDB Streams if mentioned

ElastiCache:
- Show Redis or Memcached clusters
- Show primary and replica nodes
- Show connection to application layer

=== SECURITY LAYER ===

- IAM Roles: Show as labels on resources (e.g., "EC2 Role", "Lambda Role")
- Security Groups: Visual boxes around resource groups
- Network ACLs: Show at subnet boundaries
- AWS WAF: Show as protection layer
- AWS Shield: Show as DDoS protection
- Secrets Manager: Show connections to applications
- KMS: Show encryption keys and their usage
- VPC Endpoints: Show if private connectivity to AWS services

=== MONITORING & OBSERVABILITY ===

- CloudWatch: Show metrics collection from all resources
- CloudWatch Logs: Show log aggregation
- CloudTrail: Show API logging
- X-Ray: Show distributed tracing if mentioned
- CloudWatch Alarms: Show alerting connections
- SNS Topics: Show notification flows
- EventBridge: Show event routing if mentioned

=== INTEGRATION POINTS ===

- API Gateway: Show REST/HTTP APIs with clear endpoints
- SQS Queues: Show as message queue icons with FIFO/Standard distinction
- SNS Topics: Show as pub/sub notification icons
- EventBridge: Show as event bus
- Step Functions: Show workflow if mentioned
- AppSync: Show GraphQL API if mentioned

=== VISUAL DESIGN STANDARDS - CRITICAL FOR CLEAN DIAGRAMS ===

CLEAN DESIGN PRINCIPLES (MANDATORY):
- ABSOLUTELY NO emojis anywhere in the diagram (no 🌍, 🏗️, 📍, ☁️, etc.)
- NO decorative elements or unnecessary graphics
- Use simple, clean text labels only (e.g., "Public Subnet" not "🌍 Public Subnet")
- Maintain generous white space (minimum 40px between major sections)
- Align all elements to a strict 20px grid
- Avoid overlapping elements completely
- Use minimal, professional color palette with subtle tints
- Keep labels concise and clear (max 20 characters per label)

Layout (Strict Grid System - HORIZONTAL LEFT TO RIGHT):
- Use a strict 20px grid system - all elements align to grid
- HORIZONTAL LEFT-TO-RIGHT flow: External/Edge → AWS Region (with VPC and AZs) → Additional Services
- All major sections arranged in COLUMNS from left to right
- Minimum resolution: 3840x2160 pixels (4K quality) - wider than tall to accommodate horizontal layout
- Aspect ratio: Prefer landscape orientation (width > height)
- Use consistent icon sizes: 64x64px for all AWS service icons
- Maintain 60-80px spacing between major columns (left to right)
- Maintain 20-30px spacing between components within sections
- Use alignment guides - all elements must align perfectly
- Left-align text labels consistently
- Center-align icons within their containers
- No elements should overlap or touch
- All boxes (Region, VPC, AZs, Subnets) must have CLEARLY VISIBLE BORDERS

Colors (AWS Standard Palette - SUBTLE TINTS ONLY):
- Public/Internet-facing: Very light green (#E8F5E9) - 10% opacity, subtle
- Private/Internal: Very light yellow (#FFF9C4) - 10% opacity, subtle
- Database/Storage: Very light orange (#FFE0B2) - 10% opacity, subtle
- Security: Very light red (#FFEBEE) - 10% opacity, subtle
- Management/Global: Light gray (#F5F5F5)
- AWS Region box border: Dark gray (#333333), 3px solid border - MUST be clearly visible
- VPC box border: Medium gray (#666666), 2px solid border - MUST be clearly visible
- VPC box background: Very light gray (#F9F9F9) - subtle tint to distinguish from Region
- AZ box borders: Light gray (#CCCCCC), 2px dashed border - MUST be clearly visible
- Subnet borders: Colored borders (Green/Orange/Red), 2px solid - MUST be clearly visible
- Background: Pure white (#FFFFFF) - ENTIRE diagram background must be white
- Text: Dark gray (#2D3436) or black (#000000)

Typography (Clean, Professional, NO Emojis):
- VPC/Region labels: Bold, 18pt, dark gray (#2D3436), simple text like "VPC" or "AWS Region: us-east-1"
- Subnet labels: Bold, 14pt, dark gray (#2D3436), simple text like "Public Subnet (10.0.1.0/24)"
- Service labels: Regular, 12pt, dark gray (#2D3436), simple text like "EC2 Instance" or "RDS PostgreSQL"
- Connection labels: Regular, 10pt, dark gray (#2D3436), simple text like "HTTPS/443" or "API/8080"
- Font: Arial or Helvetica (sans-serif, professional)
- CRITICAL: NO emojis, NO decorative fonts, NO special characters in labels
- Use plain text: "Public Subnet" not "🌍 Public Subnet"
- Use plain text: "VPC" not "🏗️ VPC"
- Use plain text: "Availability Zone 1" not "📍 AVAILABILITY ZONE 1"

Icons (Official AWS Icons Only):
- Use official AWS Architecture Icons exclusively
- Maintain consistent icon size: 64x64px for all icons
- Group related services visually with subtle background boxes
- Add service name labels below icons (simple text, no emojis)
- Ensure icons are properly aligned and spaced

=== CONTENT COMPLETENESS - CRITICAL ===

MANDATORY INCLUSIONS (DO NOT SIMPLIFY):
- Every AWS service mentioned in the architecture summary MUST be included
- All data flows and connections MUST be shown
- All integration points MUST be visible
- Security boundaries and controls MUST be displayed
- Network topology (subnets, AZs, routing) MUST be detailed
- High availability patterns (Multi-AZ, replication) MUST be shown
- Disaster recovery elements if mentioned MUST be included
- Cost optimization elements (reserved instances, spot) if mentioned MUST be shown

CRITICAL: This must be a COMPREHENSIVE, DETAILED architecture diagram. Do NOT create a simple diagram with only 3-5 components. The architecture summary contains multiple services, layers, and components - ALL of them must be included in the diagram. If the summary mentions:
- Multiple services → Show ALL of them
- VPC with subnets → Show the complete VPC structure with all subnets
- Multiple availability zones → Show ALL AZs
- Security services → Show ALL security layers
- Monitoring services → Show ALL monitoring components
- Storage services → Show ALL storage components
- Compute services → Show ALL compute resources

The diagram must be DETAILED and COMPLETE, not simplified or abstracted.

=== OUTPUT SPECIFICATIONS ===

CRITICAL REQUIREMENTS:
1. Generate a SINGLE high-resolution PNG image file
2. Save the file at this EXACT path: {absolute_output_path}
3. The file MUST be a valid PNG image (not code, not DOT, not text)
4. Resolution: Minimum 1920x1080, preferably 2560x1440 or higher
5. File format: PNG with transparency support
6. Quality: Production-ready for presentations and documentation

DO NOT:
- Generate DOT, Mermaid, PlantUML, or any code format
- Output text descriptions or explanations
- Create multiple files
- Use placeholder text or "TODO" items
- Use emojis or decorative elements anywhere
- Create cluttered or overlapping layouts
- Use bright or neon colors
- Add unnecessary decorative graphics

CRITICAL QUALITY REQUIREMENTS:
- The diagram must be CLEAN and PROFESSIONAL
- The diagram must be COMPREHENSIVE and DETAILED (not simplified)
- All elements must be properly aligned to a grid
- No overlapping components
- Generous white space throughout
- Simple, readable labels (no emojis, no special characters)
- Subtle color tints only (10% opacity backgrounds)
- Clear, professional typography
- Consistent spacing and alignment

FINAL REMINDER - CRITICAL REQUIREMENTS:
- This must be a FULL, DETAILED architecture diagram showing ALL services, components, and layers
- Do NOT create a simple 3-5 component diagram
- Include EVERYTHING mentioned in the architecture summary
- Show complete infrastructure with multiple tiers, subnets, availability zones

LAYOUT REQUIREMENTS (MANDATORY):
- HORIZONTAL LAYOUT: Arrange all major sections LEFT TO RIGHT (not top to bottom)
- WHITE BACKGROUND: Entire diagram background must be pure white (#FFFFFF)
- CLEAR BOXES: All containers MUST have clearly visible borders:
  * AWS Region box: Dark gray border (3px solid) - clearly visible
  * VPC box: Medium gray border (2px solid) - clearly visible, inside Region box
  * AZ boxes: Light gray dashed border (2px) - clearly visible, inside VPC box
  * Subnet boxes: Colored borders (2px solid) - clearly visible, inside AZ boxes
- All boxes must have labels at the top (Region name, VPC name, AZ names, Subnet names)
- Box borders must be thick enough to be clearly visible (minimum 2px)

The diagram must be immediately usable in:
- Architecture reviews with senior stakeholders
- Technical documentation for developers
- Client presentations (executive-level)
- Compliance documentation
- Onboarding materials for new team members
- Printing at high resolution

Generate a comprehensive, detailed, clean, professional, enterprise-grade diagram with HORIZONTAL LAYOUT, WHITE BACKGROUND, and CLEAR BOXES for Region/VPC/AZs now and save it as a PNG image file at: {absolute_output_path}"""


        # Initialize MCP client and agent
        mcp_client = MCPClient(lambda: stdio_client(
            StdioServerParameters(
                command=uvx_path,
                args=["awslabs.aws-diagram-mcp-server"]
            )
        ))
        
        with mcp_client:
            tools = mcp_client.list_tools_sync()
            
            # Configure Bedrock client with increased timeouts
            bedrock_config = Config(
                read_timeout=600,  # 10 minutes for long-running diagram generation
                connect_timeout=60,  # 1 minute connection timeout
                retries={'max_attempts': 3, 'mode': 'adaptive'}
            )
            bedrock_client = boto3.client(
                'bedrock-runtime',
                region_name='us-east-1',
                config=bedrock_config
            )
            
            # Create Bedrock model with timeout configuration
            model = BedrockModel(
                model_id='anthropic.claude-3-sonnet-20240229-v1:0',
                client=bedrock_client
            )
            
            # Create agent with model and tools
            agent = Agent(
                model=model,
                tools=tools,
                max_iterations=10  # Limit iterations to prevent infinite loops
            )
            
            # Generate diagram with timeout handling
            try:
                print("Starting diagram generation (this may take several minutes for complex diagrams)...")
                print("Timeout set to 10 minutes. Please be patient...")
                # Call the agent - it will use the configured model with increased timeouts
                response = agent(diagram_prompt)
                print(f"Agent response received: {str(response)[:200]}...")
            except Exception as e:
                error_msg = str(e).lower()
                if "timeout" in error_msg or "timed out" in error_msg or "read timed out" in error_msg:
                    print(f"Diagram generation timed out: {str(e)}")
                    print("This may happen with very complex diagrams. The summary is still available.")
                    print("Tip: Try simplifying the architecture summary or using a faster model.")
                    return None
                print(f"Diagram generation error: {str(e)}")
                raise
            print(f"Agent response received: {str(response)[:200]}...")
            
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
                
                # Try to convert DOT to PNG if Graphviz is available
                dot_path = shutil.which("dot")
                if dot_path:
                    try:
                        # Convert DOT to PNG
                        png_output = output_path
                        subprocess.run(
                            [dot_path, "-Tpng", str(latest_dot), "-o", str(png_output)],
                            check=True,
                            capture_output=True,
                            timeout=30
                        )
                        if png_output.exists():
                            print(f"Converted DOT to PNG: {png_output}")
                            return str(png_output)
                    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
                        print(f"Failed to convert DOT to PNG: {e}")
                
                # If conversion failed, check if we can return SVG or use the DOT file
                # For now, return None and let the API return the summary
                print("DOT file found but PNG conversion unavailable. Install Graphviz: brew install graphviz")
            
            # Check for image files (PNG, JPG, SVG) - prioritize files matching request ID
            image_files = []
            request_id = output_path.stem.replace('_diagram', '')  # Extract request ID from filename
            
            # Search in multiple directories
            search_dirs = [output_dir]
            if generated_diagrams_dir.exists() and generated_diagrams_dir != output_dir:
                search_dirs.append(generated_diagrams_dir)
            if parent_output_dir != output_dir:
                search_dirs.append(parent_output_dir)
            search_dirs.append(parent_dir)
            
            for search_dir in search_dirs:
                for pattern in ["*.png", "*.jpg", "*.jpeg", "*.svg"]:
                    image_files.extend([f for f in search_dir.glob(pattern) if f.is_file()])
            
            if image_files:
                # Filter to find files matching the request ID first
                matching_files = [f for f in image_files if request_id in f.stem]
                
                if matching_files:
                    # If we have files matching the request ID, use the most recent one
                    latest_image = max(matching_files, key=lambda p: p.stat().st_mtime)
                    print(f"Found matching image file for request {request_id}: {latest_image}")
                    return str(latest_image)
                else:
                    # Fallback to most recently created image overall
                    latest_image = max(image_files, key=lambda p: p.stat().st_mtime)
                    print(f"Found image file (no request ID match): {latest_image}")
                    return str(latest_image)
            
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


def generate_diagram(summary_text: str, output_path: Path) -> Optional[str]:
    """
    Generate architecture diagram using strands and MCP.
    Returns path to generated diagram image or None if failed.
    Diagram generation is optional - if unavailable, returns None gracefully.
    """
    return generate_diagram_with_strands(summary_text, output_path)


@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "Architecture Diagram Generator API", "status": "running"}


@app.post("/api/generate-diagram")
async def generate_architecture_diagram(
    file: UploadFile = File(...),
    aws_region: Optional[str] = Form("us-east-1"),
    bedrock_model_id: Optional[str] = Form("anthropic.claude-3-sonnet-20240229-v1:0")
):
    """
    Upload PDF, extract content, summarize, and generate architecture diagram
    """
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    # Generate unique ID for this request
    request_id = str(uuid.uuid4())
    temp_pdf_path = UPLOAD_DIR / f"{request_id}_{file.filename}"
    
    # Use generated-diagrams subdirectory for better organization
    generated_diagrams_dir = OUTPUT_DIR / "generated-diagrams"
    generated_diagrams_dir.mkdir(exist_ok=True)
    output_diagram_path = generated_diagrams_dir / f"{request_id}_diagram.png"
    
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
        
        # Step 3: Generate diagram
        print(f"Generating architecture diagram...")
        diagram_path = generate_diagram(summary_text, output_diagram_path)
        
        if not diagram_path or not Path(diagram_path).exists():
            # If diagram generation failed, return summary as JSON
            # This is expected if uvx/strands/mcp are not available
            print(f"Diagram generation failed or file not found: {diagram_path}")
            return JSONResponse(
                status_code=200,
                content={
                    "success": False,
                    "message": "Diagram generation unavailable. Architecture summary generated successfully.",
                    "summary": summary_text,
                    "diagram_path": None,
                    "note": "To enable diagram generation, install 'uv' (https://astral.sh/uv) and ensure strands/mcp packages are available."
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
        
        print(f"Returning diagram file: {diagram_path} (size: {file_size} bytes)")
        
        # Return diagram file with cache-busting headers
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


@app.get("/api/diagram/{request_id}")
async def get_diagram(request_id: str):
    """Retrieve a previously generated diagram by request ID"""
    diagram_path = OUTPUT_DIR / f"{request_id}_diagram.png"
    
    if not diagram_path.exists():
        raise HTTPException(status_code=404, detail="Diagram not found")
    
    return FileResponse(diagram_path, media_type="image/png")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

