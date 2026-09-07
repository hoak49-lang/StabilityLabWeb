export const Q1D='https://www.ema.europa.eu/en/documents/scientific-guideline/ich-q-1-d-bracketing-and-matrixing-designs-stability-testing-drug-substances-and-drug-products-step-5_en.pdf';
const fail=m=>{throw Error(m);};
const unique=(a,label)=>{if(new Set(a).size!==a.length)fail(label+' có mục trùng.');};
const text=(x,label)=>{if(typeof x!=='string'||!x.trim()||x.length>300)fail(label+' cần có nội dung (tối đa 300 ký tự).');return x.trim();};
export function createDesign(input){
  const c=JSON.parse(JSON.stringify(input));
  if(!['full','bracket','matrix','combined'].includes(c.mode))fail('Kiểu thiết kế không hợp lệ.');
  const bracket=['bracket','combined'].includes(c.mode),matrix=['matrix','combined'].includes(c.mode);
  if(!Array.isArray(c.strengths)||!c.strengths.length||c.strengths.length>12)fail('Khai báo 1–12 hàm lượng.');
  if(!Array.isArray(c.packs)||!c.packs.length||c.packs.length>12)fail('Khai báo 1–12 quy cách.');
  if(!Array.isArray(c.conditions)||!c.conditions.length||c.conditions.length>6)fail('Khai báo 1–6 điều kiện.');
  c.strengths.forEach(s=>{s.label=text(s.label,'Hàm lượng');if(!Array.isArray(s.batches)||!s.batches.length||s.batches.length>12)fail('Mỗi hàm lượng cần 1–12 mã lô.');s.batches=s.batches.map(b=>text(b,'Mã lô'));unique(s.batches,'Mã lô trong '+s.label);});
  c.packs.forEach(p=>{for(const k of ['label','system','size','fill'])p[k]=text(p[k],'Bao bì: '+k);});
  unique(c.strengths.map(s=>s.label),'Hàm lượng');unique(c.packs.map(p=>p.label),'Mã quy cách');
  if(!Array.isArray(c.attributes)||!c.attributes.length||c.attributes.length>20)fail('Khai báo 1–20 chỉ tiêu.');
  c.attributes=c.attributes.map(a=>text(a,'Chỉ tiêu'));unique(c.attributes,'Chỉ tiêu');
  const blockers=[],warnings=[];
  if(c.strengths.some(s=>s.batches.length<3))blockers.push('Có hàm lượng khai báo dưới 3 lô. Cần xem xét yêu cầu về lô của nghiên cứu đăng ký và giải trình thiết kế.');
  const strengths=bracket?c.strengths.filter(s=>s.selected===true):c.strengths;
  const packs=bracket?c.packs.filter(p=>p.selected===true):c.packs;
  if(!strengths.length||!packs.length)fail('Chọn ít nhất một hàm lượng và một quy cách để thử trực tiếp.');
  const reduceStrength=strengths.length<c.strengths.length,reducePack=packs.length<c.packs.length;
  if(bracket&&reduceStrength&&strengths.length<2)blockers.push('Bracketing hàm lượng cần ít nhất hai mức cực trị được chứng minh; không dùng một mức để đại diện mọi hàm lượng.');
  if(bracket&&reducePack&&packs.length<2)blockers.push('Bracketing quy cách cần các cấu hình cực trị đã được chứng minh; không tự dùng một quy cách đại diện.');
  if(bracket&&(reduceStrength||reducePack)&&c.extremes!==true)blockers.push('Chưa xác nhận các mức chọn thử bao quát cực trị của các mức được đại diện.');
  if(reduceStrength&&c.formulation==='different')blockers.push('Khác tá dược giữa các hàm lượng: không đề xuất bracketing tự động; chọn thiết kế đầy đủ hoặc đánh giá riêng.');
  if((reduceStrength||matrix&&c.strengths.length>1)&&!['related','supported','different'].includes(c.formulation))blockers.push('Chưa đánh giá quan hệ công thức giữa các hàm lượng.');
  if(c.mode!=='full'&&!String(c.rationale||'').trim())blockers.push('Thiết kế rút gọn chưa có giải trình khoa học và tài liệu hỗ trợ.');
  if(matrix){
    if(!['low','moderate','high'].includes(c.variability))blockers.push('Chưa đánh giá biến thiên dữ liệu hỗ trợ cho matrixing.');
    if(c.variability==='high')blockers.push('Biến thiên lớn: không đề xuất matrixing.');
    if(c.variability==='moderate'&&!String(c.statisticalEvidence||'').trim())blockers.push('Biến thiên vừa: cần đánh giá thống kê về độ chính xác hoặc lực kiểm định của thiết kế.');
    if(c.predictable!==true)blockers.push('Chưa xác nhận dữ liệu hỗ trợ cho thấy độ ổn định có thể dự đoán.');
    if(c.packs.length>1&&c.packEvidence!==true)blockers.push('Chưa đánh giá tính đại diện của hệ bao bì cho matrixing.');
    if(c.formulation==='different'&&!String(c.statisticalEvidence||'').trim())blockers.push('Matrixing giữa các công thức khác tá dược cần dữ liệu so sánh và giải trình riêng.');
    if(!['half','third'].includes(c.reduction))fail('Chọn mức matrixing giảm 1/2 hoặc 1/3 ở mốc trung gian.');
  }
  if(bracket&&reducePack&&!String(c.packRationale||'').trim())blockers.push('Cần giải trình cực trị bao bì dựa trên hệ kín, thấm ẩm/oxy, khoảng không đầu và các đặc tính liên quan.');
  if(c.mode==='combined'&&!String(c.combinedRationale||'').trim())blockers.push('Phối hợp bracketing và matrixing cần đánh giá riêng tác động của hai lần giảm mẫu.');
  if(c.mode!=='full')warnings.push('Lịch là đề xuất để chuyên gia đánh giá; chưa chứng minh lực kiểm định, độ chính xác hạn dùng hoặc đáp ứng mọi yêu cầu đăng ký.');
  if(bracket&&!reduceStrength&&!reducePack)warnings.push('Mọi hàm lượng và quy cách đều được chọn: bracketing chưa làm giảm tổ hợp.');
  const combinations=[];
  strengths.forEach((s,si)=>packs.forEach((p,pi)=>s.batches.forEach((batch,bi)=>combinations.push({strength:s.label,pack:p.label,system:p.system,size:p.size,fill:p.fill,batch,phase:si+pi+bi}))));
  const fullCombos=c.strengths.reduce((n,s)=>n+s.batches.length*c.packs.length,0);
  if(combinations.length>1000)fail('Thiết kế vượt 1.000 tổ hợp. Chia thành các nghiên cứu phù hợp.');
  const studies=[];let full=0,selected=0;
  c.conditions.forEach((condition,ci)=>{
    const label=text(condition.label,'Điều kiện');
    if(!['longterm','accelerated','intermediate'].includes(condition.kind))fail('Loại điều kiện không hợp lệ.');
    let times=condition.times;
    if(!Array.isArray(times)||times.length<3||times.length>40||times.some(t=>typeof t!=='number'||!Number.isFinite(t)||t<0||t>1200))fail(label+': cần 3–40 mốc tháng hợp lệ.');
    unique(times,'Mốc thời gian '+label);times=[...times].sort((a,b)=>a-b);
    if(times[0]!==0)fail(label+': cần mốc ban đầu 0 tháng.');
    const end=times.at(-1),forced=new Set([0,end]);
    if(matrix&&condition.kind==='longterm'){
      if(end>=12){if(!times.includes(12))times.push(12);forced.add(12);}
      if(condition.partial===true){const submission=Number(condition.submission);if(!(submission>0&&submission<=end))fail(label+': mốc dữ liệu cuối trước nộp hồ sơ phải lớn hơn 0 và không vượt mốc cuối nghiên cứu.');if(!times.includes(submission))times.push(submission);forced.add(submission);}
    }
    times.sort((a,b)=>a-b);
    const middle=times.filter(t=>!forced.has(t));
    const denominator=c.reduction==='third'?3:2;
    const rows=combinations.map(combo=>({...combo,tests:times.map(t=>!matrix||forced.has(t)||(combo.phase+middle.indexOf(t))%denominator!==0),repairs:[]}));
    const loads=()=>times.map((_,ti)=>rows.filter(r=>r.tests[ti]).length);
    if(matrix){
      const cutoff=condition.kind==='longterm'?Math.min(12,end):end;
      const early=times.map((t,i)=>t<=cutoff?i:-1).filter(i=>i>=0);
      if(early.length<3)fail(label+': lịch gốc chưa có ít nhất 3 mốc tính đến '+cutoff+' tháng. Thêm mốc trước khi áp dụng matrixing.');
      for(const row of rows){while(early.filter(i=>row.tests[i]).length<3){const count=loads();const candidates=early.filter(i=>!row.tests[i]).sort((a,b)=>count[a]-count[b]||times[a]-times[b]);const i=candidates[0];row.tests[i]=true;row.repairs.push(times[i]);}}
    }
    const count=rows.reduce((n,r)=>n+r.tests.filter(Boolean).length,0);
    const counts=rows.map(r=>r.tests.filter(Boolean).length);
    const cutoff=condition.partial===true?Number(condition.submission):end;
    const pre=rows.map(r=>times.filter((t,i)=>t<=cutoff&&r.tests[i]).length);
    const repaired=rows.reduce((n,r)=>n+r.repairs.length,0);
    if(Math.max(...counts)-Math.min(...counts)>1||Math.max(...pre)-Math.min(...pre)>1)warnings.push(label+': số mốc giữa các tổ hợp chưa cân bằng tốt; cần rà soát lịch và các mốc trước nộp hồ sơ.');
    if(repaired)warnings.push(label+': bổ sung '+repaired+' lượt thử để mỗi tổ hợp có ít nhất 3 mốc theo khoảng kiểm tra áp dụng.');
    full+=fullCombos*times.length;selected+=count;
    studies.push({label,kind:condition.kind,times,forced:[...forced].sort((a,b)=>a-b),rows,selected:count,full:fullCombos*times.length,min:Math.min(...counts),max:Math.max(...counts),loads:loads(),repaired});
  });
  unique(studies.map(s=>s.label),'Tên điều kiện');
  const omitted=[];c.strengths.forEach(s=>c.packs.forEach(p=>{if(!strengths.includes(s)||!packs.includes(p))omitted.push({strength:s.label,pack:p.label});}));
  return {schema:'stabilitylab.design.v1',created:new Date().toISOString(),config:c,studies,omitted,full,selected,reduction:full?100*(1-selected/full):0,tests:selected*c.attributes.length,blockers,warnings,eligible:blockers.length===0,source:Q1D};
}
export function designSheets(design){
  const summary=[['Mục','Nội dung'],['Trạng thái','DỰ THẢO — cần chuyên gia phê duyệt'],['Tên nghiên cứu',design.config.name||''],['Thiết kế',design.config.mode],['Lượt tổ hợp × mốc đầy đủ',design.full],['Lượt tổ hợp × mốc đề xuất',design.selected],['Giảm thực tế (%)',design.reduction],['Chỉ tiêu',design.config.attributes.join('; ')],['Giải trình',design.config.rationale||''],['Cực trị bao bì',design.config.packRationale||''],['Đánh giá thống kê',design.config.statisticalEvidence||''],['Phối hợp thiết kế',design.config.combinedRationale||''],['Nhập kết quả','Trang Data chứa các mốc dự kiến, giá trị trống chưa phải kết quả. Lưu nguyên lịch; tạo bản sao Data chỉ gồm quan sát đã đo, điền kết quả và nhập bản sao vào Phân tích. Không điền 0 cho mốc chưa đo.'],['Nguồn',Q1D],...design.blockers.map(x=>['Cần xử lý',x]),...design.warnings.map(x=>['Cần xem xét',x])];
  const schedule=[['Điều kiện','Hàm lượng','Quy cách','Hệ bao bì','Dung tích','Lượng nạp','Lô','Tháng','Thử','Lý do']];
  const template=[['batch','time','value','attribute','condition','strength','pack']];
  for(const s of design.studies)for(const r of s.rows)s.times.forEach((t,i)=>{schedule.push([s.label,r.strength,r.pack,r.system,r.size,r.fill,r.batch,t,r.tests[i]?'T':'—',r.repairs.includes(t)?'Bổ sung tối thiểu 3 mốc':s.forced.includes(t)?'Mốc thử đầy đủ':r.tests[i]?'Theo lịch':'Bỏ theo matrixing']);if(r.tests[i])for(const a of design.config.attributes)template.push([r.batch,t,null,a,s.label,r.strength,r.pack]);});
  const omitted=[['Hàm lượng không thử trực tiếp','Quy cách không thử trực tiếp'],...design.omitted.map(r=>[r.strength,r.pack])];
  return [['Protocol',summary],['Schedule',schedule],['Data',template],['Bracketed',omitted]];
}
