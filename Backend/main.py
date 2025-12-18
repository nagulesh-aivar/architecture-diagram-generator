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

        

        diagram_prompt = f"""YOU MUST CREATE A COMPLETE AWS ARCHITECTURE DIAGRAM FOLLOWING AWS OFFICIAL STANDARDS!

CRITICAL AWS STANDARD REQUIREMENTS:
✓ Use OFFICIAL AWS Architecture Icons (2023+ icon set)
✓ Use RECTANGULAR boxes with SHARP CORNERS (NO rounded/curved boxes)
✓ Follow AWS Well-Architected Framework diagram conventions
✓ Use AWS standard colors and styling
✓ Professional enterprise-grade appearance matching AWS documentation

✗ DO NOT use rounded/curved boxes
✗ DO NOT use custom icon styles
✗ DO NOT deviate from AWS standard diagram conventions
✗ DO NOT create flowchart-style diagrams

IMMEDIATE TASK: Use the AWS diagram MCP tools available to you to generate a FULL VISUAL AWS ARCHITECTURE DIAGRAM with:
✓ Official AWS service icons (EC2, RDS, S3, Lambda, etc.) from AWS Architecture Icons
✓ RECTANGULAR container boxes with SHARP CORNERS (AWS Cloud, Region, VPC, AZs, Subnets)
✓ Straight connection arrows showing data flow
✓ Professional labels matching AWS documentation style
✓ Horizontal 16:9 layout (3840×2160 pixels)

STEP 1: ANALYZE the architecture summary below and identify ALL AWS services, components, and data flows.
STEP 2: USE the AWS diagram MCP tool to GENERATE a complete visual diagram following AWS official standards.
STEP 3: ENSURE all boxes are RECTANGULAR with SHARP CORNERS (not rounded).
STEP 4: SAVE the diagram as a PNG to: {absolute_output_path}

You are an expert AWS Solutions Architect creating a COMPREHENSIVE, DETAILED, ENTERPRISE‑GRADE architecture diagram using OFFICIAL AWS ARCHITECTURE DIAGRAM STANDARDS. You MUST follow AWS official diagramming conventions exactly as used in AWS documentation, whitepapers, and Well-Architected Framework materials.

MANDATORY AWS DIAGRAM STANDARDS:
You MUST use the available AWS diagram generation tools to create a diagram that matches AWS official architecture diagrams:

1. OFFICIAL AWS ICONS:
   - Use ONLY official AWS Architecture Icons (latest icon set from AWS Architecture Center)
   - Each AWS service must use its official icon (orange for compute, blue for database, green for storage, purple for network, red for security)
   - Icon size: consistent 64×64 pixels or similar
   - NO custom icons, NO generic shapes for services

2. RECTANGULAR BOXES WITH SHARP CORNERS (CRITICAL):
   - ALL container boxes MUST be RECTANGULAR with SHARP 90-degree CORNERS
   - NO rounded corners, NO curved boxes, NO ellipses, NO circles for containers
   - Box types needed:
     * AWS Cloud: Large rectangular box, dark border (#232F3E), white fill
     * Region: Rectangular box, dashed border, white fill
     * VPC: Rectangular box, solid purple border (#8C4FFF), white fill
     * Availability Zones: Rectangular boxes, dashed light blue border
     * Subnets: Rectangular boxes, solid borders (green for public, cyan for private), light tinted fills
     * Security Groups: Optional thin rectangular overlays
   - All boxes must have SHARP CORNERS (corner radius = 0)

3. AWS STANDARD COLORS:
   - Background: Pure white (#FFFFFF)
   - AWS Cloud border: Dark gray (#232F3E), 2-3px solid
   - Region border: Teal (#00A4A6) or blue, 2px dashed
   - VPC border: Purple (#8C4FFF), 2-3px solid
   - AZ border: Light blue (#147EBA), 2px dashed
   - Public Subnet: Green border (#7AA116), light green fill (#F2F6E8)
   - Private Subnet: Cyan border (#00A4A6), light cyan fill (#E6F6F7)

4. PROFESSIONAL AWS STYLING:
   - Typography: Clean sans-serif (Arial, Amazon Ember, Helvetica)
   - Label placement: Top-left for containers, below/beside icons for services
   - Spacing: Generous whitespace, aligned to grid
   - Lines/Arrows: Straight lines with 90-degree angles or smooth curves (NOT hand-drawn style)
   - Arrow style: Simple solid/dashed lines with standard arrowheads

CRITICAL REQUIREMENTS:
1. CREATE THE ACTUAL DIAGRAM - not just a title, not just text, but a full visual architecture diagram
2. USE OFFICIAL AWS SERVICE ICONS - show proper AWS icons for each service
3. DRAW RECTANGULAR CONTAINERS WITH SHARP CORNERS - NO rounded boxes, follow AWS standards exactly
4. ADD DATA FLOW ARROWS - connect services with clean, professional arrows
5. USE PROPER LAYOUT - horizontal 16:9 format with left-to-right flow
6. MATCH AWS DOCUMENTATION STYLE - the diagram should look like it came from AWS official documentation

ARCHITECTURE SUMMARY TO DIAGRAM:
{summary_text}

========================================
ABSOLUTE STRUCTURAL REQUIREMENTS
========================================

1. MANDATORY LANDSCAPE ORIENTATION - 16:9 HORIZONTAL LAYOUT
   CRITICAL: The diagram MUST be in LANDSCAPE orientation (WIDE, NOT TALL).
   
   - CANVAS SIZE: Use exactly 3840x2160 pixels (width x height) OR 1920x1080 pixels
   - ASPECT RATIO: EXACTLY 16:9 (landscape/horizontal)
   - WIDTH MUST BE GREATER THAN HEIGHT (e.g., 3840 WIDTH  2160 HEIGHT)
   - THIS IS LANDSCAPE: Width=3840, Height=2160 ✓
   - THIS IS WRONG PORTRAIT: Width=2160, Height=3840 ✗
   
   FLOW DIRECTION: LEFT TO RIGHT
   - Data flows HORIZONTALLY from LEFT to RIGHT across the diagram
   - Users/External systems on the LEFT side
   - Edge services (CloudFront, ALB) in the LEFT-CENTER
   - Application services in the CENTER
   - Data services (RDS, S3) on the RIGHT side
   - The architecture MUST flow: LEFT → CENTER → RIGHT
   
   HORIZONTAL ARRANGEMENT:
   - Place external users/clients on the FAR LEFT (outside AWS Cloud)
   - Place edge/ingress services (API Gateway, ALB, CloudFront) in LEFT zone
   - Place compute/application (EC2, ECS, Lambda) in CENTER zone
   - Place data/storage (RDS, DynamoDB, S3) in RIGHT zone
   - Place monitoring/security services along the TOP or BOTTOM edge
   - Availability Zones should be arranged side-by-side HORIZONTALLY, not stacked vertically

2. MANDATORY TOP-LEVEL CONTAINERS (NO EXCEPTIONS)
   You MUST create and clearly show ALL of the following containers as distinct, labeled boxes:

   A. AWS CLOUD CONTAINER (OUTERMOST)
      - REQUIRED: Draw one outermost container labeled exactly "AWS Cloud".
      - This box MUST be visible, clearly bordered, and encompass the entire architecture.
      - It MUST be the single largest bounding box around everything else.
      - This container should span HORIZONTALLY across most of the 16:9 canvas width.

   B. REGION CONTAINER (INSIDE AWS CLOUD)
      - REQUIRED: Draw a single Region container INSIDE the "AWS Cloud" box.
      - Label it clearly, for example: "Region: us-east-1".
      - There must be exactly ONE Region container in this diagram.
      - This Region container MUST sit fully inside "AWS Cloud" and fully outside the VPC.
      - This container should be WIDE (landscape), utilizing the horizontal space.

   C. SINGLE VPC CONTAINER (INSIDE REGION)
      - REQUIRED: Draw exactly ONE VPC container inside the Region container.
      - Label it clearly, for example: "VPC: 10.0.0.0/16".
      - All AZs, subnets, and VPC-scoped resources MUST be inside this single VPC box.
      - There MUST NOT be multiple VPCs unless explicitly described, and even then this diagram still requires at least one clearly labeled primary VPC.
      - The hierarchy MUST be: AWS Cloud → Region → VPC (in that order, with visible nesting).
      - The VPC should be WIDE (landscape), spanning most of the horizontal space.

   CRITICAL: If you generate a diagram that does not show:
   - An OUTERMOST "AWS Cloud" box,
   - A single "Region" box inside that AWS Cloud box, and
   - A single "VPC" box inside that Region box,
   then the diagram is INVALID. You must not produce such a diagram.

3. STRICT CONTAINER HIERARCHY (MANDATORY)
   The COMPLETE hierarchy MUST be:

   1) AWS Cloud (outermost box) - SPANS HORIZONTALLY
   2) Region (inside AWS Cloud) - SPANS HORIZONTALLY
   3) VPC (inside Region) - SPANS HORIZONTALLY
   4) Availability Zones (inside VPC, arranged side-by-side HORIZONTALLY, not vertically)
   5) Subnets (inside each Availability Zone, can be stacked vertically within each AZ)
   6) Auto Scaling Groups (inside subnets if applicable)
   7) Individual resources (inside the appropriate subnet / group)

   No containers may "float" outside their correct parent. No AZ or subnet may exist outside the VPC. No VPC may exist outside the Region. No Region may exist outside AWS Cloud.

4. WHITE BACKGROUND (MANDATORY)
   - The ENTIRE diagram background MUST be pure white (#FFFFFF).
   - There MUST NOT be gradients, patterns, or off-white backgrounds.
   - All containers sit on top of this pure white background.

========================================
COMPREHENSIVE COVERAGE & QUALITY
========================================

CRITICAL COVERAGE:
1. COMPREHENSIVE ARCHITECTURE
   - Include EVERY AWS service, component, resource, integration, security layer, monitoring component, and data store mentioned in {summary_text}.
   - Do NOT create a simplified, high-level “marketing” diagram with only a few components. This MUST be a production-grade, detailed architecture.

2. NO OMISSIONS
   - For each service or feature described in the summary, show its corresponding icon and placement in the architecture.
   - If multiple environments or tiers (edge, web, app, data, analytics, shared services) are mentioned, show all of them.

3. PRODUCTION-READY DETAIL
   - Show multi-AZ, redundancy, failover, and DR patterns where described.
   - Show all key data flows, integration points, and dependencies.
   - Show security controls and monitoring paths.

========================================
CONTAINER DETAILS & COLORS (AWS STANDARD)
========================================

CRITICAL: ALL containers MUST use RECTANGULAR shapes with SHARP 90-degree CORNERS.
NO rounded corners, NO curved edges, NO ellipses. This is AWS standard.

AWS Cloud Container (OUTERMOST)
- Shape: RECTANGLE with SHARP CORNERS (corner radius = 0)
- Label: "AWS Cloud" at top-left
- Border: Dark gray (#232F3E), 2-3px solid, clearly visible
- Background: White (#FFFFFF)
- Contains EVERYTHING else
- MUST be rectangular, not rounded

Region Container (INSIDE AWS Cloud)
- Shape: RECTANGLE with SHARP CORNERS (corner radius = 0)
- Label: "Region: <name>" (e.g., "Region: us-east-1") at top-left
- Border: Teal/Blue (#00A4A6), 2px dashed
- Background: White (#FFFFFF)
- Contains the VPC and all regional/global services drawn in this diagram
- MUST be rectangular, not rounded

VPC Container (INSIDE Region)
- Shape: RECTANGLE with SHARP CORNERS (corner radius = 0)
- Label: "VPC: <CIDR>" (e.g., "VPC: 10.0.0.0/16") at top-left
- Border: Purple (#8C4FFF), 2-3px solid
- Background: White (#FFFFFF)
- Contains all AZs, subnets, and VPC‑scoped resources
- MUST be rectangular, not rounded

Availability Zone Containers (INSIDE VPC)
- Shape: RECTANGLES with SHARP CORNERS (corner radius = 0)
- At least 2 (preferably 2–3) AZs side-by-side horizontally: e.g., "Availability Zone 1A", "Availability Zone 1B", "Availability Zone 1C"
- Border: Light blue (#147EBA), 2px dashed
- Background: White (#FFFFFF)
- Each AZ contains its subnets arranged vertically
- MUST be rectangular, not rounded

Subnet Containers (INSIDE EACH AZ)
- Shape: RECTANGLES with SHARP CORNERS (corner radius = 0)
- Public Subnet:
  - Label: "Public Subnet"
  - Border: Green (#7AA116), 2px solid
  - Background: Very light green (#F2F6E8)
  - Contains NAT Gateway, IGW attachments, public ENIs, and public-facing load balancers if applicable
  - MUST be rectangular, not rounded

- Private Application Subnet:
  - Label: "Private Subnet (Application)" or similar
  - Border: Cyan (#00A4A6), 2px solid
  - Background: Very light cyan (#E6F6F7)
  - Contains ECS services, EC2 application servers, ASGs, etc.
  - MUST be rectangular, not rounded

- Private Database/Storage Subnet:
  - Label: "Private Subnet (Database/Storage)" or similar
  - Border: Cyan (#00A4A6), 2px solid
  - Background: Very light cyan (#E6F6F7)
  - Contains RDS, Aurora, DocumentDB, ElastiCache, and other DB/storage resources
  - MUST be rectangular, not rounded

Auto Scaling Groups (INSIDE Subnets where applicable)
- Shape: RECTANGLE with SHARP CORNERS (corner radius = 0)
- Container label: "Auto Scaling Group – <Role>"
- Border: Orange (#D86613), 2px dashed
- Background: White or transparent
- Contains multiple EC2 or container icons representing scaled instances/tasks
- MUST be rectangular, not rounded

Individual Resources
- Place EC2, ECS, Lambda, RDS, S3, DynamoDB, API Gateway, ALB/NLB, SQS, SNS, EventBridge, Secrets Manager, KMS, WAF, Shield, GuardDuty, Config, CloudTrail, CloudWatch, etc. in their appropriate containers.
- Use OFFICIAL AWS ARCHITECTURE ICONS (from AWS Architecture Icons set), consistent size (approx. 64x64px).
- Icons should be the official AWS service icons with proper colors and styling.
- Provide short, clear labels under or beside each icon.
- Icons are typically square or follow AWS icon standard shapes (NOT rounded boxes around them).

Global / Management Services (INSIDE Region, OUTSIDE VPC)
- Place IAM, CloudTrail, CloudWatch, AWS Config, GuardDuty, Security Hub, etc. along the top of the Region container.
- Arrange them horizontally with icons and labels.
- Use official AWS icons for these services.

External Entities (OUTSIDE AWS Cloud)
- Place users, clients, administrators, external systems, SaaS integrations, and partner services outside the "AWS Cloud" container.
- Use simple icons or shapes (e.g., user icon, computer icon, building icon).
- Connect them via arrows to edge services such as CloudFront, Route 53, API Gateway, ALB, or VPN/Direct Connect.

CRITICAL STYLING REMINDER:
- ALL container boxes MUST be RECTANGLES with SHARP CORNERS (90-degree angles, NO rounding)
- This is non-negotiable for AWS standard diagrams
- If the diagram tool defaults to rounded corners, you MUST override it to use sharp corners
- Set border-radius = 0 or corner-radius = 0 for all container shapes

========================================
NETWORKING & DATA FLOWS
========================================

CRITICAL: HORIZONTAL LEFT-TO-RIGHT FLOW
- The entire architecture MUST flow horizontally from LEFT to RIGHT
- Place components to create a clear left-to-right progression:
  1. LEFT: External users/clients (outside AWS Cloud)
  2. LEFT-CENTER: Edge/Ingress (CloudFront, Route53, API Gateway, ALB, IGW)
  3. CENTER: Application Layer (ECS, EC2, Lambda, ASG)
  4. RIGHT-CENTER: Data processing and caching
  5. RIGHT: Data Storage (RDS, DynamoDB, S3, databases)
- Arrows should predominantly point LEFT → RIGHT showing data flow progression
- Avoid vertical-only layouts; prioritize horizontal arrangement

Networking:
- Internet Gateway:
  - One per VPC, attached to the VPC border.
  - Connect to public subnets.

- NAT Gateway:
  - One per AZ in a Public Subnet (if used).
  - Connect NAT to private subnets with arrows.

- Load Balancers:
  - Place ALBs/NLBs at the edge of the VPC or in public subnets (depending on architecture).
  - Connect them to targets (EC2/ECS, etc.).

- VPC Peering / Transit / VPN / Direct Connect:
  - Show dashed or dedicated lines as appropriate when mentioned in the summary.

Security:
- Show security groups as boxes or overlays around groups of resources or as labels next to them.
- Show Network ACLs at subnet boundaries where relevant.
- Show WAF and Shield in front of CloudFront or ALBs if used.
- Show IAM roles next to resources where important (e.g., “EC2 IAM Role”, “Lambda Execution Role”).
- Show KMS keys and Secrets Manager where encryption and secret retrieval occur.

Data Flows:
- Use directional arrows with consistent meaning:
  - Solid green: Public HTTP/HTTPS traffic (e.g., User → CloudFront → ALB).
  - Solid blue: Internal service-to-service traffic (e.g., App → API → Microservice).
  - Dashed orange: Database queries / data store access.
  - Dashed purple: Messaging/event flows (SQS, SNS, EventBridge, streaming).
  - Solid red: Authentication/authorization flows (Cognito, IdP, IAM integration).

- Label important arrows with:
  - Protocol: HTTPS, HTTP, gRPC, MQTT, etc.
  - Ports: 443, 80, 3306, 5432, etc., when relevant.
  - Purpose: “API Request”, “File Upload”, “Metrics”, “Logs”, etc.

========================================
LAYOUT & DESIGN (16:9, CLEAN)
========================================

Layout (MUST MATCH 16:9):
- Use full width of the 16:9 canvas.
- HORIZONTAL ORIENTATION is mandatory:
  - AWS Cloud fills the canvas.
  - Region inside AWS Cloud, also spanning most of the width.
  - VPC inside Region.
  - AZs side-by-side horizontally within the VPC.
  - Subnets stacked vertically inside each AZ.

Grid and Alignment:
- Align all containers and icons to a consistent grid (e.g., 20px).
- Maintain generous white space (40px+ between major sections, 20–30px within groups).
- No overlapping boxes or icons; no elements touching borders.
- Left-align labels; center icons within containers.

Colors:
- Background: #FFFFFF (pure white) for the full canvas.
- Region border: Dark or teal as specified, clearly visible.
- VPC border: Purple (#8C4FFF), 2px solid.
- AZ border: Light blue (#147EBA), 2px dashed.
- Subnet backgrounds: subtle tints as specified (green/cyan variants).
- Text color: Dark gray (#2D3436) or black (#000000).

Typography:
- Region / VPC labels: Bold, ~18pt.
- Subnet labels: Bold, ~14pt.
- Service labels: Regular, ~12pt.
- Connection labels: Regular, ~10pt.
- Use plain, professional sans-serif font (e.g., Arial, Helvetica).
- NO emojis, NO decorative fonts, NO special characters in labels.

========================================
OUTPUT SPECIFICATIONS (MANDATORY)
========================================

- Output: ONE high‑resolution PNG image file ONLY.
- CRITICAL ASPECT RATIO: EXACTLY 16:9 LANDSCAPE (HORIZONTAL, WIDE format)
  * WIDTH > HEIGHT (e.g., 3840 pixels wide × 2160 pixels high)
  * NOT 9:16 portrait (that would be 2160 wide × 3840 high) ✗
  * MUST BE 16:9 landscape (3840 wide × 2160 high) ✓
- Valid landscape resolutions:
  * PREFERRED: 3840×2160 (width × height)
  * ACCEPTABLE: 1920×1080 (width × height)
  * ACCEPTABLE: 2560×1440 (width × height)
- INVALID portrait resolutions (DO NOT USE):
  * 2160×3840 ✗ (this is portrait 9:16, WRONG)
  * 1080×1920 ✗ (this is portrait 9:16, WRONG)
- Background: Pure white (#FFFFFF).
- File format: PNG (valid image file, not code or text).
- Save to EXACT path: {absolute_output_path}
- The diagram MUST be:
  - CLEAN (no clutter, no overlapping).
  - COMPREHENSIVE (all elements from {summary_text}).
  - PRODUCTION-READY (suitable for senior stakeholders and documentation).
  - HORIZONTAL (landscape, wider than tall, flows LEFT to RIGHT).

DO NOT:
- Produce DOT, Mermaid, PlantUML, or any text-based diagram syntax.
- Output textual description instead of the PNG.
- Use emojis or decorative graphics.
- Change the aspect ratio away from 16:9 LANDSCAPE.
- Create a PORTRAIT (9:16, tall) diagram - it MUST be LANDSCAPE (16:9, wide).
- Omit the AWS Cloud, Region, or VPC containers.
- Simplify the architecture to a small subset of components.
- Make the diagram taller than it is wide.

FINAL REMINDER:
- You MUST show:
  - An outer "AWS Cloud" box (wide, horizontal).
  - A single "Region" box inside it (wide, horizontal).
  - A single "VPC" box inside the Region (wide, horizontal).
  - Multi-AZ arranged HORIZONTALLY (side by side, not stacked).
  - Subnet-level detail, and all services and flows described in {summary_text}.
  - Data flow from LEFT (users/edge) → CENTER (app) → RIGHT (data).
- The canvas MUST be 16:9 LANDSCAPE (e.g., 3840×2160, NOT 2160×3840).
- Pure white background.
- The diagram MUST be detailed, clean, enterprise-grade, and HORIZONTAL.

========================================
ACTION REQUIRED - GENERATE THE DIAGRAM
========================================

STEP-BY-STEP DIAGRAM CREATION PROCESS:

1. IDENTIFY COMPONENTS from the architecture summary:
   - List ALL AWS services: EC2, ECS, Lambda, RDS, S3, DynamoDB, ALB, API Gateway, CloudFront, etc.
   - List all networking components: VPC, subnets, security groups, NAT gateways, internet gateways
   - List all security services: IAM, WAF, Shield, GuardDuty, KMS, Secrets Manager
   - List all monitoring: CloudWatch, CloudTrail, X-Ray
   - List all integrations: SQS, SNS, EventBridge, Step Functions

2. CREATE THE DIAGRAM STRUCTURE (AWS STANDARD SHAPES):
   - Start with AWS Cloud container (outermost RECTANGULAR box with SHARP CORNERS)
   - Add Region container inside AWS Cloud (RECTANGULAR with SHARP CORNERS)
   - Add VPC container inside Region (RECTANGULAR with SHARP CORNERS)
   - Add 2-3 Availability Zones side-by-side horizontally inside VPC (RECTANGULAR with SHARP CORNERS)
   - Add subnets (Public, Private App, Private Data) inside each AZ (RECTANGULAR with SHARP CORNERS)
   - ALL boxes MUST have 90-degree corners, NO rounded corners, NO curved edges

3. PLACE AWS SERVICE ICONS (OFFICIAL AWS ICONS):
   - Use OFFICIAL AWS Architecture Icons from AWS Architecture Icons set
   - Each service gets its official icon: EC2 (orange), RDS (blue), S3 (green), Lambda (orange), etc.
   - Place each identified service in its appropriate subnet/container
   - Size icons consistently (~64x64 pixels)
   - Add descriptive labels under each icon
   - DO NOT put service icons inside rounded boxes - use the official square/rectangular icons directly

4. DRAW CONNECTIONS:
   - Add directional arrows between services showing data flow
   - Use different arrow styles for different types of connections (sync/async, request/response)
   - Label arrows with protocols (HTTPS, gRPC, etc.)

5. APPLY VISUAL STYLING (AWS STANDARD):
   - Set canvas to 3840×2160 (16:9 landscape)
   - Use white background (#FFFFFF)
   - Apply proper colors to containers (as specified above)
   - Ensure proper spacing and alignment
   - CRITICAL: Set corner-radius = 0 or border-radius = 0 for ALL container boxes
   - Use RECTANGULAR shapes with SHARP 90-degree CORNERS throughout
   - Match AWS official documentation diagram style

6. SAVE THE DIAGRAM:
   - Export as high-quality PNG image
   - Save to: {absolute_output_path}

CRITICAL VALIDATION BEFORE SAVING:
- Verify the output is a PNG IMAGE file (not text, not code, not DOT file)
- Verify the image contains VISUAL ELEMENTS (icons, boxes, arrows) not just text
- Verify ALL services from the summary are represented
- Verify the layout is HORIZONTAL (16:9, wider than tall)
- VERIFY ALL CONTAINER BOXES ARE RECTANGULAR WITH SHARP CORNERS (NO rounded/curved boxes)
- Verify boxes match AWS official diagram standards
- Verify official AWS service icons are used (not generic shapes)

NOW EXECUTE: Use the available diagram generation tools to create this complete AWS-standard architecture diagram and save it to the specified path.

FINAL AWS STANDARDS CHECKLIST:
✓ RECTANGULAR containers with SHARP CORNERS (corner-radius = 0)
✓ Official AWS Architecture Icons
✓ AWS standard colors for containers
✓ Professional, clean layout matching AWS documentation
✓ White background
✓ 16:9 landscape orientation
✗ NO rounded corners on containers
✗ NO curved boxes
✗ NO generic/custom icons
"""

        # Initialize MCP client and agent
        mcp_client = MCPClient(lambda: stdio_client(
            StdioServerParameters(
                command=uvx_path,
                args=["awslabs.aws-diagram-mcp-server"]
            )
        ))
        
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
            
            # Generate diagram
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
            # Extract UUID request ID from filename (format: YYYYMMDD_HHMMSS_UUID_diagram.png)
            filename_parts = output_path.stem.split('_')
            # The UUID is typically the 3rd part (after timestamp and time)
            if len(filename_parts) >= 3:
                request_id = filename_parts[2]  # Just the UUID
            else:
                request_id = output_path.stem.replace('_diagram', '')  # Fallback
            
            print(f"Looking for diagram files matching request ID: {request_id}")
            print(f"Expected output path: {output_path}")
            
            # Search in multiple directories (including subdirectories)
            search_dirs = [output_dir]
            if generated_diagrams_dir.exists() and generated_diagrams_dir != output_dir:
                search_dirs.append(generated_diagrams_dir)
            if parent_output_dir != output_dir:
                search_dirs.append(parent_output_dir)
            search_dirs.append(parent_dir)
            
            # Use recursive glob to search subdirectories too
            for search_dir in search_dirs:
                for pattern in ["*.png", "*.jpg", "*.jpeg", "*.svg"]:
                    # Search current directory
                    image_files.extend([f for f in search_dir.glob(pattern) if f.is_file()])
                    # Also search one level deep (for nested generated-diagrams folders)
                    image_files.extend([f for f in search_dir.glob(f"*/{pattern}") if f.is_file()])
            
            print(f"Found {len(image_files)} total image files")
            
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
    
    # Use generated-diagrams subdirectory with timestamp for better organization
    from datetime import datetime
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


@app.get("/api/diagrams")
async def list_diagrams():
    """List all generated diagrams with metadata"""
    try:
        generated_diagrams_dir = OUTPUT_DIR / "generated-diagrams"
        if not generated_diagrams_dir.exists():
            return {"diagrams": []}
        
        diagrams = []
        for file_path in generated_diagrams_dir.glob("*.png"):
            if file_path.is_file():
                stat_info = file_path.stat()
                diagrams.append({
                    "filename": file_path.name,
                    "size": stat_info.st_size,
                    "created": stat_info.st_ctime,
                    "modified": stat_info.st_mtime,
                    "url": f"/api/diagram-file/{file_path.name}"
                })
        
        # Sort by creation time (newest first)
        diagrams.sort(key=lambda x: x["created"], reverse=True)
        
        return {"diagrams": diagrams, "count": len(diagrams)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing diagrams: {str(e)}")


@app.get("/api/diagram-file/{filename}")
async def get_diagram_file(filename: str):
    """Retrieve a specific diagram file by filename"""
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


@app.get("/api/diagram/{request_id}")
async def get_diagram(request_id: str):
    """Retrieve a previously generated diagram by request ID"""
    diagram_path = OUTPUT_DIR / f"{request_id}_diagram.png"
    
    if not diagram_path.exists():
        raise HTTPException(status_code=404, detail="Diagram not found")
    
    return FileResponse(diagram_path, media_type="image/png")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

