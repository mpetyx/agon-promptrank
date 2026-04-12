# Agon PromptRank 🏆🤖

An open-source, enterprise-grade gamification leaderboard built to track, rank, and aggressively gamify employee interactions with AI tools (like GitHub Copilot, Cursor, ChatGPT, etc.). 

By tapping into cross-platform webhooks, Agon PromptRank creates an engaging competitive environment to encourage AI usage, monitor value generation, and reward engineers with dynamic badges, historical point tracking, and leveled department handicaps.

![Python](https://img.shields.io/badge/Python-3.12%2B-blue?style=for-the-badge)
![Django](https://img.shields.io/badge/Django-4.2%2B-success?style=for-the-badge)
![Coverage](https://img.shields.io/badge/Coverage-82%25-brightgreen?style=for-the-badge)
![Celery](https://img.shields.io/badge/Celery-5.3-lightgrey?style=for-the-badge)

---

## 📖 Table of Contents
- [✨ Features](#-features)
- [🏗 Architecture](#-architecture)
- [🚀 Quickstart (Local Launch)](#-quickstart-local-launch)
- [🔌 Dynamic Admin Connectors](#-dynamic-admin-connectors-no-code)
- [🛡 Anti-Cheat Engine](#-anti-cheat-engine)
- [🤝 Contributing](#-contributing)
- [📄 License](#-license)

---

## ✨ Features
* **Zero-Code Tool Ingestion**: Configure dynamic JSON mappers directly in the Django Admin interface to support *any* third-party AI tool webhook out-of-the-box.
* **Smart Anti-Cheat Engine**: Prevents leaderboard manipulation using asynchronous Celery workers to detect and throttle rapid-fire API script-kiddie spam.
* **Leveled Handicaps**: Levels the playing field internally by dynamically grading point multipliers based on Department structures (e.g., matching Marketing vs. active Software Engineers).
* **Premium Glassmorphic UI**: Highly reactive and aesthetic frontend engineered natively in Python using **HTMX**, **Chart.js**, and **TailwindCSS** (No heavy JavaScript build steps required!).
* **Outbound Milestone Webhooks**: Asynchronously publishes corporate achievements into Slack/Teams channels when users cross predefined trophy thresholds.
* **Enterprise Grade Testing**: Covered by an 80%+ native unit-testing footprint.

---

## 🏗 Architecture
The MVP runs purely Python-native, leveraging Django for ORM/Admin/Routing, DRF for Ingestion API logic, and HTMX for async UI partials.

```text
/config/                  # Django Settings & Routing
/users/                   # Identity profiles & Department schemas
/ingestion/               # Deep-nested dynamic DRF Webhook Endpoints
/scoring/                 # Async anti-cheat celery workers & Score processing
/leaderboard/             # HTMX & Tailwind UI Views (Arena, Trophies, Profile Dashboards)
/notifications/           # Outbound webhook emitters for Badges
```

---

## 🚀 Quickstart (Local Launch)

### 1. Clone & Install
```bash
git clone https://github.com/mpetyx/agon-promptrank.git
cd agon-promptrank

# Create Python Virtual Environment
python3 -m venv .venv
source .venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

### 2. Scaffold Database & Seed Dummy Data
SQLite is pre-configured for an immediate launch. We've included a dummy script so you can visualize the platform instantly!
```bash
python manage.py makemigrations
python manage.py migrate

# Generate Admin Account (admin / admin123)
python manage.py shell -c "from users.models import CustomUser; CustomUser.objects.create_superuser('admin', 'admin@example.com', 'admin123')"

# Generate 150 mock logs, 5 users, and departments instantly
python seed_db.py 
```

### 3. Setup Async Workers (Celery & Redis)
*Note: For local testing, `CELERY_TASK_ALWAYS_EAGER = True` is set meaning you don't actually need Redis booted!*
For production environments, boot the queuing server:
```bash
redis-server &
celery -A config worker --loglevel=info &
```

### 4. Boot the Arena
```bash
python manage.py runserver
```
Navigate to `http://127.0.0.1:8000/` to gaze upon the Arena, or `http://127.0.0.1:8000/admin/` to set up new Dynamic Connectors.

---

## 🔌 Dynamic Admin Connectors (No Code!)

Unlike rigidly coded APIs, Agon PromptRank uses a dynamic resolver model.

**To add a new tool like ChatGPT:**
1. Navigate to your Django Admin (`/admin/`) and create a **ConnectorConfig**.
2. Name it "ChatGPT Enterprise". It will auto-generate the slug `chatgpt-enterprise`.
3. Inform the system where to look in the payload for data by providing dot-notation JSON paths. 
   - *Example Event payload:* `{"event": {"actor": {"email": "john@company.com"}}, "type": "completion", "metric": 5}`
   - *Email JSON Path Setting:* `event.actor.email`
   - *Action JSON Path Setting:* `type`
   - *Value JSON Path Setting:* `metric`

4. Tell ChatGPT to send outgoing webhooks to your new target URL:
   `POST https://<your-domain>/api/v1/ingest/chatgpt-enterprise/`

The engine will intelligently map the deep JSON parameters automatically to your corporate users!

---

## 🛡 Anti-Cheat Engine (`scoring/tasks.py`)
To prevent employees from writing automated bash loops just to gamify their score, the background engine acts as a defensive shield:
1. Queries the past **60 seconds** of logs per tool.
2. If the user surpasses generic rate limits (e.g., > 10 requests / minute), the `value_metric` generated is severely penalized (reduced by ~90%).
3. Flags the interference cleanly in the admin database.

---

## 🤝 Contributing
Agon PromptRank thrives on community contributions. Whether you are surfacing new features in the Command Center, contributing HTMX UI updates, or refining the Anti-Cheat algorithms, pull requests are warmly welcomed! Ensure all commits pass existing unit coverage constraints.

Please read our [Contributing Guidelines](CONTRIBUTING.md) and adhere to the [Code of Conduct](CODE_OF_CONDUCT.md).

---

## 📄 License
This project operates under the [MIT License](LICENSE).