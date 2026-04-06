# AcademiaOS — Spec v1.0

> A configurable, Docker-packaged OpenClaw wrapper for multi-agent academic workspaces  
> Author: Ronil | Date: 2026-04-06  
> Distribution: OpenClaw extension — install, configure, run

---

## 1. Overview

AcademiaOS is a **distributable OpenClaw wrapper** — like GuardClaw but for academics. Anyone with OpenClaw installed can pull the AcademiaOS Docker image, point it at their own classes, configure their models, and have a fully functional multi-agent academic workspace running locally in minutes.

A single **lead orchestrator agent** powered by an **OpenRouter LLM** manages five specialized sub-agents, each spawned as fresh **Claude CLI instances** using the user's own Claude membership — **no API keys, no LLM fallback**.

Each class gets its own tab, its own Obsidian-backed memory vault, and its own agent context. The platform handles tutoring, question generation, test creation, homework completion (with R-Studio and DOCX/PDF output), and note summarization.

### 1.1 Design Principles

- **Zero API keys for Claude.** All Claude access goes through CLI spawned via terminal. OpenRouter key is the only external credential (for the lead orchestrator only).
- **Obsidian-native memory.** Every class has a vault. Agents read/write markdown. Human-readable, version-controllable, portable.
- **Fresh agent instances.** Sub-agents are stateless processes. They receive context from the memory vault at spawn time, do their work, write results back. No persistent daemon agents.
- **Anti-slop by design.** The Homework Finisher agent is specifically tuned to produce human-quality output — referencing past submissions for style, showing work without explanation, and running multiple self-review passes.
- **Configure, don't fork.** Users never edit source code. Everything is driven by `config/` files — classes, models, semester dates, tools per class. Add a class = add a JSON entry.
- **Docker-first distribution.** One `docker compose up` and you're running. Host volumes for vaults and class files so your data lives on your machine, not in the container.

### 1.2 Distribution Model

AcademiaOS is an **OpenClaw extension** distributed as a Docker image. It sits alongside other OpenClaw wrappers (GuardClaw, ClawWorld, etc.) and follows the same pattern:

```
OpenClaw (core)
├── GuardClaw (safety wrapper)
├── ClawWorld (gamified RPG frontend)
└── AcademiaOS (academic workspace)    ← this project
```

**What ships in the image:**
- OpenClaw gateway with AcademiaOS-specific extensions (Claude CLI Spawn Provider, Vault Tool, R Execution Tool, Doc Generation Tool)
- GuardClaw (bundled)
- Observability Dashboard
- React/Vite frontend
- All 5 agent system prompts (tutor, question creator, test creator, homework finisher, note summarizer)
- `init` script that scaffolds directories from user config
- Example config for a sample semester (Ronil's Spring 2026 classes as a reference)

**What the user provides:**
- `config/classes.json` — their own classes, codes, and tool requirements
- `config/models.json` — their preferred model assignments per agent
- `config/semester.json` — semester start/end dates
- `.env` file — OpenRouter API key
- Claude CLI authenticated on the host machine
- R + Rscript on the host (if using R-dependent classes)
- Their own textbooks, submissions, and rubrics (uploaded via the UI or dropped into mounted volumes)

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     React/Vite Frontend                     │
│  ┌──────────────────────────────────────────┐ ┌─────────┐  │
│  │  Dynamic class tabs from classes.json    │ │Progress │  │
│  │  [Class 1] [Class 2] [Class 3] [...]     │ │ Tracker │  │
│  └────────────────────┬─────────────────────┘ └────┬────┘  │
│                       └──────────────┬─────────────┘       │
│                                      │                      │
│                               WebSocket Layer               │
└──────────────────────────────────────┬──────────────────────┘
                             │
┌────────────────────────────┴────────────────────────────────┐
│                    OpenClaw Gateway                          │
│                  (FastAPI + JSON-RPC 2.0)                    │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │              GuardClaw Safety Layer                    │  │
│  │         (input/output filtering, guardrails)          │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │           LEAD ORCHESTRATOR (OpenRouter)               │  │
│  │     Model: configurable (e.g. google/gemini-2.5-pro)  │  │
│  │                                                        │  │
│  │  Responsibilities:                                     │  │
│  │  - Parse user intent from frontend                     │  │
│  │  - Route to correct sub-agent                          │  │
│  │  - Spawn Claude CLI instances via terminal             │  │
│  │  - Inject class-specific memory context at spawn       │  │
│  │  - Collect results and relay to frontend               │  │
│  │  - Coordinate multi-agent workflows (e.g. Test Creator │  │
│  │    calling Question Creator)                           │  │
│  └─────────┬─────────────────────────────────────────────┘  │
│            │                                                 │
│  ┌─────────┴─────────────────────────────────────────────┐  │
│  │              SUB-AGENT SPAWN LAYER                     │  │
│  │                                                        │  │
│  │  Each sub-agent is spawned as:                         │  │
│  │    $ claude --print --system-prompt <prompt_file>      │  │
│  │                                                        │  │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐     │  │
│  │  │  Tutor  │ │Question │ │  Test   │ │Homework │     │  │
│  │  │  Agent  │ │ Creator │ │ Creator │ │Finisher │     │  │
│  │  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘     │  │
│  │       │           │           │            │          │  │
│  │  ┌────┴───────────┴───────────┴────────────┴────┐     │  │
│  │  │            Note Summarizer Agent              │     │  │
│  │  └──────────────────────────────────────────────┘     │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │                TOOL LAYER                              │  │
│  │                                                        │  │
│  │  - File system access (read/write/create)              │  │
│  │  - R-Studio CLI execution (Rscript)                    │  │
│  │  - DOCX generation (pandoc / python-docx)              │  │
│  │  - PDF generation (pandoc / LaTeX)                     │  │
│  │  - Obsidian vault read/write                           │  │
│  │  - Past submission scanner                             │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                             │
┌────────────────────────────┴────────────────────────────────┐
│                    LOCAL FILE SYSTEM (HOST)                  │
│           (mounted into container via docker volumes)        │
│                                                             │
│  ~/academia-os/                                             │
│  ├── docker-compose.yml                                     │
│  ├── .env                       # OpenRouter key, ports     │
│  ├── config/                    # USER-PROVIDED (mounted)   │
│  │   ├── classes.json           # ← user edits this        │
│  │   ├── models.json            # ← user edits this        │
│  │   └── openclaw.yaml          # ← user edits this        │
│  ├── vaults/                    # Obsidian memory vaults    │
│  │   ├── <class-id>/            # Auto-created per class    │
│  │   └── ...                                                │
│  ├── classes/                   # Per-class file storage    │
│  │   ├── <class-id>/                                        │
│  │   │   ├── textbooks/                                     │
│  │   │   ├── practice/                                      │
│  │   │   ├── submissions/       # Past HW submissions      │
│  │   │   ├── rubrics/                                       │
│  │   │   └── outputs/           # Agent-generated files     │
│  │   └── ...                                                │
│  ├── progress/                  # Progress tracker data     │
│  │   └── tracker.json                                       │
│  └── logs/                      # Observability logs        │
│      ├── events.db                                          │
│      └── pipeline.jsonl                                     │
│                                                             │
│  INSIDE CONTAINER ONLY (not mounted):                       │
│  /app/                                                      │
│  ├── src/                       # AcademiaOS source code    │
│  ├── frontend/dist/             # Built React app           │
│  ├── prompts/                   # Default agent prompts     │
│  │   ├── tutor.md                                           │
│  │   ├── question-creator.md                                │
│  │   ├── test-creator.md                                    │
│  │   ├── homework-finisher.md                               │
│  │   └── note-summarizer.md                                 │
│  └── scripts/                   # Init, archival scripts    │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Classes Configuration

Classes are entirely user-configured via `config/classes.json`. The frontend dynamically renders tabs, the backend auto-scaffolds vault and file directories, and agents scope their memory — all from this one file.

### 3.1 Example Config: Ronil's Spring 2026 (ships as `config/classes.example.json`)

| ID | Class Name | Short Code | Vault Path | Key Tools |
|---|---|---|---|---|
| 1 | Applied Multivariate Analysis | `AMV` | `vaults/applied-multivariate/` | R, matrix computation |
| 2 | Data in Context | `DIC` | `vaults/data-in-context/` | R, data viz |
| 3 | Intermediate Microeconomic Analysis | `IMEQ` | `vaults/intermediate-micro/` | Graphs, optimization |
| 4 | Regression Methods | `REGM` | `vaults/regression-methods/` | R, statistical modeling |
| 5 | Intro to Macroeconomics | `MACR` | `vaults/intro-macro/` | AD-AS, IS-LM diagrams |

### 3.2 Class Registry Schema (`config/classes.json`)

```json
{
  "semester": {
    "name": "Spring 2026",
    "start": "2026-01-20",
    "end": "2026-05-15",
    "archived": false
  },
  "classes": [
    {
      "id": "applied-multivariate",
      "name": "Applied Multivariate Analysis",
      "code": "AMV",
      "tools": ["r-studio", "docx", "pdf"],
      "active": true
    },
    {
      "id": "data-in-context",
      "name": "Data in Context",
      "code": "DIC",
      "tools": ["r-studio", "docx", "pdf"],
      "active": true
    },
    {
      "id": "intermediate-micro",
      "name": "Intermediate Microeconomic Analysis",
      "code": "IMEQ",
      "tools": ["docx", "pdf"],
      "active": true
    },
    {
      "id": "regression-methods",
      "name": "Regression Methods",
      "code": "REGM",
      "tools": ["r-studio", "docx", "pdf"],
      "active": true
    },
    {
      "id": "intro-macro",
      "name": "Intro to Macroeconomics",
      "code": "MACR",
      "tools": ["docx", "pdf"],
      "active": true
    }
  ]
}
```

### 3.3 Adding Your Own Classes

A new user copies `classes.example.json` → `classes.json` and replaces with their own classes. The only required fields per class are `id`, `name`, `code`, and `tools`. On next startup (or `docker compose restart`), the init script:

1. Creates `vaults/<id>/` with the standard vault structure
2. Creates `classes/<id>/` with subdirectories (`textbooks/`, `practice/`, `submissions/`, `rubrics/`, `outputs/`)
3. Generates a blank `_index.md`, `topics.md`, and `context.md` in the vault
4. Registers the class in the frontend tab bar

Removing a class = set `"active": false`. The vault and files are preserved but the tab disappears.

**Available tools per class:**
| Tool ID | What It Enables | Host Dependency |
|---|---|---|
| `r-studio` | R code execution via `Rscript`, R Markdown rendering | R installed on host |
| `docx` | Word document generation via python-docx or pandoc | pandoc on host (bundled in Docker) |
| `pdf` | PDF generation via pandoc + LaTeX | pandoc + texlive (bundled in Docker) |
| `python` | Python code execution for computational classes | Python (bundled in Docker) |
| `latex` | Raw LaTeX compilation for math-heavy output | texlive (bundled in Docker) |

---

## 4. Agent Specifications

### 4.1 Lead Orchestrator

| Property | Value |
|---|---|
| **Runtime** | OpenClaw process (always-on) |
| **Model** | OpenRouter — configurable (recommended: `google/gemini-2.5-pro` or `anthropic/claude-sonnet-4` via OpenRouter) |
| **API Key** | OpenRouter API key (only external credential in entire system) |
| **Role** | Intent parsing, agent routing, context injection, result relay |
| **Memory Access** | Read-only on all vaults (writes are delegated to sub-agents) |

**Orchestrator Responsibilities:**

1. Receive user message + active class context from frontend via WebSocket
2. Determine which sub-agent(s) to invoke
3. Assemble context payload from the class vault (recent memory entries, relevant files)
4. Spawn Claude CLI instance with the appropriate system prompt + context
5. Stream or collect the sub-agent response
6. If multi-agent workflow (e.g. Test Creator needs Question Creator first), chain the calls
7. Write memory entries back to the vault
8. Return final result to frontend

**Spawn Command Template:**

```bash
# Single-turn task (e.g. summarize notes)
echo "<context>\n${VAULT_CONTEXT}\n</context>\n\n${USER_MESSAGE}" | claude --print --system-prompt "$(cat prompts/note-summarizer.md)" --model claude-sonnet-4-20250514

# Interactive session (e.g. tutoring)
claude --system-prompt "$(cat prompts/tutor.md)" --model claude-sonnet-4-20250514 --resume <session_id>
```

> **Critical:** The `claude` command uses the local Claude CLI authenticated via Ronil's Claude membership. No API key is passed. The OpenRouter key is ONLY used for the lead orchestrator. If OpenRouter is down or the key is invalid, the entire system halts — there is no fallback to a different LLM.

### 4.2 Sub-Agent: Specialized Tutor

| Property | Value |
|---|---|
| **Spawn** | Fresh Claude CLI instance per session |
| **Model** | `claude-sonnet-4-20250514` (recommended — strong reasoning for explanations) |
| **Mode** | Interactive (multi-turn conversation) |
| **Memory** | Reads class vault at spawn; writes session summary to vault on exit |

**Capabilities:**
- Explain concepts at the right depth for Ronil's level (junior econ/stats student)
- Reference uploaded textbook material and practice questions
- Adapt explanations based on vault memory (what's been covered, what was struggled with)
- For quantitative classes (AMV, REGM, DIC): work through problems step-by-step, show R code when relevant
- For theory classes (IMEQ, MACR): use diagrams (described textually or generated as SVG), walk through model logic
- Track which topics have been tutored in the vault

**System Prompt Core Directives:**
```
You are a specialized tutor for [CLASS_NAME] at Rutgers University.
- The student is an Economics major with Data Science and Statistics minors.
- Explain with depth but no fluff. The student prefers terse, direct communication.
- When math is involved, show the work. Use LaTeX notation.
- For R-based classes, write executable R code when demonstrating concepts.
- Reference the provided class memory to avoid repeating covered material.
- At the end of each session, output a <memory_update> block summarizing:
  - Topics covered
  - Key concepts explained
  - Areas where the student showed uncertainty
```

### 4.3 Sub-Agent: Question Creator

| Property | Value |
|---|---|
| **Spawn** | Fresh Claude CLI instance per invocation |
| **Model** | `claude-sonnet-4-20250514` |
| **Mode** | Single-turn (receives spec, returns questions) |
| **Memory** | Reads vault to avoid duplicate questions; writes generated questions to vault |

**Capabilities:**
- Generate practice questions at configurable difficulty: `easy`, `medium`, `hard`, `exam-level`
- Pull from uploaded textbook content and practice question files for style matching
- Tag questions by topic and difficulty
- Output formats: plain text, LaTeX, or structured JSON for the frontend to render
- Can be invoked standalone or as a dependency of Test Creator

**Input Schema (from orchestrator):**
```json
{
  "class_id": "regression-methods",
  "topics": ["multiple regression", "heteroscedasticity"],
  "count": 10,
  "difficulty": "exam-level",
  "format": "json",
  "include_solutions": true,
  "style_reference": "classes/regression-methods/practice/midterm_review.pdf"
}
```

**Output Schema:**
```json
{
  "questions": [
    {
      "id": "q-regm-001",
      "topic": "multiple regression",
      "difficulty": "exam-level",
      "question": "...",
      "solution": "...",
      "r_code": "...",
      "tags": ["OLS", "coefficient interpretation"]
    }
  ]
}
```

### 4.4 Sub-Agent: Test Creator

| Property | Value |
|---|---|
| **Spawn** | Fresh Claude CLI instance per invocation |
| **Model** | `claude-sonnet-4-20250514` |
| **Mode** | Single-turn with sub-agent chaining |
| **Memory** | Reads vault for past tests created; writes test metadata to vault |

**Capabilities:**
- Creates full practice exams with configurable parameters:
  - Number of sections
  - Question types (multiple choice, short answer, computation, proof, R-coding)
  - Time estimate
  - Topic weighting
- **Calls Question Creator** as a sub-agent to generate the actual questions (orchestrator handles this chaining)
- Assembles questions into a formatted test document
- Generates answer key as a separate document
- Outputs as PDF (via pandoc/LaTeX) or DOCX

**Workflow:**
```
User Request → Orchestrator → Test Creator (defines structure)
                                    ↓
                              Orchestrator spawns Question Creator
                              with Test Creator's question specs
                                    ↓
                              Questions returned to Orchestrator
                                    ↓
                              Orchestrator passes questions back to
                              Test Creator for assembly
                                    ↓
                              Final test PDF/DOCX returned
```

### 4.5 Sub-Agent: Homework Finisher

| Property | Value |
|---|---|
| **Spawn** | Fresh Claude CLI instance per invocation |
| **Model** | `claude-opus-4-20250514` (recommended — highest quality for graded submissions) |
| **Mode** | Single-turn with tool access |
| **Memory** | Reads vault + past submissions folder + rubrics folder |

**This is the highest-stakes agent.** It produces work that gets submitted for grades.

**Capabilities:**
- Read the assignment prompt (uploaded by user or pasted)
- Read rubric if available (from `classes/<class>/rubrics/`)
- Scan past submissions (from `classes/<class>/submissions/`) to learn:
  - Formatting conventions (margins, headers, fonts, spacing)
  - Writing style and voice
  - Level of detail expected
  - Common rubric patterns (what gets full marks)
- Execute R code via `Rscript` for statistics/data classes
- Generate output files:
  - `.R` script files (clean, commented)
  - `.docx` homework documents (via python-docx or pandoc)
  - `.pdf` homework documents (via pandoc + LaTeX)
- **Anti-Slop Pipeline:**
  1. **Draft Pass:** Generate initial solution showing all work
  2. **Style Pass:** Compare against past submissions, match voice and formatting
  3. **Correctness Pass:** Verify all calculations, re-run R code, check answers
  4. **Humanization Pass:** Remove AI tells (no "Let's", "Great question", "Here's", hedging language). Ensure work is shown without unnecessary explanation unless the rubric requires it.
  5. **Final Review:** Read the complete document as a professor would. Flag anything suspicious.

**System Prompt Core Directives:**
```
You are completing a homework assignment for [CLASS_NAME].

CRITICAL RULES:
1. Show work. Do NOT explain your reasoning unless the rubric explicitly asks for it.
2. Match the formatting and style of past submissions exactly.
3. Write like a student, not an AI. No hedging, no filler, no "Note that...".
4. If R code is needed, write clean code with minimal comments.
5. If the rubric says "show your work," show the mathematical steps only.
6. Double-check every calculation. Run R code and verify output.
7. Output the final document in the requested format (DOCX or PDF).

You have access to:
- Past submissions in: classes/[CLASS_ID]/submissions/
- Rubrics in: classes/[CLASS_ID]/rubrics/
- R execution via: Rscript <file.R>
- File creation via standard file tools

After generating the document, perform a self-review:
- Does this look like it was written by a human student?
- Are all calculations correct?
- Does formatting match past submissions?
- Would a professor flag this as AI-generated?
```

### 4.6 Sub-Agent: Note Summarizer

| Property | Value |
|---|---|
| **Spawn** | Fresh Claude CLI instance per invocation |
| **Model** | `claude-sonnet-4-20250514` |
| **Mode** | Single-turn |
| **Memory** | Reads vault; writes summaries to vault under `summaries/` |

**Capabilities:**
- Summarize lecture notes, textbook chapters, or uploaded PDFs
- Generate concise study sheets (1-2 pages per chapter/lecture)
- Create formula sheets / cheat sheets for quantitative classes
- Produce flashcard-ready Q&A pairs
- Cross-reference with vault memory to highlight new vs. already-known material
- Output formats: Markdown (stored in vault), PDF, DOCX

**Output Structure:**
```markdown
# [Topic] — Summary
## Key Concepts
- ...
## Formulas
- ...
## Critical Details (exam-likely)
- ...
## Connections to Previous Topics
- ...
```

---

## 5. Memory System (Obsidian Vaults)

Each class has its own Obsidian vault at `~/AcademiaOS/vaults/<class-id>/`.

### 5.1 Vault Structure

```
vaults/regression-methods/
├── _index.md                    # Class overview, syllabus, professor info
├── sessions/                    # Tutor session logs
│   ├── 2026-04-06-ols-review.md
│   └── 2026-04-08-heteroscedasticity.md
├── summaries/                   # Note Summarizer output
│   ├── ch05-multiple-regression.md
│   └── ch06-model-diagnostics.md
├── questions/                   # Question Creator output
│   ├── midterm1-practice.json
│   └── weekly-quiz-03.json
├── tests/                       # Test Creator output
│   ├── practice-midterm-1.pdf
│   └── practice-midterm-1-key.pdf
├── homework/                    # Homework Finisher output
│   ├── hw04-output.docx
│   └── hw04-output.R
├── topics.md                    # Running topic registry
└── context.md                   # Auto-generated rolling context file
```

### 5.2 Context Assembly

When a sub-agent is spawned, the orchestrator assembles a context payload:

1. **Always included:** `_index.md` (class overview), `topics.md` (topic registry), `context.md` (rolling context — last 5 sessions + key facts)
2. **Conditionally included based on agent type:**
   - Tutor: last 3 session logs from `sessions/`
   - Question Creator: existing question files to avoid duplicates
   - Test Creator: past test structures
   - Homework Finisher: rubric files, past submission samples
   - Note Summarizer: existing summaries (to avoid re-summarizing)
3. **User-specified files:** Any files the user explicitly references in their message

### 5.3 `context.md` Auto-Generation

After every agent interaction, the orchestrator appends to and periodically regenerates `context.md`. This file is a compressed representation of the class's memory — designed to fit within Claude CLI's context window.

```markdown
# Regression Methods — Rolling Context
Last updated: 2026-04-06

## Covered Topics
- Simple linear regression (mastered)
- Multiple regression (in progress)
- OLS assumptions (reviewed, needs practice)
- Heteroscedasticity (introduced 2026-04-05)

## Key Formulas Referenced
- β̂ = (X'X)⁻¹X'Y
- Var(β̂) = σ²(X'X)⁻¹

## Recent Sessions
- 2026-04-05: Reviewed White's test for heteroscedasticity. Student struggled with interpreting test statistic. Needs more practice problems on this.
- 2026-04-03: Multiple regression coefficient interpretation. Student was solid on this.

## Active Homework
- HW4 due 2026-04-10: Regression diagnostics, VIF, Cook's distance

## Style Notes (from past submissions)
- Professor expects R output pasted inline with brief interpretation
- Handwritten-style math not required, LaTeX acceptable
- Typical length: 4-6 pages for problem sets
```

### 5.4 Semester Archival

When `semester.end` date is reached (May 15, 2026):

1. All vaults are moved to `~/AcademiaOS/archive/spring-2026/`
2. Class entries in `classes.json` are set to `"active": false`
3. Archived vaults remain accessible (read-only) for reference
4. New semester = new entries in `classes.json` + new vault directories

---

## 6. Progress Tracker

The Progress Tracker is a standalone tab (not class-specific) that shows learning progress across all classes.

### 6.1 Data Model (`progress/tracker.json`)

```json
{
  "topics": [
    {
      "id": "regm-heteroscedasticity",
      "class_id": "regression-methods",
      "name": "Heteroscedasticity",
      "status": "struggling",
      "confidence": 2,
      "first_seen": "2026-04-05",
      "last_reviewed": "2026-04-06",
      "notes": "Can identify it but struggle with White's test interpretation",
      "mastered": false
    },
    {
      "id": "regm-ols-assumptions",
      "class_id": "regression-methods",
      "name": "OLS Assumptions",
      "status": "reviewing",
      "confidence": 4,
      "first_seen": "2026-03-15",
      "last_reviewed": "2026-04-01",
      "notes": "",
      "mastered": false
    }
  ]
}
```

### 6.2 Frontend Rendering

- **Per-class grouping** with expandable sections
- **Confidence scale:** 1-5 (1 = no clue, 5 = could teach it)
- **Status badges:** `new` → `struggling` → `reviewing` → `confident` → `mastered`
- **Checkmark toggle:** User can manually mark a topic as mastered
- **Auto-population:** When Tutor or Question Creator agents detect a new topic, they append it to the tracker via the orchestrator
- **Visual:** Color-coded progress bars per class (red → yellow → green)

---

## 7. File Upload System

### 7.1 Upload Categories

Each class tab has an upload section with three bins:

| Bin | Path | Description |
|---|---|---|
| **Textbooks** | `classes/<class>/textbooks/` | PDFs, chapters, reference material |
| **Practice** | `classes/<class>/practice/` | Practice problems, worksheets, past exams |
| **Submissions** | `classes/<class>/submissions/` | Past homework submissions (for style matching) |
| **Rubrics** | `classes/<class>/rubrics/` | Grading rubrics and assignment guidelines |

### 7.2 Upload Flow

1. User drags/drops or selects file(s) in the class tab
2. Frontend sends file to OpenClaw backend via multipart upload
3. Backend stores file in the appropriate directory
4. If the file is a PDF, the system indexes it for agent reference:
   - Extract text via `pdftotext` or `pymupdf`
   - Store extracted text as `.txt` alongside the original
   - Add file reference to the class vault's `_index.md`

### 7.3 Textbook Access

The system does **not** source or download textbooks. The user must supply their own files. Legitimate sources to obtain textbook content:

- **Rutgers University Libraries** — digital access via institutional login (libraries.rutgers.edu)
- **OpenStax** — free, peer-reviewed textbooks (openstax.org) — covers Intro Macro and potentially Micro
- **Professor-provided PDFs** — lecture slides, chapter excerpts shared on Canvas
- **Libby / OverDrive** — library ebook lending (if available through Rutgers)

The user uploads these files into the appropriate class bin manually.

---

## 8. Frontend Specification

### 8.1 Stack

| Layer | Choice |
|---|---|
| Framework | React 18 + Vite |
| Styling | Tailwind CSS |
| State | Zustand |
| WebSocket | Native WebSocket (same pattern as ClawWorld) |
| Routing | React Router v6 (tab-based) |
| File Upload | `react-dropzone` |
| Markdown Rendering | `react-markdown` + `remark-math` + `rehype-katex` |
| Code Highlighting | `highlight.js` or `shiki` |

### 8.2 Layout

```
┌──────────────────────────────────────────────────────────┐
│  AcademiaOS                              [Settings] [⚙]  │
├──────────────────────────────────────────────────────────┤
│  [AMV] [DIC] [IMEQ] [REGM] [MACR] [Progress] [Files]   │
├────────────────────────────┬─────────────────────────────┤
│                            │                             │
│    CHAT / AGENT AREA       │      SIDE PANEL             │
│                            │                             │
│  Agent selector:           │  Context:                   │
│  [🎓Tutor] [❓Q-Creator]  │  - Active memory entries    │
│  [📝Test] [📄Homework]    │  - Recent topics            │
│  [📋Notes]                 │  - Uploaded files           │
│                            │  - Current assignment       │
│  [Chat messages here]      │                             │
│                            │  Quick Actions:             │
│                            │  - Upload file              │
│                            │  - View past sessions       │
│                            │  - Export notes              │
│                            │                             │
├────────────────────────────┴─────────────────────────────┤
│  [Message input]                              [Send] [📎]│
└──────────────────────────────────────────────────────────┘
```

### 8.3 Key UI Features

- **Tab persistence:** Each class tab maintains its own chat history and agent state for the current session
- **Agent selector:** Per-class agent buttons that switch the active agent context. Visual indicator shows which agent is active.
- **File preview panel:** Click uploaded files to preview (PDF viewer, text viewer, image viewer)
- **Output downloads:** When Homework Finisher or Test Creator produces a file, it appears as a downloadable card in the chat
- **LaTeX rendering:** Math expressions render inline using KaTeX
- **R code blocks:** Syntax-highlighted with a "Copy" button
- **Dark mode by default** (matches Ronil's preference for dev tools)
- **Responsive but desktop-first** (primary use case is at a desk with R-Studio open)

---

## 9. Model Assignments (`config/models.json`)

```json
{
  "orchestrator": {
    "provider": "openrouter",
    "model": "google/gemini-2.5-pro",
    "notes": "Lead agent. Only component using OpenRouter API key."
  },
  "agents": {
    "tutor": {
      "cli_model": "claude-sonnet-4-20250514",
      "notes": "Strong reasoning for explanations. Interactive mode."
    },
    "question-creator": {
      "cli_model": "claude-sonnet-4-20250514",
      "notes": "Good balance of creativity and accuracy for question generation."
    },
    "test-creator": {
      "cli_model": "claude-sonnet-4-20250514",
      "notes": "Structural assembly. Calls Question Creator for content."
    },
    "homework-finisher": {
      "cli_model": "claude-opus-4-20250514",
      "notes": "Highest quality model for graded work. Anti-slop pipeline."
    },
    "note-summarizer": {
      "cli_model": "claude-sonnet-4-20250514",
      "notes": "Efficient for distillation tasks."
    }
  }
}
```

> Models are configurable per-agent. If Claude CLI adds new models, update this file. The orchestrator model can be swapped to any OpenRouter-compatible model.

---

## 10. OpenClaw Integration

### 10.1 Required OpenClaw Components

| Component | Purpose |
|---|---|
| **OpenClaw Core** | FastAPI gateway, WebSocket management, JSON-RPC routing |
| **GuardClaw** | Input/output safety filtering, prompt injection protection |
| **Provider Router** | Routes orchestrator calls to OpenRouter; routes sub-agent calls to Claude CLI spawn |
| **Tool Registry** | Registers file tools, R execution, document generation, vault I/O |
| **Session Manager** | Tracks active class context, agent state, chat history per tab |

### 10.2 New OpenClaw Extensions Needed

1. **Claude CLI Spawn Provider** — A new provider type that executes `claude` as a subprocess instead of making an API call. Must handle:
   - Piping system prompt + context as stdin
   - Streaming stdout back to the orchestrator
   - Timeout management (homework tasks can take 60+ seconds)
   - Exit code handling and error relay

2. **Obsidian Vault Tool** — MCP-compatible tool for agents to:
   - `vault.read(class_id, path)` — Read a file from the vault
   - `vault.write(class_id, path, content)` — Write/append to a vault file
   - `vault.list(class_id, directory)` — List files in a vault subdirectory
   - `vault.search(class_id, query)` — Full-text search within a vault

3. **R Execution Tool** — MCP-compatible tool for:
   - `r.execute(script_path)` — Run an R script via `Rscript`
   - `r.execute_inline(code)` — Run inline R code, capture stdout + generated files

4. **Document Generation Tool** — MCP-compatible tool for:
   - `doc.create_docx(content, template, output_path)`
   - `doc.create_pdf(content, template, output_path)`
   - `doc.convert(input_path, output_format)`

---

## 11. Configuration & Setup

### 11.1 Prerequisites (Host Machine)

Only three things must exist on the host — everything else is bundled in the Docker image:

- **Docker + Docker Compose** (v2.20+)
- **Claude CLI** installed and authenticated (`claude` command works in terminal)
- **OpenRouter API key**

**Optional host dependencies** (only if used in `tools` config):
- **R + Rscript** — required if any class uses the `r-studio` tool. Must be on host PATH since R execution happens outside the container for access to local R packages and RStudio projects.

### 11.2 Docker Compose (`docker-compose.yml`)

```yaml
version: "3.9"

services:
  academia-gateway:
    image: openclaw/academia-os:latest
    container_name: academia-os
    ports:
      - "${GATEWAY_PORT:-8100}:8100"         # OpenClaw gateway
      - "${DASHBOARD_PORT:-8101}:8101"       # Observability dashboard
      - "${FRONTEND_PORT:-3000}:3000"        # React frontend
    environment:
      - OPENROUTER_API_KEY=${OPENROUTER_API_KEY}
      - ACADEMIA_PROJECT_ID=${PROJECT_ID:-academia-os}
      - CLAUDE_CLI_PATH=${CLAUDE_CLI_PATH:-claude}
    volumes:
      # User config (required)
      - ./config:/app/config:ro

      # Persistent data (survives container rebuilds)
      - ./vaults:/app/vaults
      - ./classes:/app/classes
      - ./progress:/app/progress
      - ./logs:/app/logs

      # Claude CLI access — mount host CLI binary + auth
      - ${CLAUDE_CLI_BIN:-/usr/local/bin/claude}:/usr/local/bin/claude:ro
      - ${CLAUDE_CONFIG:-~/.claude}:/home/app/.claude:ro

      # R access (optional — only if classes use r-studio tool)
      - ${R_BIN:-/usr/bin/Rscript}:/usr/bin/Rscript:ro
      - ${R_LIBS:-/usr/lib/R}:/usr/lib/R:ro

      # Custom prompts (optional — override defaults)
      # - ./prompts:/app/prompts:ro
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8100/health"]
      interval: 30s
      timeout: 5s
      retries: 3
```

### 11.3 Environment File (`.env`)

```bash
# Required
OPENROUTER_API_KEY=sk-or-...

# Optional — override defaults
GATEWAY_PORT=8100
DASHBOARD_PORT=8101
FRONTEND_PORT=3000
PROJECT_ID=academia-os

# Host paths (auto-detected on most systems, override if needed)
# CLAUDE_CLI_BIN=/usr/local/bin/claude
# CLAUDE_CONFIG=~/.claude
# R_BIN=/usr/bin/Rscript
# R_LIBS=/usr/lib/R
```

### 11.4 First Run

```bash
# 1. Pull the image
docker pull openclaw/academia-os:latest

# 2. Create your workspace
mkdir ~/academia-os && cd ~/academia-os

# 3. Copy example configs and customize
docker run --rm openclaw/academia-os:latest cat /app/config/classes.example.json > config/classes.json
docker run --rm openclaw/academia-os:latest cat /app/config/models.example.json > config/models.json
docker run --rm openclaw/academia-os:latest cat /app/config/openclaw.example.yaml > config/openclaw.yaml
docker run --rm openclaw/academia-os:latest cat /app/.env.example > .env
docker run --rm openclaw/academia-os:latest cat /app/docker-compose.yml > docker-compose.yml

# 4. Edit config/classes.json with your own classes
# Edit .env with your OpenRouter key

# 5. Launch
docker compose up -d

# 6. Init scaffolds directories automatically on first boot
# Check logs:
docker compose logs -f academia-gateway

# 7. Open
# Frontend:   http://localhost:3000
# Dashboard:  http://localhost:8101
# Gateway:    http://localhost:8100
```

### 11.5 Dockerfile (What Ships in the Image)

```dockerfile
FROM python:3.11-slim

# System deps: pandoc, texlive, Node.js, curl
RUN apt-get update && apt-get install -y --no-install-recommends \
    pandoc texlive-latex-base texlive-fonts-recommended texlive-latex-extra \
    nodejs npm curl poppler-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python deps (OpenClaw + AcademiaOS extensions)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Frontend build
COPY frontend/ frontend/
RUN cd frontend && npm ci && npm run build

# AcademiaOS source
COPY src/ src/
COPY prompts/ prompts/
COPY config/*.example.* config/
COPY scripts/ scripts/

# Entrypoint: run init script then start gateway + frontend
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

EXPOSE 8100 8101 3000

ENTRYPOINT ["./entrypoint.sh"]
```

### 11.6 Entrypoint Script (`entrypoint.sh`)

```bash
#!/bin/bash
set -e

echo "╔══════════════════════════════════════╗"
echo "║         AcademiaOS Starting          ║"
echo "║    OpenClaw Academic Workspace       ║"
echo "╚══════════════════════════════════════╝"

# 1. Validate required config
if [ ! -f /app/config/classes.json ]; then
  echo "ERROR: config/classes.json not found. Copy from classes.example.json and configure."
  exit 1
fi

if [ -z "$OPENROUTER_API_KEY" ]; then
  echo "ERROR: OPENROUTER_API_KEY not set. Add it to your .env file."
  exit 1
fi

# 2. Verify Claude CLI is accessible
if ! command -v claude &> /dev/null; then
  echo "ERROR: Claude CLI not found. Mount it via docker-compose volumes."
  exit 1
fi

# 3. Scaffold directories from classes.json (idempotent)
echo "Scaffolding class directories..."
python scripts/init_semester.py --config /app/config/classes.json

# 4. Verify R if any class needs it
if python -c "import json; c=json.load(open('/app/config/classes.json')); exit(0 if any('r-studio' in cl.get('tools',[]) for cl in c['classes'] if cl.get('active')) else 1)" 2>/dev/null; then
  if ! command -v Rscript &> /dev/null; then
    echo "WARNING: Classes require R but Rscript not found. Mount R via docker-compose volumes."
  else
    echo "R detected: $(Rscript --version 2>&1 | head -1)"
  fi
fi

# 5. Start services
echo "Starting OpenClaw gateway on :8100..."
python -m openclaw.server --config /app/config/openclaw.yaml &

echo "Starting Observability dashboard on :8101..."
python -m academia.dashboard --port 8101 &

echo "Serving frontend on :3000..."
npx serve frontend/dist -l 3000 -s &

echo "AcademiaOS is live."
echo "  Frontend:   http://localhost:3000"
echo "  Dashboard:  http://localhost:8101"
echo "  Gateway:    http://localhost:8100"

wait
```

### 11.7 Updating

```bash
# Pull latest image
docker compose pull

# Restart (config + data volumes persist)
docker compose up -d

# Your vaults, classes, progress, and config are untouched.
# Only the application code updates.
```

### 11.8 Non-Docker Fallback (Dev Mode)

For contributors or anyone who prefers running bare-metal:

```bash
# Clone repo
git clone <repo> ~/academia-os
cd ~/academia-os

# Backend
pip install -r requirements.txt
python -m openclaw.server --config config/openclaw.yaml

# Frontend (separate terminal)
cd frontend && npm install && npm run dev

# Prerequisites: Node 18+, Python 3.11+, pandoc, texlive, Claude CLI, R (optional)
```

---

## 12. Multi-Instance Isolation

Running multiple OpenClaw gateways on the same machine (e.g. AcademiaOS + ClawWorld + PEENS) requires **zero cross-contamination** — no shared state, no port collisions, no agents reading the wrong vault.

### 12.1 Isolation Strategy: Containers + Ports + Volumes

With Docker, isolation is largely free — each project runs in its own container with its own filesystem. The remaining shared resources are host-level: ports, the Claude CLI binary, and the Claude membership rate limit.

| Resource | Isolation Method |
|---|---|
| **Process** | Each project is a separate Docker container — fully isolated by default |
| **Port** | Each container maps to unique host ports (`8100/8101/3000` for AcademiaOS, `8200/8201/3100` for ClawWorld) |
| **Data** | Each container mounts its own host directory (`~/academia-os/`, `~/clawworld/`, etc.) |
| **Config** | Each container has its own `config/` volume mount — impossible to read another project's config |
| **Vault paths** | Container-internal. AcademiaOS agents literally cannot see ClawWorld files. |
| **Claude CLI** | Shared host binary mounted read-only. Each container spawns its own subprocesses. |
| **OpenRouter key** | Can be the same key (usage is metered, not conflicting) or different keys per `.env` |
| **Logs** | Each container writes to its own `logs/` volume mount |

### 12.2 Project Config (`config/openclaw.yaml`)

```yaml
project:
  name: "academia-os"
  id: "academia-os-spring-2026"

server:
  host: "127.0.0.1"
  port: 8100
  ws_path: "/ws"

data:
  root: "~/AcademiaOS"
  vaults: "~/AcademiaOS/vaults"
  classes: "~/AcademiaOS/classes"
  logs: "~/AcademiaOS/logs"
  prompts: "~/AcademiaOS/prompts"

providers:
  orchestrator:
    type: "openrouter"
    model: "google/gemini-2.5-pro"
    api_key_env: "OPENROUTER_API_KEY"
  subagent:
    type: "claude-cli"
    binary: "claude"
    # CLI spawn is scoped to data.root — agents cannot escape this directory

guardclaw:
  enabled: true
  config: "~/AcademiaOS/config/guardclaw.yaml"

observability:
  enabled: true
  dashboard_port: 8101    # Separate port for monitoring UI
  log_level: "debug"
  event_retention_hours: 72
```

### 12.3 Running Multiple Instances

```bash
# Terminal 1 — AcademiaOS
cd ~/academia-os && docker compose up -d
# → Gateway on :8100, Dashboard on :8101, Frontend on :3000

# Terminal 2 — ClawWorld
cd ~/clawworld && docker compose up -d
# → Gateway on :8200, Dashboard on :8201, Frontend on :3100

# Terminal 3 — PEENS standalone
cd ~/openclaw && docker compose up -d
# → Gateway on :8300, Dashboard on :8301

# View all running OpenClaw instances
docker ps --filter "label=openclaw"
```

Each container is completely independent. Stopping one does not affect the others. No shared memory, no shared DB, no shared message bus.

### 12.4 What Could Still Go Wrong

| Risk | Mitigation |
|---|---|
| **Port collision** | Each project's `.env` defines unique ports. `docker compose up` fails loudly if a port is taken. |
| **Wrong project** | Each container logs `PROJECT: academia-os` prominently. Frontend header shows project name. `docker ps` shows container names. |
| **Claude CLI rate limiting** | Multiple containers spawning Claude CLI simultaneously share the same membership quota. Add a host-level semaphore file (`~/.openclaw-cli-lock`) that all containers respect via a shared volume mount to serialize CLI spawns if needed. |
| **Disk space** | Vaults grow over time. Each project's `openclaw.yaml` specifies `max_vault_size_mb` with warnings at 80% threshold. |
| **Docker resource contention** | Set `mem_limit` and `cpus` in docker-compose.yml per container if running 3+ instances on a low-spec machine. |

---

## 13. Observability Dashboard

Silent failures are the worst kind of failure. The orchestrator makes routing decisions, spawns processes, injects context, and relays results — any of these can fail without the user knowing. The Observability Dashboard makes the entire pipeline visible in real-time.

### 13.1 Architecture

```
┌─────────────────────────────────────────────────────┐
│              Observability Dashboard                 │
│           (separate React app on :8101)              │
│                                                      │
│  ┌────────────────────────────────────────────────┐  │
│  │              LIVE EVENT STREAM                  │  │
│  │                                                 │  │
│  │  14:32:01 [RECV]  User message in REGM tab      │  │
│  │  14:32:01 [ROUTE] → Tutor agent selected        │  │
│  │  14:32:02 [CTX]   Assembled 3.2KB vault context │  │
│  │  14:32:02 [SPAWN] claude --model sonnet PID=892 │  │
│  │  14:32:03 [STREAM] ████████░░ streaming...      │  │
│  │  14:32:08 [DONE]  Response: 847 tokens, 6.1s    │  │
│  │  14:32:08 [VAULT] Wrote session log to vault    │  │
│  │  14:32:08 [SEND]  Response relayed to frontend  │  │
│  └────────────────────────────────────────────────┘  │
│                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────┐ │
│  │  Agent Stats  │  │  Error Log   │  │  Latency   │ │
│  │              │  │              │  │  Chart     │ │
│  │  Tutor: 12   │  │  ⚠ CLI exit  │  │            │ │
│  │  QCreat: 3   │  │    code 1    │  │  avg 4.2s  │ │
│  │  HWFin: 1    │  │    14:28:01  │  │  p95 11.3s │ │
│  │  Notes: 5    │  │              │  │            │ │
│  │  Tests: 0    │  │  ✗ OR 429    │  │  ▁▃▅▇▅▃▁  │ │
│  │              │  │    14:15:22  │  │            │ │
│  └──────────────┘  └──────────────┘  └────────────┘ │
│                                                      │
│  ┌────────────────────────────────────────────────┐  │
│  │           PIPELINE INSPECTOR                    │  │
│  │                                                 │  │
│  │  Click any event to see full details:           │  │
│  │  - Orchestrator reasoning (why this agent?)     │  │
│  │  - Full context payload sent to CLI             │  │
│  │  - Raw CLI stdout/stderr                        │  │
│  │  - Vault writes performed                       │  │
│  │  - Token counts (context in / response out)     │  │
│  └────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

### 13.2 Event Types

Every action in the pipeline emits a structured event to the observability system.

```json
{
  "timestamp": "2026-04-06T14:32:02.341Z",
  "event_type": "agent.spawn",
  "project": "academia-os",
  "class_id": "regression-methods",
  "agent": "tutor",
  "data": {
    "model": "claude-sonnet-4-20250514",
    "pid": 8921,
    "context_size_bytes": 3274,
    "context_files": ["_index.md", "context.md", "sessions/2026-04-05.md"],
    "system_prompt": "prompts/tutor.md",
    "spawn_command": "echo '...' | claude --print --system-prompt ..."
  }
}
```

**Full event taxonomy:**

| Event Type | Fires When | Key Data |
|---|---|---|
| `message.received` | User sends a message from frontend | class_id, message text, active agent |
| `orchestrator.route` | Orchestrator decides which agent to call | chosen agent, reasoning, alternatives considered |
| `context.assemble` | Vault context is assembled for injection | file list, total size, truncation warnings |
| `agent.spawn` | Claude CLI process is started | PID, model, command, context size |
| `agent.stream` | Streaming response chunks arrive | chunk count, bytes so far, elapsed time |
| `agent.complete` | Claude CLI process exits | exit code, total tokens, wall time, response size |
| `agent.error` | Claude CLI process fails | exit code, stderr, error classification |
| `vault.write` | Agent writes to Obsidian vault | file path, bytes written, write type (create/append) |
| `tool.execute` | An MCP tool is invoked | tool name, args, result summary |
| `tool.error` | An MCP tool fails | tool name, error, stack trace |
| `orchestrator.chain` | Multi-agent workflow step | chain position, source agent, target agent |
| `openrouter.request` | Orchestrator calls OpenRouter | model, tokens, latency |
| `openrouter.error` | OpenRouter call fails | HTTP status, error body, retry count |
| `guardclaw.filter` | GuardClaw blocks or modifies content | filter triggered, severity, action taken |
| `response.sent` | Final response sent to frontend | total pipeline time, agent count, success/partial/fail |

### 13.3 Dashboard Panels

**1. Live Event Stream** — Scrolling log of all events, color-coded by severity (green=success, yellow=warning, red=error). Filterable by class, agent, event type. Click any event to expand full details.

**2. Pipeline Trace View** — For any user message, shows the complete pipeline as a waterfall chart:
```
User Message ──→ Orchestrator (120ms)
                    ├──→ Context Assembly (45ms)
                    ├──→ Agent Spawn (2ms)
                    ├──→ CLI Execution ████████████ (5,800ms)
                    ├──→ Vault Write (12ms)
                    └──→ Response Relay (3ms)
                 Total: 5,982ms
```

**3. Agent Stats** — Per-agent invocation counts, success rates, average latency, token usage. Broken down by class.

**4. Error Log** — Dedicated panel for failures. Each error shows:
- What happened (CLI crash, OpenRouter 429, timeout, vault write failure)
- What the user saw (or didn't see — silent failures highlighted in red)
- Suggested fix
- One-click "retry" button for idempotent operations

**5. Context Size Monitor** — Shows how much vault context is being injected per agent call. Warns when approaching Claude CLI's context limits. Tracks context growth over time per class.

**6. Health Indicators** — Top-bar status lights:
- 🟢 OpenClaw gateway up
- 🟢 Claude CLI authenticated
- 🟢 OpenRouter reachable
- 🟢 GuardClaw active
- 🟡 R runtime (warning if Rscript not on PATH)
- 🔴 Vault disk space critical

### 13.4 Alert System

Configurable alerts for critical conditions:

```yaml
# config/observability.yaml
alerts:
  - name: "CLI spawn failure"
    condition: "event_type == 'agent.error' AND data.exit_code != 0"
    action: "toast"        # Show toast notification in dashboard
    severity: "error"

  - name: "OpenRouter rate limit"
    condition: "event_type == 'openrouter.error' AND data.http_status == 429"
    action: "toast"
    severity: "warning"
    cooldown_seconds: 60   # Don't spam

  - name: "Silent failure"
    condition: "event_type == 'agent.error' AND NOT event_type == 'response.sent' WITHIN 10s"
    action: "toast+log"
    severity: "critical"   # User got nothing back and doesn't know why

  - name: "Context overflow"
    condition: "event_type == 'context.assemble' AND data.context_size_bytes > 100000"
    action: "log"
    severity: "warning"

  - name: "Slow response"
    condition: "event_type == 'agent.complete' AND data.wall_time_ms > 30000"
    action: "log"
    severity: "info"
```

### 13.5 Implementation

The observability system is lightweight — it's an event bus built into OpenClaw core.

| Component | Implementation |
|---|---|
| **Event emitter** | Python `asyncio.Queue` in the OpenClaw process. Every pipeline step calls `emit(event)`. |
| **Event store** | SQLite DB at `~/AcademiaOS/logs/events.db`. Auto-prunes events older than `event_retention_hours`. |
| **Dashboard backend** | Separate FastAPI route group on `dashboard_port`. Serves the dashboard UI + SSE stream for live events. |
| **Dashboard frontend** | Lightweight React app (can be a single HTML file with inline JS for simplicity). Connects via SSE for live updates, REST for historical queries. |
| **Log files** | In addition to the DB, structured JSON logs written to `~/AcademiaOS/logs/pipeline.jsonl` for grep-ability. |

### 13.6 Integration with Main Frontend

The main AcademiaOS frontend gets a small indicator in the header:

```
AcademiaOS                    [🟢 All Systems] [📊 Dashboard] [Settings]
```

- **Status dot** turns yellow/red if any health check fails
- **Dashboard link** opens the observability dashboard in a new tab
- **Inline error toasts** — if a pipeline failure occurs during a user interaction, the chat shows a clear error message with a "View details in Dashboard" link instead of silently dropping the response

---

## 14. Security & Safety

| Concern | Mitigation |
|---|---|
| **Prompt injection** | GuardClaw filters all user input before it reaches any agent |
| **File system access** | Agents can only read/write within `~/AcademiaOS/`. No access to system files. |
| **R code execution** | R scripts are sandboxed to the class output directory. No network access from R. |
| **OpenRouter key exposure** | Key is server-side only. Never sent to frontend. |
| **Academic integrity** | This tool is for personal use. Homework Finisher output should be reviewed before submission. The system does not submit anything automatically. |

---

## 15. Future Considerations

| Feature | Priority | Notes |
|---|---|---|
| **VPS Deployment** | Medium | Deploy to DigitalOcean for access from any device |
| **Docker Hub Publishing** | High | Publish `openclaw/academia-os` image with CI/CD pipeline |
| **Canvas/LMS Integration** | Medium | Auto-pull assignments, due dates, rubrics from Canvas/Blackboard/Moodle |
| **First-Run Setup Wizard** | Medium | Browser-based UI for creating `classes.json` instead of editing JSON manually |
| **Spaced Repetition** | Low | Integrate Anki-style review scheduling with the progress tracker |
| **Voice Input** | Low | Whisper-based voice-to-text for hands-free tutoring |
| **Collaborative Mode** | Low | Share a class tab with a study partner |
| **Grade Prediction** | Medium | Track scores on submitted work, project final grade |
| **Auto-archival** | Low | Cron job to archive semester on end date |
| **Plugin System** | Low | Allow users to add custom agents beyond the 5 built-in ones |

---

## 16. Build Phases

### Phase 1 — Foundation (Week 1-2)
- [ ] Set up directory structure and config files
- [ ] Install and configure OpenClaw locally with GuardClaw
- [ ] Build Claude CLI Spawn Provider for OpenClaw
- [ ] Build Obsidian Vault Tool (read/write/list/search)
- [ ] Implement event emitter + SQLite event store for observability
- [ ] Verify: orchestrator can spawn a Claude CLI instance, pass context, get a response
- [ ] Verify: multi-instance port isolation works (start two OpenClaw configs simultaneously)

### Phase 2 — Agents (Week 2-3)
- [ ] Write all 5 system prompts (`prompts/*.md`)
- [ ] Implement Tutor agent (interactive mode)
- [ ] Implement Question Creator agent
- [ ] Implement Note Summarizer agent
- [ ] Implement Test Creator agent (with Question Creator chaining)
- [ ] Implement Homework Finisher agent (with R execution + doc generation)
- [ ] Verify: each agent works end-to-end via CLI before frontend

### Phase 3 — Frontend (Week 3-4)
- [ ] Scaffold React/Vite project
- [ ] Build tab system (dynamic from `classes.json`)
- [ ] Build chat interface with agent selector
- [ ] Build side panel (memory viewer, file list, quick actions)
- [ ] Integrate WebSocket connection to OpenClaw
- [ ] Build file upload component with class-specific routing
- [ ] Build Progress Tracker tab

### Phase 4 — Polish (Week 4-5)
- [ ] Implement anti-slop pipeline in Homework Finisher
- [ ] Add LaTeX/KaTeX rendering
- [ ] Add R code syntax highlighting
- [ ] Build output file download cards
- [ ] Build Observability Dashboard (live event stream, pipeline trace, error log)
- [ ] Wire health indicators into main frontend header
- [ ] Populate vaults with initial class data (textbook excerpts, past submissions)
- [ ] End-to-end testing: upload textbook → summarize → generate questions → create test → complete homework

### Phase 5 — Docker Packaging (Week 5)
- [ ] Write Dockerfile and docker-compose.yml
- [ ] Write entrypoint.sh with health checks and validation
- [ ] Create example configs (`classes.example.json`, `models.example.json`, `openclaw.example.yaml`)
- [ ] Test full lifecycle: `docker compose up` from scratch on a clean machine
- [ ] Test volume persistence: stop, update image, restart — verify vaults/config survive
- [ ] Write README.md with quickstart guide for new users
- [ ] Test on Windows (Docker Desktop), macOS (Docker Desktop), and Linux

### Phase 6 — Hardening (Week 6+)
- [ ] Add context.md auto-generation
- [ ] Add semester archival script
- [ ] Add error handling and retry logic for Claude CLI failures
- [ ] Performance tuning (context payload size optimization)
- [ ] Document the "add new class" workflow
- [ ] Publish to Docker Hub as `openclaw/academia-os`

---

## 17. Open Questions

1. **Claude CLI `--resume` support** — Does the current CLI support session resumption for interactive tutoring? If not, the tutor agent will need to reconstruct context from vault on each spawn.
2. **Claude CLI model flag** — Verify that `--model` flag works with membership-authenticated CLI and supports Opus.
3. **R-Studio vs Rscript** — The spec assumes `Rscript` CLI execution. If R-Studio IDE integration is needed (e.g. rendering R Markdown), additional tooling is required.
4. **Concurrent agent spawns** — Multiple CLI instances share the same membership quota. Need to verify rate limits. The global semaphore in Section 12.4 mitigates this but may serialize too aggressively.
5. **GuardClaw configuration** — What safety rules should be active? Academic content should be permissive but prevent prompt injection and data exfiltration.
6. **Observability storage** — SQLite for events is fine locally, but if deploying to VPS later, consider switching to a proper time-series store or just shipping JSONL to a log aggregator.

---

*This spec is a living document. Update as architecture decisions are made during build.*

---

## 18. Build Directive

**Scaffold as needed.** If something seems off during implementation — a dependency doesn't behave as expected, a tool doesn't support an assumed flag, an integration path hits a wall — stop, research the fix, and **update this spec before continuing**. This document is the single source of truth. Any architectural change, workaround, or deviation that isn't reflected here doesn't exist. Keep this spec accurate at all times so any agent or collaborator picking up the project can trust it completely.
