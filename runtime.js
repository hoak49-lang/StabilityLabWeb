'use strict';
const runtimeWorker=new Worker(new URL('./worker.js', location.href));
const pending=new Map();let callId=0,loaded=false,failed=false;
const statusEl=document.getElementById('runtime-status');
const readyPromise=new Promise((resolve,reject)=>{
  runtimeWorker.onmessage=({data})=>{
    if(data.ready){loaded=true;statusEl.textContent='Sẵn sàng · Dữ liệu được xử lý trong trình duyệt. Lưu thiết kế/dự án và tải báo cáo trước khi đóng hoặc tải lại trang.';resolve();return;}
    if(data.fatal){
  failed=true;
  console.error('StabilityLab worker error:', data.fatal);
  statusEl.textContent='Lỗi bộ tính toán: ' + data.fatal;
  reject(Error(data.fatal));
  return;
}
    const p=pending.get(data.id);if(p){pending.delete(data.id);data.error?p.reject(Error(data.error)):p.resolve(data);}
  };
  runtimeWorker.onerror=()=>{failed=true;const e=Error('Bộ tính toán bị gián đoạn. Hãy tải lại trang và mở dự án đã lưu.');statusEl.textContent=e.message;reject(e);for(const p of pending.values())p.reject(e);pending.clear();};
});
readyPromise.catch(()=>{});
window.stabilityRequest=async(url,body)=>{
  if(!loaded&&!failed)statusEl.textContent='Đang tải bộ tính toán lần đầu… Có thể mất 30–90 giây. Thao tác của bạn sẽ tiếp tục khi sẵn sàng.';
  await readyPromise;if(failed)throw Error(statusEl.textContent);
  const id=++callId;const r=await new Promise((resolve,reject)=>{pending.set(id,{resolve,reject});runtimeWorker.postMessage({id,url,body});});
  const bytes=Uint8Array.from(atob(r.base64),c=>c.charCodeAt(0));return new Response(bytes,{status:r.code,headers:{'Content-Type':r.kind}});
};
