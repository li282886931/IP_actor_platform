# Frontend Workbench Redesign

## Goal

Convert the current dual-preview presentation into a production-style desktop workbench. Remove every mini-program and phone-preview surface, make the desktop application the only primary experience, and improve consistency across all existing routes and roles.

## Scope

- Remove the mini-program label, phone frame, phone mock content, and two-column showcase layout from `App.jsx`.
- Retain the existing login gate and role selector for C, B, Brand, and G roles.
- Use a stable desktop shell with:
  - persistent role-aware sidebar navigation,
  - compact top header,
  - responsive main content area,
  - route-level page title and actions.
- Connect the existing Home, Artist, Generate, and ShowDetail routes to the shell.
- Consolidate duplicated visual rules from `styles.css` and `design.css`.
- Replace layout-critical inline styles with reusable classes.
- Preserve existing API contracts and backend behavior.

## Information Architecture

The authenticated application uses one shared shell:

1. Sidebar: product identity and role-specific primary navigation.
2. Header: current section, role switcher, platform status, and account action.
3. Main content: route output with a constrained readable width where appropriate.

Role navigation:

- C: Discover, Artist Search, AI Recommendation.
- B: Workbench, Artist Intelligence, AI Promotion.
- Brand: Brand Overview, Audience/Artist Intelligence, AI Campaign.
- G: City Overview, Artist Intelligence, AI Promotion.

Only routes that exist in the application will be linked. Placeholder links such as `/community`, `/tickets`, and `/heatmap` will not appear until corresponding pages exist.

## Visual Direction

- Quiet operational interface rather than a product showcase.
- Neutral dark shell with clear light/dark surface contrast and restrained violet accent.
- Cards use small radii and are reserved for metrics, repeated records, and framed tools.
- No nested cards, decorative gradient blobs, phone mockups, or oversized marketing copy.
- Dense but readable typography, stable grid tracks, and explicit responsive breakpoints.
- Use familiar text labels and lightweight symbols already supported by the project; no new icon dependency is required for this pass.

## Component Changes

- `App.jsx`: authentication gate plus authenticated application shell only.
- `Sidebar.jsx`: route-aware navigation generated from role metadata.
- `Home.jsx`: role-specific dashboard content inside consistent page sections.
- `Artist.jsx`: query form, result metrics, empty/loading/error states.
- `Generate.jsx`: structured form and generated-result panel.
- `ShowDetail.jsx`: responsive details and booking panel without fixed overlays on desktop.
- `ShowCard.jsx`: consistent show summary with date, venue, status, and price.
- `styles.css`: global reset, tokens, shell, shared components, and route layouts.
- `design.css`: removed after required styles are consolidated.

## Data And State

- Login and selected role remain persisted in local storage.
- Role changes update navigation and current page presentation immediately.
- Existing Axios API functions remain unchanged.
- Pages retain local loading/result/error state.
- Unknown routes render a safe fallback or redirect to the dashboard.

## Responsive Behavior

- Desktop: fixed-width sidebar and fluid main workspace.
- Tablet: narrower sidebar and reduced grid columns.
- Mobile: sidebar collapses into a compact top navigation; content becomes one column.
- No element depends on viewport-scaled font sizes.
- Tables/cards wrap or stack without horizontal overlap.

## Error Handling

- API failures produce visible inline error states instead of console-only feedback.
- Async actions disable their trigger while pending.
- Empty data and not-found states remain explicit.
- Clipboard failure does not break generated content display.

## Testing

- Add component tests for authenticated shell rendering and absence of the mini-program panel.
- Test role switching and role-aware navigation.
- Retain the AI generation response test.
- Add focused tests for loading/error or key route behavior where implementation changes it.
- Run `npm test` and `npm run build`.
- Validate the user's existing local dev server in desktop and mobile viewport sizes.

## Non-Goals

- No backend or API changes.
- No new business modules or placeholder routes.
- No real authentication implementation.
- No generated marketing landing page.
- No additional local preview server.
