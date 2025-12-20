# System Architecture Diagram

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER INTERFACE (React)                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐    ┌─────────────┐    ┌──────────────┐   ┌─────────────┐│
│  │   App.tsx    │    │ Gallery.tsx │    │ ComponentList│   │PseudoDiagram││
│  │   (Home)     │◄───┤  (Gallery)  ├───►│   .tsx       │◄─►│   .tsx      ││
│  │              │    │             │    │              │   │             ││
│  │ Upload PDF   │    │ View All    │    │ Structured   │   │ Mermaid     ││
│  │ Generate     │    │ Diagrams    │    │ Components   │   │ Syntax      ││
│  └──────┬───────┘    └──────┬──────┘    └──────┬───────┘   └──────┬──────┘│
│         │                   │                   │                  │        │
└─────────┼───────────────────┼───────────────────┼──────────────────┼────────┘
          │                   │                   │                  │
          │                   │                   │                  │
          ▼                   ▼                   ▼                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            API LAYER (FastAPI)                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  POST /api/generate-diagram                                                 │
│  ├─ Upload PDF                                                              │
│  ├─ Extract content                                                         │
│  ├─ Summarize with Bedrock                                                  │
│  ├─ Generate diagram image                                                  │
│  └─ Return: Image + Request ID                                              │
│                                                                              │
│  GET /api/diagrams                                                          │
│  └─ Return: List of diagrams with metadata + request_id                     │
│                                                                              │
│  GET /api/component-list/{request_id}                                       │
│  ├─ Retrieve stored summary                                                 │
│  ├─ Call extract_component_list()                                           │
│  └─ Return: ComponentListResponse (JSON)                                    │
│                                                                              │
│  GET /api/pseudo-diagram/{request_id}                                       │
│  ├─ Retrieve stored summary                                                 │
│  ├─ Call generate_pseudo_diagram()                                          │
│  └─ Return: PseudoDiagramResponse (JSON)                                    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
          │                                              │
          │                                              │
          ▼                                              ▼
┌──────────────────────────────────┐    ┌──────────────────────────────────┐
│     SERVICE LAYER (Python)       │    │   REQUEST STORAGE (In-Memory)    │
├──────────────────────────────────┤    ├──────────────────────────────────┤
│                                  │    │                                  │
│ extract_component_list()         │    │ request_storage: Dict[str, Dict] │
│ ├─ Bedrock API call              │    │                                  │
│ ├─ Parse JSON response           │◄───┤ Key: request_id                 │
│ └─ Return ComponentListResponse  │    │ Value:                           │
│                                  │    │   - summary                      │
│ generate_pseudo_diagram()        │    │   - aws_region                   │
│ ├─ Bedrock API call              │    │   - model_id                     │
│ ├─ Parse JSON response           │    │   - timestamp                    │
│ └─ Return PseudoDiagramResponse  │    │   - filename                     │
│                                  │    │                                  │
└──────────────────────────────────┘    └──────────────────────────────────┘
          │
          │
          ▼
┌──────────────────────────────────┐
│      AWS BEDROCK (Claude)        │
├──────────────────────────────────┤
│                                  │
│ - Architecture summarization     │
│ - Component extraction           │
│ - Mermaid syntax generation      │
│ - Low temperature (0.1) for      │
│   deterministic outputs          │
│                                  │
└──────────────────────────────────┘
```

---

## Data Flow Diagram

### Flow 1: Diagram Generation
```
User → Upload PDF
  ↓
Backend: Extract content → Summarize (Bedrock) → Generate diagram (MCP)
  ↓
Store request data (summary, region, model_id) in memory
  ↓
Return: PNG image + request_id (in headers)
  ↓
Frontend: Display image + Show navigation buttons
```

### Flow 2: Component List Generation
```
User → Click "Component List"
  ↓
Frontend: Navigate to /component-list/{request_id}
  ↓
Backend: GET /api/component-list/{request_id}
  ├─ Retrieve summary from request_storage
  ├─ Call extract_component_list(summary)
  │   └─ Bedrock: Parse architecture → Extract components
  └─ Return: ComponentListResponse (JSON)
  ↓
Frontend: Display hierarchical component list
```

### Flow 3: Pseudo Diagram Generation
```
User → Click "Pseudo Diagram"
  ↓
Frontend: Navigate to /pseudo-diagram/{request_id}
  ↓
Backend: GET /api/pseudo-diagram/{request_id}
  ├─ Retrieve summary from request_storage
  ├─ Call generate_pseudo_diagram(summary)
  │   └─ Bedrock: Generate Mermaid syntax
  └─ Return: PseudoDiagramResponse (JSON)
  ↓
Frontend: Display Mermaid syntax with copy/download options
```

---

## Component Interaction Diagram

```
┌────────────────────────────────────────────────────────────────────────────┐
│                          FRONTEND COMPONENTS                                │
└────────────────────────────────────────────────────────────────────────────┘
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        │                           │                           │
        ▼                           ▼                           ▼
┌───────────────┐          ┌───────────────┐          ┌───────────────┐
│   App.tsx     │          │  Gallery.tsx  │          │ ComponentList │
│               │          │               │          │    .tsx       │
│ State:        │          │ State:        │          │               │
│ - selectedFile│          │ - diagrams[]  │          │ State:        │
│ - diagramUrl  │          │ - loading     │          │ - data        │
│ - requestId   │◄─────────┤ - error       │◄─────────┤ - loading     │
│ - uploading   │   Link   │               │   Link   │ - error       │
│ - error       │          │ Actions:      │          │               │
│               │          │ - fetch()     │          │ Actions:      │
│ Actions:      │          │ - navigate()  │          │ - fetch()     │
│ - handleUpload│          │               │          │ - toggleCat() │
└───────┬───────┘          └───────┬───────┘          └───────┬───────┘
        │                          │                          │
        │                          │                          │
        │                          │                          │
        ▼                          ▼                          ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                             API ENDPOINTS                                   │
│                                                                             │
│  POST /api/generate-diagram                                                │
│  GET  /api/diagrams                                                        │
│  GET  /api/component-list/{request_id}                                     │
│  GET  /api/pseudo-diagram/{request_id}                                     │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## Routing Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        REACT ROUTER (main.tsx)                          │
└─────────────────────────────────────────────────────────────────────────┘
        │
        ├─── Route: /
        │    └─── Component: <App />
        │         ├─── Upload PDF
        │         ├─── Generate Diagram
        │         └─── Navigation: Gallery, Component List, Pseudo Diagram
        │
        ├─── Route: /gallery
        │    └─── Component: <Gallery />
        │         ├─── List all diagrams
        │         ├─── Download, View
        │         └─── Navigation: Home, Component List, Pseudo Diagram
        │
        ├─── Route: /component-list/:requestId
        │    └─── Component: <ComponentList />
        │         ├─── Fetch component data
        │         ├─── Display hierarchical structure
        │         └─── Navigation: Home, Gallery, Pseudo Diagram
        │
        └─── Route: /pseudo-diagram/:requestId
             └─── Component: <PseudoDiagram />
                  ├─── Fetch Mermaid syntax
                  ├─── Copy/Download functionality
                  └─── Navigation: Home, Gallery, Component List
```

---

## State Management Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          APPLICATION STATE                              │
└─────────────────────────────────────────────────────────────────────────┘
        │
        ├─── App State (App.tsx)
        │    ├─── selectedFile: File | null
        │    ├─── diagramUrl: string | null
        │    ├─── requestId: string | null          ← NEW
        │    ├─── uploading: boolean
        │    ├─── error: string | null
        │    ├─── awsRegion: string
        │    └─── bedrockModelId: string
        │
        ├─── Gallery State (Gallery.tsx)
        │    ├─── diagrams: Diagram[]
        │    │    └─── Diagram { filename, size, url, request_id }  ← NEW
        │    ├─── loading: boolean
        │    └─── error: string | null
        │
        ├─── ComponentList State (ComponentList.tsx)        ← NEW COMPONENT
        │    ├─── data: ComponentListData | null
        │    ├─── loading: boolean
        │    ├─── error: string | null
        │    └─── expandedCategories: Set<string>
        │
        └─── PseudoDiagram State (PseudoDiagram.tsx)        ← NEW COMPONENT
             ├─── data: PseudoDiagramData | null
             ├─── loading: boolean
             ├─── error: string | null
             └─── copied: boolean
```

---

## Error Handling Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         ERROR HANDLING STRATEGY                         │
└─────────────────────────────────────────────────────────────────────────┘

Backend:
  ├─── Service Layer
  │    ├─── Try: Bedrock API call
  │    └─── Catch: Return fallback structure
  │         └─── ComponentListResponse with error message
  │         └─── PseudoDiagramResponse with error message
  │
  ├─── API Endpoints
  │    ├─── 404: Request ID not found
  │    ├─── 500: Processing error
  │    └─── 200: Success with data or fallback
  │
  └─── Validation
       ├─── Pydantic models
       └─── Type checking

Frontend:
  ├─── Network Errors
  │    └─── Display error message + retry button
  │
  ├─── Loading States
  │    └─── Show spinner during fetch
  │
  ├─── Data Validation
  │    └─── TypeScript interfaces
  │
  └─── User Feedback
       ├─── Error banners
       ├─── Retry mechanisms
       └─── Navigation fallbacks
```

---

## Security & Performance Considerations

### Security
```
├─── Input Validation
│    ├─── PDF file type check
│    ├─── Request ID validation
│    └─── Pydantic model validation
│
├─── CORS Configuration
│    └─── Restricted to localhost:3000 (dev)
│
└─── No Sensitive Data Exposure
     └─── Request IDs are UUIDs, not predictable
```

### Performance
```
├─── Lazy Loading
│    └─── Images loaded on-demand in Gallery
│
├─── Caching Strategy
│    ├─── Cache-Control headers: no-cache
│    └─── Fresh data on every request
│
├─── Efficient State Management
│    └─── useState for local state only
│
└─── Optimized Rendering
     ├─── Conditional rendering
     └─── Key props for lists
```

---

## Deployment Architecture (Production)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         PRODUCTION DEPLOYMENT                           │
└─────────────────────────────────────────────────────────────────────────┘

Frontend:
  ├─── Build: npm run build
  ├─── Output: /dist
  └─── Deploy: S3 + CloudFront or Vercel

Backend:
  ├─── Container: Docker
  ├─── Server: Uvicorn (ASGI)
  └─── Deploy: ECS Fargate or EC2

Storage (Recommended):
  ├─── Replace in-memory storage
  └─── Options:
       ├─── DynamoDB (serverless)
       ├─── PostgreSQL (relational)
       └─── MongoDB (document store)

API Gateway:
  ├─── ALB or API Gateway
  └─── SSL/TLS termination

Monitoring:
  ├─── CloudWatch Logs
  ├─── Application metrics
  └─── Error tracking (Sentry, DataDog)
```

---

**Architecture designed for:**
- ✅ Scalability
- ✅ Maintainability
- ✅ Extensibility
- ✅ Performance
- ✅ Security
- ✅ User Experience

**Ready for production deployment.**

