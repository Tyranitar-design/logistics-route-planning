@echo off
chcp 65001 >nul
echo 🚚 物流路径规划系统 - 更新文档
echo ================================

cd /d "D:\物流路径规划系统项目"

echo 📝 添加新文档...
git add memory/Logistics_Project_Development_History.md
git add memory/Logistics_Project_Presentation_Document_Detailed.md
git add LICENSE
git add CONTRIBUTING.md

echo 💾 提交更新...
git commit -m "docs: 添加开发历程和详细演示文档"

echo 🚀 推送到 GitHub...
git push

echo.
echo ✅ 完成！
pause
