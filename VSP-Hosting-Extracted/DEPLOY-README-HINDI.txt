OM SAI AUTOMOBILES / VSP WEBSITE - HOSTING NOTES

IMPORTANT: Uploaded code is titled VSP Vehicle Spare Parts and uses VSP branding. It is not yet renamed to Om Sai Automobiles.

This is a full-stack FastAPI + HTML website. Netlify alone cannot run the Python backend. This package is arranged for a single Render Web Service, which serves both the website pages and API.

DEPLOY (account/login required):
1. Extract this ZIP.
2. Upload the extracted folder to a NEW GitHub repository. Include app/, frontend/, requirements.txt, render.yaml. Do NOT upload any .env secrets.
3. Open https://render.com/ and sign in. Choose New > Blueprint, connect the GitHub repository, and deploy render.yaml.
4. After deploy, open https://YOUR-SERVICE.onrender.com/ for the shop, /manage for admin, /health to check API.
5. Free service + SQLite is for demo/testing only: local SQLite data may not be durable on a free host. For real use, configure managed PostgreSQL and backups before accepting orders.
6. Create admin using Render Shell if available: `python scripts/create_admin.py` (this deployment bundle currently needs the scripts folder added from the backend archive if you want this command; alternatively create a secure admin using your existing process).

NETLIFY OPTION:
Netlify can host only the static frontend. The Python FastAPI backend must be deployed separately and frontend API calls configured to the backend URL. Do not upload this whole full-stack package to Netlify expecting /api routes to work.

Before public use: update brand/logo/contact details, set strong JWT_SECRET (Render blueprint generates it), configure database persistence, verify all sample product prices/stock/fitment, and test auth/orders. Product catalogue contains demo data.
