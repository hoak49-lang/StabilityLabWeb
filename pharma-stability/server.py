"""Local-only application server. No clinical/stability data leave this process."""
import bootstrap
import argparse
import base64
import hashlib
import json
import mimetypes
import platform
import secrets
import sys
import threading
import uuid

from datetime import datetime,timezone
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
import webbrowser
from pathlib import Path
from urllib.parse import urlparse,parse_qs
from engine import analyze,AnalysisError,VERSION
from dataio import parse_file,map_rows,workbook_bytes
from reporting import html_report,excel_report

ROOT=Path(__file__).resolve().parent
RUNS=ROOT/'runs'
DATASETS={}
TOKEN=secrets.token_urlsafe(32)
LOCK=threading.Lock()
PORT=0


def canonical(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')


def sha(value): return hashlib.sha256(canonical(value)).hexdigest()


def software_hash():
    h=hashlib.sha256()
    for path in sorted(list(ROOT.glob('*.py'))+list((ROOT/'static').glob('*'))+[ROOT/'requirements.txt']):
        if path.is_file():
            h.update(str(path.relative_to(ROOT)).encode());h.update(path.read_bytes())
    return h.hexdigest()


def histories():
    items=[]
    for path in sorted(RUNS.glob('*.json'),reverse=True):
        try:
            r=json.loads(path.read_text('utf-8'))
            recorded=r.pop('record_sha256')
            verified=sha(r)==recorded
            items.append(dict(id=r['id'],created_at=r['created_at'],product=r['review'].get('product',''),
                              candidate_months=r['overall']['candidate_months'],attributes=[a['attribute'] for a in r['analyses']],
                              verified=verified,record_sha256=recorded))
        except Exception:
            items.append(dict(id=path.stem,verified=False,error='Không đọc được bản ghi.'))
    return items[:100]


def get_run(id):
    if len(id)>70 or any(c not in '0123456789abcdefT_Z-' for c in id):
        raise AnalysisError('Mã phân tích không hợp lệ.')
    path=RUNS/(id+'.json')
    if not path.is_file(): raise AnalysisError('Không tìm thấy bản phân tích.')
    r=json.loads(path.read_text('utf-8'))
    digest=r.pop('record_sha256')
    if sha(r)!=digest:
        raise AnalysisError('Nội dung bản phân tích không khớp SHA-256. Không xuất báo cáo từ bản ghi đã thay đổi.')
    r['record_sha256']=digest
    return r


def store_run(run):
    with LOCK:
        RUNS.mkdir(exist_ok=True)
        latest=histories()
        run['previous_record_sha256']=latest[0].get('record_sha256') if latest else None
        run['record_sha256']=sha(run)
        path=RUNS/(run['id']+'.json')
        with path.open('x',encoding='utf-8') as out:
            json.dump(run,out,ensure_ascii=False,allow_nan=False,indent=2)


def add_dataset(raw,filename,sheet=None):
    if len(DATASETS)>=30:
        raise AnalysisError('Đã mở 30 bảng trong phiên. Lưu dự án rồi khởi động lại để giải phóng bộ nhớ.')
    table=parse_file(raw,filename,sheet)
    id=uuid.uuid4().hex
    DATASETS[id]=dict(raw=raw,table=table)
    return dict(dataset_id=id,**table)


def dataset(id):
    if id not in DATASETS: raise AnalysisError('Bảng dữ liệu không còn trong phiên. Hãy nhập lại tệp hoặc mở dự án.')
    return DATASETS[id]


def analyze_request(request):
    table=dataset(request.get('dataset_id'))['table']
    mapping=request.get('mapping',{})
    rows=map_rows(table,mapping,request.get('decimal','dot'))
    condition=request.get('condition')
    selected=[r for r in rows if r['condition']==condition]
    if not selected: raise AnalysisError('Điều kiện đã chọn không có dữ liệu.')
    groups=sorted({r.get('study_group','') for r in selected})
    group=request.get('study_group')
    if group is None:
        if len(groups)>1:raise AnalysisError('Chọn một hàm lượng × quy cách. Không gộp các tổ hợp thành lô.')
        group=groups[0]
    selected=[r for r in selected if r.get('study_group','')==group]
    if not selected:raise AnalysisError('Tổ hợp hàm lượng × quy cách không có dữ liệu ở điều kiện này.')
    if 'temp_c' in table['headers']:
        col=table['headers'].index('temp_c');ids={r['row_id'] for r in selected}
        temperatures={r['cells'][col] for r in table['rows'] if r['row_id'] in ids}
        if len(temperatures)>1:raise AnalysisError('Không gộp nhiều nhiệt độ trong hồi quy Q1E. Dùng LHCT / Arrhenius hoặc tách một điều kiện dài hạn.')
    attributes=request.get('attributes',[])
    if not isinstance(attributes,list) or not 1<=len(attributes)<=12 or len(set(attributes))!=len(attributes):
        raise AnalysisError('Chọn từ 1 đến 12 chỉ tiêu riêng biệt.')
    allattrs=sorted({r['attribute'] for r in selected})
    specifications=request.get('specifications',{})
    review=request.get('review',{})
    analyses=[]
    for attr in attributes:
        if attr not in allattrs or attr not in specifications:
            raise AnalysisError(f'Chỉ tiêu {str(attr)[:80]} thiếu dữ liệu hoặc tiêu chuẩn.')
        config=dict(specifications[attr],horizon=request.get('horizon',120))
        result=analyze([r for r in selected if r['attribute']==attr],config,review)
        result['attribute']=attr
        analyses.append(result)
    candidates=[a['candidate_months'] for a in analyses]
    all_analyzed=set(attributes)==set(allattrs)
    run=dict(id=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_Z-')+uuid.uuid4().hex[:10],
             created_at=datetime.now(timezone.utc).isoformat(),version=VERSION,
             software_sha256=software_hash(),python_version=platform.python_version(),
             source={k:v for k,v in table.items() if k!='rows'},input_snapshot=table['rows'],
             settings={k:v for k,v in request.items() if k not in ('dataset_id','review')},review=review,
             condition=condition,study_group=group,selected_rows=sum(a['n'] for a in analyses),
             unselected_rows=len(rows)-sum(a['n'] for a in analyses),analyses=analyses,
             overall=dict(candidate_months=min(candidates) if all(v is not None for v in candidates) and all_analyzed else None,
                          conditional_limit_months=min(a['conditional_limit_months'] for a in analyses),
                          all_imported_attributes_analyzed=all_analyzed,
                          scope='Selected attributes and one storage condition only. Not a released shelf life.'))
    store_run(run)
    return run


class Handler(BaseHTTPRequestHandler):
    server_version='StabilityLab/1.0'

    def log_message(self,format,*args):
        # Do not put patient/product names or uploaded data in logs.
        pass

    def valid_host(self):
        return self.headers.get('Host') in (f'127.0.0.1:{PORT}',f'localhost:{PORT}')

    def authorized(self):
        origin=self.headers.get('Origin')
        if origin and origin not in (f'http://127.0.0.1:{PORT}',f'http://localhost:{PORT}'):
            return False
        return self.valid_host() and secrets.compare_digest(self.headers.get('X-Stability-Token',''),TOKEN)

    def send(self,data,kind='application/json; charset=utf-8',code=200,filename=None):
        if not isinstance(data,bytes): data=canonical(data)
        self.send_response(code)
        self.send_header('Content-Type',kind)
        self.send_header('Content-Length',str(len(data)))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Referrer-Policy','no-referrer')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; connect-src 'self'; frame-ancestors 'none'; object-src 'none'; base-uri 'none'")
        if filename:self.send_header('Content-Disposition',f'attachment; filename="{filename}"')
        self.end_headers();self.wfile.write(data)

    def do_GET(self):
        if not self.valid_host(): return self.send(dict(error='Host not allowed'),code=403)
        route=urlparse(self.path)
        try:
            if route.path=='/':
                raw=(ROOT/'static/index.html').read_text('utf-8').replace('__TOKEN__',TOKEN)
                return self.send(raw.encode(),'text/html; charset=utf-8')
            files={('/'+n):n for n in ['app.js','style.css','runtime.js','design-ui.mjs','design-engine.mjs','arrhenius-ui.mjs','program.mjs']}
            if route.path in files:
                name=files[route.path]
                return self.send((ROOT/'static'/name).read_bytes(),'text/javascript; charset=utf-8' if name.endswith(('.js','.mjs')) else 'text/css; charset=utf-8')
            if route.path=='/favicon.ico': return self.send(b'',code=204)
            if not self.authorized(): return self.send(dict(error='Phiên không hợp lệ. Tải lại ứng dụng.'),code=403)
            if route.path=='/api/program':
                import program
                return self.send(program.snapshot())
            if route.path=='/api/health':return self.send(dict(version=VERSION,local_only=True))
            if route.path=='/api/kinetic/demo':
                return self.send(add_dataset((ROOT/'examples/arrhenius.csv').read_bytes(),'arrhenius.csv'))
            if route.path=='/api/kinetic/template':
                return self.send(workbook_bytes([('Kinetics',[['batch','strength','pack','attribute','temp_c','rh','time','value'],['B1','50 mg','P30','Assay',40,'75',0,None]])]),'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            if route.path.startswith('/api/kinetic/export/'):
                import kinetic_reporting
                id=route.path.split('/')[-1]
                if len(id)>70 or any(c not in '0123456789abcdefT_Z-' for c in id):raise AnalysisError('Mã báo cáo không hợp lệ.')
                record=json.loads((ROOT/'kinetic_runs'/(id+'.json')).read_text('utf-8'))
                digest=record.pop('record_sha256')
                if sha(record)!=digest:raise AnalysisError('Báo cáo không khớp mã SHA-256.')
                record['record_sha256']=digest
                fmt=parse_qs(route.query).get('format',['json'])[0]
                if fmt=='xlsx':return self.send(kinetic_reporting.excel_report(record),'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                if fmt=='html':return self.send(kinetic_reporting.html_report(record),'text/html; charset=utf-8')
                return self.send(record)
            if route.path=='/api/history':return self.send(histories())
            if route.path=='/api/demo':
                result=add_dataset((ROOT/'examples/demo.csv').read_bytes(),'demo.csv')
                result['demo']=True
                return self.send(result)
            if route.path=='/api/template':
                raw=workbook_bytes([('Stability',[['batch','time','value','attribute','condition'],['B001',0,None,'Assay','25C_60RH']]),('Instructions',[['Field','Meaning'],['batch','Unique batch ID'],['time','Months, numeric, include zero'],['value','Measured numeric result; no formulas, missing values or <LOQ strings'],['attribute','One quantitative quality attribute'],['condition','Exact storage condition; never pool conditions']])])
                return self.send(raw,'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',filename='StabilityLab_Template.xlsx')
            if route.path.startswith('/api/run/'):
                return self.send(get_run(route.path.split('/')[-1]))
            if route.path.startswith('/api/export/'):
                id=route.path.split('/')[-1]; r=get_run(id)
                format=parse_qs(route.query).get('format',['json'])[0]
                if format=='html':return self.send(html_report(r),'text/html; charset=utf-8',filename=f'StabilityLab_{id}.html')
                if format=='xlsx':return self.send(excel_report(r),'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',filename=f'StabilityLab_{id}.xlsx')
                if format=='json':return self.send(r,filename=f'StabilityLab_{id}.json')
                raise AnalysisError('Định dạng xuất không hợp lệ.')
            return self.send(dict(error='Không tìm thấy đường dẫn.'),code=404)
        except AnalysisError as ex:return self.send(dict(error=str(ex)),code=400)
        except Exception as ex:
            print(type(ex).__name__,str(ex)[:240],file=sys.stderr)
            return self.send(dict(error='Không thể hoàn tất thao tác. Bản phân tích chưa thay đổi.'),code=500)

    def do_POST(self):
        if not self.authorized():return self.send(dict(error='Yêu cầu không thuộc phiên cục bộ.'),code=403)
        try:
            length=int(self.headers.get('Content-Length','0'))
            if not 0<length<=16*1024*1024:raise AnalysisError('Kích thước yêu cầu không hợp lệ.')
            if 'application/json' not in self.headers.get('Content-Type',''):raise AnalysisError('Cần yêu cầu JSON.')
            request=json.loads(self.rfile.read(length))
            if not isinstance(request,dict):raise AnalysisError('Nội dung yêu cầu không hợp lệ.')
            path=urlparse(self.path).path
            if path in ('/api/program/create','/api/program/update'):
                import program
                return self.send(program.create(request) if path.endswith('/create') else program.update(request))
            if path=='/api/design/export':
                sheets=request.get('sheets')
                if not isinstance(sheets,list) or not 1<=len(sheets)<=6:raise AnalysisError('Lịch xuất không hợp lệ.')
                if sum(len(x[1]) for x in sheets)>100000:raise AnalysisError('Lịch vượt 100.000 dòng.')
                return self.send(workbook_bytes(sheets),'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            if path in ('/api/kinetic/groups','/api/kinetic/analyze'):
                from arrhenius import parse_kinetic_table,analyze_arrhenius
                ds=dataset(request.get('dataset_id'))
                rows=parse_kinetic_table(ds['table'])
                group=lambda r:json.dumps([r[k] for k in ['strength','pack','attribute','rh']],ensure_ascii=False)
                groups=sorted({group(r) for r in rows})
                if path.endswith('/groups'):return self.send(dict(groups=groups,rows=len(rows)))
                chosen=request.get('group')
                if chosen not in groups:raise AnalysisError('Chọn một hàm lượng × bao bì × chỉ tiêu × RH.')
                r=analyze_arrhenius([row for row in rows if group(row)==chosen],request.get('config',{}))
                r.update(id=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_Z-')+uuid.uuid4().hex[:10],created_at=datetime.now(timezone.utc).isoformat(),source_sha256=ds['table']['sha256'],software_sha256=software_hash())
                r['record_sha256']=sha(r)
                folder=ROOT/'kinetic_runs';folder.mkdir(exist_ok=True)
                (folder/(r['id']+'.json')).write_bytes(canonical(r))
                return self.send(r)
            if path=='/api/import':
                raw=base64.b64decode(request['base64'],validate=True)
                return self.send(add_dataset(raw,request['filename'],request.get('sheet')))
            if path=='/api/map':
                table=dataset(request.get('dataset_id'))['table']
                rows=map_rows(table,request.get('mapping',{}),request.get('decimal','dot'))
                return self.send(dict(rows=rows,attributes=sorted({r['attribute'] for r in rows}),conditions=sorted({r['condition'] for r in rows})))
            if path=='/api/analyze': return self.send(analyze_request(request))
            if path=='/api/project/save':
                ds=dataset(request.get('dataset_id'))
                project=dict(schema='stabilitylab.project.v1',filename=ds['table']['filename'],sheet=ds['table']['sheet'],
                             base64=base64.b64encode(ds['raw']).decode(),settings=request.get('settings',{}))
                return self.send(project,filename='Study.stability.json')
            if path=='/api/project/open':
                if request.get('schema')!='stabilitylab.project.v1':raise AnalysisError('Không phải tệp dự án StabilityLab v1.')
                raw=base64.b64decode(request['base64'],validate=True)
                result=add_dataset(raw,request['filename'],request.get('sheet'))
                result['settings']=request.get('settings',{})
                return self.send(result)
            if path=='/api/shutdown':
                self.send(dict(stopped=True))
                threading.Thread(target=self.server.shutdown,daemon=True).start()
                return
            return self.send(dict(error='Không tìm thấy chức năng.'),code=404)
        except (AnalysisError,KeyError,ValueError,TypeError) as ex:
            return self.send(dict(error=str(ex)),code=400)
        except Exception as ex:
            print(type(ex).__name__,str(ex)[:240],file=sys.stderr)
            return self.send(dict(error='Lỗi xử lý. Kiểm tra dữ liệu và nhật ký cục bộ; không có kết quả mới được xác nhận.'),code=500)


def main():
    global PORT
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=8765);parser.add_argument('--open',action='store_true')
    args=parser.parse_args()
    try:
        server=ThreadingHTTPServer(('127.0.0.1',args.port),Handler)
    except OSError:
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    PORT=server.server_address[1]
    print(f'StabilityLab {VERSION}: http://127.0.0.1:{PORT}',flush=True)
    print('Local only. Stop using the application button or Ctrl+C.',flush=True)
    if args.open:threading.Timer(.7,lambda:webbrowser.open(f'http://127.0.0.1:{PORT}')).start()
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()


if __name__=='__main__':main()
