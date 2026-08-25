# Travel Assistant

A Flask/Agno demo that shows the difference between **tools** (capabilities) and **skills** (expertise).

## What it does

- Lists a named Outlook folder with lightweight metadata, then selectively reads relevant messages using Microsoft Graph delegated `Mail.Read` access.
- Uses an Outlook e-mail skill to distinguish confirmations from marketing, revisions, and cancellations.
- Builds a chronological itinerary from flights, hotels, transfers, excursions, and other confirmed travel details.
- Uses live Web search plus a visa/entry-requirements skill to research current entry rules for a U.S. citizen.
- Generates an editable Word itinerary modeled after a compact three-column travel document.
- Automatically previews generated Word itineraries in the main pane; click **×** to return to the normal overview.
- Omits pricing information from generated Word documents.

Outlook retrieval uses two small tools: `list_outlook_folder()` returns short local integer IDs plus subjects/senders/dates/attachment flags, and `get_outlook_messages()` retrieves at most 25 selected bodies per call using those short IDs, each capped at 500 words.

## Install

```bash
pip install -r requirements.txt
```

Set your OpenAI API key as usual.

### Outlook / Microsoft Graph setup

Create a Microsoft Entra app registration for delegated access:

1. Register an application in Microsoft Entra ID.
2. Add Microsoft Graph **delegated** permission `Mail.Read`.
3. Enable public-client flows for the app.
4. Set the application (client) ID in `OUTLOOK_CLIENT_ID`.
5. Optionally set `OUTLOOK_TENANT_ID`; if omitted, the app uses `common`.

Windows example:

```cmd
set OPENAI_API_KEY=...
set OUTLOOK_CLIENT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
set OUTLOOK_TENANT_ID=common
flask run --debug
```

On the first call to `list_outlook_folder` or `get_outlook_messages`, the host console prints Microsoft's device-code sign-in instructions. After a successful sign-in, MSAL's serialized token cache is saved to `data/token_cache.json`. On later app runs, the app tries silent authentication first and normally does not prompt again. If the cached credentials can no longer be refreshed (for example, because consent was revoked), it falls back to device-code sign-in.

The cache contains reusable authentication material. Keep it private and do not commit or distribute it. The included `.gitignore` excludes it from source control. Delete `data/token_cache.json` if you want to force a fresh Microsoft sign-in.

The tools access mail only as the user who signs in; they do not use application-level mailbox permissions or a client secret.

## Web search

The visa skill uses Agno's `WebSearchTools`, backed by the `ddgs` package. No separate search API key is required for the default configuration.

The agent is instructed to use Web search for current visa/entry research only when that skill is relevant (or when the user explicitly asks for Web research).

## Demo flow

Try a sequence such as:

1. `Read the e-mails in Travel/Asia 2026 and build my itinerary.`
2. `What visas or entry authorizations do I need for this trip?`
3. `Now turn it into a Word document.`

The last step generates both a `.docx` and an HTML sidecar used only for the in-app preview. The user's download link points to the Word document.

## Project structure

```text
travel-agent/
├── app.py
├── agents.py
├── tools.py
├── requirements.txt
├── templates/
│   └── index.html
├── static/
│   ├── main.css
│   ├── script.js
│   └── itineraries/
└── skills/
    ├── outlook-email-reader/
    ├── itinerary-builder/
    ├── visa-entry-requirements/
    └── itinerary-publisher/
```
