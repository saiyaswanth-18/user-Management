# Northstar User Management

A Dockerized account-registration and login application. It uses React for the frontend, FastAPI for the API, PostgreSQL for verified accounts, Redis for short-lived registration data and OTPs, and SMTP for delivering verification codes.

## Run locally

1. Install Docker Desktop with Docker Compose.
2. Copy `.env.example` to `.env`. The included defaults are for local development only.
3. Start the services:

   ```powershell
   docker compose up --build
   ```

4. Open the app at <http://localhost:8081>.
5. Register with an email address, then open the Mailpit inbox at <http://localhost:8025> and enter the 6-digit code.

Mailpit captures outbound mail locally, so no external SMTP account is needed for development. To send real email, set `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_USE_TLS` or `SMTP_STARTTLS`, and `EMAIL_FROM` in `.env` to match your mail provider. A delivery error is shown to the user; the pending registration is removed so they can retry.

### Send verification codes through Gmail

1. Enable 2-Step Verification on the Google account that will send the email.
2. Create an App Password in that Google account's Security settings. Use the generated App Password, not your normal Gmail password. Google may not offer App Passwords for some account types or when the account is managed by an organization.
3. Edit `.env` and set the SMTP values as follows, replacing the two address/password placeholders. Do not share or commit the App Password.

   ```dotenv
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USERNAME=your.address@gmail.com
   SMTP_PASSWORD=your-16-character-app-password
   SMTP_USE_TLS=false
   SMTP_STARTTLS=true
   EMAIL_FROM=your.address@gmail.com
   ```

4. Recreate the backend container so it loads the new settings:

   ```powershell
   docker compose up -d --force-recreate backend
   ```

5. Register in the app with an email address you can access. The verification code will be sent through Gmail; it will no longer appear in Mailpit.

If delivery fails, check the backend logs with `docker compose logs backend` and verify the Gmail address, App Password, and SMTP settings. The app removes the pending registration when email delivery fails, so register again after correcting the settings.

## Workflow and storage

- Registration validates the email and password, hashes the password, then stores the pending name, email, password hash, and an HMAC-protected OTP in Redis for 10 minutes.
- The 6-digit OTP is emailed through the configured SMTP server. It is single-use and limited to 5 attempts.
- A correct OTP consumes the pending Redis registration and creates a verified user in PostgreSQL. Unverified registrations are not inserted into the users table.
- Login checks the password hash and verified status, then returns a short-lived bearer token.

The frontend and API share the same origin; Nginx forwards `/api/` to FastAPI. PostgreSQL and Redis data persist in named Docker volumes.

## Configuration

See `.env.example` for all supported settings. Before deployment, use strong unique values for `POSTGRES_PASSWORD` and `JWT_SECRET`, configure a real SMTP provider, and terminate HTTPS at a trusted reverse proxy. The Compose file publishes the frontend and Mailpit web interface; database and Redis ports are intentionally internal to the Docker network.

API docs are available at <http://localhost:8081/api/docs>.

## Stop services

```powershell
docker compose down
```

To also delete persisted local database and Redis data, run `docker compose down -v`.
