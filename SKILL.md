---
name: eform-builder
description: Cấu hình Eform dạng bảng (x-table, cố định số dòng, cột nhóm nhiều tầng) trên Nền tảng khai phá dữ liệu động từ file Excel, kèm bước rà soát lỗi chính tả/dữ liệu và chỉ sửa dữ liệu khi người dùng duyệt từng dòng. Dùng khi người dùng nói "cấu hình eform từ excel", "tạo eform theo sheet", "rà soát chính tả eform", "kiểm tra dữ liệu biểu mẫu trước khi cấu hình", hoặc đưa file Excel biểu mẫu báo cáo cần đưa lên hệ thống Eform.
---

# Eform builder – cấu hình Eform từ Excel, có rà soát và duyệt từng dòng

Hệ thống Eform được clone cho nhiều đơn vị nhà nước nên **domain không cố định**. Không gắn cứng địa chỉ: lấy từ tab Chrome đang mở trang danh sách Eform, hoặc hỏi người dùng.

## Quy tắc bắt buộc

1. **Không tự đăng nhập.** Không gõ mật khẩu. Mở Chrome riêng (lệnh ở Bước 0), người dùng tự đăng nhập và mở trang danh sách Eform.
2. **Chỉ sửa dữ liệu khi được duyệt từng dòng.**
   - Mỗi phát hiện của bước rà soát là **1 câu hỏi riêng** (AskUserQuestion, tối đa 4 câu/lượt). Không gộp nhiều dòng vào 1 câu, không tự sửa.
   - Tùy chọn: `Sửa: <giá trị đề xuất>` / `Giữ nguyên`. Người dùng dùng **Other** để tự nhập giá trị khác.
   - Câu bị bỏ qua hoặc đóng = **giữ nguyên**.
   - Ghi kết quả vào `approvals.json` rồi mới chạy `apply_fixes.py`.
3. **Chỉ Lưu nháp.** Không bấm Phát hành, Phân quyền, Thu hồi, Hủy, Xóa nếu người dùng không yêu cầu rõ.
4. **Không đụng Eform đã gửi đi/đang dùng** trừ khi người dùng yêu cầu đích danh.
5. **Dry-run trước, lưu sau.**
   - Chạy `build` không có `--save` để dựng thử rồi hủy bỏ.
   - Chỉ lưu thật khi người dùng đồng ý.
   - Sau khi lưu, đối chiếu dữ liệu gửi lên (script tự làm) và chạy `verify`.
6. **Ghi nhãn khi suy luận.** Cây cột nhóm, tên cột suy từ biểu chuẩn, đề xuất chính tả theo luật đều là suy luận: ghi rõ và hỏi xác nhận.

## Quy trình

### Bước 0 – Chuẩn bị
- Cần Python 3.9+, `pip install openpyxl`, Google Chrome.
- Mở Chrome riêng có cổng điều khiển:
  ```bash
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --remote-debugging-port=9334 --user-data-dir="$HOME/.eform-builder-chrome" "https://<domain-đơn-vị>/authenticate"
  ```
- Nhờ người dùng đăng nhập, vào nền tảng có menu **Quản lý Eform**, mở **Danh sách Eform**.

### Bước 1 – Đọc Excel thành spec
```bash
python3 scripts/excel_to_spec.py file.xlsx --sheet <Sheet> --key <khoa> --group "<Nhóm>" --attr <ThuocTinhBang> --fixed "B,C,D" --spec spec.json
```
- Mỗi sheet là 1 form. Tên Eform lấy từ ô `B1` ("Tên eform: …").
- Cột trong `--fixed` thành cột Text có dữ liệu cố định từng dòng. Cột còn lại thành Number để đơn vị nhập.
- Bỏ cột A (STT) vì bảng tự đánh STT.
- Xem cảnh báo **tiêu đề cột trùng**: đối chiếu sheet ẩn/biểu chuẩn trong file (vd biểu 07b) để đặt tên đúng, rồi hỏi người dùng.

### Bước 2 – Dựng cây cột nhóm (nếu có)
- Tiêu đề phẳng dạng `"Nhóm - Con"`, hoặc biểu chuẩn có ô gộp → chuyển thành `children` trong spec. Hệ thống hỗ trợ 3 tầng.
- **Cột lá giữ `attr` là tên đầy đủ, không trùng**, vd `Số lượng hồ sơ đã giải quyết - Tổng số`. Tiêu đề hiển thị có thể ngắn (`Tổng số`).
- Đưa cây cột cho người dùng xác nhận trước khi dựng. Mẫu: `examples/spec.example.json`.

### Bước 3 – Rà soát lỗi (bắt buộc trước khi cấu hình)
```bash
python3 scripts/review_spec.py spec.json --source-title "<tên file/tiêu đề kỳ báo cáo>" --out findings.json
```
Script kiểm tra:
- Từ không giống âm tiết tiếng Việt (nghi lỗi gõ).
- Kiểu bỏ dấu lệch nhau (hòa/hoà, thủy/thuỷ). Riêng "qu" là phụ âm đầu: quỹ, quý không tính.
- Viết hoa giữa cụm từ; tên cơ quan viết hoa mọi âm tiết.
- Tiền tố thừa chỉ có ở một phần danh sách (vd "Lĩnh vực …").
- Khoảng trắng, chuẩn Unicode.
- Trùng giá trị; trùng tiêu đề cột cùng cấp; trùng thuộc tính cột lá.
- Giá trị là tên cơ quan trong cột lĩnh vực.
- Kỳ báo cáo lệch với tên nguồn; tên các Eform không cùng mẫu.

Đọc thêm danh sách bằng mắt để bắt lỗi chính tả mà luật không thấy. Tự thêm vào findings với nhãn `[suy luận]`.

### Bước 4 – Hỏi duyệt từng dòng
- Trình bày bảng `No. | Vị trí | Hiện tại | Đề xuất | Lý do`.
- Hỏi lần lượt từng phát hiện theo Quy tắc 2.
- Ghi `approvals.json`, vd: `{"F015": "approve", "F016": {"value": "…"}, "F002": "reject"}`.
```bash
python3 scripts/apply_fixes.py spec.json findings.json approvals.json --out spec.fixed.json --log changelog.md
```
- Chỉ dòng `approve` hoặc `{"value"}` mới bị đổi. Script kiểm tra giá trị hiện tại trước khi ghi.
- Báo người dùng nội dung `changelog.md`.

### Bước 5 – Cấu hình lên hệ thống
```bash
python3 scripts/eform_builder.py build --spec spec.fixed.json --form <khoa>            # dry-run, tự hủy bỏ
python3 scripts/eform_builder.py build --spec spec.fixed.json --form <khoa> --save     # khi người dùng đồng ý
python3 scripts/eform_builder.py verify --spec spec.fixed.json --form <khoa>           # đọc lại server, so spec
```
- Nhóm Eform phải có sẵn. Nếu chưa có, hỏi người dùng rồi tạo tại **Quản lý nhóm Eform → Thêm mới**.
- Thêm `--base-url https://<domain>` khi Chrome mở nhiều hệ thống.

### Bước 6 – Báo cáo
Nêu cho người dùng:
- Tên Eform, nhóm, số dòng, cây cột, trạng thái (Lưu nháp).
- Kết quả đối chiếu.
- Các dòng đã/không sửa.
- Việc còn lại: phát hành, phân quyền, banner. Những việc này **không tự làm**.

## Tham khảo
- `references/ui-notes.md`: bản đồ giao diện, selector, API đọc lại, các điểm dễ lỗi.
- `scripts/cdp.py`: client CDP tối giản, có chế độ daemon cho thao tác lẻ.
