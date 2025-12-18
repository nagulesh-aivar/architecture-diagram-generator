# Installation Notes - Diagram Generation Dependencies

## Issue with `strands` Package

The `strands` package requires C++ compilation and may fail to build on some systems with the error:
```
CMake Error: add_subdirectory given source "lib/matslise" which is not an existing directory
```

This is **not a Python version issue** - it's a build system issue with the `strands` package itself.

## Solution

The backend has been updated to handle this gracefully:

1. **`strands` and `mcp` are now optional dependencies**
   - The backend will work without them
   - PDF extraction and summarization will still work
   - Diagram generation will be skipped if these packages aren't available

2. **The API will return the architecture summary** even if diagram generation fails
   - This allows you to use the extracted and summarized content
   - The frontend will display the summary if diagram generation is unavailable

## Installation Options

### Option 1: Install without diagram generation (Recommended for now)
```bash
cd Backend
pip install -r requirements.txt
# This will install everything except strands/mcp
```

The API will work and return summaries, but won't generate diagrams.

### Option 2: Try installing strands manually (Advanced)
If you want to attempt installing `strands`:

1. **Install system dependencies:**
   ```bash
   # macOS
   brew install cmake ninja
   
   # Linux (Ubuntu/Debian)
   sudo apt-get install cmake ninja-build build-essential
   ```

2. **Try installing strands:**
   ```bash
   pip install mcp strands
   ```

3. **If it still fails**, the backend will gracefully fall back to summary-only mode.

### Option 3: Use Docker (Future)
A Docker container with all dependencies pre-built could be created, but that's beyond the current scope.

## Current Status

✅ **Working:**
- PDF extraction
- Architecture summarization via AWS Bedrock
- API endpoints
- Frontend upload and display

⚠️ **Optional:**
- Diagram generation (requires strands/mcp)

## Testing

To test if diagram generation is available:
```bash
python -c "from mcp import stdio_client; from strands import Agent; print('Diagram generation available!')"
```

If this fails, diagram generation will be skipped but the rest of the system works fine.

