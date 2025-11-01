# Gateway API Reference

The Flowork Gateway API is the central hub for user authentication, engine management, and proxied communication. All API routes are prefixed with `/api/v1`.

## Authentication

The Gateway API uses two primary methods of authentication:

1.  **Cryptographic Auth (Crypto Auth):** Used for all user-facing routes. The GUI client must sign a message using the user's Private Key and send the following headers:
    * `X-User-Address`: The user's public `0x...` address.
    * `X-Signature`: The resulting signature.
    * `X-Signed-Message`: The unique message that was signed.

2.  **Internal Token Auth:** Used for service-to-service communication (e.g., Core Engine to Gateway, Momod to Gateway).
    * `X-API-Key`: Uses the shared `GATEWAY_SECRET_TOKEN`.
    * `X-Engine-Token`: Uses the unique `FLOWORK_ENGINE_TOKEN` for engine-specific calls.

---

## Auth Routes

Endpoints for handling user identity verification.

### `GET /auth/profile`
**Auth:** `Crypto Auth`

This is the primary "login" endpoint. By sending a valid signed request, the client proves its identity. The Gateway responds with the user's profile data (username, email, tier, permissions) if the signature is valid. If the `X-User-Address` is not recognized, the Gateway will auto-register a new user.

### `POST /auth/logout`
**Auth:** `Crypto Auth`

Acknowledges a user's logout request. In a stateless crypto system, this has minimal server-side effect but confirms the client's intent.

### `POST /auth/register`
**Status: Stubbed**

Not used. Identity creation (registration) is handled client-side by generating a new Private Key / Mnemonic phrase.

### `POST /auth/login`
**Status: Stubbed**

Not used. Authentication is handled by `GET /auth/profile` using a cryptographic signature.

---

## User & Engine Routes

Endpoints for managing a user's account and their registered engines.

### `GET /user/engines`
**Auth:** `Crypto Auth`

Fetches a list of all engines **owned** by the authenticated user.

### `POST /user/engines`
**Auth:** `Crypto Auth`

Registers a new engine for the authenticated user.
* **Body:** `{ "name": "My New Engine Name" }`
* **Response:** `{ "id": "...", "name": "...", "raw_token": "dev_engine_..." }`

### `DELETE /user/engines/<engine_id>`
**Auth:** `Crypto Auth`

Deletes an engine owned by the user.

### `POST /user/engines/<engine_id>/reset-token`
**Auth:** `Crypto Auth`

Generates a new `raw_token` for an existing engine and updates its hash in the database.
* **Response:** `{ "token": "dev_engine_...", "engine_id": "..." }`

### `PUT /user/engines/<engine_id>/update-name`
**Auth:** `Crypto Auth`

Updates the friendly name of an owned engine.
* **Body:** `{ "name": "New Engine Name" }`

### `GET /user/shared-engines`
**Auth:** `Crypto Auth`

Fetches a list of all engines **shared with** the authenticated user (i.e., engines they do not own but can access).

---

## Engine Sharing Routes

Endpoints for managing engine access permissions.

### `GET /engines/<engine_id>/shares`
**Auth:** `Crypto Auth`

For an engine you **own**, get a list of all users you have shared it with.

### `POST /engines/<engine_id>/shares`
**Auth:** `Crypto Auth`

Share an engine you **own** with another user.
* **Body:** `{ "share_with_identifier": "username_or_public_address" }`

### `DELETE /engines/<engine_id>/shares/<shared_user_id>`
**Auth:** `Crypto Auth`

Revoke access for a specific user from an engine you **own**.

---

## Workflow Sharing Routes

Endpoints for creating and managing public share links for workflows.

### `GET /workflows/<preset_name>/shares`
**Auth:** `Crypto Auth`

Gets a list of all share links created for one of your workflows.

### `POST /workflows/<preset_name>/shares`
**Auth:** `Crypto Auth`

Creates a new, unique share link for one of your workflows.
* **Body:** `{ "permission_level": "view-run", "link_name": "My Link" }`
* **Permissions:** `view`, `view-run`, `view-edit-run`

### `PUT /workflow-shares/<share_id>`
**Auth:** `Crypto Auth`

Updates the permission level of an existing share link you own.
* **Body:** `{ "permission_level": "view" }`

### `DELETE /workflow-shares/<share_id>`
**Auth:** `Crypto Auth`

Deletes a share link you own, revoking access.

### `GET /workflow-shares/resolve/<share_token>`
**Auth:** `Public`

A public endpoint to resolve a share token. It returns the workflow's name, owner, and permission level.

---

## User State Routes

Endpoints for storing persistent, user-specific key-value data (like GUI preferences).

### `GET /user/state/favorite_presets`
**Auth:** `Crypto Auth`

Retrieves the user's saved list of favorite preset IDs (an array of strings).

### `PUT /user/state/favorite_presets`
**Auth:** `Crypto Auth`

Overwrites the user's saved list of favorite preset IDs.
* **Body:** `[ "preset-id-1", "preset-id-2" ]`

---

## Internal & System Routes

Endpoints used for service-to-service communication.

### `GET /system/health`
**Auth:** `Public`

A simple health check endpoint for the Gateway service, used by Docker.

### `GET /engine/get-engine-auth-info`
**Auth:** `Internal Auth (X-Engine-Token)`

Called by a Core Engine on startup. The engine sends its unique token, and the Gateway responds with the list of user public addresses authorized to access that engine (the owner + all shared users).

### `GET /engine/claim-token`
**Auth:** `Internal Auth (X-API-Key)`

Called by the Core Engine's local dashboard. This is the final step in the dashboard-to-web authorization flow, allowing the engine to claim a newly generated token.

### `GET /system/disabled-components`
**Auth:** `Internal Auth (X-API-Key)`

Called by the Core Engine to fetch the global "kill-switch" list of component IDs that should be disabled for security or maintenance reasons.

---

## Proxied Routes

The Gateway acts as a reverse proxy for several routes, forwarding them to the user's **active Core Engine**.

### Public Proxies
These routes are proxied from the Core Engine and are publicly accessible (no auth needed).

* `GET /localization/<lang_code>`: Fetches language dictionary files.
* `GET /news`: Fetches the news feed.
* `GET /components/<type>/<id>/icon`: Fetches the icon for a specific component.

### Authenticated Proxies
All other requests to `/api/v1/...` that are not listed above (e.g., `/presets`, `/variables`, `/dashboard/summary`) are treated as authenticated proxy requests. The Gateway forwards them to the user's active Core Engine after verifying their **Crypto Auth** headers.