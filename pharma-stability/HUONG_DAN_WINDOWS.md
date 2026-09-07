# Pharma Stability 3.0 — MVP chạy tại máy

## Bắt đầu
1. Mở phần mềm bằng tệp Open StabilityLab.cmd trong gói đã giải nén.
2. Thiết kế: khai báo hàm lượng, lô, bao bì, chỉ tiêu và điều kiện. Lập lịch full, bracketing hoặc matrixing.
3. Xử lý các điểm chặn; chọn Đưa vào Stability Program.
4. Nhập người phụ trách, ngày vào tủ, vị trí và mã đề cương đã rà soát; tạo nghiên cứu.
5. Stability Program: lọc quá hạn/trong 30 ngày; ghi lấy mẫu, nhập kết quả cùng giới hạn và đơn vị, rà soát. Kết quả rà soát bị khóa.
6. Chọn một nghiên cứu và xuất kết quả đã rà soát ra CSV; nhập CSV tại Phân tích. Thời gian trong CSV là mốc kế hoạch; phải đánh giá ngày lấy mẫu thực tế và sai lệch trước khi sử dụng hồi quy.
7. LHCT / Arrhenius có bộ dữ liệu và báo cáo riêng.

## Lưu trữ
Chương trình lưu tự động tại app/program.sqlite3. Để sao lưu đầy đủ, đóng ứng dụng và sao chép tệp này cùng app/runs, app/kinetic_runs và các dự án/thiết kế đã lưu. Xuất bản ghi JSON chỉ là bản đọc, chưa có chức năng khôi phục JSON và chỉ chứa 100 sự kiện gần nhất.
Nhắc việc chỉ hoạt động trong giao diện đang mở; chưa có email, SMS hoặc tác vụ nền khi đóng ứng dụng.

## Phạm vi thực tế
Đây là MVP cục bộ, chưa phải hệ thống GxP đã thẩm định. Chưa có tài khoản/phân quyền, chữ ký điện tử, audit trail chống sửa đổi, quản lý kho mẫu vật lý, tích hợp LIMS, quản lý CAPA đầy đủ hoặc công thức tính kết quả từ dữ liệu máy phân tích. Nhập kết quả định lượng cuối và giới hạn tiêu chuẩn; chưa hỗ trợ kết quả định tính trong Stability Program. Rà soát là bước nghiệp vụ tự khai, không phải phê duyệt pháp quy. Không suy luận tự động cho tổ hợp không thử. Không dùng dự đoán Arrhenius thay hạn dùng đăng ký.

## Kiểm chứng
31 kiểm thử Python: hồi quy, đối chiếu ví dụ Minitab, Arrhenius, nhập/xuất, dịch vụ, lịch cuối tháng/năm nhuận, lưu kết quả, chặn chuyển bước sai và khóa kết quả. Bộ kiểm thử JavaScript kiểm tra full/bracket/matrix/combined. Giao diện chương trình được kiểm tra trong trình duyệt.

---

# StabilityLab Windows 2.0

## Mở phần mềm

Giải nén **StabilityLab_Windows_2.0.zip** bằng **Extract All**. Mở thư mục đã giải nén và nhấp đúp **Open StabilityLab.cmd**. Giữ cửa sổ nhỏ “StabilityLab Windows 2.0” mở trong lúc làm việc. Nhấn “Mở phần mềm” nếu trình duyệt chưa tự mở.

Giao diện chạy ở địa chỉ 127.0.0.1 trên chính máy tính; địa chỉ này không dùng để chia sẻ sang máy đồng nghiệp. Toàn bộ phép tính dùng Python/NumPy/SciPy đi kèm, không cần Internet, GitHub, tài khoản hay cài Python. Gói dành cho Windows 10/11 x64 và trình duyệt hiện đại có hỗ trợ JavaScript modules. Để đồng nghiệp dùng, gửi toàn bộ tệp ZIP, không chỉ gửi launcher.

## Chọn đúng quy trình

| Mục đích | Tab | Đầu vào và đầu ra |
|---|---|---|
| Lập kế hoạch nghiên cứu nhiều hàm lượng, quy cách | Thiết kế | Lịch đầy đủ / bracketing / matrixing theo thời gian / phối hợp; xuất Excel và lưu JSON |
| Đánh giá dữ liệu dài hạn tại điều kiện dự kiến | Phân tích | Hồi quy lô cố định, khả năng gộp lô, giới hạn tin cậy và trần ngoại suy ICH Q1E |
| Nghiên cứu cấp tốc / trung gian theo đề cương ICH | Thiết kế và Đánh giá ICH trong Phân tích | Lập lịch riêng; ghi nhận thay đổi đáng kể và bằng chứng để xem xét nhánh ngoại suy. Không suy ngược hạn dùng chỉ từ một điều kiện cấp tốc |
| Khảo sát ảnh hưởng nhiệt độ bằng LHCT nhiều mức nhiệt | LHCT / Arrhenius | Động học phân hủy bậc 0/1/2, Ea, k tại nhiệt độ đích, thời gian tới giới hạn và khoảng bootstrap thăm dò |

## 1. Thiết kế nghiên cứu

Chọn **Ví dụ 3 hàm lượng × 3 quy cách** để xem cách nhập. Thay toàn bộ thông tin mẫu bằng thông tin thực tế. Mã lô khai báo riêng cho từng hàm lượng. Mô-đun giả định mọi quy cách được áp dụng cho từng hàm lượng; khi có tổ hợp không tồn tại, tách các nghiên cứu thích hợp.

- **Đầy đủ:** mọi tổ hợp được thử tại mọi mốc.
- **Bracketing:** đánh dấu T vào hàm lượng/quy cách được thử trực tiếp. Người thiết kế phải chứng minh chúng thực sự bao quát cực trị; kích thước chai nhỏ/lớn không tự chứng minh tính đại diện khi lượng nạp, vật liệu, nắp hoặc độ thấm thay đổi.
- **Matrixing:** luân phiên lượt thử của các tổ hợp ở mốc trung gian. Mốc đầu/cuối được giữ đầy đủ. Ứng dụng bảo thủ giữ cả mốc 12 tháng khi nghiên cứu dài hạn ≥12 tháng và mốc dữ liệu cuối trước nộp hồ sơ đã khai báo. Có kiểm tra tối thiểu 3 mốc trong khoảng thích hợp; lịch có thể được bổ sung mốc thử để đáp ứng điều kiện này. Mức giảm thực tế sẽ nhỏ hơn tỷ lệ ban đầu.
- **Phối hợp:** cần giải trình riêng về việc đồng thời giảm tổ hợp và giảm thời điểm. Matrixing trong phiên bản này theo thời gian, chưa tối ưu matrixing loại bỏ tổ hợp đa yếu tố.

Các điều kiện bảo quản có lịch độc lập. Mọi chỉ tiêu đã khai báo cùng dùng lịch đó; không giảm bằng cách bỏ luân phiên chỉ tiêu. Số lượt tính là tổ hợp × mốc, không phải số đơn vị thuốc hay bao gói cần chuẩn bị. Phải tính thêm lượng mẫu, mẫu lặp, dự phòng và các phép thử đặc biệt theo đề cương.

Lịch gợi ý gồm dài hạn/cấp tốc theo trường hợp thường và bảo quản lạnh. Điều kiện thị trường, bao bì bán thấm, thuốc sinh học, quang ổn định, in-use và hoàn nguyên cần đánh giá riêng. Nếu dài hạn 25°C/60%RH và cấp tốc có thay đổi đáng kể, xem xét nhánh trung gian tương ứng; có thể khai báo thêm dòng intermediate và lịch phù hợp. Không tự thay điều kiện Việt Nam bằng một lựa chọn mặc định.

Excel có Protocol, Schedule, Data, Bracketed. **Data là bảng dự kiến với kết quả trống.** Giữ nguyên lịch nghiên cứu; dùng một bản sao chỉ chứa quan sát đã đo và đã điền kết quả để nhập phân tích. Không dùng số 0 thay cho kết quả chưa có. Các tổ hợp bracketed không được phần mềm tự suy ra hạn dùng.

## 2. Phân tích hạn dùng theo ICH Q1E

Chọn **Phân tích → Dùng dữ liệu minh họa** hoặc nhập CSV UTF-8 / XLSX. Gán các cột batch, time, value; có thể bổ sung attribute, condition, strength, pack. Thời gian ở tab này luôn là **tháng**. Chọn một điều kiện và một hàm lượng × quy cách. Khai báo tiêu chuẩn đã được phê duyệt, hướng biến đổi và phép biến đổi.

Giảm: giới hạn dưới một phía 95%; tăng: giới hạn trên một phía 95%; chưa biết hướng: giới hạn hai phía 95%. Thuật toán kiểm tra góc trước, sau đó chặn với alpha 0,25 để chọn mô hình lô cố định. Giao điểm là giới hạn tin cậy của trung bình chạm tiêu chuẩn, không phải khoảng dự đoán cho từng mẫu hoặc cam kết mọi lô tương lai.

Xem đồ thị, phần dư, lack-of-fit khi có lặp, độ cong, Shapiro–Wilk, Levene và các cảnh báo. Hoàn thiện đánh giá dữ liệu dài hạn, thiết kế, cấp tốc/trung gian và căn cứ ngoại suy. Kết quả phân biệt giao điểm thống kê, giới hạn có điều kiện và ứng viên để chuyên gia xem xét. Không tự gộp nhiệt độ, hàm lượng hoặc bao bì thành “lô”.

## 3. LHCT / Arrhenius

Chọn **LHCT / Arrhenius → Dữ liệu LHCT minh họa → Phân tích Arrhenius** để thử. Ví dụ là dữ liệu tổng hợp, hàm lượng ban đầu 100%, giới hạn 90%, bậc 1, nhiệt độ đích 25°C; không dùng các giá trị này như tiêu chuẩn thật.

CSV/XLSX cần đúng các cột: batch, strength, pack, attribute, temp_c, rh, time, value. Mỗi lô cần ít nhất 3 nhiệt độ; mỗi nhiệt độ ít nhất 4 quan sát tại ít nhất 3 mốc, có mốc 0. Nhiệt độ nhập theo °C, phần mềm đổi sang Kelvin. Chọn ngày hoặc tháng đúng với dữ liệu; không tự chuyển tháng thành số ngày cố định.

Mỗi lần chỉ dùng một hàm lượng × bao bì × chỉ tiêu × RH. Mô hình hiện chỉ dùng **nồng độ/hàm lượng còn lại**, dương và có giới hạn dưới 0 < Cmin < C0. Không dùng trực tiếp cho tạp chất tăng, chỉ tiêu hòa tan, vật lý, vi sinh, enzyme hay phân hủy phức tạp. Không ghép các RH khác nhau vào mô hình chỉ có nhiệt độ. Ký hiệu RH “sealed” chỉ mô tả nhóm; người dùng vẫn phải đánh giá ảnh hưởng ẩm/nước thực tế.

Các phương trình:

- Bậc 0: C = C0 − kt; t_limit = (C0 − Cmin) / k.
- Bậc 1: C = C0 exp(−kt); t_limit = ln(C0/Cmin) / k.
- Bậc 2: 1/C = 1/C0 + kt; t_limit = (1/Cmin − 1/C0) / k.
- Arrhenius: ln k(T) = ln k(Tref) + Ea/R × (1/Tref − 1/T), R = 8,314462618 J mol⁻¹ K⁻¹.

Thuật toán khớp phi tuyến trên thang nồng độ gốc, riêng mỗi lô; ước lượng log(k_ref), Ea và C0 riêng ở từng nhiệt độ. Bảng so sánh ba bậc dùng cùng thang sai số và AICc; không tự chọn bậc phản ứng chỉ vì R² cao. C0 dùng để tính hạn tới giới hạn tại nhiệt độ đích là giá trị người dùng khai báo, khác với các C0 khớp ở nhiệt độ thử.

Bootstrap lấy lại phần dư trong từng nhiệt độ, điều chỉnh gần đúng độ co của phần dư, rồi khớp lại mô hình; seed cố định hỗ trợ tái lập. Khoảng 95% là phân vị 2,5%–97,5%, có điều kiện trên mô hình và C0 đã chọn. Nếu >10% mẫu bootstrap không hợp lệ, ứng dụng không báo khoảng. Khoảng này chưa bao gồm bất định về cơ chế, chuyển pha, RH, phép chọn bậc phản ứng hoặc hiệu ứng lô chưa quan sát. Dữ liệu hỗ trợ, đánh giá chẩn đoán, dự đoán kiểm chứng ở nhiệt độ bảo quản và thẩm định mô hình vẫn cần thiết.

Ea âm/không dương, tham số sát biên hoặc khó xác định được cảnh báo. Dự đoán ở ngoài dải nhiệt thử được đánh dấu ngoại suy. Không có “hạn dùng phê duyệt” từ mô-đun Arrhenius; ước lượng ngắn nhất giữa các lô chỉ là tóm tắt thăm dò của các lô đã đo.

## Lưu, chia sẻ và kiểm tra

Lưu thiết kế JSON, dự án Q1E hoặc dự án LHCT để mở lại. Kết quả Q1E lưu ở app/runs; Arrhenius lưu ở app/kinetic_runs. Xuất HTML để xem/in PDF, Excel để phân tích tiếp, JSON để lưu hồ sơ. Các báo cáo bao gồm dữ liệu đầu vào, cấu hình và mã SHA-256. SHA-256 không phải audit trail chống sửa đổi hay chữ ký điện tử.

Đóng trình duyệt không tự dừng phần mềm; dùng “Đóng phần mềm” hoặc đóng cửa sổ điều khiển sau khi lưu. Chạy **Check installation.cmd** nếu không mở được. Giữ toàn bộ thư mục runtime và app cùng nhau. Nếu chính sách IT chặn chạy, làm việc với IT; không cần tắt phần mềm bảo vệ máy.

## Phạm vi ICH và trạng thái thẩm định

Đã kiểm tra phương pháp Q1E bằng ví dụ lô cố định của Minitab; kiểm tra động học với dữ liệu tổng hợp có Ea/k đã biết, kiểm tra lịch rút gọn, nhập/xuất dữ liệu và quyền truy cập cục bộ. Đây không phải thẩm định toàn bộ hệ thống tại đơn vị.

Phần mềm triển khai một số nguyên tắc ICH Q1A(R2), Q1D, Q1E, **không được ICH chứng nhận**, không phải bản sao đầy đủ Minitab, chưa có chữ ký điện tử, quản lý vai trò hoặc audit trail đáp ứng Part 11/Annex 11. Trước khi dùng hồ sơ chính thức cần URS, đánh giá rủi ro, IQ/OQ/PQ, kiểm chứng thuật toán, SOP, kiểm soát thay đổi và phê duyệt chuyên môn phù hợp mục đích sử dụng.

Nguồn kiểm tra ngày 07/09/2026:

- ICH Q1A(R2): https://www.ema.europa.eu/en/documents/scientific-guideline/ich-q-1-r2-stability-testing-new-drug-substances-and-products-step-5_en.pdf
- ICH Q1D: https://www.ema.europa.eu/en/documents/scientific-guideline/ich-q-1-d-bracketing-and-matrixing-designs-stability-testing-drug-substances-and-drug-products-step-5_en.pdf
- ICH Q1E: https://www.ema.europa.eu/en/documents/scientific-guideline/ich-q-1-e-evaluation-stability-data-step-5_en.pdf
- IUPAC Arrhenius: https://goldbook.iupac.org/terms/view/A00446
- EMA Q1 hợp nhất vẫn được liệt kê là dự thảo Step 2b tại thời điểm kiểm tra: https://www.ema.europa.eu/en/ich-q1-guideline-stability-testing-drug-substances-drug-products. Nội dung modelling trong dự thảo không được coi là quy định đã có hiệu lực.
