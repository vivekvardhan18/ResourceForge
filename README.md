# 📚 ResourceForge

An educational resource-sharing platform that helps students discover, organize, and track study material — built with Flask and a pandas-based recommendation engine.

## Features

- 🔍 Search and get recommended learning resources by topic, level, and type
- 🔐 User accounts with login/signup (Flask-Login)
- 🔖 Bookmark resources and organize them into personal learning paths
- ✅ Track progress on each learning path (not started / in progress / completed)
- 🤖 Lightweight content-based recommender (`ml_recommender.py`) for personalized suggestions

## Tech Stack

- **Backend:** Python, Flask, Flask-Login
- **Data:** pandas (CSV-backed storage for users, bookmarks, and learning paths)
- **Frontend:** Jinja2 templates, HTML/CSS

## Getting Started

```bash
pip install -r requirements.txt
python app.py
```

The app runs at `http://localhost:5000`.

> **Note:** This started as a learning project — data is stored in flat CSV files rather than a real database, and auth is intentionally simple. Not production-hardened.
