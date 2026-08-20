# Browser acceptance checklist

This checklist is the browser-visible acceptance layer for the generation
workspace. API and SSE behavior are covered by backend tests; run these steps
after a frontend or browser-control session is available.

## Technology-stack confirmation

1. Create an HTML project and submit a one-page profile request: no stack
   confirmation should appear.
2. Create an HTML project and submit a dashboard request with login, routing,
   filtering and pagination: the confirmation dialog should recommend Vue 3.
3. Confirm the switch: the project header and home card should show Vue 3.
4. Repeat, choose “keep HTML”: the header and home card should remain HTML and
   the generated output must not contain Vue/Vite files.

## Generation and modification replay

1. Start a generation or modification, reload the workspace while it runs,
   then confirm the same stage, chat output and SSE progress resume.
2. Add a button through element selection or chat. Confirm the chat retains the
   model summary, the diff card and its accept/undo action after re-entry.
3. Accept and undo a modification in separate runs. Re-enter each project and
   confirm the selected result is not requested again.

## Preview performance

1. Open a large Vue project twice. The second iframe load should reuse hashed
   `dist/assets` files and avoid a full bundle download.
2. Return to the home page. Only cards near the viewport should request a
   thumbnail; off-screen cards must not begin screenshot generation.
