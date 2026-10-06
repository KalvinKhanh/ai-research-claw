import time
import json
import urllib.request
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def fetch_json(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'LogMonitor/1.0'})
    with urllib.request.urlopen(req, timeout=3) as resp:
        return json.loads(resp.read().decode('utf-8'))

def main():
    print("=" * 65)
    print("   AutoResearchClaw - Live Log Monitor (Theo dõi thời gian thực)")
    print("=" * 65)
    print("Đang kết nối tới Backend (http://localhost:8090)...")
    print("Nhấn Ctrl + C để dừng theo dõi bất cứ lúc nào.\n")

    seen_lines = 0
    last_running_state = None

    while True:
        try:
            status_data = fetch_json("http://localhost:8090/api/status")
            is_running = status_data.get("is_running", False)
            topic = status_data.get("topic", "N/A")

            if is_running != last_running_state:
                if is_running:
                    print(f"\n🟢 [CÓ NGƯỜI BẮT ĐẦU VẬN HÀNH]")
                    print(f"👉 Đề tài: {topic}")
                    print("-" * 65)
                else:
                    if last_running_state is True:
                        print(f"\n⚪ [TIẾN TRÌNH ĐÃ HOÀN TẤT HOẶC DỪNG]")
                        print("-" * 65)
                    else:
                        print("⚪ [TRẠNG THÁI]: Hệ thống đang sẵn sàng (chưa có ai bấm chạy)...")
                last_running_state = is_running

            logs_data = fetch_json("http://localhost:8090/api/logs")
            logs = logs_data.get("logs", [])

            if len(logs) < seen_lines:
                seen_lines = 0

            if len(logs) > seen_lines:
                for line in logs[seen_lines:]:
                    print(f"> {line}")
                seen_lines = len(logs)

        except urllib.error.URLError:
            print("⚠️ Chưa kết nối được Backend trên port 8090. Đang thử lại...", end="\r")
        except Exception as e:
            pass

        time.sleep(1.5)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nĐã thoát trình theo dõi log.")
