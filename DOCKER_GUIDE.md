# TRADINGÍA DOCKER SETUP GUIDE
# ============================

## 🚀 QUICK START

### Paso 1: Clonar y preparar
```bash
git clone https://github.com/mayorGonzalez/tradingIA.git
cd tradingIA
cp .env.docker .env
# Edita .env con tus credenciales (opcional para DEBUG_MODE=true)
```

### Paso 2: Levantar servicios
```bash
# Con Makefile (recomendado)
make up

# O con docker-compose directo
docker-compose up -d
```

### Paso 3: Verificar estado
```bash
make health
```

### Paso 4: Acceder al Dashboard
```
http://localhost:8501
```

---

## 📋 SERVICIOS

| Servicio | Puerto | URL | Descripción |
|----------|--------|-----|------------|
| **Streamlit Dashboard** | 8501 | http://localhost:8501 | UI principal del bot |
| **Ollama LLM** | 11434 | http://localhost:11434/api/tags | Motor de IA local |
| **PostgreSQL** | 5432 | localhost | Base de datos (trades, signals) |

---

## 🛠️ COMANDOS ÚTILES

### Logs
```bash
make logs              # Ver todos los logs
make logs-app         # Solo de la app
make logs-ollama      # Solo de Ollama
```

### Shell interactivo
```bash
make shell            # Bash en trading_app
make shell-db         # psql en PostgreSQL
```

### Modelos Ollama
```bash
make pull-model                # Descargar qwen2.5-coder:3b
make pull-model-mistral        # O descargar Mistral
make list-models               # Listar modelos instalados
```

### Control
```bash
make restart          # Reiniciar servicios
make down             # Parar sin eliminar volúmenes
make clean            # Eliminar TODO (contenedores + volúmenes)
```

---

## 🔧 CONFIGURACIÓN

### Cambiar modelo Ollama
1. Edita `.env`:
   ```
   LLM_MODEL=mistral
   # o
   LLM_MODEL=neural-chat
   ```

2. Reinicia:
   ```bash
   make down
   make up
   make pull-model
   ```

### Usar Gemini en lugar de Ollama
1. Edita `.env`:
   ```
   LLM_PROVIDER=gemini
   GEMINI_API_KEY=tu_clave_aqui
   ```

2. Reinicia: `make restart`

### Conectar a Exchange real (Binance)
1. Edita `.env`:
   ```
   BINANCE_API_KEY=tu_api_key
   BINANCE_SECRET=tu_secret
   DEBUG_MODE=false
   ```

2. Reinicia: `make down && make up`

---

## 📊 BASE DE DATOS

### Conectar a PostgreSQL
```bash
make shell-db

# Dentro de psql:
SELECT * FROM trading.trades;
SELECT * FROM trading.open_positions;
SELECT * FROM trading.daily_pnl;
```

### Ver estado
```bash
docker-compose exec postgres pg_dump -U trading_user -d tradingía_db > backup.sql
```

---

## 🐛 TROUBLESHOOTING

### ❌ "Connection refused" en Ollama
```bash
make logs-ollama
# Espera a que descargue el modelo (~3-5 min)
```

### ❌ Dashboard no carga
```bash
make logs-app
# Busca errores en imports
```

### ❌ Database locked
```bash
make clean  # Nuclear option
make up     # Vuelve a levantar
```

### ❌ Fuera de espacio
```bash
docker system prune -a  # Limpia imágenes no usadas
```

---

## 💾 VOLUMES PERSISTENTES

Los datos se guardan en:
- **postgres_data**: Base de datos de trades
- **ollama_data**: Modelos descargados
- **trading_cache**: Cache de Python/pip

Para verlos:
```bash
docker volume ls | grep trading
```

---

## 🌐 NETWORKING

Todos los servicios están en la red `trading_network`:
- La app accede a Ollama como `http://ollama:11434`
- La app accede a PostgreSQL como `postgres:5432`
- Desde el host:
  - PostgreSQL: `localhost:5432`
  - Ollama: `localhost:11434`
  - Streamlit: `localhost:8501`

---

## 📈 MONITORING

### Ver recursos consumidos
```bash
docker stats
```

### Health check de servicios
```bash
make health
```

### Ver eventos de Docker
```bash
docker events --filter type=container
```

---

## 🔐 SEGURIDAD EN PRODUCCIÓN

### Cambiar contraseña PostgreSQL
Edita `docker-compose.yml` ANTES de levantar:
```yaml
environment:
  POSTGRES_PASSWORD: ${DB_PASSWORD:-tu_contrasena_segura}
```

### Usar secretos de Docker (Swarm)
```bash
echo "tu_api_key" | docker secret create NANSEN_API_KEY -
```

### Exponerse a internet (PELIGROSO)
No expongas directamente. Usa:
- Nginx reverse proxy
- Cloudflare tunel
- Wireguard VPN

---

## 📝 NEXT STEPS

1. ✅ Copia Dockerfile, docker-compose.yml, .env.docker, Makefile al repo
2. ✅ Copia scripts/init_db.sql
3. ✅ Haz los fixes de código que te indiqué
4. ✅ Ejecuta `make up`
5. ✅ Accede a http://localhost:8501
6. ✅ Haz push a GitHub