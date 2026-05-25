# Breathe ESG Ingestion Review

A Django REST + React prototype for ingesting enterprise emissions activity data, normalizing it into reviewable rows, and locking approved rows for audit.

## What It Handles

- SAP fuel/procurement CSV shaped like an IDoc/flat-file projection with plant, document, material, quantity, unit, vendor, and posting date fields.
- Utility portal electricity CSV with meter, tariff, billing period, kWh, demand, and account metadata.
- Corporate travel export with Concur-like expense rows for flights, hotels, taxis, and rentals.
- Analyst workflow: filter queue, inspect raw source payload, edit normalized quantity/factor/notes, approve, reject, and lock.
- Audit trail for analyst edits and status transitions.

## Run Locally

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
cd frontend
& 'C:\nvm4w\nodejs\npm.cmd' install
& 'C:\nvm4w\nodejs\npm.cmd' run build
cd ..
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py seed_demo
.\.venv\Scripts\python.exe manage.py runserver
```

Open `http://127.0.0.1:8000/`.

## API Shortcuts

- `GET /api/summary/?tenant=acme-industrial`
- `GET /api/activities/?tenant=acme-industrial&status=needs_review`
- `POST /api/upload/` with `tenant`, `source_type`, and CSV `file`
- `POST /api/activities/{id}/approve/`
- `POST /api/activities/{id}/reject/`
- `POST /api/activities/{id}/lock/`

## Demo Files

Sample files live in `sample_data/` and are ingested by `python manage.py seed_demo`.
