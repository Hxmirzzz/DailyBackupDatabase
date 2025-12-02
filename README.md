# 🗄️ QuantumDB — Automatic SQL Server Backup Engine

Sistema profesional de backup automático para bases de datos SQL Server, que genera scripts SQL completos con estructura, datos y objetos del esquema.
Diseñado con principios SOLID, arquitectura limpia y fácil extensión.

## ✨ Características Principales

✅ Generación de scripts SQL completos (DDL + INSERTS)

✅ Incluye:
- Tablas
- Datos
- PKs y constraints
- Defaults
- Índices
- Foreign Keys
- Stored Procedures
- Triggers

✅ Backups diarios automáticos (retención 30 días)
✅ Backups anuales permanentes (cada 1 de enero)
✅ Logs detallados con resumen por tabla/objeto
✅ Limpieza automática de históricos
✅ Variables de entorno seguras
✅ Arquitectura SOLID modular y extensible
✅ Seguro para GitHub (sin credenciales expuestas)

## 🏗️ Arquitectura

### Principios SOLID Aplicados
- Single Responsibility
- Open/Closed
- Liskov Substitution
- Interface Segregation
- Dependency Inversion

### Estructura del Proyecto

```
DailyBackupDatabase/
│
├── src/
│   ├── config.py
│   ├── logger.py
│   ├── models.py
│   │
│   ├── repositories/
│   ├── strategies/
│   ├── services/
│   └── factories/
│
├── scripts/
├── tests/
├── main.py
├── requirements.txt
├── Makefile
└── README.md
```

## 🔥 IMPORTANTE — Usar Entorno Virtual (venv)

Este proyecto requiere un entorno virtual para asegurar:
- ✔ Estabilidad
- ✔ Reproducibilidad
- ✔ No conflictos con librerías del sistema
- ✔ Funcionamiento correcto en servidores y GitHub

### Crear el entorno virtual

**Windows**
```bash
python -m venv venv
venv\Scripts\activate
```

**Linux/Mac**
```bash
python3 -m venv venv
source venv/bin/activate
```

### Instalar dependencias
```bash
pip install -r requirements.txt
```

### Guardar dependencias exactas
```bash
pip freeze > requirements.txt
```

### Ignorar venv en Git
`.gitignore` debe incluir:
```
venv/
```

## 🚀 Instalación Rápida

```bash
git clone https://github.com/Hxmirzzz/DailyBackupDatabase.git
cd DailyBackupDatabase

python -m venv venv
venv\Scripts\activate    # Windows
# source venv/bin/activate   # Linux/Mac

pip install -r requirements.txt

python main.py --init
cp .env.example .env
```

## ⚙️ Configuración

### 1. Archivo .env
```
MSSQL_USER=tu_usuario
MSSQL_PASSWORD=tu_password
```

### 2. Archivo config.json
```json
{
  "databases": [
    {
      "name": "MiBase",
      "type": "sqlserver",
      "host": "localhost",
      "port": 1433,
      "user": "${MSSQL_USER}",
      "password": "${MSSQL_PASSWORD}",
      "enabled": true
    }
  ],
  "backup_settings": {
    "daily_retention_days": 30,
    "schedule": "02:00",
    "compress": false
  }
}
```

## 🎯 Uso

### Modo automático (scheduler)
```bash
python main.py
```

### Ejecutar un backup manual
```bash
python main.py once
```

### Backup de una DB específica
```bash
python main.py --db MiBase
```

### Ver estadísticas
```bash
python main.py --stats
```

### Ejecutar backup inmediato
```bash
python main.py --now
```

# Ver ayuda
python main.py --help
```

### Usando Make

```bash
make install    # Instalar dependencias
make init       # Crear archivos de configuración
make test       # Ejecutar tests
make run        # Ejecutar en modo scheduler
make run-once   # Ejecutar backup una vez
make stats      # Ver estadísticas
make clean      # Limpiar archivos temporales
```

## 🖥️ Instalación como Servicio

### Windows (NSSM - Recomendado)

```bash
# 1. Descargar NSSM desde https://nssm.cc/download

# 2. Ejecutar el instalador (como administrador)
scripts\install_windows_service.bat

# Comandos útiles
nssm start DBBackupService
nssm stop DBBackupService
nssm status DBBackupService
nssm edit DBBackupService
nssm remove DBBackupService
```

### Windows (Task Scheduler)

1. Abrir "Programador de tareas"
2. Crear tarea básica
3. Disparador: "Al iniciar el sistema"
4. Acción: Ejecutar `start_backup.bat`
5. Configurar para ejecutar con privilegios

### Linux (systemd)

```bash
# Ejecutar script de instalación
sudo bash scripts/install_linux_service.sh

# Comandos útiles
sudo systemctl start db-backup
sudo systemctl stop db-backup
sudo systemctl status db-backup
sudo systemctl enable db-backup   # Habilitar inicio automático
sudo systemctl disable db-backup  # Deshabilitar inicio automático
journalctl -u db-backup -f        # Ver logs en tiempo real
```

## 🔒 Seguridad de Credenciales

### Crear Usuario de Backup en MySQL

```sql
-- Crear usuario específico para backups
CREATE USER 'backup_user'@'localhost' IDENTIFIED BY 'password_seguro_aqui';

-- Otorgar permisos necesarios (solo lectura)
GRANT SELECT, LOCK TABLES, SHOW VIEW, EVENT, TRIGGER 
ON *.* TO 'backup_user'@'localhost';

-- Aplicar cambios
FLUSH PRIVILEGES;
```

### Crear Usuario de Backup en PostgreSQL

```sql
-- Crear usuario
CREATE USER backup_user WITH PASSWORD 'password_seguro_aqui';

-- Otorgar permisos
GRANT CONNECT ON DATABASE mi_base_datos TO backup_user;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO backup_user;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO backup_user;

-- Para futuras tablas
ALTER DEFAULT PRIVILEGES IN SCHEMA public 
GRANT SELECT ON TABLES TO backup_user;
```

### Crear Usuario de Backup en SQL Server

```sql
-- Crear login
CREATE LOGIN backup_user WITH PASSWORD = 'password_seguro_aqui';

-- Crear usuario en la base de datos
USE mi_base_datos;
CREATE USER backup_user FOR LOGIN backup_user;

-- Otorgar permisos
GRANT BACKUP DATABASE TO backup_user;
GRANT BACKUP LOG TO backup_user;
GRANT VIEW DEFINITION TO backup_user;
```

## 📊 Logs y Monitoreo

Los logs se generan automáticamente en el directorio `logs/`:

```
logs/
├── BackupService_20241127.log
├── ConfigRepository_20241127.log
├── CleanupService_20241127.log
└── SchedulerService_20241127.log
```

### Ver Logs en Tiempo Real

```bash
# Linux
tail -f logs/BackupService_*.log

# Windows PowerShell
Get-Content logs\BackupService_*.log -Wait -Tail 50
```

## 🧪 Tests

```bash
# Ejecutar todos los tests
python -m pytest tests/ -v

# Con cobertura
python -m pytest tests/ -v --cov=src --cov-report=html
```

## � Roadmap

- Compresión GZIP
- Backups cifrados
- Dashboard Web
- API REST
- Exportar VIEWS y FUNCTIONS (opcional)
- Exportar SEQUENCES (para PostgreSQL)

## 👤 Autor

**Hamir David Rocha Causaya**
- GitHub: [https://github.com/Hxmirzzz](https://github.com/Hxmirzzz)
- LinkedIn: [https://www.linkedin.com/in/hamir01/](https://www.linkedin.com/in/hamir01/)

⭐ Si este proyecto te fue útil, ¡considera darle una estrella en GitHub!
