# 物流路径规划系统 - Docker 停止脚本
# 使用方法: .\stop-docker.ps1

Write-Host "======================================" -ForegroundColor Cyan
Write-Host "  停止物流系统 Docker 容器" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan

# 停止容器
Write-Host "正在停止容器..." -ForegroundColor Yellow
docker-compose down

Write-Host ""
Write-Host "容器已停止 ✓" -ForegroundColor Green
Write-Host ""
Write-Host "如需完全清理（包括镜像），请运行:" -ForegroundColor Yellow
Write-Host "  docker-compose down --rmi all -v" -ForegroundColor Gray
Write-Host ""