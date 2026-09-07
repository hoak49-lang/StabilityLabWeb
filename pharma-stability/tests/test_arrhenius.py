import sys,unittest,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import bootstrap
import numpy as np
from arrhenius import concentration,lifetime,fit_batch,analyze_arrhenius,parse_kinetic_table,R
from engine import AnalysisError
from dataio import parse_file

def synthetic(order=1,noise=0):
    rng=np.random.default_rng(413);k=[.2,.002,.00002][order];rows=[]
    for temp in [40,50,60]:
        kt=k*math.exp(75*1000/R*(1/298.15-1/(temp+273.15)))
        for t in [0,.5,1,2,3,6]:
            rows.append(dict(row_id=len(rows)+2,batch='B1',strength='50 mg',pack='P30',attribute='Assay',rh='75',temp_c=temp,time=t,value=float(concentration(t,100,kt,order)+rng.normal(0,noise))))
    return rows,k

class ArrheniusTests(unittest.TestCase):
    def test_known_all_orders(self):
        for order in range(3):
            rows,k=synthetic(order);fit=fit_batch(rows,order,25)
            self.assertAlmostEqual(fit['ea'],75,places=5);self.assertAlmostEqual(fit['k']/k,1,places=6)
            expected=[50,math.log(100/90)/.002,(1/90-1/100)/.00002][order]
            self.assertAlmostEqual(lifetime(100,90,fit['k'],order),expected,places=5)
    def test_bootstrap_and_reproducibility(self):
        rows,k=synthetic(noise=.12);c=dict(order=1,target_c=25,c0=100,limit=90,bootstrap=100,seed=42,time_unit='months',same_mechanism=True,humidity_controlled=True,rationale='Synthetic')
        a=analyze_arrhenius(rows,c);b=analyze_arrhenius(rows,c)
        self.assertEqual(a['batches'][0]['bootstrap_interval95'],b['batches'][0]['bootstrap_interval95'])
        interval=a['batches'][0]['bootstrap_interval95'];self.assertIsNotNone(interval);self.assertLess(interval[0],interval[1]);self.assertAlmostEqual(a['batches'][0]['time_to_limit'],math.log(100/90)/k,delta=5)
        self.assertIsNone(a['approved_shelf_life']);self.assertFalse(a['blockers'])
    def test_insufficient_temperature_and_humidity(self):
        rows,_=synthetic();config=dict(order=1,target_c=25,c0=100,limit=90,bootstrap=100)
        with self.assertRaisesRegex(AnalysisError,'3 nhiệt độ'):analyze_arrhenius([r for r in rows if r['temp_c']==40],config)
        rows[-1]['rh']='60'
        with self.assertRaisesRegex(AnalysisError,'RH'):analyze_arrhenius(rows,config)
    def test_no_baseline(self):
        rows,_=synthetic()
        with self.assertRaisesRegex(AnalysisError,'mốc 0'):analyze_arrhenius([r for r in rows if r['time']!=0],dict(order=1,target_c=25,c0=100,limit=90,bootstrap=100))
    def test_limits_and_kelvin(self):
        with self.assertRaises(AnalysisError):lifetime(100,110,.002,1)
        rows,_=synthetic()
        with self.assertRaises(AnalysisError):analyze_arrhenius(rows,dict(order=1,target_c=-273.15,c0=100,limit=90,bootstrap=100))
    def test_strict_input(self):
        for data in ['batch,time,value\nB,0,100','batch,strength,pack,attribute,temp_c,rh,time,value\nB,S,P,A,40,75,0,-1']:
            with self.assertRaises(AnalysisError):parse_kinetic_table(parse_file(data.encode(),'test.csv'))

if __name__=='__main__':unittest.main()
