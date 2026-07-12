<p align="center">
  <img src="doc/assets/menuscan-banner.jpg" alt="MenuScan Banner" width="100%" style="border-radius: 16px; border: 1px solid #d9dee7; box-shadow: 0 18px 48px rgba(15, 23, 42, 0.18);" />
</p>

<h1 align="center">MenuScan</h1>

<p align="center">
  AI-powered menu scanning platform that converts restaurant menu images into structured digital menu data.
</p>

<p align="center">
  <strong>Menu Image -> AI Processing -> Structured Digital Menu</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/status-active-success" alt="Project Status" />
  <img src="https://img.shields.io/badge/python-3.12+-3776AB?logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/react-19-61DAFB?logo=react&logoColor=111111" alt="React" />
  <img src="https://img.shields.io/badge/vite-8-646CFF?logo=vite&logoColor=white" alt="Vite" />
  <img src="https://img.shields.io/badge/license-MIT-blue" alt="License" />
</p>

---

# Overview

MenuScan helps restaurants, food platforms, and hospitality teams digitize menus from images without manual data entry.

Restaurant menus often exist as photos, scans, PDFs, or printed material. Turning those menus into clean digital data is usually slow, inconsistent, and expensive. MenuScan streamlines this workflow by using OCR and AI analysis to extract menu sections, items, descriptions, prices, and metadata from raw menu images.

The result is structured menu data that can be reviewed, stored, searched, published, or integrated into ordering systems, POS tools, websites, and internal dashboards.

The agreed MVP scope and business rules are documented in
[MenuScan MVP Contract](doc/content/mvp-contract.md).

---

# Features

- **Menu Image Upload**  
  Upload restaurant menu images or PDF files for automated processing.

- **OCR & AI Analysis**  
  Detect text, menu sections, prices, item names, descriptions, and layout context.

- **Structured Menu Extraction**  
  Convert unstructured visual menu content into predictable digital records.

- **Review-Friendly Workflow**  
  Prepare extracted data for human review, correction, and approval.

- **API-Ready Output**  
  Generate structured JSON suitable for backend storage, integrations, and frontend rendering.

- **Scalable Project Architecture**  
  Clean separation between frontend, backend, infrastructure, documentation, and AI workflow design.

---

# Contributors

<a href="https://github.com/DACNPMTT/MenuScan/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=DACNPMTT/MenuScan" />
</a>

---

# System Workflow

```text
Menu Image
   ↓
OCR & AI Analysis
   ↓
Menu Extraction
   ↓
Structured Data Generation
```

## Workflow Details

1. **Menu Image**  
   A restaurant menu is uploaded as an image or document.

2. **OCR & AI Analysis**  
   The system extracts text and analyzes visual structure, grouping related content.

3. **Menu Extraction**  
   Menu sections, item names, descriptions, prices, and optional metadata are identified.

4. **Structured Data Generation**  
   The extracted result is normalized into structured digital menu data.

---

# Architecture

MenuScan is designed as a modular SaaS-style application with clear ownership boundaries.

```text
Client Application
   ↓
Backend API
   ↓
AI Processing Layer
   ↓
Structured Data Store
```

## Architectural Principles

- **Frontend-first workflow clarity**  
  The React frontend is organized around product features and reusable shared components.

- **Backend API boundary**  
  The Python backend is responsible for request handling, processing orchestration, validation, and data delivery.

- **AI processing isolation**  
  OCR and AI extraction logic can evolve independently from the API and UI layers.

- **Structured output contract**  
  Extracted menu data follows a predictable JSON shape for integration and review.

- **Deployment-ready separation**  
  Infrastructure, documentation, app code, and frontend code are kept in dedicated directories.

---

# Tech Stack

| Layer              | Technology                 | Purpose                                           |
| ------------------ | -------------------------- | ------------------------------------------------- |
| Frontend           | React                      | Interactive web application                       |
| Frontend Build     | Vite                       | Fast development and production bundling          |
| Language           | TypeScript                 | Type-safe frontend development                    |
| Backend            | Python                     | API and AI processing orchestration               |
| Package Management | npm, uv                    | Frontend and Python dependency management         |
| AI Processing      | OCR + LLM pipeline         | Menu text extraction and structuring              |
| Documentation      | Markdown                   | Architecture, database, and product documentation |
| Infrastructure     | Docker / deployment config | Future production deployment support              |

---

# Screenshots

## Dashboard

<p align="center">
  <img src="doc/assets/screenshot-dashboard.svg" alt="MenuScan Dashboard Screenshot" width="100%" />
</p>

## Menu Upload Flow

<p align="center">
  <img src="doc/assets/screenshot-upload.svg" alt="Menu Upload Screenshot" width="100%" />
</p>

## Structured Menu Output

<p align="center">
  <img src="doc/assets/screenshot-result.svg" alt="Structured Menu Output Screenshot" width="100%" />
</p>

---

# Project Structure

```text
MenuScan/
├── app/
│   ├── main.py
│   ├── pyproject.toml
│   ├── uv.lock
│   ├── Dockerfile.dev
│   └── README.md
│
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── app/
│   │   │   ├── providers/
│   │   │   └── routes/
│   │   ├── features/
│   │   │   └── menu-scan/
│   │   ├── layouts/
│   │   ├── pages/
│   │   ├── shared/
│   │   │   ├── components/
│   │   │   ├── hooks/
│   │   │   └── lib/
│   │   └── styles/
│   ├── package.json
│   ├── Dockerfile.dev
│   ├── vite.config.ts
│   └── README.md
│
├── doc/
│   └── ai/
│       ├── architecture.md
│       ├── database.md
│       └── frontend.md
│
├── infras/
├── .github/
├── env/                    ← Local environment templates
├── docker-compose.yml      ← Local DB/Redis dependencies
├── Makefile                ← Local task runner
├── .gitignore
└── README.md
```

---

# Getting Started

## Prerequisites

- Docker Desktop for local dependency containers.
- GNU Make. On Windows, use Git Bash, WSL, or another GNU Make installation.
- Python 3.12+ and [uv](https://docs.astral.sh/uv/) for the backend.
- Node.js 22+ and npm for the frontend.

## Quick Start

```bash
git clone https://github.com/DACNPMTT/MenuScan.git
cd MenuScan
make env ENV=local
make install-be
make install-fe
make deps ENV=local
```

Run the backend and frontend in separate terminals:

```bash
make backend ENV=local
make frontend ENV=local
```

Open:

| Service  | URL                            |
| -------- | ------------------------------ |
| Frontend | `http://localhost:5173`        |
| Backend  | `http://localhost:8000`        |
| Health   | `http://localhost:8000/health` |
| Database | `localhost:55432`              |
| Redis    | `localhost:6379`               |

## Dev Commands

`Makefile` is the canonical local task runner. The root `docker-compose.yml`
only starts development dependencies; backend and frontend run natively.

```bash
make env ENV=local        # Create env/.env.local from env/.env.local.example
make deps ENV=local       # Start Postgres and Redis
make deps-down ENV=local  # Stop local dependency containers
make deps-reset ENV=local # Recreate dependencies and remove volumes
make deps-logs ENV=local  # Tail dependency logs
make deps-ps ENV=local    # Show dependency container status
make backend ENV=local    # Run migrations, then start FastAPI
make frontend ENV=local   # Start Vite
make migrate ENV=local    # Apply Alembic migrations
make test-be ENV=local    # Run backend tests
make lint                 # Run backend and frontend lint
```

## Environment Files

Local environment templates live in `env/`. Real env files such as
`env/.env.local` are gitignored.

```bash
make env ENV=local
```

The local defaults point the backend at Postgres on `localhost:55432` and Redis
on `localhost:6379`.

## Compose and CI/CD

The root `docker-compose.yml` is intentionally limited to local dependency
containers. The `infras/` directory is reserved for full-container or future
CI/CD deployment compose configuration.

---

# API Examples

## Upload Menu Image

```http
POST /api/v1/scans
Content-Type: multipart/form-data
Authorization: Bearer <access_token>
```

### Example Request

```bash
curl -X POST http://127.0.0.1:8000/api/v1/scans \
  -H "Authorization: Bearer <access_token>" \
  -F "file=@menu.jpg" \
  -F "target_language=en"
```

### Example Response

```json
{
  "success": true,
  "data": {
    "id": "71151f64-39c7-4419-810a-c0835bafe341",
    "status": "PENDING",
    "source": {
      "file_name": "menu.jpg",
      "mime_type": "image/jpeg",
      "file_size": 2458912
    },
    "target_language": "en"
  },
  "meta": null
}
```

---

# Future Improvements

- Add drag-and-drop file upload with progress tracking.
- Support batch menu processing.
- Add human review and correction workflow.
- Store scan history and versioned menu records.
- Add restaurant workspace management.
- Export structured menus to CSV, JSON, and POS-friendly formats.
- Add confidence scores for extracted fields.
- Support multilingual menus.
- Add automated image preprocessing for low-quality photos.
- Deploy production-ready API and frontend environments.

---
