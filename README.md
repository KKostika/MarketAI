# 📘 MarketAI — Intelligent Stock Analysis Telegram Bot

MarketAI is a GenAI‑powered financial analysis system built with **FastAPI**, **LLM Agents**, **SQLModel**, **AlphaVantage**, **NewsAPI**, and a fully interactive **Telegram Bot interface**.  
It provides real‑time stock insights, structured analysis, and multilingual output through a clean, modular backend architecture.

---

## 🔍 1. Project Overview

MarketAI combines external financial data with LLM reasoning to deliver:

- Real‑time stock prices  
- Historical price data  
- Earnings reports  
- Latest news  
- Summaries  
- Full structured analysis (sentiment, risks, opportunities, scenarios)

The system is designed for reliability, extensibility, and production‑ready deployment.

---

## ⭐ 2. Key Features

- Real‑time stock price retrieval  
- Historical price data  
- Earnings reports  
- Latest news  
- Full LLM‑powered analysis  
- Inline keyboards  
- Progressive (stream‑like) message delivery  
- Follow‑up context  
- Automatic language detection  
- Strict JSON schema output  

---

## 🧱 3. System Architecture

MarketAI follows a layered architecture:

### **Presentation Layer (Handlers)**
- Telegram message parsing  
- Symbol extraction  
- Intent detection  
- Routing to services  
- Progressive message delivery  

### **Business Logic Layer (Services)**
- Fetches external API data  
- Fetches database data  
- Composes unified `stock_data` objects  
- Invokes the GenAI Agent  
- Returns structured JSON  

### **GenAI Layer (Agent)**
- Receives structured data  
- Performs reasoning  
- Produces strict JSON output  
- Supports multilingual responses  
- Enforces schema validation  

### **Data Layer**
- SQLModel database  
- ORM models  
- Pydantic schemas  
- External API communication (AlphaVantage, NewsAPI)

---

## 🔄 4. Data Flow

```text
User → Telegram Bot → FastAPI Webhook → Handlers → Services
→ External APIs + Database → GenAI Agent → Services → Handlers → User
```

---

## 📁 5. Project Structure

```text
marketai/
│
├── api/              # FastAPI routers
├── agents/           # GenAI agent logic
├── services/         # Business logic
├── models/           # ORM + Pydantic models
├── database/         # DB initialization
├── utils/            # Helper functions
├── main.py           # FastAPI entry point
└── requirements.txt
```

---

## ⚙️ 6. Installation

### **Clone the repository**
```bash
git clone https://github.com/<your-username>/marketai.git
cd marketai
```

### **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate   # Linux/Mac
venv\Scripts\activate      # Windows
```

### **Install dependencies**
```bash
pip install -r requirements.txt
```

### **Create `.env` file**
```bash
TELEGRAM_BOT_TOKEN=xxxx
OPENAI_API_KEY=xxxx
ALPHAVANTAGE_API_KEY=xxxx
NEWSAPI_KEY=xxxx
WEBHOOK_URL=https://your-domain.com/telegram/webhook
```

---

## ▶️ 7. Running the Application

### **Start FastAPI**
```bash
uvicorn main:app --reload
```

### **Set Telegram webhook**
```bash
https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/setWebhook?url=<WEBHOOK_URL>
```

Once the webhook is set, Telegram will forward all bot messages to your FastAPI endpoint.

---

## 💬 8. Developer Usage Examples

```bash
TSLA full analysis
AAPL news
MSFT earnings
bring me the last 3 articles
show me summary
```

---

## 🧠 9. GenAI Agent Details

The Agent performs reasoning on structured data and produces:

- sentiment  
- summary  
- risks  
- opportunities  
- scenarios  

It uses:

- PCTF Prompt Engineering  
- strict JSON schema  
- multilingual output  
- deterministic formatting  

---

## 🔮 10. Future Improvements

- Multi‑agent pipelines  
- Contextual news retrieval (RAG‑style)  
- Dashboard for data visualization  
- Caching layer to reduce API cost & latency  
- Advanced NLP symbol detection  
