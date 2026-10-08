# API Documentation

## Authentication Endpoints

### POST `/auth/register`
Register a new user with email and password.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "securepassword123",
  "full_name": "John Doe",
  "username": "johndoe"
}
```

**Response:**
```json
{
  "id": "user-uuid",
  "email": "user@example.com",
  "username": "johndoe",
  "full_name": "John Doe",
  "is_active": true,
  "is_verified": false,
  "profile_picture": null,
  "created_at": "2024-01-01T00:00:00"
}
```

### POST `/auth/login`
Login with email and password.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

**Response:**
```json
{
  "access_token": "jwt-token-string",
  "token_type": "bearer"
}
```

### GET `/auth/me`
Get current user profile (requires authentication).

**Headers:**
```
Authorization: Bearer <jwt-token>
```

**Response:**
```json
{
  "id": "user-uuid",
  "email": "user@example.com",
  "username": "johndoe",
  "full_name": "John Doe",
  "is_active": true,
  "is_verified": false,
  "profile_picture": null,
  "created_at": "2024-01-01T00:00:00"
}
```

## Chat Endpoints

### POST `/chat`
Send a message to the AI tutor (requires authentication).

**Headers:**
```
Authorization: Bearer <jwt-token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "message": "What is the derivative of x^2?",
  "session_id": "optional-existing-session-uuid"
}
```

**Response:**
```json
{
  "response": "The derivative of x² is 2x. Here's the explanation...",
  "session_id": "session-uuid",
  "rag": {
    "route": "rag",
    "source": "knowledge_base",
    "trace_id": "trace-uuid"
  },
  "user": {
    "id": "user-uuid",
    "email": "user@example.com",
    "full_name": "John Doe"
  }
}
```

Requests are limited to 4,000 characters. The endpoint can return `429` for rate or
concurrency limits and `503` when the tutor provider is temporarily unavailable.

## Session Endpoints

All session endpoints require `Authorization: Bearer <jwt-token>` and return `404`
for sessions owned by another user.

- `POST /sessions` creates a session from `{ "title": "Linear algebra" }`.
- `GET /sessions` lists the current user's sessions.
- `GET /sessions/{session_id}` returns the session and up to 100 recent messages.
- `DELETE /sessions/{session_id}` deletes the session and its messages.

## Static Endpoints

### GET `/`
Serve the main chat interface.

### GET `/login`
Serve the login page.

### GET `/health`
Health check endpoint.

**Response:**
```json
{
  "status": "ok"
}
```
