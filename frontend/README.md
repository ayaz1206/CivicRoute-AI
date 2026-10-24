# CivicRoute AI — Frontend

Next.js (App Router) + TypeScript + Tailwind CSS. M0 foundation: app shell and a
home page that shows live backend health status.

## Develop

```bash
npm install
cp .env.local.example .env.local
npm run dev
```

Open http://localhost:3000.

## Scripts

| Script          | Purpose                     |
| --------------- | --------------------------- |
| `npm run dev`   | Start the dev server        |
| `npm run build` | Production build            |
| `npm run start` | Serve the production build  |
| `npm run lint`  | ESLint                      |
| `npm run typecheck` | TypeScript, no emit     |

## Environment

| Variable              | Default                 | Purpose          |
| --------------------- | ----------------------- | ---------------- |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Backend base URL |
