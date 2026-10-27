import subprocess
import sys
import os
import time
import webbrowser

# 强制切换工作目录到脚本所在目录
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# 自动激活虚拟环境
venv_python = os.path.join(os.getcwd(), ".venv", "Scripts", "python.exe")
if sys.executable != venv_python:
    subprocess.Popen([venv_python, __file__], creationflags=subprocess.CREATE_NEW_CONSOLE)
    sys.exit()

# 下面是你原来的脚本代码，直接复制粘贴即可
FRONTEND_DIR = os.path.join(os.getcwd(), "frontend")
BACKEND_CMD = f'"{venv_python}" app.py'
FRONTEND_CMD = "npm run dev"

def kill_port(port):
    try:
        subprocess.run(f"netstat -ano | findstr :{port}", shell=True, check=True, capture_output=True)
        subprocess.run(f"for /f \"tokens=5\" %a in ('netstat -ano ^| findstr :{port} ^| findstr LISTENING') do taskkill /PID %a /F", shell=True)
    except subprocess.CalledProcessError:
        pass

kill_port(5173)
kill_port(5000)

print("="*60)
print("📦 ContractGuard 一键启动脚本")
print("="*60)

backend_proc = subprocess.Popen(
    BACKEND_CMD,
    cwd=os.getcwd(),
    shell=True,
    creationflags=subprocess.CREATE_NEW_CONSOLE
)
print("🚀 后端启动中...")

time.sleep(5)

frontend_proc = subprocess.Popen(
    FRONTEND_CMD,
    cwd=FRONTEND_DIR,
    shell=True,
    creationflags=subprocess.CREATE_NEW_CONSOLE
)
print("🚀 前端启动中...")

time.sleep(5)

print("\n" + "="*60)
print("✅ 服务已启动")
print("🌐 前端：http://localhost:5173/")
print("🔧 后端：http://127.0.0.1:5000/")
print("="*60)

webbrowser.open("http://localhost:5173/")
input("\n按回车退出脚本（不会关闭服务窗口）...")