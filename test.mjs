import fs from 'node:fs';import {loadPyodide} from 'pyodide';import assert from 'node:assert/strict';
const py=await loadPyodide();await py.loadPackage(['numpy','scipy']);
py.FS.mkdirTree('/app/examples');py.unpackArchive(new Uint8Array(fs.readFileSync('public/excel-libs.zip')),'zip',{extractDir:'/app'});
for(const name of ['bootstrap.py','engine.py','dataio.py','reporting.py','server.py','bridge.py','requirements.txt','examples/demo.csv'])py.FS.writeFile('/app/'+name,fs.readFileSync('public/'+name));
py.runPython("import sys,os\nos.chdir('/app')\nsys.path.insert(0,'/app')\nfrom bridge import dispatch");
function request(url,body){py.globals.set('_r',url);py.globals.set('_b',body===undefined?'':JSON.stringify(body));const r=JSON.parse(py.runPython('dispatch(_r,_b)'));const raw=Buffer.from(r.base64,'base64');return {status:r.code,raw,json:()=>JSON.parse(raw.toString())};}
const d=request('/api/demo').json();assert.equal(d.rows.length,42);
const mapping={batch:'batch',time:'time',value:'value',attribute:'attribute',condition:'condition'};
const m=request('/api/map',{dataset_id:d.dataset_id,mapping}).json();assert.equal(m.attributes.length,2);
const config={dataset_id:d.dataset_id,mapping,condition:m.conditions[0],attributes:['Assay','Impurity'],horizon:120,specifications:{Assay:{direction:'decrease',lower:90,transform:'none'},Impurity:{direction:'increase',upper:.5,transform:'none'}},review:{}};
const response=request('/api/analyze',config);assert.equal(response.status,200,response.raw.toString());const run=response.json();assert.ok(Math.abs(run.analyses[0].statistical_months-49.49367760527471)<1e-5);assert.equal(run.overall.candidate_months,null);
assert.equal(request('/api/history').json().length,1);
for(const format of ['html','xlsx','json']){const r=request('/api/export/'+run.id+'?format='+format);assert.equal(r.status,200);assert.ok(r.raw.length>100);if(format==='xlsx')assert.equal(r.raw.subarray(0,2).toString(),'PK');}
const project=request('/api/project/save',{dataset_id:d.dataset_id,settings:config}).json();assert.equal(request('/api/project/open',project).json().rows.length,42);
assert.equal(request('/api/map',{dataset_id:d.dataset_id,mapping:{}}).status,400);
assert.equal(request('/api/import',{filename:'bad.csv',base64:Buffer.from('batch,time,value\nB,0,abc').toString('base64')}).status,200);
assert.equal(request('/api/template').raw.subarray(0,2).toString(),'PK');
const multi=['batch,time,value,attribute,condition,strength,pack'];
for(const strength of ['50 mg','100 mg'])for(const row of d.rows)multi.push([...row.cells,strength,'P30'].join(','));
const multid=request('/api/import',{filename:'multi.csv',base64:Buffer.from(multi.join('\n')).toString('base64')}).json();
const multimap=request('/api/map',{dataset_id:multid.dataset_id,mapping}).json();assert.equal(new Set(multimap.rows.map(r=>r.study_group)).size,2);
const ungrouped=request('/api/analyze',{...config,dataset_id:multid.dataset_id});assert.equal(ungrouped.status,400);
const grouped=request('/api/analyze',{...config,dataset_id:multid.dataset_id,study_group:multimap.rows[0].study_group});assert.equal(grouped.status,200,grouped.raw.toString());assert.equal(grouped.json().selected_rows,42);assert.equal(grouped.json().unselected_rows,42);assert.ok(Math.abs(grouped.json().analyses[0].statistical_months-run.analyses[0].statistical_months)<1e-8);
const {createDesign,designSheets}=await import('./public/design-engine.mjs');
const plan=createDesign({mode:'full',strengths:[{label:'50 mg',batches:['B1','B2','B3']}],packs:[{label:'P30',system:'HDPE',size:'50mL',fill:'30 tablets'}],attributes:['Assay'],conditions:[{label:'LT',kind:'longterm',times:[0,3,6]}]});
assert.equal(request('/api/design/export',{sheets:designSheets(plan)}).raw.subarray(0,2).toString(),'PK');assert.equal(request('/api/design/export',{sheets:[]}).status,400);
request('/api/shutdown',{});assert.equal(request('/api/history').json().length,0);
console.log('PASS: WebAssembly runtime, 42-row import, mapping, two-attribute analysis, reference crossing, review blockers, history, three exports, project round-trip, invalid input, Excel template, session clear.');

