# GharMitra

A Flask-based local discovery demo for home-service professionals and construction material shops. The app uses server-rendered HTML, CSS, vanilla JavaScript, and JSON files for data.

## Run locally

1. Install Python 3.10 or later.
2. From this folder, create and activate a virtual environment:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. Install Flask:

   ```powershell
   pip install -r requirements.txt
   ```

4. Start the development server:

   ```powershell
   python app.py
   ```

5. Open `http://127.0.0.1:5000`.

Set `GHAR_MITRA_SECRET_KEY` to a persistent random secret before deploying. The generated fallback key is suitable only for local development and invalidates login sessions when the app restarts.

To configure the local administrator, set environment variables before starting the app:

```powershell
$env:GHAR_MITRA_ADMIN_MOBILE = "9999999999"
$env:GHAR_MITRA_ADMIN_PASSWORD = "choose-a-strong-password"
$env:GHAR_MITRA_SECRET_KEY = "choose-a-long-random-secret"
python app.py
```

Open `/admin/login`. The default development credentials are mobile `9999999999` and password `admin123`; replace them for any shared or public deployment.

## Demo behavior

- Sample approved listings are stored in `data/workers.json` and `data/shops.json`.
- Accounts and demo work requests are stored in `data/users.json` and `data/requests.json`.
- New worker and shop listings are saved with `pending` status and do not appear in public search until an administrator approves them in `/admin`.
- Search uses provider-entered city, locality, and PIN code. It does not calculate GPS distance. The optional location control only requests browser permission and does not transmit coordinates.
- Contact form submissions are a UI demo and are not emailed or persisted.
- JSON files are suitable for a local prototype, not concurrent or production use.
