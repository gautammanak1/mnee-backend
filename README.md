# Sociantra - AI-Powered LinkedIn Content Automation

**🏆 Built for MNEE Hackathon: Programmable Money for Agents, Commerce, and Automated Finance**  
**Track:** AI & Agent Payments and Commerce | **Contract:** `0x8ccedbAe4916b79da7F3F612EfB2EB93A2bFD6cF` | **Deadline:** January 13, 2026

## 📦 Repositories

- **Backend:** [https://github.com/gautammanak1/mnee-backend](https://github.com/gautammanak1/mnee-backend)
- **Frontend:** [https://github.com/gautammanak1/mnee-frontend](https://github.com/gautammanak1/mnee-frontend)

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

## ☁️ Azure Deployment

This guide will help you deploy the MNEE Backend to Azure Container Apps using GitHub Actions CI/CD.

### Prerequisites

- Azure account with active subscription
- Azure CLI installed ([Install Guide](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli))
- Docker installed
- GitHub repository with this code

### Option 1: Automated Deployment with GitHub Actions (Recommended)

#### Step 1: Create Azure Resources

1. **Login to Azure**
```bash
az login
```

2. **Set your subscription** (if you have multiple)
```bash
az account set --subscription "Your Subscription Name"
```

3. **Register Required Resource Providers** ⚠️ **IMPORTANT: Run this first!**
```bash
# Register all required providers (this may take 1-2 minutes)
az provider register --namespace Microsoft.ContainerRegistry --wait
az provider register --namespace Microsoft.App --wait
az provider register --namespace Microsoft.OperationalInsights --wait

# Verify registration status
az provider list --query "[?namespace=='Microsoft.ContainerRegistry' || namespace=='Microsoft.App' || namespace=='Microsoft.OperationalInsights'].{Namespace:namespace, State:registrationState}" --output table
```

**Note:** If you see `MissingSubscriptionRegistration` errors, you must register these providers first.

4. **Create Resource Group**
```bash
az group create \
  --name mnee-backend-rg \
  --location eastus
```

5. **Create Azure Container Registry**
```bash
az acr create \
  --resource-group mnee-backend-rg \
  --name mneebackendacr \
  --sku Basic \
  --admin-enabled true
```

6. **Create Container Apps Environment**
```bash
az containerapp env create \
  --name mnee-backend-env \
  --resource-group mnee-backend-rg \
  --location eastus
```

6. **Create Container App** (initial deployment)
```bash
az containerapp create \
  --name mnee-backend-app \
  --resource-group mnee-backend-rg \
  --environment mnee-backend-env \
  --image mcr.microsoft.com/azuredocs/containerapps-helloworld:latest \
  --target-port 8023 \
  --ingress external \
  --min-replicas 1 \
  --max-replicas 3 \
  --cpu 1.0 \
  --memory 2.0Gi
```

#### Step 2: Configure GitHub Secrets

Go to your GitHub repository → Settings → Secrets and variables → Actions → New repository secret

Add the following secrets:

**Azure Credentials:**
```bash
# Get Azure credentials JSON
az ad sp create-for-rbac --name "mnee-backend-github" --role contributor \
  --scopes /subscriptions/{subscription-id}/resourceGroups/mnee-backend-rg \
  --sdk-auth
```

Copy the JSON output and save it as `AZURE_CREDENTIALS` secret.

**Application Secrets:**
- `CONTRACT_ADDRESS` - Your MNEE contract address
- `SUPABASE_URL` - Your Supabase project URL
- `SUPABASE_KEY` - Your Supabase anon key
- `SUPABASE_SERVICE_KEY` - Your Supabase service role key
- `SUPABASE_JWT_SECRET` - Your Supabase JWT secret
- `GEMINI_API_KEY` - Your Google Gemini API key
- `LINKEDIN_CLIENT_ID` - LinkedIn OAuth client ID
- `LINKEDIN_CLIENT_SECRET` - LinkedIn OAuth client secret
- `LINKEDIN_REDIRECT_URI` - LinkedIn redirect URI (use your Azure app URL)
- `LINKEDIN_SCOPE` - LinkedIn OAuth scopes
- `MNEE_API_KEY` - Your MNEE API key
- `MNEE_ENV` - `sandbox` or `production`
- `FRONTEND_URL` - Your frontend URL
- `AGENT_SEED` - 64-character seed for agent

#### Step 3: Update Workflow Variables

Edit `.github/workflows/azure-deploy.yml` and update these variables if needed:

```yaml
env:
  AZURE_WEBAPP_NAME: mnee-backend
  AZURE_RESOURCE_GROUP: mnee-backend-rg
  AZURE_CONTAINER_REGISTRY: mneebackendacr
  AZURE_CONTAINER_APP_NAME: mnee-backend-app
  AZURE_CONTAINER_APP_ENVIRONMENT: mnee-backend-env
```

#### Step 4: Push to Main Branch

```bash
git add .
git commit -m "Add Azure deployment workflow"
git push origin main
```

The GitHub Actions workflow will automatically:
1. Build and test your code
2. Build Docker image
3. Push to Azure Container Registry
4. Deploy to Azure Container Apps

### Option 2: Manual Azure CLI Deployment

1. **Build and push Docker image**
```bash
# Login to ACR
az acr login --name mneebackendacr

# Build image
docker build -t mneebackendacr.azurecr.io/mnee-backend:latest .

# Push image
docker push mneebackendacr.azurecr.io/mnee-backend:latest
```

2. **Update Container App**
```bash
az containerapp update \
  --name mnee-backend-app \
  --resource-group mnee-backend-rg \
  --image mneebackendacr.azurecr.io/mnee-backend:latest \
  --set-env-vars \
    PORT=8023 \
    CONTRACT_ADDRESS="your-contract-address" \
    SUPABASE_URL="your-supabase-url" \
    # ... add all other environment variables
```

### Post-Deployment

1. **Get your app URL**
```bash
az containerapp show \
  --name mnee-backend-app \
  --resource-group mnee-backend-rg \
  --query "properties.configuration.ingress.fqdn" -o tsv
```

**Output:** `https://mnee-backend-app.xyz123.azurecontainerapps.io`

2. **Test deployment**
```bash
curl https://your-app-url.azurecontainerapps.io/api/health
```

3. **View logs**
```bash
az containerapp logs show \
  --name mnee-backend-app \
  --resource-group mnee-backend-rg \
  --follow
```

### 🔗 Backend URL Setup (Frontend & LinkedIn)

**Important:** Backend URL ko frontend aur LinkedIn mein add karna zaroori hai!

📖 **Complete guide:** See `BACKEND_URL_SETUP.md` for detailed instructions.

**Quick Steps:**
1. **Frontend:** `.env.local` mein `NEXT_PUBLIC_API_BASE=https://your-backend-url.azurecontainerapps.io` add karein
2. **LinkedIn:** Developer Portal mein redirect URI add karein: `https://your-backend-url.azurecontainerapps.io/api/linkedin/callback`
3. **Backend:** Environment variable update: `LINKEDIN_REDIRECT_URI=https://your-backend-url.azurecontainerapps.io/api/linkedin/callback`

### Updating Environment Variables

To update environment variables after deployment:

```bash
az containerapp update \
  --name mnee-backend-app \
  --resource-group mnee-backend-rg \
  --set-env-vars \
    GEMINI_API_KEY="new-key" \
    SUPABASE_URL="new-url"
```

### Scaling

```bash
# Scale to 3 replicas
az containerapp update \
  --name mnee-backend-app \
  --resource-group mnee-backend-rg \
  --min-replicas 1 \
  --max-replicas 3
```

### Monitoring

- **Azure Portal**: Navigate to your Container App → Monitoring
- **Application Insights**: Enable for detailed telemetry
- **Logs**: Use `az containerapp logs show` command

### Troubleshooting

**Issue: MissingSubscriptionRegistration Error**
If you see errors like:
- `The subscription is not registered to use namespace 'Microsoft.ContainerRegistry'`
- `Subscription is not registered for the Microsoft.OperationalInsights resource provider`

**Solution:**
```bash
# Register all required providers (run this first!)
az provider register --namespace Microsoft.ContainerRegistry --wait
az provider register --namespace Microsoft.App --wait
az provider register --namespace Microsoft.OperationalInsights --wait

# Verify registration
az provider list --query "[?namespace=='Microsoft.ContainerRegistry' || namespace=='Microsoft.App' || namespace=='Microsoft.OperationalInsights'].{Namespace:namespace, State:registrationState}" --output table
```

**Note:** Registration can take 1-2 minutes. The `--wait` flag waits until completion.

**Issue: Deployment fails**
- Check GitHub Actions logs
- Verify all secrets are set correctly
- Ensure Azure resources exist
- Make sure resource providers are registered (see above)

**Issue: App not responding**
- Check container logs: `az containerapp logs show`
- Verify environment variables are set
- Check ingress configuration

**Issue: Image pull fails**
- Verify ACR credentials
- Check image exists: `az acr repository list --name mneebackendacr`
- Ensure Container App has access to ACR

### Cost Optimization

- Use **Consumption Plan** for pay-as-you-go pricing
- Set appropriate min/max replicas based on traffic
- Use Basic tier ACR for development
- Enable auto-scaling based on CPU/memory

### Security Best Practices

1. **Use Managed Identity** for ACR access (already configured in workflow)
2. **Store secrets in Azure Key Vault** (optional)
3. **Enable HTTPS only** (default in Container Apps)
4. **Regularly update base images** in Dockerfile
5. **Use private endpoints** for production

### Additional Resources

- [Azure Container Apps Documentation](https://docs.microsoft.com/azure/container-apps/)
- [GitHub Actions for Azure](https://github.com/marketplace?type=actions&query=azure)
- [Azure CLI Reference](https://docs.microsoft.com/cli/azure/)

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
