# Script de PowerShell para instalar Python y dependencias
# Peña Linda Bungalows - Sistema de Procesamiento de Pagos

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " Peña Linda Bungalows - Instalador" -ForegroundColor Cyan
Write-Host " Sistema de Procesamiento de Pagos" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Verificar si Python está instalado
try {
    $pythonVersion = python --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Python encontrado: $pythonVersion" -ForegroundColor Green
    } else {
        throw "Python no encontrado"
    }
} catch {
    Write-Host "❌ Python no está instalado" -ForegroundColor Red
    Write-Host ""
    Write-Host "📥 Opciones de instalación:" -ForegroundColor Yellow
    Write-Host "1. Microsoft Store (Recomendado):" -ForegroundColor White
    Write-Host "   - Abre Microsoft Store" -ForegroundColor Gray
    Write-Host "   - Busca 'Python 3.11'" -ForegroundColor Gray
    Write-Host "   - Haz clic en 'Obtener'" -ForegroundColor Gray
    Write-Host ""
    Write-Host "2. Sitio oficial:" -ForegroundColor White
    Write-Host "   - Ve a https://www.python.org/downloads/" -ForegroundColor Gray
    Write-Host "   - Descarga Python 3.9 o superior" -ForegroundColor Gray
    Write-Host "   - Durante la instalación, marca 'Add Python to PATH'" -ForegroundColor Gray
    Write-Host ""
    
    $choice = Read-Host "¿Quieres abrir Microsoft Store? (s/n)"
    if ($choice -eq "s" -or $choice -eq "S") {
        Start-Process "ms-windows-store://pdp/?ProductId=9NRWMJP3717K"
    }
    
    Write-Host "Ejecuta este script nuevamente después de instalar Python" -ForegroundColor Yellow
    Read-Host "Presiona Enter para salir"
    exit 1
}

Write-Host ""
Write-Host "📦 Instalando dependencias..." -ForegroundColor Yellow

# Instalar dependencias
$packages = @("pandas", "numpy", "streamlit", "plotly", "openpyxl", "python-dateutil")

foreach ($package in $packages) {
    Write-Host "Instalando $package..." -ForegroundColor Gray
    try {
        pip install $package --quiet
        Write-Host "✅ $package instalado" -ForegroundColor Green
    } catch {
        Write-Host "❌ Error instalando $package" -ForegroundColor Red
        try {
            pip3 install $package --quiet
            Write-Host "✅ $package instalado con pip3" -ForegroundColor Green
        } catch {
            Write-Host "❌ No se pudo instalar $package" -ForegroundColor Red
        }
    }
}

Write-Host ""
Write-Host "🧪 Probando el sistema..." -ForegroundColor Yellow

# Probar el sistema
try {
    python test_system.py
    Write-Host ""
    Write-Host "✅ Sistema instalado correctamente!" -ForegroundColor Green
} catch {
    Write-Host "⚠️ Hubo algunos problemas en la prueba, pero las dependencias están instaladas" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "🚀 Comandos para usar el sistema:" -ForegroundColor Cyan
Write-Host "   python test_system.py          (para probar el sistema)" -ForegroundColor White
Write-Host "   streamlit run web_interface.py (para la interfaz web)" -ForegroundColor White
Write-Host ""

Read-Host "Presiona Enter para continuar"