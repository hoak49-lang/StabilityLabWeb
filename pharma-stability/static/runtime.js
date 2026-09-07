'use strict';
window.stabilityRequest=async(url,body)=>fetch(url,{method:body===undefined?'GET':'POST',headers:{'X-Stability-Token':document.querySelector('meta[name="stability-token"]').content,...(body===undefined?{}:{'Content-Type':'application/json'})},body:body===undefined?undefined:JSON.stringify(body)});
