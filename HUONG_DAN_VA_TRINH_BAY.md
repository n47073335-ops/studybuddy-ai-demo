# StudyBuddy AI — Hướng dẫn chạy demo và trình bày

## 1. Bản demo làm được gì?
- Giao diện web tiếng Việt, phù hợp trình diễn trên máy tính.
- Có sẵn 3 tài liệu mẫu để thử ngay.
- Thêm ghi chú hoặc nạp tệp văn bản `.txt`, `.md`, `.csv`, `.json`; tìm kiếm, xem và xóa tài liệu.
- Trợ lý truy xuất các đoạn nội dung liên quan và hiển thị nguồn.
- Quiz tương tác 5 câu; kế hoạch học tập có thể thêm và đánh dấu hoàn thành.
- Màn hình mô hình CSDL thể hiện các bảng, trường, PK/FK và quan hệ.
- Chế độ HTML offline lưu trạng thái vào LocalStorage.
- Khi chạy Python backend, dữ liệu được lưu trong SQLite (`studybuddy.db`); câu hỏi, câu trả lời và các nguồn được lưu quan hệ.
- Có thể bật Gemini LLM thật bằng biến môi trường `GEMINI_API_KEY`.

## 2. Cách chạy dễ nhất trên Windows
1. Giải nén toàn bộ thư mục vào một nơi dễ tìm.
2. Cài Python 3.10 hoặc mới hơn, trong trình cài đặt chọn **Add Python to PATH**.
3. Nhấp đúp `run_demo.bat`. Lần đầu cần mạng để cài thư viện Python.
4. Trình duyệt mở `http://127.0.0.1:8000`. Nếu chưa tự mở, hãy dán địa chỉ này vào Chrome/Edge.
5. Đừng đóng cửa sổ terminal khi đang demo vì đó là máy chủ.

Nếu chưa có Python hoặc mạng, có thể nhấp đúp `index.html` để mở bản offline. Ở chế độ này, dữ liệu được lưu trong trình duyệt và phần trả lời chỉ là truy xuất/xử lý mẫu; không nên giới thiệu là LLM thật.

## 3. Bật Gemini LLM thật (không bắt buộc cho demo offline)
1. Tạo Gemini API key từ Google AI Studio bằng tài khoản của bạn.
2. Trong thư mục này, sao chép `.env.example` thành `.env`.
3. Mở `.env`, điền `GEMINI_API_KEY=KHÓA_CỦA_BẠN` và giữ nguyên/chọn một model đang được API của tài khoản hỗ trợ.
4. Dừng máy chủ bằng `Ctrl+C`, sau đó chạy lại `run_demo.bat`.
5. Vào Cài đặt & kết nối → Kiểm tra kết nối backend. Khi `LLM` hiển thị Gemini API, hỏi một câu để trình diễn.

Bảo mật: không chụp/chiếu khóa API, không gửi `.env` cho người khác và không commit `.env` lên kho mã. API có thể có giới hạn sử dụng hoặc chi phí theo điều khoản hiện hành. Nếu lỗi 404/model không hỗ trợ, kiểm tra danh sách mô hình mà khóa API của tài khoản đang được phép gọi và điều chỉnh `GEMINI_MODEL`.

## 4. Kịch bản demo 4–6 phút trước giảng viên
1. **Giới thiệu bài toán (30 giây):** sinh viên thường phân tán tài liệu và muốn hỏi đáp, ôn tập theo nội dung cá nhân.
2. **Thư viện tài liệu (45 giây):** mở Thư viện tài liệu, xem 3 tài liệu mẫu, thêm một ghi chú của riêng mình.
3. **Trình diễn RAG (1–2 phút):** vào Trợ lý AI, hỏi “RAG là gì và hoạt động như thế nào?”. Chỉ vào khu vực “Ngữ cảnh truy xuất” để cho thấy hệ thống tìm nguồn trước khi trả lời. Hỏi thêm một câu về khóa chính/khóa ngoại.
4. **Giải thích LLM (30 giây):** nếu đã cấu hình khóa, chỉ ra trạng thái Gemini API và kết quả sinh dựa trên ngữ cảnh; nếu không có khóa, nói rõ đây là demo truy xuất offline, LLM chưa bật.
5. **CSDL quan hệ (45 giây):** mở Cơ sở dữ liệu, giải thích `Users` có quan hệ 1-N với `Documents`, `Documents` 1-N `DocumentChunks`, `Conversations` 1-N `Messages`, và `MessageSources` gắn nguồn vào tin nhắn.
6. **Tương tác người dùng (45 giây):** mở Ôn tập nhanh trả lời 1 câu, sau đó thêm/đánh dấu hoàn thành một nhiệm vụ.
7. **Kết luận (20 giây):** nhấn mạnh hệ thống kết hợp CSDL quan hệ cho dữ liệu nghiệp vụ, RAG cho truy xuất ngữ cảnh, LLM cho sinh câu trả lời.

## 5. Cấu trúc cơ bản
- `index.html`: giao diện, chế độ offline, truy xuất từ khóa và quiz.
- `app.py`: FastAPI, SQLite, xử lý tài liệu, retrieval và gọi Gemini API tùy cấu hình.
- `studybuddy.db`: được tạo tự động khi backend khởi động; lưu CSDL demo.
- `.env.example`: mẫu cấu hình biến môi trường.
- `requirements.txt`: thư viện Python cần thiết.
- `run_demo.bat` / `run_demo.sh`: script khởi chạy.

## 6. Mô tả kiến trúc để đưa vào báo cáo
`Người học → Giao diện web → API backend → (1) CSDL quan hệ SQLite để lưu người dùng/tài liệu/hội thoại/nhiệm vụ; (2) Pipeline RAG: chia tài liệu thành chunks → xếp hạng truy xuất → chọn top-k chunks → ghép câu hỏi + ngữ cảnh → LLM Gemini nếu cấu hình → câu trả lời và nguồn → giao diện.`

## 7. Giới hạn nên nói thật khi bảo vệ
- Retrieval hiện dùng xếp hạng từ khóa kiểu TF/IDF đơn giản, chưa dùng vector database hoặc semantic embedding. Có thể phát triển tiếp bằng Gemini Embedding hoặc một vector store.
- Tệp đọc trực tiếp giới hạn ở văn bản `.txt/.md/.csv/.json`, chưa có bộ trích xuất PDF/DOCX.
- Đây là prototype học thuật chạy trên một tài khoản demo cố định, chưa có đăng ký/đăng nhập thật, phân quyền, đa người dùng hoặc kiểm thử bảo mật triển khai công khai.
- Kết quả LLM phụ thuộc ngữ cảnh truy xuất và API; cần đánh giá factuality, độ chính xác nguồn và quyền riêng tư trước khi triển khai thực tế.
