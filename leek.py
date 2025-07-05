#!/usr/bin/env python3
"""
Leek 项目管理脚本
统一管理前端构建、后端启动等功能
"""

import os
import sys
if sys.version_info < (3, 11):
    print("请使用Python3.11及以上版本")
    print("请使用Python3.11及以上版本")
    sys.exit(1)
import subprocess
import shutil
import time
from pathlib import Path
from typing import Optional
def ensure_module(module, package=None):
    try:
        __import__(module)
    except ImportError:
        print(f"安装依赖: {package or module}")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--force-reinstall", package or module])
        return True
    return False

installed = False
installed = ensure_module("psutil") or installed
installed = ensure_module("alembic") or installed
installed = ensure_module("poetry") or installed
if installed and os.geteuid() == 0 and not os.environ.get('LEEK_RESTARTED'):
    env = os.environ.copy()
    env['LEEK_RESTARTED'] = '1'
    print(f"重启进程: {sys.executable} {sys.argv}")
    # 修复：确保第一个参数是脚本路径，而不是命令参数
    exec_args = [sys.executable, str(Path(__file__).absolute())] + sys.argv[1:]
    os.execve(sys.executable, exec_args, env)
    
import psutil
try:
    import tomllib
except ImportError:
    # 对于Python 3.10及以下版本，使用tomli
    ensure_module("tomli", "tomli")
    import tomli as tomllib

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
        
    def run_command(self, command: str, cwd: Optional[Path] = None, capture_output: bool = True, env: Optional[dict] = None, timeout: int = 300) -> bool:
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
                    universal_newlines=True,
                    env=env
                )
                
                import time
                start_time = time.time()
                last_output_time = start_time
                while True:
                    # 检查超时（无输出超时）
                    current_time = time.time()
                    if current_time - last_output_time > timeout:
                        print(f"命令执行超时（{timeout}秒无输出），强制终止...")
                        process.terminate()
                        try:
                            process.wait(timeout=10)
                        except subprocess.TimeoutExpired:
                            process.kill()
                        return False
                    
                    output = process.stdout.readline()
                    if output == '' and process.poll() is not None:
                        break
                    if output:
                        output = output.strip()
                        last_output_time = current_time  # 重置超时计时器
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
                    text=True,
                    env=env
                )
                return result.returncode == 0
                
        except Exception as e:
            print(f"命令执行异常: {e}")
            return False
    
    def _remove(self, path: Path, name: str=None):
        if not path.exists():
            return True
        try:
            if path.is_dir():
                shutil.rmtree(path)
                print(f"清理{name or '目录'}: {path} 成功")
            else:
                path.unlink()
                print(f"清理{name or '文件'}: {path} 成功")
        except Exception as e:
            print(f"清理{name or '文件或目录'}失败: {path}, 错误: {e}")
            return False
        return True
    
    def _remove_pattern(self, pattern: str, name: str=None):
        import glob
        for path in glob.glob(pattern, recursive=True):
            path_obj = Path(path)
            self._remove(path_obj, name)

    def clean(self):
        print("开始清理构建输出...")
        
        # 清理前端构建文件
        self._remove(self.frontend_dir / "dist", "前端构建目录")
        
        # 清理前端node_modules
        self._remove(self.frontend_dir / "node_modules", "前端依赖")
        
        # 清理后端静态文件（复制的前端文件）
        self._remove(self.backend_dir / "static", "后端静态文件")
        
        # 清理Python缓存文件
        for root, dirs, files in os.walk(self.project_root):
            # 清理 __pycache__ 目录
            for dir_name in dirs[:]:  # 使用切片创建副本，避免修改迭代中的列表
                if dir_name == "__pycache__":
                    cache_dir = Path(root) / dir_name
                    self._remove(cache_dir, "Python缓存")
                    dirs.remove(dir_name)  # 从dirs中移除，避免继续遍历
            
            # 清理 .pyc 文件
            for file_name in files:
                if file_name.endswith('.pyc'):
                    pyc_file = Path(root) / file_name
                    self._remove(pyc_file, "Python字节码")
        
        # 清理其他构建文件
        build_dirs = [
            self.backend_dir / "build",
            self.backend_dir / "dist",
        ]
        
        for build_dir in build_dirs:
            self._remove(build_dir, "构建文件")
        
        # 清理 egg-info 文件（使用通配符）
        egg_info_pattern = str(self.backend_dir / "*.egg-info")
        import glob
        for path in glob.glob(egg_info_pattern):
            path_obj = Path(path)
            self._remove(path_obj, "egg-info 文件")
        
        # 清理PID文件
        self._remove(self.pid_file, "PID文件")
        
        # 清理日志文件
        specific_logs = [
            self.backend_dir / "leek.log",
            self.project_root / "leek.log",
        ]
        
        for log_file in specific_logs:
            self._remove(log_file, "日志文件")
        
        # 清理所有 .log 文件（使用通配符）
        log_patterns = [
            str(self.backend_dir / "*.log"),
            str(self.project_root / "*.log")
        ]
        
        import glob
        for pattern in log_patterns:
            for path in glob.glob(pattern):
                path_obj = Path(path)
                if path_obj.exists() and path_obj.is_file():
                    self._remove(path_obj, "日志文件")
        
        # 清理奇怪的文件（如 =1.0.0）
        strange_patterns = [
            str(self.core_dir / "=*"),
            str(self.backend_dir / "=*")
        ]
        
        import glob
        for pattern in strange_patterns:
            for path in glob.glob(pattern):
                path_obj = Path(path)
                if path_obj.exists() and path_obj.is_file():
                    self._remove(path_obj, "奇怪文件")
        
        # 清理 Poetry 锁文件（可选）
        poetry_lock_files = [
            self.core_dir / "poetry.lock",
            self.backend_dir / "poetry.lock"
        ]
        
        for lock_file in poetry_lock_files:
            self._remove(lock_file, "Poetry 锁文件")
        
        # 清理前端 package-lock.json 文件
        self._remove(self.frontend_dir / "package-lock.json", "前端 package-lock.json 文件")
        
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
            if not process.is_running():
                return False
            
            # 检查进程名或命令行参数
            process_name = process.name().lower()
            cmdline = ' '.join(process.cmdline()).lower()
            
            # 检查是否是 uvicorn 进程或者 Python 进程且包含 uvicorn
            return (process_name == 'uvicorn' or 
                   (process_name.startswith('python') or 'python' in process_name) and 'uvicorn' in cmdline)
        except psutil.NoSuchProcess:
            return False
    
    def start(self, port=8009):
        """后台启动服务，支持自定义端口"""
        # 启动前自动安装依赖
        if not self.install():
            print("依赖安装失败，无法启动服务")
            return False
        # 检查 uvicorn 是否已安装
        if not self.check_uvicorn():
            print("uvicorn 检查失败，无法启动服务")
            return False
        if self.is_running():
            print("服务已在运行中")
            return True
        print("启动服务...")
        try:
            # 使用 poetry run 来确保在正确的虚拟环境中运行
            cmd = f"nohup poetry run uvicorn app.main:app --host 0.0.0.0 --port {port} --log-level error > ../leek.log 2>&1 & echo $! > {self.pid_file}"
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
        cmd = "poetry run alembic revision --autogenerate"
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
        
        cmd = "poetry run alembic upgrade head"
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
        
        cmd = f"poetry run alembic downgrade {revision}"
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
        
        cmd = "poetry run alembic current"
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
        cmd = f"poetry run python -c \"from app.db.session import reset_connection; reset_connection()\""
        print("重置连接状态...")
        self.run_command(cmd, cwd=self.backend_dir)
        
        # 执行迁移
        cmd = "poetry run alembic upgrade head"
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

    def check_poetry(self):
        if not shutil.which("poetry"):
            print("未检测到 poetry，请先安装 poetry: https://python-poetry.org/docs/#installation")
            return False
        pyproject_file = self.backend_dir / "pyproject.toml"
        if not pyproject_file.exists():
            print("未找到 leek-manager/pyproject.toml")
            return False
        # 检查 leek-core 目录是否存在
        if not (self.core_dir / "pyproject.toml").exists():
            print(f"未找到 leek-core/pyproject.toml")
            return False
        return True
    
    def check_uvicorn(self):
        """检查 uvicorn 是否已安装"""
        try:
            import uvicorn
            return True
        except ImportError:
            print("未检测到 uvicorn，正在尝试安装...")
            # 尝试安装 uvicorn
            if self.run_command(f"{sys.executable} -m pip install uvicorn"):
                print("uvicorn 安装成功!")
                return True
            else:
                print("uvicorn 安装失败，请手动安装: pip install uvicorn")
                return False
    
    def install(self):
        with open(self.core_dir / "pyproject.toml", "rb") as f:
            local_config = tomllib.load(f)
        expected_version = local_config.get("project", {}).get("version")
        
        # 改进版本检测逻辑，考虑虚拟环境隔离问题
        installed_version = None
        
        # 方法1: 尝试在当前Python环境中检测
        try:
            installed_version = importlib.metadata.version("leek-core")
        except importlib.metadata.PackageNotFoundError:
            pass
        
        # 方法2: 如果方法1失败，尝试在poetry虚拟环境中检测
        if installed_version is None:
            try:
                result = subprocess.run(
                    ["poetry", "run", "python", "-c", "import importlib.metadata; print(importlib.metadata.version('leek-core'))"],
                    cwd=self.backend_dir,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                if result.returncode == 0:
                    installed_version = result.stdout.strip()
            except Exception:
                pass
        
        # 方法3: 如果前两种方法都失败，检查是否在开发模式下安装
        if installed_version is None:
            try:
                # 检查leek-core是否以开发模式安装
                result = subprocess.run(
                    ["poetry", "run", "python", "-c", "import leek_core; print('installed')"],
                    cwd=self.backend_dir,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                if result.returncode == 0:
                    # 如果能导入，说明已安装，使用期望版本作为已安装版本
                    installed_version = expected_version
            except Exception:
                pass
        
        # 如果仍然检测不到版本，或者版本不匹配，则重新安装
        if installed_version is None or installed_version != expected_version:
            print(f"更新leek-core:{installed_version or '未安装'} -> {expected_version}")
            # 本地路径依赖，使用 poetry run pip install 确保在虚拟环境中安装
            if not self.run_command(f"poetry run pip install -e {self.core_dir}", cwd=self.backend_dir):
                print("leek-core 本地安装失败！")
                return False
            print("leek-core 安装完成！")
        print("开始安装依赖（可能需要几分钟）...")
        if not self.run_command(f"poetry env use {sys.executable} && poetry install --no-interaction", cwd=self.backend_dir):
            print(f"leek-manager 依赖安装失败, 请检查!")
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
        # 检查 uvicorn 是否已安装
        if not self.check_uvicorn():
            print("uvicorn 检查失败，无法启动服务")
            return False
        backend_dir = self.backend_dir
        # 检查前端是否已构建
        backend_static = backend_dir / "static"
        if not backend_static.exists():
            print("前端未构建，将没有页面， 只有api服务...")
        # 切换到后端目录并运行 uvicorn
        print(f"切换到目录: {self.backend_dir}")
        os.chdir(self.backend_dir)
        # 使用 poetry run 来确保在正确的虚拟环境中运行
        cmd = f"poetry run uvicorn app.main:app --host 0.0.0.0 --port {port}"
        print(f"执行命令: {cmd}")
        os.execvp("poetry", ["poetry", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", str(port)])

def _print_help():
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
    print("  help      - 显示帮助信息")
def main():
    if len(sys.argv) < 2:
        _print_help()
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
    elif command == "help":
        _print_help()
    else:
        print(f"未知命令: {command}")
        _print_help()

if __name__ == "__main__":
    main() 