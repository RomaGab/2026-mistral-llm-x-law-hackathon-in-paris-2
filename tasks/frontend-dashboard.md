# Dashboard UI preview

The intake's three-second preparation preview opens the example dashboard. `/dashboard`
also opens it directly. The dashboard omits the back/new-case navigation control.
The example uses fictional precedents and is not an analysis of submitted documents.

## Data and interaction

- The homepage is the style reference: shared Inter typography, 24px page headings,
  12px white surfaces, 8px controls, light borders and dark selected actions. The
  balance uses a white summary surface and the question lives in a permanent
  bottom-right panel; orange is reserved for small accents.
  Appearance tokens and motion durations live in `src/app/globals.css` and are used
  by both intake and dashboard components.
- Dashboard entrance uses the homepage's 320ms, 6px rise and fade. Floating panels
  enter in 220ms; evidence panels finish their 200ms upward exit before unmounting. Questions and
  percentages fade when updated; radio selection slides between the three choices.
  Reduced motion removes movement and completes exit lifecycles in 1ms. No entrance
  transform is applied to the table or an ancestor of its sticky header.
- The initial view shows the balance, one permanently floating pivotal question, and the expanded
  Facts & precedents table with no disclosure control. The header contains only the app brand. Section numbers, the demo
  badge, simulation/reset toolbar, balance status/info button, and question helper copy
  are omitted.
- The pivotal question appears only in the bottom-right panel from the initial render
  and stays there while scrolling, on desktop and mobile. The balance occupies the
  top summary. An active override adds the changed fact, original-to-current estimate, and
  percentage-point difference beneath the balance. The interval remains visible.
- When the main percentage scrolls above the viewport, a compact estimate appears at
  the bottom right and follows fact changes. It hides as soon as the main percentage
  re-enters view. On mobile it does not appear before the user reaches the balance.
  The duplicate is visual only; the existing result status handles screen-reader updates.
- The permanent bottom-right question has working Yes / No / Unknown controls and
  follows the selected table fact. Only the percentage uses scroll-based visibility;
  the question never disappears when returning to the top. The card's measured height
  reserves space beneath the last rows and above it for desktop evidence; the table
  header remains at the top.
- Shared contract IDs are preserved; frontend labels translate the grid into English.
  The merged table groups originally unknown facts first,
  retaining grid order within each group and keeping rows stable during simulation.
- All fact rows are displayed at their natural height; only the page scrolls vertically.
  Horizontal table scrolling remains available when the columns exceed the viewport.
- The actual table header stays at the viewport top while scrolling through the rows
  and leaves with the table's bottom edge. It follows horizontal panning with the cells.
  Native CSS handles vertical sticking; no scroll-driven transforms move the header.
  A shared column grid and synchronized horizontal scrolling keep its labels aligned
  with the body, with one semantic table and no duplicate header controls.
  Precedent headers use check-circle icons for retained decisions and cross-circle icons
  for excluded decisions, alongside the text labels.
- Your case cells open native Yes / No / Unknown selectors. Precedent cells show their
  recorded values as buttons and open a right-hand evidence panel; they cannot be edited.
  Selecting a row label opens the case evidence, and precedent headings open decision summaries.
- Your case dropdowns are borderless with transparent backgrounds and bold values,
  including Unknown. Keyboard focus retains a visible outline. Clicking the cell or focusing its
  selector selects that fact and updates the focused question immediately, without
  changing its value or the simulation until an option is chosen.
  It also dismisses any open evidence panel with its exit animation, clears the
  precedent selection, and keeps focus on the case selector rather than returning
  to the precedent button. Explicit Close and Escape still restore the opening button.
- Your case is emphasized with an edit icon, Editable header label, neutral shaded column,
  and bold values with dropdown chevrons. Precedent cells use information icons and read-only
  accessible labels so inspecting evidence is visually distinct from changing facts.
- Precedent headers highlight retention changes against the original case as Newly excluded
  or Newly retained. See why opens the floating panel with the returned reasons and a change
  label. The panel never opens automatically after editing a fact.
- The workspace is horizontally centered. The table uses roomy rows, thin vertical and horizontal
  grid lines and left-aligned values. Fact labels are plain text without a background
  or border; hover and active evidence use an underline.
- The table uses the available workspace width. Evidence floats over the right side in
  a rounded, shadowed panel, without reserving a column or resizing the table. Under
  768px, the floating panel is modal with a backdrop and viewport-safe margins. A selected-cell highlight
  identifies the current evidence; Close or Escape restores focus to the opening button.
  Case edits update the open comparison; selecting another cell replaces the panel content.
- The focused question uses native radio choices and stays synchronized with the table.
  Both controls share the same tri-state options; Unknown remains `null`.
- A simulation changes one fact relative to the original example. A change to another fact replaces
  the previous simulation. Choosing the original value restores the original case. No facts are saved.
- The original and all 36 alternative single-fact responses are generated by the existing Python
  calculator, then checked with the shared dossier validator. The browser only selects a response.
- Regenerate with `uv run python scripts/generate-dashboard-fixtures.py` from the repository root.
- The result supplies probabilities, interval bounds and level, uncertainty, ordered pivot IDs,
  retained decisions, alignment, and optional v1.3 decision explanations.
- Evidence excerpts and exclusion reasons are displayed in English through
  `src/lib/dashboard/source-copy.ts`. Translated quotations are labeled accordingly;
  the shared French sources remain unchanged. Source warnings remain in the fixture data.
- Backend integration must provide English text or extend the reviewed translations.
  Unrecognized excerpts and reasons show an English unavailable message rather than raw text.
- Multiple-factor simulations are not supported by the fixture adapter. Combined pivots can be
  displayed when returned but require backend integration to explore.

## Integration

Replace `getDashboardPreview` in `src/mocks/dashboard.ts` with the analysis API adapter.
`CaseFactsTable.onFactChange` and `PivotInsight.onFactChange` expose factor IDs and tri-state values.
Production flow must confirm extracted facts (`PATCH /cas/{id}`) before analysis; dashboard changes
are temporary overrides sent to `POST /cas/{id}/analyse`. Do not persist them through PATCH.
Keep extraction, error/retry states, confirmed source facts, and scenario overrides separate.

## Verification

Run lint, typecheck, and production build. Check the following in Safari:

- Preparation opens the dashboard; there is no back button above the title.
- Scroll past the main percentage: the bottom-right estimate appears, stays in sync
  when editing facts, and disappears on scrolling back. Desktop evidence leaves room
  for the estimate, and page bottom padding keeps the last table rows reachable.
- The question appears only once, in the bottom-right panel, immediately on entry.
  All three choices update the table and estimate. Clicking or focusing another Your
  case cell selects it and updates the question without changing its value. Scrolling
  back hides only the floating percentage; the question remains available. Mobile
  must not show a floating percentage while its original is still below view.
- Original example: 47% employment estimate, 95% interval 8–91%, uncertain, four retained decisions.
- Account suspension / Yes: 72%, 95% interval 16–97%, still uncertain, three retained decisions;
  before/after reads 47% → 72%, +25 points. Paris Appeal 2021 becomes newly excluded.
- Account suspension / No: 24%; Unknown returns to the original response.
- Changing a different fact replaces the previous override, rather than compounding it.
- Decision details explain exclusions; unknown arguments are distinct from opposite arguments.
- Native radios, cell selectors, and evidence buttons work from the keyboard; the table
  displays all 18 rows with no internal vertical scrollbar and permits horizontal scrolling
  on smaller screens. Opening evidence does not insert or expand table rows.
- Scroll the full table: its single header stays at the top until the last row passes.
  Resize and pan horizontally while pinned; labels must stay aligned with their columns.
  Header buttons still open evidence, and status icons update after a fact change.
- Your case is the only table column with select controls. Its editable label and
  bold, borderless inputs stay visible while precedent cells use information icons.
- Returning a fact to its original value removes the estimate delta and changed-precedent
  labels. An override with no status changes must not highlight any precedent as changed.
- Desktop evidence permits continued table interaction. On smaller screens, the panel
  traps focus and locks background scrolling. Closing it restores focus and page scrolling;
  switching across the 768px breakpoint updates the presentation while the panel is open.
- The focused question and Your case cells stay in sync; precedent values remain unchanged.
- Facts & precedents is always visible; the balance status and info button are absent.
- Compare the dashboard with the homepage: same heading scale, neutral surfaces,
  corner radii, control styling and easing. Panel closing keeps content present until
  the exit completes; reopening during exit cancels the close. Verify keyboard focus
  restoration and the reduced-motion setting as well as normal animation.
