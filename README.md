# eform-builder

Bộ công cụ cấu hình **Eform dạng bảng** trên *Nền tảng khai phá dữ liệu động* từ file Excel:

- Đọc sheet Excel thành `spec.json`: tên Eform, cột cố định, cột số, cây cột nhóm tối đa 3 tầng.
- **Rà soát lỗi chính tả/dữ liệu tiếng Việt**, xuất danh sách phát hiện và phiếu duyệt Excel.
- **Chỉ sửa dữ liệu khi người dùng duyệt từng dòng** (hỏi từng dòng, hoặc điền phiếu `duyet.xlsx`).
- Dựng Eform trên hệ thống qua trình duyệt: chạy thử trước, chỉ Lưu nháp, đối chiếu lại với spec.

Hệ thống được clone cho nhiều đơn vị nên domain không cố định. Script tự nhận domain từ tab đang mở, hoặc nhận qua `--base-url`.

## Dùng với công cụ nào

| Bạn dùng | Cách dùng |
|---|---|
| **Claude Code** | Chép thư mục vào `~/.claude/skills/eform-builder`. Gọi `/eform-builder` hoặc nói "cấu hình eform từ excel". |
| **AI khác hỗ trợ SKILL.md** (Codex CLI, Gemini CLI, Cursor, Copilot, …) | Chép thư mục vào thư mục skills của công cụ đó (xem tài liệu của công cụ). AI đọc `SKILL.md`. |
| **AI khác chạy được lệnh nhưng không hỗ trợ skill** | Mở thư mục này làm thư mục làm việc; AI đọc `AGENTS.md` rồi `SKILL.md`. |
| **AI chat trên web** (ChatGPT, Gemini, …) hoặc **không dùng AI** | Làm theo [`HUONG_DAN_CHAY_TAY.md`](HUONG_DAN_CHAY_TAY.md). |

| Trình duyệt | Cách điều khiển | Cài thêm |
|---|---|---|
| Chrome, Edge, Cốc Cốc, Brave, Chromium | CDP: `scripts/browser.py open` mở cửa sổ riêng có cổng điều khiển | Không |
| Firefox, WebKit (nhân Safari) | Playwright: script tự mở cửa sổ, người dùng đăng nhập | `pip install playwright` + `playwright install firefox webkit` |
| Safari thật | Không hỗ trợ. Dùng `--browser webkit` hoặc trình duyệt khác. | |

Hệ điều hành: Windows, macOS, Linux. Windows dùng `python` hoặc `py` thay cho `python3`.

## Cài đặt

```bash
python3 -m pip install openpyxl
git clone https://github.com/trucvanne/eform-builder.git ~/.claude/skills/eform-builder   # Claude Code
```

Người dùng tự đăng nhập; công cụ không nhập mật khẩu.

## Cấu trúc

```
SKILL.md                    quy trình + quy tắc bắt buộc (Claude Code và AI hỗ trợ SKILL.md)
AGENTS.md                   bản rút gọn cho AI khác
HUONG_DAN_CHAY_TAY.md       chạy tay từng bước, không cần AI
scripts/excel_to_spec.py    Excel → spec.json
scripts/review_spec.py      rà soát → findings.json + bảng Markdown + phiếu duyệt duyet.xlsx
scripts/vn_text.py          kiểm tra âm tiết, kiểu bỏ dấu, viết hoa tiếng Việt
scripts/approval_sheet.py   ghi/đọc phiếu duyệt Excel
scripts/apply_fixes.py      chỉ áp dụng các dòng đã duyệt (approvals.json hoặc duyet.xlsx) → spec mới + changelog
scripts/browser.py          tìm/mở trình duyệt; lớp điều khiển CDP / Playwright
scripts/eform_builder.py    dựng / lưu / đối chiếu Eform trên hệ thống
scripts/cdp.py              client Chrome DevTools Protocol tối giản
scripts/common.py           tiện ích chung (in tiếng Việt trên Windows)
references/ui-notes.md      bản đồ giao diện, API đọc lại, điểm dễ lỗi
examples/                   spec mẫu, findings mẫu, approvals mẫu
```

## Chạy nhanh

```bash
python3 scripts/browser.py open --url "https://<domain-đơn-vị>/authenticate"     # đăng nhập trong cửa sổ này
python3 scripts/excel_to_spec.py BieuMau.xlsx --sheet Tinh --key tinh --group "Tên nhóm" --attr TenThuocTinh --fixed "B,C,D" --spec spec.json
python3 scripts/review_spec.py spec.json --source-title "BIỂU MẪU BC THÁNG 8" --out findings.json --xlsx duyet.xlsx
# … người dùng duyệt từng dòng trong duyet.xlsx (hoặc trả lời từng câu hỏi → approvals.json)
python3 scripts/apply_fixes.py spec.json findings.json duyet.xlsx --out spec.fixed.json
python3 scripts/eform_builder.py build  --spec spec.fixed.json --form tinh          # chạy thử, không lưu
python3 scripts/eform_builder.py build  --spec spec.fixed.json --form tinh --save   # Lưu nháp
python3 scripts/eform_builder.py verify --spec spec.fixed.json --form tinh
```

Firefox/WebKit: thêm `--browser firefox --base-url "https://<domain-đơn-vị>"` vào các lệnh `eform_builder.py`, bỏ lệnh `browser.py open`.
