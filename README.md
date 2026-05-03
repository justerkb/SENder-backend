# PackageGo 📦

A collaborative package delivery platform connecting travelers with senders for affordable international shipping.

## 👥 Team

| Name | Role | ID | 
|------|------|------|
| Yerkebulan Nurbossyn | Backend Engineer |  230103236
| Arsen Dunesov | UX/UI Designer & Product Manager | 230103038
| Nigmet Nazir | Frontend Engineer | 230103334
| Meirambek Nadir | QA Tester |  230103155


LINK PROD: https://package-go.netlify.app/ 
---

## 📋 Project Overview

PackageGo is a full-stack web application that enables:
- **Senders** to post packages for delivery
- **Travelers** to accept packages and earn rewards
- **Reviews & Ratings** for both parties
- **Real-time Notifications** for package updates
- **Secure Authentication** with JWT tokens

---

## 🛠 Tech Stack

### Backend
- **Framework**: FastAPI (Python)
- **Database**: PostgreSQL 16
- **ORM**: SQLModel
- **Cache**: Redis
- **Search**: Elasticsearch
- **Storage**: MinIO (S3-compatible)
- **Task Queue**: Celery + Celery Beat
- **Email**: Mailpit (dev) / SMTP (prod)
- **Monitoring**: Flower (Celery UI)

### Frontend
- **Framework**: React 18
- **Build Tool**: Vite
- **Routing**: React Router v6
- **HTTP Client**: Axios
- **UI Styling**: CSS/Tailwind CSS (optional)
- **State**: React Context API

### DevOps
- **Containerization**: Docker & Docker Compose
- **Reverse Proxy**: Nginx
- **DNS**: Cloudflare
- **Hosting**: Ubuntu VPS
- **Frontend Hosting**: Netlify

---

## 📁 Project Structure

```
PackageGo/
├── web-back PackageGO/          # Backend application
│   ├── main.py                  # FastAPI entry point
│   ├── models/                  # SQLModel database models
│   │   ├── user.py
│   │   ├── sender.py
│   │   ├── traveler.py
│   │   ├── package.py
│   │   ├── trip.py
│   │   ├── review.py
│   │   └── notification.py
│   ├── routes/                  # API endpoint handlers
│   │   ├── auth.py
│   │   ├── senders.py
│   │   ├── travelers.py
│   │   ├── packages.py
│   │   ├── reviews.py
│   │   └── notifications.py
│   ├── schemas/                 # Pydantic request/response schemas
│   ├── services/                # Business logic
│   ├── database.py              # Database configuration
│   ├── celery_app.py            # Celery configuration
│   ├── tasks.py                 # Background tasks
│   ├── Dockerfile               # Container image
│   ├── docker-compose.yml       # Development environment
│   ├── docker-compose.prod.yml  # Production environment
│   ├── nginx/nginx.conf         # Nginx reverse proxy config
│   ├── .env.docker              # Development environment variables
│   ├── .env.prod                # Production environment variables
│   └── requirements.txt         # Python dependencies
│
├── frontend/                    # Frontend application
│   ├── src/
│   │   ├── main.jsx            # React entry point
│   │   ├── App.jsx             # Main app component
│   │   ├── api/                # API client functions
│   │   │   ├── client.js       # Axios instance
│   │   │   ├── auth.js
│   │   │   ├── senders.js
│   │   │   ├── travelers.js
│   │   │   ├── packages.js
│   │   │   ├── reviews.js
│   │   │   └── notifications.js
│   │   ├── context/            # React Context providers
│   │   │   └── AuthContext.jsx
│   │   ├── pages/              # Page components
│   │   │   ├── auth/
│   │   │   ├── sender/
│   │   │   ├── traveler/
│   │   │   └── shared/
│   │   ├── components/         # Reusable components
│   │   └── App.css
│   ├── index.html
│   ├── vite.config.js
│   ├── package.json
│   ├── .env.development        # Development environment variables
│   ├── .env.production         # Production environment variables
│   ├── netlify.toml            # Netlify deployment config
│   └── README.md
│
└── README.md                   # This file
```

---

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose (for development)
- Node.js 18+ (for frontend local development)
- Python 3.12+ (for backend local development)
- Git

### Development Setup

#### 1. Clone & Install Backend
```bash
cd "web-back PackageGO"
python -m venv venv

# On Windows
venv\Scripts\activate
# On Linux/macOS
source venv/bin/activate

pip install -r requirements.txt
```

#### 2. Clone & Install Frontend
```bash
cd frontend
npm install
```

#### 3. Start Development Stack (Docker)
```bash
cd "web-back PackageGO"
docker compose up -d
```

This starts:
- PostgreSQL (port 5433)
- Redis (port 6379)
- Elasticsearch (port 9200)
- MinIO (ports 9000, 9001)
- Mailpit (ports 1025, 8025)
- FastAPI (port 8080)
- Celery Worker & Beat
- Flower (port 5555)
- Redis Commander (port 8081)

#### 4. Start Frontend Development Server
```bash
cd frontend
npm run dev
```

Frontend runs on `http://localhost:5173`
API runs on `http://localhost:8080`

---

## 📊 Database Schema

### Users
- Stores authentication info, email, profile data
- Roles: `sender`, `traveler`, or both

### Senders
- User profile for sending packages
- Relationship: One User → One Sender Profile

### Travelers
- User profile for accepting packages
- Relationship: One User → One Traveler Profile

### Packages
- Package listings with origin, destination, reward
- Statuses: `pending`, `accepted`, `in_transit`, `delivered`, `cancelled`

### Trips
- Traveler routes (origin → destination with dates)

### Reviews
- Sender reviews Traveler and vice versa
- Ratings: 1-5 stars

### Notifications
- Real-time updates for users
- Types: `info`, `package_accepted`, `package_delivered`, `review`, `system`

---

## 🔐 Authentication

**JWT Token Flow:**
1. User registers/logs in
2. Backend returns `access_token` (30 min) + `refresh_token` (7 days)
3. Frontend stores tokens in localStorage
4. Every API request includes: `Authorization: Bearer {access_token}`
5. When access token expires, use refresh_token to get a new one

**Endpoints:**
- `POST /auth/register` - User registration
- `POST /auth/login` - Login
- `POST /auth/refresh` - Refresh access token
- `PATCH /auth/me` - Update profile
- `POST /auth/me/change-password` - Change password

---

## 📦 API Endpoints Overview

### Authentication
```
POST   /auth/register
POST   /auth/login
POST   /auth/refresh
GET    /auth/me
PATCH  /auth/me
POST   /auth/me/change-password
```

### Senders
```
POST   /senders                    # Create sender profile
GET    /senders/me                 # Get own sender profile
GET    /senders/{sender_id}        # Get sender by ID
PATCH  /senders/{sender_id}        # Update sender profile
POST   /packages                   # Create package
GET    /packages                   # List packages
GET    /packages/{package_id}      # Get package details
PATCH  /packages/{package_id}      # Update package
DELETE /packages/{package_id}      # Cancel package
```

### Travelers
```
POST   /travelers                  # Create traveler profile
GET    /travelers/me               # Get own traveler profile
GET    /travelers/{traveler_id}    # Get traveler by ID
PATCH  /travelers/{traveler_id}    # Update traveler profile
POST   /trips                      # Create trip
GET    /trips                      # List trips
POST   /packages/{package_id}/accept  # Accept package
```

### Reviews
```
POST   /reviews                    # Create review
GET    /reviews/{review_id}        # Get review
PATCH  /reviews/{review_id}        # Update review
DELETE /reviews/{review_id}        # Delete review
```

### Notifications
```
GET    /notifications              # List user notifications
POST   /notifications/{id}/read    # Mark as read
POST   /notifications/mark-all-read # Mark all as read
DELETE /notifications/{id}         # Delete notification
```

---

## 🐳 Docker Compose Commands

### Development
```bash
# Start all services
docker compose up -d

# Start with build (after code changes)
docker compose up -d --build

# View logs
docker compose logs -f app

# Stop services
docker compose down

# Stop and remove volumes (reset database)
docker compose down -v

# View service status
docker compose ps
```

### Production (on VPS)
```bash
# Start production stack
docker compose -f docker-compose.prod.yml up -d --build

# View logs
docker compose -f docker-compose.prod.yml logs -f app

# Stop
docker compose -f docker-compose.prod.yml down
```

---

## 🌍 Production Deployment

### Backend Deployment (VPS)

#### 1. SSH into VPS
```bash
ssh root@89.124.117.208
```

#### 2. Clone Repository
```bash
cd /app
git clone <your-repo-url> packagego
cd packagego/web-back\ PackageGO
```

#### 3. Update Environment Variables
```bash
cp .env.prod.example .env.prod
nano .env.prod

# Set:
# - DATABASE_URL with secure password
# - JWT_SECRET (generated: openssl rand -hex 32)
# - SMTP credentials
# - MinIO credentials
```

#### 4. Start with Docker Compose
```bash
docker compose -f docker-compose.prod.yml up -d --build
```


#### 5. SSL Certificate (via Nginx)
- Nginx config automatically handles SSL with Cloudflare
- Cloudflare provides free SSL/TLS encryption

### Frontend Deployment (Netlify)

#### 1. Connect GitHub Repository
```bash
# In Netlify dashboard:
# New site from Git → Select repo → Authorize
```

#### 2. Build Settings
- Build command: `npm run build`
- Publish directory: `dist`
- Environment variables: `VITE_API_URL=https://api.mukhametzhan-kunashuly.cycnet.kz`

#### 3. Deploy
```bash
# Automatic on every push to main branch
# Manual: npm run build && netlify deploy --prod
```

---

## 🧪 Testing

### Backend Unit Tests
```bash
pytest tests/
pytest tests/ -v  # Verbose
pytest tests/test_auth.py  # Specific file
```

### Frontend Testing
```bash
cd frontend
npm test
npm run test:ui  # Vitest UI
```

### API Testing
```bash
# Using curl
curl -X POST http://localhost:8080/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email":"test@example.com",
    "password":"Password123!",
    "first_name":"John",
    "last_name":"Doe"
  }'

# Using Postman
# Import: web-back PackageGO/postman_collection.json
```

---

## 🔧 Environment Variables

### Backend (.env.prod)
```env
DATABASE_URL=postgresql+asyncpg://packagego:PASSWORD@postgres:5432/packagego
REDIS_URL=redis://redis:6379/0
JWT_SECRET=<generated-secret>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=app-password
ELASTICSEARCH_URL=http://elasticsearch:9200
MINIO_URL=http://minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
```

### Frontend (.env.production)
```env
VITE_API_URL=https://api.mukhametzhan-kunashuly.cycnet.kz
```

---

## 📝 Development Guidelines

### Code Style
- **Backend**: Follow PEP 8, use type hints
- **Frontend**: Use ES6+, JSX best practices

### Git Workflow
```bash
git checkout -b feature/feature-name
git add .
git commit -m "feat: add feature description"
git push origin feature/feature-name
# Create Pull Request
```

### Commits
- `feat:` - New feature
- `fix:` - Bug fix
- `refactor:` - Code refactoring
- `docs:` - Documentation
- `test:` - Test updates
- `chore:` - Maintenance

### Database Migrations
```bash
# After model changes
alembic revision --autogenerate -m "description"
alembic upgrade head
```

---

## 🐛 Troubleshooting

### Backend Issues

**Password Authentication Failed**
```
ERROR: asyncpg.exceptions.InvalidPasswordError: password authentication failed
```
Fix: Ensure DATABASE_URL password matches postgres POSTGRES_PASSWORD in docker-compose.yml
```bash
docker compose down -v
docker compose up -d --build
```

**Celery Module Not Found**
```
ModuleNotFoundError: No module named 'tasks'
```
Fix: Add `PYTHONPATH=/app` to celery service environment in docker-compose.yml

**Database Connection Issues**
```bash
# Check postgres health
docker compose exec postgres pg_isready -U packagego

# View postgres logs
docker compose logs postgres
```

### Frontend Issues

**API Connection Failed**
- Check `VITE_API_URL` in .env files
- Verify backend is running: `docker compose ps`
- Check browser console for CORS errors

**Node Modules Issues**
```bash
rm -rf node_modules package-lock.json
npm install
```

---

## 📚 Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Documentation](https://react.dev/)
- [SQLModel Documentation](https://sqlmodel.tiangolo.com/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Docker Documentation](https://docs.docker.com/)
- [Celery Documentation](https://docs.celeryproject.io/)

---

