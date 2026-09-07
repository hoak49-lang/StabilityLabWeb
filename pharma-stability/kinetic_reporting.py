import html,json
from dataio import workbook_bytes

def sheets(run):
    meta=[['Thông tin','Giá trị'],['Trạng thái','DỰ ĐOÁN THĂM DÒ — không phải hạn dùng ICH được phê duyệt'],['Mã',run['id']],['Ngày UTC',run['created_at']],['SHA-256',run['record_sha256']],['Phiên bản',run['version']],['Bậc phản ứng',run['order']],['Đơn vị thời gian',run['time_unit']],['Nhiệt độ đích °C',run['target_c']],['C0 đích',run['c0']],['Giới hạn dưới',run['limit']],['Hàm lượng / bao bì / chỉ tiêu / RH',' / '.join(run['group'])],['Cấu hình',json.dumps(run['config'],ensure_ascii=False)],['SHA-256 dữ liệu nguồn',run['source_sha256']],['SHA-256 mã chương trình',run['software_sha256']],*[["Cần xử lý",x] for x in run['blockers']],*[["Giới hạn",x] for x in run['warnings']]]
    summary=[['Lô','k tại nhiệt độ đích','Ea kJ/mol','Thời gian tới giới hạn','Bootstrap 2.5%','Bootstrap 97.5%','RMSE','R2','Bootstrap hợp lệ']]
    residual=[['Lô','Dòng','Nhiệt độ °C','Thời gian','Kết quả','Khớp','Phần dư']]
    rates=[['Lô','Nhiệt độ °C','k độc lập','C0 khớp độc lập']]
    comparison=[['Lô','Bậc','RMSE trên thang nồng độ','AICc cùng thang đo']]
    for b in run['batches']:
        interval=b['bootstrap_interval95'] or [None,None]
        summary.append([b['batch'],b['k_target'],b['ea_kj_mol'],b['time_to_limit'],*interval,b['rmse'],b['r_squared'],b['bootstrap_valid']])
        residual.extend([[b['batch'],r['row_id'],r['temp_c'],r['time'],r['value'],r['fitted'],r['residual']] for r in b['residuals']])
        rates.extend([[b['batch'],r['temp_c'],r['k'],r['c0']] for r in b['independent_rates']])
        comparison.extend([[b['batch'],r['order'],r['rmse'],r['aicc']] for r in b['comparison']])
    inputs=[['batch','strength','pack','attribute','temp_c','rh','time','value'],*[[r[k] for k in ['batch','strength','pack','attribute','temp_c','rh','time','value']] for r in run['input_snapshot']]]
    return [('Report',meta),('Estimates',summary),('Rates',rates),('Order comparison',comparison),('Residuals',residual),('Input',inputs)]

def excel_report(run):return workbook_bytes(sheets(run))

def html_report(run):
    out=['<!doctype html><html lang="vi"><meta charset="utf-8"><title>StabilityLab — LHCT / Arrhenius</title><style>body{font:16px/1.6 Arial;margin:32px;color:#173b45}table{border-collapse:collapse;width:100%;margin-bottom:24px}td,th{border:1px solid #bdd1d4;padding:8px;text-align:left;overflow-wrap:anywhere}th{background:#eaf3f5}h2{break-before:auto}@media print{tr{break-inside:avoid}}</style><h1>LHCT / Arrhenius — dự đoán thăm dò</h1>']
    for title,rows in sheets(run):
        out.append('<h2>'+html.escape(title)+'</h2><table>')
        for i,row in enumerate(rows):
            tag='th' if i==0 else 'td'
            out.append('<tr>'+''.join('<'+tag+'>'+html.escape('—' if v is None else f'{v:.7g}' if isinstance(v,float) else str(v))+'</'+tag+'>' for v in row)+'</tr>')
        out.append('</table>')
    out.append('</html>');return ''.join(out).encode('utf-8')
