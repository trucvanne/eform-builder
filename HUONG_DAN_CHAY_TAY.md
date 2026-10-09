# Hướng dẫn chạy tay (không cần AI)

Dùng khi máy không có Claude Code / AI chạy được lệnh, hoặc chỉ có AI dạng chat trên web. Mỗi bước có lệnh cho **Windows** và **macOS/Linux**.

## 0. Cài đặt (làm 1 lần)
1. Cài **Python 3.9 trở lên** từ python.org. Windows: tick **Add python.exe to PATH** khi cài.
2. Tải skill: trên GitHub bấm **Code → Download ZIP**, giải nén (hoặc `git clone`).
3. Mở cửa sổ lệnh **tại thư mục skill**:
   - Windows: mở thư mục `eform-builder` trong File Explorer, gõ `cmd` vào thanh địa chỉ, Enter.
   - macOS: chuột phải thư mục → **New Terminal at Folder**.
4. Cài thư viện đọc Excel:
   ```bat
   python -m pip install openpyxl
   ```
   ```bash
   python3 -m pip install openpyxl
   ```
5. Chỉ khi dùng **Firefox** hoặc **WebKit (nhân Safari)**:
   ```bat
   python -m pip install playwright
   python -m playwright install firefox webkit
   ```

## 1. Mở trình duyệt điều khiển
Xem máy có trình duyệt nào:
```bat
python scripts\browser.py list
```
Mở trình duyệt riêng (hồ sơ riêng, không ảnh hưởng trình duyệt bạn đang dùng):
```bat
python scripts\browser.py open --browser auto --url "https://<domain-đơn-vị>/authenticate"
```
```bash
python3 scripts/browser.py open --browser auto --url "https://<domain-đơn-vị>/authenticate"
```
- Thay `auto` bằng `chrome`, `edge`, `coccoc`, `brave` hoặc `chromium` nếu muốn chọn.
- Trong cửa sổ vừa mở: **tự đăng nhập**, vào **Quản lý Eform → Danh sách Eform**.
- Firefox/WebKit: bỏ qua bước này; ở bước 4 thêm `--browser firefox --base-url "https://<domain-đơn-vị>"`.

## 2. Đọc Excel thành spec
```bat
python scripts\excel_to_spec.py "BieuMau.xlsx" --sheet Tinh --key tinh --group "Tên nhóm Eform" --attr TenThuocTinhBang --fixed "B,C,D" --spec spec.json
```
- `--fixed`: các cột có dữ liệu cố định từng dòng (vd Lĩnh vực, Năm, Tháng). Cột còn lại là cột số để đơn vị nhập.
- Cột nhóm cha/con: sửa `spec.json` theo mẫu `examples/spec.example.json` (có thể nhờ AI chat làm phần này rồi dán lại).

## 3. Rà soát và duyệt từng dòng
```bat
python scripts\review_spec.py spec.json --source-title "BIỂU MẪU BC THÁNG 8" --out findings.json --xlsx duyet.xlsx
```
1. Mở `duyet.xlsx`, sheet **Duyet**. Mỗi dòng là 1 phát hiện.
2. Cột **Quyết định**: chọn `Sửa theo đề xuất`, `Giữ nguyên` hoặc `Giá trị khác` (gõ giá trị vào cột **Giá trị khác**). Để trống = giữ nguyên.
3. Lưu file, rồi áp dụng:
```bat
python scripts\apply_fixes.py spec.json findings.json duyet.xlsx --out spec.fixed.json --log changelog.md
```
Mở `changelog.md` để xem dòng nào đã đổi, dòng nào bị bỏ qua.

## 4. Cấu hình lên hệ thống
```bat
python scripts\eform_builder.py build  --spec spec.fixed.json --form tinh
python scripts\eform_builder.py build  --spec spec.fixed.json --form tinh --save
python scripts\eform_builder.py verify --spec spec.fixed.json --form tinh
```
- Lệnh 1 là **chạy thử**: dựng xong rồi tự Hủy bỏ, không lưu gì. Xem kết quả in ra trước.
- Lệnh 2 **Lưu nháp** thật. Không phát hành, không phân quyền.
- Lệnh 3 đọc lại từ hệ thống và so với spec: phải in `KHỚP`.
- Firefox: thêm `--browser firefox --base-url "https://<domain-đơn-vị>"` vào cả 3 lệnh; mỗi lần chạy, đăng nhập trong cửa sổ Firefox mà script mở.

## Dùng ChatGPT web cho phần dữ liệu
ChatGPT web/app chat chạy được bước 2–3 (đọc Excel, rà soát, áp dụng duyệt) trên máy chủ OpenAI, **không** chạy được bước 1 và 4 (trình duyệt). Dùng Codex thì làm được đủ quy trình: xem `README.md`.

1. Tải lên khung chat: file zip của skill (`eform-builder-skill.zip` hoặc **Code → Download ZIP** trên GitHub) và file Excel biểu mẫu. Nếu tài khoản có tính năng **Skills**, có thể tải thư mục skill lên một lần tại **Create → Upload from your computer**, sau đó chỉ cần tải file Excel.
2. Gõ câu lệnh (sửa phần trong `< >`):
   ```text
   Giải nén eform-builder-skill.zip, đọc SKILL.md. Cài openpyxl nếu chưa có.
   Chạy: python scripts/excel_to_spec.py "<file>.xlsx" --sheet <Sheet> --key <khoa> --group "<Nhóm>" --attr <ThuocTinh> --fixed "B,C,D" --spec spec.json
   Rồi chạy: python scripts/review_spec.py spec.json --source-title "<tiêu đề kỳ báo cáo>" --out findings.json --xlsx duyet.xlsx
   KHÔNG tự sửa dữ liệu. Cho tôi tải về duyet.xlsx, spec.json, findings.json.
   ```
3. Mở `duyet.xlsx` trên máy, chọn cột **Quyết định** cho từng dòng (như mục 3 ở trên), lưu lại.
4. Tải `duyet.xlsx` đã điền lên và gõ:
   ```text
   Chạy: python scripts/apply_fixes.py spec.json findings.json duyet.xlsx --out spec.fixed.json --log changelog.md
   Chỉ áp dụng các dòng tôi đã chọn, không sửa thêm gì. Cho tôi tải về spec.fixed.json và changelog.md.
   ```
   Nếu ChatGPT báo không còn `spec.json` / `findings.json` (file trong phiên có thể bị xóa sau một thời gian), tải lại 2 file đã lưu ở bước 2.
5. Chép `spec.fixed.json` vào thư mục skill trên máy, rồi chạy **mục 1** (mở trình duyệt, đăng nhập) và **mục 4** (dry-run → lưu nháp → đối chiếu).

Lưu ý:
- Cột nhóm cha/con: có thể nhờ ChatGPT sửa `spec.json` theo `examples/spec.example.json`, nhưng đọc lại cây cột trước khi dùng.
- Không dán mật khẩu, mã đăng nhập vào ChatGPT. File tải lên sẽ nằm trên máy chủ OpenAI: kiểm tra quy định của đơn vị về dữ liệu trước khi tải.

## Lỗi hay gặp
| Thông báo | Cách xử lý |
|---|---|
| `'python' is not recognized` | Cài lại Python, tick **Add python.exe to PATH**; hoặc dùng `py` thay `python`. |
| `No module named 'openpyxl'` | Chạy lại lệnh cài ở mục 0.4. |
| `Không tìm thấy trình duyệt nhân Chromium` | Cài Chrome/Edge, hoặc truyền `--browser-path "C:\...\chrome.exe"`, hoặc dùng Firefox (mục 0.5). |
| `Không có trình duyệt nào mở cổng 9334` | Chạy lại bước 1, giữ cửa sổ trình duyệt đó mở. |
| `Không tìm thấy tab hệ thống Eform` | Trong cửa sổ trình duyệt điều khiển, mở **Danh sách Eform**; hoặc thêm `--base-url`. |
| `cổng 9334 không phản hồi` | Đóng hết cửa sổ của trình duyệt đó rồi chạy lại bước 1. |
| Kết quả đối chiếu `LỆCH` | Không lưu tiếp. Gửi phần in ra cho người phụ trách kiểm tra. |
