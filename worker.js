'use strict';
let ready;
async function initialize(){
  importScripts('https://cdn.jsdelivr.net/pyodide/v314.0.6/full/pyodide.js');
  const py=await loadPyodide({indexURL:'https://cdn.jsdelivr.net/pyodide/v314.0.6/full/'});
  await py.loadPackage(['numpy','scipy']);
  py.FS.mkdirTree('/app/examples');
  const libs=await fetch('./excel-libs.zip');if(!libs.ok)throw Error('Không tải được thư viện Excel');
  py.unpackArchive(new Uint8Array(await libs.arrayBuffer()),'zip',{extractDir:'/app'});
  for(const name of ['bootstrap.py','engine.py','dataio.py','reporting.py','server.py','bridge.py','requirements.txt','examples/demo.csv']){
    const r=await fetch('./'+name);if(!r.ok)throw Error('Không tải được '+name);
    py.FS.writeFile('/app/'+name,new Uint8Array(await r.arrayBuffer()));
  }
  py.runPython("import sys, os\nos.chdir('/app')\nsys.path.insert(0, '/app')\nfrom bridge import dispatch");
  return py;
}
ready=initialize();
ready.then(()=>postMessage({ready:true})).catch(e=>postMessage({fatal:String(e)}));
let queue=Promise.resolve();
self.onmessage=({data})=>{queue=queue.then(async()=>{try{const py=await ready;py.globals.set('_route',data.url);py.globals.set('_body',data.body===undefined?'':JSON.stringify(data.body));const r=JSON.parse(py.runPython('dispatch(_route, _body)'));postMessage({id:data.id,...r});}catch(e){postMessage({id:data.id,error:String(e)});}});};
