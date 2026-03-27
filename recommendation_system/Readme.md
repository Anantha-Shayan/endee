# 🚀 AI-Powered Job Recommendation System

An intelligent job recommendation system that matches candidates to relevant job roles based on their resume using semantic similarity.

Powered by **ENDEE**.

---

## 📌 Overview

This extracts information from a candidate’s resume once uploaded, converts it into embeddings, and performs similarity search with stored job embeddings to recommend the most relevant jobs.

It also highlights **missing skills** and **AI powered improvements and suggestions**, helping users understand how to improve their profile.

---

## ⚙️ Features

- 📄 Resume parsing (Only PDF/DOCX. Image, scanned pdfs not supported for now )
- 🧠 Semantic similarity using sentence embeddings
- 📊 Match score for each job
- ❗ Missing skills identification
- 🤖 AI Powered suggestions
- 🌐 Clean frontend for job recommendations
- 🔁 Persistent job storage using `jobs.json`

---

## 🏗️ Tech Stack

### Backend
- Python
- Flask

### Machine Learning
- Sentence Transformers (`all-MiniLM-L6-v2`)
- NumPy

### Retrieval System
- Endee

### Frontend
- HTML + Tailwind CSS

---

## 📂 Project Structure

```text
recommendation_system/<br>
│<br>
├── app.py # Flask backend<br>
├── build_vector_store.py # Embedding & indexing logic<br>
├── jobs.json # Job dataset<br>
├── templates/<br> # Frontend
│ └── home.html
│ └── jobs.html
├── static/ # Static assets (if any)<br>
├── uploads/ # Uploaded resumes<br>
├── requirements.txt<br>
└── README.md<br>
```

---


## 🔄 How It Works

### 1. Resume Upload
- User uploads a resume (PDF/DOCX only. Images and scanned pdfs not supported yet)

### 2. Text Extraction
- Resume is parsed into raw text. Requiered sections (e.g., skills) are extracted.

### 3. Embedding Generation
- Extracted text and sections are converted into vector embeddings

### 4. Similarity Search
- Resume embeddings are compared with pre-stored job embeddings for top-k similarity.

### 5. Ranking
- Jobs are ranked based on match score

### 6. Skill Gap Analysis
- Missing skills are identified by comparing resume vs job requirements.<br>
  AI powered suggestions and improvements are provided.

---

## 🧠 Core Logic

- Uses **cosine similarity** between embeddings
- Jobs are pre-processed and stored in a structured format (`jobs.json`)
- Resume embedding is matched against job embeddings

---

## 🚀 Setup Instructions

### 1. Clone the Repository

```bash 
git clone https://github.com/Anantha-Shayan/endee.git
cd endee/recommendation_system
```

### 2. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate     # Linux/Mac
venv\Scripts\activate        # Windows
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Build Embeddings
```bash
python build_vector_store.py
```

### 5. Run the Application
```bash
python app.py
```

### 6. Open in Browser
```bash
http://localhost:5000
```

---

## ⚠️ Current Limitations<br>
Skill extraction is rule-based (can be improved with NLP)<br>
Match scoring may not always align perfectly with human intuition<br>
No user authentication (yet)<br>
Limited dataset (depends on jobs.json)<br>

## 🔥 Future Improvements
✅ Better skill extraction using NLP / LLMs<br>
✅ Weighted scoring (skills > experience > keywords)<br>
✅ Real-time job scraping (LinkedIn, Indeed APIs)<br>
✅ Deploy using Docker + Cloud (AWS/GCP)<br>
✅ Expand Endee into a full retrieval engine<br>
✅ Add recruiter-side AI Hiring Copilot<br>
✅ Resume feedback & improvement suggestions<br>

💡 Use Cases<br>
Students preparing for placements<br>
Job seekers improving resumes<br>
Recruiters screening candidates<br>
Demonstration of ML + backend integration<br>

🧑‍💻 Author

Anantha Shayan
BTech CSE (AI & ML)
