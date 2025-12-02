"""
Repositorio para manejar configuración (Dependency Inversion)
"""
import json
import os
from pathlib import Path
from typing import Dict, List, Optional
from ..config import Config
from ..logger import LoggerService
from ..models import DatabaseConfig, BackupSettings

class ConfigRepository:
    """Repositorio para manejar configuración"""

    def __init__(self, config_file: Optional[Path] = None):
        """
        Inicializa el repositorio de configuración
        
        Args:
            config_file: Ruta al archivo de configuración (opcional)
        """
        self.config_file = config_file or Config.CONFIG_FILE
        self.logger = LoggerService.get_logger("ConfigRepository")
        self._raw_config = None

    def load(self) -> Dict:
        """
        Carga configuración desde archivo JSON
        
        Returns:
            Diccionario con la configuración
        """
        if not self.config_file.exists():
            self.logger.warning(f"El archivo de configuración no existe: {self.config_file}")
            self._raw_config = Config.DEFAULT_CONFIG
            return self._raw_config

        try:
            with open(self.config_file, "r", encoding='utf-8') as f:
                self._raw_config = json.load(f)
            self.logger.info(f"Configuración cargada exitosamente: {self.config_file}")
            return self._raw_config
        except json.JSONDecodeError as e:
            self.logger.error(f"Error al parsear JSON: {e}")
            self._raw_config = Config.DEFAULT_CONFIG
            return self._raw_config
        except Exception as e:
            self.logger.error(f"Error al cargar la configuración: {str(e)}")
            self._raw_config = Config.DEFAULT_CONFIG
            return self._raw_config

    def save(self, config: Dict) -> bool:
        """
        Guarda configuración en archivo JSON
        
        Args:
            config: Diccionario con la configuración
            
        Returns:
            True si se guardó exitosamente
        """
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, "w", encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            self.logger.info(f"Configuración guardada exitosamente: {self.config_file}")
            return True
        except Exception as e:
            self.logger.error(f"Error al guardar la configuración: {str(e)}")
            return False

    def get_databases(self) -> List[DatabaseConfig]:
        """
        Obtiene lista de configuraciones de bases de datos
        
        Returns:
            Lista de objetos DatabaseConfig
        """
        if self._raw_config is None:
            self.load()

        databases = []
        for db_dict in self._raw_config.get('databases', []):
            try:
                db_config = DatabaseConfig(
                    name=db_dict.get('name', ''),
                    type=db_dict.get('type', 'mysql'),
                    host=db_dict.get('host', 'localhost'),
                    port=db_dict.get('port', 3306),
                    user=self._resolve_credential(db_dict.get('user', '')),
                    password=self._resolve_credential(db_dict.get('password', '')),
                    enabled=db_dict.get('enabled', True),
                    database=db_dict.get('database')  # Para SQL Server
                )
                databases.append(db_config)
            except Exception as e:
                self.logger.error(f"Error al cargar configuración de base de datos: {str(e)}")
        return databases

    def get_backup_settings(self) -> BackupSettings:
        """
        Obtiene configuración de backups
        
        Returns:
            Objeto BackupSettings
        """
        if self._raw_config is None:
            self.load()

        settings_dict = self._raw_config.get('backup_settings', {})
        try:
            return BackupSettings(
                retention_days=settings_dict.get('retention_days', 30),
                schedule=settings_dict.get('schedule', ["02:00"]),
                compress=settings_dict.get('compress', True),
                annual_backup_date=settings_dict.get('annual_backup_date', '01-01'),
                keep_annual_backups=settings_dict.get('keep_annual_backups', True)
            )
        except Exception as e:
            self.logger.error(f"Error al cargar configuración de backups: {str(e)}")
            return BackupSettings()

    def _resolve_credential(self, value: str) -> str:
        """
        Resuelve credencial desde variable de entorno si es necesario
        
        Args:
            value: Valor que puede contener referencia a variable de entorno
            
        Returns:
            Valor resuelto
        """
        if value.startswith("${") and value.endswith("}"):
            env_var = value[2:-1]
            resolved = os.getenv(env_var, "")
            if not resolved:
                self.logger.warning(f"Variable de entorno no encontrada: {env_var}")
            return resolved
        return value

    def create_example_config(self) -> bool:
        """
        Crea un archivo de configuración de ejemplo
        
        Returns:
            True si se creó exitosamente
        """
        return self.save(Config.DEFAULT_CONFIG)