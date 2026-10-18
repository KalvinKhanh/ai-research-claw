# PaperWriter: Kế hoạch triển khai (PLAN v2)

> Thay thế hoàn toàn PLAN v0.3 trước đó. Đi kèm [SPEC.md](SPEC.md) v2.
> Viết cho: bạn và nhóm đồ án, để duyệt hướng đi trước khi code.

## 1. Quyết định đã chốt (từ các câu trả lời của bạn)

| Chủ đề | Quyết định |
|---|---|
| Ý tưởng | Tách **phần write** của AutoResearchClaw thành hệ thống riêng, nhận đầu ra của các hệ thống khác và viết ra một paper |
| Phạm vi stage | **Stage 16–23** (Phase G + H): outline, draft, peer review, revision, quality gate, archive, export, citation verify |
| Cách làm | **Dùng lại code Stage 16–23 gốc** (đã khôi phục trên nhánh `restore/full-23-stage`) qua một lớp adapter. Không viết lại từ đầu |
| Nguồn đầu vào | Engine stage 1–8, SLR system, JSM. Có thể có hoặc không có kết quả thực nghiệm. Trường hợp dùng chính (suy ra từ SLR): bài **tổng quan hệ thống (systematic review)**, không thực nghiệm |
| Giao diện | Web đơn giản theo phong cách SLR-FE (React + Vite + Tailwind 4 + React Query + TipTap) |
| Người dùng | Nội bộ, ít người; đăng nhập bằng **SSO của nhóm** (OIDC, `SSO_BE`) |
| Mẫu LaTeX | **Mẫu chung** (`generic`) |
| Nơi chạy | Máy cá nhân (tạm thời) |
| LLM | AWS Bedrock (repo đã có adapter); bạn đã có tài khoản |

JSM chỉ hiển thị biểu đồ và không có tệp xuất, nên PaperWriter **không kết nối** JSM. Người dùng nhập tay vài số chuẩn phong cách đọc từ biểu đồ.

## 2. Những điều đã xác minh trong mã (và điều chưa)

Đã xác minh:
- Hợp đồng Stage 16–23 (từ `contracts.py`): Stage 16 cần `analysis.md` và `decision.md` → `outline.md`; Stage 17 → `paper_draft.md`; Stage 18 → `reviews.md`; Stage 19 → `paper_revised.md`; Stage 20 → `quality_report.json`; Stage 21 → `archive.md`, `bundle_index.json`; Stage 22 → `paper_final.md`, `code/`; Stage 23 → `verification_report.json`, `references_verified.bib`.
- Stage 17 có hai chặn cứng: dữ liệu toàn "simulated", và không có metric thật ở các miền thực nghiệm (ml, engineering, biology, chemistry). Cả hai bị bỏ qua khi `_topic_is_literature_first()` trả `True`: chủ đề chứa "survey/review/meta-analysis" hoặc `research.project_mode == "docs-first"`. Đây là cách xử lý trường hợp **không có kết quả thực nghiệm** mà không phải sửa luật chống bịa số liệu.
- Trong lịch sử git có một **PRD paper-writing 2307 dòng** và **hợp đồng đầu vào `paper_input_contract_v1`** (xóa ở commit `3bdf8f4`; xem bằng `git show 3bdf8f4^:paper_writing_module_prd.md`). Nội dung trùng ý tưởng này: fork-and-adapt Stage 16–23, gói `paper-input/` có `manifest.yaml`, `research/`, `literature/`, `methodology/`, `evidence/`, `claims/`, `publication/`. Plan này dùng lại hợp đồng đó làm điểm xuất phát.

Chưa xác minh (G0 phải trả lời):
1. Runner có chạy được `from_stage=16` trên một thư mục chạy dựng tay, và đọc artifact trước đó theo tên thư mục `stage-N` nào (`stage-1` hay `stage-01`).
2. Chế độ `docs-first` thực sự cho ra bài báo ra sao khi không có `runs/*.json`.
3. Cách HITL của repo tạm dừng ở outline, review triage và duyệt cuối, để viết một adapter web thay cho CLI.
4. Bedrock hoạt động với tài khoản AWS của bạn (dùng `/api/health/bedrock` có sẵn).
5. Định dạng dữ liệu thật mà SLR system xuất (xem mục 7).

## 3. Kiến trúc

```
Browser: paperwriter-web (Vite + React, như SLR-FE)
   │  REST + SSE
   ▼
paperwriter (FastAPI, cổng 8002)
   ├─ packages/   : nhập và kiểm tra gói paper-input
   ├─ adapters/   : engine(1–8) | slr | manual (JSM) → paper-input
   ├─ materialize : paper-input → thư mục chạy kiểu ARC (stage-N/…)
   ├─ runner      : gọi researchclaw.pipeline (from_stage=16, to_stage=23)
   ├─ hitl_web    : adapter HITL cho web (outline review, triage, final approval)
   └─ store       : SQLite (chỉ mục dự án, trạng thái) + thư mục chạy trên đĩa
researchclaw/   : Stage 16–23 gốc, prompts, templates, llm (Bedrock), hitl
```

Nguyên tắc: không sửa `researchclaw/` nếu không bắt buộc. Chỗ nào phải sửa thì ghi rõ trong danh sách thay đổi (mục 6).

## 4. Các giai đoạn

### G0. Spike kỹ thuật (3 ngày)
Mục tiêu: trả lời 5 điểm chưa xác minh ở mục 2 bằng cách chạy thật, trước khi dựng gì lớn.
- Tạo tay một gói đầu vào nhỏ cho một đề tài mẫu, vừa có kết quả giả định hợp lệ vừa không có.
- Dựng thư mục chạy kiểu ARC bằng tay, chạy Stage 16→23 với Bedrock; chạy cả chế độ `docs-first`.
- Ghi lại: tên thư mục stage, file nào thực sự cần, thời gian, chi phí token, kết quả và các chỗ vỡ.
- Phục hồi tài liệu PRD và contract cũ vào `docs/paperwriter/reference/` để tra cứu.
- Chạy `pytest` đầy đủ lấy baseline.
- **Xong khi**: có một paper mẫu (Markdown + LaTeX) sinh ra từ gói tạo tay, và danh sách các khác biệt giữa kỳ vọng và thực tế.

### G1. Gói đầu vào và adapter (4 ngày)
- `paperwriter/packages/`: schema `paper-input` (Pydantic), mức đầy đủ 1/2/3 theo contract cũ, kiểm tra tính hợp lệ có thông báo lỗi rõ.
- `paperwriter/materialize.py`: chuyển gói thành thư mục chạy ARC (`analysis.md`, `decision.md`, `stage-1/goal.md`, `stage-7/synthesis.md`, `stage-8/hypotheses.md`, `stage-12/runs/*.json`…).
- Adapter **engine**: đọc run dir stage 1–8 (`goal.md`, `synthesis.md`, `hypotheses.md`, `cards/`, `shortlist.jsonl`) → gói.
- Adapter **manual**: form nhập tay chuẩn phong cách (độ dài câu, % bị động, % "We", % hedge, ghi chú) → `publication/style_benchmark.yaml` và phần chỉ dẫn viết.
- Chế độ tự động: có `runs/*.json` thật → thực nghiệm; không có → ghi `project_mode: docs-first`.
- **Xong khi**: từ một run dir engine thật, tạo ra gói hợp lệ và thư mục chạy mà Stage 16 nhận được.

### G2. Adapter SLR (3 ngày)
Điều đã đọc trong `slr-be`: mô-đun PRISMA trả **số liệu thống kê luồng PRISMA** (số bản ghi tìm thấy, đã sàng lọc, loại, đưa vào…) qua `GET /projects/:id/prisma/reports/latest` (JSON) và xuất `.docx`; **không** có danh sách paper hay bảng trích xuất trong báo cáo này. PRISMA (Preferred Reporting Items for Systematic reviews and Meta-Analyses) là chuẩn báo cáo cho tổng quan hệ thống; các con số của nó thành phần "Study selection" trong mục Methods của bài tổng quan.
- Đầu vào chấp nhận (v1, đều là tệp, không gọi API của SLR): (a) JSON báo cáo PRISMA, (b) CSV/XLSX danh sách các nghiên cứu được đưa vào, (c) CSV/XLSX bảng trích xuất dữ liệu. Bạn nhớ "hình như CSV" nên G0 cần một tệp mẫu thật của (b) và (c).
- Ánh xạ: số liệu PRISMA → `evidence/prisma.json` và đoạn Methods dựng sẵn; danh sách nghiên cứu → `literature/references.bib` + `notes.md`; bảng trích xuất → `evidence/tables/`.
- Chủ đề/`project_mode` tự đặt thành `docs-first` với nhãn "systematic review".
- **Xong khi**: từ một dự án SLR mẫu tạo được gói có `references.bib`, bảng và số liệu PRISMA.

### G3. Dịch vụ và điều phối chạy (4 ngày)
- FastAPI: dự án, tải gói lên, nhập từ engine/SLR/form, bắt đầu/dừng chạy, trạng thái từng stage, tải artifact, SSE sự kiện.
- Trình điều phối chạy nền (hàng đợi đơn giản, một lần chạy mỗi lúc), lưu trạng thái để khởi động lại không mất.
- `hitl_web`: adapter HITL dừng ở 3 cổng (duyệt dàn ý, phân loại review, duyệt chất lượng cuối) và chờ phản hồi từ web.
- Cấu hình Bedrock qua `llm:` YAML; thống kê token mỗi lần chạy và hạn mức tối đa.
- **Đăng nhập SSO**: FastAPI kiểm tra JWT RS256 bằng JWKS của IdP (`/.well-known/jwks.json` của `SSO_BE`); web dùng luồng OIDC PKCE như các FE khác của nhóm. Giai đoạn đầu dùng khóa dev để không chặn tiến độ, bật SSO ở cuối G3 (khoảng 2 ngày). Cần client_id, redirect URI đăng ký ở IdP và quy ước vai trò.
- **Xong khi**: chạy Stage 16→23 qua API, dừng ở cả 3 cổng và tiếp tục sau khi gọi API duyệt.

### G4. Web (7–9 ngày)
- Dựng `paperwriter-web/` theo SLR-FE (Vite, React, Tailwind 4, React Query, TipTap; token và font Manrope; màu `#0071BC`).
- Trang: danh sách dự án; tạo dự án (tải gói, nhập từ engine, nhập từ SLR, form phong cách); trang chạy với dòng thời gian Stage 16–23; màn duyệt dàn ý; trình soạn bản nháp theo section (sửa tay, nhờ AI polish, finalize); màn phân loại review; màn duyệt cuối; trang xuất và tải xuống (`.tex`, `.bib`, `paper_final.md`, báo cáo xác minh).
- Streaming trạng thái bằng SSE, lưu tự động, trạng thái tải và lỗi thật (không giả dữ liệu).
- **Xong khi**: đi trọn từ tạo dự án đến tải paper bằng giao diện.

### G5. Phong cách tạp chí từ JSM nhập tay (1–2 ngày)
- Đưa chuẩn phong cách vào chỉ dẫn tác giả cho Stage 17/19 và hiển thị thẻ chuẩn trên giao diện.
- Bản sau (ngoài v1): bộ kiểm tra phong cách nội bộ tính trên bản nháp, hoặc nhập số từ tệp khi JSM có chức năng xuất.

### G6. Kiểm thử, tài liệu, dọn dẹp (3 ngày)
- Test cho adapter, materialize, kiểm tra gói, điều phối chạy (LLM giả); một kịch bản e2e với LLM giả.
- Chạy thử trên trình duyệt thật cho đường dẫn chính, gồm 375px.
- `docs/paperwriter/RUN_GUIDE.md`.
- Xử lý bộ khung `paperwriter/` có từ trước (contracts W1–W6 không còn dùng) và cập nhật README.

Tổng ước tính: khoảng 27–32 ngày công cho một người. Đây là ước tính của tôi, chưa có số đo thực tế; G0 sẽ cho số chính xác hơn về công sức của phần còn lại.

## 5. Phân việc cho sub-agent

| Việc | Giao agent? | Lý do |
|---|---|---|
| G0 spike | Không | Cần đọc kết quả thật và quyết định |
| Schema gói và kiểm tra (G1) | Có | Cơ học, có contract cũ làm đặc tả |
| Adapter engine (G1) | Có | Ánh xạ file rõ ràng |
| Adapter SLR (G2) | Có, sau khi biết định dạng | |
| API và điều phối (G3) | Một phần | Phần HITL cần người xem |
| Web (G4) | Có, theo từng trang | Theo mẫu SLR-FE; người duyệt UX |
| Test và tài liệu (G6) | Có | |

Mỗi agent làm trong thư mục riêng (`paperwriter/packages`, `paperwriter/adapters`, `paperwriter-web/`).

## 6. Danh sách thay đổi dự kiến trong `researchclaw/` (để chủ động kiểm soát)
- Có thể cần thêm cấu hình hoặc tham số cho chạy "paper-only" (bỏ qua kiểm tra phần cứng, thực nghiệm). Xác định ở G0.
- Có thể cần một HITL adapter dạng web (thêm file mới trong `hitl/adapters/`, không sửa file cũ).
- Không sửa luật chống bịa số liệu; dùng `project_mode: docs-first` cho trường hợp không có kết quả.

## 7. Câu trả lời của bạn và quyết định mặc định

| # | Câu hỏi | Trả lời / quyết định |
|---|---|---|
| 1 | SLR xuất gì | PRISMA (chưa rõ định dạng, nghi CSV). Đã tìm hiểu: PRISMA ở SLR là số liệu luồng, xuất JSON/DOCX. Danh sách nghiên cứu và bảng trích xuất cần tệp CSV/XLSX riêng; G0 lấy tệp mẫu |
| 2 | Cách nhận run dir của engine | Bạn chưa rõ → **mặc định: nhận cả hai** (đường dẫn thư mục cục bộ vì chạy trên máy cá nhân, và zip tải lên). Làm đường dẫn cục bộ trước |
| 3 | Kết quả thực nghiệm | Bạn chưa rõ → **mặc định: v1 chỉ hỗ trợ `docs-first`** (tổng quan, proposal). Chừa chỗ `evidence/` để nhập kết quả sau |
| 4 | Mẫu LaTeX | Mẫu chung (`generic`) |
| 5 | Đăng nhập | SSO của nhóm |
| 6 | Bedrock | Đã có tài khoản; G0 kiểm tra quyền model |
| 7 | Nơi chạy | Máy cá nhân; không cần Docker ở v1 |

Còn mở:
- **SSO**: client_id, redirect URI, và vai trò nào được dùng PaperWriter. Cần người quản lý `SSO_BE` cấp.
- **Mẫu dữ liệu**: một tệp PRISMA JSON, một CSV danh sách nghiên cứu và một CSV trích xuất từ một dự án SLR thật; một thư mục chạy engine stage 1–8 thật (có thể dùng `artifacts/rc-20261005-074706-96890a` nếu còn).
- **Loại bài chính**: nếu mục tiêu là bài **systematic review**, hướng dẫn viết cần theo PRISMA 2020 (Introduction, Methods, Results, Discussion). Cần xác nhận để chọn prompt phù hợp.

## 8. Rủi ro chính

| Rủi ro | Mức | Cách giảm |
|---|---|---|
| Code Stage 16–23 gốc gắn chặt với bố cục thư mục chạy ARC, adapter khó hơn dự kiến | Cao | G0 spike kiểm chứng sớm; materialize bám contract cũ |
| Chế độ `docs-first` cho bài kém khi chỉ có giả thuyết và tài liệu | Cao | G0 đánh giá chất lượng; gắn nhãn rõ proposal/survey; không bịa số liệu |
| Chi phí Bedrock (nhiều vòng review, revise) | Trung bình | Đếm token, hạn mức mỗi dự án, dùng model nhỏ cho bước phụ |
| HITL của repo thiết kế cho CLI, nối web khó | Trung bình | Viết adapter mới; tham khảo `hitl/adapters/` hiện có |
| Dữ liệu SLR không có sẵn dạng xuất | Trung bình | Nhận tệp tải lên (CSV/XLSX) làm phương án dự phòng |
| Số phong cách nhập tay từ biểu đồ JSM không chính xác | Thấp | Gắn nhãn "gợi ý"; coi là tùy chọn |
| Test cũ về paper có thể hỏng khi tách | Thấp | Chạy `pytest` đầy đủ lấy baseline ở G0 |

## 9. Việc làm tiếp theo
1. Bạn đưa các tệp mẫu nêu ở mục 7 (PRISMA JSON, CSV SLR, run dir của engine) và xác nhận loại bài chính.
2. Bắt đầu G0 trên nhánh mới từ `dev` (đã chứa bản khôi phục 23 stage).
