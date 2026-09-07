import bootstrap
from pathlib import Path
import json,hashlib,tkinter as tk
from dataio import parse_file,map_rows
from engine import analyze
from arrhenius import parse_kinetic_table,fit_batch

root=Path(__file__).resolve().parent
manifest=root.parent/'MANIFEST_SHA256.json'
if manifest.exists():
    entries=json.loads(manifest.read_text('utf-8'))
    for name,digest in entries.items():
        path=root.parent/name
        assert path.is_file(),f'Missing: {name}'
        assert hashlib.sha256(path.read_bytes()).hexdigest()==digest,f'Changed: {name}'
    print('PASS: distribution checksums')
t=parse_file((root/'examples/demo.csv').read_bytes(),'demo.csv')
rows=map_rows(t,{k:k for k in ['batch','time','value','attribute','condition']})
q=analyze([r for r in rows if r['attribute']=='Assay'],{'direction':'decrease','lower':90})
assert abs(q['statistical_months']-49.49367760527471)<1e-5
a=parse_kinetic_table(parse_file((root/'examples/arrhenius.csv').read_bytes(),'arrhenius.csv'))
f=fit_batch(a,1,25);assert abs(f['ea']-75)<2;assert abs(f['k']-.002)<.0001
window=tk.Tk();window.withdraw();window.update();window.destroy()
print('PASS: scientific libraries, ICH Q1E reference, Arrhenius reference, native window')
print('No Internet used. This is an installation check, not a GxP validation certificate.')
