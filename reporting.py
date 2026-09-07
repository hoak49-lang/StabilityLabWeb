import bootstrap
import html
import json
from dataio import workbook_bytes

SOURCES=[
 ('ICH Q1E (2003), §§2.3–2.6 và Appendix B','https://database.ich.org/sites/default/files/Q1E%20Guideline.pdf'),
 ('ICH Q1A(R2), thiết kế nghiên cứu độ ổn định','https://database.ich.org/sites/default/files/Q1A%28R2%29%20Step4.pdf'),
 ('Minitab: ví dụ Stability Study với lô cố định','https://support.minitab.com/en-us/minitab/help-and-how-to/statistical-modeling/regression/how-to/stability-study/before-you-start/example-with-a-fixed-batch-factor/'),
 ('EMA: tình trạng hướng dẫn ICH Q1 hợp nhất','https://www.ema.europa.eu/en/ich-q1-guideline-stability-testing-drug-substances-drug-products'),
]


def e(v): return html.escape(str(v if v is not None else '—'))


def f(v): return '—' if v is None else f'{v:.6g}' if isinstance(v,(float,int)) else str(v)


def htable(headers,rows):
    return '<table><thead><tr>'+''.join('<th>'+e(h)+'</th>' for h in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+e(f(v))+'</td>' for v in row)+'</tr>' for row in rows)+'</tbody></table>'


def chart(result):
    allpts=[v for series in result['series'] for v in series['points']]
    vals=[p[k] for p in allpts for k in ('mean','lower','upper')]+[r['value'] for r in result['residuals']]
    vals += [v for v in (result['lower'],result['upper']) if v is not None]
    lo,hi=min(vals),max(vals)
    span=max(hi-lo,1e-6); lo-=span*.08; hi+=span*.08
    def x(t): return 65+800*t/result['search_horizon']
    def y(v): return 330-280*(v-lo)/(hi-lo)
    out=['<svg viewBox="0 0 920 390" role="img" aria-label="Đồ thị độ ổn định"><rect width="920" height="390" fill="white"/>']
    for i in range(6):
        v=lo+(hi-lo)*i/5; t=result['search_horizon']*i/5
        out.append(f'<path d="M65 {y(v)} H865" stroke="#e0e7e7"/><text x="5" y="{y(v)+5}" font-size="13">{e(f(v))}</text><text x="{x(t)-10}" y="355" font-size="13">{e(f(t))}</text>')
    palette=['#007f83','#8958aa','#d47729','#3467ae','#aa4667']
    for index,series in enumerate(result['series']):
        for key in ['mean']+(['lower','upper'] if result['direction']=='both' else ['lower' if result['direction']=='decrease' else 'upper']):
            d=' '.join(('M' if i==0 else 'L')+f'{x(p["time"]):.2f} {y(p[key]):.2f}' for i,p in enumerate(series['points']))
            out.append(f'<path d="{d}" fill="none" stroke="{palette[index%5]}" stroke-width="2" '+('stroke-dasharray="6 4"' if key!='mean' else '')+'/>')
    for r in result['residuals']:
        color=palette[result['batches'].index(r['batch'])%5]
        out.append(f'<circle cx="{x(r["time"])}" cy="{y(r["value"])}" r="3" fill="{color}"/>')
    for limit in (result['lower'],result['upper']):
        if limit is not None: out.append(f'<path d="M65 {y(limit)} H865" stroke="#ba344a" stroke-dasharray="8 4"/>')
    out.append('<text x="430" y="383" font-size="16">Thời gian (tháng)</text></svg>')
    return ''.join(out)


def html_report(run):
    parts=['''<!doctype html><html lang="vi"><meta charset="utf-8"><title>StabilityLab · Báo cáo phân tích</title>
<style>body{font:15px/1.55 Arial,sans-serif;color:#193c45;max-width:1080px;margin:40px auto;padding:0 25px}h1{font-size:32px}h2{margin-top:40px}table{border-collapse:collapse;width:100%;font-size:13px;margin:14px 0}td,th{border:1px solid #cad8d9;padding:8px;text-align:left;overflow-wrap:anywhere}th{background:#eaf1ef}svg{width:100%;max-height:480px}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px}.note{background:#fff5df;padding:18px}.section{break-before:page}a{color:#087b80}@media print{body{margin:0;max-width:none}button{display:none}tr{break-inside:avoid}}</style>
<h1>StabilityLab · Báo cáo độ ổn định</h1>''']
    parts.append('<p>Hỗ trợ phương pháp ICH Q1E, mô hình lô cố định. Báo cáo phân tích hỗ trợ đánh giá chuyên môn.</p>')
    parts.append(htable(['Thông tin','Giá trị'],[
        ['Mã phân tích',run['id']],['Thời gian UTC',run['created_at']],['Phiên bản',run['version']],
        ['Sản phẩm',run['review'].get('product','')],['Người đánh giá (tự khai)',run['review'].get('reviewer','')],
        ['Tệp nguồn',run['source']['filename']],['SHA-256 tệp gốc',run['source']['sha256']],
        ['SHA-256 chương trình',run['software_sha256']],['SHA-256 nội dung bản phân tích',run['record_sha256']],
        ['Điều kiện được chọn',run['condition']],['Hàm lượng × quy cách', ' / '.join(json.loads(run.get('study_group','["",""]'))) or 'Không phân tầng'],['Số dòng dùng / không thuộc nhóm chọn',f'{run["selected_rows"]} / {run["unselected_rows"]}'],
        ['Dòng trống trong tệp',str(run['source']['blank_rows'])],['Chỉ tiêu đã phân tích',', '.join(a['attribute'] for a in run['analyses'])],
        ['Ứng viên chung, tháng',run['overall']['candidate_months']],['Giới hạn chung có điều kiện, tháng',run['overall']['conditional_limit_months']],
    ]))
    parts.append('<div class="note">Ứng viên chung chỉ có giá trị trong phạm vi chỉ tiêu, điều kiện và hàm lượng × quy cách đã phân tích; không áp dụng tự động cho tổ hợp không thử. Chưa có xác nhận thẩm định hệ thống tại đơn vị, chữ ký điện tử hay phê duyệt hạn dùng. Không dùng điểm giao thống kê riêng lẻ làm hạn dùng ghi nhãn.</div>')
    for a in run['analyses']:
        parts.append('<section class="section"><h2>'+e(a['attribute'])+'</h2>')
        parts.append(htable(['Kết quả','Giá trị'],[
            ['Mô hình',a['model_name']],['Phép biến đổi',a['transform']],['Giới hạn tin cậy',f'{a["confidence"]*100:g}% / {a["confidence_sides"]} phía, cho trung bình trên thang phân tích'],
            ['Giao điểm thống kê, tháng',a['statistical_months'] if a['statistical_months'] is not None else f'Chưa chạm trong 0–{a["search_horizon"]:g} tháng'],
            ['Thời gian dài hạn chung X',a['observed_common_months']],['Trần ngoại suy có điều kiện',a['extrapolation']['months']],
            ['Nhánh ngoại suy',a['extrapolation']['section']+'; '+a['extrapolation']['rule']],['Giải thích',a['extrapolation']['reason']],
            ['Giới hạn kết hợp, cần đánh giá',a['conditional_limit_months']],['Ứng viên (làm tròn xuống tháng)',a['candidate_months']],
            ['N / bậc tự do dư',f'{a["n"]} / {a["df_error"]}'],['SSE',a['sse']],['MSE',a['mse']],['RMSE',a['rmse']],['R²',a['r_squared']],
        ]))
        parts.append(chart(a))
        parts.append('<p>Đường liền: hồi quy. Nét đứt màu lô: giới hạn tin cậy. Nét đứt đỏ: tiêu chuẩn. Các giới hạn tin cậy mô tả trung bình trên thang phân tích, không phải khoảng dự đoán cho từng viên hoặc khoảng dung sai.</p>')
        parts.append('<h3>ANCOVA theo trình tự</h3>')
        tests=[]
        for label,key in [('Khác biệt hệ số góc','slope_test'),('Khác biệt hệ số chặn','intercept_test')]:
            t=a[key]
            tests.append([label,t['df1'] if t else None,t['df2'] if t else None,t['f'] if t else None,t['p'] if t else None,'Đã kiểm tra' if t else 'Không cần kiểm tra'])
        parts.append(htable(['Kiểm định','df1','df2','F','p','Trạng thái'],tests))
        parts.append(htable(['Lô','n','Chặn','SE chặn','Góc / tháng','SE góc','Giao điểm, tháng'],[[b[k] for k in ('batch','n','intercept','intercept_se','slope','slope_se','crossing')] for b in a['coefficients']]))
        parts.append('<h3>Các vấn đề cần đánh giá</h3><ul>'+''.join('<li>'+e(w)+'</li>' for w in a['blockers']+a['warnings'])+'</ul>')
        parts.append('<h3>Chẩn đoán mô hình</h3><pre>'+e(json.dumps(a['diagnostics'],ensure_ascii=False,indent=2))+'</pre>')
        parts.append('<details open><summary>Dữ liệu và phần dư (thang phân tích)</summary>')
        parts.append(htable(['Dòng nguồn','Lô','Tháng','Giá trị gốc','Giá trị khớp','Phần dư','Chuẩn hóa','Leverage','Cook'],[[r[k] for k in ('row_id','batch','time','value','fitted_transformed','residual','standardized','leverage','cooks_distance')] for r in a['residuals']]))
        parts.append('</details></section>')
    parts.append('<h2>Khai báo và giải trình của người dùng</h2><pre>'+e(json.dumps(run['review'],ensure_ascii=False,indent=2))+'</pre>')
    parts.append('<h2>Cấu hình nhập và phân tích</h2><pre>'+e(json.dumps(run['settings'],ensure_ascii=False,indent=2))+'</pre>')
    parts.append('<h2>Nguồn phương pháp</h2><ul>'+''.join('<li><a href="'+url+'">'+e(label)+'</a></li>' for label,url in SOURCES)+'</ul>')
    parts.append('<p>Tình trạng tài liệu kiểm tra ngày 06/09/2026: EMA liệt kê Q1E là phiên bản hiệu lực; Q1 hợp nhất ở trạng thái dự thảo Step 2b. Cần kiểm tra việc áp dụng tại thị trường đăng ký.</p></html>')
    return ''.join(parts).encode('utf-8')


def excel_report(run):
    overview=[['Field','Value'],['Analysis ID',run['id']],['UTC',run['created_at']],['Version',run['version']],
              ['Product',run['review'].get('product','')],['Condition',run['condition']],['Strength / pack', ' / '.join(json.loads(run.get('study_group','["",""]'))) or 'Not stratified'],['Source SHA256',run['source']['sha256']],
              ['Record SHA256',run['record_sha256']],['Overall candidate months',run['overall']['candidate_months']],
              ['Conditional bound months',run['overall']['conditional_limit_months']],['Status','Analytical support; not approved shelf life']]
    sheets=[('Overview',overview)]
    for i,a in enumerate(run['analyses'],1):
        rows=[['Measure','Value'],['Attribute',a['attribute']],['Model',a['model_name']],['Transform',a['transform']],
              ['Confidence target',a['confidence_target']],['Confidence level',.95],['Sides',a['confidence_sides']],['Pooling alpha',.25],
              ['Statistical crossing months',a['statistical_months']],['No crossing search horizon',a['search_horizon']],
              ['Common observed months',a['observed_common_months']],['Extrapolation cap',a['extrapolation']['months']],
              ['Candidate months',a['candidate_months']],['Conditional bound months',a['conditional_limit_months']],
              ['SSE',a['sse']],['MSE',a['mse']],['Error DF',a['df_error']],['R-squared',a['r_squared']]]
        rows.extend(['Blocker',w] for w in a['blockers']);rows.extend(['Warning',w] for w in a['warnings'])
        sheets.append((f'{i}_Summary',rows))
        sheets.append((f'{i}_ANCOVA',[['Test','df1','df2','F','p','SS']]+[[key]+[a[key][k] if a[key] else None for k in ('df1','df2','f','p','ss')] for key in ('slope_test','intercept_test')]))
        keys=['batch','n','intercept','intercept_se','slope','slope_se','crossing','max_time']
        sheets.append((f'{i}_Coefficients',[keys]+[[r[k] for k in keys] for r in a['coefficients']]))
        keys=['row_id','batch','time','value','fitted_transformed','residual','standardized','leverage','cooks_distance']
        sheets.append((f'{i}_Residuals',[keys]+[[r[k] for k in keys] for r in a['residuals']]))
        sheets.append((f'{i}_Confidence',[['Curve','Months','Mean','Lower CI','Upper CI']]+[[s['batch'],r['time'],r['mean'],r['lower'],r['upper']] for s in a['series'] for r in s['points']]))
    sheets.append(('Declarations',[['Field','Value']]+[[k,str(v)] for k,v in run['review'].items()]))
    sheets.append(('Sources',[['Reference','URL']]+[list(s) for s in SOURCES]))
    return workbook_bytes(sheets)
