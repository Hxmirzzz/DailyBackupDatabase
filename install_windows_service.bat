@echo off
REM ============================================
REM Instalador de Servicio de Backup de BBDD
REM Sistema de backup automatico SQL Server
REM ============================================

echo.
echo ============================================
echo Instalador de Servicio de Backup de BBDD
echo ============================================
echo.

REM Verificar privilegios de administrador
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: Este script requiere privilegios de administrador
    echo.
    echo Por favor:
    echo 1. Cierra esta ventana
    echo 2. Click derecho en el archivo install_windows_service.bat
    echo 3. Selecciona "Ejecutar como administrador"
    echo.
    pause
    exit /b 1
)

echo [OK] Ejecutando con privilegios de administrador
echo.

REM Obtener directorio actual (donde esta el .bat)
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

echo Directorio de trabajo: %CD%
echo.

REM Verificar Python (probar python y py)
echo Verificando instalacion de Python...

REM Intentar con 'python'
python --version >nul 2>&1
if %errorLevel% equ 0 (
    set "PYTHON_CMD=python"
    for /f "tokens=*" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
    echo [OK] %PYTHON_VERSION% detectado (comando: python^)
    goto :python_found
)

REM Intentar con 'py'
py --version >nul 2>&1
if %errorLevel% equ 0 (
    set "PYTHON_CMD=py"
    for /f "tokens=*" %%i in ('py --version 2^>^&1') do set PYTHON_VERSION=%%i
    echo [OK] %PYTHON_VERSION% detectado (comando: py^)
    goto :python_found
)

REM Buscar Python en ubicaciones comunes
echo Buscando Python en ubicaciones comunes...
for %%P in (
    "C:\Python312\python.exe"
    "C:\Python311\python.exe"
    "C:\Python310\python.exe"
    "C:\Python39\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
    "%USERPROFILE%\AppData\Local\Programs\Python\Python312\python.exe"
    "%USERPROFILE%\AppData\Local\Programs\Python\Python311\python.exe"
) do (
    if exist %%P (
        set "PYTHON_CMD=%%~P"
        for /f "tokens=*" %%i in ('%%~P --version 2^>^&1') do set PYTHON_VERSION=%%i
        echo [OK] %PYTHON_VERSION% encontrado en: %%~P
        goto :python_found
    )
)

REM Si llegamos aqui, Python no se encontro
echo.
echo ============================================
echo ERROR: Python no esta instalado o no esta en el PATH
echo ============================================
echo.
echo Soluciones:
echo.
echo OPCION 1 - Verificar instalacion:
echo   1. Abre CMD y prueba:
echo      python --version
echo      py --version
echo.
echo OPCION 2 - Reinstalar Python:
echo   1. Ve a: https://www.python.org/downloads/
echo   2. Descarga Python 3.9 o superior
echo   3. IMPORTANTE: Marca "Add Python to PATH"
echo   4. Reinicia la terminal despues de instalar
echo.
echo OPCION 3 - Agregar Python al PATH manualmente:
echo   1. Busca donde esta instalado Python
echo   2. Panel de Control ^> Sistema ^> Configuracion avanzada
echo   3. Variables de entorno ^> PATH
echo   4. Agrega la ruta de Python
echo.
echo OPCION 4 - Usar Python Launcher:
echo   En algunos sistemas, usa 'py' en lugar de 'python'
echo.
pause
exit /b 1

:python_found
echo.

REM Verificar que existe main.py
if not exist "main.py" (
    echo ERROR: No se encuentra main.py en el directorio actual
    echo Asegurate de estar en la raiz del proyecto DailyBackupDatabase
    echo.
    pause
    exit /b 1
)

echo [OK] main.py encontrado
echo.

REM Crear directorios necesarios
echo Creando directorios del sistema...
if not exist "Logs" mkdir Logs
if not exist "Backups" mkdir Backups
if not exist "Backups\Annual" mkdir Backups\Annual
echo [OK] Directorios creados
echo.

REM Verificar/Crear entorno virtual
if not exist "venv\Scripts\python.exe" (
    echo Creando entorno virtual...
    python -m venv venv
    if %errorLevel% neq 0 (
        echo ERROR: No se pudo crear el entorno virtual
        pause
        exit /b 1
    )
    echo [OK] Entorno virtual creado
    echo.
    
    echo Instalando dependencias...
    call venv\Scripts\activate
    python -m pip install --upgrade pip
    pip install -r requirements.txt
    if %errorLevel% neq 0 (
        echo ERROR: No se pudieron instalar las dependencias
        pause
        exit /b 1
    )
    call venv\Scripts\deactivate
    echo [OK] Dependencias instaladas
    echo.
) else (
    echo [OK] Entorno virtual ya existe
    echo.
)

REM Verificar archivos de configuracion
echo Verificando archivos de configuracion...

if not exist "config.json" (
    if exist "config.json.example" (
        echo Copiando config.json.example a config.json...
        copy config.json.example config.json >nul
        echo.
        echo IMPORTANTE: Debes editar config.json con tu configuracion
        set NEED_CONFIG=1
    ) else (
        echo Creando config.json desde main.py...
        venv\Scripts\python.exe main.py --init
        set NEED_CONFIG=1
    )
) else (
    echo [OK] config.json encontrado
)

if not exist ".env" (
    if exist ".env.example" (
        echo Copiando .env.example a .env...
        copy .env.example .env >nul
        echo.
        echo IMPORTANTE: Debes editar .env con tus credenciales
        set NEED_ENV=1
    )
) else (
    echo [OK] .env encontrado
)

echo.

REM Advertencia de configuracion
if defined NEED_CONFIG (
    echo ============================================
    echo ATENCION: CONFIGURACION REQUERIDA
    echo ============================================
    echo.
    echo Se han creado archivos de configuracion de ejemplo.
    echo DEBES editarlos antes de continuar:
    echo.
    echo 1. Edita config.json con:
    echo    - Nombre de tu base de datos
    echo    - Host del servidor SQL Server
    echo    - Puerto (normalmente 1433^)
    echo.
    echo 2. Edita .env con:
    echo    - MSSQL_USER=tu_usuario
    echo    - MSSQL_PASSWORD=tu_password
    echo.
    echo Presiona cualquier tecla cuando hayas terminado...
    pause >nul
    echo.
)

REM Verificar NSSM
echo Verificando NSSM (Non-Sucking Service Manager^)...
where nssm >nul 2>&1
if %errorLevel% neq 0 (
    echo.
    echo ============================================
    echo ERROR: NSSM no esta instalado
    echo ============================================
    echo.
    echo NSSM es necesario para instalar el servicio de Windows.
    echo.
    echo Opciones:
    echo.
    echo 1. INSTALAR NSSM (Recomendado^):
    echo    a. Descarga desde: https://nssm.cc/download
    echo    b. Extrae nssm.exe a C:\Windows\System32
    echo    c. O agrega la carpeta de NSSM al PATH
    echo.
    echo 2. USAR TASK SCHEDULER:
    echo    - Abre "Programador de tareas"
    echo    - Crea tarea basica
    echo    - Disparador: "Al iniciar el sistema"
    echo    - Accion: "%CD%\venv\Scripts\python.exe" "%CD%\main.py"
    echo.
    pause
    exit /b 1
)

echo [OK] NSSM instalado
echo.

REM Detener y eliminar servicio existente
echo Verificando servicios existentes...
nssm status DBBackupService >nul 2>&1
if %errorLevel% equ 0 (
    echo Servicio existente detectado. Deteniendo...
    nssm stop DBBackupService
    timeout /t 2 /nobreak >nul
    echo Eliminando servicio anterior...
    nssm remove DBBackupService confirm
    timeout /t 2 /nobreak >nul
    echo [OK] Servicio anterior eliminado
) else (
    echo [OK] No hay servicios previos
)
echo.

REM Instalar servicio
echo ============================================
echo INSTALANDO SERVICIO
echo ============================================
echo.
echo Configuracion:
echo - Nombre: DBBackupService
echo - Python: %CD%\venv\Scripts\python.exe
echo - Script: %CD%\main.py
echo - Directorio: %CD%
echo.

nssm install DBBackupService "%CD%\venv\Scripts\python.exe"
nssm set DBBackupService AppParameters "\"%CD%\main.py\""
nssm set DBBackupService AppDirectory "%CD%"

if %errorLevel% neq 0 (
    echo ERROR: No se pudo instalar el servicio
    pause
    exit /b 1
)
echo [OK] Servicio instalado
echo.

REM Configurar servicio
echo Configurando parametros del servicio...

nssm set DBBackupService AppDirectory "%CD%"
nssm set DBBackupService DisplayName "Database Backup Service"
nssm set DBBackupService Description "Sistema automatico de backup para SQL Server con scripts completos DDL+DML"
nssm set DBBackupService Start SERVICE_AUTO_START

REM Configurar logs
nssm set DBBackupService AppStdout "%CD%\Logs\service_stdout.log"
nssm set DBBackupService AppStderr "%CD%\Logs\service_stderr.log"
nssm set DBBackupService AppStdoutCreationDisposition 4
nssm set DBBackupService AppStderrCreationDisposition 4
nssm set DBBackupService AppEnvironmentExtra code_page=65001

REM Configurar rotacion de logs (10MB maximo)
nssm set DBBackupService AppRotateFiles 1
nssm set DBBackupService AppRotateOnline 1
nssm set DBBackupService AppRotateSeconds 86400
nssm set DBBackupService AppRotateBytes 10485760

REM Configurar reinicio automatico
nssm set DBBackupService AppExit Default Restart
nssm set DBBackupService AppRestartDelay 5000
nssm set DBBackupService AppThrottle 10000

REM Configurar dependencias (esperar a que SQL Server inicie)
nssm set DBBackupService DependOnService LanmanServer

echo [OK] Servicio configurado
echo.

REM Verificar instalacion
echo Verificando instalacion...
nssm status DBBackupService >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: El servicio no se instalo correctamente
    pause
    exit /b 1
)

echo [OK] Servicio verificado
echo.

REM Resumen
echo ============================================
echo INSTALACION COMPLETADA
echo ============================================
echo.
echo El servicio "DBBackupService" ha sido instalado correctamente.
echo.
echo COMANDOS UTILES:
echo.
echo   Iniciar servicio:
echo     nssm start DBBackupService
echo     o desde Servicios de Windows (services.msc^)
echo.
echo   Detener servicio:
echo     nssm stop DBBackupService
echo.
echo   Ver estado:
echo     nssm status DBBackupService
echo.
echo   Editar configuracion:
echo     nssm edit DBBackupService
echo.
echo   Ver logs:
echo     type Logs\service_stdout.log
echo     type Logs\service_stderr.log
echo     type Logs\BackupService_*.log
echo.
echo   Eliminar servicio:
echo     nssm stop DBBackupService
echo     nssm remove DBBackupService confirm
echo.
echo ARCHIVOS IMPORTANTES:
echo   - config.json  : Configuracion de bases de datos
echo   - .env         : Credenciales (NUNCA subir a Git^)
echo   - Logs\        : Logs del sistema
echo   - Backups\     : Backups diarios (30 dias^)
echo   - Backups\Annual\ : Backups anuales (permanentes^)
echo.
echo ============================================
echo.

set /p START_NOW="¿Deseas iniciar el servicio ahora? (S/N): "
if /i "%START_NOW%"=="S" (
    echo.
    echo Iniciando servicio...
    nssm start DBBackupService
    timeout /t 3 /nobreak >nul
    echo.
    nssm status DBBackupService
    echo.
    echo Revisa los logs en: %CD%\Logs\
    echo.
) else (
    echo.
    echo El servicio esta instalado pero NO iniciado.
    echo Para iniciarlo manualmente:
    echo   nssm start DBBackupService
    echo   o desde Servicios de Windows (services.msc^)
    echo.
)

echo Presiona cualquier tecla para salir...
pause >nul