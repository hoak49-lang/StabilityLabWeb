import unittest, tempfile, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import program

class ProgramTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.old=program.DB;program.DB=Path(self.tmp.name)/'test.db'
    def tearDown(self):
        program.DB=self.old;self.tmp.cleanup()
    def test_calendar(self):
        self.assertEqual(program.month_date('2024-01-31',1),'2024-02-29')
        self.assertEqual(program.month_date('2024-02-29',12),'2025-02-28')
        with self.assertRaises(ValueError):program.month_date('2024-01-01',1.5)
    def test_lifecycle_and_persistence(self):
        d={'eligible':True,'blockers':[],'config':{'attributes':['Assay']},'studies':[{'label':'25C','times':[0,3,6],'rows':[{'batch':'B1','strength':'50mg','pack':'P30','tests':[True,False,True]}]}]}
        r=program.create({'name':'Test','owner':'QC','start':'2024-01-31','review':'P001 v1','design':d})
        self.assertEqual(r['count'],2)
        t=program.snapshot()['tasks'][0]
        req={'id':t['id'],'actor':'QC','actual':'2024-01-31','note':'P001 v1'}
        with self.assertRaises(ValueError):program.update(dict(req,status='reviewed'))
        program.update(dict(req,status='pulled'))
        with self.assertRaises(ValueError):program.update(dict(req,status='tested',value='nan',lower=90,unit='%'))
        program.update(dict(req,status='tested',value=89,lower=90,upper=110,unit='%'))
        program.update(dict(req,status='reviewed'))
        with self.assertRaises(ValueError):program.update(dict(req,status='tested',value=99,lower=90,unit='%'))
        snap=program.snapshot();self.assertEqual(snap['tasks'][0]['value'],89);self.assertEqual(len(snap['events']),4)
        self.assertEqual(snap['tasks'][1]['due'],'2024-07-31')

if __name__=='__main__':unittest.main()
