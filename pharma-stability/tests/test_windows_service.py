import sys,unittest,tempfile,threading,json,urllib.request,urllib.error,shutil
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import server

class ServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.oldroot=server.ROOT;cls.oldruns=server.RUNS;cls.oldport=server.PORT
        cls.tmp=tempfile.TemporaryDirectory();server.ROOT=Path(cls.tmp.name);server.RUNS=server.ROOT/'runs'
        for folder in ['static','examples']:shutil.copytree(cls.oldroot/folder,server.ROOT/folder)
        shutil.copy2(cls.oldroot/'requirements.txt',server.ROOT/'requirements.txt')
        cls.http=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler);server.PORT=cls.http.server_address[1]
        cls.thread=threading.Thread(target=cls.http.serve_forever,daemon=True);cls.thread.start()
    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown();cls.http.server_close();cls.thread.join();server.ROOT=cls.oldroot;server.RUNS=cls.oldruns;server.PORT=cls.oldport;cls.tmp.cleanup()
    def req(self,path,body=None,token=True):
        data=json.dumps(body).encode() if body is not None else None
        headers={'Content-Type':'application/json'}
        if token:headers['X-Stability-Token']=server.TOKEN
        request=urllib.request.Request(f'http://127.0.0.1:{server.PORT}'+path,data=data,headers=headers)
        try:
            with urllib.request.urlopen(request,timeout=120) as r:return r.status,r.read(),r.headers
        except urllib.error.HTTPError as e:return e.code,e.read(),e.headers
    def test_assets_offline_and_auth(self):
        for route in ['/','/app.js','/runtime.js','/design-ui.mjs','/design-engine.mjs','/arrhenius-ui.mjs','/style.css']:
            status,body,headers=self.req(route);self.assertEqual(status,200,route)
            if route.endswith(('.js','.mjs')):self.assertIn('javascript',headers['Content-Type'])
        self.assertEqual(self.req('/api/demo',token=False)[0],403)
        runtime=self.req('/runtime.js')[1].decode();self.assertNotIn('pyodide',runtime);self.assertNotIn('cdn.',runtime)
    def test_kinetic_flow_and_reports(self):
        d=json.loads(self.req('/api/kinetic/demo')[1]);id=d['dataset_id']
        groups=json.loads(self.req('/api/kinetic/groups',{'dataset_id':id})[1])
        config=dict(order=1,target_c=25,c0=100,limit=90,bootstrap=100,time_unit='months',same_mechanism=True,humidity_controlled=True,rationale='Synthetic')
        status,body,_=self.req('/api/kinetic/analyze',{'dataset_id':id,'group':groups['groups'][0],'config':config})
        self.assertEqual(status,200,body);run=json.loads(body);self.assertIsNone(run['approved_shelf_life'])
        for ext in ['json','xlsx','html']:
            status,body,_=self.req('/api/kinetic/export/'+run['id']+'?format='+ext);self.assertEqual(status,200);self.assertGreater(len(body),100)
            if ext=='xlsx':self.assertEqual(body[:2],b'PK')
        filename=server.ROOT/'kinetic_runs'/(run['id']+'.json');modified=json.loads(filename.read_bytes());modified['c0']=999;filename.write_text(json.dumps(modified),encoding='utf-8')
        self.assertEqual(self.req('/api/kinetic/export/'+run['id'])[0],400)
        mapping={k:k for k in ['batch','time','value','attribute','strength','pack']}
        params=dict(dataset_id=id,mapping=mapping,condition='Dài hạn',attributes=['Assay'],specifications={'Assay':{'direction':'decrease','lower':90}})
        self.assertEqual(self.req('/api/analyze',params)[0],400)
    def test_design_export(self):
        status,body,_=self.req('/api/design/export',{'sheets':[['Protocol',[['Item','Value'],['Status','DRAFT']]],['Data',[['batch','time','value'],['B1',0,None]]]]})
        self.assertEqual(status,200);self.assertEqual(body[:2],b'PK')

if __name__=='__main__':unittest.main()
