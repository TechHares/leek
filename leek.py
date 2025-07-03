#!/usr/bin/env python3
"""
Leek 项目管理脚本
统一管理前端构建、后端启动等功能
"""

import os
import sys
if sys.version_info < (3, 8) or sys.version_info >= (3, 13):
    print("请使用Python3.8-3.12版本")
    print("请使用Python3.8-3.12版本")
    print("请使用Python3.8-3.12版本")
    sys.exit(1)
import subprocess

def ensure_module(module, package=None):
    try:
        __import__(module)
    except ImportError:
        print(f"自动安装依赖: {package or module}")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package or module])

# 自动确保 leek.py 运行所需的依赖
ensure_module("toml")
ensure_module("psutil")
ensure_module("alembic")
ensure_module("poetry")

import shutil
import signal
import time
import psutil
from pathlib import Path
from typing import Optional
import re
import toml


try:
    import importlib.metadata
except ImportError:
    ensure_module("importlib_metadata", "importlib-metadata")


class LeekManager:
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.frontend_dir = self.project_root / "leek-web"
        self.backend_dir = self.project_root / "leek-manager"
        self.core_dir = self.project_root / "leek-core"
        self.pid_file = self.project_root / "leek.pid"
        
    def run_command(self, command: str, cwd: Optional[Path] = None, capture_output: bool = True) -> bool:
        """运行命令并返回结果"""
        print(f"执行命令: {command}")
        if cwd:
            print(f"工作目录: {cwd}")
        
        try:
            if capture_output:
                # 实时输出模式
                process = subprocess.Popen(
                    command,
                    shell=True,
                    cwd=cwd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    universal_newlines=True
                )
                
                while True:
                    output = process.stdout.readline()
                    if output == '' and process.poll() is not None:
                        break
                    if output:
                        output = output.strip()
                        if "finished with status 'error'" in output:
                            print(output)
                            print("请检查依赖包是否安装成功")
                            return False
                        print(output)
                
                returncode = process.poll()
                return returncode == 0
            else:
                # 非捕获模式，直接执行
                result = subprocess.run(
                    command,
                    shell=True,
                    cwd=cwd,
                    text=True
                )
                return result.returncode == 0
                
        except Exception as e:
            print(f"命令执行异常: {e}")
            return False
    
    def clean(self):
        """清理所有构建输出"""
        print("开始清理构建输出...")
        
        # 清理前端构建文件
        frontend_dist = self.frontend_dir / "dist"
        if frontend_dist.exists():
            print(f"清理前端构建目录: {frontend_dist}")
            shutil.rmtree(frontend_dist)
        
        # 清理前端node_modules
        frontend_node_modules = self.frontend_dir / "node_modules"
        if frontend_node_modules.exists():
            print(f"清理前端依赖: {frontend_node_modules}")
            shutil.rmtree(frontend_node_modules)
        
        # 清理后端静态文件（复制的前端文件）
        backend_static = self.backend_dir / "static"
        if backend_static.exists():
            print(f"清理后端静态文件: {backend_static}")
            shutil.rmtree(backend_static)
        
        # 清理Python缓存文件
        for root, dirs, files in os.walk(self.project_root):
            # 清理 __pycache__ 目录
            for dir_name in dirs[:]:  # 使用切片创建副本，避免修改迭代中的列表
                if dir_name == "__pycache__":
                    cache_dir = Path(root) / dir_name
                    print(f"清理Python缓存: {cache_dir}")
                    shutil.rmtree(cache_dir)
                    dirs.remove(dir_name)  # 从dirs中移除，避免继续遍历
            
            # 清理 .pyc 文件
            for file_name in files:
                if file_name.endswith('.pyc'):
                    pyc_file = Path(root) / file_name
                    print(f"清理Python字节码: {pyc_file}")
                    pyc_file.unlink()
        
        # 清理其他构建文件
        build_dirs = [
            self.backend_dir / "build",
            self.backend_dir / "dist",
            self.backend_dir / "*.egg-info",
        ]
        
        for build_dir in build_dirs:
            if isinstance(build_dir, str):
                # 处理通配符
                import glob
                for path in glob.glob(str(self.backend_dir / build_dir.split('/')[-1])):
                    path_obj = Path(path)
                    if path_obj.exists():
                        print(f"清理构建文件: {path_obj}")
                        if path_obj.is_dir():
                            shutil.rmtree(path_obj)
                        else:
                            path_obj.unlink()
            elif build_dir.exists():
                print(f"清理构建文件: {build_dir}")
                shutil.rmtree(build_dir)
        
        # 清理PID文件
        if self.pid_file.exists():
            print(f"清理PID文件: {self.pid_file}")
            self.pid_file.unlink()
        
        # 清理日志文件
        log_files = [
            self.backend_dir / "leek.log",
            self.project_root / "leek.log",
            self.backend_dir / "*.log",
            self.project_root / "*.log"
        ]
        
        for log_file in log_files:
            if isinstance(log_file, str):
                # 处理通配符
                import glob
                for path in glob.glob(str(log_file)):
                    path_obj = Path(path)
                    if path_obj.exists() and path_obj.is_file():
                        print(f"清理日志文件: {path_obj}")
                        path_obj.unlink()
            elif log_file.exists() and log_file.is_file():
                print(f"清理日志文件: {log_file}")
                log_file.unlink()
        
        # 清理奇怪的文件（如 =1.0.0）
        strange_files = [
            self.core_dir / "=*",
            self.backend_dir / "=*"
        ]
        
        for pattern in strange_files:
            import glob
            for path in glob.glob(str(pattern)):
                path_obj = Path(path)
                if path_obj.exists() and path_obj.is_file():
                    print(f"清理奇怪文件: {path_obj}")
                    path_obj.unlink()
        
        # 清理 Poetry 锁文件（可选）
        poetry_lock_files = [
            self.core_dir / "poetry.lock",
            self.backend_dir / "poetry.lock"
        ]
        
        for lock_file in poetry_lock_files:
            if lock_file.exists():
                print(f"清理 Poetry 锁文件: {lock_file}")
                lock_file.unlink()
        
        # 清理前端 package-lock.json 文件
        package_lock_file = self.frontend_dir / "package-lock.json"
        if package_lock_file.exists():
            print(f"清理前端 package-lock.json 文件: {package_lock_file}")
            package_lock_file.unlink()
        
        print("清理完成!")
    
    def build(self):
        """构建前端并复制到后端"""
        print("开始构建前端...")
        
        # 检查前端目录
        if not self.frontend_dir.exists():
            print("错误: 前端目录不存在")
            return False
        
        package_json = self.frontend_dir / "package.json"
        if not package_json.exists():
            print("错误: package.json不存在")
            return False
        
        # 安装前端依赖
        print("安装前端依赖...")
        if not self.run_command("npm install", cwd=self.frontend_dir):
            print("依赖安装失败")
            return False
        
        # 构建前端
        print("构建前端...")
        if not self.run_command("npm run build", cwd=self.frontend_dir):
            print("前端构建失败")
            return False
        
        # 检查构建结果
        frontend_dist = self.frontend_dir / "dist"
        if not frontend_dist.exists():
            print("错误: 前端构建目录不存在")
            return False
        
        index_html = frontend_dist / "index.html"
        if not index_html.exists():
            print("错误: index.html不存在")
            return False
        
        # 清空后端静态目录
        backend_static = self.backend_dir / "static"
        if backend_static.exists():
            print("清空后端静态目录...")
            shutil.rmtree(backend_static)
        
        # 复制前端构建文件到后端
        print("复制前端文件到后端...")
        shutil.copytree(frontend_dist, backend_static)
        
        print("构建完成!")
        print(f"前端构建目录: {frontend_dist}")
        print(f"后端静态目录: {backend_static}")
        return True
    
    def get_pid(self) -> Optional[int]:
        """获取运行中的PID"""
        if not self.pid_file.exists():
            return None
        
        try:
            with open(self.pid_file, 'r') as f:
                pid = int(f.read().strip())
            return pid
        except (ValueError, IOError):
            return None
    
    def is_running(self) -> bool:
        """检查服务是否运行"""
        pid = self.get_pid()
        if pid is None:
            return False
        
        try:
            process = psutil.Process(pid)
            return process.is_running() and process.name().startswith('python')
        except psutil.NoSuchProcess:
            return False
    
    def start(self, port=8009):
        """后台启动服务，支持自定义端口"""
        # 启动前自动安装依赖
        if not self.install():
            print("依赖安装失败，无法启动服务")
            return False
        if self.is_running():
            print("服务已在运行中")
            return True
        backend_static = self.backend_dir / "static"
        if not backend_static.exists():
            print("前端未构建，正在构建...")
            if not self.build():
                print("构建失败，无法启动服务")
                return False
        print("启动服务...")
        try:
            cmd = f"nohup python -m uvicorn app.main:app --host 0.0.0.0 --port {port} --log-level error > ../leek.log 2>&1 & echo $! > {self.pid_file}"
            if self.run_command(cmd, cwd=self.backend_dir, capture_output=False):
                time.sleep(2)
                if self.is_running():
                    print(f"服务启动成功! 访问地址: http://localhost:{port}")
                    return True
                else:
                    print("服务启动失败")
                    return False
            else:
                print("启动命令执行失败")
                return False
        except Exception as e:
            print(f"启动服务异常: {e}")
            return False
    
    def stop(self):
        """停止服务"""
        pid = self.get_pid()
        if pid is None:
            print("服务未运行")
            return True
        
        try:
            process = psutil.Process(pid)
            print(f"停止服务 (PID: {pid})...")
            process.terminate()
            
            # 等待进程结束
            try:
                process.wait(timeout=10)
            except psutil.TimeoutExpired:
                print("强制终止进程...")
                process.kill()
            
            # 清理PID文件
            if self.pid_file.exists():
                self.pid_file.unlink()
            
            print("服务已停止")
            return True
        except psutil.NoSuchProcess:
            print("进程不存在，清理PID文件")
            if self.pid_file.exists():
                self.pid_file.unlink()
            return True
        except Exception as e:
            print(f"停止服务异常: {e}")
            return False
    
    def restart(self, port=8009):
        print("重启服务...")
        # 启动前自动安装依赖
        if not self.install():
            print("依赖安装失败，无法启动服务")
            return False
        if self.stop():
            time.sleep(2)
            return self.start(port=port)
        return False
    
    def status(self):
        """查看服务状态"""
        if self.is_running():
            pid = self.get_pid()
            print(f"服务运行中 (PID: {pid})")
            print("访问地址: http://localhost:8000")
        else:
            print("服务未运行")
        
        # 检查前端构建状态
        backend_static = self.backend_dir / "static"
        if backend_static.exists():
            print("前端已构建")
        else:
            print("前端未构建")

    def dml(self, message: str = None):
        """生成数据库迁移脚本"""
        print("生成数据库迁移脚本...")
        
        if not self.ensure_alembic_dirs():
            return False
        
        # 构建alembic命令
        cmd = "alembic revision --autogenerate"
        if message:
            cmd += f" -m '{message}'"
        
        print(f"执行迁移命令: {cmd}")
        
        # 执行alembic命令
        if self.run_command(cmd, cwd=self.backend_dir):
            print("迁移脚本生成成功!")
            return True
        else:
            print("迁移脚本生成失败!")
            return False

    def migrate(self):
        """应用数据库迁移"""
        print("应用数据库迁移...")
        
        if not self.ensure_alembic_dirs():
            return False
        
        cmd = "alembic upgrade head"
        print(f"执行迁移命令: {cmd}")
        
        if self.run_command(cmd, cwd=self.backend_dir):
            print("数据库迁移应用成功!")
            return True
        else:
            print("数据库迁移应用失败!")
            return False

    def downgrade(self, revision: str = "-1"):
        """回滚数据库迁移"""
        print(f"回滚数据库迁移到: {revision}")
        
        if not self.ensure_alembic_dirs():
            return False
        
        cmd = f"alembic downgrade {revision}"
        print(f"执行回滚命令: {cmd}")
        
        if self.run_command(cmd, cwd=self.backend_dir):
            print("数据库回滚成功!")
            return True
        else:
            print("数据库回滚失败!")
            return False

    def db_status(self):
        """查看数据库迁移状态"""
        print("查看数据库迁移状态...")
        
        if not self.ensure_alembic_dirs():
            return False
        
        cmd = "alembic current"
        print(f"执行状态查询命令: {cmd}")
        
        if self.run_command(cmd, cwd=self.backend_dir):
            print("数据库状态查询成功!")
            return True
        else:
            print("数据库状态查询失败!")
            return False

    def check_migration(self):
        """手动触发迁移检查"""
        print("手动触发迁移检查...")
        
        if not self.ensure_alembic_dirs():
            return False
        
        # 重置迁移检查状态，强制重新检查
        cmd = "python -c \"from app.db.session import reset_connection; reset_connection()\""
        print("重置连接状态...")
        self.run_command(cmd, cwd=self.backend_dir)
        
        # 执行迁移
        cmd = "alembic upgrade head"
        print(f"执行迁移命令: {cmd}")
        
        if self.run_command(cmd, cwd=self.backend_dir):
            print("迁移检查完成!")
            return True
        else:
            print("迁移检查失败!")
            return False

    def ensure_alembic_dirs(self) -> bool:
        """确保alembic相关目录存在"""
        if not self.backend_dir.exists():
            print("错误: 后端目录不存在")
            return False
        
        alembic_ini = self.backend_dir / "alembic.ini"
        if not alembic_ini.exists():
            print("错误: alembic.ini不存在")
            return False
        
        # 检查并创建migrations/versions目录
        versions_dir = self.backend_dir / "migrations" / "versions"
        if not versions_dir.exists():
            print(f"创建目录: {versions_dir}")
            versions_dir.mkdir(parents=True, exist_ok=True)
        
        return True

    def install(self):
        """使用pyproject.toml和poetry安装leek-manager和leek-core依赖，支持本地开发版"""
        import toml
        import shutil
        import importlib.metadata
        print("处理 leek-core 依赖...")
        
        # 检查 poetry 是否安装
        if not shutil.which("poetry"):
            print("未检测到 poetry，请先安装 poetry: https://python-poetry.org/docs/#installation")
            return False

        # 检查 leek-core 目录是否存在
        if not (self.core_dir / "pyproject.toml").exists():
            print(f"未找到 leek-core/pyproject.toml")
            return False

        # 然后处理 leek-manager 的依赖
        pyproject_file = self.backend_dir / "pyproject.toml"
        if not pyproject_file.exists():
            print("未找到 leek-manager/pyproject.toml")
            return False

        # 解析 pyproject.toml 获取 leek-core 依赖
        pyproject = toml.load(pyproject_file)
        deps = pyproject.get("tool", {}).get("poetry", {}).get("dependencies", {})
        core_dep = deps.get("leek-core")
        
        # 检查是否需要安装到 leek-manager
        if core_dep is None:
            print("pyproject.toml 未指定 leek-core 依赖，跳过 leek-manager 中的 leek-core 安装")
        else:
            # 获取期望的版本
            expected_version = None
            if isinstance(core_dep, dict):
                if core_dep.get("path"):
                    # 本地路径依赖，获取本地版本
                    core_path = (self.backend_dir / core_dep["path"]).resolve()
                    local_pyproject = core_path / "pyproject.toml"
                    if local_pyproject.exists():
                        local_config = toml.load(local_pyproject)
                        expected_version = local_config.get("project", {}).get("version")
                else:
                    expected_version = core_dep.get("version")
            else:
                expected_version = core_dep
            
            # 检查是否已安装到当前环境
            try:
                installed_version = importlib.metadata.version("leek-core")
                print(f"已安装 leek-core 版本: {installed_version}")
            except importlib.metadata.PackageNotFoundError:
                installed_version = None
                print("leek-core 未安装到当前环境")
            
            # 比较版本，如果未安装或版本不匹配，则安装到 leek-manager
            if installed_version is None or installed_version != expected_version:
                if installed_version is None:
                    print("leek-core 未安装到当前环境，正在安装...")
                else:
                    print(f"版本不匹配，期望: {expected_version}，已安装: {installed_version}，正在更新...")
                
                # 如果是本地路径依赖，先确保 leek-core 依赖已安装
                print(f"检测到leek-core，需要更新:{installed_version} -> {expected_version}")
                if not self.run_command("poetry install", cwd=self.core_dir):
                    print("leek-core 依赖安装失败！")
                    return False
                print("leek-core 依赖安装完成！")
                
                # 本地路径依赖，使用 pip install
                print(f"使用 pip install -e {self.core_dir} ...")
                if not self.run_command(f"pip install -e .", cwd=self.core_dir):
                    print("leek-core 本地安装失败！")
                    return False
                print("leek-core 安装完成！")
            else:
                print(f"leek-core 已是最新版本({installed_version})，无需安装")

        print("使用 poetry install 安装 leek-manager 依赖...")
        if not self.run_command("poetry install", cwd=self.backend_dir):
            print("leek-manager 依赖安装失败！")
            return False
        print("leek-manager 依赖安装完成！")
        return True

    def run(self, port=8009):
        """前台运行 leek-manager 服务（适合开发/调试）"""
        print(f"前台运行 leek-manager 服务，端口: {port} ...")
        # 启动前自动安装依赖
        if not self.install():
            print("依赖安装失败，无法启动服务")
            return False
        backend_dir = self.backend_dir
        # 检查前端是否已构建
        backend_static = backend_dir / "static"
        if not backend_static.exists():
            print("前端未构建，将没有页面， 只有api服务...")
        # 切换到后端目录并运行 uvicorn
        print(f"切换到目录: {self.backend_dir}")
        os.chdir(self.backend_dir)
        cmd = f"uvicorn app.main:app --host 0.0.0.0 --port {port} --log-level error"
        print(f"执行命令: {cmd}")
        os.execvp("uvicorn", ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", str(port), "--log-level", "error"])

def main():
    if len(sys.argv) < 2:
        print("用法: python leek.py <command>")
        print("命令:")
        print("  clean    - 清理所有构建输出")
        print("  build    - 构建前端并复制到后端")
        print("  start    - 启动服务")
        print("  stop     - 停止服务")
        print("  restart  - 重启服务")
        print("  status   - 查看服务状态")
        print("  dml      - 生成数据库迁移脚本")
        print("  migrate  - 应用数据库迁移")
        print("  downgrade - 回滚数据库迁移")
        print("  db_status - 查看数据库迁移状态")
        print("  check_migration - 手动触发迁移检查")
        print("  install   - 安装leek-manager和leek-core依赖")
        print("  run       - 前台运行 leek-manager 服务")
        return
    
    manager = LeekManager()
    command = sys.argv[1].lower()
    
    if command == "clean":
        manager.clean()
    elif command == "build":
        manager.build()
    elif command == "start":
        if len(sys.argv) < 3:
            print("用法: python leek.py start <port>")
            return
        port = int(sys.argv[2])
        manager.start(port)
    elif command == "stop":
        manager.stop()
    elif command == "restart":
        if len(sys.argv) < 3:
            print("用法: python leek.py restart <port>")
            return
        port = int(sys.argv[2])
        manager.restart(port)
    elif command == "status":
        manager.status()
    elif command == "dml":
        if len(sys.argv) < 3:
            print("用法: python leek.py dml <message>")
            return
        message = sys.argv[2]
        manager.dml(message)
    elif command == "migrate":
        manager.migrate()
    elif command == "downgrade":
        if len(sys.argv) < 3:
            print("用法: python leek.py downgrade <revision>")
            return
        revision = sys.argv[2]
        manager.downgrade(revision)
    elif command == "db_status":
        manager.db_status()
    elif command == "check_migration":
        manager.check_migration()
    elif command == "install":
        manager.install()
    elif command == "run":
        if len(sys.argv) < 3:
            print("用法: python leek.py run <port>")
            return
        port = int(sys.argv[2])
        manager.run(port)
    else:
        print(f"未知命令: {command}")
        print("可用命令: clean, build, start, stop, restart, status, dml, migrate, downgrade, db_status, check_migration, install, run")

if __name__ == "__main__":
    main() 