# PaperWriter Web: Đặc tả (SPEC)

> Trạng thái: bản nháp v0.3 để duyệt (v0.3: dùng **đầu ra của JSM** làm đầu vào phong cách, **không kết nối với JSM**; xem 4.3). Đi kèm [PLAN.md](PLAN.md).
> Phạm vi: chỉ giữ **phase viết bài báo** của AutoResearchClaw và dựng thành một web app độc lập, có UI tương tác thật. Các phase trước (scoping, literature, synthesis, experiment) **không nằm trong sản phẩm này**.

## 1. Mục tiêu và phi mục tiêu

**Mục tiêu**
- Người dùng đưa vào chủ đề, giả thuyết, danh sách tài liệu tham khảo và ghi chú, rồi cùng AI viết ra một bài báo hoàn chỉnh theo từng bước: dàn ý, bản nháp, review, sửa, xuất LaTeX.
- Người dùng kiểm soát từng section: xem, sửa tay, yêu cầu AI viết lại, khóa (finalize).
- Mọi trích dẫn phải đến từ danh sách tài liệu người dùng cung cấp. Không bịa số liệu.
- Bài viết **bám phong cách của tạp chí mục tiêu** nhờ hồ sơ phong cách (StyleProfile) mà người dùng xuất từ JSM và nhập vào (xem 4.3). PaperWriter là hệ thống riêng, không gọi JSM. Hồ sơ này chỉ cung cấp văn phong, không cung cấp nội dung.

**Phi mục tiêu (v1)**
- Không tìm kiếm tài liệu, không chạy thực nghiệm, không sinh hypothesis.
- Không đồng bộ Overleaf, không cộng tác nhiều người cùng lúc (real-time co-editing).
- Không đăng nhập OIDC. Dùng một khóa truy cập đơn giản (xem 8).

## 2. Người dùng và kịch bản chính

Vai trò duy nhất: **tác giả** (sinh viên hoặc nhà nghiên cứu).

| # | Kịch bản | Kết quả |
|---|---|---|
| U1 | Tạo dự án mới, nhập chủ đề, giả thuyết, tài liệu | Dự án ở trạng thái `intake_done` |
| U2 | Duyệt dàn ý do AI đề xuất, sửa, chọn tiêu đề | Dàn ý được khóa |
| U3 | Sinh nháp từng section, sửa tay, yêu cầu AI polish | Các section ở trạng thái `finalized` |
| U4 | Chạy review đa reviewer, chọn áp dụng hoặc bỏ qua từng nhận xét | Bản đã sửa |
| U5 | Xuất `.tex`, `.bib`, `.md` và báo cáo kiểm tra citation | Gói tải về `.zip` |
| U6 | (Tùy chọn) Nhập run dir của engine cũ để điền sẵn dữ liệu | Form U1 tự điền |

## 3. Đầu vào (Input)

Vì không còn phase trước, đầu vào do người dùng cung cấp trực tiếp:

| Trường | Bắt buộc | Mô tả |
|---|---|---|
| `title_hint` | Không | Gợi ý tiêu đề |
| `topic` | Có | Chủ đề và bài toán, 1–3 đoạn |
| `hypotheses[]` | Có (>= 1) | Mỗi mục: `id`, `statement`, `rationale`, `falsifiable_by` |
| `references[]` | Có (>= 5) | Mỗi mục: `key`, `title`, `authors`, `year`, `venue`, `abstract`, `doi/url` |
| `notes` | Không | Ghi chú tự do, ví dụ khoảng trống nghiên cứu, hạn chế |
| `style_profile` | Không | Tệp JSON StyleProfile xuất từ JSM (xem 4.3). Không có thì tắt tính năng phong cách |
| `venue` | Có | Mẫu LaTeX: `neurips`, `iclr`, `icml`, `generic`, `article` (theo `researchclaw/templates/conference.py`). Có bảng ánh xạ `journal_id` của StyleProfile → `venue` (mục 4.3) |
| `language` | Có | `en` (v1 chỉ hỗ trợ tiếng Anh cho bài báo) |
| `results` | Không | Chỉ chấp nhận ở bản sau, xem 12 |

Cách nhập tài liệu: dán BibTeX, tải lên file `.bib`/`.json`, hoặc thêm từng mục bằng form. Hệ thống tự gán `key` duy nhất.

**Nhập từ engine cũ (U6)**: người dùng chỉ đường dẫn run dir hoặc tải lên `.zip`. Hệ thống ánh xạ:
`stage-08/hypotheses.md` → `hypotheses[]`, `stage-05/shortlist.jsonl` + `stage-06/cards/` → `references[]`, `stage-07/synthesis.md` → `notes`, `stage-01/goal.md` → `topic`. Việc này chỉ là tiện ích nhập liệu, không phải phụ thuộc.

**Chế độ viết**: không có `results` thì bài báo là **proposal / position paper**. Cấm sinh bảng kết quả, số liệu, p-value, so sánh hiệu năng. Mục Experiments được thay bằng "Proposed evaluation protocol".

## 4. Quy trình viết (6 bước)

| Bước | Tên | Dùng LLM | Gate người dùng |
|---|---|---|---|
| W1 | Intake: kiểm tra đầu vào, dựng evidence index (giả thuyết ↔ tài liệu); **đọc StyleProfile do người dùng nhập** | Không | Không |
| W2 | Outline: 3 tiêu đề ứng viên, dàn ý từng section có mục tiêu số từ và gắn bằng chứng; **chuỗi rhetorical move trong profile làm khung cho dàn ý** | Có | **Có**: duyệt dàn ý |
| W3 | Draft: viết từng section theo thứ tự, **prompt kèm chỉ dẫn phong cách theo section; chấm phong cách nội bộ ngay sau khi sinh** | Có | Mỗi section: sửa, polish, finalize |
| W4 | Review: 3 reviewer (phương pháp, lĩnh vực, độ chặt chẽ) + kiểm tra claim so với bằng chứng + **reviewer phong cách (bộ kiểm tra nội bộ, không dùng LLM)** | Có | Chọn áp dụng từng nhận xét |
| W5 | Revise: sửa theo nhận xét đã chọn, kiểm tra độ dài; **chấm lại phong cách, lặp tối đa N vòng** | Có | Xem diff, chấp nhận hoặc hoàn tác |
| W6 | Export: LaTeX, BibTeX, kiểm tra citation; **báo cáo phong cách cuối cùng đi kèm gói tải về** | Gần như không | **Có**: duyệt trước khi tải |

Quy tắc quay lui: người dùng có thể quay lại bước trước. Các bước sau bị đánh dấu `stale` (không bị xóa) cho đến khi chạy lại.

### 4.1 Cấu trúc bài báo
Thứ tự section: Title, Abstract, Introduction, Related Work, Method, Proposed Evaluation (thay Experiments/Results ở chế độ proposal), Discussion, Limitations, Broader Impact, Conclusion, References.

Mục tiêu số từ (lấy từ `prompts/shared.py` `SECTION_WORD_TARGETS`): abstract 180–220, introduction 800–1000, related work 600–800, method 1000–1500, discussion 400–600, limitations 200–300, conclusion 200–300, broader impact 200–400.

### 4.2 Quy tắc nội dung (ép cả ở prompt lẫn kiểm tra sau)
- Mọi trích dẫn dạng `[cite_key]`, `cite_key` phải nằm trong `references[]`. Khóa lạ bị cờ lỗi và chặn xuất.
- Không số liệu thực nghiệm khi không có `results`. Bộ kiểm tra bắt các mẫu: bảng có số, "%" đi kèm so sánh, "p <", "outperforms".
- Tiêu đề tối đa 14 từ, dạng `MethodName: Subtitle` nếu có tên phương pháp.
- Mỗi hạn chế chỉ nêu một lần (ở Limitations). Không dùng văn phong rào đón ở các section khác.
- Ít nhất 15 tài liệu được trích trong Related Work nếu `references[]` đủ lớn; ngược lại báo cảnh báo thiếu tài liệu.

### 4.3 Dùng đầu ra của JSM làm đầu vào phong cách

**Nguyên tắc: PaperWriter là hệ thống riêng biệt và không kết nối với JSM.** Không gọi API của JSM, không dùng chung cơ sở dữ liệu, không phụ thuộc JSM đang chạy. JSM (System Journal Miner, `jsm-be`) chỉ là nơi sinh ra **tệp đầu ra**; người dùng xuất tệp đó từ JSM rồi nhập vào PaperWriter như một loại đầu vào, giống cách nhập BibTeX.

**Tệp đầu ra của JSM được hỗ trợ (đọc từ mã nguồn JSM, cần đối chiếu với tệp xuất thật)**
- `StyleProfile` (JSON) của một tạp chí, theo schema `app/modules/nlp/schemas/style_profile.py`: `journal_id`, `journal_name`, `total_articles_analyzed`, và `sections` theo `INTRO/BG/METHOD/RESULT/DISC/CONCL/ABS`. Mỗi section có phân phối độ dài câu P10–P90, tỷ lệ chủ động/bị động/ngôi "We"/vô nhân xưng, mức hedge và booster, `lexical_bundles`, `rhetorical_move_distribution`, `exemplars` (câu mẫu kèm DOI).
- (Tùy chọn) Báo cáo kiểm tra bản thảo (`ManuscriptCheckResultResponse`) của chính bản thảo người dùng: điểm phù hợp, cảnh báo, so sánh đặc trưng. PaperWriter dùng làm đầu vào cho bước sửa đầu tiên, không tự chấm lại bằng JSM.

**Nhập tệp**: tải lên JSON ở màn hình tạo dự án (tab "Journal style"). Hệ thống kiểm tra schema, lưu bản sao cùng `journal_id`, `snapshot_id`, ngày nhập vào dự án. Không có tệp này thì mọi tính năng phong cách tắt và phần còn lại hoạt động bình thường.

**Cách PaperWriter dùng StyleProfile**

| Bước | Hành động | Cần LLM |
|---|---|---|
| W1 | Đọc và kiểm tra tệp, hiển thị thẻ chuẩn mực của tạp chí (benchmark card) | Không |
| W2 | Khung dàn ý bám `rhetorical_move_distribution` của INTRO (Background → Gap → Purpose) | Có |
| W3 | Đưa vào prompt theo section: khoảng độ dài câu (P25–P75), tỷ lệ ngôi "We", mức hedge, vài bundle đặc trưng, 2–3 exemplar (chỉ để học văn phong, cấm chép nguyên văn) | Có |
| W3–W5 | **Bộ kiểm tra phong cách nội bộ** chấm lại văn bản so với profile (xem dưới) | Không |
| W4 | Reviewer phong cách: lấy kết quả bộ kiểm tra nội bộ thành nhận xét | Không |
| W5 | Cảnh báo chuyển thành chỉ dẫn sửa; chấm lại; dừng khi đạt ngưỡng hoặc hết N vòng (mặc định 2) | Có |
| W6 | Ghi `style_report.json` vào gói tải về | Không |

**Bộ kiểm tra phong cách nội bộ (`paperwriter/style/`)**
Vì không gọi JSM, PaperWriter tự tính một tập chỉ số đơn giản trên văn bản và so với profile:
- Phân vị độ dài câu và tỷ lệ câu nằm ngoài khoảng P10–P90.
- Tỷ lệ ngôi "We", câu bị động (quy tắc ngữ pháp hoặc spaCy), hedge và booster (từ điển).
- Tỷ lệ bundle đặc trưng của tạp chí xuất hiện trong bài.
- Điểm tổng hợp theo section và mức đánh giá (gần chuẩn / lệch vừa / lệch nhiều).

Hạn chế cần chấp nhận:
- Không phân loại được rhetorical move vì mô hình phân loại nằm trong JSM. Phần này dựa vào LLM (nhờ đánh nhãn câu theo taxonomy 11 nhãn) hoặc bỏ qua ở v1.
- Điểm của PaperWriter **không bằng** điểm của JSM, vì thuật toán và từ điển có thể khác. Giao diện ghi rõ "Style score (PaperWriter)" và không mượn tên JSM. Ai cần điểm gốc thì chạy bản thảo qua JSM.
- Từ điển hedge/booster tự xây dựng hoặc sao chép từ `jsm-be/app/modules/nlp/lexicons/` **sau khi được chủ JSM đồng ý**; ghi nguồn trong tài liệu.

**Cách trình bày**: điểm phong cách là gợi ý về độ gần với phân bố bài đã đăng của tạp chí, không phải điểm chất lượng bài báo. Bài cần có đủ nội dung khoa học trước; phong cách chỉ là lớp chỉnh sau.

**Bảng ánh xạ tạp chí → mẫu LaTeX** (`paperwriter/journal_map.yaml`): ví dụ `ieee-tse → generic`; thiếu ánh xạ thì người dùng chọn `venue` tay.

## 5. Giao diện (UI)

Một ứng dụng nhiều trang, bố cục workspace. Văn bản giao diện bằng tiếng Anh theo design system của team FE; có thể thêm `vi` qua file i18n.

### 5.1 Trang và route
| Route | Nội dung |
|---|---|
| `/` | Danh sách dự án, nút "New paper" |
| `/projects/new` | Form nhập liệu (U1) với 4 tab: Topic, Hypotheses, References, Settings; nút "Import from engine run" |
| `/projects/[id]` | Workspace chính, có thanh tiến trình 6 bước ở trên |
| `/projects/[id]/export` | Bước W6, xem trước và tải xuống |

### 5.2 Workspace (`/projects/[id]`)
Ba vùng:
- **Trái**: cây dàn ý và trạng thái từng section (`pending`, `ai_draft`, `human_edited`, `ai_polished`, `finalized`, `stale`). Kéo thả đổi thứ tự section ở bước Outline.
- **Giữa**: trình soạn thảo của section đang chọn (Markdown, có xem trước). Thanh công cụ: Generate, Regenerate, AI polish (có ô hướng dẫn), Finalize, Undo/Redo, so sánh `ai_version` với `human_version`.
- **Phải**: panel ngữ cảnh gồm Evidence (giả thuyết và tài liệu gắn với section), Citations (chèn `[key]` bằng tìm kiếm), Checks (vi phạm quy tắc 4.2, đếm từ so với mục tiêu), Review comments (bước W4), **Style**: điểm phù hợp của section, boxplot độ dài câu so với P10–P90 của tạp chí, các chỉ số ngôi/bị động/hedge so với chuẩn, cảnh báo, và exemplar kèm liên kết DOI. Nút "Apply as instruction" biến một cảnh báo thành chỉ dẫn cho AI polish.
- **Thanh trên**: thẻ chuẩn mực (benchmark card) của tạp chí lấy từ tệp StyleProfile đã nhập; nút "Import style profile".

### 5.3 Hành vi tương tác bắt buộc
- Sinh nội dung dạng **streaming** (token hiện dần), có nút Stop.
- Tự động lưu bản nháp sau 1.5 giây không gõ; hiển thị "Saved" hoặc "Saving…".
- Mọi thao tác dài có trạng thái tải, lỗi có nút Retry. Không giả lập dữ liệu: nếu backend chưa sẵn sàng, hiển thị trạng thái "API pending" thật.
- Thanh Checks cập nhật tức thì khi sửa nội dung.
- Phím tắt: `Ctrl+S` lưu, `Ctrl+Enter` Generate, `Ctrl+Z` hoàn tác.
- Trình duyệt hẹp (375px) không tràn ngang; workspace chuyển sang 1 cột với tab chuyển vùng.

### 5.4 Đường dẫn hạnh phúc (happy path)
`New paper` → nhập liệu → `Generate outline` → chỉnh và `Approve outline` → `Draft all sections` (hoặc từng section) → sửa và `Finalize` → `Run review` → chọn nhận xét → `Revise` → `Export` → tải `.zip`.

## 6. Kiến trúc

```
Browser (Next.js 15, React 19, TanStack Query)
   │  same-origin /api/*  (Next route handlers = BFF, giữ khóa phía server)
   ▼
PaperWriter API (FastAPI, cổng 8002)  ── paperwriter/
   ├─ intake, stages W1..W6, checks, export
   ├─ store: SQLite (dự án, section, phiên bản, review) + thư mục file
   ├─ style/: đọc StyleProfile đã nhập + bộ kiểm tra phong cách nội bộ
   └─ LLM: researchclaw.llm.create_llm_client (tái dùng)

JSM là hệ thống riêng; chỉ trao đổi bằng tệp JSON do người dùng xuất rồi nhập. Không có kết nối mạng giữa hai hệ thống.
```

- Frontend: thư mục mới `paperwriter-web/` trong repo, Next.js 15 App Router + TypeScript + TanStack Query v5. Cấu trúc feature-folder giống `ResearchPulse-Publication-Repository-FE` (`features/<name>/{api,hooks,views,components,styles,types.ts,index.ts}`; trang trong `app/` mỏng).
- Style: dùng token và component từ `@hyperdata/design-system` của team FE (copy gói hoặc tham chiếu `file:`), font Manrope, màu chính `#0071bc`. Không dùng Tailwind.
- Backend: mở rộng `paperwriter/` hiện có (đã có `contracts.py`, `intake.py`, `app.py`, `routes/runs.py`).
- Streaming: Server-Sent Events từ FastAPI qua BFF (cùng cách team đã dùng cho notification SSE).

## 7. Mô hình dữ liệu (SQLite)

| Bảng | Trường chính |
|---|---|
| `projects` | id, title, topic, venue, language, mode (`proposal`/`with_results`), status, current_step, created_at, updated_at |
| `hypotheses` | id, project_id, key, statement, rationale, falsifiable_by |
| `references` | id, project_id, cite_key (unique theo dự án), title, authors, year, venue, abstract, doi, url |
| `sections` | id, project_id, name, position, status, target_words |
| `section_versions` | id, section_id, kind (`ai`/`human`/`polish`/`revise`), content, created_at, note |
| `outlines` | id, project_id, title_candidates (JSON), chosen_title, content, approved_at |
| `reviews` | id, project_id, reviewer (`A`/`B`/`C`), content, items (JSON: id, section, text, severity, decision) |
| `runs` | id, project_id, step, status, started_at, finished_at, error, tokens_in, tokens_out |
| `exports` | id, project_id, path, verification_report (JSON), style_report (JSON), created_at |
| `style_profiles` | id, project_id, journal_id, snapshot_id, profile (JSON), source_filename, imported_at |
| `style_checks` | id, project_id, section_id (nullable), version_id, score, rating_level, warnings (JSON), features (JSON), created_at |

`projects` có thêm cột `style_enabled` (boolean, mặc định bật khi có profile).

`section_versions` giữ toàn bộ lịch sử để hoàn tác và so sánh.

## 8. API (FastAPI, tiền tố `/api`)

Xác thực: header `X-Service-Key` giữa BFF và API; người dùng vào web bằng một mật khẩu truy cập cấu hình qua biến môi trường (v1). Không đưa khóa vào trình duyệt.

| Method | Đường dẫn | Mô tả |
|---|---|---|
| GET/POST | `/projects` | Liệt kê, tạo dự án |
| GET/PATCH/DELETE | `/projects/{id}` | Chi tiết, cập nhật, xóa |
| PUT | `/projects/{id}/hypotheses` | Thay toàn bộ danh sách |
| PUT/POST | `/projects/{id}/references` , `/references/import-bibtex` | Quản lý tài liệu |
| POST | `/projects/{id}/import-engine-run` | U6 |
| POST | `/projects/{id}/outline/generate` | W2 (SSE) |
| POST | `/projects/{id}/outline/approve` | Gate W2 |
| POST | `/projects/{id}/sections/{name}/generate` | W3 (SSE) |
| POST | `/projects/{id}/sections/{name}/polish` | Body: `instructions` (SSE) |
| PUT | `/projects/{id}/sections/{name}` | Lưu bản sửa tay |
| POST | `/projects/{id}/sections/{name}/finalize` | Khóa section |
| GET | `/projects/{id}/sections/{name}/versions` | Lịch sử |
| POST | `/projects/{id}/review/run` | W4 (SSE) |
| PATCH | `/projects/{id}/review/items/{item}` | Chọn áp dụng hoặc bỏ qua |
| POST | `/projects/{id}/revise` | W5 (SSE) |
| GET | `/projects/{id}/checks` | Kết quả kiểm tra 4.2 |
| POST | `/projects/{id}/style/profile` | Nhập tệp StyleProfile JSON (kiểm tra schema) |
| GET/DELETE | `/projects/{id}/style/profile` | Xem hoặc gỡ profile đã nhập |
| POST | `/projects/{id}/style/check` | Chấm phong cách nội bộ toàn bài hoặc một section (`section` tùy chọn) |
| GET | `/projects/{id}/style/history` | Lịch sử điểm phong cách qua các phiên bản |
| POST | `/projects/{id}/export` | W6 |
| GET | `/projects/{id}/export/download` | Tải `.zip` |
| POST | `/runs/{id}/cancel` | Dừng tác vụ đang chạy |
| GET | `/health` | Kiểm tra sống |

Sự kiện SSE: `token`, `section.progress`, `step.completed`, `error`, `done`.
Mã lỗi theo contract: `W01_BUNDLE_INVALID` … `W06_EXPORT_FAIL` (xem `paperwriter/contracts.py`).

## 9. LLM và chi phí

- Dùng `researchclaw.llm.create_llm_client`. Cấu hình bằng YAML `llm:` (xem `config.researchclaw.example.yaml`), khóa lấy từ biến môi trường (`OPENAI_API_KEY` hoặc provider khác).
- Cho phép cấu hình riêng **model reviewer** khác model writer.
- Ghi `tokens_in/out` mỗi lần chạy; hiển thị tổng token đã dùng cho dự án. Có hạn mức tối đa mỗi dự án (cấu hình), vượt thì chặn và báo.
- Prompt: chuyển từ `researchclaw/prompts/ml.py` (`paper_outline`, `paper_draft`, `peer_review`, `paper_revision`) về `paperwriter/prompts/`, **sửa lại** cho chế độ proposal (bỏ yêu cầu bảng kết quả, hình từ `charts/`, p-value). Giữ khối quy tắc trong `prompts/shared.py`.

## 10. Kiểm tra citation (W6)

1. Mọi `[key]` trong bài phải có trong `references[]`.
2. Mọi mục trong `references[]` được trích ít nhất một lần, nếu không cảnh báo.
3. Tùy chọn: đối chiếu DOI/tiêu đề với OpenAlex hoặc Semantic Scholar. Tắt được. Kết quả ghi vào `verification_report.json` (`ok`, `unknown_keys[]`, `uncited[]`, `unresolved[]`).
Có `unknown_keys` thì Export bị chặn.

## 11. Yêu cầu phi chức năng

- **Hiệu năng**: phản hồi đầu tiên của streaming dưới 3 giây (không tính độ trễ của nhà cung cấp LLM); lưu nháp dưới 300 ms.
- **Độ bền**: trạng thái dự án lưu SQLite, không mất khi khởi động lại. Tác vụ đang chạy khi restart được đánh dấu `interrupted` và cho phép chạy lại.
- **Bảo mật**: khóa API chỉ ở server; sanitize Markdown khi xem trước; giới hạn kích thước tải lên (10 MB); chống path traversal ở import run dir (chỉ thư mục nằm trong danh sách cho phép cấu hình).
- **Độc lập với JSM**: không có phụ thuộc thời gian chạy vào JSM. Tệp profile sai schema bị từ chối với thông báo rõ; tệp hợp lệ nhưng thiếu section thì chỉ tắt kiểm tra cho section đó.
- **Khả năng truy cập**: đạt các điều khoản trong design system (tương phản >= 4.5:1, nút >= 44px, focus ring, `role="alert"/"status"`).
- **Trình duyệt**: Chrome, Edge, Firefox bản hiện hành; hoạt động tới 375px.
- **Kiểm thử**: backend có unit test với LLM giả; frontend có test thành phần chính và một kịch bản e2e happy path.

## 12. Mở rộng sau (ngoài v1)
- Nhập `results/` (bảng, hình) từ hệ thống thực nghiệm, chuyển chế độ `with_results` và bật lại quy tắc bảng/p-value.
- Xuất PDF biên dịch sẵn (cần TeX trên máy chủ).
- Đa người dùng, đăng nhập OIDC như FE chính, quyền theo vai trò.
- Overleaf sync, i18n bài báo tiếng Việt.

## 13. Câu hỏi còn mở (cần bạn xác nhận)
1. Web này **nằm trong repo này** (`paperwriter-web/`) hay tích hợp vào FE chính `ResearchPulse-Publication-Repository-FE`?
2. Một người dùng hay nhiều người dùng (có đăng nhập)?
3. Provider LLM bạn sẽ dùng và có hạn mức chi phí nào không?
4. Bài báo v1 chỉ ở chế độ proposal (không số liệu) có đủ cho mục tiêu học phần không?
5. Có xuất được StyleProfile từ JSM ra tệp JSON không (có sẵn chức năng xuất, hay phải chạy `POST /nlp/build-profile` hoặc lấy từ cơ sở dữ liệu)? Cần một tệp mẫu thật để chốt schema nhập.
6. JSM hiện có hồ sơ cho những tạp chí nào, và có phù hợp lĩnh vực bài báo của bạn không?
7. Chủ JSM có đồng ý cho sao chép từ điển hedge/booster (`lexicons/*.txt`) sang PaperWriter không? Nếu không thì tự xây dựng từ điển.
