# Sociantra - AI-Powered LinkedIn Content Automation

**🏆 Built for MNEE Hackathon: Programmable Money for Agents, Commerce, and Automated Finance**  
**Track:** AI & Agent Payments and Commerce | **Contract:** `0x8ccedbAe4916b79da7F3F612EfB2EB93A2bFD6cF` | **Deadline:** January 13, 2026

## 🚀 Overview

Sociantra is an AI-powered social media automation platform that helps entrepreneurs, agencies, and businesses create and manage LinkedIn content 10x faster. Built with MNEE stablecoin integration for seamless micropayments.

### Key Features

- **🤖 AI Content Generation**: Generate engaging LinkedIn posts using Google Gemini AI with real-time web search
- **📅 Smart Scheduling**: Schedule posts with team approval workflow
- **💰 MNEE Payments**: All services cost 0.01 MNEE per use with instant blockchain verification
- **📊 Analytics Dashboard**: Track spending, engagement, and performance metrics
- **💝 Tip Jar**: Support creators by tipping posts with MNEE
- **🔗 LinkedIn Integration**: Direct posting to LinkedIn with OAuth authentication
- **🌐 Multi-Language**: Support for 7 languages (EN, FR, ES, IT, DE, PT, NL)

## 🏗️ Architecture

Built on **uAgents framework** with modular architecture:

```
mnee-backend/
├── agent.py                 # Main agent entry point
├── chains/                  # LangChain integrations
│   └── ai_chain.py          # AI post generation with web search
├── handlers/                # REST endpoint handlers
│   ├── ai_handlers.py       # AI content generation
│   ├── scheduler_handlers.py # Post scheduling
│   ├── payment_handlers.py  # MNEE payments
│   ├── analytics_handlers.py # Analytics & insights
│   └── tip_handlers.py      # Tip jar functionality
├── services/                # Core services
│   ├── ai/                  # AI services
│   ├── linkedin_service.py  # LinkedIn integration
│   └── scheduler_service.py # Scheduling logic
├── utils/                   # Utilities
│   ├── markdown_converter.py # Markdown to LinkedIn converter
│   └── constants.py          # Constants
└── rest_models.py           # Pydantic models
```

## 📦 Installation

### Prerequisites

- Python 3.10+
- Supabase account
- Google Gemini API key
- LinkedIn OAuth credentials
- MNEE API key

### Quick Start

1. **Clone the repository**
```bash
git clone <repository-url>
cd mnee-backend
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Configure environment**
```bash
cp env.example .env
# Edit .env with your credentials
```

4. **Run with Docker (Recommended)**
```bash
docker-compose up -d
```

5. **Or run directly**
```bash
python agent.py
```

The agent will start on `http://localhost:5000`

## 🐳 Docker Setup

### Using Docker Compose

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Manual Docker Build

```bash
docker build -t sociantra-backend .
docker run -p 5000:5000 --env-file .env sociantra-backend
```

## ⚙️ Environment Variables

See `env.example` for all required variables:

```env
# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-anon-key
SUPABASE_SERVICE_KEY=your-supabase-service-role-key
SUPABASE_JWT_SECRET=your-jwt-secret

# AI
GEMINI_API_KEY=your-gemini-api-key

# LinkedIn OAuth
LINKEDIN_CLIENT_ID=your-client-id
LINKEDIN_CLIENT_SECRET=your-client-secret
LINKEDIN_REDIRECT_URI=http://localhost:5500/api/linkedin/callback

# MNEE Stablecoin
MNEE_API_KEY=your-mnee-api-key
MNEE_ENV=sandbox

# Application
PORT=5000
FRONTEND_URL=http://localhost:5500
AGENT_SEED=your-64-character-seed
```

## 🔌 API Endpoints

### AI Content Generation
- `POST /ai/generate-post` - Generate LinkedIn post with AI
- `POST /ai/generate-image` - Generate image for post

### Scheduling
- `POST /linkedin/schedule` - Schedule a post (requires payment)
- `GET /linkedin/schedules` - Get all schedules
- `POST /linkedin/schedules/action` - Activate/deactivate schedule

### Payments
- `POST /api/payment/verify` - Verify MNEE payment
- `GET /api/payment/history` - Get payment history
- `GET /api/mnee/balance` - Check wallet balance

### Analytics
- `GET /analytics` - Get analytics dashboard data

### Tips
- `POST /api/posts/tip` - Tip a post creator

## 💳 Payment Flow

1. **User schedules post** → Payment required (0.01 MNEE)
2. **Payment processed** → Frontend uses MNEE SDK
3. **Payment verified** → Backend verifies transaction
4. **Post scheduled** → Status set to `pending`
5. **Team approves** → Post goes live at scheduled time

## 🗄️ Database Schema

### Required Supabase Tables

- `scheduled_posts` - Post scheduling with review workflow
- `user_wallets` - Encrypted wallet storage
- `payments` - Transaction history
- `linkedin_connections` - LinkedIn OAuth tokens
- `generated_posts` - AI-generated content

Run `supabase_migration.sql` to set up the schema.

## 🧪 Testing

```bash
# Health check
curl http://localhost:5000/api/health

# Generate post (requires auth)
curl -X POST http://localhost:5000/ai/generate-post \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"topic": "AI trends 2026", "language": "en"}'
```

## 🏆 MNEE Hackathon Submission

### Track: AI & Agent Payments

**What We Built:**
- Autonomous AI agents that verify payments before generating content
- Agent-to-service payment workflow with MNEE stablecoin
- Complete payment analytics and transaction tracking
- Tip jar system for creator monetization

**Key Differentiators:**
- Real-time web search integration for factual content
- Team approval workflow with automatic payment processing
- Multi-language support (7 languages)
- Complete analytics dashboard

**Contract Address:** `0x8ccedbAe4916b79da7F3F612EfB2EB93A2bFD6cF`

## 📝 License

UNLICENSED

## 🤝 Contributing

This project is built for the MNEE Hackathon. Contributions welcome!

## 📞 Support

For issues or questions, please open an issue on GitHub.
