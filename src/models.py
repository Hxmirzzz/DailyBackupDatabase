"""
Modelos de datos del sistema
"""
from dataclasses import dataclass
from typing import Optional

@dataclass
class DatabaseConfig:
    """Configuración de una base de datos"""
    name: str
    type: str
    host: str
    port: int
    user: str
    password: str
    enabled: bool = True
    database: Optional[str] = None

    def __post_init__(self):
        """Validación después de inicialización"""
        if not self.name:
            raise ValueError("El nombre de la base de datos es obligatorio")
        if not self.type:
            raise ValueError("El tipo de base de datos es obligatorio")


@dataclass
class BackupSettings:
    """Configuración de backups"""
    retention_days: int = 30
    schedule: list = None
    compress: bool = True
    annual_backup_enabled: bool = True
    annual_backup_date: str = "01-01"  # MM-DD formato
    keep_annual_backups: bool = True

    def __post_init__(self):
        """Validación después de inicialización"""
        if self.retention_days < 1:
            raise ValueError("retention_days debe ser mayor a 0")
        if isinstance(self.schedule, str):
            self.schedule = [self.schedule]
        elif self.schedule is None:
            self.schedule = ["02:00"]
        for time_str in self.schedule:
            if not self._validate_time_format(time_str):
                raise ValueError(f"Formato inválido de horario: {time_str}. Debe ser HH:MM")
        if not self._validate_date_format(self.annual_backup_date):
            raise ValueError("El formato de annual_backup_date debe ser MM-DD")

    @staticmethod
    def _validate_time_format(time_str: str) -> bool:
        """Valida formato de hora HH:MM"""
        try:
            parts = time_str.split(":")
            if len(parts) != 2:
                return False
            hours, minutes = int(parts[0]), int(parts[1])
            return 0 <= hours < 24 and 0 <= minutes < 60
        except (ValueError, AttributeError):
            return False
    
    @staticmethod
    def _validate_date_format(date_str: str) -> bool:
        """Valida formato de fecha MM-DD"""
        try:
            parts = date_str.split("-")
            if len(parts) != 2:
                return False
            month, day = int(parts[0]), int(parts[1])
            return 1 <= month <= 12 and 1 <= day <= 31
        except (ValueError, AttributeError):
            return False


@dataclass
class BackupResult:
    """Resultado de una operación de backup"""
    database_name: str
    success: bool
    output_file: Optional[str] = None
    error: Optional[str] = None
    duration_seconds: float = 0.0

    def __str__(self):
        if self.success:
            return f"✓ {self.database_name}: {self.output_file} ({self.duration_seconds:.2f}s)"
        else:
            return f"✗ {self.database_name}: {self.error}"