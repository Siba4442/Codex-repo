# MenuExtractor (OCR + Multimodal LLM Menu Parsing)

MenuExtractor is a multi-phase extraction system that converts restaurant menu PDFs into structured JSON using OCR + multimodal LLMs.  
It is designed for **high accuracy**, supports **multi-page menus**, and includes an API layer for production integration.

---

## ✨ What This Project Does

Given a menu PDF, the pipeline extracts:

✅ **Phase 1 — Categories**  
- Discovers category headings per page  
- Optionally detects subcategories  

✅ **Phase 2 — Items Under Categories**  
- Extracts item names (and optionally descriptions/prices/variations) under each category  
- Handles multi-column/menu layouts using image + text prompting  



The system uses:
- **FastAPI** for production endpoints
- **OpenRouter multimodal LLM** as extraction engine
- **Pydantic schemas** for strict validation
- **Repair logic** to handle malformed LLM JSON

---

## 📁 Repo Layout

backend/
main.py # FastAPI app
extractor.py # multi-phase pipeline logic
prompts/ # phase prompt templates (.j2)
utils/ # client + pdf/image processing + models
outputs/ # generated runtime outputs (ignored in git)
evaluation/ # gold + metrics + reports (see subfolder README)

frontend/
index.html # basic UI
categories.html
items.html

🚀 API Endpoints (Main)
✅ Phase 1: Upload PDF & Extract Categories

POST /api/phase1/extract-categories

Upload a PDF

Returns a job_id

Saves Phase 1 output in job folder

✅ Phase 2: Extract Items Under Categories

POST /api/phase2/extract-items/{job_id}

Provide reviewed categories payload

Returns structured category → items output

Saves Phase 2 output