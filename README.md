# Antigravity Proxy

**Antigravity Proxy** is a unified API gateway that allows you to use Google's Gemini models through OpenAI, Claude, or native Gemini API protocols. It manages multiple Google accounts and automatically rotates between them based on quota availability.

## ✨ Features

- 🔄 **Multi-Protocol Support** - Compatible with OpenAI, Anthropic Claude, and native Gemini APIs
- 👥 **Multi-Account Management** - Add multiple Google accounts and auto-rotate based on quota
- 🖼️ **Image Generation** - Imagen 3 support via OpenAI-compatible endpoint
- 📊 **Statistics Dashboard** - Monitor usage, quotas, and request metrics
- 🔐 **User Authentication** - Secure login with API key management
- 🗺️ **Model Routing** - Map model names to different backends

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Antigravity Proxy                    │
├─────────────────────────────────────────────────────────┤
│  Frontend (React + TypeScript + Vite)                   │
│    - Dashboard, Account Management, API Testing         │
├─────────────────────────────────────────────────────────┤
│  Backend (FastAPI + Python)                             │
│    - OpenAI/Claude/Gemini Protocol Handlers             │
│    - Token Management & Quota Tracking                  │
│    - SQLite Database                                    │
└─────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- [uv](https://github.com/astral-sh/uv) (Python package manager)

### Local Development

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/Antigravity-Proxy.git
cd Antigravity-Proxy

# Backend
cd backend
uv sync
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000

# Frontend (in another terminal)
cd frontend
npm install
npm run dev
```

Visit `http://localhost:5173` to access the web interface.

## 👤 Adding Google Accounts

### Method 1: Direct OAuth (Local Development)

When running locally on `localhost:8000`:

1. Go to **Accounts** page
2. Click **"Login with Google"**
3. Complete Google authorization
4. Account is automatically added

### Method 2: OAuth Relay (Production/Remote Server)

When your server is deployed remotely (e.g., `https://your-server.com`), the OAuth callback needs special handling since Google's redirect URI is configured for `localhost`.

**Step 1: Run the relay tool on your local machine**

```bash
python tools/oauth_relay.py --target https://your-server.com
```

**Step 2: Add account from production UI**

1. Go to your production server's **Accounts** page
2. Click the green **"Relay Login"** button
3. Complete Google authorization in the browser
4. The relay forwards the callback to your production server

### Method 3: Manual Token Import

If you have a refresh token:

1. Go to **Accounts** page
2. Click **"Add Token"**
3. Enter email and refresh token
4. Click **Add**

## 🔌 API Usage

Please log in to the web interface to view API documentation and usage examples.

## 📁 Project Structure

```
Antigravity-Proxy/
├── backend/           # FastAPI backend
│   ├── app/
│   │   ├── api/       # API routes
│   │   ├── core/      # Core logic (OAuth, proxy, token management)
│   │   └── models/    # Database models
│   └── pyproject.toml
├── frontend/          # React frontend
│   ├── src/
│   │   ├── pages/     # Page components
│   │   ├── stores/    # Zustand stores
│   │   └── services/  # API client
│   └── package.json
├── deploy/            # Deployment configs
│   ├── antigravity.service
│   └── antigravity.caddy
└── tools/             # Utility scripts
    └── oauth_relay.py # OAuth relay for remote deployment
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `AG_DB_PATH` | SQLite database path | `./antigravity.db` |
| `AG_FRONTEND_DIST` | Frontend build directory | `None` (API only) |

### First Run

On first run, a default admin user is created:

- **Username**: `admin`
- **Password**: `admin`

Please change the password immediately after logging in.

## 📜 License

MIT License
