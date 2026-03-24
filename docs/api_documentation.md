# Account Risk Early Warning System - API Documentation

## Overview

Base URL: `http://localhost:8000`

All API endpoints (except health check) require JWT authentication.

### Authentication

All protected endpoints require a Bearer token in the Authorization header:

```bash
Authorization: Bearer <access_token>
```

### Content Type

All request/response bodies use JSON format:

```
Content-Type: application/json
```

### Error Responses

All errors follow a standard format:

```json
{
  "detail": "Error message description"
}
```

| Status Code | Description |
|-------------|--------------|
| 400 | Bad Request - Invalid parameters |
| 401 | Unauthorized - Missing or invalid token |
| 403 | Forbidden - Insufficient permissions |
| 404 | Not Found - Resource not found |
| 422 | Validation Error - Request validation failed |
| 500 | Internal Server Error |

---

## Authentication Endpoints

### POST /api/v1/auth/login

User login endpoint. Returns access token and refresh token.

**Request:**

```http
POST /api/v1/auth/login
Content-Type: application/x-www-form-urlencoded

username=testuser&password=testpass
```

**Response (200):**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_in": 86400,
  "token_type": "bearer"
}
```

---

### POST /api/v1/auth/refresh

Refresh access token using refresh token.

**Request:**

```http
POST /api/v1/auth/refresh
Authorization: Bearer <refresh_token>
```

**Response (200):**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_in": 86400,
  "token_type": "bearer"
}
```

---

### POST /api/v1/auth/logout

User logout endpoint.

**Request:**

```http
POST /api/v1/auth/logout
Authorization: Bearer <access_token>
```

**Response (200):**

```json
{
  "message": "Logged out successfully"
}
```

---

### POST /api/v1/auth/register

Register a new user.

**Request:**

```json
{
  "username": "newuser",
  "email": "user@example.com",
  "password": "securepassword123"
}
```

**Response (201):**

```json
{
  "id": 1,
  "username": "newuser",
  "email": "user@example.com",
  "user_level": "normal",
  "status": "active",
  "created_at": "2024-01-15T10:30:00"
}
```

---

## Risk Assessment Endpoints

### POST /api/v1/risk/analyze

Analyze user behavior and calculate risk score in real-time.

**Request:**

```json
{
  "user_id": "user_123",
  "login_time": "2024-01-15T10:30:00",
  "ip_address": "192.168.1.100",
  "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
  "screen_resolution": "1920x1080",
  "timezone": "UTC+8",
  "location": {
    "latitude": 39.9042,
    "longitude": 116.4074
  },
  "event_type": "login"
}
```

**Response (200):**

```json
{
  "user_id": "user_123",
  "risk_score": 45.5,
  "risk_level": "medium",
  "risk_level_display": "中风险",
  "color": "yellow",
  "reasons": [
    "LSTM模型检测到中度异常 (概率: 0.50)"
  ],
  "components": [
    {
      "name": "lstm",
      "score": 30.0,
      "weight": 0.6
    },
    {
      "name": "location",
      "score": 8.0,
      "weight": 0.2
    },
    {
      "name": "device",
      "score": 0.0,
      "weight": 10.0
    },
    {
      "name": "time",
      "score": 0.0,
      "weight": 10.0
    }
  ],
  "alert_triggered": false,
  "alert_id": null,
  "analyzed_at": "2024-01-15T10:30:00"
}
```

**Authentication:** Required (JWT Bearer token)

---

### GET /api/v1/risk/history/{user_id}

Query historical risk records for a user with pagination.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| user_id | path | Yes | User ID |
| start_date | query | No | Start date (ISO format) |
| end_date | query | No | End date (ISO format) |
| page | query | No | Page number (default: 1) |
| page_size | query | No | Items per page (default: 20, max: 100) |

**Request:**

```http
GET /api/v1/risk/history/user_123?page=1&page_size=20
Authorization: Bearer <access_token>
```

**Response (200):**

```json
{
  "user_id": "user_123",
  "total": 50,
  "page": 1,
  "page_size": 20,
  "items": [
    {
      "id": "alert_abc123",
      "user_id": "user_123",
      "risk_score": 85.5,
      "risk_level": "critical",
      "event_type": "login",
      "ip_address": "192.168.1.100",
      "reasons": [
        "LSTM模型检测到高度异常行为 (概率: 0.95)",
        "地理位置异常: 与常用登录地距离过远",
        "检测到新设备登录"
      ],
      "created_at": "2024-01-15T10:30:00"
    }
  ]
}
```

**Authentication:** Required (JWT Bearer token)

---

### POST /api/v1/risk/threshold

Update risk alert threshold configuration.

**Request:**

```json
{
  "config": {
    "low_threshold": 25,
    "medium_threshold": 55,
    "high_threshold": 75,
    "alert_enabled": true,
    "alert_threshold": 55
  }
}
```

**Response (200):**

```json
{
  "success": true,
  "message": "Threshold configuration updated successfully",
  "updated_config": {
    "low_threshold": 25,
    "medium_threshold": 55,
    "high_threshold": 75,
    "alert_enabled": true,
    "alert_threshold": 55
  },
  "updated_at": "2024-01-15T10:30:00"
}
```

**Authentication:** Required (JWT Bearer token)

**Validation:**
- low_threshold < medium_threshold
- medium_threshold < high_threshold

---

### GET /api/v1/risk/trend/{user_id}

Analyze risk score trends over time.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| user_id | path | Yes | User ID |
| days | query | No | Number of days to analyze (default: 30, max: 365) |

**Request:**

```http
GET /api/v1/risk/trend/user_123?days=7
Authorization: Bearer <access_token>
```

**Response (200):**

```json
{
  "user_id": "user_123",
  "days": 7,
  "trend": [
    {
      "date": "2024-01-15",
      "high_risk_count": 2,
      "avg_risk_score": 45.5
    }
  ],
  "peak_times": {
    "09:00": 5,
    "14:00": 3
  }
}
```

**Authentication:** Required (JWT Bearer token)

---

## Alert Endpoints

### GET /api/v1/alerts

Query alerts with filters.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| user_id | query | No | Filter by user ID |
| status | query | No | Filter by status (pending/sent/failed) |
| alert_type | query | No | Filter by alert type |
| start_time | query | No | Start time |
| end_time | query | No | End time |
| page | query | No | Page number (default: 1) |
| page_size | query | No | Items per page (default: 20) |

**Request:**

```http
GET /api/v1/alerts?user_id=user_123&page=1
Authorization: Bearer <access_token>
```

**Response (200):**

```json
{
  "total": 100,
  "page": 1,
  "page_size": 20,
  "items": [
    {
      "id": "alert_abc123",
      "user_id": "user_123",
      "risk_score": 85.5,
      "risk_level": "critical",
      "channels": ["email", "sms"],
      "status": "sent",
      "reasons": [
        "LSTM模型检测到高度异常行为"
      ],
      "created_at": "2024-01-15T10:30:00",
      "sent_at": "2024-01-15T10:30:05"
    }
  ]
}
```

**Authentication:** Required (JWT Bearer token)

---

### GET /api/v1/alerts/{alert_id}

Get alert detail by ID.

**Request:**

```http
GET /api/v1/alerts/alert_abc123
Authorization: Bearer <access_token>
```

**Response (200):**

```json
{
  "id": "alert_abc123",
  "user_id": "user_123",
  "risk_score": 85.5,
  "risk_level": "critical",
  "channels": ["email", "sms"],
  "status": "sent",
  "reasons": [
    "LSTM模型检测到高度异常行为 (概率: 0.95)",
    "地理位置异常: 与常用登录地距离过远",
    "检测到新设备登录",
    "登录时间异常: 非常用时段"
  ],
  "ip_address": "192.168.1.100",
  "created_at": "2024-01-15T10:30:00",
  "sent_at": "2024-01-15T10:30:05"
}
```

**Authentication:** Required (JWT Bearer token)

---

## Admin Endpoints

### GET /api/v1/admin/users

User management endpoint.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| page | query | No | Page number |
| page_size | query | No | Items per page |
| status | query | No | Filter by status |

**Request:**

```http
GET /api/v1/admin/users?page=1
Authorization: Bearer <access_token>
```

**Response (200):**

```json
{
  "total": 1000,
  "page": 1,
  "page_size": 20,
  "items": [
    {
      "id": 1,
      "username": "user1",
      "email": "user1@example.com",
      "user_level": "normal",
      "status": "active",
      "created_at": "2024-01-01T00:00:00"
    }
  ]
}
```

**Authentication:** Required (JWT Bearer token + Admin role)

---

### GET /api/v1/admin/stats

System statistics endpoint.

**Request:**

```http
GET /api/v1/admin/stats
Authorization: Bearer <access_token>
```

**Response (200):**

```json
{
  "total_users": 1000,
  "active_users": 500,
  "total_alerts": 150,
  "critical_alerts": 10,
  "avg_risk_score": 35.5
}
```

**Authentication:** Required (JWT Bearer token + Admin role)

---

## Health Endpoints

### GET /api/v1/health

Health check endpoint. **No authentication required.**

**Request:**

```http
GET /api/v1/health
```

**Response (200):**

```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00"
}
```

---

### GET /api/v1/readiness

Readiness check endpoint. **No authentication required.**

**Request:**

```http
GET /api/v1/readiness
```

**Response (200):**

```json
{
  "status": "ready",
  "database": "connected",
  "redis": "connected",
  "timestamp": "2024-01-15T10:30:00"
}
```

---

## Risk Levels

| Level | Score Range | Color | Description |
|-------|-------------|-------|-------------|
| low | 0-30 | green | Normal behavior |
| medium | 31-60 | yellow | Suspicious behavior |
| high | 61-80 | orange | High risk detected |
| critical | 81-100 | red | Account theft likely |

---

## Risk Score Calculation

The risk score is calculated using:

- **LSTM Model** (60%): Deep learning anomaly detection
- **Location Anomaly** (20%): Distance from historical login locations
- **Device Change** (+10): New device detected
- **Time Anomaly** (+10): Login at unusual hours

Formula: `score = lstm_prob * 60 + location * 20 + device_score + time_score`

---

## Pagination

All list endpoints support pagination with the following parameters:

| Parameter | Default | Max | Description |
|-----------|----------|-----|-------------|
| page | 1 | - | Page number |
| page_size | 20 | 100 | Items per page |

Response includes: `total`, `page`, `page_size`, `items`

---

## cURL Examples

### Login

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=testuser&password=testpass"
```

### Analyze Risk

```bash
curl -X POST http://localhost:8000/api/v1/risk/analyze \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "user_id": "user_123",
    "login_time": "2024-01-15T10:30:00",
    "ip_address": "192.168.1.100",
    "user_agent": "Mozilla/5.0",
    "screen_resolution": "1920x1080",
    "timezone": "UTC+8",
    "event_type": "login"
  }'
```

### Get Risk History

```bash
curl -X GET "http://localhost:8000/api/v1/risk/history/user_123?page=1&page_size=20" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```