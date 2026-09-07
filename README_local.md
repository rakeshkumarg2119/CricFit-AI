# 🏏 CricFit AI — AI-Powered Cricket Fitness Coach

> **"Upload. Analyze. Improve."**  
> An AI-driven movement quality, posture, balance, and physical conditioning application for cricket athletes.

---

## 📌 Project Overview

**CricFit AI** is a cutting-edge sports-tech platform designed to analyze an athlete's physical performance through cricket movements. While traditional applications focus solely on cricket shot execution, **CricFit AI** uses batting and bowling video actions as the vehicle to measure key biomechanical health indicators:

- **Movement Quality & Coordination**
- **Balance & Trunk Control**
- **Lower-Body Plant Stability**
- **Hip Mobility & Rotation**
- **Core Stability & Anti-Rotational Strength**
- **Bilateral Body Symmetry**

---

## ✨ Key Features

1. **🔒 Athlete Authentication**: Login and registration interface with session state persistence.
2. **🎯 Activity Selector (Batting vs. Bowling)**: Independent analysis pipelines for Batting strokes and Bowling actions.
3. **📹 Video Upload & Validation**: Secure file uploader supporting `.mp4`, `.mov`, `.avi` with real-time format and size validation.
4. **🧠 Step-by-Step AI Pipeline Display**: Simulated pose landmark detection, biomechanical evaluation, and fitness insight generation.
5. **📊 Comprehensive Fitness Report**:
   - Circular Overall Fitness Gauge (e.g. 78/100)
   - 7 Core Biomechanical Metrics with explicit text status labels (*Excellent, Good, Average, Needs Improvement*)
   - Interactive **Plotly Biomechanical Radar Chart**
   - 🤖 **CRICFIT AI Insight Box** with natural language feedback
   - **Strengths & Areas to Improve Cards** with priority levels
   - **Personalized Fitness Plan**: Exercise cards with set/rep prescriptions, difficulty tags, and biomechanical rationale
6. **💾 Report Saving & History**: Store report outputs locally for fast access in **My Reports**.
7. **📈 Historical Progress Tracking**: Interactive Plotly score trend line charts tracking performance over multiple analyses.
8. **👤 Athlete Profile**: High-level athlete summary, total analyses completed, and personal best scores.

---

## 🛠️ Technology Stack

- **Frontend Interface**: Streamlit (Python)
- **Visualizations**: Plotly Express & Plotly Graph Objects
- **Data Parser**: Resilient JSON adapter for Keras AI model schema normalization
- **Styling**: Modern dark sports-tech CSS injection with glassmorphism aesthetics
- **Future Backend**: FastAPI + Keras Pose Estimation AI Model + MongoDB

---

## 📂 Project Architecture

```
cricfit-ai/
│
├── frontend/                   # Streamlit Frontend Web Application
│   ├── app.py                  # Main entrypoint, design system CSS & page router
│   ├── config.py               # Frontend settings, pages, branding, backend URL
│   ├── requirements.txt        # Frontend-specific Python dependencies
│   ├── pages/                  # Page views (login, home, batting, bowling, yoyo, injury, reports)
│   ├── components/             # UI components (navbar, sidebar, cards, charts)
│   ├── services/               # API clients and response parsers
│   ├── utils/                  # Session state and formatting helpers
│   ├── assets/                 # App logos and images
│   └── static/                 # Static web resources
│
├── backend/                    # FastAPI Backend Service
│   ├── main.py                 # FastAPI endpoints & CORS configuration
│   ├── database.py             # MongoDB connection manager
│   ├── injury_service.py       # Rule-based injury screening engine
│   └── requirements.txt        # Backend-specific dependencies
│
├── batting_model/              # Batting biomechanics ML pipeline
├── bowling_model/              # Bowling biomechanics ML pipeline
├── yoyo_test_model/            # Yo-Yo cadence tracker & ML pipeline
│
├── run_project.py              # Unified launcher (starts backend + frontend)
├── run_project.bat             # Windows launcher script
├── run_project.ps1             # PowerShell launcher script
├── start.ps1                   # Dual-window development launcher
├── app.py                      # Root convenience shim forwarding to frontend/app.py
├── requirements.txt            # Root dependencies
└── .env                        # Environment configuration
```

---

## 🚀 Quick Start Guide

### 1. Prerequisites
Ensure Python 3.9+ is installed on your system.

### 2. Installation
Navigate to the project root directory:

```bash
cd cricfit-ai
```

Install required Python packages:

```bash
pip install -r requirements.txt
```

### 3. Running the Application (One Command)
Launch both the **FastAPI backend** and **Streamlit frontend** with a single command:

**Cross-platform (Recommended):**
```bash
python run_project.py
```

**Windows Batch:**
```cmd
run_project.bat
```

**PowerShell:**
```powershell
.\run_project.ps1
```

The launcher will:
1. Detect and activate your virtual environment automatically.
2. Start the FastAPI backend and verify its health endpoint (`/health`).
3. Start the Streamlit application at `http://localhost:8501`.
4. Gracefully terminate both services when you press `Ctrl+C`.

---

## 🎯 Mock Mode vs. Live Backend Mode

- **Mock Mode (`USE_MOCK=true`)**: Enabled by default in `.env`. Allows testing and presenting the complete application flow (video upload, step processing, fitness reports, Plotly charts, report saving) without needing a running backend server.
- **Live Backend Mode (`USE_MOCK=false`)**: Set `USE_MOCK=false` in `.env` and provide your FastAPI endpoint URL (`BACKEND_URL=http://localhost:8000`).

---

## 🔗 Future AI Model & Backend Integration

The backend AI pipeline expected architecture:

```
[ USER VIDEO ] ──> [ STREAMLIT FRONTEND ] ──> [ FASTAPI BACKEND ] ──> [ KERAS POSE MODEL ]
                                                                             │
[ STREAMLIT REPORT UI ] <── [ REPORT GENERATOR ] <── [ JSON ANALYSIS ] <─────┘
```

The frontend includes a defensive adapter (`services/parser.py`) that normalizes incoming Keras JSON fields, providing fallback defaults so that API variations or missing parameters never break the user interface.

---

## 📄 License
Hackathon Project — Created for CricFit AI.
