"""Narrative Mind 启动器 — 用于 PyInstaller 打包"""
import sys
from pathlib import Path

# 确保 src 目录在 Python 路径中
_SRC = Path(__file__).resolve().parent / "src"
if getattr(sys, 'frozen', False):
    _SRC = Path(sys._MEIPASS) / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from api_server import app

if __name__ == '__main__':
    import webbrowser
    import threading

    print("=" * 50)
    print("  Narrative Mind v3.1 — AI 辅助小说创作系统")
    print("=" * 50)
    print()

    # 打开浏览器
    threading.Timer(1.5, lambda: webbrowser.open("http://127.0.0.1:5000")).start()
    print("  浏览器将自动打开 → http://127.0.0.1:5000")
    print("  按 Ctrl+C 停止服务器")
    print()

    app.run(debug=False, port=5000)
