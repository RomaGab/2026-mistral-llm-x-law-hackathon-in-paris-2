# Frontend project instructions

## Goal and scope

The app is named `pivot` (lowercase).

Develop the visuals and frontend interactions for a Next.js + React + TypeScript
dashboard during an eight-hour hackathon. The user is responsible for the visual
part of the project.

Product context: users enter a prompt and add documents; the backend extracts facts
with Mistral, and the calculator returns a completed dossier. Use the contracts
and example dossiers for UI work until backend integration is available.
AI calls, document extraction, and analysis calculations are owned by other contributors.

Use the supplied mockup as the initial visual reference:

- A balance indicator between opposing conclusions.
- A matrix comparing facts across cases or documents, with a visible legend.
- Editable case facts, including highlighted pivotal facts.
- Match the inspected Mistral Studio UI: Inter, workspace `#fbfbf8`, white surfaces, text `#201f1c`, orange `#fa500f`, and thin translucent borders. The intake has the pivot logo, a short heading and supporting line above a minimal prompt composer with attachment controls. Omit the sidebar, avatar, logo tagline, and stepper. The supplied dashboard screenshot establishes behavior and panel structure.

The sample facts, cases, score, and interval are fixture data, not fixed product results.

## Hackathon delivery

- Prioritize a polished, navigable visual demo: prompt entry, document selection, dashboard display, and editable fact controls.
- Work in small increments and keep the app runnable after each change.
- Choose the simplest implementation that meets the visual need; avoid speculative abstractions and unnecessary dependencies.
- Make routine frontend choices autonomously. Ask about visual decisions only when the reference and project context do not establish a reasonable default.
- Backend details are not questions for this contributor. Record integration assumptions briefly and continue with fixtures.

## Stack and organization

- The scaffold uses Next.js App Router, React, strict TypeScript, ESLint, and npm. Follow the installed versions in `package.json` and `package-lock.json`.
- Commands: `npm run dev`, `npm run lint`, `npm run typecheck`, `npm run build`, and `npm start` after building.
- Use plain CSS with shared design tokens in `src/app/globals.css` and CSS Modules for component styles as needed.
- Use Feather icons from `react-icons/fi` for interface controls; keep the custom pivot brand mark.
- Start with React state and props; add a state library only for a concrete need.
- Initial layout: routes in `src/app`, shared UI in `src/components/ui`, dashboard components in `src/components/dashboard`, view models in `src/types/dashboard.ts`, and fixtures in `src/mocks/dashboard.ts`.
- Reuse equivalent existing folders rather than reorganizing the project to match this suggestion.
- Use Server Components by default and client boundaries for interactive state, event handlers, and browser APIs.

## Shared components and React practices

- Search for existing components, utilities, and types before creating another.
- Reuse components for repeated panels, controls, matrix cells, and status displays. Keep props explicit and components focused.
- Render the fact list from data through one reusable `FactToggle` component; do not copy JSX for each fact.
- Extract duplicated behavior into a utility or hook when it has real repeated use. Avoid building a generic dashboard framework during the hackathon.
- Give shared dashboard state one owner. Use controlled inputs with values and callbacks, and lift coordinated state to the nearest common parent.
- Derive values from existing state instead of storing duplicates. Update state immutably and use functional setters when depending on previous state.
- Use effects to synchronize with external systems, not to maintain redundant state or perform actions that belong in event handlers.
- Use stable IDs for list keys and fact updates; avoid editable labels or array indexes as identity.
- Add memoization when there is a demonstrated need.

## Types, mock data, and integration

- Read `distinguo-architecture-contrats.md` for workflow and API behavior; `contracts/` is the source of truth. Preserve the shared schemas, examples, and calculator contracts.
- Facts are `true`, `false`, or `null` (unknown). Follow factor labels and order from the grid. Render factor explanations from `resultat.facteurs`, ordered pivots from `resultat.pivots`, and combined scenarios from `resultat.pivots_combines`; never calculate these in the frontend.
- Toggle overrides request a simulation through `POST /cas/{id}/analyse`; permanent fact confirmation uses `PATCH /cas/{id}`. The frontend performs no prediction or pivot calculation.
- Intake uses PDF, TXT, and DOCX. Map the prompt to `question`, optional context to `description`, and court to `ressort`; real `document_ids` come from backend upload responses.
- The intake preview enforces a local 20 Mo file-size guard with validation feedback and keeps selected files in memory until backend integration.
- Use typed props and callbacks; prefer inference for obvious local values. Avoid `any` and unchecked assertions that hide invalid data.
- Keep fixtures separate from rendering code. Use the same components for fixtures and eventual real data.
- Fact labels and values come from data. The UI renders known components rather than executing AI-generated JSX or HTML.
- Keep original fact values separate from user overrides. Represent unknown facts explicitly rather than treating them as false.
- Expose callbacks such as `onSubmit` and `onFactChange` for later integration. Keep mock behavior in the demo container or adapter.
- Document selection currently demonstrates file selection, removal, and filenames. Show extraction and upload progress only as explicit demo states until connected.
- Changing a toggle updates its UI state and invokes its callback. Any simulated balance or matrix changes must be deterministic fixture behavior and clearly labeled as demo results.
- Treat example probabilities, intervals, and citations as visibly labeled mock content. Display real analysis values when supplied by the integration.

## Visual quality and accessibility

- Write user-facing interface content in English, including placeholders, validation messages, metadata, and accessible labels.
- Use shared tokens for colors, spacing, typography, borders, and radii. Avoid repeating slightly different values across components.
- Preserve the reference's panel hierarchy while adapting the layout to desktop and mobile. Stack panels on narrow screens and allow wide matrices to scroll.
- Keep content readable with long fact labels, many rows, missing values, and empty lists.
- Use semantic buttons, labeled controls, visible keyboard focus, and native checkbox behavior for fact toggles.
- Distinguish matrix states through symbols or text as well as color. Keep the legend visible and ensure sufficient contrast.
- Provide reusable empty, loading, success, and error states, with fixtures to preview them before integration.
- Make the prompt, document selection, and fact controls visibly respond to user actions.

## Verification and working agreements

- After code changes, run the relevant available type checks, lint, tests, and build using the actual `package.json` scripts. Report missing or blocked checks accurately.
- Prioritize visual review at desktop and mobile sizes, keyboard interaction, and toggle behavior. Add focused tests for nontrivial shared logic when useful; avoid a broad test suite for this visual hackathon scope.
- Keep changes scoped to the requested task and preserve other contributors' edits.
- Report what changed, what was checked, and any mocked behavior or remaining integration points.
- Commits, publishing, and deployment require a user request.
- Update these instructions when the team establishes tooling or integration contracts.

## Official references

Consult these when relevant to the change:

- [Next.js server and client components](https://nextjs.org/docs/app/getting-started/server-and-client-components)
- [React state structure](https://react.dev/learn/choosing-the-state-structure)
- [TypeScript strict mode](https://www.typescriptlang.org/tsconfig/strict.html)

<!-- BEGIN:nextjs-agent-rules -->

# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` (resolved from this file's directory; in monorepos the `next` package may not be visible from the repo root) before writing any code. Heed deprecation notices.

This block is written and re-added by `next dev` — verify at `node_modules/next/dist/server/lib/generate-agent-files.js`. Removing it from a diff only re-creates the uncommitted change; committing it with your work keeps the tree clean.

<!-- END:nextjs-agent-rules -->
