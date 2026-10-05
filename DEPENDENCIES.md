# MARKUS AI — Dependency Overview

Two install targets: **backend** (`markus-next/package.json`, Next.js/TypeScript) and
**frontend** (`frontend/package.json`, Vite/React).

## Backend (`markus-next`) — `npm install`

| Subsystem | Packages | Why |
|---|---|---|
| Web Framework | `next`, `react`, `react-dom`, `typescript` | Next.js App Router API server & route handlers |
| AI Gateway | `openai`, `dotenv` | OmniRoute client and direct LLM multi-provider streaming/fallback |
| Storage & RAG | `better-sqlite3`, `@types/better-sqlite3` | Persistent SQLite memory storage with WAL mode, in-memory TF-IDF vector store |
| System & Utilities | `systeminformation`, `bcryptjs`, `uuid`, `simple-git`, `axios` | System metrics, permissions, ID generation, git integration |
| UI & Visuals | `lucide-react`, `framer-motion`, `gsap`, `three`, `@react-three/fiber`, `@react-three/drei` | Dashboard and 3D assistant visualization |
| Markdown & Syntax | `react-markdown`, `remark-gfm`, `rehype-highlight`, `@monaco-editor/react` | Formatted AI output and integrated editor |

> **Note:** The legacy Python/FastAPI backend was fully migrated and replaced by `markus-next`. No Python environment, `pip`, or `requirements.txt` is required.

## Frontend (Node) — `npm install`

| Subsystem | Packages | Why |
|---|---|---|
| Framework | `react`, `react-dom`, `react-router-dom`, `vite`, `typescript`, `@vitejs/plugin-react` | App shell, routing, build tooling |
| Styling | `tailwindcss`, `postcss`, `autoprefixer`, `tailwindcss-animate`, `clsx`, `tailwind-merge`, `class-variance-authority` | Design system (glassmorphism, gradients, states from `MARKUS.md`) |
| Motion / orb | `framer-motion`, `gsap`, `three`, `@react-three/fiber`, `@react-three/drei`, `@studio-freight/lenis` | AI Orb animation states, particle system, smooth scroll |
| UI components | `@radix-ui/*`, `lucide-react` | Accessible primitives (dialog, tabs, tooltip...) + icon set (design system says no emojis) |
| Chat / code | `react-markdown`, `remark-gfm`, `rehype-highlight`, `@monaco-editor/react` | Markdown rendering, syntax highlighting, integrated code editor |
| State / data | `zustand`, `axios`, `socket.io-client` | Client state, REST calls, WebSocket streaming from the backend |
| Auth | `better-auth` | Matches the auth choice in `MARKUS.md` §6/§8 |
| Types/lint | `@types/react`, `@types/react-dom`, `@types/three`, `eslint`, `eslint-plugin-react-hooks` | Dev-time only |

## What you don't need to install yourself

OmniRoute itself is a separate service (its own repo:
https://github.com/blessedalways/omniroute) — it's a dependency of the
*system*, not a pip/npm package. Run it separately and point
`OMNIROUTE_BASE_URL=http://localhost:20128/v1` at it; the `openai` package
above is the only thing the backend needs to talk to it.
