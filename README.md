# pivot

Next.js App Router frontend with React, strict TypeScript, ESLint, and plain CSS.
The intake screen contains a prompt composer with PDF/TXT/DOCX selection, drag and
drop, and removable attachments. Files remain in memory; the send action only
acknowledges the local preview. Backend upload and analysis are not connected.

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
