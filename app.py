"""
Flask主应用 - 统一管理三个Streamlit应用
"""

import os
import sys

# 【修复】尽早设置环境变量，确保所有模块都使用无缓冲模式
os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['PYTHONUTF8'] = '1'
os.environ['PYTHONUNBUFFERED'] = '1'  # 禁用Python输出缓冲，确保日志实时输出

import subprocess
import time
import threading
import uuid
from datetime import datetime
from queue import Queue
from flask import Flask, render_template, request, jsonify, Response
from flask_socketio import SocketIO, emit
import atexit
import requests
from loguru import logger
import importlib
from pathlib import Path
from MindSpider.main import MindSpider

# 导入ReportEngine
try:
    from ReportEngine.flask_interface import report_bp, initialize_report_engine
    REPORT_ENGINE_AVAILABLE = True
except ImportError as e:
    logger.error(f"ReportEngine导入失败: {e}")
    REPORT_ENGINE_AVAILABLE = False

app = Flask(__name__)
app.config['SECRET_KEY'] = 'Dedicated-to-creating-a-concise-and-versatile-public-opinion-analysis-platform'
socketio = SocketIO(app, cors_allowed_origins="*")

# eventlet 在客户端主动断开时偶尔会抛出 ConnectionAbortedError，这里做一次防御性包裹，
# 避免无意义的堆栈污染日志（仅在 eventlet 可用时启用）。
def _patch_eventlet_disconnect_logging():
    try:
        import eventlet.wsgi  # type: ignore
    except Exception as exc:  # pragma: no cover - 仅在生产环境有效
        logger.debug(f"eventlet 不可用，跳过断开补丁: {exc}")
        return

    try:
        original_finish = eventlet.wsgi.HttpProtocol.finish  # type: ignore[attr-defined]
    except Exception as exc:  # pragma: no cover
        logger.debug(f"eventlet 缺少 HttpProtocol.finish，跳过断开补丁: {exc}")
        return

    def _safe_finish(self, *args, **kwargs):  # pragma: no cover - 运行时才会触发
        try:
            return original_finish(self, *args, **kwargs)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError) as exc:
            try:
                environ = getattr(self, 'environ', {}) or {}
                method = environ.get('REQUEST_METHOD', '')
                path = environ.get('PATH_INFO', '')
                logger.warning(f"客户端已主动断开，忽略异常: {method} {path} ({exc})")
            except Exception:
                logger.warning(f"客户端已主动断开，忽略异常: {exc}")
            return

    eventlet.wsgi.HttpProtocol.finish = _safe_finish  # type: ignore[attr-defined]
    logger.info("已对 eventlet 连接中断进行安全防护")

_patch_eventlet_disconnect_logging()

# 注册ReportEngine Blueprint
if REPORT_ENGINE_AVAILABLE:
    app.register_blueprint(report_bp, url_prefix='/api/report')
    logger.info("ReportEngine接口已注册")
else:
    logger.info("ReportEngine不可用，跳过接口注册")

# 创建日志目录
LOG_DIR = Path('logs')
LOG_DIR.mkdir(exist_ok=True)

CONFIG_MODULE_NAME = 'config'
CONFIG_FILE_PATH = Path(__file__).resolve().parent / 'config.py'
CONFIG_KEYS = [
    'HOST',
    'PORT',
    'DB_DIALECT',
    'DB_HOST',
    'DB_PORT',
    'DB_USER',
    'DB_PASSWORD',
    'DB_NAME',
    'DB_CHARSET',
    'INSIGHT_ENGINE_API_KEY',
    'INSIGHT_ENGINE_BASE_URL',
    'INSIGHT_ENGINE_MODEL_NAME',
    'QUERY_ENGINE_API_KEY',
    'QUERY_ENGINE_BASE_URL',
    'QUERY_ENGINE_MODEL_NAME',
    'REPORT_ENGINE_API_KEY',
    'REPORT_ENGINE_BASE_URL',
    'REPORT_ENGINE_MODEL_NAME',
    'KEYWORD_OPTIMIZER_API_KEY',
    'KEYWORD_OPTIMIZER_BASE_URL',
    'KEYWORD_OPTIMIZER_MODEL_NAME',
    'TAVILY_API_KEY',
    'SEARCH_TOOL_TYPE',
    'BOCHA_WEB_SEARCH_API_KEY',
    'ANSPIRE_API_KEY',
    'AUTO_QUERY_TOPICS'
]


def _load_config_module():
    """Load or reload the config module to ensure latest values are available."""
    importlib.invalidate_caches()
    module = sys.modules.get(CONFIG_MODULE_NAME)
    try:
        if module is None:
            module = importlib.import_module(CONFIG_MODULE_NAME)
        else:
            module = importlib.reload(module)
    except ModuleNotFoundError:
        return None
    return module


def read_config_values():
    """Return the current configuration values that are exposed to the frontend."""
    try:
        # 重新加载配置以获取最新的 Settings 实例
        from config import reload_settings, settings
        reload_settings()
        
        values = {}
        for key in CONFIG_KEYS:
            # 从 Pydantic Settings 实例读取值
            value = getattr(settings, key, None)
            # Convert to string for uniform handling on the frontend.
            if value is None:
                values[key] = ''
            else:
                values[key] = str(value)
        return values
    except Exception as exc:
        logger.exception(f"读取配置失败: {exc}")
        return {}


def _serialize_config_value(value):
    """Serialize Python values back to a config.py assignment-friendly string."""
    if isinstance(value, bool):
        return 'True' if value else 'False'
    if isinstance(value, (int, float)):
        return str(value)
    if value is None:
        return 'None'

    value_str = str(value)
    escaped = value_str.replace('\\', '\\\\').replace('"', '\\"')
    return f'"{escaped}"'


def write_config_values(updates):
    """Persist configuration updates to .env file (Pydantic Settings source)."""
    from pathlib import Path
    
    # 确定 .env 文件路径（与 config.py 中的逻辑一致）
    project_root = Path(__file__).resolve().parent
    cwd_env = Path.cwd() / ".env"
    env_file_path = cwd_env if cwd_env.exists() else (project_root / ".env")
    
    # 读取现有的 .env 文件内容
    env_lines = []
    env_key_indices = {}  # 记录每个键在文件中的索引位置
    if env_file_path.exists():
        env_lines = env_file_path.read_text(encoding='utf-8').splitlines()
        # 提取已存在的键及其索引
        for i, line in enumerate(env_lines):
            line_stripped = line.strip()
            if line_stripped and not line_stripped.startswith('#'):
                if '=' in line_stripped:
                    key = line_stripped.split('=')[0].strip()
                    env_key_indices[key] = i
    
    # 更新或添加配置项
    for key, raw_value in updates.items():
        # 格式化值用于 .env 文件（不需要引号，除非是字符串且包含空格）
        if raw_value is None or raw_value == '':
            env_value = ''
        elif isinstance(raw_value, (int, float)):
            env_value = str(raw_value)
        elif isinstance(raw_value, bool):
            env_value = 'True' if raw_value else 'False'
        else:
            value_str = str(raw_value)
            # 如果包含空格或特殊字符，需要引号
            if ' ' in value_str or '\n' in value_str or '#' in value_str:
                escaped = value_str.replace('\\', '\\\\').replace('"', '\\"')
                env_value = f'"{escaped}"'
            else:
                env_value = value_str
        
        # 更新或添加配置项
        if key in env_key_indices:
            # 更新现有行
            env_lines[env_key_indices[key]] = f'{key}={env_value}'
        else:
            # 添加新行到文件末尾
            env_lines.append(f'{key}={env_value}')
    
    # 写入 .env 文件
    env_file_path.parent.mkdir(parents=True, exist_ok=True)
    env_file_path.write_text('\n'.join(env_lines) + '\n', encoding='utf-8')
    
    # 重新加载配置模块（这会重新读取 .env 文件并创建新的 Settings 实例）
    _load_config_module()


system_state_lock = threading.Lock()
system_state = {
    'started': False,
    'starting': False,
    'shutdown_in_progress': False
}


def _set_system_state(*, started=None, starting=None):
    """Safely update the cached system state flags."""
    with system_state_lock:
        if started is not None:
            system_state['started'] = started
        if starting is not None:
            system_state['starting'] = starting


def _get_system_state():
    """Return a shallow copy of the system state flags."""
    with system_state_lock:
        return system_state.copy()


def _prepare_system_start():
    """Mark the system as starting if it is not already running or starting."""
    with system_state_lock:
        if system_state['started']:
            return False, '系统已启动'
        if system_state['starting']:
            return False, '系统正在启动'
        system_state['starting'] = True
        return True, None

def _mark_shutdown_requested():
    """标记关机已请求；若已有关机流程则返回 False。"""
    with system_state_lock:
        if system_state.get('shutdown_in_progress'):
            return False
        system_state['shutdown_in_progress'] = True
        return True


def initialize_system_components():
    """启动所有依赖组件（Streamlit 子应用、ReportEngine）。"""
    logs = []
    errors = []

    spider = MindSpider()
    if spider.initialize_database():
        logger.info("数据库初始化成功")
    else:
        logger.error("数据库初始化失败")

    for app_name, script_path in STREAMLIT_SCRIPTS.items():
        logs.append(f"检查文件: {script_path}")
        if os.path.exists(script_path):
            success, message = start_streamlit_app(app_name, script_path, processes[app_name]['port'])
            logs.append(f"{app_name}: {message}")
            if success:
                startup_success, startup_message = wait_for_app_startup(app_name, 30)
                logs.append(f"{app_name} 启动检查: {startup_message}")
                if not startup_success:
                    errors.append(f"{app_name} 启动失败: {startup_message}")
            else:
                errors.append(f"{app_name} 启动失败: {message}")
        else:
            msg = f"文件不存在: {script_path}"
            logs.append(f"错误: {msg}")
            errors.append(f"{app_name}: {msg}")

    if REPORT_ENGINE_AVAILABLE:
        try:
            if initialize_report_engine():
                logs.append("ReportEngine 初始化成功")
            else:
                msg = "ReportEngine 初始化失败"
                logs.append(msg)
                errors.append(msg)
        except Exception as exc:  # pragma: no cover
            msg = f"ReportEngine 初始化异常: {exc}"
            logs.append(msg)
            errors.append(msg)

    if errors:
        cleanup_processes()
        return False, logs, errors

    return True, logs, []


# 全局变量存储进程信息
processes = {
    'insight': {'process': None, 'port': 8501, 'status': 'stopped', 'output': [], 'log_file': None, 'start_time': None, 'healthcheck_started_at': None},
    'query': {'process': None, 'port': 8503, 'status': 'stopped', 'output': [], 'log_file': None, 'start_time': None, 'healthcheck_started_at': None}
}

STREAMLIT_SCRIPTS = {
    'insight': 'SingleEngineApp/insight_engine_streamlit_app.py',
    # 'media': 'SingleEngineApp/media_engine_streamlit_app.py',  # Media Agent 已屏蔽
    'query': 'SingleEngineApp/query_engine_streamlit_app.py'
}

def _log_shutdown_step(message: str):
    """统一记录关机步骤，便于排查。"""
    logger.info(f"[Shutdown] {message}")


def _describe_running_children():
    """列出当前存活的子进程。"""
    running = []
    for name, info in processes.items():
        proc = info.get('process')
        if proc is not None and proc.poll() is None:
            port_desc = f", port={info.get('port')}" if info.get('port') else ""
            running.append(f"{name}(pid={proc.pid}{port_desc})")
    return running

# 输出队列
output_queues = {
    'insight': Queue(),
    'query': Queue()
}

def write_log_to_file(app_name, line):
    """将日志写入文件"""
    try:
        log_file_path = LOG_DIR / f"{app_name}.log"
        with open(log_file_path, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
            f.flush()
    except Exception as e:
        logger.error(f"Error writing log for {app_name}: {e}")

def read_log_from_file(app_name, tail_lines=None):
    """从文件读取日志"""
    try:
        log_file_path = LOG_DIR / f"{app_name}.log"
        if not log_file_path.exists():
            return []
        
        with open(log_file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            lines = [line.rstrip('\n\r') for line in lines if line.strip()]
            
            if tail_lines:
                return lines[-tail_lines:]
            return lines
    except Exception as e:
        logger.exception(f"Error reading log for {app_name}: {e}")
        return []

def read_process_output(process, app_name):
    """读取进程输出并写入文件"""
    import select
    import sys
    
    while True:
        try:
            if process.poll() is not None:
                # 进程结束，读取剩余输出
                remaining_output = process.stdout.read()
                if remaining_output:
                    lines = remaining_output.decode('utf-8', errors='replace').split('\n')
                    for line in lines:
                        line = line.strip()
                        if line:
                            timestamp = datetime.now().strftime('%H:%M:%S')
                            formatted_line = f"[{timestamp}] {line}"
                            write_log_to_file(app_name, formatted_line)
                            socketio.emit('console_output', {
                                'app': app_name,
                                'line': formatted_line
                            })
                break
            
            # 使用非阻塞读取
            if sys.platform == 'win32':
                # Windows下使用不同的方法
                output = process.stdout.readline()
                if output:
                    line = output.decode('utf-8', errors='replace').strip()
                    if line:
                        timestamp = datetime.now().strftime('%H:%M:%S')
                        formatted_line = f"[{timestamp}] {line}"
                        
                        # 写入日志文件
                        write_log_to_file(app_name, formatted_line)
                        
                        # 发送到前端
                        socketio.emit('console_output', {
                            'app': app_name,
                            'line': formatted_line
                        })
                else:
                    # 没有输出时短暂休眠
                    time.sleep(0.1)
            else:
                # Unix系统使用select
                ready, _, _ = select.select([process.stdout], [], [], 0.1)
                if ready:
                    output = process.stdout.readline()
                    if output:
                        line = output.decode('utf-8', errors='replace').strip()
                        if line:
                            timestamp = datetime.now().strftime('%H:%M:%S')
                            formatted_line = f"[{timestamp}] {line}"
                            
                            # 写入日志文件
                            write_log_to_file(app_name, formatted_line)
                            
                            # 发送到前端
                            socketio.emit('console_output', {
                                'app': app_name,
                                'line': formatted_line
                            })
                            
        except Exception as e:
            error_msg = f"Error reading output for {app_name}: {e}"
            logger.exception(error_msg)
            write_log_to_file(app_name, f"[{datetime.now().strftime('%H:%M:%S')}] {error_msg}")
            break

def start_streamlit_app(app_name, script_path, port):
    """启动Streamlit应用"""
    try:
        if processes[app_name]['process'] is not None:
            return False, "应用已经在运行"
        
        # 检查文件是否存在
        if not os.path.exists(script_path):
            return False, f"文件不存在: {script_path}"
        
        # 清空之前的日志文件
        log_file_path = LOG_DIR / f"{app_name}.log"
        if log_file_path.exists():
            log_file_path.unlink()
        
        # 创建启动日志
        start_msg = f"[{datetime.now().strftime('%H:%M:%S')}] 启动 {app_name} 应用..."
        write_log_to_file(app_name, start_msg)
        
        cmd = [
            sys.executable, '-m', 'streamlit', 'run',
            script_path,
            '--server.port', str(port),
            '--server.headless', 'true',
            '--browser.gatherUsageStats', 'false',
            # '--logger.level', 'debug',  # 增加日志详细程度
            '--logger.level', 'info',
            '--server.enableCORS', 'false'
        ]
        
        # 设置环境变量确保UTF-8编码和减少缓冲
        env = os.environ.copy()
        env.update({
            'PYTHONIOENCODING': 'utf-8',
            'PYTHONUTF8': '1',
            'LANG': 'en_US.UTF-8',
            'LC_ALL': 'en_US.UTF-8',
            'PYTHONUNBUFFERED': '1',  # 禁用Python缓冲
            'STREAMLIT_BROWSER_GATHER_USAGE_STATS': 'false'
        })
        
        # 使用当前工作目录而不是脚本目录
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=0,  # 无缓冲
            universal_newlines=False,
            cwd=os.getcwd(),
            env=env,
            encoding=None,  # 让我们手动处理编码
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
        )
        
        processes[app_name]['process'] = process
        processes[app_name]['status'] = 'starting'
        processes[app_name]['output'] = []
        processes[app_name]['start_time'] = time.time()
        processes[app_name]['healthcheck_started_at'] = time.time()
        
        # 启动输出读取线程
        output_thread = threading.Thread(
            target=read_process_output,
            args=(process, app_name),
            daemon=True
        )
        output_thread.start()
        
        return True, f"{app_name} 应用启动中..."
        
    except Exception as e:
        error_msg = f"启动失败: {str(e)}"
        write_log_to_file(app_name, f"[{datetime.now().strftime('%H:%M:%S')}] {error_msg}")
        return False, error_msg

def stop_streamlit_app(app_name):
    """停止Streamlit应用"""
    try:
        process = processes[app_name]['process']
        if process is None:
            _log_shutdown_step(f"{app_name} 未运行，跳过停止")
            return False, "应用未运行"
        
        try:
            pid = process.pid
        except Exception:
            pid = 'unknown'

        _log_shutdown_step(f"正在停止 {app_name} (pid={pid})")
        process.terminate()
        
        # 等待进程结束
        try:
            process.wait(timeout=5)
            _log_shutdown_step(f"{app_name} 退出完成，returncode={process.returncode}")
        except subprocess.TimeoutExpired:
            _log_shutdown_step(f"{app_name} 终止超时，尝试强制结束 (pid={pid})")
            process.kill()
            process.wait()
            _log_shutdown_step(f"{app_name} 已强制结束，returncode={process.returncode}")
        
        processes[app_name]['process'] = None
        processes[app_name]['status'] = 'stopped'
        processes[app_name]['start_time'] = None
        processes[app_name]['healthcheck_started_at'] = None
        
        return True, f"{app_name} 应用已停止"
        
    except Exception as e:
        _log_shutdown_step(f"{app_name} 停止失败: {e}")
        return False, f"停止失败: {str(e)}"

HEALTHCHECK_PATH = "/_stcore/health"
HEALTHCHECK_PROXIES = {'http': None, 'https': None}
HEALTHCHECK_GRACE_SECONDS = 15


def _build_healthcheck_url(port):
    return f"http://127.0.0.1:{port}{HEALTHCHECK_PATH}"


def _healthcheck_grace_active(app_name: str) -> bool:
    started_at = processes.get(app_name, {}).get('healthcheck_started_at')
    if not started_at:
        return False
    return (time.time() - started_at) < HEALTHCHECK_GRACE_SECONDS


def _log_healthcheck_failure(app_name: str, exc: Exception):
    if _healthcheck_grace_active(app_name):
        logger.debug(f"正在启动{app_name}，请等待")
        return
    logger.warning(f"{app_name} 健康检查失败: {exc}")


def check_app_status():
    """检查应用状态"""
    for app_name, info in processes.items():
        if info['process'] is not None:
            if info['process'].poll() is None:
                # 进程仍在运行，检查端口是否可访问
                try:
                    response = requests.get(
                        _build_healthcheck_url(info['port']),
                        timeout=2,
                        proxies=HEALTHCHECK_PROXIES
                    )
                    if response.status_code == 200:
                        info['status'] = 'running'
                    else:
                        info['status'] = 'starting'
                except Exception as exc:
                    _log_healthcheck_failure(app_name, exc)
                    info['status'] = 'starting'
            else:
                # 进程已结束
                info['process'] = None
                info['status'] = 'stopped'
                info['start_time'] = None
                info['healthcheck_started_at'] = None

def wait_for_app_startup(app_name, max_wait_time=90):
    """等待应用启动完成"""
    import time
    start_time = time.time()
    while time.time() - start_time < max_wait_time:
        info = processes[app_name]
        if info['process'] is None:
            return False, "进程已停止"
        
        if info['process'].poll() is not None:
            return False, "进程启动失败"
        
        try:
            response = requests.get(
                _build_healthcheck_url(info['port']),
                timeout=2,
                proxies=HEALTHCHECK_PROXIES
            )
            if response.status_code == 200:
                info['status'] = 'running'
                return True, "启动成功"
        except Exception as exc:
            _log_healthcheck_failure(app_name, exc)

        time.sleep(1)

    return False, "启动超时"

def cleanup_processes():
    """清理所有进程"""
    _log_shutdown_step("开始串行清理子进程")
    for app_name in STREAMLIT_SCRIPTS:
        stop_streamlit_app(app_name)

    _log_shutdown_step("子进程清理完成")
    _set_system_state(started=False, starting=False)

def cleanup_processes_concurrent(timeout: float = 6.0):
    """并发清理所有子进程，超时后强制杀掉残留进程。"""
    _log_shutdown_step(f"开始并发清理子进程（超时 {timeout}s）")
    _log_shutdown_step("仅终止当前控制台启动并记录的子进程，不做端口扫描")
    running_before = _describe_running_children()
    if running_before:
        _log_shutdown_step("当前存活子进程: " + ", ".join(running_before))
    else:
        _log_shutdown_step("未检测到存活子进程，仍将发送关闭指令")

    threads = []

    # 并发关闭 Streamlit 子进程
    for app_name in STREAMLIT_SCRIPTS:
        t = threading.Thread(target=stop_streamlit_app, args=(app_name,), daemon=True)
        threads.append(t)
        t.start()

    # 等待所有线程完成，最多 timeout 秒
    end_time = time.time() + timeout
    for t in threads:
        remaining = end_time - time.time()
        if remaining <= 0:
            break
        t.join(timeout=remaining)

    # 二次检查：强制杀掉仍存活的子进程
    for app_name in STREAMLIT_SCRIPTS:
        proc = processes[app_name]['process']
        if proc is not None and proc.poll() is None:
            try:
                _log_shutdown_step(f"{app_name} 进程仍存活，触发二次终止 (pid={proc.pid})")
                proc.terminate()
                proc.wait(timeout=1)
            except Exception:
                try:
                    _log_shutdown_step(f"{app_name} 二次终止失败，尝试kill (pid={proc.pid})")
                    proc.kill()
                    proc.wait(timeout=1)
                except Exception:
                    logger.warning(f"{app_name} 进程强制退出失败，继续关机")
            finally:
                processes[app_name]['process'] = None
                processes[app_name]['status'] = 'stopped'
                processes[app_name]['start_time'] = None

    _log_shutdown_step("并发清理结束，标记系统未启动")
    _set_system_state(started=False, starting=False)

def _schedule_server_shutdown(delay_seconds: float = 0.1):
    """在清理完成后尽快退出，避免阻塞当前请求。"""
    def _shutdown():
        time.sleep(delay_seconds)
        try:
            socketio.stop()
        except Exception as exc:  # pragma: no cover
            logger.warning(f"SocketIO 停止时异常，继续退出: {exc}")
        _log_shutdown_step("SocketIO 停止指令已发送，即将退出主进程")
        os._exit(0)

    threading.Thread(target=_shutdown, daemon=True).start()

def _start_async_shutdown(cleanup_timeout: float = 3.0):
    """异步触发清理并强制退出，避免HTTP请求阻塞。"""
    _log_shutdown_step(f"收到关机指令，启动异步清理（超时 {cleanup_timeout}s）")

    def _force_exit():
        _log_shutdown_step("关机超时，触发强制退出")
        os._exit(0)

    # 硬超时保护，即便清理线程异常也能退出
    hard_timeout = cleanup_timeout + 2.0
    force_timer = threading.Timer(hard_timeout, _force_exit)
    force_timer.daemon = True
    force_timer.start()

    def _cleanup_and_exit():
        try:
            cleanup_processes_concurrent(timeout=cleanup_timeout)
        except Exception as exc:  # pragma: no cover
            logger.exception(f"关机清理异常: {exc}")
        finally:
            _log_shutdown_step("清理线程结束，调度主进程退出")
            _schedule_server_shutdown(0.05)

    threading.Thread(target=_cleanup_and_exit, daemon=True).start()

# 注册清理函数
atexit.register(cleanup_processes)

@app.route('/')
def index():
    """主页"""
    return render_template('index.html')

@app.route('/api/status')
def get_status():
    """获取所有应用状态"""
    check_app_status()
    return jsonify({
        app_name: {
            'status': info['status'],
            'port': info['port'],
            'output_lines': len(info['output']),
            'start_time': info.get('start_time')
        }
        for app_name, info in processes.items()
    })

@app.route('/api/start/<app_name>')
def start_app(app_name):
    """启动指定应用"""
    if app_name not in processes:
        return jsonify({'success': False, 'message': '未知应用'})

    script_path = STREAMLIT_SCRIPTS.get(app_name)
    if not script_path:
        return jsonify({'success': False, 'message': '该应用不支持启动操作'})

    success, message = start_streamlit_app(
        app_name,
        script_path,
        processes[app_name]['port']
    )

    if success:
        # 等待应用启动
        startup_success, startup_message = wait_for_app_startup(app_name, 15)
        if not startup_success:
            message += f" 但启动检查失败: {startup_message}"
    
    return jsonify({'success': success, 'message': message})

@app.route('/api/stop/<app_name>')
def stop_app(app_name):
    """停止指定应用"""
    if app_name not in processes:
        return jsonify({'success': False, 'message': '未知应用'})

    success, message = stop_streamlit_app(app_name)
    return jsonify({'success': success, 'message': message})

@app.route('/api/output/<app_name>')
def get_output(app_name):
    """获取应用输出"""
    if app_name not in processes:
        return jsonify({'success': False, 'message': '未知应用'})

    output_lines = read_log_from_file(app_name)

    return jsonify({
        'success': True,
        'output': output_lines
    })

@app.route('/api/test_log/<app_name>')
def test_log(app_name):
    """测试日志写入功能"""
    if app_name not in processes:
        return jsonify({'success': False, 'message': '未知应用'})
    
    # 写入测试消息
    test_msg = f"[{datetime.now().strftime('%H:%M:%S')}] 测试日志消息 - {datetime.now()}"
    write_log_to_file(app_name, test_msg)
    
    # 通过Socket.IO发送
    socketio.emit('console_output', {
        'app': app_name,
        'line': test_msg
    })
    
    return jsonify({
        'success': True,
        'message': f'测试消息已写入 {app_name} 日志'
    })


@app.route('/api/search', methods=['POST'])
def search():
    """统一搜索接口"""
    data = request.get_json()
    query = data.get('query', '').strip()
    
    if not query:
        return jsonify({'success': False, 'message': '搜索查询不能为空'})

    # 检查哪些应用正在运行
    check_app_status()
    running_apps = [name for name, info in processes.items() if info['status'] == 'running']
    
    if not running_apps:
        return jsonify({'success': False, 'message': '没有运行中的应用'})
    
    # 向运行中的应用发送搜索请求
    results = {}
    api_ports = {'insight': 8501, 'query': 8503}
    
    for app_name in running_apps:
        try:
            api_port = api_ports[app_name]
            # 调用Streamlit应用的API端点
            response = requests.post(
                f"http://localhost:{api_port}/api/search",
                json={'query': query},
                timeout=10
            )
            if response.status_code == 200:
                results[app_name] = response.json()
            else:
                results[app_name] = {'success': False, 'message': 'API调用失败'}
        except Exception as e:
            results[app_name] = {'success': False, 'message': str(e)}
    
    # 搜索完成后可以选择停止监控，或者让它继续运行以捕获后续的处理日志
    # 这里我们让监控继续运行，用户可以通过其他接口手动停止
    
    return jsonify({
        'success': True,
        'query': query,
        'results': results
    })


# 全局搜索状态（页面刷新后保留进度）
search_state = {
    'running': False,
    'topics': [],
    'current_index': 0,
    'start_time': None,
    'results': {},
}

# 收集所有搜索结果（用于最终汇总）
all_search_results = {}  # {topic: {query_results: [...], insight_report: str}}
summary_generated = False
summary_report = ""


@app.route('/api/search-state', methods=['GET'])
def search_state_api():
    """返回当前搜索进度状态"""
    return jsonify({
        'success': True,
        'running': search_state['running'],
        'current_index': search_state['current_index'],
        'total': len(search_state['topics']),
        'topics': search_state['topics'],
        'start_time': search_state['start_time'].isoformat() if search_state['start_time'] else None,
        'results': search_state['results'],
    })


@app.route('/api/search-progress', methods=['POST'])
def update_search_progress():
    """前端上报搜索进度"""
    data = request.get_json()
    index = data.get('index', 0)
    topic = data.get('topic', '')
    result = data.get('result', {})
    search_state['current_index'] = index
    if result:
        search_state['results'][topic] = result
    return jsonify({'success': True})


@app.route('/api/insight-search', methods=['POST'])
def insight_search():
    """深度搜索 — 直接调用 InsightEngine Agent，完整 LLM 分析管道"""
    data = request.get_json()
    query = data.get('query', '').strip()
    if not query:
        return jsonify({'success': False, 'message': '查询不能为空'})

    task_id = str(uuid.uuid4())[:8]
    thread = threading.Thread(target=_run_insight_search, args=(task_id, query), daemon=True)
    thread.start()

    return jsonify({'success': True, 'task_id': task_id, 'message': 'Insight 深度搜索已启动'})


def _run_insight_search(task_id, query):
    """后台运行 Insight 深度搜索"""
    try:
        socketio.emit('insight_progress', {'task_id': task_id, 'status': 'starting', 'query': query, 'message': '正在初始化...'})
        from InsightEngine.agent import DeepSearchAgent
        from InsightEngine.utils.config import settings as insight_settings

        agent = DeepSearchAgent(insight_settings)
        socketio.emit('insight_progress', {'task_id': task_id, 'status': 'running', 'query': query, 'message': '正在生成报告结构...'})
        report = agent.research(query, save_report=True)
        # 保存到汇总结果
        if query not in all_search_results:
            all_search_results[query] = {'query_results': [], 'insight_report': ''}
        all_search_results[query]['insight_report'] = report or ''
        socketio.emit('insight_progress', {'task_id': task_id, 'status': 'completed', 'query': query, 'message': 'Insight 分析完成', 'report': report[:2000] if report else ''})
        logger.info(f"Insight 深度搜索完成: {query}")
    except Exception as e:
        logger.error(f"Insight 搜索失败: {e}")
        socketio.emit('insight_progress', {'task_id': task_id, 'status': 'error', 'query': query, 'message': str(e)})


@app.route('/api/quick-search', methods=['POST'])
def quick_search():
    """快速搜索 — 直接使用 Tavily API，不经过 Streamlit，秒级返回"""
    data = request.get_json()
    query = data.get('query', '').strip()
    if not query:
        return jsonify({'success': False, 'message': '查询不能为空'})

    try:
        from tavily import TavilyClient
        from config import settings
        client = TavilyClient(api_key=settings.TAVILY_API_KEY or '')
        result = client.search(query, max_results=5, search_depth='basic')
        results = []
        for r in result.get('results', []):
            results.append({
                'title': r.get('title', ''),
                'url': r.get('url', ''),
                'content': (r.get('content', '') or '')[:300],
            })
        # 存储结果用于汇总
        all_search_results[query] = {'query_results': results, 'insight_report': ''}
        return jsonify({'success': True, 'query': query, 'results': results, 'count': len(results)})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


def _build_topics_text(include_insight=False):
    """构建用于 LLM 汇总的主题文本"""
    topics_summary = []
    for topic, data in all_search_results.items():
        urls = [r.get('url', '') for r in data.get('query_results', []) if r.get('url')]
        titles = [r.get('title', '') for r in data.get('query_results', []) if r.get('title')]
        entry = f"### {topic}\n搜索结果数: {len(data.get('query_results', []))}\n"
        entry += "\n".join(f"- [{title}]({url})" for title, url in zip(titles[:3], urls[:3]))
        if include_insight and data.get('insight_report'):
            entry += f"\n深度分析: {(data['insight_report'] or '')[:300]}"
        topics_summary.append(entry)
    return topics_summary


def _save_report_html(path, name, report_md, title):
    """将 Markdown 报告保存为 HTML 文件"""
    html = f"""<!DOCTYPE html><html lang=\"zh-CN\"><head><meta charset=\"UTF-8\">
<title>{title}</title><style>body{{font-family:Arial,sans-serif;max-width:900px;margin:40px auto;padding:20px;line-height:1.8;color:#333}}
h2{{color:#1565c0;border-bottom:2px solid #eee;padding-bottom:8px}}h3{{color:#333}}a{{color:#1976d2}}
.report-meta{{color:#888;font-size:13px;margin-bottom:24px}}</style></head><body>
<h1>{title}</h1><div class=\"report-meta\">生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
{report_md.replace(chr(10), '<br>')}
</body></html>"""
    (path / f'{name}.html').write_text(html, encoding='utf-8')


@app.route('/api/download/<path:filepath>')
def download_report(filepath):
    """下载报告文件（支持子目录）"""
    from flask import send_file
    fullpath = Path('final_reports') / filepath
    if not fullpath.exists():
        return jsonify({'success': False, 'message': '文件不存在'}), 404
    mimetype = 'text/html' if filepath.endswith('.html') else 'text/markdown'
    return send_file(str(fullpath.absolute()), mimetype=mimetype, as_attachment=True, download_name=Path(filepath).name)


def _call_llm_summary(prompt, max_tokens=2000):
    """通用 LLM 汇总调用"""
    from openai import OpenAI
    from config import settings
    client = OpenAI(
        api_key=settings.REPORT_ENGINE_API_KEY or settings.INSIGHT_ENGINE_API_KEY,
        base_url=settings.REPORT_ENGINE_BASE_URL or settings.INSIGHT_ENGINE_BASE_URL,
    )
    model = settings.REPORT_ENGINE_MODEL_NAME or 'deepseek-chat'
    response = client.chat.completions.create(
        model=model, messages=[{'role': 'user', 'content': prompt}], max_tokens=max_tokens)
    return response.choices[0].message.content or ''


@app.route('/api/summary-v1', methods=['POST'])
def summary_v1():
    """舆情简报 v1 — 仅用 Quick-search 结果，秒级生成"""
    start = time.time()
    if not all_search_results:
        return jsonify({'success': False, 'message': '没有搜索结果'})

    topics_text = "\n\n".join(_build_topics_text(include_insight=False))
    today = datetime.now().strftime('%Y年%m月%d日')
    prompt = f"""你是舆情监测分析专家。报告日期：{today}，监测范围：近半年（2025年11月至今）。

以下是{len(all_search_results)}个关键词的近半年**舆情监测**搜索结果。请生成舆情简报（600字以内）。

重要：只关注近半年的**舆论争议、负面评价、投诉、安全事故、公众情绪**，忽略半年以前的旧闻和项目建设进度信息。

分类要求：
- 集团品牌：搜索广州交投集团、广州高速运营公司的**舆论评价、投诉、声誉事件**
- 路段项目：搜索各路段的**事故、拥堵投诉、收费争议、路面质量问题**，不是建设进展
- 收费服务：搜索**收费员态度投诉、收费标准争议、乱收费举报**
- 行业风险：搜索全国高速公路**重大事故、塌方、桥梁安全问题、边坡水毁**等

每个类别列出关键舆情发现（有争议写争议，无争议写"未发现明显负面舆情"），标注来源URL。末尾汇总所有URL。

搜索结果：
{topics_text}

请生成舆情简报（v1 快速版）："""

    try:
        report = _call_llm_summary(prompt)
        elapsed = round((time.time() - start) * 1000)
        path = Path('final_reports/summary_v1'); path.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        md_name = f'summary_v1_{ts}'
        (path / f'{md_name}.md').write_text(report, encoding='utf-8')
        _save_report_html(path, md_name, report, '舆情简报 v1')
        return jsonify({'success': True, 'report': report, 'elapsed_ms': elapsed, 'source_count': len(all_search_results), 'version': 'v1', 'download_md': f'/api/download/summary_v1/{md_name}.md', 'download_html': f'/api/download/summary_v1/{md_name}.html'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/summary-v2', methods=['POST'])
def summary_v2():
    """舆情简报 v2 — Quick-search + Insight 深度分析结果"""
    start = time.time()
    if not all_search_results:
        return jsonify({'success': False, 'message': '没有搜索结果'})

    insight_count = sum(1 for d in all_search_results.values() if d.get('insight_report'))
    topics_text = "\n\n".join(_build_topics_text(include_insight=True))
    today = datetime.now().strftime('%Y年%m月%d日')
    prompt = f"""你是舆情监测分析专家。报告日期：{today}。

以下是{len(all_search_results)}个关键词的深度舆情分析结果（含{insight_count}个Insight深度分析），请生成详细舆情深度简报（1200字以内）。

重要：聚焦**舆论争议、负面评价、投诉、安全事故、公众情绪**，不是项目建设进展。

分类要求：
- 集团品牌：广州交投、广州高速运营的**舆论评价、声誉风险**
- 路段项目：各路段的**事故、投诉、质量问题、收费纠纷**
- 收费服务：**收费态度、乱收费、收费标准争议**
- 行业风险：全国高速**重大事故、塌方、桥梁安全、边坡水毁**

每个类别：关键舆情发现 + 深度洞察 + 来源URL。末尾汇总所有URL。

数据：
{topics_text}

请生成舆情深度简报（v2 深度版）："""

    try:
        report = _call_llm_summary(prompt, max_tokens=3000)
        elapsed = round((time.time() - start) * 1000)
        path = Path('final_reports/summary_v2'); path.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        md_name = f'summary_v2_{ts}'
        (path / f'{md_name}.md').write_text(report, encoding='utf-8')
        _save_report_html(path, md_name, report, '舆情详报 v2')
        return jsonify({'success': True, 'report': report, 'elapsed_ms': elapsed, 'source_count': len(all_search_results), 'insight_count': insight_count, 'version': 'v2', 'download_md': f'/api/download/summary_v2/{md_name}.md', 'download_html': f'/api/download/summary_v2/{md_name}.html'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/latest-report')
def latest_report():
    """返回最近生成的报告"""
    path = Path('final_reports')
    v1_files = sorted((path / 'summary_v1').glob('*.md'), reverse=True) if (path / 'summary_v1').exists() else []
    v2_files = sorted((path / 'summary_v2').glob('*.md'), reverse=True) if (path / 'summary_v2').exists() else []
    result = {'success': True}
    if v1_files:
        f = v1_files[0]
        result['v1'] = f.read_text(encoding='utf-8')
        name = f.stem
        result['v1_time'] = name.replace('summary_v1_', '')
        result['v1_html'] = f'/api/download/summary_v1/{name}.html'
        result['v1_md'] = f'/api/download/summary_v1/{name}.md'
    if v2_files:
        f = v2_files[0]
        result['v2'] = f.read_text(encoding='utf-8')
        name = f.stem
        result['v2_time'] = name.replace('summary_v2_', '')
        result['v2_html'] = f'/api/download/summary_v2/{name}.html'
        result['v2_md'] = f'/api/download/summary_v2/{name}.md'
    return jsonify(result)


@app.route('/api/auto-search', methods=['POST'])
def auto_search():
    """返回查询主题列表。如搜索正在运行，返回当前进度用于恢复。"""
    from config import settings
    from utils.querything_parser import get_query_keywords

    # 如果搜索正在运行，返回当前进度（用于页面刷新后恢复）
    if search_state['running']:
        return jsonify({
            'success': True,
            'topics': search_state['topics'],
            'total': len(search_state['topics']),
            'current_index': search_state['current_index'],
            'resume': True,
        })

    querything_path = Path(__file__).parent / 'querything.md'
    if not querything_path.exists():
        querything_path = Path(__file__).parent.parent / 'querything.md'

    if querything_path.exists():
        topics = get_query_keywords(str(querything_path))
        if topics:
            logger.info(f"从 querything.md 加载了 {len(topics)} 个查询主题")
        else:
            topics = []
    else:
        topics = []

    if not topics:
        topics_str = (settings.AUTO_QUERY_TOPICS or '').strip()
        if topics_str:
            topics = [t.strip() for t in topics_str.split(',') if t.strip()]

    if not topics:
        return jsonify({'success': False, 'message': '未找到查询主题'})

    # 开始新的搜索
    search_state['running'] = True
    search_state['topics'] = topics
    search_state['current_index'] = 0
    search_state['start_time'] = datetime.now()
    search_state['results'] = {}

    return jsonify({
        'success': True,
        'topics': topics,
        'total': len(topics),
        'current_index': 0,
        'resume': False,
    })


@app.route('/api/config', methods=['GET'])
def get_config():
    """Expose selected configuration values to the frontend."""
    try:
        config_values = read_config_values()
        return jsonify({'success': True, 'config': config_values})
    except Exception as exc:
        logger.exception("读取配置失败")
        return jsonify({'success': False, 'message': f'读取配置失败: {exc}'}), 500


@app.route('/api/config', methods=['POST'])
def update_config():
    """Update configuration values and persist them to config.py."""
    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict) or not payload:
        return jsonify({'success': False, 'message': '请求体不能为空'}), 400

    updates = {}
    for key, value in payload.items():
        if key in CONFIG_KEYS:
            updates[key] = value if value is not None else ''

    if not updates:
        return jsonify({'success': False, 'message': '没有可更新的配置项'}), 400

    try:
        write_config_values(updates)
        updated_config = read_config_values()
        return jsonify({'success': True, 'config': updated_config})
    except Exception as exc:
        logger.exception("更新配置失败")
        return jsonify({'success': False, 'message': f'更新配置失败: {exc}'}), 500


@app.route('/api/system/status')
def get_system_status():
    """返回系统启动状态。"""
    state = _get_system_state()
    return jsonify({
        'success': True,
        'started': state['started'],
        'starting': state['starting']
    })


@app.route('/api/system/start', methods=['POST'])
def start_system():
    """在接收到请求后启动完整系统。"""
    allowed, message = _prepare_system_start()
    if not allowed:
        return jsonify({'success': False, 'message': message}), 400

    try:
        success, logs, errors = initialize_system_components()
        if success:
            _set_system_state(started=True)
            return jsonify({'success': True, 'message': '系统启动成功', 'logs': logs})

        _set_system_state(started=False)
        return jsonify({
            'success': False,
            'message': '系统启动失败',
            'logs': logs,
            'errors': errors
        }), 500
    except Exception as exc:  # pragma: no cover - 保底捕获
        logger.exception("系统启动过程中出现异常")
        _set_system_state(started=False)
        return jsonify({'success': False, 'message': f'系统启动异常: {exc}'}), 500
    finally:
        _set_system_state(starting=False)

@app.route('/api/system/shutdown', methods=['POST'])
def shutdown_system():
    """优雅停止所有组件并关闭当前服务进程。"""
    state = _get_system_state()
    if state['starting']:
        return jsonify({'success': False, 'message': '系统正在启动/重启，请稍候'}), 400

    target_ports = [
        f"{name}:{info['port']}"
        for name, info in processes.items()
        if info.get('port')
    ]

    # 已有关机请求执行中时，返回当前存活的子进程，便于前端判断进度
    if not _mark_shutdown_requested():
        running = _describe_running_children()
        detail = '关机指令已下发，请稍等...'
        if running:
            detail = f"关机指令已下发，等待进程退出: {', '.join(running)}"
        if target_ports:
            detail = f"{detail}（端口: {', '.join(target_ports)}）"
        return jsonify({'success': True, 'message': detail, 'ports': target_ports})

    running = _describe_running_children()
    if running:
        _log_shutdown_step("开始关闭系统，正在等待子进程退出: " + ", ".join(running))
    else:
        _log_shutdown_step("开始关闭系统，未检测到存活子进程")

    try:
        _set_system_state(started=False, starting=False)
        _start_async_shutdown(cleanup_timeout=6.0)
        message = '关闭系统指令已下发，正在停止进程'
        if running:
            message = f"{message}: {', '.join(running)}"
        if target_ports:
            message = f"{message}（端口: {', '.join(target_ports)}）"
        return jsonify({'success': True, 'message': message, 'ports': target_ports})
    except Exception as exc:  # pragma: no cover - 兜底捕获
        logger.exception("系统关闭过程中出现异常")
        return jsonify({'success': False, 'message': f'系统关闭异常: {exc}'}), 500

@socketio.on('connect')
def handle_connect():
    """客户端连接"""
    emit('status', 'Connected to Flask server')

@socketio.on('request_status')
def handle_status_request():
    """请求状态更新"""
    check_app_status()
    emit('status_update', {
        app_name: {
            'status': info['status'],
            'port': info['port']
        }
        for app_name, info in processes.items()
    })

def _auto_start_and_query():
    """后台自动启动系统组件，并直接执行查询（不依赖前端）"""
    time.sleep(3)
    try:
        logger.info("自动启动系统组件...")
        initialize_system_components()
        _set_system_state(started=True, starting=False)
        logger.info("系统组件已自动启动，开始后端自动查询...")

        # 直接从后端执行查询
        _run_backend_queries()
    except Exception as e:
        logger.error(f"自动启动失败: {e}")
        _set_system_state(started=False, starting=False)


def _run_backend_queries():
    """后端直接执行 Quick-search 和 Insight 查询"""
    from utils.querything_parser import get_query_keywords
    from config import settings

    querything_path = Path(__file__).parent / 'querything.md'
    if not querything_path.exists():
        querything_path = Path(__file__).parent.parent / 'querything.md'

    if not querything_path.exists():
        logger.warning("未找到 querything.md，跳过查询")
        return

    topics = get_query_keywords(str(querything_path))
    if not topics:
        return

    # 设置搜索状态
    search_state['running'] = True
    search_state['topics'] = topics
    search_state['current_index'] = 0
    search_state['start_time'] = datetime.now()
    search_state['results'] = {}

    logger.info(f"后端开始查询 {len(topics)} 个主题")
    socketio.emit('console_output', {
        'app': 'system',
        'line': f"[{datetime.now().strftime('%H:%M:%S')}] [系统] 开始自动查询 {len(topics)} 个主题..."
    })

    # Phase 1: Quick-search 所有主题
    from tavily import TavilyClient
    tavily = TavilyClient(api_key=settings.TAVILY_API_KEY or '')

    for i, topic in enumerate(topics):
        try:
            result = tavily.search(topic + ' 舆情 2025 2026', max_results=5, search_depth='basic', days=180)
            results_list = []
            for r in result.get('results', []):
                results_list.append({
                    'title': r.get('title', ''),
                    'url': r.get('url', ''),
                    'content': (r.get('content', '') or '')[:200],
                })
            all_search_results[topic] = {'query_results': results_list, 'insight_report': ''}
            search_state['current_index'] = i + 1
            if (i + 1) % 5 == 0:
                logger.info(f"Quick-search 进度: {i+1}/{len(topics)}")
        except Exception as e:
            logger.warning(f"Quick-search 失败 [{topic}]: {e}")
            all_search_results[topic] = {'query_results': [], 'insight_report': ''}

    search_state['current_index'] = len(topics)
    logger.info(f"Quick-search 完成: {len(topics)} 个主题")
    socketio.emit('console_output', {
        'app': 'system',
        'line': f"[{datetime.now().strftime('%H:%M:%S')}] [系统] Quick-search 完成，开始 Insight 深度分析..."
    })

    # Phase 2: Insight 逐个深度分析（可选，耗时长）
    # 如果需要 Insight，取消下面的注释
    # for i, topic in enumerate(topics[:3]):  # 先只跑前3个
    #     try:
    #         from InsightEngine.agent import DeepSearchAgent
    #         from InsightEngine.utils.config import settings as insight_settings
    #         agent = DeepSearchAgent(insight_settings)
    #         report = agent.research(topic, save_report=True)
    #         all_search_results[topic]['insight_report'] = report or ''
    #         logger.info(f"Insight 完成 [{i+1}]: {topic}")
    #     except Exception as e:
    #         logger.error(f"Insight 失败 [{topic}]: {e}")

    search_state['running'] = False
    logger.info("后端自动查询全部完成")
    socketio.emit('console_output', {
        'app': 'system',
        'line': f"[{datetime.now().strftime('%H:%M:%S')}] [系统] 全部查询完成，可生成报告"
    })


if __name__ == '__main__':
    from config import settings
    HOST = settings.HOST
    PORT = settings.PORT

    logger.info("系统正在启动，Agent 组件将自动初始化...")
    logger.info(f"Flask服务器启动，访问地址: http://{HOST}:{PORT}")

    # 启动自动初始化线程
    auto_init_thread = threading.Thread(target=_auto_start_and_query, daemon=True)
    auto_init_thread.start()

    try:
        socketio.run(app, host=HOST, port=PORT, debug=False)
    except KeyboardInterrupt:
        logger.info("\n正在关闭应用...")
        cleanup_processes()
        
    
