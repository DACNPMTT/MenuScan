# MenuScan Frontend

React + TypeScript app scaffolded with Vite.

## Scripts

```bash
npm install
npm run dev
npm run build
npm run lint
```

## Structure

```text
src/
  app/                 App composition, providers, route composition
  features/            Product features grouped by domain
  layouts/             Page shells and reusable layout frames
  pages/               Route-level pages
  shared/components/   Reusable presentational components
  shared/hooks/        Reusable React hooks
  shared/lib/          Small framework-agnostic utilities
  styles/              Global CSS and design tokens
```

Use direct imports with the `@/` alias, for example:

```ts
import { UploadPanel } from '@/features/menu-scan/components/UploadPanel'
```
