# Invoice Extractor — Setup Guide

## What this is
A simple 2-file app: Python backend + HTML frontend.
Upload any invoice → AI extracts all fields instantly.

---

## Step 1 — Install dependencies

```bash
pip install flask flask-cors requests
```

---

## Step 2 — Get your OpenRouter API key

1. Go to https://openrouter.ai
2. Sign up (free)
3. Go to Keys → Create new key
4. Copy the key (starts with sk-or-v1-...)

---

## Step 3 — Add your key to app.py

Open app.py and find this line:

```python
OPENROUTER_API_KEY = "sk-or-v1-YOUR_KEY_HERE"
```

Replace with your actual key.

---

## Step 4 — Run the app

```bash
python app.py
```

Then open your browser at:
http://localhost:5000

---

## Files

```
invoice_app/
├── app.py       ← Python backend (Flask)
└── index.html   ← Frontend (HTML + CSS + JS)
```

---

## Free models on OpenRouter you can use

| Model | Speed | Quality |
|-------|-------|---------|
| google/gemini-2.0-flash-001 | Very fast | Excellent (default) |
| meta-llama/llama-3.2-11b-vision-instruct | Fast | Good |
| mistralai/mistral-small-3.1-24b-instruct | Medium | Very good |

Change the MODEL variable in app.py to switch.

---

## How to show the demo to a CA client

1. Run app.py on your laptop
2. Open http://localhost:5000
3. Say: "Do you have any invoice on your phone?"
4. Let them upload it or use the sample
5. Watch the magic happen in 5 seconds
6. Say: "How long does your staff take to type this manually?"
7. Stay silent.

That silence is where they sell themselves.
