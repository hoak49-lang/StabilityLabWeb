import io
from server import *

class BrowserHandler(Handler):
    def __init__(self,path,body=None):
        self.path=path
        raw=canonical(body) if body is not None else b''
        self.headers={'Content-Length':str(len(raw)),'Content-Type':'application/json'}
        self.rfile=io.BytesIO(raw)
    def authorized(self):return True
    def valid_host(self):return True
    def send(self,data,kind='application/json; charset=utf-8',code=200,filename=None):
        if not isinstance(data,bytes):data=canonical(data)
        self.result={'base64':base64.b64encode(data).decode(),'kind':kind,'code':code}

def dispatch(path,body_json):
    body=json.loads(body_json) if body_json else None
    if path=='/api/design/export':
        try:
            sheets=body.get('sheets') if isinstance(body,dict) else None
            if not isinstance(sheets,list) or not 1<=len(sheets)<=6:raise AnalysisError('Các trang lịch không hợp lệ.')
            total=0
            for item in sheets:
                if not isinstance(item,list) or len(item)!=2 or not isinstance(item[0],str) or not isinstance(item[1],list):raise AnalysisError('Trang lịch không hợp lệ.')
                for row in item[1]:
                    if not isinstance(row,list) or len(row)>30:raise AnalysisError('Dòng lịch không hợp lệ.')
                    if any(not isinstance(x,(str,int,float,type(None))) for x in row):raise AnalysisError('Giá trị ô không hợp lệ.')
                total+=len(item[1])
            if total>100000:raise AnalysisError('Lịch quá lớn để xuất; hãy chia nghiên cứu.')
            raw=workbook_bytes(sheets)
            return json.dumps({'base64':base64.b64encode(raw).decode(),'kind':'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet','code':200})
        except (AnalysisError,ValueError,TypeError) as e:
            return json.dumps({'base64':base64.b64encode(canonical({'error':str(e)})).decode(),'kind':'application/json','code':400})
    if path=='/api/shutdown':
        DATASETS.clear()
        for p in RUNS.glob('*.json'):p.unlink()
        return json.dumps({'base64':'e30=','kind':'application/json','code':200})
    h=BrowserHandler(path,body)
    if body is None:h.do_GET()
    else:h.do_POST()
    return json.dumps(h.result)
