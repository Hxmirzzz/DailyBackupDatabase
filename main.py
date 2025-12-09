#!/usr/bin/env python3
"""
Sistema de Backup Automático de Bases de Datos
Punto de entrada principal

Uso:
    python main.py                  # Modo scheduler (automático)
    python main.py once             # Ejecutar backup una vez
    python main.py --db nombre_db   # Backup de una BD específica
    python main.py --help           # Ayuda
"""
import sys
import argparse
from pathlib import Path

# Agregar directorio src al path
sys.path.insert(0, str(Path(__file__).parent))

from src.config import Config
from src.logger import LoggerService
from src.repositories.config_repository import ConfigRepository
from src.services.backup_service import BackupService
from src.services.scheduler_service import SchedulerService


def parse_arguments():
    """
    Parsea argumentos de línea de comandos
    
    Returns:
        Namespace con los argumentos parseados
    """
    parser = argparse.ArgumentParser(
        description='Sistema de Backup Automático de Bases de Datos',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python main.py                    # Iniciar servicio automático
  python main.py once               # Ejecutar backup una sola vez
  python main.py --db mi_db         # Backup de una base específica
  python main.py --stats            # Ver estadísticas de backups
  python main.py --init             # Crear archivos de configuración
        """
    )
    
    parser.add_argument(
        'mode',
        nargs='?',
        choices=['once', 'scheduler'],
        default='scheduler',
        help='Modo de ejecución (default: scheduler)'
    )
    
    parser.add_argument(
        '--db',
        type=str,
        metavar='NOMBRE',
        help='Realizar backup de una base de datos específica'
    )
    
    parser.add_argument(
        '--stats',
        action='store_true',
        help='Mostrar estadísticas de backups'
    )
    
    parser.add_argument(
        '--init',
        action='store_true',
        help='Crear archivos de configuración de ejemplo'
    )
    
    parser.add_argument(
        '--now',
        action='store_true',
        help='Ejecutar backup inmediatamente al iniciar scheduler'
    )
    
    return parser.parse_args()


def initialize_config():
    """
    Inicializa archivos de configuración si no existen
    
    Returns:
        True si se inicializó correctamente
    """
    logger = LoggerService.get_logger("Init")
    config_repo = ConfigRepository()
    
    created_files = []
    
    # Crear config.json si no existe
    if not Config.CONFIG_FILE.exists():
        if config_repo.create_example_config():
            created_files.append(str(Config.CONFIG_FILE))
            logger.info(f"Creado: {Config.CONFIG_FILE}")
    
    # Crear .env.example si no existe
    env_example = Config.BASE_DIR / ".env.example"
    if not env_example.exists():
        env_content = """# Variables de entorno para credenciales
# Copia este archivo como .env y completa con tus credenciales

# MySQL/MariaDB
DB_USER=backup_user
DB_PASSWORD=tu_password_seguro

# PostgreSQL
PG_USER=postgres_user
PG_PASSWORD=otro_password

# SQL Server
MSSQL_USER=sa
MSSQL_PASSWORD=password_sqlserver
"""
        try:
            with open(env_example, 'w', encoding='utf-8') as f:
                f.write(env_content)
            created_files.append(str(env_example))
            logger.info(f"Creado: {env_example}")
        except Exception as e:
            logger.error(f"Error creando .env.example: {e}")
    
    if created_files:
        logger.info("=" * 70)
        logger.info("ARCHIVOS DE CONFIGURACIÓN CREADOS")
        logger.info("=" * 70)
        for file in created_files:
            logger.info(f"  - {file}")
        logger.info("")
        logger.info("IMPORTANTE:")
        logger.info("1. Copia .env.example como .env")
        logger.info("2. Edita .env con tus credenciales")
        logger.info("3. Edita config.json con tu configuración de bases de datos")
        logger.info("4. Ejecuta nuevamente este script")
        logger.info("=" * 70)
        return True
    
    return False


def show_statistics(backup_service: BackupService):
    """
    Muestra estadísticas de backups
    
    Args:
        backup_service: Servicio de backup
    """
    logger = LoggerService.get_logger("Stats")
    stats = backup_service.cleanup_service.get_backup_stats(Config.BACKUP_DIR)
    
    logger.info("=" * 70)
    logger.info("ESTADÍSTICAS DE BACKUPS")
    logger.info("=" * 70)
    logger.info(f"Directorio: {Config.BACKUP_DIR}")
    logger.info(f"Total de archivos: {stats['total_files']}")
    logger.info(f"Espacio utilizado: {stats['total_size_mb']:.2f} MB")
    
    if stats['oldest_backup']:
        logger.info(f"Backup más antiguo: {stats['oldest_backup']}")
    if stats['newest_backup']:
        logger.info(f"Backup más reciente: {stats['newest_backup']}")
    
    logger.info(f"Retención configurada: {backup_service.backup_settings.retention_days} días")
    logger.info("=" * 70)


def main():
    """Función principal"""
    try:
        # Reconfigurar stdout (lo que va a service_stdout.log)
        if sys.stdout.encoding.lower() != 'utf-8':
            sys.stdout.reconfigure(encoding='utf-8')
            
        # Reconfigurar stderr (lo que va a service_stderr.log)
        if sys.stderr.encoding.lower() != 'utf-8':
            sys.stderr.reconfigure(encoding='utf-8')
            
    except Exception as e:
        # Esto previene fallos si el entorno del servicio es muy restrictivo
        # o si la función reconfigure no está disponible.
        # En caso de fallar, el error de Unicode podría persistir, pero el programa continúa.
        pass
    
    args = parse_arguments()
    
    # Modo inicialización
    if args.init:
        initialize_config()
        return
    
    # Verificar que existe configuración
    if not Config.CONFIG_FILE.exists():
        print(f"Error: No se encontró {Config.CONFIG_FILE}")
        print("Ejecuta: python main.py --init")
        sys.exit(1)
    
    # Cargar variables de entorno desde .env si existe
    env_file = Config.BASE_DIR / ".env"
    if env_file.exists():
        try:
            from dotenv import load_dotenv
            load_dotenv(env_file)
        except ImportError:
            pass  # python-dotenv no es obligatorio
    
    # Crear repositorio y servicio
    config_repo = ConfigRepository()
    backup_service = BackupService(config_repo)
    
    # Modo estadísticas
    if args.stats:
        show_statistics(backup_service)
        return
    
    # Modo backup específico
    if args.db:
        logger = LoggerService.get_logger("Main")
        logger.info(f"Realizando backup de: {args.db}")
        result = backup_service.backup_specific_database(args.db)
        
        if result.success:
            logger.info(f"✓ Backup exitoso: {result.output_file}")
            sys.exit(0)
        else:
            logger.error(f"✗ Backup fallido: {result.error}")
            sys.exit(1)
    
    # Modo once (una sola ejecución)
    if args.mode == 'once':
        logger = LoggerService.get_logger("Main")
        logger.info("Modo: Ejecución única")
        results = backup_service.backup_all_databases()
        
        # Exit code basado en resultados
        failed = sum(1 for r in results if not r.success)
        sys.exit(1 if failed > 0 else 0)
    
    # Modo scheduler (por defecto)
    scheduler = SchedulerService(backup_service)
    scheduler.start(run_immediately=args.now)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nPrograma interrumpido por el usuario")
        sys.exit(0)
    except Exception as e:
        print(f"Error crítico: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)