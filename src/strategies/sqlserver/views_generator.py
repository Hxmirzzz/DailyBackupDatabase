import pyodbc
from pathlib import Path

class ViewGenerator:
    def __init__(self, logger):
        self.logger = logger

    def generate(self, conn, script_file: Path):
        """Genera todas las VIEWS de la base de datos"""
        try:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT 
                    s.name AS schema_name,
                    v.name AS view_name,
                    m.definition
                FROM sys.views v
                INNER JOIN sys.schemas s ON s.schema_id = v.schema_id
                INNER JOIN sys.sql_modules m ON m.object_id = v.object_id
                ORDER BY s.name, v.name
            """)

            rows = cursor.fetchall()
            if not rows:
                self.logger.info("No se encontraron VIEWS.")
                return True

            with open(script_file, "a", encoding="utf-8") as f:
                f.write("\n-- =============================================\n")
                f.write("-- VIEWS\n")
                f.write("-- =============================================\n\n")

                for schema, view, definition in rows:
                    f.write(
                        f"IF OBJECT_ID('[{schema}].[{view}]', 'V') IS NOT NULL\n"
                        f"    DROP VIEW [{schema}].[{view}];\nGO\n\n"
                    )
                    f.write(definition + "\nGO\n\n")

            self.logger.info(f"✓ Exportadas {len(rows)} views")

            return True

        except Exception as e:
            self.logger.error(f"Error generando views: {e}")
            return False