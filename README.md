# 🧙‍♂️ Database Guru

Your AI-powered database expert!

## Quick Start

```bash
./start.sh
```

Then visit: http://localhost:8000

## Manual Start

```bash
source venv/bin/activate
pip install -r requirements.txt
python src/main.py
```
# 🧙‍♂️ Database Guru

> *Your AI-powered database expert that speaks your language*

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104-green.svg)](https://fastapi.tiangolo.com/)

## 🌟 What is Database Guru?

Database Guru transforms natural language questions into SQL queries, making database interaction accessible to everyone. No SQL knowledge required - just ask your question in plain English!

### ✨ Features

- 🗣️ **Natural Language Queries** - Ask questions in plain English
- 🔒 **Enterprise Security** - SQL injection prevention, encryption, audit logging
- 🚀 **High Performance** - Multi-layer caching, query optimization
- 🧠 **AI-Powered** - Powered by Ollama and LangChain
- 📊 **Smart Analytics** - Automatic insights and visualizations
- 🔄 **Multi-Database** - Supports PostgreSQL, MySQL, SQLite, MongoDB
- 👥 **Team Ready** - Role-based access control
- 📈 **Production Ready** - Docker, Kubernetes, monitoring included

## 🚀 Quick Start

### Prerequisites
- macOS 10.15+ (Catalina or later)
- Python 3.11+
- Docker Desktop
- 8GB RAM minimum (16GB recommended for LLMs)

### Installation

1. **Clone the repository:**
```bash
git clone https://github.com/yourusername/database-guru.git
cd database-guru
```

2. **Run the setup script:**
```bash
./start_database_guru.sh
```

3. **Access Database Guru:**
- Web UI: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

## 💬 Usage Examples

### Ask Database Guru:
- "How many customers do we have?"
- "Show me the top 10 products by revenue last month"
- "What's the average order value by region?"
- "Find all users who signed up this week"
- "Which products are running low on inventory?"

### API Example:
```python
import requests

response = requests.post(
    "http://localhost:8000/api/query",
    json={"question": "How many active users this month?"},
    headers={"Authorization": "Bearer YOUR_TOKEN"}
)

print(response.json())
# {
#   "answer": "You have 1,247 active users this month",
#   "sql_query": "SELECT COUNT(DISTINCT user_id) FROM ...",
#   "data": [...],
#   "insights": ["23% increase from last month"]
# }
```

## 🏗️ Architecture

```
┌─────────────────────────────────┐
│     Natural Language Input      │
└────────────┬────────────────────┘
             │
┌────────────▼────────────────────┐
│       Database Guru API         │
│   (FastAPI + Authentication)    │
└────────────┬────────────────────┘
             │
      ┌──────┴──────┐
      │             │
┌─────▼─────┐ ┌────▼─────┐
│   Ollama  │ │  Cache   │
│   (LLM)   │ │  (Redis) │
└─────┬─────┘ └──────────┘
      │
┌─────▼─────────────────┐
│   SQL Generation &    │
│   Validation Engine   │
└─────┬─────────────────┘
      │
┌─────▼─────────────────┐
│   Your Database(s)    │
│  (PostgreSQL, MySQL,  │
│   SQLite, MongoDB)    │
└───────────────────────┘
```

## 🔧 Configuration

Create a `.env` file:
```env
# Database Guru Configuration
DATABASE_URL=postgresql://user:pass@localhost:5432/your_db
OLLAMA_MODEL=llama3
CACHE_TTL=3600
RATE_LIMIT=100
```

## 🧪 Testing

```bash
# Run all tests
make test

# Run specific test suite
pytest tests/unit/ -v

# Check code coverage
pytest --cov=src --cov-report=html
```

## 📊 Monitoring

Database Guru includes built-in monitoring:
- Prometheus metrics at `/metrics`
- Grafana dashboards for visualization
- Query performance tracking
- Error rate monitoring
- Usage analytics

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## 📝 License

MIT License - see [LICENSE](LICENSE) for details.

## 🙏 Acknowledgments

- Powered by [Ollama](https://ollama.ai)
- Built with [FastAPI](https://fastapi.tiangolo.com)
- LLM orchestration by [LangChain](https://langchain.com)

## 📞 Support

- Documentation: [docs.databaseguru.ai](https://docs.databaseguru.ai)
- Issues: [GitHub Issues](https://github.com/yourusername/database-guru/issues)
- Discord: [Join our community](https://discord.gg/databaseguru)

---

**Database Guru** - *Making databases speak your language* 🧙‍♂️

EOF

# Create main application file with Database Guru branding
echo "🧙‍♂️ Creating Database Guru application..."