This is a [Next.js](https://nextjs.org) project bootstrapped with [`create-next-app`](https://nextjs.org/docs/app/api-reference/cli/create-next-app).

## bagCoin — mock vs API

- **`src/lib/feature-flags.ts` — `USE_MOCK_DATA`:** when `true`, server RSC fetchers (`api-server`) and the matching hooks use `src/data/seed.ts` via `mock-api` (no backend required for many list views).
- Set **`USE_MOCK_DATA` to `false`** for real FastAPI data; set **`API_URL`** to your API base (e.g. `http://localhost:8000/api/v1`). Client requests use same-origin `/api/v1` and are proxied by Next rewrites.
- **Vitest** forces `USE_MOCK_DATA: false` in `src/__tests__/setup.ts` so unit tests use MSW against the client API shape.
- **Playwright** starts `pnpm run dev` with **`API_URL` forced to `http://localhost:8000/api/v1`** (so `page.route("**/api/v1/...")` matches). For **`CI=1`**, free port `3000` first. With **`reuseExistingServer`**, restart dev if e2e mocks fail (child env only applies to the server Playwright spawns).

## Getting Started

First, run the development server:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

You can start editing the page by modifying `app/page.tsx`. The page auto-updates as you edit the file.

This project uses [`next/font`](https://nextjs.org/docs/app/building-your-application/optimizing/fonts) to automatically optimize and load [Geist](https://vercel.com/font), a new font family for Vercel.

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.
