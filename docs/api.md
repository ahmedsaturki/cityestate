# CityEstate API Documentation

## Base URL

```
http://localhost:8000/api/v1
```

## Authentication

All endpoints (except `/api/v1/auth/login` and `/api/v1/auth/register`) require a JWT token in the `Authorization` header:

```
Authorization: Bearer <jwt_token>
```

### Login

```
POST /api/v1/auth/login
Content-Type: application/json

{
  "username": "admin",
  "password": "password"
}

Response:
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "username": "admin",
    "full_name": "Admin User",
    "role": "admin"
  }
}
```

### Register

```
POST /api/v1/auth/register
Content-Type: application/json

{
  "username": "user1",
  "password": "password123",
  "full_name": "User One"
}
```

## Routes

### Auth (`/api/v1/auth/`)

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/login` | Login with username/password | No |
| POST | `/register` | Register new user | No |
| GET | `/me` | Get current user profile | Yes |
| PUT | `/me` | Update current user profile | Yes |

### Automation (`/api/v1/automation/`)

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/status` | Get automation status | Yes |
| POST | `/whatsapp/send` | Send WhatsApp message | Yes |
| POST | `/whatsapp/connect` | Connect WhatsApp session | Yes |
| POST | `/whatsapp/disconnect` | Disconnect WhatsApp session | Yes |
| GET | `/whatsapp/sessions` | List active WhatsApp sessions | Yes |
| POST | `/facebook/scrape` | Scrape Facebook posts | Yes |
| GET | `/facebook/leads` | Get Facebook leads | Yes |

### Content (`/api/v1/content/`)

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/templates` | List content templates | Yes |
| POST | `/templates` | Create new template | Yes |
| PUT | `/templates/{id}` | Update template | Yes |
| DELETE | `/templates/{id}` | Delete template | Yes |
| POST | `/generate` | Generate content using AI | Yes |

### Dashboard (`/api/v1/dashboard/`)

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/stats` | Dashboard statistics | Yes |
| GET | `/leads/recent` | Recent leads | Yes |
| GET | `/properties/recent` | Recent properties | Yes |
| GET | `/campaigns/active` | Active campaigns | Yes |

### Data (`/api/v1/data/`)

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/import/csv` | Import leads from CSV | Yes |
| GET | `/leads` | List all leads | Yes |
| GET | `/leads/{id}` | Get lead details | Yes |
| PUT | `/leads/{id}` | Update lead | Yes |
| DELETE | `/leads/{id}` | Delete lead | Yes |
| GET | `/export/csv` | Export leads as CSV | Yes |

### Leads (`/api/v1/leads/`)

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/` | List all leads | Yes |
| POST | `/` | Create new lead | Yes |
| GET | `/{id}` | Get lead by ID | Yes |
| PUT | `/{id}` | Update lead | Yes |
| DELETE | `/{id}` | Delete lead | Yes |
| GET | `/{id}/matches` | Get matched properties | Yes |

### Properties (`/api/v1/properties/`)

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/` | List all properties | Yes |
| POST | `/` | Create new property | Yes |
| GET | `/{id}` | Get property by ID | Yes |
| PUT | `/{id}` | Update property | Yes |
| DELETE | `/{id}` | Delete property | Yes |
| GET | `/{id}/matches` | Get matched requests | Yes |

### Requests (`/api/v1/requests/`)

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/` | List all client requests | Yes |
| POST | `/` | Create new client request | Yes |
| GET | `/{id}` | Get request by ID | Yes |
| PUT | `/{id}` | Update request | Yes |
| DELETE | `/{id}` | Delete request | Yes |
| POST | `/{id}/match` | Trigger matching for request | Yes |
| GET | `/{id}/notifications` | Get notification history | Yes |

### Scheduler (`/api/v1/scheduler/`)

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/jobs` | List all scheduled jobs | Yes |
| POST | `/jobs/{name}/run` | Run job immediately | Yes |
| GET | `/jobs/{name}/status` | Get job status | Yes |
| PUT | `/jobs/{name}/config` | Update job configuration | Yes |

### Skills (`/api/v1/skills/`)

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/tasks` | List all tasks | Yes |
| POST | `/tasks` | Create new task | Yes |
| PUT | `/tasks/{id}` | Update task | Yes |
| DELETE | `/tasks/{id}` | Delete task | Yes |
| GET | `/goals` | List all goals | Yes |
| POST | `/goals` | Create new goal | Yes |
| PUT | `/goals/{id}` | Update goal | Yes |
| GET | `/kanban` | Get kanban board | Yes |
| POST | `/kanban` | Create kanban board | Yes |
| GET | `/notes` | List all notes | Yes |
| POST | `/notes` | Create new note | Yes |
| POST | `/notes/brainstorm` | Brainstorm ideas | Yes |
| GET | `/time-tracking` | Get time tracking data | Yes |
| POST | `/time-tracking` | Start/stop time tracking | Yes |

### Webhooks (`/api/v1/webhooks/`)

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/form` | Receive form webhook | No (HMAC) |
| POST | `/whatsapp` | Receive WhatsApp webhook | No (HMAC) |
| POST | `/facebook` | Receive Facebook webhook | No (HMAC) |

### WebSocket (`/ws`)

WebSocket endpoint for real-time updates. Connect at:

```
ws://localhost:8000/ws
```

## Error Responses

All error responses follow this format:

```json
{
  "detail": "Error message",
  "error_code": "ERROR_CODE",
  "status_code": 400
}
```

### Common Error Codes

| Code | Meaning |
|------|---------|
| `AUTH_INVALID_TOKEN` | JWT token is invalid or expired |
| `AUTH_MISSING_TOKEN` | No JWT token provided |
| `AUTH_INSUFFICIENT_PERMISSIONS` | User lacks required role |
| `VALIDATION_ERROR` | Request body validation failed |
| `NOT_FOUND` | Resource not found |
| `RATE_LIMITED` | Too many requests |
| `WEBHOOK_INVALID_SIGNATURE` | HMAC signature verification failed |