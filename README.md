# Dulce Arte - Sistema de Trazabilidad y Gestión de Pedidos

**Pastelería Artesanal - Evaluación Parcial N°3 (EVA 3)**

Sistema completo desarrollado con Django 4.2+ / DRF 3.14+ para la gestión integral de una pastelería artesanal, incluyendo trazabilidad de insumos, escalado automático de recetas (BOM) por porciones (12, 20, 40 personas), tablero Kanban de producción, despachos con firma digital y pagos con WebPay Transbank.

---

## Características Principales

### Gestión de Negocio
- **6 Roles de usuario**: Admin, Ventas, Cocinero, Bodega, Repartidor, Cliente
- **Clientes**: CRUD completo, historial de pedidos, preferencias (alergias, sabores favoritos)
- **Productos/Recetas**: Con BOM (Bill of Materials) detallado, costo automático, margen de ganancia
- **Escalado BOM automático**: Calcula ingredientes para 12, 20 o 40 porciones (`scale_factor = target_servings / base_servings`)
- **Validación de stock en tiempo real**: Pre-check antes de confirmar pedidos
- **Consumo automático de stock**: Descuenta insumos escalados al confirmar/producir

### Producción (Kanban)
- **5 columnas**: Recibido → En Preparación → Horneado/Decorado → Control Calidad → Listo
- **Drag & Drop nativo** (vanilla JS, sin librerías externas)
- **Registro de mermas** por tarjeta con motivo
- **Asignación a cocineros** con trazabilidad de movimientos

### Despacho y Logística
- **Rutas programadas** por fecha con conductor asignado
- **Confirmación de entrega** con:
  - Firma digital (HTML5 Canvas)
  - Foto de entrega (input file con `capture="environment"`)
  - GPS automático (Geolocation API)
- **Estados**: Pendiente → En Ruta → Entregado / Fallido

### Pagos (WebPay Transbank)
- **Integración WebPay Plus** (sandbox: commerce_code `597055555532`)
- **Flujo completo**: Crear transacción → Redirección → Callback → Confirmación
- **Estados de pago**: Pendiente → Pagado Parcial (seña 50%) → Pagado Total
- **Conciliación automática** de transacciones

### Reportes y Dashboards
- **8 reportes**: Ventas, Productos, Producción, Stock, Rentabilidad, Clientes, Despachos, Pagos
- **Períodos**: Hoy, Semana, Mes, Año, Personalizado
- **Gráficos** con Chart.js
- **Exportación** a Excel (openpyxl) y PDF (reportlab)

### Portal Cliente
- Historial de pedidos con estado en tiempo real
- Pagos pendientes con botón WebPay
- Catálogo de productos con carrito
- Gestión de perfil y cambio de contraseña

---

## Stack Tecnológico

| Capa | Tecnología |
|------|------------|
| Backend | Django 4.2+, Django REST Framework 3.14+ |
| Base de Datos | PostgreSQL 15+ |
| Autenticación | JWT (djangorestframework-simplejwt) + Session |
| Frontend | Django Templates + Bootstrap 5.3 + Vanilla JS (fetch API) |
| Pagos | Transbank WebPay Plus SDK |
| Servidor | Gunicorn + Nginx (proxy inverso) |
| Despliegue | AWS EC2 (Ubuntu 22.04), Elastic IP |
| Estáticos | WhiteNoise + Nginx |

---

## Estructura del Proyecto

```
dulcearte/
├── core/                    # Configuración Django (settings, urls, wsgi)
├── apps/
│   ├── accounts/           # Usuarios, roles, auth, perfiles, portal cliente
│   ├── clients/            # Clientes, preferencias, historial
│   ├── products/           # Productos, Categorías, BOM, Escalado por porciones
│   ├── ingredients/        # Insumos, Stock, Proveedores, Movimientos, Compras
│   ├── orders/             # Pedidos, Cotizaciones, Items, Pagos
│   ├── production/         # Kanban (Columnas, Tarjetas, Movimientos, Mermas)
│   ├── dispatch/           # Conductores, Rutas, Despachos, Firma/Foto/GPS
│   ├── payments/           # WebPay, Transacciones, Conciliación
│   ├── reports/            # Dashboards, Reportes, Exportación
│   └── frontend/           # Vistas TemplateView, context_processors
├── templates/              # Templates base + por módulo (Bootstrap 5 + Vanilla JS)
├── static/                 # CSS, JS, imágenes
├── media/                  # Archivos subidos (firmas, fotos, productos)
├── deploy/                 # Scripts despliegue EC2
│   ├── setup_ec2.sh        # Provisioning completo EC2
│   ├── gunicorn.service    # Systemd service
│   └── nginx.conf          # Configuración Nginx
├── requirements.txt        # Dependencias Python
├── .env.example            # Variables de entorno ejemplo
└── manage.py
```

---

## Instalación Local

### Prerrequisitos
- Python 3.10+
- PostgreSQL 15+
- Git

### Pasos

```bash
# 1. Clonar repositorio
git clone https://github.com/TU_USUARIO/dulcearte.git
cd dulcearte

# 2. Crear y activar entorno virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# .\venv\Scripts\activate  # Windows

# 3. Instalar dependencias
pip install --upgrade pip
pip install -r requirements.txt

# 4. Configurar PostgreSQL
# Crear BD y usuario:
# sudo -u postgres psql
# CREATE DATABASE dulcearte;
# CREATE USER dulcearte WITH ENCRYPTED PASSWORD 'tu_password';
# GRANT ALL PRIVILEGES ON DATABASE dulcearte TO dulcearte;

# 5. Configurar variables de entorno
cp .env.example .env
# Editar .env con tus credenciales de PostgreSQL

# 6. Ejecutar migraciones
python manage.py migrate

# 7. Crear superusuario (opcional, se crea en seed_data)
python manage.py createsuperuser

# 8. Cargar datos de prueba
python manage.py seed_data

# 9. Recopilar archivos estáticos
python manage.py collectstatic --noinput

# 10. Iniciar servidor
python manage.py runserver
```

### Acceso Local
- **Frontend**: http://127.0.0.1:8000/
- **API**: http://127.0.0.1:8000/api/v1/
- **Admin**: http://127.0.0.1:8000/admin/

### Credenciales Demo (password: `demo123`)
| Rol | Email |
|-----|-------|
| Admin | admin@dulcearte.cl |
| Ventas | ventas1@dulcearte.cl |
| Cocinero | cocinero1@dulcearte.cl |
| Bodega | bodega1@dulcearte.cl |
| Repartidor | repartidor1@dulcearte.cl |
| Cliente | (registrarse en portal) |

---

## Despliegue en AWS EC2

### 1. Crear Instancia EC2
- **AMI**: Ubuntu Server 22.04 LTS
- **Tipo**: t3.micro (Free Tier) o t3.small
- **Security Group**: Puertos 22 (SSH), 80 (HTTP), 443 (HTTPS)
- **Key Pair**: Crear/descargar `.pem`
- **Elastic IP**: Asociar IP elástica fija

### 2. Conectar y Ejecutar Setup
```bash
# Conectar
ssh -i "tu-key.pem" ubuntu@<ELASTIC_IP>

# Clonar repo
git clone https://github.com/TU_USUARIO/dulcearte.git
cd dulcearte

# Ejecutar script de provisioning (como root)
sudo bash deploy/setup_ec2.sh
```

### 3. Qué hace `setup_ec2.sh`
- Actualiza sistema e instala: Python, PostgreSQL, Nginx, Git, Certbot, Redis
- Configura PostgreSQL: BD `dulcearte`, usuario, permisos, timezone `America/Santiago`
- Clona repo, crea venv, instala `requirements.txt`
- Genera `.env` producción con `SECRET_KEY` aleatoria, `DEBUG=False`, `ALLOWED_HOSTS` con IP pública
- Ejecuta `migrate`, `collectstatic`, `createsuperuser` (admin/admin123), `seed_data`
- Configura **Gunicorn** (systemd, 3 workers, unix socket `/run/gunicorn.sock`)
- Configura **Nginx** (proxy inverso, static/media, WebSocket, rate limiting, headers de seguridad)
- Configura **Firewall** (UFW: SSH + Nginx Full)
- Configura **Logrotate** para Gunicorn y Nginx
- Crea services **Celery** y **Celery Beat** (opcional, para tareas asíncronas)

### 4. Post-Instalación
```bash
# Verificar servicios
sudo systemctl status gunicorn nginx

# Ver logs
sudo journalctl -u gunicorn -f
sudo tail -f /var/log/nginx/dulcearte_access.log

# Configurar HTTPS (Let's Encrypt)
sudo certbot --nginx -d tudominio.cl -d www.tudominio.cl

# Cambiar contraseña admin
python manage.py changepassword admin
```

### 5. URLs Producción
- **App**: http://<ELASTIC_IP>/ o https://tudominio.cl/
- **Admin**: http://<ELASTIC_IP>/admin/
- **API**: http://<ELASTIC_IP>/api/v1/

### Credenciales Importantes (guardadas en `/opt/dulcearte/.env`)
```
DB_NAME=dulcearte
DB_USER=dulcearte
DB_PASSWORD=<generada_aleatoriamente>
SECRET_KEY=<generada_aleatoriamente>
WEBPAY_COMMERCE_CODE=597055555532 (sandbox)
WEBPAY_API_KEY=579B532A7440BB0C9079DED94D31EA1615BACEB56610332264630D42D0A36B1C (sandbox)
```

---

## API Endpoints Principales

### Autenticación
```
POST   /api/v1/auth/token/           # Login (JWT)
POST   /api/v1/auth/token/refresh/   # Refresh token
POST   /api/v1/auth/token/verify/    # Verify token
```

### Clientes
```
GET    /api/v1/clients/              # Listar (filtros: search, ordering)
POST   /api/v1/clients/              # Crear
GET    /api/v1/clients/{id}/         # Detalle con historial
PUT    /api/v1/clients/{id}/         # Actualizar
DELETE /api/v1/clients/{id}/         # Eliminar
```

### Productos
```
GET    /api/v1/products/             # Listar
POST   /api/v1/products/             # Crear (con BOM)
GET    /api/v1/products/{id}/        # Detalle
GET    /api/v1/products/{id}/bom-scaled/?servings=20  # Preview BOM escalado
```

### Insumos
```
GET    /api/v1/ingredients/          # Listar con alertas stock
POST   /api/v1/stock-movements/      # Registrar ENTRADA/SALIDA/MERMA/AJUSTE
GET    /api/v1/purchase-orders/      # Órdenes de compra
```

### Pedidos
```
GET    /api/v1/orders/               # Listar (filtros: status, client, date)
POST   /api/v1/orders/               # Crear (estado COTIZACION)
POST   /api/v1/orders/{id}/confirm/  # Confirmar: valida stock, descuenta BOM escalado
GET    /api/v1/orders/{id}/          # Detalle con items y pagos
```

### Producción (Kanban)
```
GET    /api/v1/kanban-columns/       # Columnas ordenadas
GET    /api/v1/production-cards/     # Tarjetas (filtro: column)
POST   /api/v1/production-cards/{id}/move/  # Mover: {to_column_id, notes}
POST   /api/v1/production-cards/{id}/waste/ # Registrar merma
```

### Despachos
```
GET    /api/v1/routes/               # Rutas por fecha
POST   /api/v1/dispatches/{id}/deliver/  # Confirmar: {signature_base64, photo_base64, gps_lat, gps_lng}
```

### Pagos WebPay
```
POST   /api/v1/payments/webpay/create/  # Crear transacción: {order_id, amount, return_url}
GET    /api/v1/payments/webpay/return/  # Callback success (TBK_TOKEN, TBK_ORDEN_COMPRA, TBK_ID_SESION)
POST   /api/v1/payments/webpay/confirm/ # Confirmar transacción
```

### Reportes
```
GET    /api/v1/reports/dashboard/    # KPIs por rol
GET    /api/v1/reports/sales/?period=month
GET    /api/v1/reports/stock-critical/
GET    /api/v1/reports/profitability/
```

---

## Flujos de Trabajo Clave

### 1. Cotización → Pedido → Producción
```
Ventas crea Cotización (con porciones 12/20/40)
    ↓
Cliente acepta → Ventas convierte a Pedido (COTIZACION)
    ↓
Ventas confirma Pedido → Sistema:
    - Valida stock escalado para TODOS los items
    - Descuenta stock (BOM escalado × cantidad)
    - Guarda bom_snapshot_scaled en cada item
    - Cambia estado a CONFIRMADO
    - Crea tarjetas en Kanban (columna RECIBIDO)
```

### 2. Kanban Producción
```
Cocinero ve tablero → Arrastra tarjeta (Drag & Drop)
    ↓
API POST /move/ → Actualiza columna, registra CardMovement
    ↓
En columna CONTROL_CALIDAD → Puede registrar merma
    ↓
En columna LISTO → Disponible para despacho
```

### 3. Despacho con Firma Digital
```
Bodega programa Ruta → Asigna conductor → Agrega despachos (secuencia)
    ↓
Repartidor ve ruta en móvil → Llega a destino
    ↓
Confirma entrega:
    - Firma en Canvas HTML5 → Base64
    - Foto con cámara → Base64
    - GPS automático → lat/lng
    ↓
API POST /deliver/ → Guarda todo, marca ENTREGADO
```

### 4. Pago WebPay
```
Pedido confirmado → Ventas genera pago 50% (seña)
    ↓
POST /webpay/create/ → Retorna form_url + token
    ↓
Frontend redirige a Transbank (sandbox)
    ↓
Usuario paga con tarjeta de prueba
    ↓
Callback GET /webpay/return/ → POST /webpay/confirm/
    ↓
Sistema verifica → Actualiza Payment + WebPayTransaction
    ↓
Estado: PAGADO_PARCIAL → Al entregar: PAGADO_TOTAL (saldo)
```

---

## Variables de Entorno (.env)

| Variable | Descripción | Ejemplo |
|----------|-------------|---------|
| `SECRET_KEY` | Clave secreta Django (64 chars base64) | `openssl rand -base64 64` |
| `DEBUG` | Modo debug | `False` |
| `ALLOWED_HOSTS` | Hosts permitidos (coma-separated) | `tudominio.cl,www.tudominio.cl,1.2.3.4` |
| `DB_ENGINE` | Motor BD | `django.db.backends.postgresql` |
| `DB_NAME` | Nombre BD | `dulcearte` |
| `DB_USER` | Usuario BD | `dulcearte` |
| `DB_PASSWORD` | Password BD | `password_seguro` |
| `DB_HOST` | Host BD | `localhost` |
| `DB_PORT` | Puerto BD | `5432` |
| `WEBPAY_COMMERCE_CODE` | Código comercio Transbank | `597055555532` (sandbox) |
| `WEBPAY_API_KEY` | API Key Transbank | `579B532A...` (sandbox) |
| `WEBPAY_ENVIRONMENT` | `INTEGRATION` o `PRODUCTION` | `INTEGRATION` |
| `EMAIL_HOST` | SMTP host | `smtp.gmail.com` |
| `EMAIL_PORT` | SMTP puerto | `587` |
| `EMAIL_HOST_USER` | Email remitente | `noreply@dulcearte.cl` |
| `EMAIL_HOST_PASSWORD` | App password | `app_password_gmail` |

---

## Testing

```bash
# Ejecutar tests
pytest

# Con cobertura
pytest --cov=apps --cov-report=html

# Tests específicos
pytest apps/orders/tests/ -v
pytest apps/products/tests/test_bom_scaling.py -v
```

---

## Comandos de Gestión

```bash
# Cargar datos demo
python manage.py seed_data

# Limpiar y recargar
python manage.py seed_data --clear

# Crear superusuario
python manage.py createsuperuser

# Cambiar password
python manage.py changepassword <usuario>

# Recopilar estáticos
python manage.py collectstatic --noinput

# Migraciones
python manage.py makemigrations
python manage.py migrate

# Shell Django
python manage.py shell

# Verificar deployment
python manage.py check --deploy
```

---

## Rúbrica EVA 3 - Verificación

| Criterio | Estado | Evidencia |
|----------|--------|-----------|
| Conexión PostgreSQL | ✅ | `settings/base.py` DATABASES config, `setup_ec2.sh` crea BD |
| Django Admin habilitado | ✅ | `urls.py` path('admin/'), admins personalizados por app |
| CRUD completo sobre BD | ✅ | ViewSets + Serializers + Templates para todas las entidades |
| Seguridad/permisos por rol | ✅ | `IsAdmin`, `IsStaffOrReadOnly`, `IsDriverOrStaff`, `IsOwnerOrStaff` |
| Desplegado en AWS EC2 público | ✅ | `deploy/setup_ec2.sh` automatiza todo, Elastic IP |
| README + prompts_ia.md en repo | ✅ | Este archivo + `prompts_ia.md` |
| WebPay integrado | ✅ | `apps/payments/` + sandbox Transbank credenciales |

---

## Licencia

Proyecto académico - Evaluación Parcial N°3 - Desarrollo Backend con Django/DRF

---

## Autor

**Gabriel** - Estudiante Desarrollo Backend
- GitHub: [@TU_USUARIO](https://github.com/TU_USUARIO)
- Proyecto: Dulce Arte - Pastelería Artesanal