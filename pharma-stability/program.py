"""Persistent local stability programme; not an authenticated enterprise service."""
from contextlib import contextmanager
import sqlite3, json, uuid, calendar, math
from datetime import date, datetime, timezone
from pathlib import Path

DB = Path(__file__).parent / 'program.sqlite3'

@contextmanager
def connect():
    db = sqlite3.connect(DB, timeout=20)
    db.row_factory = sqlite3.Row
    db.executescript('''CREATE TABLE IF NOT EXISTS studies(id TEXT PRIMARY KEY, name TEXT, owner TEXT, start TEXT, location TEXT, design TEXT);
    CREATE TABLE IF NOT EXISTS tasks(id TEXT PRIMARY KEY, study TEXT, batch TEXT, strength TEXT, pack TEXT, condition TEXT, month INTEGER, attribute TEXT, due TEXT, status TEXT, actual TEXT, value REAL, lower_limit REAL, upper_limit REAL, unit TEXT, note TEXT);
    CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY, at TEXT, actor TEXT, action TEXT, detail TEXT);''')
    try:
        with db:
            yield db
    finally:
        db.close()

def log(db, actor, action, detail):
    db.execute('INSERT INTO events(at,actor,action,detail) VALUES(?,?,?,?)', (datetime.now(timezone.utc).isoformat(), actor, action, json.dumps(detail, ensure_ascii=False)))

def month_date(start, month):
    d = date.fromisoformat(start)
    if int(month) != month or not 0 <= month <= 1200:
        raise ValueError('Lịch vận hành chỉ nhận tháng nguyên từ 0 đến 1200.')
    n = d.year*12 + d.month-1 + int(month)
    y,m = divmod(n,12); m += 1
    return date(y,m,min(d.day,calendar.monthrange(y,m)[1])).isoformat()

def snapshot():
    with connect() as db:
        return { 'studies':[dict(r) for r in db.execute('SELECT id,name,owner,start,location FROM studies ORDER BY rowid DESC')],
          'tasks':[dict(r) for r in db.execute('SELECT tasks.*, studies.name,studies.owner,studies.location FROM tasks JOIN studies ON studies.id=tasks.study ORDER BY due,study,batch')],
          'events':[dict(r) for r in db.execute('SELECT * FROM events ORDER BY id DESC LIMIT 100')] }

def create(req):
    name=str(req.get('name','')).strip(); owner=str(req.get('owner','')).strip()
    if not name or not owner: raise ValueError('Cần tên nghiên cứu và người phụ trách.')
    design=req['design']; start=req['start']; month_date(start,0)
    if not design.get('eligible') or design.get('blockers'): raise ValueError('Thiết kế còn vấn đề cần xử lý. Hoàn tất bước thiết kế trước.')
    if not str(req.get('review','')).strip(): raise ValueError('Cần mã đề cương/căn cứ rà soát để đưa lịch vào chương trình.')
    sid=uuid.uuid4().hex; rows=[]; seen=set()
    for s in design['studies']:
        for r in s['rows']:
            if len(r['tests']) != len(s['times']): raise ValueError('Lịch không hợp lệ.')
            for t, selected in zip(s['times'],r['tests']):
                if not selected: continue
                for attr in design['config']['attributes']:
                    key=(r['batch'],r['strength'],r['pack'],s['label'],t,attr)
                    if key in seen: raise ValueError('Lịch có tổ hợp bị trùng.')
                    seen.add(key)
                    rows.append((uuid.uuid4().hex,sid,*key,month_date(start,t),'planned',None,None,None,None,'',''))
    if not 1 <= len(rows) <= 50000: raise ValueError('Lịch cần 1–50.000 lượt chỉ tiêu.')
    with connect() as db:
        db.execute('INSERT INTO studies VALUES(?,?,?,?,?,?)',(sid,name,owner,start,str(req.get('location','')),json.dumps(design,ensure_ascii=False)))
        db.executemany('INSERT INTO tasks VALUES('+','.join('?'*16)+')',rows)
        log(db,owner,'CREATE_STUDY',{'study':sid,'tasks':len(rows),'review':req['review']})
    return {'id':sid,'count':len(rows)}

def update(req):
    actor=str(req.get('actor','')).strip()
    if not actor: raise ValueError('Cần người thực hiện.')
    status=req['status']
    transitions={'planned':['pulled'],'pulled':['tested'],'tested':['reviewed'],'reviewed':[]}
    with connect() as db:
        row=db.execute('SELECT * FROM tasks WHERE id=?',(req['id'],)).fetchone()
        if row is None: raise ValueError('Không tìm thấy công việc.')
        if status not in transitions[row['status']]: raise ValueError('Trạng thái đã thay đổi hoặc chuyển bước không hợp lệ. Tải lại danh sách.')
        actual=req.get('actual') or row['actual']
        if not actual: raise ValueError('Cần ngày lấy mẫu thực tế.')
        if date.fromisoformat(actual)>date.today(): raise ValueError('Ngày thực tế không được ở tương lai.')
        value=row['value']; lower=row['lower_limit']; upper=row['upper_limit']; unit=row['unit']
        if status=='tested':
            def number(v):
                if v is None or v=='': return None
                n=float(v)
                if not math.isfinite(n): raise ValueError('Giá trị phải là số hữu hạn.')
                return n
            value=number(req.get('value'));lower=number(req.get('lower'));upper=number(req.get('upper'));unit=str(req.get('unit','')).strip()
            if value is None or (lower is None and upper is None) or not unit: raise ValueError('Cần kết quả, đơn vị và ít nhất một giới hạn tiêu chuẩn.')
            if lower is not None and upper is not None and lower>=upper: raise ValueError('Giới hạn dưới phải nhỏ hơn giới hạn trên.')
        note=str(req.get('note','')).strip()
        if not note: raise ValueError('Cần ghi chú: mã phiếu thử/phiên bản tiêu chuẩn hoặc căn cứ rà soát.')
        db.execute('UPDATE tasks SET status=?,actual=?,value=?,lower_limit=?,upper_limit=?,unit=?,note=? WHERE id=?',(status,actual,value,lower,upper,unit,note,req['id']))
        log(db,actor,'TASK_'+status.upper(),{'before':dict(row),'request':req})
    return {'ok':True}
