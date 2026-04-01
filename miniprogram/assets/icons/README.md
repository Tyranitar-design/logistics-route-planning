# 小程序图标资源说明

## TabBar 图标要求

| 属性 | 要求 |
|------|------|
| 尺寸 | 81px × 81px（推荐） |
| 格式 | PNG |
| 颜色 | 默认状态：灰色 #999999<br>选中状态：蓝色 #409EFF |
| 背景 | 透明 |

## 需要的图标文件

### TabBar 图标（共 8 个）

| 文件名 | 用途 | 默认 | 选中 |
|--------|------|------|------|
| home.png | 首页 | 灰色房子 | 蓝色房子 |
| home-active.png | 首页（选中） | - | - |
| order.png | 订单 | 灰色列表 | 蓝色列表 |
| order-active.png | 订单（选中） | - | - |
| map.png | 地图 | 灰色地图 | 蓝色地图 |
| map-active.png | 地图（选中） | - | - |
| user.png | 我的 | 灰色用户 | 蓝色用户 |
| user-active.png | 我的（选中） | - | - |

## 获取图标的方式

### 方式一：在线图标库（推荐）

1. **阿里巴巴矢量图标库**
   - 网址：https://www.iconfont.cn/
   - 搜索关键词：home、order、map、user
   - 选择图标 → 下载 PNG → 选择尺寸 81px

2. **Flaticon**
   - 网址：https://www.flaticon.com/
   - 搜索对应图标

### 方式二：使用 Figma/Sketch 制作

1. 创建 81×81 画布
2. 绘制或导入图标
3. 导出 PNG

### 方式三：使用占位图标

如果暂时没有设计资源，可以用纯色圆形占位：

**灰色版（home.png, order.png, map.png, user.png）**
- 81×81 像素
- 灰色圆形 #999999

**蓝色版（home-active.png 等）**
- 81×81 像素
- 蓝色圆形 #409EFF

## 图标存放位置

```
miniprogram/
└── assets/
    └── icons/
        ├── home.png
        ├── home-active.png
        ├── order.png
        ├── order-active.png
        ├── map.png
        ├── map-active.png
        ├── user.png
        ├── user-active.png
        │
        ├── start.png      # 地图标记-起点
        ├── end.png        # 地图标记-终点
        ├── driver.png     # 地图标记-司机
        ├── location.png   # 定位按钮
        ├── refresh.png    # 刷新按钮
        └── logo.png       # 登录页 Logo
```