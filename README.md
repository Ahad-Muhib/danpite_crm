# Danpite CRM - Enterprise Business Management System

A comprehensive, production-ready Customer Relationship Management (CRM) and Enterprise Resource Planning (ERP) platform built with Django. Designed for businesses to manage sales pipelines, customer relations, invoicing, multi-account finances, orders, and human resources in a unified interface.

---

##  Key Modules & Capabilities

- **Executive Dashboard**: Real-time sales analytics, deal win rates, revenue vs expense graphs, upcoming follow-ups, and key financial summaries.
- **Lead & Deal Pipeline**: Complete sales funnel management, activity tracking (calls, emails, meetings), recurring follow-ups, and one-click lead-to-client conversion.
- **Client Directory**: Multi-category client profiling, account manager assignment, and complete transaction history.
- **Invoicing & Payments**: Dynamic multi-item invoice generation, partial & full payment tracking, multi-currency support, custom logo branding, and print-ready PDF invoices.
- **Multi-Account Banking & Expense Tracking**: Support for Bank Accounts, Cash Registers, and Mobile Financial Services (bKash, Nagad, Rocket, Upay). Features internal fund transfers and categorized expense tracking with receipts.
- **Order Management**: Order lifecycle tracking (Pending, Processing, Shipped, Delivered) linked with client profiles.
- **Human Resources (HR)**: Employee directory, role-based access control (Admin, Manager, HR, Employee), leave management with approval workflows, attendance logs, and automatic user account deactivation upon employee termination.
- **Audit & Activity Logs**: System-wide event logging recording creations, updates, and deletions across all modules.

---

##  Technology Stack

- **Backend**: Python 3.11+ / Django 5.2 (LTS)
- **Database**: PostgreSQL (Production) / SQLite (Development)
- **Frontend**: Vanilla CSS, Bootstrap 5.3, Bootstrap Icons, Google Fonts (Plus Jakarta Sans)
- **Static Assets**: WhiteNoise with Brotli/Gzip compression & manifest caching
- **WSGI Server**: Gunicorn
- **Security**: Granular role-based permissions, CSRF protection, secure session management, SSL/HSTS hardening

---

##  Local Development Setup

### 1. Clone the repository & enter the directory:
```bash
git clone <repository_url>
cd danpite_crm
```

### 2. Create and activate a Python virtual environment:
- **On Linux/macOS:**
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```
- **On Windows (PowerShell):**
  ```powershell
  python -m venv venv
  .\venv\Scripts\Activate.ps1
  ```

### 3. Install required dependencies:
```bash
pip install -r requirements.txt
```

### 4. Configure environment variables:
Copy the example environment file:
```bash
cp .env.example .env
```
Open `.env` and verify your local settings (default settings use SQLite and `DEBUG=True`).

### 5. Run database migrations:
```bash
python manage.py migrate
```

### 6. Create an administrator account:
```bash
python manage.py createsuperuser
```

### 7. Start the development server:
```bash
python manage.py runserver
```
Navigate to `http://127.0.0.1:8000` in your web browser and log in with your superuser credentials.

---

##  Production Deployment Guide (Ubuntu 22.04 / 24.04 LTS)

Follow these steps to deploy Danpite CRM to a production Linux VPS with **PostgreSQL**, **Gunicorn**, **Nginx**, and **Let's Encrypt SSL**.

### Step 1: System Packages & Dependencies
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-pip python3-venv python3-dev libpq-dev postgresql postgresql-contrib nginx curl git
```

### Step 2: Configure PostgreSQL Database
```bash
sudo -u postgres psql
```
Inside the PostgreSQL shell:
```sql
CREATE DATABASE danpite_crm_db;
CREATE USER crm_user WITH PASSWORD 'YourStrongPasswordHere';
ALTER ROLE crm_user SET client_encoding TO 'utf8';
ALTER ROLE crm_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE crm_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE danpite_crm_db TO crm_user;
\q
```

### Step 3: Application Setup
```bash
cd /var/www
sudo git clone <repository_url> danpite_crm
cd /var/www/danpite_crm
sudo python3 -m venv venv
sudo chown -R www-data:www-data /var/www/danpite_crm
sudo -u www-data ./venv/bin/pip install -r requirements.txt
```

### Step 4: Configure Production `.env`
Create `/var/www/danpite_crm/.env`:
```ini
SECRET_KEY=generate_a_strong_50_character_secret_key
DEBUG=False
ALLOWED_HOSTS=crm.yourdomain.com,www.crm.yourdomain.com
CSRF_TRUSTED_ORIGINS=https://crm.yourdomain.com,https://www.crm.yourdomain.com
DATABASE_URL=postgres://crm_user:YourStrongPasswordHere@localhost:5432/danpite_crm_db

SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_HSTS_SECONDS=31536000

EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your_email@gmail.com
EMAIL_HOST_PASSWORD=your_app_password
DEFAULT_FROM_EMAIL=Danpite CRM <no-reply@yourdomain.com>
```

### Step 5: Migrate Database & Collect Static Files
```bash
sudo -u www-data ./venv/bin/python manage.py migrate
sudo -u www-data ./venv/bin/python manage.py collectstatic --noinput
sudo -u www-data ./venv/bin/python manage.py createsuperuser
```

### Step 6: Configure Gunicorn Systemd Service
Create `/etc/systemd/system/gunicorn.service`:
```ini
[Unit]
Description=Gunicorn daemon for Danpite CRM
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/danpite_crm
ExecStart=/var/www/danpite_crm/venv/bin/gunicorn \
          --access-logfile - \
          --workers 3 \
          --bind unix:/run/gunicorn.sock \
          danpite_crm.wsgi:application

[Install]
WantedBy=multi-user.target
```
Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl start gunicorn
sudo systemctl enable gunicorn
```

### Step 7: Configure Nginx Reverse Proxy
Create `/etc/nginx/sites-available/danpite_crm`:
```nginx
server {
    server_name crm.yourdomain.com;

    client_max_body_size 25M;

    location = /favicon.ico { access_log off; log_not_found off; }

    location /static/ {
        alias /var/www/danpite_crm/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, max-age=2592000";
    }

    location /media/ {
        alias /var/www/danpite_crm/media/;
        expires 7d;
        add_header Cache-Control "public, max-age=604800";
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:/run/gunicorn.sock;
    }
}
```
Enable the site and restart Nginx:
```bash
sudo ln -s /etc/nginx/sites-available/danpite_crm /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### Step 8: Install SSL Certificate (HTTPS)
```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d crm.yourdomain.com
```

---

##  Environment Configuration Reference

| Variable | Type | Description | Example |
| :--- | :--- | :--- | :--- |
| `SECRET_KEY` | String | Django cryptographic signing key | `django-insecure-...` |
| `DEBUG` | Boolean | Debug mode (`False` in production) | `False` |
| `ALLOWED_HOSTS` | Comma-separated | Domains allowed to serve the app | `crm.domain.com,127.0.0.1` |
| `CSRF_TRUSTED_ORIGINS` | Comma-separated | Trusted origins for HTTPS forms | `https://crm.domain.com` |
| `DATABASE_URL` | String (URI) | PostgreSQL / MySQL connection string | `postgres://user:pass@host:5432/db` |
| `SECURE_SSL_REDIRECT` | Boolean | Redirect HTTP to HTTPS | `True` |
| `SESSION_COOKIE_SECURE`| Boolean | Send session cookies only via HTTPS | `True` |
| `CSRF_COOKIE_SECURE` | Boolean | Send CSRF cookies only via HTTPS | `True` |
| `SECURE_HSTS_SECONDS` | Integer | HTTP Strict Transport Security duration | `31536000` |
| `EMAIL_BACKEND` | String | Django email backend class | `...backends.smtp.EmailBackend` |
| `EMAIL_HOST` | String | SMTP host server | `smtp.gmail.com` |
| `EMAIL_PORT` | Integer | SMTP port | `587` |
| `EMAIL_HOST_USER` | String | SMTP authentication user | `notifications@domain.com` |
| `EMAIL_HOST_PASSWORD` | String | SMTP password / app password | `app_password` |

---

##  Maintenance & Backup

### Automated PostgreSQL Backup Script
Create `/home/ubuntu/backup_crm.sh`:
```bash
#!/bin/bash
BACKUP_DIR="/var/backups/danpite_crm"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
mkdir -p "$BACKUP_DIR"

# Backup Database
pg_dump -U crm_user -h localhost danpite_crm_db > "$BACKUP_DIR/db_$TIMESTAMP.sql"

# Backup Uploaded Media Files
tar -czf "$BACKUP_DIR/media_$TIMESTAMP.tar.gz" -C /var/www/danpite_crm media

# Keep only the last 14 days of backups
find "$BACKUP_DIR" -type f -mtime +14 -delete
```
Make executable and add to crontab:
```bash
chmod +x /home/ubuntu/backup_crm.sh
# Run nightly at 2:00 AM
(crontab -l 2>/dev/null; echo "0 2 * * * /home/ubuntu/backup_crm.sh") | crontab -
```

---

##  License & Commercial Terms
Proprietary commercial software. Unauthorized copying, distribution, or decompilation of this software is strictly prohibited.
