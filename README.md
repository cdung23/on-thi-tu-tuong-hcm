# Ứng Dụng Ôn Thi Trắc Nghiệm - Tư Tưởng Hồ Chí Minh 🇻🇳

Hệ thống trắc nghiệm trực quan 464 câu hỏi trắc nghiệm môn **Tư tưởng Hồ Chí Minh**, có đáp án, trích dẫn văn kiện và lời giải thích chi tiết từng câu.

## 🚀 Tính Năng Chính
- **464 câu hỏi chuẩn xác**: Phân chia theo chương, chủ đề rõ ràng.
- **Giải thích & Dẫn chứng**: Giải thích chi tiết cơ sở lý luận và trích dẫn văn kiện cho từng đáp án đúng/sai.
- **Chế độ học đa dạng**:
  - *Luyện thi ngẫu nhiên*: Trộn ngẫu nhiên câu hỏi theo số lượng tuỳ chọn.
  - *Ôn tập theo chương*: Tập trung vào từng phần kiến thức.
  - *Chế độ thi tính giờ*: Giả lập phòng thi thực tế.
  - *Sổ tay câu sai (Bookmark / Review)*: Ôn lại các câu trả lời sai để ghi nhớ.
- **Giao diện hiện đại**: Tối ưu hiển thị cho cả điện thoại (mobile) và máy tính, hỗ trợ chế độ Tối/Sáng (Dark/Light Mode).

---

## 🌐 Dành Cho Bạn Bè Sử Dụng Trực Tiếp (GitHub Pages)

Bạn không cần cài đặt phần mềm nào, chỉ cần mở trực tiếp đường dẫn trên trình duyệt web:

👉 **Link web**: `https://<ten-tai-khoan-github>.github.io/<ten-repo>/`

*(Sau khi tạo repo, vào mục **Settings** -> **Pages** -> tại mục **Branch** chọn `main` và nhấn **Save** để nhận link).*

---

## 💻 Sử Dụng Offline Trên Máy Tính
1. Tải toàn bộ mã nguồn hoặc clone repository:
   ```bash
   git clone https://github.com/<ten-tai-khoan-github>/<ten-repo>.git
   ```
2. Nhấp đúp chuột vào file `index.html` để mở ngay trên trình duyệt (Chrome, Edge, Safari, Firefox,...).

---

## 📁 Cấu Trúc Dự Án
- `index.html`: Giao diện ứng dụng web trắc nghiệm.
- `questions_data.js`: Cơ sở dữ liệu 464 câu hỏi và lời giải chi tiết.
- `Trắc nghiệm - Đáp án và Giải thích.md`: Tài liệu tra cứu dạng văn bản.
- `convert_pdf_to_md.py` & `solve_questions_notebooklm.py`: Scripts trích xuất và xử lý dữ liệu.
