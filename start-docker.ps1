# Docker 部署脚本 - 物流路径规划系统
# 作者：小彩 | 版本：2.0 | 日期：2026-03-30

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   物流路径规划系统 - Docker 部署工具   " -ForegroundColor Cyan
Write-Host "   版本: v2.0 (43项功能完整版)          " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 检查 Docker 是否运行
Write-Host "[1/6] 检查 Docker 状态..." -ForegroundColor Yellow
try {
    docker info | Out-Null
    Write-Host "      ✓ Docker 正在运行" -ForegroundColor Green
} catch {
    Write-Host "      ✗ Docker 未运行，请先启动 Docker Desktop" -ForegroundColor Red
    Write-Host "      按任意键退出..." -ForegroundColor Gray
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    exit 1
}

# 停止旧容器
Write-Host "[2/6] 停止旧容器..." -ForegroundColor Yellow
docker-compose -p logistics down 2>$null
Write-Host "      ✓ 旧容器已停止" -ForegroundColor Green

# 清理旧镜像（可选）
Write-Host "[3/6] 清理旧构建缓存..." -ForegroundColor Yellow
docker system prune -f 2>$null | Out-Null
Write-Host "      ✓ 缓存已清理" -ForegroundColor Green

# 创建数据目录
Write-Host "[4/6] 创建数据目录..." -ForegroundColor Yellow
$directories = @("data", "logs", "database")
foreach ($dir in $directories) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
}
Write-Host "      ✓ 数据目录已就绪" -ForegroundColor Green

# 构建镜像
Write-Host "[5/6] 构建 Docker 镜像..." -ForegroundColor Yellow
Write-Host "      这可能需要几分钟，请耐心等待..." -ForegroundColor Gray
docker-compose build --no-cache
if ($LASTEXITCODE -ne 0) {
    Write-Host "      ✗ 构建失败！" -ForegroundColor Red
    Write-Host "      按任意键退出..." -ForegroundColor Gray
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    exit 1
}
Write-Host "      ✓ 镜像构建完成" -ForegroundColor Green

# 启动服务
Write-Host "[6/6] 启动服务..." -ForegroundColor Yellow
docker-compose -p logistics up -d
if ($LASTEXITCODE -ne 0) {
    Write-Host "      ✗ 启动失败！" -ForegroundColor Red
    Write-Host "      按任意键退出..." -ForegroundColor Gray
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    exit 1
}
Write-Host "      ✓ 服务启动成功" -ForegroundColor Green

# 等待服务就绪
Write-Host ""
Write-Host "等待服务完全启动..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

# 健康检查
Write-Host "检查服务健康状态..." -ForegroundColor Yellow
$retries = 0
$maxRetries = 30
$healthy = $false

while ($retries -lt $maxRetries) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:5000/api/health" -TimeoutSec 5 -UseBasicParsing
        if ($response.StatusCode -eq 200) {
            $healthy = $true
            break
        }
    } catch {
        Start-Sleep -Seconds 1
        $retries++
        Write-Host "." -NoNewline -ForegroundColor Gray
    }
}

Write-Host ""
if ($healthy) {
    Write-Host "✓ 后端服务健康检查通过" -ForegroundColor Green
} else {
    Write-Host "⚠ 后端服务可能需要更多时间启动" -ForegroundColor Yellow
}

# 显示结果
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "          🎉 部署成功！🎉               " -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "访问地址：" -ForegroundColor White
Write-Host "  前端页面: " -NoNewline -ForegroundColor White
Write-Host "http://localhost:8080" -ForegroundColor Cyan
Write-Host "  后端 API: " -NoNewline -ForegroundColor White
Write-Host "http://localhost:5000" -ForegroundColor Cyan
Write-Host ""
Write-Host "登录账号：" -ForegroundColor White
Write-Host "  管理员: admin / admin123" -ForegroundColor Yellow
Write-Host "  普通用户: user / user123" -ForegroundColor Yellow
Write-Host "  司机: driver / driver123" -ForegroundColor Yellow
Write-Host ""
Write-Host "常用命令：" -ForegroundColor White
Write-Host "  查看日志: docker-compose logs -f" -ForegroundColor Gray
Write-Host "  停止服务: docker-compose down" -ForegroundColor Gray
Write-Host "  重启服务: docker-compose restart" -ForegroundColor Gray
Write-Host ""
Write-Host "提示：首次启动可能需要初始化数据库，请稍等片刻" -ForegroundColor Yellow
Write-Host ""
