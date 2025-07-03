# Leek 量化交易系统

## 项目结构

```
leek/
├── leek-core/          # 核心交易引擎
├── leek-manager/       # 后端管理系统
├── leek-web/          # 前端界面
└── leek.py            # 项目管理脚本
```

## 快速开始

- [开发文档](https://github.com/TechHares/leek-core/blob/main/README.md)
- [使用文档](https://github.com/TechHares/leek-manager/blob/main/README.md)
- 讨论组：<a href="https://t.me/+lFHR-vTZ6Y1iZTU1">Telegram</a>

### 开发环境

#### 1. 直接使用
```bash
# clone代码
git clone --recurse-submodules https://github.com/TechHares/leek.git 
# 指定端口
python leek.py start 8010
```

#### 2. 启动后端
```bash
cd leek-manager
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### 3. 启动前端
```bash
cd leek-web
npm run dev
```

### 生产环境

使用统一的管理脚本：

```bash
# 清理所有构建输出
python leek.py clean

# 构建前端并复制到后端
python leek.py build

# 启动服务（后台，默认8009）
python leek.py start
# 或指定端口
python leek.py start 8010

# 前台运行（适合开发，默认8009）
python leek.py run
# 或指定端口
python leek.py run 8011

# 查看服务状态
python leek.py status

# 停止服务
python leek.py stop

# 重启服务（默认8009）
python leek.py restart
# 或指定端口
python leek.py restart 8012

# 数据库迁移相关
python leek.py dml "添加用户表"      # 生成迁移脚本
python leek.py migrate              # 应用迁移
python leek.py downgrade -1         # 回滚一个版本
python leek.py db_status            # 查看迁移状态
python leek.py check_migration      # 手动触发迁移检查
```

## 脚本功能说明

### `python leek.py clean`
清理所有构建输出，包括：
- 前端构建文件 (`leek-web/dist/`)
- 前端依赖 (`leek-web/node_modules/`)
- 后端静态文件 (`leek-manager/static/`)
- Python缓存文件 (`__pycache__/`, `*.pyc`)
- 其他构建文件
- PID文件

### `python leek.py build`
构建前端并复制到后端：
- 安装前端依赖
- 构建前端到 `leek-web/dist/`
- 清空后端静态目录
- 复制前端文件到 `leek-manager/static/`

### `python leek.py start [port]`
后台启动服务，端口可选，默认8009。
- 检查前端是否已构建，未构建则自动构建
- 在后台启动FastAPI服务
- 服务地址：http://localhost:端口

### `python leek.py run [port]`
前台运行服务（适合开发/调试），端口可选，默认8009。
- 检查前端是否已构建，未构建则自动构建
- 前台直接运行 FastAPI 服务
- Ctrl+C 可直接停止

### `python leek.py stop`
停止服务：
- 优雅停止运行中的服务
- 清理PID文件

### `python leek.py restart [port]`
重启服务，端口可选，默认8009。
- 先停止服务
- 再启动服务

### `python leek.py status`
查看服务状态：
- 显示服务运行状态
- 显示前端构建状态

### `python leek.py dml <message>`
生成数据库迁移脚本：
- 自动检测模型变化
- 生成迁移脚本到 `leek-manager/migrations/versions/`
- 需要提供迁移描述信息

### `python leek.py migrate`
应用数据库迁移：
- 将待应用的迁移脚本应用到数据库
- 更新数据库结构

### `python leek.py downgrade <revision>`
回滚数据库迁移：
- 回滚到指定的迁移版本
- 支持相对版本号（如 `-1` 表示回滚一个版本）

### `python leek.py db_status`
查看数据库迁移状态：
- 显示当前数据库版本
- 显示迁移历史

### `python leek.py check_migration`
手动触发迁移检查：
- 重置连接状态
- 强制重新检查并应用迁移
- 用于解决迁移状态不一致问题

## 数据库迁移机制

### 自动迁移
系统在每次数据库连接时会自动检查并应用迁移：
- 使用alembic进行数据库版本管理
- 只在需要时执行迁移（避免重复执行）
- 支持并发安全（使用线程锁）

### 手动迁移
可以通过以下命令手动管理迁移：
- `dml` - 生成迁移脚本
- `migrate` - 应用迁移
- `downgrade` - 回滚迁移
- `check_migration` - 强制检查迁移

## 部署说明

### 单服务部署
生产环境只需要启动一个服务，同时提供API和前端界面：

```bash
# 构建并启动
python leek.py build
python leek.py start
```

访问 http://localhost:8009 即可使用完整系统。

### 环境变量
```bash
# 设置环境变量（可选）
export HOST=0.0.0.0
export PORT=8009
export ENVIRONMENT=production
```

## 注意事项

1. **首次使用**：需要先安装依赖
   ```bash
   python leek.py install
   ```

2. **前端更新**：修改前端代码后需要重新构建
   ```bash
   python leek.py build
   ```

3. **服务日志**：服务运行日志保存在 `leek.log` 文件中

4. **端口占用**：确保端口未被占用

## 故障排除

### 服务启动失败
```bash
# 检查端口占用
lsof -i :8009

# 查看日志
tail -f leek.log
```

### 前端构建失败
```bash
# 清理后重新构建
python leek.py clean
python leek.py build
```

