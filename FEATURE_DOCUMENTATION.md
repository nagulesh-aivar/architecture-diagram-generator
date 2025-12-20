# Architecture Diagram Generator - Feature Documentation

## Overview

This document describes the enhanced architecture diagram generation system with structured component output and pseudo diagram generation capabilities.

---

## 🎯 New Features

### 1. **Structured Component List**
A hierarchical, well-organized list of all architecture components with their relationships, types, and descriptions.

**Features:**
- Categorized by function (Compute, Storage, Network, Security, etc.)
- Clear component relationships and dependencies
- Type-based color coding
- Collapsible/expandable categories
- Total component count

**Access:** 
- From Gallery: Click "Components" button on any diagram card
- From Main Page: Click "Component List" button after generating a diagram

### 2. **Pseudo Diagram Description**
A text-based diagram definition using Mermaid syntax, ready to paste into diagramming tools.

**Features:**
- Mermaid flowchart syntax (LR layout)
- Complete component representation
- Data flow arrows with labels
- Grouped components (subgraphs)
- Copy-to-clipboard functionality
- Download as text file
- Links to recommended visualization tools

**Access:**
- From Gallery: Click "Pseudo" button on any diagram card
- From Main Page: Click "Pseudo Diagram" button after generating a diagram

---

## 🏗️ Architecture Design

### Backend Architecture

#### **Data Models**

```python
# Component representation
class ComponentItem(BaseModel):
    name: str
    type: str  # compute, storage, network, security, monitoring, integration, database
    description: str
    relationships: List[str]  # Related component names

class ComponentCategory(BaseModel):
    category: str
    components: List[ComponentItem]

class ComponentListResponse(BaseModel):
    project_name: str
    summary: str
    categories: List[ComponentCategory]
    total_components: int

# Pseudo diagram representation
class PseudoDiagramResponse(BaseModel):
    project_name: str
    diagram_type: str  # e.g., "mermaid"
    description: str
    syntax: str  # Full diagram syntax
```

#### **Service Layer**

**Location:** `/Backend/main.py`

1. **`extract_component_list(summary_text, aws_region, model_id)`**
   - Uses AWS Bedrock (Claude) to parse architecture summary
   - Generates structured JSON with components and relationships
   - Returns `ComponentListResponse` object
   - Handles errors gracefully with fallback structure

2. **`generate_pseudo_diagram(summary_text, aws_region, model_id)`**
   - Uses AWS Bedrock (Claude) to create Mermaid syntax
   - Generates left-to-right flowchart representation
   - Includes subgraphs for logical grouping
   - Returns `PseudoDiagramResponse` object

#### **API Endpoints**

1. **`GET /api/component-list/{request_id}`**
   - Retrieves component list for a specific diagram
   - Returns structured JSON with categories and components
   - Requires valid request_id from diagram generation

2. **`GET /api/pseudo-diagram/{request_id}`**
   - Retrieves pseudo diagram syntax for a specific diagram
   - Returns Mermaid syntax ready for visualization
   - Requires valid request_id from diagram generation

3. **`GET /api/diagrams`** (Enhanced)
   - Now includes `request_id` in response
   - Enables navigation to component list and pseudo diagram

4. **`POST /api/generate-diagram`** (Enhanced)
   - Stores request data in memory for later retrieval
   - Returns `X-Request-ID` header for tracking

#### **Request Storage**

```python
# In-memory storage (production: use database)
request_storage: Dict[str, Dict[str, Any]] = {
    "request_id": {
        "summary": "Architecture summary text",
        "aws_region": "us-east-1",
        "model_id": "anthropic.claude-3-sonnet-20240229-v1:0",
        "timestamp": "20251220_143000",
        "filename": "original_file.pdf"
    }
}
```

---

### Frontend Architecture

#### **New Components**

1. **`ComponentList.tsx`**
   - **Route:** `/component-list/:requestId`
   - **Features:**
     - Fetches component data from backend
     - Displays hierarchical component structure
     - Color-coded component types
     - Expandable/collapsible categories
     - Home navigation button
     - Links to Pseudo Diagram and Gallery

2. **`PseudoDiagram.tsx`**
   - **Route:** `/pseudo-diagram/:requestId`
   - **Features:**
     - Fetches pseudo diagram syntax from backend
     - Displays syntax in code-style textarea
     - Copy-to-clipboard functionality
     - Download as text file
     - Usage instructions
     - Links to visualization tools (Mermaid Live, draw.io, Lucidchart)
     - Home navigation button
     - Links to Component List and Gallery

#### **Enhanced Components**

1. **`Gallery.tsx`** (Updated)
   - Added "Components" and "Pseudo" buttons to each diagram card
   - Displays buttons only for diagrams with valid request_id
   - Maintains existing Download and View functionality

2. **`App.tsx`** (Updated)
   - Stores request_id from response headers
   - Displays Component List and Pseudo Diagram buttons after generation
   - Buttons appear alongside Download button

#### **Routing**

```typescript
// main.tsx
<Routes>
  <Route path="/" element={<App />} />
  <Route path="/gallery" element={<Gallery />} />
  <Route path="/component-list/:requestId" element={<ComponentList />} />
  <Route path="/pseudo-diagram/:requestId" element={<PseudoDiagram />} />
</Routes>
```

---

## 🔄 User Flow

### Primary Flow (New Diagram)

1. **Upload PDF** → Main page
2. **Generate Diagram** → Processing
3. **View Results** → Three buttons appear:
   - Download Diagram (PNG)
   - Component List (Structured view)
   - Pseudo Diagram (Mermaid syntax)

### Gallery Flow (Existing Diagram)

1. **Navigate to Gallery** → View all diagrams
2. **Select a diagram** → See diagram card with buttons:
   - Download (PNG file)
   - View (Open in new tab)
   - Components (Navigate to Component List)
   - Pseudo (Navigate to Pseudo Diagram)

### Navigation

- **Home Icon:** Present on Component List and Pseudo Diagram pages
- **Back to Gallery:** Available on both new pages
- **Cross-navigation:** Component List ↔ Pseudo Diagram

---

## 🛠️ Technical Implementation Details

### State Management

**App.tsx:**
```typescript
const [requestId, setRequestId] = useState<string | null>(null)

// After successful diagram generation
const rid = response.headers.get('X-Request-ID')
if (rid) {
  setRequestId(rid)
}
```

**ComponentList.tsx & PseudoDiagram.tsx:**
```typescript
const { requestId } = useParams<{ requestId: string }>()

useEffect(() => {
  fetchComponentList() // or fetchPseudoDiagram()
}, [requestId])
```

### Error Handling

- **404 Errors:** Request ID not found or data not available
- **500 Errors:** Backend processing failures
- **Graceful Degradation:** Fallback structures for parsing errors
- **User Feedback:** Clear error messages with retry options

### Data Persistence

**Current Implementation:**
- In-memory storage using `request_storage` dictionary
- Data persists only during backend runtime
- Suitable for development and testing

**Production Recommendation:**
- Replace with database (PostgreSQL, MongoDB, DynamoDB)
- Store summary, region, model_id, timestamp
- Enable historical component list/pseudo diagram retrieval

---

## 📊 Component Type Color Coding

```typescript
const typeColors = {
  compute: '#FF9900',      // Orange
  storage: '#3B48CC',      // Blue
  database: '#3B48CC',     // Blue
  network: '#7AA116',      // Green
  security: '#DD344C',     // Red
  monitoring: '#146EB4',   // Dark Blue
  integration: '#9C83C9',  // Purple
}
```

---

## 🎨 Design Principles

### 1. **Consistency**
- All pages follow the same design language
- Purple accent color (#9C83C9) throughout
- Consistent button styles and interactions
- Unified card layouts

### 2. **Clarity**
- Clear visual hierarchy
- Readable typography
- Intuitive navigation
- Descriptive labels and icons

### 3. **Extensibility**
- Modular component structure
- Reusable service functions
- Type-safe interfaces
- Easy to add new diagram formats

### 4. **Accessibility**
- Semantic HTML
- Keyboard navigation support
- High contrast text
- Descriptive alt text and aria labels

---

## 🚀 Future Enhancements

### Backend
1. **Database Integration**
   - Persistent storage of request data
   - Historical component list retrieval
   - User session management

2. **Export Formats**
   - PDF export of component lists
   - Multiple diagram syntaxes (PlantUML, DOT, etc.)
   - CSV export of component data

3. **AI Improvements**
   - Fine-tuned prompts for better component extraction
   - Relationship inference from architecture patterns
   - Automated diagram layout optimization

### Frontend
1. **Interactive Features**
   - Search/filter components
   - Highlight component relationships
   - Interactive pseudo diagram editor
   - Real-time preview of Mermaid syntax

2. **Collaboration**
   - Share component lists via link
   - Export to team tools (Confluence, Notion)
   - Comments and annotations

3. **Visualization**
   - Inline Mermaid rendering
   - Component dependency graph
   - Architecture comparison view

---

## 🧪 Testing

### Manual Testing Checklist

#### Backend
- [ ] Component list generation with various architectures
- [ ] Pseudo diagram generation with different complexity levels
- [ ] Error handling for invalid request IDs
- [ ] Request storage and retrieval

#### Frontend
- [ ] Navigation from Gallery to Component List
- [ ] Navigation from Gallery to Pseudo Diagram
- [ ] Home button navigation from new pages
- [ ] Copy-to-clipboard functionality
- [ ] Download pseudo diagram as text
- [ ] Responsive design on mobile/tablet
- [ ] Error states and retry functionality

#### Integration
- [ ] End-to-end flow: Upload → Generate → View Components
- [ ] End-to-end flow: Upload → Generate → View Pseudo Diagram
- [ ] Cross-navigation between Component List and Pseudo Diagram
- [ ] Request ID tracking throughout the flow

---

## 📝 API Examples

### Get Component List

**Request:**
```bash
GET http://localhost:8000/api/component-list/a1b2c3d4-5678-90ab-cdef-1234567890ab
```

**Response:**
```json
{
  "project_name": "E-Commerce Platform",
  "summary": "Cloud-native e-commerce platform with microservices architecture",
  "categories": [
    {
      "category": "Compute & Application",
      "components": [
        {
          "name": "ECS Service",
          "type": "compute",
          "description": "Containerized application services running on ECS Fargate",
          "relationships": ["RDS Database", "ElastiCache", "S3 Bucket"]
        }
      ]
    }
  ],
  "total_components": 15
}
```

### Get Pseudo Diagram

**Request:**
```bash
GET http://localhost:8000/api/pseudo-diagram/a1b2c3d4-5678-90ab-cdef-1234567890ab
```

**Response:**
```json
{
  "project_name": "E-Commerce Platform",
  "diagram_type": "mermaid",
  "description": "Architecture flow showing user requests through edge services to application and data layers",
  "syntax": "graph LR\n    subgraph External\n        Users((Users))\n    end\n    ..."
}
```

---

## 🔧 Configuration

### Backend Environment Variables
```bash
AWS_REGION=us-east-1
BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0
```

### Frontend Environment Variables
```bash
VITE_API_BASE_URL=http://localhost:8000
```

---

## 📚 Dependencies

### Backend (Python)
- `fastapi` - Web framework
- `boto3` - AWS SDK
- `pydantic` - Data validation
- `uvicorn` - ASGI server

### Frontend (TypeScript/React)
- `react` - UI framework
- `react-router-dom` - Routing
- `vite` - Build tool
- `typescript` - Type safety

---

## ✅ Completion Checklist

- [x] Backend data models defined
- [x] Service layer functions implemented
- [x] API endpoints created and tested
- [x] Frontend ComponentList page created
- [x] Frontend PseudoDiagram page created
- [x] Gallery page updated with navigation buttons
- [x] Main page updated with navigation buttons
- [x] Home icon navigation added to new pages
- [x] Routing configured
- [x] Error handling implemented
- [x] Code documentation added
- [x] Feature documentation created

---

## 📞 Support

For questions or issues related to these features, refer to:
- Backend code: `/Backend/main.py`
- Frontend components: `/Frontend/src/ComponentList.tsx`, `/Frontend/src/PseudoDiagram.tsx`
- API documentation: This file

---

**Last Updated:** December 20, 2024
**Version:** 2.0.0

