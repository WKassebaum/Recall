# REST API Documentation

## Overview

This API provides endpoints for managing user accounts, authentication, and data access.

## Authentication

All API requests require authentication using JWT tokens.

### Obtaining a Token

**Endpoint:** `POST /auth/login`

**Request Body:**
```json
{
  "username": "user@example.com",
  "password": "secure_password"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### Using the Token

Include the token in the `Authorization` header:

```
Authorization: Bearer <access_token>
```

## User Management

### Create User

**Endpoint:** `POST /users`

**Headers:**
- `Authorization: Bearer <token>`
- `Content-Type: application/json`

**Request Body:**
```json
{
  "email": "newuser@example.com",
  "password": "secure_password",
  "full_name": "John Doe",
  "role": "user"
}
```

**Response (201 Created):**
```json
{
  "id": "user-123",
  "email": "newuser@example.com",
  "full_name": "John Doe",
  "role": "user",
  "created_at": "2024-01-15T10:30:00Z"
}
```

### Get User

**Endpoint:** `GET /users/{user_id}`

**Headers:**
- `Authorization: Bearer <token>`

**Response (200 OK):**
```json
{
  "id": "user-123",
  "email": "user@example.com",
  "full_name": "John Doe",
  "role": "user",
  "created_at": "2024-01-15T10:30:00Z",
  "last_login": "2024-01-20T14:25:00Z"
}
```

### Update User

**Endpoint:** `PATCH /users/{user_id}`

**Headers:**
- `Authorization: Bearer <token>`
- `Content-Type: application/json`

**Request Body:**
```json
{
  "full_name": "Jane Doe",
  "role": "moderator"
}
```

**Response (200 OK):**
```json
{
  "id": "user-123",
  "email": "user@example.com",
  "full_name": "Jane Doe",
  "role": "moderator",
  "updated_at": "2024-01-21T09:15:00Z"
}
```

### Delete User

**Endpoint:** `DELETE /users/{user_id}`

**Headers:**
- `Authorization: Bearer <token>`

**Response (204 No Content)**

## Data Access

### List Items

**Endpoint:** `GET /items`

**Query Parameters:**
- `page` (int): Page number (default: 1)
- `limit` (int): Items per page (default: 20, max: 100)
- `sort` (string): Sort field (default: created_at)
- `order` (string): Sort order - asc or desc (default: desc)

**Headers:**
- `Authorization: Bearer <token>`

**Response (200 OK):**
```json
{
  "items": [
    {
      "id": "item-456",
      "title": "Sample Item",
      "description": "This is a sample item",
      "created_at": "2024-01-20T10:00:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 100,
    "pages": 5
  }
}
```

## Error Handling

### Error Response Format

All errors follow this format:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {
      "field": "Additional error context"
    }
  }
}
```

### Common Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `INVALID_REQUEST` | 400 | Request validation failed |
| `UNAUTHORIZED` | 401 | Authentication required |
| `FORBIDDEN` | 403 | Insufficient permissions |
| `NOT_FOUND` | 404 | Resource not found |
| `CONFLICT` | 409 | Resource conflict |
| `RATE_LIMITED` | 429 | Too many requests |
| `SERVER_ERROR` | 500 | Internal server error |

## Rate Limiting

API requests are rate-limited to prevent abuse:

- **Authenticated requests:** 1000 requests per hour
- **Unauthenticated requests:** 100 requests per hour

Rate limit information is included in response headers:

```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 995
X-RateLimit-Reset: 1642248600
```

## Pagination

List endpoints support cursor-based pagination:

**Request:**
```
GET /items?cursor=eyJpZCI6MTIzfQ&limit=20
```

**Response:**
```json
{
  "items": [...],
  "pagination": {
    "next_cursor": "eyJpZCI6MTQzfQ",
    "has_more": true
  }
}
```

## Webhooks

Subscribe to events using webhooks.

### Register Webhook

**Endpoint:** `POST /webhooks`

**Request Body:**
```json
{
  "url": "https://example.com/webhook",
  "events": ["user.created", "user.updated"],
  "secret": "webhook_signing_secret"
}
```

### Webhook Payload

```json
{
  "event": "user.created",
  "timestamp": "2024-01-21T10:30:00Z",
  "data": {
    "id": "user-789",
    "email": "webhook@example.com"
  }
}
```

Webhooks include a signature header for verification:
```
X-Webhook-Signature: sha256=<hmac_signature>
```
