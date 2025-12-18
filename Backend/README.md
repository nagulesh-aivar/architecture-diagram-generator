# Backend API Server

FastAPI backend server for the Architecture Diagram Generator application.

## Setup

1. Install dependencies:
```bash
cd Backend
pip install -r requirements.txt
```

2. Ensure you have AWS credentials configured for Bedrock access:
   - Set up AWS CLI: `aws configure`
   - Or set environment variables: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`
   - Ensure your AWS account has access to Bedrock and the required models

3. Ensure `uvx` is installed (required for diagram generation):
```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh
```

4. Create a `.env` file in the project root if needed for additional configuration.

## Running the Server

```bash
python main.py
```

The server will start on `http://localhost:8000`

## API Endpoints

### GET `/`
Health check endpoint.

### POST `/api/generate-diagram`
Upload a PDF file to extract content, summarize, and generate an architecture diagram.

**Parameters:**
- `file` (multipart/form-data): PDF file to upload
- `aws_region` (form data, optional): AWS region for Bedrock (default: us-east-1)
- `bedrock_model_id` (form data, optional): Bedrock model ID (default: anthropic.claude-3-sonnet-20240229-v1:0)

**Response:**
- Success: Returns the generated diagram image (PNG)
- Failure: Returns JSON with error message and summary (if available)

### GET `/api/diagram/{request_id}`
Retrieve a previously generated diagram by request ID.

## Directory Structure

- `uploads/`: Temporary storage for uploaded PDF files
- `outputs/`: Generated diagram images

## Notes

- The server uses `pdf_extractor.py` from the parent directory for PDF extraction
- Diagram generation uses the AWS Diagram MCP Server via `strands` and `mcp` (optional)
- **Important**: The `strands` package may fail to build on some systems due to C++ dependencies. If this happens:
  - The API will still work and return the architecture summary
  - Diagram generation will be skipped if `strands`/`mcp` are not available
  - To enable diagram generation, you can try installing `strands` manually or use an alternative approach
- Make sure all dependencies from the parent `requirements.txt` are also installed

## Troubleshooting Diagram Generation

If diagram generation fails:

1. **Check if strands/mcp are installed:**
   ```bash
   python -c "import strands; import mcp; print('OK')"
   ```

2. **If installation fails**, the API will still:
   - Extract PDF content ✓
   - Generate architecture summary ✓
   - Return summary as JSON (diagram generation skipped)

3. **To install strands manually** (if needed):
   ```bash
   # May require additional system dependencies (CMake, C++ compiler, etc.)
   pip install mcp strands
   ```

