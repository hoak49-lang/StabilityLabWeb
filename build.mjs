import fs from 'node:fs';
fs.mkdirSync('dist',{recursive:true});
fs.cpSync('public','dist',{recursive:true});
for(const name of ['index.html','app.js','worker.js','bridge.py','engine.py','server.py','dataio.py']) if(!fs.existsSync('dist/'+name))throw Error('Missing '+name);
console.log('Static application built.');
