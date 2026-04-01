# Frontend Dockerfile - 物流路径规划系统前端
# Vue 3 + Element Plus + ECharts

# 阶段 1: 构建
FROM node:18-alpine AS builder

LABEL maintainer="小彩 <xiaocai@openclaw.ai>"
LABEL version="2.0"

WORKDIR /app

# 复制依赖文件
COPY package*.json ./

# 安装依赖（使用淘宝镜像加速）
RUN npm install --registry=https://registry.npmmirror.com

# 复制源代码
COPY . .

# 构建生产版本
RUN npm run build

# 阶段 2: 生产环境（Nginx）
FROM nginx:alpine

# 安装 curl 用于健康检查
RUN apk add --no-cache curl

# 复制构建产物
COPY --from=builder /app/dist /usr/share/nginx/html

# 复制 nginx 配置
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 暴露端口
EXPOSE 80

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost/ || exit 1

# 启动 nginx
CMD ["nginx", "-g", "daemon off;"]
