"""Exploratory multi-temperature kinetic modelling. Never issues an ICH shelf life."""
import bootstrap
import math
import numpy as np
from scipy.optimize import least_squares
from engine import AnalysisError,number

R=8.31446261815324
VERSION='StabilityLab Windows 2.0 / Arrhenius 1.0'

def concentration(t,c0,k,order):
    if order==0:return c0-k*t
    if order==1:return c0*np.exp(np.clip(-k*t,-700,700))
    return c0/(1+k*c0*t)

def lifetime(c0,limit,k,order):
    if not 0<limit<c0 or not np.isfinite(k) or k<=0:raise AnalysisError('Cần 0 < giới hạn dưới < C0 và tốc độ k dương.')
    return ((c0-limit) if order==0 else math.log(c0/limit) if order==1 else (1/limit-1/c0))/k

def parse_kinetic_table(table):
    required=['batch','strength','pack','attribute','temp_c','rh','time','value']
    headers=table['headers']
    missing=[k for k in required if k not in headers]
    if missing:raise AnalysisError('Bảng LHCT thiếu cột: '+', '.join(missing)+'. Dùng mẫu Arrhenius riêng.')
    output=[]
    for row in table['rows']:
        r={'row_id':row['row_id']}
        for k in required:
            v=row['cells'][headers.index(k)]
            if k in ('temp_c','time','value'):v=number(v,f'Dòng {row["row_id"]}: {k}')
            elif v is None or not str(v).strip():raise AnalysisError(f'Dòng {row["row_id"]}: {k} trống.')
            else:v=str(v).strip()
            r[k]=v
        if r['time']<0 or r['value']<=0 or not -80<=r['temp_c']<=200:raise AnalysisError('LHCT: thời gian phải ≥0, nồng độ còn lại >0, nhiệt độ trong −80…200 °C.')
        output.append(r)
    return output

def fit_batch(rows,order,target_c,initial=None,values=None):
    temps=sorted({r['temp_c'] for r in rows})
    ti=np.array([temps.index(r['temp_c']) for r in rows],dtype=int)
    t=np.array([r['time'] for r in rows],dtype=float)
    y=np.array([r['value'] for r in rows],dtype=float) if values is None else np.array(values,dtype=float)
    c0=np.array([np.mean(y[(ti==i)&(t==0)]) for i in range(len(temps))])
    x=(1/(target_c+273.15)-1/(np.array(temps)+273.15))*1000/R
    independent=[]
    for i,temp in (enumerate(temps) if initial is None else []):
        ix=ti==i;times=t[ix];obs=y[ix]
        transformed=obs if order==0 else np.log(np.maximum(obs,1e-12)) if order==1 else 1/np.maximum(obs,1e-12)
        slope=float(np.polyfit(times,transformed,1)[0])
        k=max((slope if order==2 else -slope),1e-10)
        opt=least_squares(lambda p:concentration(times,p[0],np.exp(p[1]),order)-obs,[max(c0[i],1e-9),np.log(k)],bounds=([1e-10,-40],[max(100,float(np.max(y))*10),20]),max_nfev=500)
        independent.append({'temp_c':temp,'k':float(np.exp(opt.x[1])),'c0':float(opt.x[0]),'success':bool(opt.success)})
    if initial is None:
        ea,logk=np.polyfit(x,np.log([r['k'] for r in independent]),1)
        initial=np.r_[np.clip(logk,-39,19),np.clip(ea,-199,399),np.maximum(c0,1e-8)]
    bounds=(np.r_[-40,-200,np.full(len(temps),1e-10)],np.r_[20,400,np.full(len(temps),max(100,float(np.max(y))*10))])
    def predict(p):return concentration(t,p[2:][ti],np.exp(np.clip(p[0]+p[1]*x[ti],-60,60)),order)
    result=least_squares(lambda p:predict(p)-y,initial,bounds=bounds,max_nfev=700,x_scale='jac')
    if not result.success or not np.all(np.isfinite(result.x)):raise AnalysisError('Mô hình động học không hội tụ. Kiểm tra dữ liệu hoặc chọn bậc khác.')
    predicted=predict(result.x);residual=y-predicted;n=len(y);p=len(result.x);sse=float(residual@residual)
    if n<=p+1:raise AnalysisError('Không đủ quan sát cho số tham số của mô hình.')
    sst=float(np.sum((y-np.mean(y))**2))
    aic=n*math.log(max(sse/n,1e-300))+2*(p+1)
    aicc=aic+2*(p+1)*(p+2)/(n-p-2) if n>p+2 else None
    covariance=np.linalg.pinv(result.jac.T@result.jac)*(sse/(n-p))
    return dict(params=result.x,temps=temps,ti=ti,t=t,y=y,predicted=predicted,residual=residual,
                k=float(np.exp(result.x[0])),ea=float(result.x[1]),rmse=math.sqrt(sse/(n-p)),
                r_squared=1-sse/sst if sst>0 else None,aicc=aicc,n=n,df=n-p,
                independent=independent,condition_number=float(np.linalg.cond(result.jac)),
                covariance=covariance,boundary=bool(np.any(result.active_mask)))

def analyze_arrhenius(rows,config):
    order_raw=number(config.get('order',1),'Bậc phản ứng')
    if order_raw not in (0,1,2):raise AnalysisError('Chọn bậc phản ứng 0, 1 hoặc 2.')
    order=int(order_raw);target=number(config.get('target_c'),'Nhiệt độ đích');c0=number(config.get('c0'),'C0 đích');limit=number(config.get('limit'),'Giới hạn dưới')
    if not -80<=target<=150:raise AnalysisError('Nhiệt độ đích phải trong −80…150 °C.')
    lifetime(c0,limit,1,order)
    unit=config.get('time_unit','months')
    if unit not in ('days','months'):raise AnalysisError('Đơn vị thời gian là days hoặc months; không trộn đơn vị.')
    draws=number(config.get('bootstrap',200),'Số mẫu bootstrap')
    if draws!=int(draws) or not 100<=draws<=1000:raise AnalysisError('Chọn 100–1000 lần bootstrap.')
    seed=number(config.get('seed',20260907),'Hạt giống ngẫu nhiên')
    if seed!=int(seed) or not 0<=seed<2**32:raise AnalysisError('Seed phải là số nguyên từ 0 đến 2^32−1.')
    if not rows or len(rows)>5000:raise AnalysisError('Cần 1–5000 dòng dữ liệu LHCT.')
    keys={(r['strength'],r['pack'],r['attribute'],r['rh']) for r in rows}
    if len(keys)!=1:raise AnalysisError('Arrhenius chỉ phân tích một hàm lượng × bao bì × chỉ tiêu × RH. Không gộp độ ẩm khác nhau vào mô hình chỉ có nhiệt độ.')
    batches=sorted({r['batch'] for r in rows})
    if len(batches)>12:raise AnalysisError('Tối đa 12 lô trong một lần phân tích LHCT.')
    warnings=['Dự đoán thăm dò từ mô hình nhiệt độ; không phải hạn dùng ICH Q1E, không thay thế dữ liệu dài hạn.',
              'Bootstrap lấy lại phần dư trong từng nhiệt độ, có điều kiện trên bậc động học, C0 đích và cơ chế đã chọn; không bao gồm sai số do chọn sai cơ chế hoặc ảnh hưởng RH chưa mô hình hóa.']
    blockers=[]
    if config.get('same_mechanism') is not True:blockers.append('Chưa xác nhận cùng cơ chế phân hủy, không chuyển pha hoặc thay đổi hệ bao bì trong dải nhiệt độ.')
    if config.get('humidity_controlled') is not True:blockers.append('Chưa xác nhận ảnh hưởng độ ẩm/bao bì đã kiểm soát khi ngoại suy nhiệt độ.')
    if not str(config.get('rationale','')).strip():blockers.append('Chưa ghi căn cứ chọn bậc phản ứng, C0 và phạm vi dự đoán.')
    if len(batches)<3:warnings.append('Dưới 3 lô; không suy rộng kết quả thành hạn dùng chung của sản phẩm.')
    rng=np.random.default_rng(int(seed));results=[]
    for batch in batches:
        subset=sorted([r for r in rows if r['batch']==batch],key=lambda r:(r['temp_c'],r['time'],r['row_id']))
        temps=sorted({r['temp_c'] for r in subset})
        if len(temps)<3:raise AnalysisError(f'Lô {batch}: cần ít nhất 3 nhiệt độ khác nhau để ước lượng và kiểm tra Arrhenius; một điều kiện cấp tốc không đủ.')
        if len(temps)>12:raise AnalysisError('Tối đa 12 nhiệt độ mỗi lô.')
        for temp in temps:
            points=[r for r in subset if r['temp_c']==temp]
            if len(points)<4 or len({r['time'] for r in points})<3 or not any(r['time']==0 for r in points):raise AnalysisError(f'Lô {batch}, {temp} °C: cần ≥4 quan sát, ≥3 mốc khác nhau và có mốc 0.')
        fit=fit_batch(subset,order,target)
        if fit['ea']<=0:blockers.append(f'Lô {batch}: Ea không dương; mô hình tăng tốc nhiệt thông thường không được hỗ trợ.')
        if fit['boundary'] or fit['condition_number']>1e10:blockers.append(f'Lô {batch}: tham số sát biên hoặc khó xác định; cần thiết kế/dữ liệu tốt hơn.')
        if target<min(temps) or target>max(temps):warnings.append(f'Lô {batch}: {target:g} °C nằm ngoài dải {min(temps):g}–{max(temps):g} °C; đang ngoại suy.')
        if len(temps)==3:warnings.append(f'Lô {batch}: chỉ 3 mức nhiệt; khả năng phát hiện độ cong Arrhenius còn hạn chế.')
        comparison=[]
        for candidate in (0,1,2):
            try:
                other=fit if candidate==order else fit_batch(subset,candidate,target)
                comparison.append(dict(order=candidate,rmse=other['rmse'],aicc=other['aicc']))
            except AnalysisError:comparison.append(dict(order=candidate,rmse=None,aicc=None))
        boot=[];ea_boot=[];failures=0
        for _ in range(int(draws)):
            values=fit['predicted'].copy()
            for i in range(len(temps)):
                mask=fit['ti']==i;res=fit['residual'][mask];res=res-res.mean()
                # Leverage correction approximately restores residual variance within each stratum.
                factor=math.sqrt(len(res)/max(1,len(res)-2))
                values[mask]+=rng.choice(res,len(res),replace=True)*factor
            if np.any(values<=0):failures+=1;continue
            try:
                bf=fit_batch(subset,order,target,initial=fit['params'],values=values)
                if bf['boundary']:failures+=1;continue
                life=lifetime(c0,limit,bf['k'],order)
                if not math.isfinite(life):failures+=1;continue
                boot.append(life);ea_boot.append(bf['ea'])
            except (AnalysisError,ValueError,FloatingPointError):failures+=1
        interval=None
        if failures>draws*.1:blockers.append(f'Lô {batch}: {failures}/{int(draws)} mẫu bootstrap không hợp lệ; không báo khoảng bất định.')
        else:interval=[float(x) for x in np.quantile(boot,[.025,.975])]
        if ea_boot and np.quantile(ea_boot,.025)<=0:warnings.append(f'Lô {batch}: khoảng bootstrap của Ea bao gồm giá trị không dương.')
        residual_rows=[dict(row_id=r['row_id'],temp_c=r['temp_c'],time=r['time'],value=r['value'],fitted=float(f),residual=float(e)) for r,f,e in zip(subset,fit['predicted'],fit['residual'])]
        curves=[]
        for i,temp in enumerate(temps):
            tt=np.linspace(0,max(r['time'] for r in subset if r['temp_c']==temp),61)
            k=fit['k']*math.exp(fit['ea']*1000/R*(1/(target+273.15)-1/(temp+273.15)))
            yy=concentration(tt,fit['params'][2+i],k,order)
            curves.append(dict(temp_c=temp,k=k,c0=float(fit['params'][2+i]),points=[dict(time=float(t),value=float(v)) for t,v in zip(tt,yy)]))
        results.append(dict(batch=batch,temperatures=temps,n=fit['n'],df=fit['df'],k_target=fit['k'],ea_kj_mol=fit['ea'],
                            time_to_limit=lifetime(c0,limit,fit['k'],order),bootstrap_interval95=interval,bootstrap_valid=len(boot),bootstrap_failed=failures,
                            rmse=fit['rmse'],r_squared=fit['r_squared'],aicc=fit['aicc'],comparison=comparison,
                            independent_rates=fit['independent'],residuals=residual_rows,curves=curves))
    return dict(version=VERSION,model='Arrhenius nonlinear least squares on original concentration scale',order=order,
                time_unit=unit,target_c=target,c0=c0,limit=limit,group=list(next(iter(keys))),batches=results,
                minimum_point_estimate=min(r['time_to_limit'] for r in results),approved_shelf_life=None,
                warnings=warnings,blockers=blockers,config=config,input_snapshot=rows,
                sources=['https://goldbook.iupac.org/terms/view/A00446','https://www.ema.europa.eu/en/ich-q1-guideline-stability-testing-drug-substances-drug-products'])
