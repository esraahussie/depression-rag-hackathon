# depression-rag-hackathon

MindCare lives in the `depression-rag-hackathon/` folder.

```powershell
cd depression-rag-hackathon
pip install -r requirements.txt
# create a .env file with GROQ_API_KEY=...
uvicorn api:app --reload --port 8000
```

```powershell
cd depression-rag-hackathon\frontend
npm install
npm run dev
```

Open http://localhost:5173
