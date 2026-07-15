# MediTwin

A Django-based healthcare AI platform for patient management, medical assistance, predictions, prescriptions, remedy recommendations, and report summarization.

## Features

- User account management (`apps/accounts`)
- AI assistant chat and medical intent handling (`apps/assistant`)
- Dashboard and analytics views (`apps/dashboard`)
- Health prediction models and dataset support (`apps/prediction`)
- Prescription and medication services (`apps/prescription`)
- Remedy recommendations and treatment guidance (`apps/remedy`)
- Medical report summarization and extraction (`apps/report_summarizer`)

## Getting Started

### Requirements

- Python 3.12+
- Django
- Other dependencies listed in `requirements.txt`

### Setup

1. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   venv\Scripts\activate
   ```

2. Install requirements:
   ```bash
   pip install -r requirements.txt
   ```

3. Apply migrations:
   ```bash
   python manage.py migrate
   ```

4. Create a superuser:
   ```bash
   python manage.py createsuperuser
   ```

5. Run the development server:
   ```bash
   python manage.py runserver
   ```

6. Open the app in your browser:
   ```
   http://127.0.0.1:8000/
   ```

## Project Structure

- `apps/` — Django applications and services
- `config/` — Django settings and URL configuration
- `templates/` — HTML templates for app views
- `static/` — Static assets
- `media/` — Uploaded media files
- `requirements.txt` — Python package dependencies
- `README.md` — Project overview and setup instructions

## Notes

- The repository uses `main` as the primary branch.
- Add a `.env` file for environment-specific settings and secrets.
- Exclude local database files, virtual environments, and cache files from commits.
