"""
Estrategia de backup para SQL Server usando pyodbc
Genera script SQL completo con estructura y datos
Compatible con SQL Server 2008-2022
"""
import pyodbc
from pathlib import Path
from datetime import datetime
from .base_strategy import BackupStrategy
from ..models import DatabaseConfig, BackupResult


class SQLServerBackupStrategy(BackupStrategy):
    """Estrategia de backup para SQL Server usando pyodbc"""
    
    def backup(self, db_config: DatabaseConfig, output_file: Path) -> BackupResult:
        """
        Ejecuta backup de SQL Server generando script SQL completo
        """
        try:
            database_name = db_config.database or db_config.name
            script_file = output_file.with_suffix('.sql')
            
            self.logger.info(f"Generando backup SQL completo de: {database_name}")
            self.logger.info(f"Archivo destino: {script_file}")

            # Validar credenciales
            if not db_config.user or not db_config.password:
                return BackupResult(
                    database_name=db_config.name,
                    success=False,
                    error="Usuario o contraseña no configurados"
                )
            
            if '${' in db_config.user or '${' in db_config.password:
                return BackupResult(
                    database_name=db_config.name,
                    success=False,
                    error="Variables de entorno no resueltas"
                )

            # Crear directorio
            script_file.parent.mkdir(parents=True, exist_ok=True)

            # Conectar
            conn = self._connect(db_config, database_name)
            if not conn:
                return BackupResult(
                    database_name=db_config.name,
                    success=False,
                    error="No se pudo conectar a SQL Server"
                )

            try:
                # Encabezado general
                with open(script_file, 'w', encoding='utf-8') as f:
                    f.write("-- =============================================\n")
                    f.write(f"-- BACKUP DE BASE DE DATOS: {database_name}\n")
                    f.write(f"-- Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"-- Servidor: {db_config.host}\n")
                    f.write("-- =============================================\n\n")
                    f.write("USE [{}];\nGO\n\n".format(database_name))

                # 1. Estructura
                self.logger.info("Paso 1/2: Generando estructura...")
                if not self._generate_schema(conn, database_name, script_file):
                    return BackupResult(database_name=db_config.name, success=False,
                                       error="Error generando estructura")

                # 2. Datos
                self.logger.info("Paso 2/2: Generando datos...")
                if not self._generate_data(conn, database_name, script_file):
                    return BackupResult(database_name=db_config.name, success=False,
                                       error="Error generando datos")

                # 3. Extras
                self.logger.info("Generando constraints y objetos adicionales...")
                self._generate_defaults(conn, script_file)
                self._generate_indexes(conn, script_file)
                self._generate_stored_procedures(conn, script_file)
                self._generate_foreign_keys(conn, script_file)
                self._generate_triggers(conn, script_file)
                
                file_size = script_file.stat().st_size / (1024 * 1024)
                self.logger.info(f"✓ Backup completado: {script_file.name} ({file_size:.2f} MB)")
                
                return BackupResult(database_name=db_config.name, success=True,
                                    output_file=str(script_file))

            finally:
                conn.close()

        except Exception as e:
            self.logger.error(f"Error: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return BackupResult(database_name=db_config.name, success=False, error=str(e))


    def _connect(self, db_config: DatabaseConfig, database_name: str):
        """Conecta a SQL Server"""
        try:
            conn_str = (
                f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                f"SERVER={db_config.host};"
                f"DATABASE={database_name};"
                f"UID={db_config.user};"
                f"PWD={db_config.password};"
                f"TrustServerCertificate=yes;"
            )
            
            self.logger.info(f"Conectando a: {db_config.host}")
            conn = pyodbc.connect(conn_str, timeout=30)
            self.logger.info("✓ Conexión establecida")
            return conn
            
        except pyodbc.Error as e:
            self.logger.error(f"Error de conexión: {e}")
            return None


    def _generate_schema(self, conn, database_name: str, script_file: Path) -> bool:
        """Genera estructura de la BD (compatible SQL 2008+)"""
        try:
            cursor = conn.cursor()

            with open(script_file, 'a', encoding='utf-8') as f:
                f.write("-- =============================================\n")
                f.write("-- ESTRUCTURA DE LA BASE DE DATOS\n")
                f.write("-- =============================================\n\n")

            cursor.execute("""
                SELECT s.name, t.name
                FROM sys.tables t
                INNER JOIN sys.schemas s ON t.schema_id = s.schema_id
                WHERE t.is_ms_shipped = 0
                ORDER BY s.name, t.name
            """)
            
            tables = cursor.fetchall()
            if not tables:
                return True

            self.logger.info(f"  Exportando estructura de {len(tables)} tablas...")

            for i, (schema, table) in enumerate(tables, 1):
                self.logger.info(f"    [{i}/{len(tables)}] {schema}.{table}")

                with open(script_file, 'a', encoding='utf-8') as f:
                    f.write(f"\n-- Tabla: [{schema}].[{table}]\n")
                    f.write(f"IF OBJECT_ID('[{schema}].[{table}]', 'U') IS NOT NULL\n")
                    f.write(f"    DROP TABLE [{schema}].[{table}];\nGO\n\n")

                    # Obtener columnas
                    cursor.execute(f"""
                        SELECT 
                            c.name,
                            TYPE_NAME(c.user_type_id),
                            c.max_length,
                            c.precision,
                            c.scale,
                            c.is_nullable,
                            c.is_identity
                        FROM sys.columns c
                        WHERE c.object_id = OBJECT_ID('[{schema}].[{table}]')
                        ORDER BY c.column_id
                    """)

                    columns = cursor.fetchall()

                    f.write(f"CREATE TABLE [{schema}].[{table}] (\n")

                    for j, col in enumerate(columns):
                        col_name, type_name, max_len, precision, scale, nullable, is_identity = col

                        if type_name in ('varchar', 'char', 'varbinary', 'binary'):
                            type_str = f"{type_name}({max_len if max_len != -1 else 'MAX'})"
                        elif type_name in ('nvarchar', 'nchar'):
                            type_str = f"{type_name}({max_len//2 if max_len != -1 else 'MAX'})"
                        elif type_name in ('decimal', 'numeric'):
                            type_str = f"{type_name}({precision},{scale})"
                        else:
                            type_str = type_name
                        
                        identity_str = " IDENTITY(1,1)" if is_identity else ""
                        null_str = " NULL" if nullable else " NOT NULL"
                        comma = "," if j < len(columns) - 1 else ""

                        f.write(f"    [{col_name}] {type_str}{identity_str}{null_str}{comma}\n")

                    f.write(");\nGO\n\n")

                    # PRIMARY KEY usando FOR XML PATH (compatible con SQL 2008+)
                    cursor.execute(f"""
                        SELECT 
                            i.name,
                            STUFF((
                                SELECT ', ' + c.name
                                FROM sys.index_columns ic2
                                INNER JOIN sys.columns c 
                                    ON ic2.object_id = c.object_id 
                                    AND ic2.column_id = c.column_id
                                WHERE ic2.object_id = i.object_id
                                    AND ic2.index_id = i.index_id
                                ORDER BY ic2.key_ordinal
                                FOR XML PATH(''), TYPE
                            ).value('.', 'NVARCHAR(MAX)'), 1, 2, '') as columns
                        FROM sys.indexes i
                        WHERE i.object_id = OBJECT_ID('[{schema}].[{table}]')
                        AND i.is_primary_key = 1
                    """)

                    pk = cursor.fetchone()
                    if pk and pk[1]:
                        pk_name, cols = pk
                        f.write(
                            f"ALTER TABLE [{schema}].[{table}]\n"
                            f"    ADD CONSTRAINT [{pk_name}] PRIMARY KEY CLUSTERED ({cols});\nGO\n\n"
                        )

            return True
        
        except Exception as e:
            self.logger.error(f"Error en _generate_schema: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False


    def _generate_data(self, conn, database_name: str, script_file: Path) -> bool:
        """Genera datos de todas las tablas"""
        try:
            cursor = conn.cursor()

            with open(script_file, 'a', encoding='utf-8') as f:
                f.write("\n-- =============================================\n")
                f.write("-- DATOS DE LAS TABLAS\n")
                f.write("-- =============================================\n\n")

            cursor.execute("""
                SELECT s.name, t.name
                FROM sys.tables t
                INNER JOIN sys.schemas s ON t.schema_id = s.schema_id
                WHERE t.is_ms_shipped = 0
                ORDER BY s.name, t.name
            """)

            tables = cursor.fetchall()
            if not tables:
                return True

            for i, (schema, table) in enumerate(tables, 1):
                full = f"{schema}.{table}"
                self.logger.info(f"    [{i}/{len(tables)}] {full}")

                cursor.execute(f"SELECT COUNT(*) FROM [{schema}].[{table}]")
                total = cursor.fetchone()[0]

                if total == 0:
                    continue

                cursor.execute(f"""
                    SELECT c.name 
                    FROM sys.columns c
                    WHERE c.object_id = OBJECT_ID('[{schema}].[{table}]')
                    ORDER BY c.column_id
                """)
                col_names = [c[0] for c in cursor.fetchall()]

                cursor.execute(f"""
                    SELECT COUNT(*) 
                    FROM sys.columns 
                    WHERE object_id = OBJECT_ID('[{schema}].[{table}]')
                    AND is_identity = 1
                """)
                has_identity = cursor.fetchone()[0] > 0

                cursor.execute(f"SELECT * FROM [{schema}].[{table}]")
                rows = cursor.fetchall()

                with open(script_file, 'a', encoding='utf-8') as f:
                    f.write(f"\n-- Datos de [{schema}].[{table}] ({total} registros)\n")

                    if has_identity:
                        f.write(f"SET IDENTITY_INSERT [{schema}].[{table}] ON;\n")

                    batch_size = 400

                    for batch_start in range(0, len(rows), batch_size):
                        batch = rows[batch_start:batch_start + batch_size]

                        for row in batch:
                            values = []

                            for v in row:
                                if v is None:
                                    values.append("NULL")
                                elif isinstance(v, str):
                                    values.append("'" + v.replace("'", "''") + "'")
                                elif hasattr(v, "isoformat"):
                                    values.append(f"'{v}'")
                                elif isinstance(v, (bytes, bytearray)):
                                    values.append("0x" + v.hex() if v else "NULL")
                                elif isinstance(v, bool):
                                    values.append("1" if v else "0")
                                else:
                                    values.append(str(v))

                            cols = ", ".join(f"[{c}]" for c in col_names)
                            vals = ", ".join(values)

                            f.write(f"INSERT INTO [{schema}].[{table}] ({cols}) VALUES ({vals});\n")

                        f.write("GO\n")

                    if has_identity:
                        f.write(f"SET IDENTITY_INSERT [{schema}].[{table}] OFF;\n")

                    f.write("\n")

            return True

        except Exception as e:
            self.logger.error(f"Error en _generate_data: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False


    def _generate_defaults(self, conn, script_file: Path):
        """Genera DEFAULT constraints"""
        try:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT 
                    dc.name,
                    s.name,
                    t.name,
                    c.name,
                    dc.definition
                FROM sys.default_constraints dc
                INNER JOIN sys.columns c ON c.default_object_id = dc.object_id
                INNER JOIN sys.tables t ON t.object_id = c.object_id
                INNER JOIN sys.schemas s ON s.schema_id = t.schema_id
            """)

            rows = cursor.fetchall()
            if not rows:
                return True

            with open(script_file, 'a', encoding='utf-8') as f:
                f.write("\n-- =============================================\n")
                f.write("-- DEFAULT CONSTRAINTS\n")
                f.write("-- =============================================\n\n")

                for def_name, schema, table, col, definition in rows:
                    f.write(
                        f"ALTER TABLE [{schema}].[{table}] "
                        f"ADD CONSTRAINT [{def_name}] DEFAULT {definition} FOR [{col}];\nGO\n"
                    )

            return True
        except Exception as e:
            self.logger.warning(f"Error generando DEFAULTs: {e}")
            return False


    def _generate_indexes(self, conn, script_file: Path):
        """Genera índices (compatible SQL 2008+)"""
        try:
            cursor = conn.cursor()

            # Usar FOR XML PATH en lugar de STRING_AGG (compatible con SQL 2008+)
            cursor.execute("""
                SELECT 
                    i.name,
                    s.name,
                    t.name,
                    STUFF((
                        SELECT ', ' + c.name
                        FROM sys.index_columns ic2
                        INNER JOIN sys.columns c 
                            ON c.object_id = ic2.object_id 
                            AND c.column_id = ic2.column_id
                        WHERE ic2.object_id = i.object_id 
                            AND ic2.index_id = i.index_id
                        ORDER BY ic2.key_ordinal
                        FOR XML PATH(''), TYPE
                    ).value('.', 'NVARCHAR(MAX)'), 1, 2, '') as columns
                FROM sys.indexes i
                INNER JOIN sys.tables t ON t.object_id = i.object_id
                INNER JOIN sys.schemas s ON s.schema_id = t.schema_id
                WHERE i.is_primary_key = 0
                AND i.is_unique_constraint = 0
                AND i.index_id > 0
            """)

            rows = cursor.fetchall()
            if not rows:
                return True

            with open(script_file, 'a', encoding='utf-8') as f:
                f.write("\n-- =============================================\n")
                f.write("-- INDICES\n")
                f.write("-- =============================================\n\n")

                for idx_name, schema, table, cols in rows:
                    if cols:  # Solo si tiene columnas
                        f.write(
                            f"CREATE INDEX [{idx_name}] ON "
                            f"[{schema}].[{table}] ({cols});\nGO\n"
                        )

            return True

        except Exception as e:
            self.logger.warning(f"Error generando índices: {e}")
            return False


    def _generate_stored_procedures(self, conn, script_file: Path):
        """Genera procedimientos almacenados"""
        try:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT 
                    s.name,
                    p.name,
                    m.definition
                FROM sys.procedures p
                INNER JOIN sys.schemas s ON s.schema_id = p.schema_id
                INNER JOIN sys.sql_modules m ON m.object_id = p.object_id
                ORDER BY s.name, p.name
            """)

            rows = cursor.fetchall()
            if not rows:
                return True

            with open(script_file, 'a', encoding='utf-8') as f:
                f.write("\n-- =============================================\n")
                f.write("-- STORED PROCEDURES\n")
                f.write("-- =============================================\n\n")

                for schema, name, definition in rows:
                    f.write(f"IF OBJECT_ID('[{schema}].[{name}]', 'P') IS NOT NULL\n")
                    f.write(f"    DROP PROCEDURE [{schema}].[{name}];\nGO\n\n")
                    f.write(definition + "\nGO\n\n")

            return True
        except Exception as e:
            self.logger.warning(f"Error generando procedimientos: {e}")
            return False


    def _generate_foreign_keys(self, conn, script_file: Path):
        """Genera Foreign Keys"""
        try:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT 
                    fk.name,
                    s1.name,
                    t1.name,
                    c1.name,
                    s2.name,
                    t2.name,
                    c2.name
                FROM sys.foreign_keys fk
                INNER JOIN sys.foreign_key_columns fkc
                    ON fkc.constraint_object_id = fk.object_id
                INNER JOIN sys.tables t1 
                    ON t1.object_id = fkc.parent_object_id
                INNER JOIN sys.schemas s1 
                    ON s1.schema_id = t1.schema_id
                INNER JOIN sys.columns c1 
                    ON c1.column_id = fkc.parent_column_id
                    AND c1.object_id = t1.object_id
                INNER JOIN sys.tables t2 
                    ON t2.object_id = fkc.referenced_object_id
                INNER JOIN sys.schemas s2 
                    ON s2.schema_id = t2.schema_id
                INNER JOIN sys.columns c2 
                    ON c2.column_id = fkc.referenced_column_id
                    AND c2.object_id = t2.object_id
                ORDER BY fk.name, fkc.constraint_column_id
            """)

            rows = cursor.fetchall()
            if not rows:
                return True

            # Reagrupar por constraint
            fk_map = {}
            for fk_name, schema, table, col, ref_s, ref_t, ref_c in rows:
                key = (fk_name, schema, table, ref_s, ref_t)
                fk_map.setdefault(key, []).append((col, ref_c))

            with open(script_file, 'a', encoding='utf-8') as f:
                f.write("\n-- =============================================\n")
                f.write("-- FOREIGN KEYS\n")
                f.write("-- =============================================\n\n")

                for (fk_name, schema, table, ref_s, ref_t), cols in fk_map.items():
                    parent_cols = ", ".join(f"[{c}]" for c, _ in cols)
                    ref_cols = ", ".join(f"[{c}]" for _, c in cols)

                    f.write(
                        f"ALTER TABLE [{schema}].[{table}] WITH CHECK "
                        f"ADD CONSTRAINT [{fk_name}] FOREIGN KEY ({parent_cols}) "
                        f"REFERENCES [{ref_s}].[{ref_t}] ({ref_cols});\nGO\n"
                    )

            return True

        except Exception as e:
            self.logger.warning(f"Error generando FKs: {e}")
            return False


    def _generate_triggers(self, conn, script_file: Path):
        """Genera triggers"""
        try:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT 
                    s.name,
                    t.name,
                    tr.name,
                    m.definition
                FROM sys.triggers tr
                INNER JOIN sys.tables t ON t.object_id = tr.parent_id
                INNER JOIN sys.schemas s ON s.schema_id = t.schema_id
                INNER JOIN sys.sql_modules m ON m.object_id = tr.object_id
                WHERE tr.is_ms_shipped = 0
                AND tr.parent_class = 1
                ORDER BY s.name, t.name, tr.name
            """)

            rows = cursor.fetchall()
            if not rows:
                return True

            with open(script_file, "a", encoding="utf-8") as f:
                f.write("\n-- =============================================\n")
                f.write("-- TRIGGERS\n")
                f.write("-- =============================================\n\n")

                for schema, table, trigger, definition in rows:
                    f.write(f"IF OBJECT_ID('[{schema}].[{trigger}]', 'TR') IS NOT NULL\n")
                    f.write(f"    DROP TRIGGER [{schema}].[{trigger}];\nGO\n\n")
                    f.write(definition + "\nGO\n\n")

            return True

        except Exception as e:
            self.logger.warning(f"Error generando TRIGGERS: {e}")
            return False