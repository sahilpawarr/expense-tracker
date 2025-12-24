# Self-Hosting Guide - Family Expense Tracker

This is a Progressive Web App (PWA) that works offline and on mobile devices. You can run it on your own server.

## Quick Start (5 minutes)

### Option 1: Docker (Simplest)
```bash
# Build image
docker build -t expense-tracker .

# Run container
docker run -p 5000:5000 \
  -e DATABASE_URL=postgresql://user:pass@localhost/expenses \
  expense-tracker
```

### Option 2: Linux/Mac (Direct Install)

**Requirements:**
- Python 3.11+
- PostgreSQL (or SQLite for testing)

**Setup:**
```bash
# 1. Clone/Download the app
cd expense-tracker

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure database (create init_db.py first)
python init_db.py

# 4. Run the server
gunicorn --bind 0.0.0.0:5000 main:app
```

### Option 3: Windows
Use WSL2 or follow the Linux guide above within WSL.

---

## Database Options

### Option A: SQLite (Simplest, Local Only)
No setup needed! The app uses SQLite by default.

```bash
# Just run:
python main.py
```

### Option B: PostgreSQL (Recommended, Shareable)
```bash
# Install PostgreSQL
# Ubuntu: sudo apt install postgresql
# Mac: brew install postgresql

# Create database
createdb family_expenses

# Run with database
export DATABASE_URL=postgresql://localhost/family_expenses
gunicorn --bind 0.0.0.0:5000 main:app
```

### Option C: Supabase (Cloud-Hosted PostgreSQL)
1. Create account at supabase.com
2. Create new project
3. Copy connection string
4. Run:
   ```bash
   export DATABASE_URL=<your-supabase-url>
   gunicorn --bind 0.0.0.0:5000 main:app
   ```

---

## Accessing from Family Phones

### Same Network (Home WiFi)
1. Find your computer's IP: `ipconfig` (Windows) or `ifconfig` (Mac/Linux)
2. On phones, visit: `http://<your-ip>:5000`
3. Tap the menu icon → "Install app"

### Remote Access (Optional)
Use ngrok for temporary public access:
```bash
ngrok http 5000
# Share the ngrok URL with family
```

Or use a proper reverse proxy like Nginx.

---

## Production Deployment

### On a VPS (DigitalOcean, Linode, AWS EC2, etc.)

**1. SSH into server**
```bash
ssh user@server-ip
```

**2. Install dependencies**
```bash
sudo apt update
sudo apt install python3.11 postgresql nginx
```

**3. Clone and setup app**
```bash
git clone <your-repo> expense-tracker
cd expense-tracker
pip install -r requirements.txt
```

**4. Setup PostgreSQL**
```bash
sudo -u postgres createdb family_expenses
```

**5. Create systemd service** (`/etc/systemd/system/expense-tracker.service`)
```ini
[Unit]
Description=Family Expense Tracker
After=network.target

[Service]
User=www-data
WorkingDirectory=/home/user/expense-tracker
ExecStart=/usr/bin/gunicorn --bind 0.0.0.0:5000 main:app
Restart=always

[Install]
WantedBy=multi-user.target
```

**6. Enable and start**
```bash
sudo systemctl daemon-reload
sudo systemctl enable expense-tracker
sudo systemctl start expense-tracker
```

**7. Setup Nginx** (`/etc/nginx/sites-available/expense-tracker`)
```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

**8. Enable and test**
```bash
sudo ln -s /etc/nginx/sites-available/expense-tracker /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

Visit `yourdomain.com` in your browser!

---

## Features

✅ **Works Offline** - Service Worker caches data  
✅ **Mobile Optimized** - Touch-friendly interface  
✅ **Installable** - Add to home screen  
✅ **No Cloud Dependency** - Self-contained  
✅ **Simple Data** - No complex cloud sync needed  

---

## Troubleshooting

**Port 5000 already in use?**
```bash
gunicorn --bind 0.0.0.0:8080 main:app
```

**Database connection error?**
```bash
# Check PostgreSQL is running
pg_isready

# Verify DATABASE_URL
echo $DATABASE_URL
```

**Can't access from phone?**
- Check both devices on same WiFi
- Check firewall allows port 5000
- Try http (not https) on local network

---

## Support

Keep it simple - this app does one thing well. For issues:
1. Check the logs: `journalctl -u expense-tracker -f`
2. Restart: `sudo systemctl restart expense-tracker`
3. Check database: `psql family_expenses`
