#!/bin/bash
# Dulce Arte - Setup Script for AWS EC2 (Ubuntu 22.04)
# Run as: sudo bash setup_ec2.sh

set -e

echo "========================================"
echo "Dulce Arte - EC2 Setup Script"
echo "========================================"

# Variables
PROJECT_DIR="/opt/dulcearte"
REPO_URL="https://github.com/TU_USUARIO/dulcearte.git"  # Cambiar por tu repo
DB_NAME="dulcearte"
DB_USER="dulcearte"
DB_PASSWORD=$(openssl rand -base64 32)
SECRET_KEY=$(openssl rand -base64 64)

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log() { echo -e "${GREEN}[$(date '+%H:%M:%S')] $1${NC}"; }
warn() { echo -e "${YELLOW}[$(date '+%H:%M:%S')] WARNING: $1${NC}"; }
error() { echo -e "${RED}[$(date '+%H:%M:%S')] ERROR: $1${NC}"; exit 1; }

# Check root
if [[ $EUID -ne 0 ]]; then
   error "Este script debe ejecutarse como root (sudo)"
fi

# Update system
log "Actualizando sistema..."
apt-get update && apt-get upgrade -y

# Install dependencies
log "Instalando dependencias del sistema..."
apt-get install -y \
    python3 python3-venv python3-pip \
    postgresql postgresql-contrib \
    nginx \
    git \
    curl \
    certbot python3-certbot-nginx \
    build-essential libpq-dev \
    redis-server

# Configure PostgreSQL
log "Configurando PostgreSQL..."
sudo -u postgres psql <<EOF
CREATE DATABASE ${DB_NAME};
CREATE USER ${DB_USER} WITH ENCRYPTED PASSWORD '${DB_PASSWORD}';
ALTER ROLE ${DB_USER} SET client_encoding TO 'utf8';
ALTER ROLE ${DB_USER} SET default_transaction_isolation TO 'read committed';
ALTER ROLE ${DB_USER} SET timezone TO 'America/Santiago';
GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};
\q
EOF

# Create project directory
log "Creando directorio del proyecto..."
mkdir -p ${PROJECT_DIR}
cd ${PROJECT_DIR}

# Clone repository (or copy files if local)
if [ -d ".git" ]; then
    log "Repositorio ya existe, actualizando..."
    git pull origin main
else
    log "Clonando repositorio..."
    git clone ${REPO_URL} .
fi

# Create virtual environment
log "Creando entorno virtual..."
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
log "Instalando dependencias Python..."
pip install --upgrade pip
pip install -r requirements.txt

# Create .env file
log "Creando archivo .env..."
cat > .env <<EOF
DEBUG=False
SECRET_KEY=${SECRET_KEY}
ALLOWED_HOSTS=*,localhost,127.0.0.1,$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)

# Database
DB_NAME=${DB_NAME}
DB_USER=${DB_USER}
DB_PASSWORD=${DB_PASSWORD}
DB_HOST=localhost
DB_PORT=5432

# WebPay Transbank (Sandbox)
WEBPAY_COMMERCE_CODE=597055555532
WEBPAY_API_KEY=579B532A7440BB0C9079DED94D31EA1615BACEB56610332264630D42D0A36B1C
WEBPAY_ENVIRONMENT=TEST

# Redis
REDIS_URL=redis://localhost:6379/0

# Email (configurar con tus credenciales)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=tu_email@gmail.com
EMAIL_HOST_PASSWORD=tu_app_password

# Media/Static
MEDIA_URL=/media/
STATIC_URL=/static/
EOF

# Run migrations
log "Ejecutando migraciones..."
python manage.py migrate

# Collect static files
log "Recopilando archivos estáticos..."
python manage.py collectstatic --noinput

# Create superuser
log "Creando superusuario..."
DJANGO_SUPERUSER_PASSWORD=admin123 python manage.py createsuperuser \
    --username admin \
    --email admin@dulcearte.cl \
    --noinput || true

# Seed data
log "Cargando datos de prueba..."
python manage.py seed_data

# Configure Gunicorn service
log "Configurando servicio Gunicorn..."
cp deploy/gunicorn.service /etc/systemd/system/gunicorn.service
systemctl daemon-reload
systemctl enable gunicorn
systemctl start gunicorn

# Configure Nginx
log "Configurando Nginx..."
cp deploy/nginx.conf /etc/nginx/sites-available/dulcearte
ln -sf /etc/nginx/sites-available/dulcearte /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

# Configure firewall
log "Configurando firewall..."
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw --force enable

# Setup log rotation
log "Configurando rotación de logs..."
cat > /etc/logrotate.d/dulcearte <<EOF
/var/log/gunicorn/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 640 www-data www-data
}

/var/log/nginx/dulcearte_*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 640 www-data www-data
}
EOF

# Create systemd service for Celery (if using async tasks)
log "Configurando Celery (opcional)..."
cat > /etc/systemd/system/celery.service <<EOF
[Unit]
Description=Celery Service for Dulce Arte
After=network.target redis.service

[Service]
Type=forking
User=www-data
Group=www-data
WorkingDirectory=${PROJECT_DIR}
Environment="PATH=${PROJECT_DIR}/venv/bin"
ExecStart=${PROJECT_DIR}/venv/bin/celery -A dulcearte worker --loglevel=info --detach
ExecStop=${PROJECT_DIR}/venv/bin/celery -A dulcearte control shutdown
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

cat > /etc/systemd/system/celerybeat.service <<EOF
[Unit]
Description=Celery Beat Service for Dulce Arte
After=network.target redis.service

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=${PROJECT_DIR}
Environment="PATH=${PROJECT_DIR}/venv/bin"
ExecStart=${PROJECT_DIR}/venv/bin/celery -A dulcearte beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable celery celerybeat 2>/dev/null || true

# Final message
echo ""
echo "========================================"
echo -e "${GREEN}¡Instalación completada!${NC}"
echo "========================================"
echo ""
echo "Credenciales importantes:"
echo "  - Django Admin: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)/admin/"
echo "    Usuario: admin"
echo "    Password: admin123"
echo ""
echo "  - Base de datos PostgreSQL:"
echo "    DB: ${DB_NAME}"
echo "    User: ${DB_USER}"
echo "    Password: ${DB_PASSWORD}"
echo ""
echo "  - Archivo .env guardado en: ${PROJECT_DIR}/.env"
echo ""
echo "Próximos pasos:"
echo "  1. Configurar DNS y SSL con: certbot --nginx -d tudominio.cl"
echo "  2. Cambiar contraseña de admin"
echo "  3. Configurar credenciales WebPay de producción"
echo "  4. Configurar email en .env"
echo ""
echo "Logs:"
echo "  - Gunicorn: journalctl -u gunicorn -f"
echo "  - Nginx: tail -f /var/log/nginx/dulcearte_access.log"
echo "  - Django: tail -f /var/log/gunicorn/error.log"
echo ""