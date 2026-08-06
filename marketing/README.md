# JobPilot Marketing (Next.js SSR / ISR)

SEO-friendly marketing site separate from the Vite SPA app.

```bash
cd marketing
npm install
npm run dev   # http://localhost:3002
```

- **SSR** via Next.js App Router
- **ISR** via `export const revalidate = 3600` on the homepage
- Point `NEXT_PUBLIC_APP_URL` at the main app (default `http://localhost:3000`)
