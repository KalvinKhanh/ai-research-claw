# PaperWriter Web: Đặc tả (SPEC v2)

> Thay thế SPEC v0.3. Đi kèm [PLAN.md](PLAN.md). Trạng thái: bản nháp để duyệt.
> Các chỗ đánh dấu **(cần xác nhận ở G0)** chưa được kiểm chứng bằng cách chạy thật.

## 1. Mục tiêu và phi mục tiêu

**Mục tiêu**
- Một hệ thống riêng, nhận đầu ra của các hệ thống khác (engine stage 1–8, SLR, thông tin phong cách tạp chí từ JSM) và cùng người dùng viết ra một bài báo hoàn chỉnh.
- Dùng lại Stage 16–23 gốc của AutoResearchClaw: outline, draft, peer review, revision, quality gate, archive, export LaTeX, citation verify.
- Giữ luật chống bịa số liệu của hệ gốc. Trích dẫn chỉ đến từ tài liệu được cung cấp.
- Người dùng kiểm soát ba điểm: duyệt dàn ý, phân loại nhận xét review, duyệt chất lượng cuối; và có thể sửa tay từng section.

**Phi mục tiêu (v1)**
- Không chạy thực nghiệm, không tìm kiếm tài liệu, không sinh hypothesis (đó là việc của các hệ thống khác).
- Không kết nối thời gian chạy với JSM, SLR hay engine. Chỉ nhận **tệp hoặc thư mục** làm đầu vào.
- Không đồng bộ Overleaf, không chỉnh sửa đồng thời nhiều người, không biên dịch PDF (v1 xuất `.tex` và `.bib`).

## 2. Người dùng
Nhóm nội bộ, ít người, vai trò duy nhất: tác giả. Đăng nhập bằng SSO của nhóm (OIDC PKCE, JWT RS256 kiểm tra bằng JWKS của IdP). Chạy trên máy cá nhân ở giai đoạn đầu.

## 3. Gói đầu vào `paper-input`

Dựa trên `paper_input_contract_v1` trong lịch sử git (`git show 3bdf8f4^:paper_writing_full_output/arc_paper_input_sample/paper_input_contract_v1.md`).

```text
paper-input/
├── manifest.yaml            # tên dự án, mức đầy đủ, nguồn gốc, ngày tạo
├── research/                # context.md, questions.yaml, hypotheses.yaml, contributions.md
├── literature/              # references.bib, notes.md
├── methodology/             # method.md, experiment.yaml, environment.yaml, code/
├── evidence/                # analysis.md, decision.md, experiment_summary.json,
│   └── runs/ , figures/ , tables/        # runs/*.json, results.json
├── claims/                  # claims.yaml (tùy chọn)
└── publication/             # target.yaml, author_instructions.md, style_benchmark.yaml
```

**Ba mức đầy đủ**
- Mức 1 (tối thiểu): `manifest.yaml`, `research/context.md`, `literature/references.bib`, `hypotheses` hoặc `contributions`. Chạy ở chế độ `docs-first`.
- Mức 2 (chuẩn): thêm `methodology/method.md`, `literature/notes.md`, `publication/target.yaml`.
- Mức 3 (giàu bằng chứng): thêm `evidence/` với `runs/*.json` thật (`status` khác `simulated`, có `metrics`), bảng, hình, `claims.yaml`. Chạy ở chế độ thực nghiệm.

Hệ thống tự chọn chế độ: có kết quả thật thì thực nghiệm, ngược lại ghi `project_mode: docs-first` để Stage 17 bỏ qua chặn cứng thiếu metric (`_topic_is_literature_first()`). **Cần xác nhận ở G0** là chế độ này cho bài đạt yêu cầu.

## 4. Các nguồn đầu vào và adapter

| Nguồn | Người dùng đưa gì | Adapter làm gì |
|---|---|---|
| Engine stage 1–8 | Thư mục chạy (`stage-01 … stage-08`) hoặc gói nén | `goal.md` → `research/context.md`; `problem_tree.md` → `research/questions.yaml`; `hypotheses.md` → `research/hypotheses.yaml`; `synthesis.md` → `literature/notes.md`; `shortlist.jsonl` + `cards/` → `literature/references.bib` |
| SLR system | Báo cáo PRISMA (JSON, số liệu luồng), CSV/XLSX danh sách nghiên cứu và bảng trích xuất (định dạng cần mẫu thật) | PRISMA → `evidence/prisma.json` và đoạn Methods "Study selection"; danh sách → `references.bib`, `notes.md`; bảng → `evidence/tables/`; đặt `docs-first` |
| JSM | Vài số đọc từ biểu đồ, nhập tay vào form (JSM không có tệp xuất) | Ghi `publication/style_benchmark.yaml` và chuyển thành chỉ dẫn viết trong `author_instructions.md` |
| Tải gói sẵn | Gói `paper-input` hoàn chỉnh | Chỉ kiểm tra hợp lệ |

Số phong cách nhập tay: độ dài câu trung vị, P10 và P90, % câu bị động, % ngôi "We", % hedge, ghi chú. Gắn nhãn "gợi ý" trên giao diện.

## 5. Quy trình chạy (Stage 16–23)

| Stage | Tên | Người dùng can thiệp |
|---|---|---|
| (trước) | Nhập, kiểm tra, materialize gói thành thư mục chạy kiểu ARC | Sửa lỗi gói nếu có |
| 16 | PAPER_OUTLINE | **Duyệt dàn ý** (cổng 1) |
| 17 | PAPER_DRAFT | Sửa tay từng section, nhờ AI polish, finalize |
| 18 | PEER_REVIEW | **Phân loại nhận xét** (cổng 2): chấp nhận, bỏ qua |
| 19 | PAPER_REVISION | Xem diff, hoàn tác |
| 20 | QUALITY_GATE | **Duyệt chất lượng cuối** (cổng 3) |
| 21 | KNOWLEDGE_ARCHIVE | Không |
| 22 | EXPORT_PUBLISH | Mẫu LaTeX mặc định `generic` |
| 23 | CITATION_VERIFY | Xem báo cáo xác minh |

Hợp đồng artifact (từ mã): 16 → `outline.md`; 17 → `paper_draft.md`; 18 → `reviews.md`; 19 → `paper_revised.md`; 20 → `quality_report.json`; 21 → `archive.md`, `bundle_index.json`; 22 → `paper_final.md`, `code/`; 23 → `verification_report.json`, `references_verified.bib`.

Quay lui: người dùng có thể chạy lại từ một stage; các stage sau được đánh dấu cũ (stale), không bị xóa.

## 6. Quy tắc nội dung
- Không có kết quả thực nghiệm thì không được sinh bảng kết quả, số liệu, p-value hay so sánh hiệu năng; luật chống bịa số liệu của hệ gốc giữ nguyên.
- Trích dẫn chỉ đến từ `references.bib` của gói. Khóa lạ bị Stage 23 cờ lỗi và chặn xuất.
- Bài ở chế độ `docs-first` gắn nhãn rõ là proposal hoặc survey trong `manifest` và trên giao diện.
- Chuẩn phong cách từ JSM chỉ là gợi ý đưa vào prompt, không phải điều kiện bắt buộc.

## 7. Giao diện (theo phong cách SLR-FE)

Công nghệ: React + Vite + TypeScript + Tailwind 4 + React Query (+ Redux Toolkit nếu cần) + TipTap; token màu của SLR (`#0071BC`, nền `#F7F9FA`, chữ `#122331`), font Manrope.

**Trang**
| Route | Nội dung |
|---|---|
| `/` | Danh sách dự án, trạng thái, nút "New paper" |
| `/projects/new` | Bốn cách tạo: tải gói; nhập từ engine; nhập từ SLR; điền form tay. Tab "Journal style" nhập số JSM |
| `/projects/:id` | Dòng thời gian Stage 16–23; vùng nội dung theo stage đang chọn |
| `/projects/:id/outline` | Duyệt và sửa dàn ý (cổng 1) |
| `/projects/:id/draft` | Soạn thảo theo section: cây section bên trái, editor ở giữa, ngữ cảnh bên phải (nguồn tham khảo, kiểm tra, nhận xét) |
| `/projects/:id/review` | Phân loại nhận xét (cổng 2) |
| `/projects/:id/final` | Báo cáo chất lượng, duyệt cuối (cổng 3) |
| `/projects/:id/export` | Chọn mẫu, xem trước, tải `.zip` |

**Hành vi bắt buộc**
- Cập nhật trạng thái chạy theo thời gian thực (SSE); nút Dừng; lỗi có nút Thử lại.
- Tự lưu bản sửa sau 1,5 giây không gõ; lịch sử phiên bản mỗi section và hoàn tác.
- Không giả lập dữ liệu: khi API chưa sẵn sàng, hiển thị đúng trạng thái đó.
- Hiển thị token đã dùng và hạn mức của dự án.
- Responsive tới 375px, không tràn ngang; đạt tiêu chí truy cập cơ bản (tương phản, focus, nút >= 44px).

## 8. API (FastAPI, tiền tố `/api`)

| Method | Đường dẫn | Mô tả |
|---|---|---|
| GET/POST | `/projects` | Liệt kê, tạo dự án |
| GET/DELETE | `/projects/{id}` | Chi tiết, xóa |
| POST | `/projects/{id}/package` | Tải gói `paper-input` (zip) |
| POST | `/projects/{id}/import/engine` | Nhập từ thư mục chạy hoặc zip của engine |
| POST | `/projects/{id}/import/slr` | Nhập tệp xuất từ SLR |
| PUT | `/projects/{id}/style-benchmark` | Lưu số phong cách nhập tay |
| GET | `/projects/{id}/validation` | Kết quả kiểm tra gói (mức 1/2/3, lỗi, cảnh báo) |
| POST | `/projects/{id}/runs` | Bắt đầu chạy (`from_stage`, `to_stage`) |
| POST | `/runs/{id}/cancel` | Dừng |
| GET | `/runs/{id}` | Trạng thái từng stage |
| GET | `/runs/{id}/events` | SSE: tiến trình, chờ phản hồi ở cổng |
| POST | `/runs/{id}/gates/{gate}` | Trả lời cổng (approve, reject, kèm phản hồi) |
| GET/PUT | `/runs/{id}/artifacts/{name}` | Đọc, sửa artifact (outline, draft theo section…) |
| POST | `/runs/{id}/sections/{name}/polish` | Nhờ AI polish một section |
| GET | `/runs/{id}/export` | Tải gói cuối (`.tex`, `.bib`, `paper_final.md`, báo cáo) |
| GET | `/health` | Kiểm tra sống |

Xác thực: `Authorization: Bearer <JWT từ SSO>`; giai đoạn đầu cho phép khóa dev `X-Service-Key`.

## 9. Dữ liệu và lưu trữ
- Thư mục chạy trên đĩa theo bố cục ARC là nguồn chân lý cho artifact (`runs/<run_id>/stage-NN/...`), đúng như pipeline gốc.
- SQLite chỉ giữ chỉ mục: `projects` (id, tên, chế độ, mức gói, trạng thái, ngày), `runs` (id, project_id, stage hiện tại, trạng thái, token vào/ra, lỗi), `gate_events` (run_id, cổng, quyết định, ghi chú, thời gian).
- Khởi động lại dịch vụ: lần chạy dở dang được đánh dấu `interrupted` và chạy lại từ checkpoint mà pipeline gốc đã có (`checkpoint.json`).

## 10. LLM
- AWS Bedrock qua adapter có sẵn `researchclaw/llm/bedrock_adapter.py` (Converse API); cấu hình bằng YAML `llm:`, thông tin AWS theo cách chuẩn của AWS (biến môi trường hoặc `aws configure`).
- Cho phép chọn model khác nhau cho viết và cho reviewer; có hạn mức token mỗi dự án và dừng khi vượt.
- Bedrock **chưa được thử** với tài khoản của bạn; G0 kiểm tra bằng `/api/health/bedrock`.

## 11. Yêu cầu phi chức năng
- **Độ bền**: lần chạy ghi checkpoint sau mỗi stage; mất điện hoặc restart không mất artifact.
- **Bảo mật**: khóa AWS chỉ nằm phía server; giới hạn kích thước tải lên; chống path traversal khi nhập thư mục chạy engine (chỉ thư mục trong danh sách cho phép cấu hình); làm sạch Markdown khi xem trước.
- **Hiệu năng**: tương tác giao diện không phụ thuộc thời gian chạy LLM; mọi tác vụ dài chạy nền và có trạng thái.
- **Kiểm thử**: LLM giả cho toàn bộ test tự động; một kịch bản e2e; kiểm tra thủ công trên trình duyệt thật cho đường dẫn chính.

## 12. Ngoài v1
- Nhập kết quả thực nghiệm từ hệ thống chạy thí nghiệm (ngoài engine).
- Bộ kiểm tra phong cách nội bộ và nhập số từ tệp khi JSM có chức năng xuất.
- Biên dịch PDF, Overleaf, đa người dùng có phân quyền.
- Tự thu thập tài liệu mở rộng thay vì chỉ dùng gói.

## 13. Câu hỏi còn mở
Xem [PLAN.md](PLAN.md) mục 7: cấu hình SSO (client_id, redirect URI), các tệp mẫu từ SLR và engine, và xác nhận loại bài chính (systematic review theo PRISMA 2020).
