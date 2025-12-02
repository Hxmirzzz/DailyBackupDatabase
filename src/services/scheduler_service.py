"""
Servicio de programación de tareas de backup
"""
import schedule
import time
import signal
import sys
from ..logger import LoggerService
from .backup_service import BackupService


class SchedulerService:
    """Servicio para programar y ejecutar backups automáticos"""
    
    def __init__(self, backup_service: BackupService):
        """
        Inicializa el servicio de programación
        
        Args:
            backup_service: Servicio de backup a ejecutar
        """
        self.backup_service = backup_service
        self.logger = LoggerService.get_logger("SchedulerService")
        self.running = False
        
        # Registrar manejadores de señales para shutdown graceful
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def start(self, run_immediately: bool = False):
        """
        Inicia el programador de tareas
        
        Args:
            run_immediately: Si es True, ejecuta un backup inmediatamente al iniciar
        """
        schedules = self.backup_service.backup_settings.schedule
        annual_enabled = self.backup_service.backup_settings.annual_backup_enabled
        annual_date = self.backup_service.backup_settings.annual_backup_date
        
        for schedule_time in schedules:
            schedule.every().day.at(schedule_time).do(self._run_daily_backup_job)
        
        self.logger.info("=" * 70)
        self.logger.info("SERVICIO DE BACKUP AUTOMÁTICO INICIADO")
        self.logger.info("=" * 70)
        self.logger.info(f"Backups diarios programados: {len(schedules)}")
        for scheduled_time in schedules:
            self.logger.info(f"  - A las {scheduled_time}")
        self.logger.info(f"Retención de backups diarios: {self.backup_service.backup_settings.retention_days} días")
        
        if annual_enabled:
            self.logger.info(f"Backup anual: Habilitado (fecha: {annual_date})")
            self.logger.info(f"Backups anuales se mantienen indefinidamente")
        else:
            self.logger.info(f"Backup anual: Deshabilitado")
        
        self.logger.info(f"Bases de datos configuradas: {len(self.backup_service.databases)}")
        
        for db in self.backup_service.databases:
            status = "✓ Habilitada" if db.enabled else "✗ Deshabilitada"
            self.logger.info(f"  - {db.name} ({db.type}): {status}")
        
        self.logger.info("-" * 70)
        self.logger.info(f"Próxima ejecución: {self.get_next_run()}")
        self.logger.info("Presiona Ctrl+C para detener el servicio")
        self.logger.info("=" * 70)
        
        # Ejecutar backup inmediatamente si se solicita
        if run_immediately:
            self.logger.info("Ejecutando backup inicial...")
            self._run_daily_backup_job()
        
        # Loop principal
        self.running = True
        try:
            while self.running:
                schedule.run_pending()
                time.sleep(60)  # Revisar cada minuto
        except KeyboardInterrupt:
            self._shutdown()
    
    def _run_daily_backup_job(self):
        """Ejecuta el trabajo de backup diario"""
        try:
            self.logger.info(f"Ejecutando backup programado a las {time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Verificar si hoy es día de backup anual
            should_annual = self.backup_service.should_create_annual_backup()
            
            if should_annual:
                self.logger.info("=" * 70)
                self.logger.info("¡HOY ES DÍA DE BACKUP ANUAL!")
                self.logger.info("=" * 70)
                
                # Ejecutar backup anual
                annual_results = self.backup_service.backup_all_databases(is_annual=True)
                
                # Verificar errores en backup anual
                failed_annual = [r for r in annual_results if not r.success]
                if failed_annual:
                    self.logger.warning(
                        f"Backup anual completado con {len(failed_annual)} error(es)"
                    )
                else:
                    self.logger.info("Backup anual completado exitosamente")
                
                self.logger.info("-" * 70)
                self.logger.info("Continuando con backup diario...")
            
            # Ejecutar backup diario normal
            results = self.backup_service.backup_all_databases(is_annual=False)
            
            # Verificar si hubo errores
            failed = [r for r in results if not r.success]
            if failed:
                self.logger.warning(
                    f"Backup diario completado con {len(failed)} error(es). "
                    "Revisa los logs para más detalles."
                )
            else:
                self.logger.info("Backup diario completado exitosamente")
                
        except Exception as e:
            self.logger.error(f"Error crítico durante backup: {e}", exc_info=True)
    
    def _signal_handler(self, signum, frame):
        """
        Manejador de señales para shutdown graceful
        
        Args:
            signum: Número de señal
            frame: Frame actual
        """
        try:
            signal_name = signal.Signals(signum).name
        except:
            signal_name = str(signum)
        
        self.logger.info(f"Señal recibida: {signal_name}")
        self._shutdown()
    
    def _shutdown(self):
        """Detiene el servicio de forma ordenada"""
        self.logger.info("Deteniendo servicio de backup...")
        self.running = False
        schedule.clear()
        self.logger.info("Servicio detenido correctamente")
        sys.exit(0)
    
    def get_next_run(self) -> str:
        """
        Obtiene el tiempo hasta la próxima ejecución
        
        Returns:
            String con el tiempo hasta la próxima ejecución
        """
        next_run = schedule.next_run()
        if next_run:
            return next_run.strftime('%Y-%m-%d %H:%M:%S')
        return "No hay ejecuciones programadas"