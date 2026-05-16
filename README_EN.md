# 🎨 StoryCanvas — Free-Canvas Narrative Creation System

> **Place, connect, and organize narrative elements on a canvas. AI helps transform your structure into high-quality prose.**
> Suitable for: Novels · Screenplays · Epic World-Building
> Comparable scope: World of Warcraft · A Song of Ice and Fire · Re:Zero

---

## Interface Preview

> 📸 **Screenshot Guide**: The following are placeholder screenshot positions. Replace the image paths after taking screenshots.

### 1. Canvas Editor — Core Workspace

![Canvas Editor](docs/screenshots/canvas-overview.png)
*Canvas editor overview: narrative blocks on the left canvas, four-dimension progress bar at the top, chapter ruler at the bottom for scene snapping*

### 2. Add Block Menu

![Add Block Menu](docs/screenshots/add-block-menu.png)
*Click the "+" button in the top-right corner to open the grouped menu with 33 block types organized by Character/World/Structure/Relationship categories*

### 3. Block Editing & AI Generation

![Block Editor](docs/screenshots/block-editor.png)
*Click any block to open the right-side editor, fill in fields or click "🤖 Generate by Condition" to let AI auto-fill, supports writing generation conditions*

### 4. Connection Operations

![Connection Picker](docs/screenshots/connection-picker.png)
*After dragging a line from one block to another, an 8-type connection selector pops up (Causal/Sequential/Parallel/Foreshadow/Resolve/Contain/Conflict/Influence)*

### 5. Writing Panel & Audit

![Writing Panel](docs/screenshots/writing-panel.png)
*Writing panel selects chapter outline blocks, generates outlines/prose, audit mode displays 12-dimension structured issue list*

### 6. Block Pool Management

![Block Pool](docs/screenshots/block-pool.png)
*Block pool stores blocks not on the canvas, can filter by category and search, click "📌" to place back on canvas*

### 7. Story Card Selection

![Story Card Picker](docs/screenshots/story-card-picker.png)
*When creating a project, a 35-card story card picker pops up; select main card + overlay secondary cards to auto-build initial canvas structure*

### 8. LLM Configuration

![Model Settings](docs/screenshots/llm-settings.png)
*Supports 6 providers: DeepSeek/OpenAI/Claude/Gemini/Ollama/Custom, one-click connection test*

---

## Table of Contents

- [User Guide](#user-guide)
- [Project Overview](#project-overview)
- [System Architecture](#system-architecture)
- [Tech Stack](#tech-stack)
- [Backend Structure](#backend-structure)
- [Frontend Structure](#frontend-structure)
- [Database Schema](#database-schema)
- [API Endpoints](#api-endpoints)
- [LLM Providers](#llm-providers)
- [Block Types (35)](#block-types-35)
- [Story Card System (11)](#story-card-system-11)
- [Five-Layer Agent Writing Pipeline](#five-layer-agent-writing-pipeline)
- [Three-Layer Save Mechanism](#three-layer-save-mechanism)
- [Export & Import](#export--import)
- [Style Signature System](#style-signature-system)
- [Configuration](#configuration)
- [Quick Start](#quick-start)
- [Project Structure](#project-structure)

---

## User Guide

### 🚀 Quick Start

```
Create Project → Select Story Card → Add Blocks/Connections → Configure Model → Generate Prose
```

### 1. Create a Project

| Step | Action |
|------|--------|
| ① | Open `http://localhost:5173`, click **"New Project"** |
| ② | Enter project name and genre (e.g., Fantasy, Sci-Fi, Mystery) |
| ③ | After creation, the **Story Card Picker** pops up; select a main card to start |

> If you skip story cards, you can always click the **"Story Cards"** button at the top to re-select later.

### 2. Add Blocks

Click the **"+"** button in the top-right corner of the canvas to expand the grouped menu:

| Group | Block Types |
|-------|-------------|
| **Character** | Character, Personality, Growth Arc, Backstory, Current State, Info Boundary, Omniscient Layer |
| **World** | Worldview, Faction, Rule Constraint, World Development, Timestamp |
| **Narrative Structure** | Timeline, Scene, Event, Goal, Conflict, Turning Point, Hook, Foreshadow, Surprise |
| **Relationship** | Character Relationship, Faction Relationship |
| **Expression** | Atmosphere, Emotion Target, Rhythm, Theme Statement, Lens |
| **Screenplay** | Scene Heading, Action Line, Dialogue, Visual Motif |
| **Special** | Reader Emotion Curve |

After clicking a block type, the block appears on the canvas. Click the block to open the right-side editor and fill in fields.

### 3. Create Connections

Drag from the right side of one block to the left side of another, then release to show the **connection type selector**:

| Connection Type | Meaning | Color |
|-----------------|---------|-------|
| Causal | A causes B to happen | `#666` Gray |
| Sequential | A happens before B | `#999` Light Gray |
| Parallel | A and B happen simultaneously | `#4A90D9` Blue |
| Foreshadow | A hints at B's occurrence | `#F39C12` Orange (animated) |
| Resolve | A resolves B's suspense | `#50C878` Green |
| Contain | A contains B | `#333` Dark Gray |
| Conflict | A conflicts with B | `#E74C3C` Red |
| Influence | A influences B's development | `#9370DB` Purple |

**Connection Examples**: Character → Goal (causal line), Character → Conflict (conflict line), Hook → Scene (foreshadow line)

### 4. Edit Blocks

Click any block to open the editor panel on the right. Different block types show different fields:

- **Character Block**: Name, External Goal, Inner Desire, Fatal Flaw, Personality, Appearance, etc.
- **Scene Block**: Title, Scene Goal, Emotion Target, Tension Level, Scene Content, etc.
- **Worldview Block**: World Name, Core Rules, Cosmology, Power System, etc.
- Other block types come with dedicated fields; some fields have dropdown selections

Auto-saves after editing. The completeness indicator (green/yellow/red) on the block's top-left updates in real-time.

### 5. View Modes

Switch canvas display mode from the top dropdown:

| Mode | Display Content |
|------|----------------|
| **Overview** | All blocks and connections |
| **Character Focus** | Only character-type blocks (Character/Personality/Growth/Backstory/State/Info Boundary/Relationship) |
| **Timeline Mode** | Only temporal blocks (Timeline/Scene/Event, etc.) |
| **Foreshadow Tracking** | Only foreshadow-related blocks (Hook/Foreshadow/Surprise) |
| **Progress Mode** | Overview + progress bar highlight |
| **Screenplay Mode** | Only screenplay blocks (Scene Heading/Action Line/Dialogue/Visual Motif) |

### 6. LLM Settings

Click the **"🤖 Model"** button at the top to configure the AI writing engine:

| Provider | Description | Configuration |
|----------|-------------|---------------|
| **DeepSeek** | Available in China, cost-effective | API Key, Model Selection |
| **OpenAI** | GPT series models | API Key, Model, API URL |
| **Claude** | Anthropic series | API Key, Model, API URL |
| **Gemini** | Google series | API Key, Model |
| **Ollama** | Local, free | Service URL, Model (can refresh local list) |
| **Custom** | Any OpenAI-compatible API | API URL, API Key, Model Name |

Supports **one-click connection test** to confirm configuration is correct.

### 7. Generate Prose

Click the **"Writing Panel"** button at the top:

1. **Select Chapter** — Choose the chapter to generate from the chapter list
2. **Generate Outline** — AI generates chapter outline based on canvas blocks
3. **Generate Prose** — SSE streaming output of complete chapter
4. **Optional Instructions** — Can fill in additional writing instructions

> Before generating, you can improve the fields of related blocks on the canvas. Higher completeness leads to better generation quality.

### 8. Progress & Tracking

**Progress Bar** (top of canvas):
- Four dimensions: World Layer / Character Layer / Structure Layer / Tension Layer
- Overall Controllability + Quality Description (e.g., "Drafting" → "Publishable")

**Narrative Tracking** (click **"📊 Track"**):
- **Foreshadow Tracking** — Which hooks/foreshadows have been set but not resolved
- **Character Arcs** — Growth arc status for each character
- **Relationship Network** — Various relationships between characters
- **Timeline** — Multi-thread narrative timeline view
- **Info Boundary** — Detect if characters know information they shouldn't

### 9. Save & Snapshots

| Level | Method | Description |
|-------|--------|-------------|
| L1 Real-time Save | Automatic | Every edit writes to DB immediately, green dot status |
| L2 Auto Snapshot | Every 15 minutes | Auto-created in background, keeps latest 20 |
| L3 Checkpoint | Manual | Click ⏱ button to create milestone snapshot |

### 10. Export & Import

**Export** (click **"📤 Export"**):
- `.storycanvas` — Full project backup (including all data)
- `canvas.json` — Canvas structure only
- `Markdown` — Full book text

**Import**:
- Drag `.storycanvas` / `canvas.json` / `PNG` files onto the canvas
- Or click "📤 Export" → select file to import
- Preview confirmation dialog appears before import

### 💡 Creative Tips

```
Beginner: Select story card → Add characters and scenes → Simple connections → Try generating
Advanced: Freely build canvas → Refine block fields → Multiple generation iterations
Expert: Full customization → Fine-tune each layer → Combine with audit revisions
```

StoryCanvas is an AI-assisted narrative creation system with a **free canvas** at its core. It's not a linear writing tool, but a spatial story-building environment — authors place, connect, and organize narrative elements on the canvas, and the system transforms the structure into AI-understandable writing context, ultimately generating high-quality prose.

### Core Design Philosophy

| Principle | Description |
|-----------|-------------|
| **Progressive Scaffold Removal** | Beginners see guidance, veteran authors see freedom; the same system auto-adapts |
| **Block Independence** | Each block carries its own state, doesn't depend on other blocks |
| **Always Generatable** | The progress bar is a quality predictor, not a barrier — even a single block can generate |
| **Canvas is the Director's Desk** | Users make director decisions, AI does the execution |
| **Layered World State** | Omniscient Layer (author) / Character Layer / Reader Layer, maintained independently |

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                       Canvas Layer                                   │
│   React Flow Canvas · 35 Block Renders · 8 Connection Types ·       │
│   Story Card Expansion                                               │
├─────────────────────────────────────────────────────────────────────┤
│                       State Layer                                    │
│   Zustand Store · Canvas Node/Edge State · Project Data ·           │
│   UI State · Progress Calculation                                    │
├─────────────────────────────────────────────────────────────────────┤
│                       API Layer                                      │
│   FastAPI · Project CRUD · Block CRUD · Connection Management ·      │
│   Generation Trigger · Snapshot Management · Export/Import ·         │
│   Settings Management · Connection Test                              │
├─────────────────────────────────────────────────────────────────────┤
│                     Narrative Engine                                  │
│   Context Aggregator · Block Translator · Outline Generator ·        │
│   Consistency Checker · Style Signature System                       │
├─────────────────────────────────────────────────────────────────────┤
│                       Pipeline Layer                                  │
│   Architect Agent → Writer Agent → Validator → Auditor Agent →       │
│   Revisor Agent                                                      │
│                                                                      │
│                       Writeback                                       │
│   Write settlement results back to canvas: update character state /  │
│   foreshadows / relationships / world snapshot                       │
├─────────────────────────────────────────────────────────────────────┤
│                       LLM Abstraction Layer                           │
│   DeepSeek · OpenAI · Claude · Gemini · Ollama · Custom Compatible   │
└─────────────────────────────────────────────────────────────────────┘
```

### Data Flow

```
Canvas Block Data (JSON)
    │
    ├─→ Render Layer: React Flow node/edge rendering
    │
    ├─→ Persistence Layer: SQLite (projects/blocks/connections/chapters/canvas_layout/snapshots)
    │
    └─→ Context Aggregator (ContextAggregator):
            ↓
         Collect related blocks by chapter
            ↓
         to_context() structured output
            ↓
         Inject writing prompts (including style signature)
            ↓
         Agent pipeline generation (Architect→Writer→Validator→Auditor→Revisor)
            ↓
         Result writeback → Update block state (Writeback)
```

---

## Tech Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Canvas Engine | React Flow | ^11.11.3 |
| Frontend Framework | React + TypeScript | ^18.3.1 |
| State Management | Zustand + Immer | ^4.5.4 |
| Build Tool | Vite | ^5.4.2 |
| Backend Framework | FastAPI (Python) | ≥0.100.0 |
| Database | SQLite (WAL mode) | - |
| AI Protocol | OpenAI Compatible / Anthropic / Google Gemini / Ollama | - |
| Streaming Response | SSE (Server-Sent Events) via sse-starlette | - |
| HTTP Client | httpx (async) | ≥0.25.0 |

---

## Backend Structure

### Directory Tree

```
backend/
├── main.py                          # FastAPI app entry, route registration, health check
├── requirements.txt                 # Python dependencies
│
├── core/                            # Core modules
│   ├── config.py                    # Config loading (.env + llm_settings.json)
│   ├── database.py                  # SQLite connection management, 6-table DDL
│   ├── models.py                    # Pydantic request/response models
│   └── snapshot.py                  # Snapshot engine (auto/checkpoint/rollback/cleanup/integrity)
│
├── api/                             # RESTful API routes
│   ├── projects.py                  # Project CRUD + progress query + story card application
│   ├── blocks.py                    # Block CRUD + batch create/move
│   ├── connections.py               # Connection CRUD + AI-suggested connections
│   ├── canvas.py                    # Canvas layout query/save
│   ├── generate.py                  # SSE streaming generation (outline/prose/block content)
│   ├── export_import.py             # .storycanvas export/import + canvas.json + Markdown
│   └── snapshots_api.py             # Snapshot management (list/create/rollback/delete/integrity)
│
├── narrative/                       # Narrative engine
│   ├── aggregator.py                # Context aggregator (collect blocks by chapter)
│   ├── translator.py                # Block → prompt translation + style signature injection
│   ├── progress.py                  # Completeness calculation + categorized progress bar
│   └── validator.py                 # Info boundary detection (zero-LLM rules)
│
├── pipeline/                        # Writing pipeline (five-layer Agent)
│   ├── architect.py                 # Architect Agent
│   ├── writer.py                    # Writer Agent (streaming)
│   ├── auditor.py                   # Auditor Agent
│   ├── revisor.py                   # Revisor Agent
│   └── writeback.py                 # Settlement writeback
│
├── llm/                             # LLM abstraction layer
│   ├── base.py                      # BaseLLM abstract base class + create_llm() factory
│   ├── openai_compat.py             # OpenAI compatible protocol (DeepSeek / OpenAI / Custom)
│   ├── claude.py                    # Anthropic Claude API
│   ├── gemini.py                    # Google Gemini API
│   ├── ollama.py                    # Ollama local models
│   └── deepseek.py                  # (Legacy, replaced by openai_compat)
│
├── story_cards/                     # Story card system
│   ├── cards.json                   # 35 story card definitions (A-G categories)
│   └── cards.py                     # Story card loader
│
└── data/                            # Runtime data
    ├── storycanvas.db               # SQLite database file
    └── llm_settings.json            # LLM settings persistence (saved via Web UI)
```

### Core Module Descriptions

#### `config.py`
- Loads default configuration from `.env` file
- Loads runtime configuration from `data/llm_settings.json` saved via Web UI (higher priority than `.env`)
- Provides `Settings` singleton with configuration attributes for 6 LLM providers
- `get_settings_dict()` / `update_settings()` for API read/write

#### `database.py`
- 6 tables: `projects`, `blocks`, `connections`, `chapters`, `canvas_layout`, `snapshots`
- WAL mode + foreign key constraints
- `_migrate_add_column()` for safe migration of new fields

#### `snapshot.py`
- Auto snapshots triggered every 15 minutes (keeps latest 20)
- Checkpoints created manually by users (permanently retained)
- Auto-creates "pre-rollback backup" snapshot on rollback
- Full write: all blocks + connections + layout + chapters

---

## Frontend Structure

### Directory Tree

```
frontend/
├── index.html                       # HTML entry
├── package.json                     # npm dependencies
├── tsconfig.json                    # TypeScript config
├── vite.config.ts                   # Vite config (with API proxy to :8767)
│
└── src/
    ├── main.tsx                     # React entry
    ├── App.tsx                      # Main component (routing/state/layout/import-export/drag)
    │
    ├── i18n/                        # Internationalization
    │   ├── index.ts                 # t() function and language switching logic
    │   ├── useT.ts                  # useT hook for component-level translation
    │   ├── zh.ts                    # Chinese language pack
    │   └── en.ts                    # English language pack
    │
    ├── store/                       # Zustand state management
    │   ├── canvasStore.ts           # Canvas state (nodes/edges/viewport/viewMode)
    │   ├── projectStore.ts          # Project data (CRUD API wrapper)
    │   └── uiStore.ts               # UI state (panels/modals/Toast)
    │
    ├── api/                         # API call layer
    │   ├── blocks.ts                # Project/block/connection/canvas layout/progress/story card API
    │   ├── generate.ts              # SSE streaming generation client
    │   ├── settings.ts              # LLM settings API
    │   ├── snapshots.ts             # Snapshot management API
    │   └── export_import.ts         # Export/import API
    │
    ├── types/                       # TypeScript type definitions
    │   ├── blocks.ts                # 35 block types + 8 connection types + color mapping
    │   └── canvas.ts                # View modes + story cards + progress data
    │
    ├── canvas/                      # Canvas core
    │   ├── CanvasView.tsx           # Main canvas component (React Flow + progress bar + chapter axis)
    │   ├── nodes/                   # Block rendering components
    │   │   ├── BaseBlock.tsx        # Generic block (universal render for 35 types)
    │   │   ├── CharacterBlock.tsx   # Character block (with want/need/fatal_flaw)
    │   │   ├── SceneBlock.tsx       # Scene block (with tension bar/emotion target)
    │   │   └── index.ts             # Node type exports
    │   └── overlays/
    │       └── ProgressBar.tsx      # Four-dimension progress bar component
    │
    ├── panels/                      # Side panels
    │   ├── BlockEditor.tsx          # Block editor (dynamic field display by type)
    │   ├── BlockPoolPanel.tsx       # Block pool panel (filter/search/pin to canvas)
    │   ├── StoryCardPicker.tsx      # Story card picker (category display + main/secondary card overlay)
    │   ├── WritingPanel.tsx         # Writing panel (outline/prose generation + SSE streaming)
    │   ├── LLMSettingsModal.tsx     # LLM settings (6 provider configurations)
    │   ├── SnapshotHistoryPanel.tsx # Snapshot history panel (checkpoint/auto snapshot/rollback/delete)
    │   ├── ImportDialog.tsx         # Import dialog (text extraction/JSON/Dramatica-Flow)
    │   └── LanguageSwitcher.tsx     # Language switcher (Chinese/English)
    │
    └── styles/
        └── index.css                # Global styles (dark theme)
```

### Core Component Descriptions

#### `App.tsx`
- **State Management**: Project selection, creation, export, import drag-and-drop, and other global operations
- **Header**: Logo, project name, save status indicator (green/yellow/red dot), tab switching (canvas/writing), view mode selection, action buttons (export/story cards/writing/model/new)
- **Layout**: Canvas or writing panel as main body, block editor/writing panel/history panel on the right
- **Drag Import**: Listens for `dragover/drop` events, detects `.storycanvas` / `.json` / `.png` files

---

## Database Schema

### `projects`

| Field | Type | Description |
|-------|------|-------------|
| id | TEXT PK | UUID |
| title | TEXT NOT NULL | Project name |
| genre | TEXT | Genre (Fantasy, Sci-Fi, etc.) |
| style_signature | TEXT | JSON: Style signature configuration |
| story_cards | TEXT | JSON: Applied story card IDs |
| created_at / updated_at | TEXT | Timestamps |

### `blocks`

| Field | Type | Description |
|-------|------|-------------|
| id | TEXT PK | UUID |
| project_id | TEXT FK | Parent project |
| type | TEXT NOT NULL | Block type (35 types) |
| canvas_x / canvas_y | REAL | Canvas position |
| canvas_w | REAL | Block width |
| on_canvas | INTEGER | 1=on canvas, 0=in pool |
| collapsed | INTEGER | Collapse state |
| color | TEXT | Custom color |
| timeline_id | TEXT | Timeline association |
| chapter_pos | TEXT | Chapter position |
| completeness | REAL | Completeness 0.0~1.0 |
| tags | TEXT | JSON: Tag array |
| notes | TEXT | Notes |
| content | TEXT | JSON: Block-specific content fields |
| is_draft | INTEGER | Draft flag |
| created_at / updated_at | TEXT | Timestamps |

### `connections`

| Field | Type | Description |
|-------|------|-------------|
| id | TEXT PK | UUID |
| project_id | TEXT FK | Parent project |
| from_id | TEXT FK | Source block |
| to_id | TEXT FK | Target block |
| conn_type | TEXT NOT NULL | Connection type (8 types) |
| label | TEXT | Optional text annotation |
| chapter_hint | TEXT | Associated chapter hint |
| created_at | TEXT | Creation time |

**conn_type enum**: `causes` · `follows` · `parallels` · `foreshadows` · `resolves` · `contains` · `conflicts` · `influences`

### `chapters`

| Field | Type | Description |
|-------|------|-------------|
| id | TEXT PK | UUID |
| project_id | TEXT FK | Parent project |
| chapter_num | INTEGER NOT NULL | Chapter number |
| title | TEXT | Chapter title |
| timeline_id | TEXT | Timeline |
| outline | TEXT | AI-generated outline |
| content | TEXT | Prose content |
| audit_result | TEXT | JSON: Audit result |
| status | TEXT | planned/outlined/generated/approved/imported |
| word_count | INTEGER | Word count |
| block_refs | TEXT | JSON: Block IDs used during generation |
| special_links | TEXT | JSON: Outline special connection lines |
| created_at / updated_at | TEXT | Timestamps |

### `canvas_layout`

| Field | Type | Description |
|-------|------|-------------|
| project_id | TEXT PK FK | Project ID |
| viewport_x / viewport_y | REAL | Canvas viewport position |
| zoom | REAL | Zoom level |
| timeline_y | TEXT | JSON: {timeline_id: y coordinate} |
| updated_at | TEXT | Update time |

### `snapshots`

| Field | Type | Description |
|-------|------|-------------|
| id | TEXT PK | UUID |
| project_id | TEXT FK | Parent project |
| snapshot_type | TEXT NOT NULL | "auto" or "checkpoint" |
| label | TEXT | User-defined checkpoint name |
| blocks_json | TEXT NOT NULL | Full JSON snapshot of all blocks |
| connections_json | TEXT NOT NULL | Full JSON of all connections |
| canvas_layout_json | TEXT | Canvas viewport and layout |
| chapters_json | TEXT | All chapter prose snapshot |
| created_at | TEXT NOT NULL | Creation time |
| word_count | INTEGER | Total word count at snapshot |
| block_count | INTEGER | Block count at snapshot |

---

## API Endpoints

### System

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Health check |

### Project Management

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/projects` | List projects |
| POST | `/api/projects` | Create project |
| GET | `/api/projects/{id}` | Project details (with all blocks and connections) |
| PUT | `/api/projects/{id}` | Update project info |
| DELETE | `/api/projects/{id}` | Delete project |
| GET | `/api/projects/{id}/progress` | Get progress bar data (4 dimensions + overall) |
| POST | `/api/projects/{id}/apply-story-cards` | Apply story cards to project |
| GET | `/api/projects/{id}/export` | Export full Markdown (legacy) |
| GET | `/api/projects/{id}/narrative-tracking` | Narrative tracking data (foreshadows/character arcs) |

### Story Cards

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/story-cards` | Get all story card definitions |
| GET | `/api/story-cards/{id}` | Get single story card details |

### Block CRUD

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/projects/{id}/blocks` | Get all blocks (supports ?type= and ?timeline_id= filters) |
| POST | `/api/projects/{id}/blocks` | Create block |
| GET | `/api/projects/{id}/blocks/{bid}` | Get single block |
| PUT | `/api/projects/{id}/blocks/{bid}` | Update block (auto-recalculate completeness) |
| DELETE | `/api/projects/{id}/blocks/{bid}` | Delete block (cascade delete connections) |
| POST | `/api/projects/{id}/blocks/batch` | Batch create blocks |
| PUT | `/api/projects/{id}/blocks/batch-move` | Batch move blocks (for selection drag) |

### Connection Management

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/projects/{id}/connections` | Get all connections |
| POST | `/api/projects/{id}/connections` | Create connection |
| PUT | `/api/projects/{id}/connections/{cid}` | Update connection |
| DELETE | `/api/projects/{id}/connections/{cid}` | Delete connection |
| GET | `/api/projects/{id}/connections/suggest` | AI-suggested connections (heuristic rules) |

### Canvas Layout

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/projects/{id}/canvas-layout` | Get canvas layout |
| PUT | `/api/projects/{id}/canvas-layout` | Save canvas layout |

### AI Generation (SSE Streaming)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/projects/{id}/generate/chapter-outline` | Generate chapter outline |
| POST | `/api/projects/{id}/generate/chapter-content` | Generate chapter prose (five-layer Agent pipeline) |
| POST | `/api/projects/{id}/generate/block-content` | AI-assisted block content fill |

### Snapshot Management

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/projects/{id}/snapshots` | Get all snapshots (supports ?type= filter) |
| POST | `/api/projects/{id}/snapshots` | Manually create checkpoint |
| POST | `/api/projects/{id}/snapshots/{sid}/restore` | Rollback to snapshot |
| DELETE | `/api/projects/{id}/snapshots/{sid}` | Delete snapshot |
| GET | `/api/projects/{id}/integrity` | Check database integrity |

### Export/Import

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/projects/{id}/export/full` | Export .storycanvas file (ZIP) |
| GET | `/api/projects/{id}/export/canvas-json` | Export canvas.json |
| GET | `/api/projects/{id}/export/markdown` | Export full Markdown |
| POST | `/api/projects/import/preview` | Import preview (no DB write) |
| POST | `/api/projects/import` | General import entry |

### Settings

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/settings` | Get system settings (API keys masked) |
| PUT | `/api/settings` | Update system settings |
| GET | `/api/settings/ollama-models` | Get Ollama local model list |
| POST | `/api/settings/test-connection` | Test LLM connection |

---

## LLM Providers

The system supports 6 LLM providers, configurable via Web UI or `.env`.

| Provider | Identifier | Implementation | API Format | Config Fields |
|----------|-----------|---------------|------------|---------------|
| **DeepSeek** | `deepseek` | `OpenAICompatibleProvider` | OpenAI compatible (v1/chat/completions) | api_key, model, base_url |
| **OpenAI** | `openai` | `OpenAICompatibleProvider` | OpenAI compatible | api_key, model, base_url |
| **Claude** | `claude` | `ClaudeProvider` | Anthropic Messages API (v1/messages) | api_key, model, base_url |
| **Gemini** | `gemini` | `GeminiProvider` | Google streamGenerateContent | api_key, model |
| **Ollama** | `ollama` | `OllamaProvider` | Ollama Chat API (api/chat) | base_url, model |
| **Custom** | `custom` | `OpenAICompatibleProvider` | OpenAI compatible | api_key, model, base_url |

### Connection Details
- All requests to LLM use `httpx.AsyncClient` (async HTTP)
- Streaming generation uses SSE (Server-Sent Events)
- Timeout: OpenAI compatible 180s, Claude 180s, Gemini 180s, Ollama 300s
- Temperature: Generation 0.8, Audit 0.0

### Web UI Settings
Open the settings modal via the header "🤖 Model" button:
- Switch providers (6 options)
- Select preset models (including Ollama local model refresh)
- Custom model name input
- Fill in API Key and API URL
- One-click connection test (`/api/settings/test-connection`)
- Settings persist to `data/llm_settings.json`

---

## Block Types (35)

Each block has a specific color on the canvas and belongs to a specific category in the progress bar.

### Character (7 types) — Category: character

| Type | Identifier | Canvas Color | Key Fields |
|------|-----------|-------------|------------|
| Character Base | `CHARACTER` | `#4A90D9` Blue | name, want, need, fatal_flaw, appearance, voice_style, information_boundary |
| Personality | `PERSONALITY` | `#6BA3D6` Light Blue | core_values, behavior_patterns, triggers, dramatica_function |
| Growth | `GROWTH` | `#5B9BD5` Medium Blue | arc_type, start_state, end_state, keystone_moments, emotional_arc |
| Backstory | `BACKSTORY` | `#4472C4` Dark Blue | origin, formative_events, secrets |
| Current State | `CURRENT_STATE` | `#70B0D8` Sky Blue | location, physical, psychological, active_goals |
| Info Boundary | `INFORMATION_BOUNDARY` | `#2E75B6` Indigo | confirmed_knowledge, suspected, wrongly_believes, dramatic_irony |
| Omniscient Layer | `OMNISCIENT_LAYER` | `#FFD700` Gold (unique) | true_facts, reader_reveal_plan, never_reveal_to_characters |

### World (5 types) — Category: world

| Type | Identifier | Canvas Color | Key Fields |
|------|-----------|-------------|------------|
| Worldview | `WORLDVIEW` | `#7B68EE` Purple | world_name, fundamental_rules, cosmology, power_system, hidden_layer |
| Faction | `FACTION` | `#9370DB` Deep Purple | name, ideology, goal, real_goal, resources, weakness |
| Rule Constraint | `RULE_CONSTRAINT` | `#8A2BE2` Violet | rule_name, scope, mechanism, loopholes, dramatic_use |
| World Development | `WORLD_DEVELOPMENT` | `#A78BFA` Lavender | power_balance, active_conflicts, recent_changes, faction_states |
| Timestamp | `TIMESTAMP` | `#C4B5FD` Light Purple | story_time, timeline_id, chapter_range, simultaneous_events |

### Structure (9 types) — Category: structure

| Type | Identifier | Canvas Color | Key Fields |
|------|-----------|-------------|------------|
| Timeline | `TIMELINE` | User-defined | timeline_name, timeline_type(main/branch/dead/parallel/flashback), status |
| Scene | `SCENE` | `#50C878` Green | title, scene_goal, emotion_target, tension_level, draft_content, generated_content |
| Event | `EVENT` | `#3CB371` Dark Green | what_happens, event_type, cause, immediate/long_term_effects |
| Goal | `GOAL` | `#90EE90` Light Green | surface_goal, deep_goal, obstacle, stakes, progress |
| Conflict | `CONFLICT` | `#E74C3C` Red | conflict_type, root_cause, escalation_chapters, resolution_type |
| Turning Point | `TURNING_POINT` | `#FF6B6B` Coral | turning_type(inciting_incident/midpoint/climax), before/after_state |
| Hook | `HOOK` | `#E8873A` Orange | hook_type, plant_chapter, payoff_chapter, urgency_level, status |
| Foreshadow | `FORESHADOW` | `#F39C12` Gold Orange | foreshadow_type, planted_in, payoff_in, subtlety_level, status |
| Surprise | `SURPRISE` | `#FF8C00` Dark Orange | surprise_type, setup_chapters, trigger_chapter, consequence |

### Relationship (2 types) — Category: tension

| Type | Identifier | Canvas Color | Key Fields |
|------|-----------|-------------|------------|
| Character Relationship | `RELATIONSHIP` | `#FF69B4` Pink | relationship_type, intensity(-100~+100), dynamic, evolution, information_asymmetry |
| Faction Relationship | `FACTION_RELATION` | `#DB7093` Rose | surface_relation, real_relation, intensity, current_flashpoint |

### Expression (5 types) — Category: tension

| Type | Identifier | Canvas Color | Key Fields |
|------|-----------|-------------|------------|
| Atmosphere | `ATMOSPHERE` | `#708090` Slate Gray | sensory(visual/sound/smell/tactile), mood, symbolic_elements |
| Emotion Target | `EMOTION_TARGET` | `#778899` Gray-Blue | reader_emotion_goal, character_emotion, tension_curve, avoid |
| Rhythm | `RHYTHM` | `#808080` Medium Gray | pace, sentence_style, dialogue_density, chapter_role |
| Theme Statement | `THEME_STATEMENT` | `#696969` Dim Gray | theme, how_expressed, avoid_preaching |
| Lens | `LENS` | `#2F4F4F` Dark Gray-Green | shot_sequence, camera_movement, color_grading_note |

### Screenplay (4 types)

| Type | Identifier | Canvas Color | Key Fields |
|------|-----------|-------------|------------|
| Scene Heading | `SCENE_HEADING` | `#1C1C1C` Near Black | interior_exterior, location, time_of_day |
| Action Line | `ACTION_LINE` | `#333333` Dark Gray | content, visual_subtext |
| Dialogue | `DIALOGUE` | `#555555` Medium Dark Gray | exchanges(character/line/subtext), alternatives |
| Visual Motif | `VISUAL_MOTIF` | `#404040` Dim Gray | first_appearance, recurrence_chapters, symbolic_meaning |

### Special (1 type) — Category: world

| Type | Identifier | Canvas Color | Key Fields |
|------|-----------|-------------|------------|
| Reader Emotion Curve | `READER_EMOTION_CURVE` | `#FFA500` Orange-Gold | scope, curve_points[{chapter, emotion, intensity}], design_note, ai_use |

### Progress Bar Category Weights

| Category | Included Block Types |
|----------|---------------------|
| **World** (world) | WORLDVIEW(0.3), FACTION(0.2), RULE_CONSTRAINT(0.2), WORLD_DEVELOPMENT(0.2), TIMESTAMP(0.1) |
| **Character** (character) | CHARACTER(0.3), PERSONALITY(0.15), GROWTH(0.15), BACKSTORY(0.1), CURRENT_STATE(0.1), INFORMATION_BOUNDARY(0.1), OMNISCIENT_LAYER(0.1) |
| **Structure** (structure) | SCENE(0.2), TIMELINE(0.15), EVENT(0.15), GOAL(0.1), CONFLICT(0.1), TURNING_POINT(0.1), HOOK(0.1), FORESHADOW(0.05), SURPRISE(0.05) |
| **Tension** (tension) | RELATIONSHIP(0.2), FACTION_RELATION(0.15), READER_EMOTION_CURVE(0.3), EMOTION_TARGET(0.2), RHYTHM(0.15) |

### Completeness Calculation Rules

Each block type's `completeness` is calculated based on field fill status with weighted scoring (0.0~1.0). For example:

```python
COMPLETENESS_RULES = {
    "CHARACTER": {"name": 0.30, "want": 0.20, "need": 0.20, "fatal_flaw": 0.15, "surface_personality": 0.15},
    "SCENE":     {"title": 0.20, "scene_goal": 0.30, "characters_present": 0.20, "emotion_target": 0.30},
    "WORLDVIEW": {"world_name": 0.10, "fundamental_rules": 0.40, "power_system": 0.30, "tone": 0.20},
    # ... other block types
}
```

---

## Story Card System (35)

Story cards are the entry point for new users. After selecting a card, the system automatically expands preset blocks and connections on the canvas, and users fill in and adjust based on the skeleton.

### 7 Categories (35 Cards Total)

| Category | ID | Story Cards | Difficulty |
|----------|-----|------------|------------|
| Goal-Driven | A | Hero's Journey / Revenge Narrative / Power Struggle / Rescue Mission / Defy Destiny | Beginner~Intermediate |
| Relationship-Driven | B | Dual Growth / Love Triangle / Family Epic / Ensemble Cast / Civilizational Dialogue | Intermediate~Expert |
| Revelation-Driven | C | Mystery / Identity Reveal / Historical Truth / World of Lies / Mythological Archaeology | Intermediate~Expert |
| Survival-Driven | D | Post-Apocalyptic / Systemic Oppression / Isekai Adaptation / Game Rules / Multi-Species Coexistence | Intermediate~Expert |
| Growth-Driven | E | Underdog Rise / Cognitive Shift / Redemption Arc / Cost of Growth / Anti-Hero Arc | Beginner~Advanced |
| World-Driven | F | Civilizational Conflict / Era Transition / Myth Retelling / Multi-Thread Weave / Millennial Epic / Pantheon System | Advanced~Expert |
| Special Structure | G | Nested Narrative / Unreliable Narrator / Parallel Universe / Chronicle | Advanced~Expert |

### Story Card Data Structure

```json
{
  "id": "F4",
  "name": "Multi-Thread Weave",
  "category": "F",
  "description": "Multiple timelines in parallel, character information asymmetry...",
  "difficulty": "advanced",
  "reference_works": ["Re:Zero", "Cloud Atlas"],
  "auto_blocks": {
    "required": [{ "type": "OMNISCIENT_LAYER", "canvas": { "x": 100, "y": 100 } }, ...],
    "recommended": [{ "type": "INFORMATION_BOUNDARY", "canvas": { "x": 500, "y": 300 } }, ...]
  },
  "auto_connections": [{ "from_type": "OMNISCIENT_LAYER", "to_type": "TIMELINE", "conn_type": "contains" }],
  "progress_weights": { "OMNISCIENT_LAYER": 0.20, ... },
  "writing_prompt_modifier": "This is a multi-thread narrative work. AI writing must: ..."
}
```

### Overlay Rules
- Multiple story cards can be used in combination
- System auto-merges block lists (deduplicated)
- Same-type required blocks retain the one with higher completeness

---

## Five-Layer Agent Writing Pipeline

The complete flow when generating a chapter:

```
Snapshot Backup (automatic)
    ↓
① Architect Agent
    Input: Chapter outline + full context (aggregator output)
    Output: Writing blueprint (per-scene writing instructions: opening/conflict/character trajectory/emotion curve/foreshadow operations)
    ↓
② Writer Agent
    Input: Writing blueprint + style signature
    Output: Chapter prose + post-writing settlement table (character position/emotion/relationship/foreshadow changes)
    ↓
③ Post-Writer Validator — Zero-LLM, pure rules
    Checks: Word count / forbidden words / info boundary violations
    If issues found → spot-fix
    ↓
④ Auditor Agent — temperature=0
    Audit dimensions:
    - Info Boundary: Did a character say/know something they shouldn't?
    - Causal Consistency: Are chapter events coherent with prior causes?
    - Character OOC: Does behavior match personality settings?
    - Foreshadow Omission: Should resolved foreshadows be resolved?
    - Style Consistency: Does it match the style signature?
    Critical issues → Revisor Agent → Re-audit (max 2 rounds)
    ↓
⑤ Writeback
    Write settlement table results back to canvas:
    - Update character CURRENT_STATE block
    - Update FORESHADOW/HOOK block status
    - Update RELATIONSHIP block intensity
    - Create chapter WORLD_DEVELOPMENT snapshot
    - Mark "generated" on the chapter's scene block
```

---

## Three-Layer Save Mechanism

| Level | Name | Trigger | Retention | Purpose |
|-------|------|---------|-----------|---------|
| L1 | Real-time Incremental Save | Every block operation writes to SQLite immediately | Permanent (current state) | Prevent single-operation loss |
| L2 | Session Auto Snapshot | Every 15 minutes in background | Keep latest 20 | Prevent crash loss |
| L3 | User Checkpoint | User manually marks | Permanent (user-managed) | Version milestone rollback |

### Frontend Save Status Indicator

- ● **Green Dot** "Saved" — All persistence complete
- ○ **Gray Spinning** "Saving..." — Writing to DB
- ● **Red Dot** "Save Failed" — Block write failure (click for details/retry)

---

## Export & Import

### `.storycanvas` File Format

`.storycanvas` is a ZIP archive that fully restores when dragged in:

```
project.storycanvas
├── metadata.json              # Project info + version + statistics
├── canvas.json                # Core: all blocks + connections + layout
├── style_signature.json       # Style signature
├── story_cards.json           # Used story cards
├── omniscient.json            # Omniscient layer (sensitive content stored separately)
├── snapshots/                 # User checkpoints (auto snapshots not exported)
│   ├── checkpoint_001.json
│   └── ...
└── chapters/                  # Generated chapter prose
    ├── chapter_001.md
    └── ...
```

### Export Methods

| Format | API Endpoint | Includes Canvas | Purpose |
|--------|-------------|----------------|---------|
| `.storycanvas` | `/export/full` | ✓ Full | Complete project backup/workflow sharing |
| `canvas.json` | `/export/canvas-json` | ✓ Canvas | Pure canvas structure sharing |
| Markdown | `/export/markdown` | ✗ | Full book text publishing |

### Import Methods

| File Type | Detection Method | Restored Content |
|-----------|-----------------|------------------|
| `.storycanvas` | Extension | Full project: blocks/connections/chapters/checkpoints/style signature |
| `canvas.json` | Extension + JSON structure | Canvas structure: blocks and connections |
| PNG (with metadata) | Read tEXt chunk | Extract canvas.json from PNG metadata |

Frontend supports dragging files onto the canvas area for direct import.

---

## Style Signature System

The style signature is an orthogonal configuration that cuts across all writing, set at project creation and injected into every AI generation request.

```json
{
  "narrative_pov": "Multi-POV Rotation | Omniscient | Limited Third Person | First Person | No-Focus Ensemble",
  "time_structure": "Linear Sequential | In Medias Res | Cross-Cutting | Nonlinear Fragments | Loop Structure",
  "language_density": "Minimalist | Standard Narrative | Epic Density | Stream of Consciousness | Poetic Prose",
  "tone": ["Moral Ambiguity", "Stoic Restraint", "Hot-Blooded", "Absurdist"],
  "world_depth": "World as Backdrop | World as Character | World as Puzzle | World as Critique",
  "chapter_length_target": 3000,
  "dialogue_ratio": 0.3,
  "reference_authors": ["George R.R. Martin", "Tolkien"],
  "avoid_tropes": ["Plot Armor", "Power Creep"],
  "custom_instructions": ""
}
```

---

## Configuration

### Environment Variables (.env)

```bash
# LLM Provider (deepseek|openai|claude|gemini|ollama|custom)
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=sk-xxx
DEEPSEEK_MODEL=deepseek-chat
OPENAI_API_KEY=sk-xxx
OPENAI_MODEL=gpt-4o
OPENAI_BASE_URL=https://api.openai.com/v1
CLAUDE_API_KEY=sk-ant-xxx
CLAUDE_MODEL=claude-3-sonnet-20240229
CLAUDE_BASE_URL=https://api.anthropic.com
GEMINI_API_KEY=xxx
GEMINI_MODEL=gemini-1.5-pro
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5
CUSTOM_BASE_URL=https://your-api.com/v1
CUSTOM_API_KEY=sk-xxx
CUSTOM_MODEL=custom-model

# Service
PORT=8767
DATABASE_PATH=./backend/data/storycanvas.db

# Generation Parameters
DEFAULT_TEMPERATURE=0.8
AUDIT_TEMPERATURE=0.0
MAX_RETRIES=2
CHAPTER_WORD_TARGET=3000
```

> **Note**: Settings saved via the Web UI "🤖 Model" button are written to `backend/data/llm_settings.json` and take priority over `.env` file values.

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- npm 9+

### Installation

```bash
# 1. Install Python dependencies
pip install -r backend/requirements.txt

# 2. Install frontend dependencies
cd frontend && npm install && cd ..

# 3. Configure LLM (choose one)
# Option A: Edit .env to set DEEPSEEK_API_KEY
# Option B: Start Ollama then configure via Web UI
```

### Launch

```bash
# Terminal 1: Backend (port 8767)
cd backend && python main.py

# Terminal 2: Frontend (port 5173)
cd frontend && npm run dev
```

Or use the one-click script:

```bash
start.bat    # Windows
```

### Access

| Service | URL |
|---------|-----|
| Frontend UI | http://localhost:5173 |
| Backend API | http://localhost:8767 |
| API Docs (Swagger) | http://localhost:8767/docs |

---

## Project Structure

```
storycanvas/
├── backend/                     # FastAPI backend
│   ├── main.py                  # App entry + 28+ API endpoints
│   ├── requirements.txt
│   ├── core/                    # Database (6 tables), config, models, snapshot engine
│   ├── api/                     # 7 route modules
│   ├── narrative/               # Context aggregator, translator, progress, validator
│   ├── pipeline/                # 5-layer Agent (Architect/Writer/Auditor/Revisor/Writeback)
│   ├── llm/                     # 5 provider implementations
│   ├── story_cards/             # 35 story cards
│   └── data/                    # SQLite + LLM settings
│
├── frontend/                    # React frontend
│   ├── index.html / package.json / vite.config.ts / tsconfig.json
│   └── src/
│       ├── App.tsx              # Main application
│       ├── i18n/                # Internationalization (Chinese/English)
│       ├── store/               # 3 Zustand Stores
│       ├── api/                 # 5 API modules
│       ├── types/               # 35 block types + 8 connection type definitions
│       ├── canvas/              # React Flow canvas
│       ├── panels/              # 8 panel components
│       └── styles/              # Dark theme CSS
│
├── .env.example                 # Environment variable template
├── install.bat                  # One-click install (Windows)
├── start.bat                    # One-click start (Windows)
└── README.md                    # This document
```
