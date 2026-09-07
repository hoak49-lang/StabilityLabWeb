from pathlib import Path
import sys,zipfile,hashlib,json,html
source=Path(__file__).resolve().parent
runtime=Path(sys.base_prefix)
vendor=source/'.vendor'
if not vendor.exists(): raise RuntimeError('Install requirements into pharma-stability/.vendor before packaging.')
out=source.parent/'output'/'PharmaStability_Windows_3.0.zip'
out.parent.mkdir(exist_ok=True)
prefix='PharmaStability_Windows_3.0'
manifest={}
launcher='@echo off\r\nif not exist "%~dp0runtime\\pythonw.exe" (\r\n echo Please extract the complete ZIP first.\r\n pause\r\n exit /b 1\r\n)\r\nstart "" "%~dp0runtime\\pythonw.exe" -X utf8 "%~dp0app\\launcher.py"\r\n'
check='@echo off\r\n"%~dp0runtime\\python.exe" -X utf8 "%~dp0app\\check_installation.py"\r\npause\r\n'
readme='''PHARMA STABILITY WINDOWS 3.0 — HƯỚNG DẪN MỞ

1. Nhấn chuột phải tệp ZIP → Extract All / Giải nén tất cả.
2. Mở thư mục PharmaStability_Windows_3.0 đã giải nén.
3. Nhấp đúp Open StabilityLab.cmd.
4. Giữ cửa sổ StabilityLab Windows 2.0 mở; giao diện mở trong trình duyệt.

Không cần Internet, GitHub, tài khoản hoặc cài Python để tính toán.
Dành cho Windows 10/11 x64. Không mở chương trình trực tiếp bên trong ZIP.
Giao diện 127.0.0.1 chạy tại máy; không gửi địa chỉ này cho đồng nghiệp.
Để đồng nghiệp dùng: gửi toàn bộ tệp ZIP này.

THỬ PHẦN MỀM
- Thiết kế → Ví dụ 3 hàm lượng × 3 quy cách → xem lịch / xuất Excel.
- Phân tích → Dùng dữ liệu minh họa → Phân tích độ ổn định.
- LHCT / Arrhenius → Dữ liệu LHCT minh họa → Phân tích Arrhenius.

Mẫu là dữ liệu tổng hợp, không phải nghiên cứu thực tế.
Lưu thiết kế và dự án trước khi đóng. Hồ sơ tính toán lưu tại app/runs
và app/kinetic_runs. Gói phân phối không chứa hồ sơ nghiên cứu của người gửi.

Đọc app/HUONG_DAN_WINDOWS.md hoặc HUONG_DAN.html để xem đầy đủ phương pháp.
Nếu không mở được, chạy Check installation.cmd và xem app/startup-error.log.
Giữ nguyên hai thư mục runtime và app; không tắt phần mềm bảo vệ máy.

Phần mềm hỗ trợ một số phương pháp ICH Q1A(R2)/Q1D/Q1E và Arrhenius.
Chưa thẩm định GxP tại đơn vị, không được ICH chứng nhận.
Arrhenius là dự đoán thăm dò, không tự thay thế hạn dùng từ dữ liệu dài hạn.
Giấy phép thành phần: runtime/LICENSE.txt và app/.vendor/*dist-info/licenses.
'''
def put(z,name,data):
    if isinstance(data,str):data=data.encode('utf-8')
    z.writestr(prefix+'/'+name,data);manifest[name]=hashlib.sha256(data).hexdigest()
with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for name in ['program.py','bootstrap.py','engine.py','dataio.py','reporting.py','server.py','arrhenius.py','kinetic_reporting.py','launcher.py','check_installation.py','requirements.txt','HUONG_DAN_WINDOWS.md']:
        put(z,'app/'+name,(source/name).read_bytes())
    for folder in ['static','examples']:
        for f in (source/folder).rglob('*'):
            if f.is_file():put(z,'app/'+f.relative_to(source).as_posix(),f.read_bytes())
    for f in vendor.rglob('*'):
        if f.is_file() and '__pycache__' not in f.parts and f.suffix not in ('.pyc','.whl'):
            put(z,'app/.vendor/'+f.relative_to(vendor).as_posix(),f.read_bytes())
    for f in runtime.rglob('*'):
        if not f.is_file():continue
        rel=f.relative_to(runtime)
        if 'site-packages' in rel.parts or '__pycache__' in rel.parts or f.suffix=='.pyc' or rel.parts[0] in ('include','libs','Scripts'):continue
        put(z,'runtime/'+rel.as_posix(),f.read_bytes())
    put(z,'Open StabilityLab.cmd',launcher);put(z,'Check installation.cmd',check)
    put(z,'README_FIRST.txt','\ufeff'+readme)
    guide=(source/'HUONG_DAN_WINDOWS.md').read_text('utf-8')
    put(z,'HUONG_DAN.html','<!doctype html><html lang="vi"><meta charset="utf-8"><title>StabilityLab Windows 2.0 — Hướng dẫn</title><style>body{max-width:1080px;margin:40px auto;padding:24px;background:#f2f6f6;color:#173b45;font:17px/1.7 "Segoe UI",Arial}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:inherit;background:white;padding:30px;border:1px solid #d4e4e5;border-radius:12px}</style><h1>StabilityLab Windows 2.0</h1><pre>'+html.escape(readme)+'\n\n'+html.escape(guide)+'</pre></html>')
    z.writestr(prefix+'/MANIFEST_SHA256.json',json.dumps(manifest,indent=2))
with zipfile.ZipFile(out) as z:
    assert z.testzip() is None
    for n in z.namelist():
        assert not any(n.startswith(prefix+'/app/'+folder+'/') for folder in ['runs','kinetic_runs','tests'])
        name=n[len(prefix)+1:]
        if name in manifest:assert hashlib.sha256(z.read(n)).hexdigest()==manifest[name]
print(json.dumps({'path':str(out),'bytes':out.stat().st_size,'entries':len(manifest),'sha256':hashlib.sha256(out.read_bytes()).hexdigest()}))
