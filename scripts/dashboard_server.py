import http.server
import socketserver
import json
import os
import subprocess
import sys
import threading
from urllib.parse import urlparse

PORT = 8090
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DASHBOARD_DIR = os.path.join(BASE_DIR, "dashboard")

pipeline_process = None
pipeline_log = []
pipeline_status = {
    "is_running": False,
    "topic": "",
    "current_stage": None,
    "last_log": "",
    "error": None
}

class DashboardRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DASHBOARD_DIR, **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(pipeline_status).encode("utf-8"))
            return
            
        elif parsed.path == "/api/logs":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            logs_tail = pipeline_log[-40:] if pipeline_log else []
            self.wfile.write(json.dumps({"logs": logs_tail}).encode("utf-8"))
            return

        # Fallback to static file serving
        return super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        
        if parsed.path == "/api/run-phase-1":
            global pipeline_process, pipeline_status, pipeline_log
            
            if pipeline_status["is_running"]:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Pipeline đang chạy, vui lòng chờ hoàn thành."}).encode("utf-8"))
                return

            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            data = json.loads(body) if body else {}
            topic = data.get("topic", "").strip()
            api_key = data.get("api_key", "").strip()

            if not topic:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Vui lòng nhập đề tài nghiên cứu."}).encode("utf-8"))
                return

            # Launch pipeline in background thread
            threading.Thread(target=self._run_pipeline, args=(topic, api_key), daemon=True).start()

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "started", "topic": topic}).encode("utf-8"))
            return

        elif parsed.path == "/api/rebuild-data":
            try:
                cmd = [sys.executable, os.path.join(BASE_DIR, "scripts", "build_dashboard_data.py")]
                res = subprocess.run(cmd, cwd=BASE_DIR, capture_output=True, text=True)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "rebuilt", "output": res.stdout}).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
            return

        self.send_response(404)
        self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def _run_pipeline(self, topic, api_key=None):
        global pipeline_process, pipeline_status, pipeline_log
        pipeline_status["is_running"] = True
        pipeline_status["topic"] = topic
        pipeline_status["error"] = None
        pipeline_log = [f"=== BẮT ĐẦU CHẠY PHASE 1 CHO ĐỀ TÀI: {topic} ==="]

        # Prepare environment
        env = os.environ.copy()
        
        # Load .env if present
        env_file = os.path.join(BASE_DIR, ".env")
        if os.path.exists(env_file):
            try:
                with open(env_file, encoding="utf-8") as f:
                    for line in f:
                        if "=" in line and not line.strip().startswith("#"):
                            k, v = line.strip().split("=", 1)
                            env[k.strip()] = v.strip()
            except Exception:
                pass

        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"

        if api_key:
            env["GEMINI_API_KEY"] = api_key
            env["OPENAI_API_KEY"] = api_key

        if not env.get("GEMINI_API_KEY") and not env.get("OPENAI_API_KEY"):
            msg = "CẢNH BÁO: Chưa tìm thấy GEMINI_API_KEY trong hệ thống hoặc file .env!"
            pipeline_log.append(f"⚠️  {msg}")

        try:
            cmd = [
                sys.executable, "-m", "researchclaw", "run",
                "--topic", topic,
                "--mode", "full-auto",
                "--to-stage", "HYPOTHESIS_GEN",
                "--config", "config.arc.yaml"
            ]
            pipeline_process = subprocess.Popen(
                cmd,
                cwd=BASE_DIR,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )

            for line in iter(pipeline_process.stdout.readline, ''):
                clean_line = line.strip()
                if clean_line:
                    pipeline_log.append(clean_line)
                    pipeline_status["last_log"] = clean_line

            pipeline_process.wait()
            ret_code = pipeline_process.returncode

            if ret_code == 0:
                pipeline_log.append(f"=== PIPELINE THÀNH CÔNG (MÃ 0) ===")
                subprocess.run([sys.executable, os.path.join(BASE_DIR, "scripts", "build_dashboard_data.py")], cwd=BASE_DIR)
                pipeline_log.append("=== ĐÃ CẬP NHẬT DỮ LIỆU DASHBOARD REAL-TIME ===")
            else:
                pipeline_status["error"] = f"Pipeline thất bại với mã lỗi {ret_code}."
                pipeline_log.append(f"❌ PIPELINE THẤT BẠI VỚI MÃ LỖI: {ret_code}")
                if "400" in pipeline_status["last_log"] or "API key" in "".join(pipeline_log):
                    pipeline_log.append("💡 NGUYÊN NHÂN: Thiếu hoặc sai GEMINI_API_KEY. Vui lòng nhập API Key trên giao diện hoặc lưu vào file .env")

        except Exception as ex:
            pipeline_status["error"] = str(ex)
            pipeline_log.append(f"LỖI HỆ THỐNG: {ex}")
        finally:
            pipeline_status["is_running"] = False


def main():
    with socketserver.TCPServer(("", PORT), DashboardRequestHandler) as httpd:
        print(f"AutoResearchClaw Dashboard & Execution Server running on http://localhost:{PORT}")
        httpd.serve_forever()

if __name__ == "__main__":
    main()
