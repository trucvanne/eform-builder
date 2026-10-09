# Ghi chú giao diện Eform (Nền tảng khai phá dữ liệu động)

Đường dẫn tương đối, áp dụng cho mọi domain đơn vị:

| Màn hình | Đường dẫn |
|---|---|
| Danh sách E-Form | `/list-eform` |
| Chi tiết E-Form (tạo/sửa) | `/detail-eform` |
| Nhập liệu một Eform | `/e-form/<uuid>` |
| Quản lý nhóm Eform | `/quan-ly-nhom-eform` |
| Quản lý component Eform | `/ql-component-eform` |

## Chi tiết E-Form
- `input[placeholder="Nhập tên E-Form"]` là tên Eform.
- Ô **Nhóm**: chữ "Chọn nhóm" mở popover `.MuiPopover-root`, lựa chọn là text tên nhóm.
- Bảng **Danh sách thuộc tính**, dòng 1: `tbody [role=combobox]` là Loại Control (chọn `x-table`).
  - Ba ô `input[type=text]` theo thứ tự: Tên thuộc tính, Tiêu đề hiển thị, Mô tả.
  - Nút `button[title="Chỉnh sửa"]` mở hộp thoại **Cấu hình Meta data**.
- Nút **Lưu** (xanh lá) và **Hủy bỏ**. Hủy bỏ luôn hỏi "Xác nhận hủy bỏ"; bấm **Đồng ý** để thoát.

## Hộp thoại Cấu hình Meta data (x-table)
- Toggle **Cố định số dòng**, **Ẩn cột STT mặc định**, **Cố định dòng tiêu đề**; ô **Số cột cố định**.
- Mỗi cột có các ô: `input[placeholder="Nhập tiêu đề..."]`, `input[placeholder="Nhập thuộc tính..."]`, `[role=combobox]` KIỂU (Date, Number, Text, Select, Radio, Checkbox), `input[placeholder="Auto"]` RỘNG (PX).
- Nút THAO TÁC theo `title`:
  - `Xóa cột`
  - `Thêm cột cùng cấp`: chèn ngay sau **toàn bộ cây con** của cột đó.
  - `Thêm cột con (nhóm)`: biến cột thành **Nhóm** (không còn KIỂU/RỘNG) và tạo con đầu tiên. Con cũng có nút này nên hỗ trợ 3 tầng; dữ liệu lưu ở `children`.
  - Nút không có title (biểu tượng ghim, có huy hiệu số dòng): mở **Dữ liệu cố định** của cột. Nút chỉ có khi bật Cố định số dòng.
- Panel **Dữ liệu cố định — cột "…" (n dòng)**:
  - Ô số + nút **Thêm** (tối đa 50 dòng/lần) và nút **Thêm dòng**.
  - Mỗi dòng là một `input[placeholder="Nhập nội dung..."]`.
  - Bấm lại nút ghim để thu gọn.
- **Lưu** ghi cấu hình vào thuộc tính; dữ liệu chỉ lên server khi bấm **Lưu** của màn hình Chi tiết E-Form.

## Điểm dễ lỗi
- **Cột mới tạo lưu kiểu `null`** dù giao diện hiện "Text". Cách sửa: chọn kiểu khác rồi chọn lại Text.
- Ô nhập là React controlled: nhập bằng focus + select + chèn chữ thật (`Input.insertText` của CDP, `keyboard.insert_text` của Playwright). Không gán `.value` trực tiếp.
- Nút trong hộp thoại: dùng `element.click()` (JS) cho ổn định. Click chuột theo tọa độ dễ trượt khi danh sách đang render lại.
- Combobox/lựa chọn MUI: dùng click chuột thật (sự kiện `isTrusted`), không dùng `element.click()`.
- Playwright (Firefox/WebKit): chờ bằng `page.wait_for_timeout`, không dùng `time.sleep` khi cần đọc `page.url`, vì Playwright chỉ cập nhật trạng thái khi có lệnh gọi.
- Đánh dấu thuộc tính trong nội dung: gõ `[[` + vài ký tự rồi Enter để chọn gợi ý. Gõ tay đủ `[[ten]]` mà không chọn gợi ý thì không thành control.
- Mở lại trang danh sách sau khi lưu: thứ tự dòng thay đổi theo ngày cập nhật. Luôn tìm dòng theo **tên**, không theo vị trí.

## API đọc lại (chỉ đọc, dùng cookie phiên của trình duyệt)
Token nằm trong bộ nhớ ứng dụng, nên script móc vào XHR của trang thay vì gọi API riêng:
- Khi mở **Chỉnh sửa eform**: `GET /api/eform-service/api/v1/eform/find-by-id/<id>`. Trường `metadata[0].fields[]` có `description` (tiêu đề), `fieldName` (thuộc tính), `typeControl`, `widthColumn`, `fixedRowValues`, `children`.
- Khi **Lưu**: `POST …/eform/create` (tạo mới) hoặc `…/eform/update`; body là JSON cấu hình đầy đủ.

## Quy ước dữ liệu đang dùng (tham khảo)
- Biểu mẫu báo cáo: 1 x-table, bật Cố định số dòng.
  - Các cột định danh dòng (lĩnh vực/chỉ tiêu, năm, kỳ) có dữ liệu cố định.
  - Cột số để đơn vị nhập.
- THUỘC TÍNH cột thường đặt trùng TIÊU ĐỀ (tiếng Việt). Riêng cột lá trong nhóm dùng tên đầy đủ để không trùng khóa.
- Trường lựa chọn: giá trị = nhãn (vd "Tháng 1", "Năm 2026").
