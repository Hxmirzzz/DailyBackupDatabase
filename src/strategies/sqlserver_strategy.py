"""
Estrategia de backup para SQL Server
"""
import subprocess
from pathlib import Path
from .base_strategy import BackupStrategy
from ..models import DatabaseConfig, BackupResult


class SQLServerBackupStrategy(BackupStrategy):
    """Estrategia de backup para SQL Server"""
    
    def backup(self, db_config: DatabaseConfig, output_file: Path) -> BackupResult:
        """
        Ejecuta backup de SQL Server
        
        Args:
            db_config: Configuración de la base de datos
            output_file: Archivo de salida para el backup
            
        Returns:
            Resultado del backup
        """
        # Validar herramientas - sqlcmd debe estar instalado
        tool_error = self._validate_tools(['sqlcmd'])
        if tool_error:
            return BackupResult(
                database_name=db_config.name,
                success=False,
                error=tool_error
            )
        
        try:
            # Determinar el nombre de la base de datos
            database_name = db_config.database or db_config.name
            
            # Generar archivo .bak
            script_file = output_file.with_suffix('.sql')
            
            self.logger.info(f"Ejecutando backup de SQL Server: {database_name}")

            bak_success = self._create_bak_backup(db_config, database_name)

            if not bak_success:
                return BackupResult(
                    database_name=db_config.name,
                    success=False,
                    error="Error al crear backup .bak"
                )

            sql_success = self._generate_sql_script(db_config, database_name, script_file)

            if sql_success:
                self.logger.info(f"✓ Script .sql creado: {script_file.name}")
            else:
                self.logger.warning(f"⚠ El .sql falló, pero el backup .bak se creó en la ruta por defecto.")

            return BackupResult(
                database_name=db_config.name,
                success=sql_success,
                output_file=script_file.name
            )

        except subprocess.TimeoutExpired:
            return BackupResult(
                database_name=db_config.name,
                success=False,
                error="Timeout: El backup tardó más de 1 hora"
            )
        except Exception as e:
            if 'script_file' in locals() and script_file.exists():
                script_file.unlink()

            return BackupResult(
                database_name=db_config.name,
                success=False,
                error=str(e)
            )

    def _create_bak_backup(self, db_config: DatabaseConfig, database_name: str) -> bool:
        """
        Crea el archivo .bak en la ubicación POR DEFECTO de SQL Server.

        NO se usa 'backup_file', porque SQL Server decidirá la ruta.
        """
        try:
            sql_query = f"""
            BACKUP DATABASE [{database_name}]
            TO DISK = N''
            WITH FORMAT,
                INIT,
                NAME = N'{database_name}-Full Database Backup',
                SKIP,
                COMPRESSION,
                STATS = 10;
            """

            cmd = [
                'sqlcmd',
                '-S', self._get_server_string(db_config),
                '-U', db_config.user,
                '-P', db_config.password,
                '-Q', sql_query
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)

            if result.returncode == 0:
                self.logger.info("✓ Backup .bak generado en la ruta por defecto de SQL Server.")
                return True
            else:
                self.logger.error(f"Error en backup .bak: {result.stderr or result.stdout}")
                return False

        except Exception as e:
            self.logger.error(f"Excepción al crear backup .bak: {e}")
            return False
    
    def _generate_sql_script(self, db_config: DatabaseConfig, database_name: str, script_file: Path) -> bool:
        """
        Genera script SQL con la estructura completa de la BD
        
        Args:
            db_config: Configuración de la BD
            database_name: Nombre de la base de datos
            script_file: Ruta del archivo .sql
            
        Returns:
            True si fue exitoso
        """
        try:
            self.logger.info(f"Generando script SQL de estructura...")
            
            # Script SQL que genera DDL de tablas, índices, vistas, etc.
            sql_query = f"""
                SET NOCOUNT ON;

                PRINT '-- ============================================';
                PRINT '-- Database: {database_name}';
                PRINT '-- Generated: ' + CONVERT(VARCHAR, GETDATE(), 120);
                PRINT '-- ============================================';
                PRINT '';

                USE [{database_name}];
                GO

                -- ============================================
                -- TABLAS
                -- ============================================
                DECLARE @TableName NVARCHAR(128);
                DECLARE @SchemaName NVARCHAR(128);
                DECLARE @SQL NVARCHAR(MAX);

                DECLARE table_cursor CURSOR FOR
                SELECT SCHEMA_NAME(t.schema_id), t.name
                FROM sys.tables t
                WHERE t.is_ms_shipped = 0
                ORDER BY SCHEMA_NAME(t.schema_id), t.name;

                OPEN table_cursor;
                FETCH NEXT FROM table_cursor INTO @SchemaName, @TableName;

                WHILE @@FETCH_STATUS = 0
                BEGIN
                    PRINT '';
                    PRINT '-- Tabla: [' + @SchemaName + '].[' + @TableName + ']';
                    PRINT 'IF OBJECT_ID(''[' + @SchemaName + '].[' + @TableName + ']'', ''U'') IS NOT NULL';
                    PRINT '    DROP TABLE [' + @SchemaName + '].[' + @TableName + '];';
                    PRINT 'GO';
                    
                    SET @SQL = 'CREATE TABLE [' + @SchemaName + '].[' + @TableName + '] (';
                    
                    SELECT @SQL = @SQL + CHAR(13) + '    [' + c.name + '] ' + 
                        TYPE_NAME(c.user_type_id) +
                        CASE 
                            WHEN c.max_length = -1 THEN '(MAX)'
                            WHEN TYPE_NAME(c.user_type_id) IN ('varchar', 'char', 'varbinary', 'binary') 
                            THEN '(' + CAST(c.max_length AS VARCHAR) + ')'
                            WHEN TYPE_NAME(c.user_type_id) IN ('nvarchar', 'nchar') 
                            THEN '(' + CAST(c.max_length/2 AS VARCHAR) + ')'
                            WHEN TYPE_NAME(c.user_type_id) IN ('decimal', 'numeric')
                            THEN '(' + CAST(c.precision AS VARCHAR) + ',' + CAST(c.scale AS VARCHAR) + ')'
                            ELSE ''
                        END +
                        CASE WHEN c.is_identity = 1 THEN ' IDENTITY(' + CAST(IDENT_SEED(@SchemaName + '.' + @TableName) AS VARCHAR) + ',' + CAST(IDENT_INCR(@SchemaName + '.' + @TableName) AS VARCHAR) + ')' ELSE '' END +
                        CASE WHEN c.is_nullable = 0 THEN ' NOT NULL' ELSE ' NULL' END +
                        CASE WHEN c.column_id < (SELECT MAX(column_id) FROM sys.columns WHERE object_id = c.object_id) THEN ',' ELSE '' END
                    FROM sys.columns c
                    WHERE c.object_id = OBJECT_ID('[' + @SchemaName + '].[' + @TableName + ']')
                    ORDER BY c.column_id;
                    
                    SET @SQL = @SQL + CHAR(13) + ');';
                    
                    PRINT @SQL;
                    PRINT 'GO';
                    
                    FETCH NEXT FROM table_cursor INTO @SchemaName, @TableName;
                END;

                CLOSE table_cursor;
                DEALLOCATE table_cursor;

                -- ============================================
                -- PRIMARY KEYS
                -- ============================================
                PRINT '';
                PRINT '-- ============================================';
                PRINT '-- PRIMARY KEYS';
                PRINT '-- ============================================';

                SELECT 'ALTER TABLE [' + SCHEMA_NAME(t.schema_id) + '].[' + t.name + '] 
                    ADD CONSTRAINT [' + i.name + '] PRIMARY KEY ' + 
                    CASE WHEN i.type = 1 THEN 'CLUSTERED' ELSE 'NONCLUSTERED' END + ' (' +
                    STUFF((SELECT ', [' + c.name + ']' + CASE WHEN ic.is_descending_key = 1 THEN ' DESC' ELSE ' ASC' END
                        FROM sys.index_columns ic
                        INNER JOIN sys.columns c ON ic.object_id = c.object_id AND ic.column_id = c.column_id
                        WHERE ic.object_id = i.object_id AND ic.index_id = i.index_id
                        ORDER BY ic.key_ordinal
                        FOR XML PATH('')), 1, 2, '') + ');
                GO'
                FROM sys.indexes i
                INNER JOIN sys.tables t ON i.object_id = t.object_id
                WHERE i.is_primary_key = 1 AND t.is_ms_shipped = 0;

                -- ============================================
                -- ÍNDICES
                -- ============================================
                PRINT '';
                PRINT '-- ============================================';
                PRINT '-- ÍNDICES';
                PRINT '-- ============================================';

                SELECT 'CREATE ' + 
                    CASE WHEN i.is_unique = 1 THEN 'UNIQUE ' ELSE '' END +
                    CASE WHEN i.type = 1 THEN 'CLUSTERED' WHEN i.type = 2 THEN 'NONCLUSTERED' ELSE '' END + 
                    ' INDEX [' + i.name + '] ON [' + SCHEMA_NAME(t.schema_id) + '].[' + t.name + '] (' +
                    STUFF((SELECT ', [' + c.name + ']' + CASE WHEN ic.is_descending_key = 1 THEN ' DESC' ELSE ' ASC' END
                        FROM sys.index_columns ic
                        INNER JOIN sys.columns c ON ic.object_id = c.object_id AND ic.column_id = c.column_id
                        WHERE ic.object_id = i.object_id AND ic.index_id = i.index_id
                        ORDER BY ic.key_ordinal
                        FOR XML PATH('')), 1, 2, '') + ');
                GO'
                FROM sys.indexes i
                INNER JOIN sys.tables t ON i.object_id = t.object_id
                WHERE i.is_primary_key = 0 AND i.type IN (1,2) AND t.is_ms_shipped = 0;

                PRINT '';
                PRINT '-- Script generado exitosamente';
                """
            
            cmd = [
                'sqlcmd',
                '-S', self._get_server_string(db_config),
                '-U', db_config.user,
                '-P', db_config.password,
                '-d', database_name,
                '-Q', sql_query,
                '-o', str(script_file),
                '-y', '0'  # Sin límite de ancho
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            
            if result.returncode == 0 and script_file.exists():
                # Verificar que el archivo tenga contenido
                if script_file.stat().st_size > 100:
                    return True
                else:
                    self.logger.warning("Script SQL generado pero está casi vacío")
                    return False
            else:
                self.logger.warning(f"No se pudo generar script SQL: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.warning(f"Error al generar script SQL: {e}")
            return False
    
    def _get_server_string(self, db_config):
        """
        Genera el string de conexión al servidor
        
        Args:
            db_config: Configuración de la BD
            
        Returns:
            String de servidor (ej: "192.168.1.16,1433")
        """
        if db_config.port and db_config.port != 1433:
            return f"{db_config.host},{db_config.port}"
        return db_config.host