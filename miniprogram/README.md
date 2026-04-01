# 微信小程序开发指南

## 一、安装微信开发者工具

### 1. 下载地址
https://developers.weixin.qq.com/miniprogram/dev/devtools/download.html

### 2. 选择版本
- **Windows 64位**：选择 `Windows 64` 版本下载
- **Mac**：选择 `macOS` 版本下载

### 3. 安装步骤
1. 双击下载的安装包
2. 按照提示完成安装
3. 安装完成后打开微信开发者工具

---

## 二、注册小程序账号（如果还没有）

### 1. 注册地址
https://mp.weixin.qq.com/

### 2. 注册流程
1. 点击「立即注册」
2. 选择「小程序」
3. 填写账号信息（邮箱、密码）
4. 邮箱激活
5. 信息登记（主体类型选择「个人」即可）
6. 完成注册

### 3. 获取 AppID
1. 登录小程序后台：https://mp.weixin.qq.com/
2. 左侧菜单：开发 → 开发管理 → 开发设置
3. 找到「AppID(小程序ID)」复制

---

## 三、导入项目

### 1. 打开微信开发者工具
- 首次打开会提示登录
- 使用微信扫码登录

### 2. 导入项目
1. 点击左侧「小程序」
2. 点击「+」号（或「导入项目」）
3. 填写项目信息：
   - **项目名称**：物流司机端（可自定义）
   - **目录**：选择 `D:\物流路径规划系统项目\miniprogram`
   - **AppID**：填入你的小程序 AppID
   - **开发模式**：小程序
   - **后端服务**：不使用云服务

4. 点击「导入」

### 3. 项目打开后
- 左侧是代码目录
- 中间是代码编辑器
- 右侧是模拟器预览

---

## 四、配置项目

### 1. 替换 AppID
打开 `miniprogram/app.json`，找到：
```json
{
  "appid": "wx1234567890abcdef"
}
```
替换为你自己的 AppID

### 2. 配置后端地址
打开 `miniprogram/app.js`，找到：
```javascript
globalData: {
  baseUrl: 'http://localhost:5000/api',
  ...
}
```

如果后端部署在其他地址，修改为实际地址，例如：
```javascript
baseUrl: 'http://你的服务器IP:5000/api'
```

### 3. 添加图标
将图标文件放到 `miniprogram/assets/icons/` 目录

---

## 五、调试运行

### 1. 启动后端服务
```powershell
# 在 PowerShell 中运行
cd D:\物流路径规划系统项目\backend
.\venv\Scripts\python.exe run.py
```

等待显示 `Running on http://127.0.0.1:5000`

### 2. 在开发者工具中预览
- 点击顶部「编译」按钮
- 右侧模拟器会显示小程序界面
- 可以在模拟器中操作测试

### 3. 真机预览
1. 点击顶部「预览」按钮
2. 生成二维码
3. 用微信扫码体验

---

## 六、常见问题

### Q1: 提示「不在以下 request 合法域名列表中」
**解决方案**：
1. 小程序后台 → 开发 → 开发管理 → 开发设置
2. 找到「服务器域名」
3. 添加你的后端域名到「request合法域名」

**开发阶段临时方案**：
- 开发者工具右上角 → 详情 → 本地设置
- 勾选「不校验合法域名」

### Q2: 登录失败
- 检查后端是否启动
- 检查 baseUrl 配置是否正确
- 查看开发者工具控制台错误信息

### Q3: 图标不显示
- 确保图标文件存在于正确目录
- 检查文件名是否与 app.json 中配置一致
- 图片格式必须是 png

---

## 七、目录结构说明

```
miniprogram/
├── app.js          # 小程序入口，全局数据
├── app.json        # 全局配置（页面、TabBar、权限）
├── app.wxss        # 全局样式
├── project.config.json  # 项目配置
├── sitemap.json    # 小程序搜索配置
│
├── assets/         # 静态资源
│   └── icons/      # 图标文件
│       ├── home.png
│       ├── home-active.png
│       ├── order.png
│       ├── order-active.png
│       ├── map.png
│       ├── map-active.png
│       ├── user.png
│       └── user-active.png
│
├── components/     # 公共组件
│   └── location-tracker/  # 轨迹上报组件
│
├── utils/          # 工具函数
│   ├── api.js      # API 接口封装
│   └── util.js     # 通用工具函数
│
└── pages/          # 页面
    ├── index/      # 首页
    ├── dispatch/   # 派单通知
    ├── orders/     # 订单列表
    ├── order-detail/  # 订单详情
    ├── sign/       # 电子签收
    ├── map/        # 地图导航
    ├── profile/    # 个人中心
    └── login/      # 登录页面
```

---

## 八、快速开始检查清单

- [ ] 已安装微信开发者工具
- [ ] 已注册小程序账号
- [ ] 已获取 AppID
- [ ] 已导入项目
- [ ] 已替换 AppID
- [ ] 已添加图标文件
- [ ] 已启动后端服务
- [ ] 已在开发者工具中预览

---

**提示**：开发阶段可以不配置合法域名，直接勾选「不校验合法域名」即可调试。