@echo off
chcp 65001 >nul
echo ========================================
echo   物流大数据实时数据管道启动器
echo ========================================
echo.

cd /d D:\物流路径规划系统项目\backend

echo [1/3] 检查依赖...
pip show kafka-python >nul 2>&1
if errorlevel 1 (
    echo 安装 kafka-python...
    pip install kafka-python requests -q
)
echo ✅ 依赖已就绪

echo.
echo [2/3] 启动 Kafka 消费者 (Kafka -^> ClickHouse)...
start "Kafka-ClickHouse Consumer" cmd /k "cd /d D:\物流路径规划系统项目\backend\services && python kafka_to_clickhouse.py"
timeout /t 3 >nul

echo.
echo [3/3] 启动数据生成器...
start "Data Generator" cmd /k "cd /d D:\物流路径规划系统项目\backend\services && python realtime_data_generator.py"
timeout /t 3 >nul

echo.
echo ========================================
echo   ✅ 所有服务已启动！
echo ========================================
echo.
echo   窗口说明:
echo   - Kafka-ClickHouse Consumer: 数据消费者
echo   - Data Generator: 数据生成器
echo.
echo   数据流:
echo   数据生成器 -^> Kafka -^> 消费者 -^> ClickHouse
echo.
echo   Grafana 访问: http://localhost:3000
echo   默认账号: admin / admin
echo.
echo   按任意键关闭此窗口...
pause >nul
