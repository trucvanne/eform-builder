---
name: eform-builder
description: Cấu hình Eform dạng bảng (x-table, cố định số dòng, cột nhóm nhiều tầng) trên Nền tảng khai phá dữ liệu động từ file Excel, kèm bước rà soát lỗi chính tả/dữ liệu và chỉ sửa dữ liệu khi người dùng duyệt từng dòng. Dùng khi người dùng nói "cấu hình eform từ excel", "tạo eform theo sheet", "rà soát chính tả eform", "kiểm tra dữ liệu biểu mẫu trước khi cấu hình", hoặc đưa file Excel biểu mẫu báo cáo cần đưa lên hệ thống Eform.
---

# Eform builder – cấu hình Eform từ Excel, có rà soát và duyệt từng dòng

Hệ thống Eform được clone cho nhiều đơn vị nhà nước nên **domain không cố định**. Không gắn cứng địa chỉ: lấy từ tab trình duyệt đang mở trang danh sách Eform, hoặc hỏi người dùng.

Skill chạy được trên Windows, macOS, Linux; với Chrome, Edge, Cốc Cốc, Brave, Chromium, Firefox, WebKit; với mọi AI chạy được lệnh trên máy (hoặc không cần AI: xem `HUONG_DAN_CHAY_TAY.md`).

## Quy tắc bắt buộc

1. **Không tự đăng nhập.** Không gõ mật khẩu. Mở trình duyệt riêng (Bước 0), người dùng tự đăng nhập và mở trang danh sách Eform.
2. **Chỉ sửa dữ liệu khi được duyệt từng dòng.** Không gộp nhiều dòng vào 1 câu, không tự sửa. Chọn 1 trong 2 cách:
   - **Hỏi trong khung chat**: mỗi phát hiện là **1 câu hỏi riêng**. Nếu công cụ có hộp hỏi đáp (vd `AskUserQuestion` của Claude Code, tối đa 4 câu/lượt) thì dùng nó; nếu không, hỏi từng dòng bằng tin nhắn và chờ trả lời. Tùy chọn: `Sửa: <giá trị đề xuất>` / `Giữ nguyên` / người dùng tự gõ giá trị khác. Câu bị bỏ qua = **giữ nguyên**. Ghi kết quả vào `approvals.json`.
   - **Phiếu Excel `duyet.xlsx`** (do `review_spec.py` tạo): người dùng chọn cột *Quyết định* cho từng dòng. Dòng để trống = giữ nguyên.
   - Chỉ sau đó mới chạy `apply_fixes.py`.
3. **Chỉ Lưu nháp.** Không bấm Phát hành, Phân quyền, Thu hồi, Hủy, Xóa nếu người dùng không yêu cầu rõ.
4. **Không đụng Eform đã gửi đi/đang dùng** trừ khi người dùng yêu cầu đích danh.
5. **Dry-run trước, lưu sau.**
   - Chạy `build` không có `--save` để dựng thử rồi hủy bỏ.
   - Chỉ lưu thật khi người dùng đồng ý.
   - Sau khi lưu, đối chiếu dữ liệu gửi lên (script tự làm) và chạy `verify`.
6. **Ghi nhãn khi suy luận.** Cây cột nhóm, tên cột suy từ biểu chuẩn, đề xuất chính tả theo luật đều là suy luận: ghi rõ và hỏi xác nhận.

## Quy trình

Lệnh dưới đây viết `python3`. Trên Windows dùng `python` hoặc `py`. Các script nằm trong thư mục `scripts/` của skill.

### Bước 0 – Chuẩn bị
- Cần Python 3.9+ và `pip install openpyxl`.
- Mở trình duyệt riêng có cổng điều khiển (hồ sơ riêng, không đụng trình duyệt chính):
  ```bash
  python3 scripts/browser.py list                                                  # xem máy có trình duyệt nào
  python3 scripts/browser.py open --browser auto --url "https://<domain-đơn-vị>/authenticate"
  ```
  - `--browser chrome|edge|coccoc|brave|chromium` để chọn cụ thể; `--browser-path "<đường dẫn>"` nếu cài ở chỗ khác.
  - **Firefox / WebKit (nhân Safari)**: không cần lệnh `open`. Cài `pip install playwright` và `playwright install firefox webkit`, rồi ở Bước 5 thêm `--browser firefox --base-url https://<domain>`; script tự mở cửa sổ và chờ người dùng đăng nhập.
  - Safari thật không hỗ trợ điều khiển kiểu này: dùng `--browser webkit` hoặc trình duyệt khác.
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
python3 scripts/review_spec.py spec.json --source-title "<tên file/tiêu đề kỳ báo cáo>" --out findings.json --xlsx duyet.xlsx
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

### Bước 4 – Duyệt từng dòng
- Trình bày bảng `No. | Vị trí | Hiện tại | Đề xuất | Lý do`.
- Duyệt theo Quy tắc 2: hỏi từng dòng (ghi `approvals.json`, vd `{"F015": "approve", "F016": {"value": "…"}, "F002": "reject"}`) **hoặc** đưa `duyet.xlsx` cho người dùng điền.
```bash
python3 scripts/apply_fixes.py spec.json findings.json approvals.json --out spec.fixed.json --log changelog.md
python3 scripts/apply_fixes.py spec.json findings.json duyet.xlsx     --out spec.fixed.json --log changelog.md
```
- Chỉ dòng được duyệt sửa mới bị đổi. Script kiểm tra giá trị hiện tại trước khi ghi.
- Báo người dùng nội dung `changelog.md`, kể cả các dòng bị bỏ qua.

### Bước 5 – Cấu hình lên hệ thống
```bash
python3 scripts/eform_builder.py build  --spec spec.fixed.json --form <khoa>            # dry-run, tự hủy bỏ
python3 scripts/eform_builder.py build  --spec spec.fixed.json --form <khoa> --save     # khi người dùng đồng ý
python3 scripts/eform_builder.py verify --spec spec.fixed.json --form <khoa>           # đọc lại server, so spec
```
- Mặc định gắn vào trình duyệt đã mở ở Bước 0 (cổng 9334). Firefox/WebKit: thêm `--browser firefox --base-url https://<domain>` (hoặc `webkit`).
- Thêm `--base-url https://<domain>` khi trình duyệt mở nhiều hệ thống.
- Nhóm Eform phải có sẵn. Nếu chưa có, hỏi người dùng rồi tạo tại **Quản lý nhóm Eform → Thêm mới**.

### Bước 6 – Báo cáo
Nêu cho người dùng:
- Tên Eform, nhóm, số dòng, cây cột, trạng thái (Lưu nháp).
- Kết quả đối chiếu.
- Các dòng đã/không sửa.
- Việc còn lại: phát hành, phân quyền, banner. Những việc này **không tự làm**.

## Tham khảo
- `references/ui-notes.md`: bản đồ giao diện, selector, API đọc lại, các điểm dễ lỗi.
- `scripts/browser.py`: tìm/mở trình duyệt; lớp điều khiển chung (CDP cho nhân Chromium, Playwright cho Firefox/WebKit).
- `scripts/cdp.py`: client CDP tối giản, có chế độ daemon cho thao tác lẻ.
- `AGENTS.md`: bản rút gọn cho AI khác; `HUONG_DAN_CHAY_TAY.md`: chạy tay không cần AI.
