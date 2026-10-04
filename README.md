# pivot

Next.js App Router frontend with React, strict TypeScript, ESLint, and plain CSS.
The intake screen contains a prompt composer with PDF/TXT/DOCX selection, drag and
drop, and removable attachments. On send, the documents are uploaded, the backend extracts
the facts with Mistral, and the dashboard opens on the real analysis. The `/dashboard` route
still shows the frozen fixtures, for offline demos.

The design tokens were inspected in Mistral Studio using Safari Web Inspector.
Inter is self-hosted, with its license in `public/fonts/Inter-LICENSE.txt`.

## Development

```bash
npm ci
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

Start editing `src/app/page.tsx`. Shared design tokens and base styles are in
`src/app/globals.css`. Project conventions are in [AGENTS.md](AGENTS.md).

## Run with the backend

```bash
uv sync                                                         # Python dependencies (repo root)
uv run --env-file .env uvicorn back.api:app --port 8000          # API + calculator (needs MISTRAL_API_KEY in .env)
npm run dev                                                     # front on http://localhost:3000
```

The front calls `NEXT_PUBLIC_API_URL` (default `http://localhost:8000`, see `.env.example`).
Only decisions validated in `data/fiches/` are used by the analysis.

## Checks

```bash
npm run lint
npm run typecheck
npm run build
```

## Production preview

After a successful build, run `npm start`.

See the [official Next.js installation guide](https://nextjs.org/docs/app/getting-started/installation)
for framework setup details.
