# PaperWriter Web: Kế hoạch triển khai (PLAN)

> Bản v0.3: bài viết bám phong cách tạp chí mục tiêu bằng cách nhập **đầu ra của JSM** (System Journal Miner). PaperWriter là hệ thống riêng và **không kết nối với JSM**. Đi kèm [SPEC.md](SPEC.md). Thay thế phần "tích hợp với engine" trong kế hoạch trước: sản phẩm giờ là **web app độc lập chỉ có phase viết**, engine chỉ là nguồn nhập liệu tùy chọn.

## 1. Hiện trạng
- Đã có bộ khung `paperwriter/` (FastAPI, `contracts.py`, `intake.py`, `routes/runs.py`, `app.py`) và 3 test pass ([tests/test_paperwriter_skeleton.py](../../tests/test_paperwriter_skeleton.py)).
- Bộ khung này đang giả định đầu vào là run dir của engine (`INPUT_BUNDLE`). Cần đổi sang đầu vào do người dùng nhập; phần đọc run dir giữ lại làm tiện ích import.
- Prompt viết paper còn trong `researchclaw/prompts/ml.py` (khoảng dòng 950–1226) và `shared.py`, nhưng soạn cho trường hợp có kết quả thực nghiệm. Cần viết lại cho chế độ proposal.
- Code xuất LaTeX còn trong `researchclaw/templates/` (`conference.py`, `compiler.py`, `converter.py`).
- FE của team: Next 15 + React 19 + TanStack Query + `@hyperdata/design-system` (xem `ResearchPulse-Publication-Repository-FE`).
- JSM (`../jsm-be`) là hệ thống riêng, đã có StyleProfile theo tạp chí và theo section (schema `style_profile.py`). PaperWriter chỉ nhận **tệp JSON xuất từ JSM**, không gọi API và không dùng chung dữ liệu. Vì vậy chấm phong cách phải do PaperWriter tự làm (SPEC 4.3).
- Baseline test của repo đã có 1 lỗi collect: `tests/test_rc_sanitization.py` (import `_sanitize_fabricated_data` từ `executor`). Chưa chạy toàn bộ bộ test.

## 2. Nguyên tắc
1. Vertical slice trước: có một luồng chạy được từ đầu đến cuối (dù thô) rồi mới làm đẹp.
2. Không giả lập dữ liệu trên UI; trạng thái chưa có API phải hiện đúng.
3. Prompt sửa cho proposal mode **trước** khi viết UI sinh nội dung, vì chất lượng đầu ra quyết định giá trị demo.
4. Chưa động vào code của engine (xóa/di chuyển) cho đến khi web chạy được; việc dọn dẹp để cuối.

## 3. Các giai đoạn

### G0. Chốt phạm vi (0.5 ngày)
- Bạn trả lời các câu hỏi mở ở mục 13 của SPEC (7 câu, riêng câu 5–7 liên quan JSM).
- Lấy một tệp StyleProfile thật xuất từ JSM để chốt schema nhập và dùng làm dữ liệu mẫu cho test.
- Xin phép chủ JSM về việc sao chép từ điển hedge/booster; nếu không thì lên kế hoạch tự xây.
- Chạy `pytest` đầy đủ lấy baseline.
- Đầu ra: SPEC v1.0 được duyệt.

### G1. Nền backend (2 ngày)
- Thêm lớp lưu trữ SQLite (`paperwriter/store/`) theo mô hình dữ liệu SPEC mục 7.
- Thay `INPUT_BUNDLE` bằng schema đầu vào người dùng (Pydantic); chuyển `intake.py` thành `engine_import.py` (tùy chọn).
- CRUD dự án, hypotheses, references, import BibTeX.
- Nhập StyleProfile: endpoint tải JSON, kiểm tra bằng Pydantic (model sao chép từ schema JSM, ghi nguồn), lưu vào bảng `style_profiles`.
- Thêm cột `style_enabled` và các bảng `style_profiles`, `style_checks`.
- Test: CRUD, import BibTeX, idempotency, giới hạn tải lên, nhập profile (hợp lệ, sai schema, thiếu section).
- **Xong khi**: tạo được dự án đầy đủ đầu vào qua API và nhập được một StyleProfile mẫu.

### G2. Lõi viết với LLM (3–4 ngày)
- `paperwriter/prompts/`: viết prompt outline, draft, polish, review, revise cho **proposal mode**, tái dùng khối quy tắc từ `researchclaw/prompts/shared.py`.
- `paperwriter/llm.py`: bọc `researchclaw.llm.create_llm_client`, hỗ trợ streaming, đếm token, model reviewer riêng.
- Stage W2–W5 dưới dạng hàm thuần (đầu vào dự án, đầu ra phiên bản mới), kèm SSE.
- `paperwriter/checks.py`: kiểm tra quy tắc 4.2 (khóa trích dẫn lạ, mẫu số liệu bịa, đếm từ, độ dài tiêu đề).
- Test với LLM giả; thêm một test "golden" kiểm tra bộ checks bắt được số liệu bịa.
- **Phong cách từ profile của JSM (không gọi JSM)**:
  - `paperwriter/style/guidance.py`: chuyển StyleProfile thành chỉ dẫn prompt theo section (khoảng độ dài câu P25–P75, tỷ lệ ngôi "We", hedge, vài bundle, 2–3 exemplar); chuyển cảnh báo thành chỉ dẫn sửa.
  - `paperwriter/style/checker.py`: bộ kiểm tra nội bộ (phân vị độ dài câu, ngôi "We", bị động, hedge/booster, bundle) so với profile, trả điểm theo section. Không phân loại rhetorical move bằng mô hình; nếu cần thì nhờ LLM đánh nhãn, mặc định tắt.
  - Dàn ý W2 bám `rhetorical_move_distribution` của profile.
  - Reviewer phong cách ở W4 và vòng sửa W5 (tối đa N vòng, mặc định 2, dừng khi đạt ngưỡng).
  - Test: dùng StyleProfile mẫu để kiểm tra checker (văn bản gần chuẩn điểm cao, văn bản lệch điểm thấp), vòng lặp dừng đúng, và nhánh không có profile.
- **Xong khi**: script chạy xuyên W1→W5 trên một dự án mẫu, checks không báo lỗi nặng và điểm phong cách nội bộ ghi vào `style_checks` qua các vòng sửa.

### G3. Xuất bản (1–2 ngày)
- Chuyển/bọc `researchclaw/templates/*` vào `paperwriter/export/` (bắt đầu bằng `git mv` hoặc import trực tiếp, tùy mức phụ thuộc).
- Chuyển Markdown `[cite_key]` thành LaTeX + `.bib`; bộ kiểm tra citation theo SPEC mục 10.
- Gói `.zip` gồm cả `style_report.json`. Biên dịch PDF nằm ngoài v1.
- `paperwriter/journal_map.yaml`: ánh xạ tạp chí JSM sang mẫu LaTeX.
- **Xong khi**: `paper.tex` và `references.bib` của dự án mẫu biên dịch được bằng TeX cục bộ.

### G4. Frontend khung (2 ngày)
- Tạo `paperwriter-web/` (Next 15, TypeScript, TanStack Query), cấu trúc feature-folder và `ROUTES` như FE chính; nối design system.
- BFF route handlers proxy sang FastAPI, giữ `X-Service-Key` phía server.
- Trang danh sách, form tạo dự án (4 tab, có tab "Journal style" để nhập tệp StyleProfile), hook `useProject*`.
- **Xong khi**: tạo dự án trên web và thấy dữ liệu lưu thật.

### G5. Workspace tương tác (4–5 ngày)  **(phần giá trị chính)**
- Bố cục 3 vùng, thanh tiến trình 6 bước.
- Hook SSE; trình soạn thảo section có Generate/Stop/Regenerate/Polish/Finalize, lưu nháp tự động, lịch sử phiên bản và so sánh.
- Panel Evidence, Citations, Checks (cập nhật tức thì).
- Panel **Style**: điểm theo section, boxplot độ dài câu so với P10–P90, chỉ số ngôi/bị động/hedge so với chuẩn, cảnh báo, exemplar kèm DOI, nút "Apply as instruction", biểu đồ điểm qua các phiên bản. Thẻ benchmark của tạp chí (từ profile đã nhập) ở thanh trên.
- Gate duyệt dàn ý; kéo thả đổi thứ tự section.
- Review: chọn áp dụng từng nhận xét; Revise có xem diff và hoàn tác.
- Responsive tới 375px, phím tắt, trạng thái tải/lỗi.
- **Xong khi**: đi trọn happy path ở SPEC mục 5.4 chỉ bằng UI.

### G6. Export UI và hoàn thiện (1–2 ngày)
- Trang Export: xem trước LaTeX, báo cáo citation, chặn khi có khóa lạ, tải `.zip`.
- Import từ run dir engine (U6).
- Hiển thị token đã dùng và hạn mức.

### G7. Kiểm thử, tài liệu, dọn dẹp (2 ngày)
- Test thành phần FE chính và một e2e happy path (LLM giả).
- Kiểm tra trình duyệt thật cho đường dẫn chính, gồm 375px.
- Viết `docs/paperwriter/RUN_GUIDE.md` (cài đặt, biến môi trường, chạy 2 dịch vụ).
- Dọn engine như kế hoạch trước (xóa `_package_deliverables`, `paper_verifier` không dùng, sửa docstring "23-stage", README). Chỉ làm sau khi web ổn định.

Ước lượng: khoảng 18–23 ngày làm việc cho một người (đã cộng khoảng 3–4 ngày cho nhập profile và bộ kiểm tra phong cách nội bộ so với bản v0.1).

## 4. Phân việc cho sub-agent (nếu dùng)
| Việc | Phù hợp giao agent | Lý do |
|---|---|---|
| Viết prompt proposal-mode (G2) | Không | Quyết định chất lượng, cần duyệt trực tiếp |
| CRUD + SQLite + test (G1) | Có | Cơ học, tiêu chuẩn |
| Kiểm tra citation, converter (G3) | Có | Có sẵn code để tái dùng |
| Nhập và kiểm tra schema StyleProfile (G1) | Có | Cơ học, ranh giới rõ |
| Chuyển profile thành chỉ dẫn prompt, bộ kiểm tra phong cách (G2) | Không | Ảnh hưởng chất lượng bài, cần duyệt trực tiếp |
| Khung FE, BFF, hook (G4) | Có | Theo mẫu FE chính |
| Workspace tương tác (G5) | Một phần | Agent làm component, người duyệt UX |
| Tài liệu, dọn dẹp (G7) | Có | Cơ học |

Mỗi agent làm trong thư mục riêng (`paperwriter/store/`, `paperwriter/export/`, `paperwriter-web/`) để tránh xung đột; hợp nhất qua git worktree hoặc nhánh riêng.

## 5. Rủi ro và cách giảm

| Rủi ro | Mức | Giảm thiểu |
|---|---|---|
| Model viết số liệu bịa dù có luật | Cao | Bộ checks quét mẫu số liệu và khóa lạ; chặn export; reviewer dùng model khác |
| Prompt cũ cho thực nghiệm làm đầu ra lệch proposal | Cao | G2 viết lại trước, có test golden |
| Chi phí LLM tăng nhanh (draft + review + revise) | Trung bình | Đếm token, hạn mức dự án, hiển thị cho người dùng |
| Streaming qua BFF Next bị buffer | Trung bình | Dùng route handler trả `ReadableStream`, kiểm tra sớm ở G4 |
| Phụ thuộc `researchclaw` kéo nhiều package nặng | Trung bình | Chỉ import `researchclaw.llm` và `templates`; nếu vướng thì sao chép phần cần thiết |
| Biên dịch LaTeX cần TeX trên máy | Thấp | v1 chỉ xuất `.tex`/`.bib` |
| Điểm của bộ kiểm tra nội bộ lệch so với điểm của JSM (thuật toán, từ điển khác) | Cao | Gọi rõ là "Style score (PaperWriter)"; chỉ dùng làm gợi ý; kiểm tra chéo vài mẫu với điểm của JSM ở G7 |
| Schema tệp xuất của JSM thay đổi hoặc không có chức năng xuất | Trung bình | Lấy tệp mẫu thật ở G0; model nhập có `extractor_version`; báo lỗi rõ khi không khớp |
| Không phân loại được rhetorical move vì mô hình ở JSM | Trung bình | Bỏ qua ở v1 hoặc dùng LLM đánh nhãn, có thể tắt |
| Tối ưu theo điểm phong cách làm giảm chất lượng nội dung hoặc sinh câu giả theo exemplar | Trung bình | Điểm chỉ là gợi ý; giới hạn số vòng; không đưa nguyên văn exemplar vào bài, kiểm tra trùng lặp |
| Hồ sơ JSM chỉ phủ một số tạp chí (mảng phần mềm/CNTT) | Trung bình | Người dùng chỉ nhập được profile đã có; tính năng phong cách tắt được cho từng dự án |
| State chạy tác vụ mất khi restart | Trung bình | Lưu `runs` vào SQLite, đánh dấu `interrupted` |
| FE chính và FE này lệch design | Thấp | Dùng chung `@hyperdata/design-system` |

## 6. Tiêu chí hoàn thành (Definition of Done) toàn dự án
- Đi trọn happy path bằng trình duyệt thật, không dữ liệu giả.
- Bài báo mẫu ở proposal mode: không có khóa trích dẫn lạ, không số liệu thực nghiệm, tiêu đề <= 14 từ, các section nằm trong ±20% mục tiêu số từ.
- `paper.tex` + `references.bib` biên dịch được.
- Với tạp chí có hồ sơ thật: điểm phong cách của bản cuối không thấp hơn bản nháp đầu, và `style_report.json` có trong gói tải về. Không có tệp profile: bài vẫn xuất được và UI báo rõ không có kiểm tra phong cách.
- Test backend pass; các test mới không phụ thuộc mạng/LLM thật.
- `RUN_GUIDE.md` đủ để người khác chạy lại từ đầu.

## 7. Việc làm tiếp theo ngay
1. Bạn duyệt [SPEC.md](SPEC.md) và trả lời các câu hỏi mở.
2. Bạn đưa một tệp StyleProfile thật xuất từ JSM; tôi chạy `pytest` đầy đủ lấy baseline (G0).
3. Bắt đầu G1; có thể giao G1 và khung FE (G4) cho hai sub-agent chạy song song.
