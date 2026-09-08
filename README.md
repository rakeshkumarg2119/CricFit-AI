<div align="center">
  <img src="cricfit_ai_logo.png" alt="CricFit AI Logo" width="500" height="500"/>
  <h1>CricFit AI 🏏</h1>
  <p><em>AI-Powered Biomechanics & Fitness Analysis for Cricketers</em></p>
</div>

---

## 🌟 Overview

**CricFit AI** is an intelligent video-analysis platform that helps cricketers assess and improve their physical performance. Users log in, upload a **batting**, **bowling**, or **Yo-Yo test (shuttle run)** video, and our AI pipeline analyzes body mechanics to generate a structured fitness report — covering balance, stability, flexibility, and more. Reports are stored in MongoDB and enriched by **Grok AI**, which turns raw metrics into actionable, motivating feedback. On repeat uploads, CricFit AI compares the new report against the user's history to track real improvement over time. The platform also includes an **Injury Detection module**, giving athletes stage-wise guidance on reported pain/injury and when to see a doctor.

---

## ✨ Features

- **🎥 Video Upload & Analysis:** Users upload bowling or batting footage directly from the Streamlit frontend.
- **🤖 Custom Keras Models:** Separate deep-learning models trained specifically for batting and bowling action analysis.
- **🦴 Pose Estimation Engine:** Extracts body keypoints from video frames to power all biomechanical metrics.
- **📊 7-Point Fitness Report:** Every analysis scores the athlete across:
  - ⚖️ Balance
  - 🦵 Lower-body stability
  - 🧘 Flexibility / mobility
  - 💪 Core stability
  - ⚡ Agility
  - 🎯 Coordination
  - ↔️ Body symmetry
  - 🏃 Movement quality
- **🧠 Grok AI Coaching Layer:** Converts raw scores into personalized exercise recommendations and boosting/motivational messages.
- **📈 Progress Tracking:** On repeat uploads, current and historical reports are both sent to Grok AI to generate an improvement summary and updated fitness tips.
- **🏆 Bowling Action Match (Bowling-only):** Compares the user's bowling action against professional players (e.g. Jasprit Bumrah) and reports a closeness/match score, alongside improvement guidance.
- **🏃‍♂️ Yo-Yo Test Analysis:** Users upload a shuttle-run (Yo-Yo test) video; CricFit AI + Grok AI analyze running/turning form and generate improvement guidance — a key indicator for fitness and team selection.
- **🩹 Injury Detection Module:** Users select injury type(s), pain level, and body location, plus a free-text description. The system returns a **stage-wise assessment** (e.g. Stage 1 — mild, home care; up to Stage 4 — critical, requires surgical consultation), always recommending professional medical consultation for higher-severity stages.
- **🗄️ MongoDB Report History:** All reports are persisted per user, enabling longitudinal progress comparisons.

---

## 🛠️ Tech Stack

- **Frontend:** Streamlit (login, video upload, report display)
- **Backend:** Python, FastAPI
- **AI Models:** TensorFlow / Keras (custom-trained batting & bowling models, trained in Jupyter Notebook)
- **Pose Estimation:** MediaPipe
- **LLM Coaching:** Grok AI (exercise recommendations, improvement & boosting messages)
- **Database:** MongoDB (user auth, report storage, historical comparisons)
- **Computer Vision:** OpenCV

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- MongoDB (local or Atlas)
- Grok AI API Key

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/<org>/CricFit-AI.git
   cd CricFit-AI
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # Linux/Mac
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Variables:**
   Create a `.env` file based on `.env.example`:
   ```env
   GROK_API_KEY=your_key_here
   MONGODB_URI=your_mongodb_connection_string
   MODEL_PATH_BATTING=models/batting_model.h5
   MODEL_PATH_BOWLING=models/bowling_model.h5
   ```

5. **Run the FastAPI backend:**
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```

6. **Run the Streamlit frontend:**
   ```bash
   streamlit run app.py
   ```

---

## 🔄 Analysis Workflow

```text
1. User logs in via Streamlit
2. User uploads batting / bowling / Yo-Yo test video
3. Pose estimation extracts body keypoints frame-by-frame
4. Keras model (batting/bowling specific) scores the fitness metrics
   → For Yo-Yo test: form + pacing metrics generated instead
5. Report saved to MongoDB (linked to user)
6. Report sent to Grok AI → generates exercises + boosting message
7. [Bowling only] Action compared against pro player reference → match score
8. On next upload:
   → Previous + current report sent to Grok AI
   → Grok AI returns improvement summary + updated fitness tips
9. Final report returned to user via Streamlit

Injury Detection (separate flow):
1. User selects injury type(s), pain level, body location + free-text description
2. System classifies severity into stages (Stage 1 → Stage 4)
3. Stage-appropriate guidance returned (home care → medical consultation → surgical referral)
4. Higher stages always flag "consult a doctor" — module is advisory, not diagnostic
```

---

## 👥 Team

| Member                  | Responsibility                                                                 |
|--------------------------|----------------------------------------------------------------------------------|
| Varshini                 | Frontend (login, upload, report display) + frontend-side API integration code   |
| Siva Dharshana            | Backend core (FastAPI setup, auth, upload endpoint, model/Grok orchestration)    |
| Kavya                     | Backend-frontend connection, MongoDB CRUD (save/fetch/compare reports), dataset collection (batting) |
| Mithun Maharajan K        | Batting model training & tuning (Keras)                                          |
| Rakesh Kumar G             | Bowling model training & tuning (Keras), Bumrah action-match scoring logic       |
| Sudherson                 | Pose estimation metric calculation (keypoints → fitness scores), dataset collection (bowling) |

---

## 📁 Demo

<div align="center">
  <img src="demo/batting_demo.gif" width="270"/>
  <img src="demo/bowling_demo.gif" width="270"/>
  <img src="demo/yoyo_demo.gif" width="270"/>
  <br/>
  <sub>Batting · Bowling · Yo-Yo Test — live annotated analysis</sub>
</div>

- 📄 [Sample fitness report (PDF)](backend/outputs/reports/sample_report.pdf)

```text
demo/                       → Inline-preview GIFs (batting, bowling, Yo-Yo test)
backend/outputs/videos/     → Full-length annotated analysis recordings
backend/outputs/reports/    → Generated fitness reports (PDF)
```

---

## 🔮 Future Improvements

- **🏏 Live Match Ball Prediction:** Predict live delivery outcomes in real time — bowler-favored (wicket, dot ball) vs batter-favored (four, six, run) — factoring in pitch conditions.
- **🏟️ Cricket Coaching Center Deployment:** Package CricFit AI as a B2B analysis tool for cricket coaching academies to track and train multiple athletes at scale.

---

<p align="center">Building better cricketers with AI and Biomechanics. 🏏⚙️</p>
