# Phase 23: Data Flow (Deployment)

## Deployment Data Flow

No code changes. This is a visual representation of the flow introduced by the current docker-containerization branch:
```mermaid
graph TD
    User[User Browser]
    subgraph Docker Host
        Nginx[Nginx Container (Port 3000)]
        Backend[Backend Container (Port 8000)]
        Ollama[Ollama Container (Port 11434)]
        Postgres[Postgres Container (Port 5432)]
        Redis[Redis Container (Port 6379)]
        
        Volume_Data[Docker Volume: dbguru-data]
        Volume_Models[Docker Volume: ollama-models]
    end

    User -->|HTTP/HTTPS| Nginx
    Nginx -->|Reverse Proxy /api| Backend
    Nginx -->|Static Files| User
    
    Backend -->|SQL| Postgres
    Backend -->|Cache| Redis
    Backend -->|Generate/Embed| Ollama
    
    Backend -->|Read/Write| Volume_Data
    Ollama -->|Load Models| Volume_Models
```
