# pivot

Next.js App Router frontend with React, strict TypeScript, ESLint, and plain CSS.
The intake screen contains a prompt composer with PDF/TXT/DOCX selection, drag and
drop, and removable attachments. On sending, the heading and composer fade away
before a small pivot mark blends into pixel shapes beside “Preparing your case…”.
Its square blocks move and merge at full opacity to form each shape.
Below the heading, a scrollable three-line window follows illustrative progress
sentences with grey task icons. Text aligns with the heading, and the lower half
of the third row fades to suggest scrolling. Scrolling back pauses automatic
following until the user returns to the latest updates. The document-reading step is shown
only when files are attached. Copy and timing live in `src/mocks/case-preparation.ts`;
the display accepts steps and a current step for eventual backend integration.
This frontend preview lasts three seconds, then restores the draft and attachments.
Preview timers are cleaned up on unmount; backend events will replace them.
Files remain in memory; backend upload, extraction, and analysis are not connected.
Reduced-motion preferences disable the loading animation and fades.

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
