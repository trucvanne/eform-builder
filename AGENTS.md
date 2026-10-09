# Hướng dẫn cho AI agent (Codex, Copilot, Cursor, Gemini CLI, …)

Thư mục này là skill **eform-builder**: cấu hình Eform dạng bảng từ file Excel trên *Nền tảng khai phá dữ liệu động*, có rà soát chính tả và **chỉ sửa dữ liệu khi người dùng duyệt từng dòng**.

Quy trình đầy đủ và lệnh: **đọc `SKILL.md` trước khi làm**. File này chỉ nhắc các quy tắc không được bỏ qua và điểm khác khi không dùng Claude Code.

## Quy tắc bắt buộc
1. Không tự đăng nhập, không gõ mật khẩu. Người dùng tự đăng nhập trong cửa sổ trình duyệt.
2. Không tự sửa dữ liệu. Mỗi phát hiện của `review_spec.py` phải được người dùng quyết định **riêng từng dòng**:
   - hỏi từng dòng trong khung chat (1 câu hỏi cho 1 dòng; dòng không được trả lời = giữ nguyên) rồi ghi `approvals.json`, **hoặc**
   - đưa phiếu `duyet.xlsx` cho người dùng chọn cột *Quyết định*.
   Sau đó mới chạy `scripts/apply_fixes.py`.
3. Chỉ **Lưu nháp**. Không Phát hành, Phân quyền, Thu hồi, Hủy, Xóa nếu người dùng không yêu cầu rõ.
4. Không đụng Eform đã gửi đi/đang dùng trừ khi người dùng nêu đích danh.
5. Luôn dry-run (`build` không `--save`) trước; chỉ `--save` khi người dùng đồng ý; sau đó chạy `verify`.
6. Domain không cố định (mỗi đơn vị một domain): không gắn cứng địa chỉ; hỏi người dùng hoặc để script tự nhận.
7. Ghi rõ phần nào là suy luận (cây cột nhóm, tên cột, đề xuất chính tả) và hỏi xác nhận.

## Khác biệt khi không dùng Claude Code
- Không có `AskUserQuestion`: hỏi bằng tin nhắn thường, mỗi lần 1 dòng (hoặc liệt kê có số và chờ người dùng trả lời từng số), hoặc dùng `duyet.xlsx`.
- Lệnh Python: Windows dùng `python` hoặc `py` thay cho `python3`.
- Trình duyệt: `python scripts/browser.py list` để xem máy có gì; `python scripts/browser.py open --url https://<domain>/authenticate` để mở (Chrome/Edge/Cốc Cốc/Brave/Chromium). Firefox/WebKit dùng Playwright: thêm `--browser firefox --base-url https://<domain>` khi chạy `eform_builder.py`.
- AI dạng chat trên web (không chạy được lệnh trên máy): người dùng làm theo `HUONG_DAN_CHAY_TAY.md`, AI chỉ hỗ trợ đọc bảng phát hiện.
