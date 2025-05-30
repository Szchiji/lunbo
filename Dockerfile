FROM python:3.11-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目代码
COPY . .

# 暴露端口（Render默认端口为10000，也可改）
EXPOSE 10000

# 启动命令
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000"]