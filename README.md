# Rate Limiter

## Overview
A simple yet production-ready Rate Limiter built with FastAPI, Redis, and Lua scripting.
It acts as a reverse proxy and protects backend services from being overwhelmed by excessive traffic.

## ✨ Features
- ⚡ High-performance rate limiting using Redis
- 🔒 Atomic operations with Redis Lua scripts
- 🔁 Reverse proxy to forward requests to backend services
- 🧠 IP + route based limiting
- ⏱️ TTL-based windowing
- 📊 Rate limit headers for observability
- 🚀 Fully async (FastAPI + httpx + redis-async)

## 🧩 How it works 
1. Incoming request hits the Rate Limiter Proxy
2. Middleware:
    - Identifies client (IP + route)
    - Executes Redis Lua script atomically
3. If limit exceeded:
    - Responds with 429 Too Many Requests
4. If allowed:
    - Request is forwarded to the backend service
5. Response is returned with rate-limit headers

## 🏗️ Architecture

``` Client
  │
  ▼
Rate Limiter (FastAPI)
  │
  ├── Redis (Lua Script)
  │
  └── Backend Service
```

## 🚀 Getting Started

### 1️⃣ Install dependencies
```bash
pip install -r requirements.txt
```

### 2️⃣ Start Redis
```bash
docker run --name my-redis -p 6379:6379 -d redis
```

### 3️⃣ Start Rate Limiter Proxy
```bash
uvicorn app:app --port=8000 --reload
```

## 🔐 Redis Key Strategy
```
rate_limit:{path}:{hostname}
```

## 🧠 Why Redis + Lua?
- Guarantees atomicity
- Eliminates race conditions
- Extremely fast
- Production-proven approach

## Developer Contact
```
Saurav Muke : saurav54muke@gmail.com
```

