# Joyce Messaging API

External applications can submit SMS through Joyce. Joyce talks to Jasmin
(HTTP `/send` or REST `/secure/sendbatch`) and always receives DLRs on its own
`/dlr` endpoint. Optionally, Joyce forwards DLRs to your **external channel** URL.

## Enable the API

1. Open **Workspace settings**.
2. Under **External channel**:
   - Enable **Joyce messaging API** and save — a token is generated automatically (existing tokens are kept)
   - Use the refresh icon beside the token to rotate it
   - Copy the bearer token for `POST /api/v1/messaging/send/` only
   - Download the **API documentation (PDF)** for integrators (same content as this guide)
3. For **My own Jasmin**, set **REST API base URL** (port 8080) if you want bulk via `sendbatch`.
4. Optionally set **External DLR URL** (+ method, retry delay, max retries).

Demo workspaces use `JASMIN_REST_API_URL` from the Joyce server environment when set
(Docker Compose defaults to `http://jasmin_rest:8080`).

## Authentication

All send requests require a bearer token:

```http
Authorization: Bearer <messaging_api_token>
```

Alternatively:

```http
X-Joyce-Token: <messaging_api_token>
```

## Send SMS

```http
POST /api/v1/messaging/send/
Content-Type: application/json
Authorization: Bearer <token>
```

Joyce inspects the payload and chooses single vs bulk automatically.

### Single destination

```json
{
  "username": "u1_myuser",
  "to": "256700000001",
  "content": "Hello",
  "from": "JOYCE",
  "client_message_id": "ord-100-sms-1",
  "client_batch_id": "campaign-42",
  "dlr_level": 3,
  "priority": 0
}
```

### Same content, many destinations

```json
{
  "username": "u1_myuser",
  "to": ["256700000001", "256700000002"],
  "content": "Promo text",
  "client_batch_id": "broadcast-99",
  "client_message_ids": ["msg-a", "msg-b"]
}
```

### Personalized messages

```json
{
  "username": "u1_myuser",
  "client_batch_id": "orders-2026-07-13",
  "messages": [
    {"to": "256700000001", "content": "Order #100 is ready", "client_message_id": "ord-100"},
    {"to": "256700000002", "content": "Order #101 is ready", "client_message_id": "ord-101"}
  ],
  "from": "JOYCE",
  "dlr_level": 3
}
```

`username` must be an **enabled** Jasmin user in that workspace.

Optional correlation ids (max 128 chars):

| Field | Scope |
|-------|--------|
| `client_message_id` | One destination (top-level or per `messages[]` entry). Alias: `message_id`. |
| `client_message_ids` | Parallel list matching a multi-value `to`. |
| `client_batch_id` | Whole submit / broadcast. Alias: `broadcast_id`. |

Jasmin still generates its own message UUID and REST `batchId`. Your ids are stored by Joyce and echoed on DLR forwards.

### Routing behaviour

| Destinations | REST API URL configured? | Behaviour |
|--------------|--------------------------|-----------|
| 1 | n/a | Sync classic HTTP `/send` |
| 2+ | Yes | Chunked Jasmin REST `sendbatch` |
| 2+ | No | Async Celery: classic `/send` one-by-one |

Joyce always owns a `batch_id` for the whole submit. Each REST chunk gets its own
Jasmin `batchId` (listed in `jasmin_batch_ids`).

### Response

**200** (single or REST bulk):

```json
{
  "batch_id": "a1b2c3d4e5f6g7h8",
  "client_batch_id": "campaign-42",
  "mode": "single",
  "message_count": 1,
  "jasmin_batch_ids": [],
  "messages": [
    {
      "id": 42,
      "to": "256700000001",
      "status": "submitted",
      "client_message_id": "ord-100-sms-1",
      "client_batch_id": "campaign-42",
      "jasmin_msg_id": "…",
      "error": null
    }
  ],
  "messages_truncated": false
}
```

`mode` is one of `single`, `bulk_rest`, `bulk_async`.

**202** when `mode` is `bulk_async` (accepted; workers submit in the background).

The `messages` array is capped at 100 rows; use `batch_id` in the Operate UI to find the rest.

## Delivery reports

1. Jasmin always calls Joyce: `GET|POST {JOYCE_PUBLIC_BASE_URL}/dlr` (or `JOYCE_DLR_CALLBACK_URL`).
2. Joyce updates the outbound message.
3. If **External DLR URL** is set, Joyce queues an async forward (GET or POST as configured).
4. Forward failures are retried up to **max retries** (default 5), waiting **retry delay** seconds (default 60). Internal DLR handling is never blocked by the external channel.

### External DLR payload

Joyce forwards an **enriched** JSON body (POST) or query params (GET), including Jasmin’s original DLR fields plus:

| Field | Meaning |
|-------|---------|
| `client_message_id` | Your optional message id from send |
| `client_batch_id` | Your optional broadcast/batch id from send |
| `joyce_message_id` | Joyce `OutboundMessage` primary key |
| `joyce_batch_id` | Joyce batch id for the submit |
| `jasmin_msg_id` | Jasmin gateway UUID (`id` on the raw DLR) |
| `jasmin_batch_id` | Jasmin REST chunk batch id (when used) |
| `to` / `from` | Addresses |
| `status` / `dlr_status` | Joyce status + raw DLR status |

Match on `client_message_id` (or `client_batch_id` + `to`) in your app. You do not need Jasmin to accept your ids.

## Batch progress callbacks (REST bulk)

When using `sendbatch`, Joyce registers:

`{JOYCE_PUBLIC_BASE_URL}/batch-callback`

Jasmin calls this per successful/failed item so Joyce can store `jasmin_msg_id` for later DLR matching.