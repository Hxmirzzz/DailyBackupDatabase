"""
Configuración centralizada del sistema de backup
"""
import logging
import os
from pathlib import Path
from dotenv import load_dotenv, find_dotenv

class Config:
    """Configuración centralizada del sistema"""

    ENV_FILE = find_dotenv()

    # Cargar variables de entorno desde la raíz real del proyecto
    load_dotenv(ENV_FILE)

    # BASE_DIR debe ser la raíz donde está main.py
    BASE_DIR = Path(ENV_FILE).parent if ENV_FILE else Path(__file__).resolve().parents[2]

    BACKUP_DIR = Path(os.getenv("BACKUP_DIR")) if os.getenv("BACKUP_DIR") else (BASE_DIR / "Backups")
    LOG_DIR = BASE_DIR / "Logs"
    CONFIG_FILE = BASE_DIR / "config.json"

    # Directorio para backups anuales
    ANNUAL_BACKUP_DIR = BACKUP_DIR / "Annual"

    MAX_BACKUP_DAYS = 30  # Días de retención de backups diarios (aumentado a 30)
    BACKUP_HOUR = "02:00"  # Hora de ejecución del backup diario
    ANNUAL_BACKUP_DAY = "01-01"  # Día del año para backup anual (MM-DD)

    LOG_LEVEL = logging.INFO
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

    SUPPORTED_DB_TYPES = ['mysql', 'mariadb', 'postgresql', 'postgres', 'sqlserver', 'mssql']

    DEFAULT_CONFIG = {
        "databases": [
            {
                "name": "ACCSA2MASTER",
                "type": "sqlserver",
                "host": "VATCOSVR05\\SQLSBCET",
                "port": 1433,
                "user": "${DB_USER}",
                "password": "${DB_PASSWORD}",
                "database": "ACCSA2MASTER",
                "enabled": True
            }
        ],
        "backup_settings": {
            "retention_days": 30,  # Retención de 30 días
            "schedule": "02:00",
            "compress": True,
            "annual_backup_enabled": True,  # Habilitar backups anuales
            "annual_backup_date": "01-01",  # Primer día del año
            "keep_annual_backups": True  # Mantener backups anuales indefinidamente
        }
    }

    @classmethod
    def ensure_directories(cls):
        """Crea los directorios necesarios si no existen"""
        cls.BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        cls.LOG_DIR.mkdir(parents=True, exist_ok=True)
        cls.ANNUAL_BACKUP_DIR.mkdir(parents=True, exist_ok=True)