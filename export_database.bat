@echo off
echo 🗄️  Supabase Database Export Tools
echo ========================================
echo.
echo Prerequisites:
echo 1. Install required packages: pip install -r requirements-db-export.txt
echo 2. Ensure your .env file has the correct DATABASE_URL
echo 3. Install PostgreSQL client tools (for pg_dump option)
echo.
echo Available Export Methods:
echo ========================================
echo.
echo 1. Using pg_dump (requires PostgreSQL client)
echo    - Most comprehensive export
echo    - Exact PostgreSQL DDL/DML
echo    - Fastest for large databases
echo.
echo 2. Using Python + psycopg2 (pure Python)
echo    - Programmatic access to schema
echo    - Custom export formats
echo    - Good for analysis and manipulation
echo.
echo 3. Using SQLAlchemy (works with existing setup)
echo    - Uses your existing database configuration
echo    - Object-oriented approach
echo    - Good for selective exports
echo.
echo ========================================
echo.

:menu
echo Select an export method:
echo [1] pg_dump export
echo [2] Python + psycopg2 export  
echo [3] SQLAlchemy export
echo [4] Exit
echo.

set /p choice="Enter your choice (1-4): "

if "%choice%"=="1" goto pgdump
if "%choice%"=="2" goto python
if "%choice%"=="3" goto sqlalchemy
if "%choice%"=="4" goto exit
goto invalid

:pgdump
echo.
echo 🔧 Running pg_dump export...
python scripts/export_db_schema.py
goto end

:python
echo.
echo 🐍 Running Python psycopg2 export...
python scripts/extract_schema_python.py
goto end

:sqlalchemy
echo.
echo ⚡ Running SQLAlchemy export...
python scripts/sqlalchemy_exporter.py
goto end

:invalid
echo.
echo ❌ Invalid choice. Please select 1-4.
echo.
goto menu

:end
echo.
echo ✅ Export completed! Check the 'exports' folder for output files.
echo.
pause
goto exit

:exit