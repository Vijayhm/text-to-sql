# 🚀 Natural Language to SQL Chatbot (FastAPI + Gemini + AWS)

A chatbot that allows users to **query a database in natural language**, which is then **converted into SQL using Google's Gemini API**. The results are summarized and displayed as a **table**.

---

## ✨ Features
✅ Convert **natural language queries** to SQL  
✅ Uses **Google Gemini API** for AI-based query generation  
✅ Supports **SQLite (local) & AWS RDS (for production)**  
✅ Summarizes results in a human-readable format  
✅ Displays query results in a **table format** in the UI  
✅ **FastAPI-based** backend with **CORS enabled**  

---

## 🛠️ Tech Stack
- **Backend:** FastAPI, Uvicorn
- **Frontend:** HTML, JavaScript (fetch API)
- **Database:** SQLite (local), AWS RDS (production)
- **AI Integration:** Google Gemini API
- **Cloud Hosting:** AWS EC2 (for deployment)
- **Caching:** AWS DynamoDB (optional)

---

## 🚀 Installation & Setup
### **1️⃣ Clone the Repository**
```bash
git clone https://github.com/vijayhm/text-to-sql.git
cd your-repo
