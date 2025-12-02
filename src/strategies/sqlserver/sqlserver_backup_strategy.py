import pyodbc
from pathlib import Path
from datetime import datetime

from .schema_generator import SchemaGenerator
from .data_generator import DataGenerator
from .defaults_generator import DefaultConstraintGenerator
from .indexes_generator import IndexGenerator
from .procedures_generator import StoredProcedureGenerator
from .foreign_keys_generator import ForeignKeyGenerator
from .triggers_generator import TriggerGenerator

from .views_generator import ViewGenerator

from ..base_strategy import BackupStrategy
from ...models import DatabaseConfig, BackupResult


class SQLServerBackupStrategy(BackupStrategy):

    def backup(self, db_config: DatabaseConfig, output_file: Path) -> BackupResult:
        try:
            db_name = db_config.database or db_config.name
            script_file = output_file.with_suffix(".sql")

            # Conexión
            conn = self._connect(db_config, db_name)
            if not conn:
                return BackupResult(database_name=db_name, success=False, error="Connection failed")

            try:
                # Encabezado
                with open(script_file, "w", encoding="utf-8") as f:
                    f.write(f"-- BACKUP OF DATABASE: {db_name}\n")
                    f.write(f"-- DATE: {datetime.now()}\n")
                    f.write(f"USE [{db_name}];\nGO\n\n")

                # Crear módulos
                schema = SchemaGenerator(self.logger)
                data = DataGenerator(self.logger)
                defaults = DefaultConstraintGenerator(self.logger)
                indexes = IndexGenerator(self.logger)
                procs = StoredProcedureGenerator(self.logger)
                fks = ForeignKeyGenerator(self.logger)
                triggers = TriggerGenerator(self.logger)
                views = ViewGenerator(self.logger)

                # Ejecutar en orden correcto
                schema.generate(conn, script_file)
                data.generate(conn, script_file)
                defaults.generate(conn, script_file)
                indexes.generate(conn, script_file)
                procs.generate(conn, script_file)
                triggers.generate(conn, script_file)
                views.generate(conn, script_file)
                fks.generate(conn, script_file)

                size_mb = script_file.stat().st_size / (1024 * 1024)
                self.logger.info(f"[BACKUP] Completed {script_file} ({size_mb:.2f} MB)")

                return BackupResult(database_name=db_name, success=True, output_file=str(script_file))

            finally:
                conn.close()

        except Exception as e:
            self.logger.error(f"[BACKUP] ERROR: {e}")
            return BackupResult(database_name=db_name, success=False, error=str(e))

    def _connect(self, db_config: DatabaseConfig, db_name: str):
        try:
            conn_str = (
                f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                f"SERVER={db_config.host};"
                f"DATABASE={db_name};"
                f"UID={db_config.user};"
                f"PWD={db_config.password};"
                f"TrustServerCertificate=yes;"
            )
            self.logger.info(f"[SQLSERVER] Connecting to {db_config.host}")
            return pyodbc.connect(conn_str, timeout=30)
        except Exception as e:
            self.logger.error(f"[SQLSERVER] Connection error: {e}")
            return None
