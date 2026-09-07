# Pharma Stability 3.0

MVP chạy tại máy cho thiết kế nghiên cứu độ ổn định, phân tích Q1E/Arrhenius và Stability Program.

## Chạy từ mã nguồn
Cài Python 3.12 x64. Từ thư mục gốc kho:

```powershell
python -m pip install -r pharma-stability/requirements.txt --target pharma-stability/.vendor
python -X utf8 pharma-stability/launcher.py
```

Giao diện mở trong trình duyệt, dữ liệu và phép tính xử lý tại máy. Đây không phải bản chạy trên GitHub Pages; Pages không chạy máy chủ Python hoặc cơ sở dữ liệu SQLite.

## Sử dụng
Thiết kế → lập lịch → Đưa vào Stability Program → nhập ngày vào tủ, vị trí, người phụ trách và mã đề cương → tạo lịch → lấy mẫu → nhập kết quả → rà soát. Kết quả đã rà soát được khóa. Nhắc việc chỉ hiển thị khi mở phần mềm.

Bản nguồn chỉ chứa dữ liệu minh họa; không chứa cơ sở dữ liệu hoặc hồ sơ nghiên cứu của người dùng.

## Kiểm thử
```powershell
python -X utf8 -m unittest discover -s pharma-stability/tests -v
node pharma-stability/design-test.mjs
```

## Đóng gói Windows
Sau khi cài dependencies vào .vendor như trên, chạy trên Windows với Python 3.12 x64:
```powershell
python -X utf8 pharma-stability/package_windows.py
```
Tệp ZIP nằm tại output/PharmaStability_Windows_3.0.zip. Người nhận giải nén rồi mở Open StabilityLab.cmd; bản ZIP kèm môi trường Python, bản Source code ZIP của GitHub không kèm môi trường chạy.

## Phạm vi
Chưa có đăng nhập/phân quyền, email nhắc nền, chữ ký điện tử, audit trail chống sửa đổi hoặc thẩm định GxP. Không tuyên bố được ICH chứng nhận. Arrhenius là dự đoán thăm dò, không thay thế đánh giá hạn dùng đăng ký. Đọc [hướng dẫn chi tiết](HUONG_DAN_WINDOWS.md).
