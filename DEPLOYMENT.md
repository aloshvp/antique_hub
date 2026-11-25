# Antique Hub – Production Deployment Guide

> **Enterprise & Cloud Deployment Manual** | Configurations for Windows (Waitress), Linux (Gunicorn + Nginx), PythonAnywhere, and Render with MySQL

---

## 1. Production Readiness Checklist

Before publishing Antique Hub to any public server or cloud host, complete the following mandatory security and performance configurations:

### 1.1 Disable Debug Mode (`DEBUG = False`)
In production, `DEBUG` must **never** be enabled. Leaving `DEBUG=True` exposes internal code traces, active SQL queries, cryptographic keys, and environment variables during errors.
```ini
# In .env
DEBUG=False
```

### 1.2 Restrict Host Headers (`ALLOWED_HOSTS`)
Specify exact domain names and IP addresses allowed to serve requests:
```ini
# In .env
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com,127.0.0.1,your-app.onrender.com
```

### 1.3 Secure Cryptographic Secret Key (`SECRET_KEY`)
Generate a unique, cryptographically random key:
```bash
python -c "import secrets; print(secrets.token_urlsafe(50))"
```
Place the generated string into your production `.env` file and ensure `.env` is listed in `.gitignore`.

### 1.4 Static Files Compilation (`collectstatic`)
Django's development server serves static files automatically, but production WSGI servers (Gunicorn/Waitress) do not. You must compile all CSS, JavaScript, and fonts into `STATIC_ROOT`:
```bash
python manage.py collectstatic --noinput
```

### 1.5 Media Upload Storage (`MEDIA_ROOT`)
Ensure the directory for uploaded antique photographs exists and has appropriate read/write permissions:
```bash
# Linux
mkdir -p media/antiques/items
chmod -R 755 media/
```

### 1.6 Production Security Headers (Optional HTTPS Enforcements)
When serving behind an active SSL certificate (HTTPS), add the following settings to `antique_hub/settings.py`:
```python
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
```

---

## 2. Windows Deployment via Waitress

For Windows Server environments, **Waitress** is a pure-Python, production-quality WSGI server that operates efficiently without requiring Unix sockets or complex worker forks.

### Step 1: Install Waitress
```powershell
.\venv\Scripts\activate
pip install waitress
```

### Step 2: Test Run Waitress CLI
```powershell
waitress-serve --port=8000 --threads=8 antique_hub.wsgi:application
```
Access the application at `http://localhost:8000/`.

### Step 3: Run as a Background Windows Service (via NSSM)
To ensure the server starts automatically when Windows boots and restarts upon failure:
1. Download **NSSM** (Non-Sucking Service Manager) from `https://nssm.cc/download`.
2. Extract `nssm.exe` and execute:
   ```cmd
   nssm install AntiqueHubService
   ```
3. In the GUI configuration dialog:
   - **Path:** `D:\antique_hub\venv\Scripts\waitress-serve.exe`
   - **Startup directory:** `D:\antique_hub`
   - **Arguments:** `--port=8000 --threads=8 antique_hub.wsgi:application`
4. Click **Install service**.
5. Start the service:
   ```cmd
   nssm start AntiqueHubService
   ```

---

## 3. Linux Production Deployment (Gunicorn + Nginx + Systemd)

This is the standard enterprise configuration for Ubuntu / Debian Linux VPS servers (e.g., AWS EC2, DigitalOcean, Linode).

### Architecture
```
[ Client Browser ] ──HTTPS (Port 443)──► [ Nginx Reverse Proxy ]
                                                    │
                                   ┌────────────────┴────────────────┐
                                   ▼                                 ▼
                         [ Static & Media Files ]          [ Gunicorn WSGI Socket ]
                           (Served directly)                unix:/run/antique_hub.sock
                                                                     │
                                                                     ▼
                                                          [ Antique Hub Django App ]
                                                                     │
                                                                     ▼
                                                          [ MySQL 8.0 Database ]
```

### Step 1: Install System Packages
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install python3-pip python3-venv python3-dev default-libmysqlclient-dev build-essential nginx certbot python3-certbot-nginx -y
```

### Step 2: Clone & Set Up Virtual Environment
```bash
cd /var/www
sudo git clone https://github.com/your-username/antique_hub.git
sudo chown -R www-data:www-data /var/www/antique_hub
cd antique_hub
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install gunicorn
```

### Step 3: Configure Gunicorn Systemd Service
Create the service unit file:
```bash
sudo nano /etc/systemd/system/antique_hub.service
```

Paste the following configuration:
```ini
[Unit]
Description=Gunicorn daemon for Antique Hub Marketplace
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/antique_hub
ExecStart=/var/www/antique_hub/venv/bin/gunicorn \
          --access-logfile /var/log/gunicorn/access.log \
          --error-logfile /var/log/gunicorn/error.log \
          --workers 3 \
          --bind unix:/run/antique_hub.sock \
          antique_hub.wsgi:application

Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start Gunicorn:
```bash
sudo mkdir -p /var/log/gunicorn
sudo chown -R www-data:www-data /var/log/gunicorn
sudo systemctl daemon-reload
sudo systemctl start antique_hub
sudo systemctl enable antique_hub
sudo systemctl status antique_hub
```

### Step 4: Configure Nginx as Reverse Proxy
Create the Nginx site configuration:
```bash
sudo nano /etc/nginx/sites-available/antique_hub
```

Paste the following block (replace `yourdomain.com` with your actual domain):
```nginx
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    client_max_body_size 20M;

    # Serve static assets directly through Nginx
    location /static/ {
        alias /var/www/antique_hub/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, no-transform";
    }

    # Serve uploaded media directly
    location /media/ {
        alias /var/www/antique_hub/media/;
        expires 7d;
        add_header Cache-Control "public, no-transform";
    }

    # Pass all other requests to Gunicorn WSGI socket
    location / {
        include proxy_params;
        proxy_pass http://unix:/run/antique_hub.sock;
    }
}
```

Enable the configuration and reload Nginx:
```bash
sudo ln -s /etc/nginx/sites-available/antique_hub /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### Step 5: Install Free SSL Certificate (Let's Encrypt)
```bash
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```
Certbot automatically provisions an SSL certificate and configures HTTP-to-HTTPS redirection in Nginx.

---

## 4. Cloud Deployment 1: PythonAnywhere with MySQL

PythonAnywhere is a widely used managed platform for hosting Django applications with integrated MySQL databases.

### Step 1: Create Account & Open Bash Console
1. Register an account at [PythonAnywhere](https://www.pythonanywhere.com/).
2. In the dashboard, click **Consoles** and launch a new **Bash Console**.

### Step 2: Clone Repository & Create Virtual Environment
```bash
git clone https://github.com/your-username/antique_hub.git
cd antique_hub
python3.10 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 3: Create MySQL Database on PythonAnywhere
1. In the PythonAnywhere dashboard, navigate to the **Databases** tab.
2. Under **MySQL database**, set a database password.
3. In **Create a database**, type `antique_hub_db` and click **Create**.
4. Note the database connection details provided on screen:
   - **Host:** `yourusername.mysql.pythonanywhere-services.com`
   - **Database Name:** `yourusername$antique_hub_db`
   - **Username:** `yourusername`

### Step 4: Configure Production `.env`
In your bash console:
```bash
nano .env
```
Set the following:
```ini
SECRET_KEY=generate-a-unique-random-key-here
DEBUG=False
ALLOWED_HOSTS=yourusername.pythonanywhere.com

DB_ENGINE=mysql
DB_NAME=yourusername$antique_hub_db
DB_USER=yourusername
DB_PASSWORD=your_mysql_password
DB_HOST=yourusername.mysql.pythonanywhere-services.com
DB_PORT=3306
```

### Step 5: Execute Migrations, Collect Static & Seed Data
```bash
python manage.py migrate
python manage.py collectstatic --noinput
python scripts/seed_demo_data.py
```

### Step 6: Configure PythonAnywhere Web Tab
1. In the dashboard, click the **Web** tab.
2. Click **Add a new web app**, choose **Manual configuration**, and select **Python 3.10**.
3. Under **Virtualenv**, set the path to:  
   `/home/yourusername/antique_hub/venv`
4. Under **Code**, set **Source code** to:  
   `/home/yourusername/antique_hub`
5. Click on the **WSGI configuration file** link to edit it. Replace its entire contents with:
   ```python
   import os
   import sys

   path = '/home/yourusername/antique_hub'
   if path not in sys.path:
       sys.path.append(path)

   os.environ['DJANGO_SETTINGS_MODULE'] = 'antique_hub.settings'

   from django.core.wsgi import get_wsgi_application
   application = get_wsgi_application()
   ```
6. In the **Static files** section, add two url-to-path mappings:
   - **URL:** `/static/` $\rightarrow$ **Directory:** `/home/yourusername/antique_hub/staticfiles/`
   - **URL:** `/media/` $\rightarrow$ **Directory:** `/home/yourusername/antique_hub/media/`
7. Click the green **Reload yourusername.pythonanywhere.com** button.
8. Visit your live site at `https://yourusername.pythonanywhere.com/`!

---

## 5. Cloud Deployment 2: Render.com with Managed MySQL

Render is a modern cloud platform offering seamless Git-based CI/CD deployment.

### Step 1: Prepare a Cloud MySQL Database
You can provision a free managed MySQL database on [Aiven.io](https://aiven.io/) or [PlanetScale](https://planetscale.com/):
1. Create a MySQL database and retrieve the:
   - Hostname (e.g., `mysql-antique-hub.aivencloud.com`)
   - Port (e.g., `12345`)
   - User, Password, and Database Name (`antique_hub_db`)

### Step 2: Create a Web Service on Render
1. Log in to [Render Dashboard](https://dashboard.render.com/) and click **New + $\rightarrow$ Web Service**.
2. Connect your GitHub repository containing Antique Hub.
3. Configure the following build settings:
   - **Name:** `antique-hub`
   - **Region:** Singapore / Frankfurt / Oregon (choose closest to users)
   - **Branch:** `main`
   - **Runtime:** `Python 3`
   - **Build Command:**
     ```bash
     pip install --upgrade pip && pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate && python scripts/seed_demo_data.py
     ```
   - **Start Command:**
     ```bash
     gunicorn antique_hub.wsgi:application --bind 0.0.0.0:$PORT
     ```

### Step 3: Configure Environment Variables in Render
In the **Environment Variables** section of your Render Web Service, add:

| Key | Value |
|---|---|
| `PYTHON_VERSION` | `3.11.8` |
| `DEBUG` | `False` |
| `SECRET_KEY` | *(Generate a 50-character random key)* |
| `ALLOWED_HOSTS` | `.onrender.com` |
| `DB_ENGINE` | `mysql` |
| `DB_NAME` | `antique_hub_db` |
| `DB_USER` | `avnadmin` |
| `DB_PASSWORD` | *(Your Aiven/PlanetScale password)* |
| `DB_HOST` | *(Your cloud database host)* |
| `DB_PORT` | `12345` |

### Step 4: Add Persistent Disk for Uploaded Media
Because cloud containers have ephemeral filesystems, uploaded photos would be wiped on every deploy unless a disk is attached:
1. In your Render service, click **Disks $\rightarrow$ Add Disk**.
2. **Name:** `antique_media_disk`
3. **Mount Path:** `/opt/render/project/src/media`
4. **Size:** 1 GB (or as required)
5. Save and deploy.

Your application will build, migrate, seed demo records, and deploy live at:  
👉 **`https://antique-hub.onrender.com`**

---

## 6. Post-Deployment Verification Steps

After deploying to any platform, verify the following 5 smoke tests:

1. **Homepage Loading:** Check that the landing page renders with the antique theme, fonts, and images.
2. **Catalog Browsing:** Ensure `/catalog/marketplace/` returns results and images load without broken links.
3. **Admin Login:** Navigate to `/accounts/login/` and log in with `admin` / `AdminPass123!`. Check that the Dashboard and Chart.js charts load.
4. **End-to-End Test Purchase:** Log in with `collector_roy` / `BuyerPass123!`, add an item to the cart, check out with card `4111 1111 1111 1111`, and confirm that the printable Tax Invoice with the green `PAID` stamp displays correctly.
5. **PDF Report Export:** As admin, navigate to `/dashboard/admin/reports/orders/` and click **Export PDF** to ensure ReportLab generates and downloads the document cleanly.
