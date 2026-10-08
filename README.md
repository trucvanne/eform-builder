# eform-builder

Skill cho Claude Code dùng để cấu hình **Eform dạng bảng** trên *Nền tảng khai phá dữ liệu động* từ file Excel:

- Đọc sheet Excel thành `spec.json`: tên Eform, cột cố định, cột số, cây cột nhóm tối đa 3 tầng.
- **Rà soát lỗi chính tả/dữ liệu tiếng Việt** và xuất danh sách phát hiện theo từng dòng.
- **Chỉ sửa dữ liệu khi người dùng duyệt từng dòng** (`approvals.json`).
- Dựng Eform trên hệ thống qua Chrome DevTools Protocol:
  - Dry-run trước, chỉ Lưu nháp.
  - Đối chiếu lại dữ liệu đã lưu với spec.

Hệ thống được clone cho nhiều đơn vị nên domain không cố định. Script tự nhận domain từ tab đang mở, hoặc nhận qua `--base-url`.

## Cài đặt

```bash
pip install openpyxl
# cài cho Claude Code (mức người dùng)
mkdir -p ~/.claude/skills && cp -R eform-builder ~/.claude/skills/
```

Cần Google Chrome. Người dùng tự đăng nhập; skill không nhập mật khẩu.

## Cấu trúc

```
SKILL.md                    hướng dẫn quy trình + quy tắc bắt buộc
scripts/excel_to_spec.py    Excel → spec.json
scripts/review_spec.py      rà soát → findings.json + bảng Markdown
scripts/vn_text.py          kiểm tra âm tiết, kiểu bỏ dấu, viết hoa tiếng Việt
scripts/apply_fixes.py      chỉ áp dụng các dòng đã duyệt → spec mới + changelog
scripts/eform_builder.py    dựng / lưu / đối chiếu Eform trên hệ thống
scripts/cdp.py              client Chrome DevTools Protocol tối giản
references/ui-notes.md      bản đồ giao diện, API đọc lại, điểm dễ lỗi
examples/                   spec mẫu, findings mẫu, approvals mẫu
```

## Chạy nhanh

```bash
python3 scripts/excel_to_spec.py BieuMau.xlsx --sheet Tinh --key tinh --group "Biểu mẫu Kiểm soát TTHC" --attr TTHC_CapTinh --fixed "B,C,D" --spec spec.json
python3 scripts/review_spec.py spec.json --source-title "BIỂU MẪU BC THÁNG 8" --out findings.json
# … người dùng duyệt từng dòng → approvals.json
python3 scripts/apply_fixes.py spec.json findings.json approvals.json --out spec.fixed.json
python3 scripts/eform_builder.py build --spec spec.fixed.json --form tinh          # dry-run
python3 scripts/eform_builder.py build --spec spec.fixed.json --form tinh --save   # Lưu nháp
python3 scripts/eform_builder.py verify --spec spec.fixed.json --form tinh
```
