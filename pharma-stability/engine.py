"""Fixed-batch stability analysis. ICH Q1E B.1 and B.2.2.

All confidence limits refer to the fitted mean, not individual predictions.
No observations are removed, no acceptance limits are inferred from data.
"""
import bootstrap  # noqa: F401
import math
from collections import defaultdict
import numpy as np
from scipy import stats, optimize

VERSION = '1.0.0'
MODEL_NAMES = {
    'pooled': 'Một đường hồi quy chung',
    'common_slope': 'Hệ số góc chung, hệ số chặn riêng',
    'separate': 'Hệ số góc và hệ số chặn riêng từng lô',
}


class AnalysisError(ValueError):
    pass


def number(value, name):
    if isinstance(value, bool) or value is None or str(value).strip() == '':
        raise AnalysisError(f'{name}: cần giá trị số, không được để trống.')
    try:
        result = float(value)
    except (ValueError, TypeError):
        raise AnalysisError(f'{name}: giá trị {str(value)[:60]!r} không phải số. Không tự thay giá trị dưới LOQ hoặc thiếu dữ liệu.')
    if not math.isfinite(result) or abs(result) > 1e12:
        raise AnalysisError(f'{name}: số phải hữu hạn và nằm trong phạm vi ±10^12.')
    return result


def fit_ols(X, y):
    beta, _, rank, singular = np.linalg.lstsq(X, y, rcond=None)
    n, k = X.shape
    if rank != k or n <= k or singular[0] / singular[-1] > 1e10:
        raise AnalysisError('Thiết kế không đủ hạng hoặc không còn bậc tự do sai số. Cần thêm mốc thời gian / quan sát độc lập.')
    residual = y - X @ beta
    sse = float(residual @ residual)
    # SVD avoids explicitly inverting X.T @ X, which squares its condition number.
    _, s, vt = np.linalg.svd(X, full_matrices=False)
    inverse = (vt.T / (s * s)) @ vt
    mse = sse / (n - k)
    return dict(beta=beta, residual=residual, fitted=X @ beta, sse=sse,
                mse=mse, df=n-k, k=k, inverse=inverse, covariance=mse*inverse, X=X)


def nested_test(reduced, full):
    df1 = full['k'] - reduced['k']
    ss = max(0., reduced['sse'] - full['sse'])
    if df1 <= 0 or full['mse'] <= 1e-24:
        return dict(f=None, p=None, df1=df1, df2=full['df'], ss=ss)
    f = ss / df1 / full['mse']
    return dict(f=float(f), p=float(stats.f.sf(f, df1, full['df'])),
                df1=df1, df2=full['df'], ss=ss)


def extrapolation_cap(duration, review):
    """Conservative implementation for quantitative attributes with analysis.

    Little/no-change non-statistical shortcuts are deliberately not automated.
    Decisions use explicitly supplied supporting evidence, never a regression p-value.
    """
    storage = review.get('storage', 'room')
    accelerated = review.get('accelerated', 'unknown')
    months = number(review.get('accelerated_months', 0), 'Thời gian lão hóa cấp tốc')
    intermediate_months = number(review.get('intermediate_months', 0), 'Thời gian điều kiện trung gian')
    if storage not in ('room', 'refrigerated', 'frozen', 'below20'):
        raise AnalysisError('Nhóm điều kiện bảo quản không hợp lệ.')
    if accelerated not in ('unknown', 'no_change', 'change'):
        raise AnalysisError('Đánh giá lão hóa cấp tốc không hợp lệ.')
    if review.get('intermediate', 'unknown') not in ('unknown', 'no_change', 'change'):
        raise AnalysisError('Đánh giá điều kiện trung gian không hợp lệ.')
    if months < 0 or intermediate_months < 0:
        raise AnalysisError('Thời gian nghiên cứu hỗ trợ không được âm.')
    support = review.get('supporting_data') is True and len(str(review.get('evidence', '')).strip()) >= 15
    if storage in ('frozen', 'below20'):
        return dict(months=duration, rule='X', section='Q1E 2.5.2–2.5.3',
                    reason='Không tự động ngoại suy cho bảo quản đông lạnh hoặc dưới −20 °C.')
    if not review.get('allow_extrapolation'):
        return dict(months=duration, rule='X', section='Giới hạn do người dùng chọn', reason='Không ngoại suy ngoài thời gian dài hạn chung.')
    if accelerated == 'unknown' or not support:
        return dict(months=duration, rule='X', section='Q1E 2.3', reason='Chưa có đánh giá cấp tốc và hồ sơ hỗ trợ đủ để mở ngoại suy.')
    if accelerated == 'no_change' and months >= 6:
        factor, extra = (2., 12.) if storage == 'room' else (1.5, 6.)
        return dict(months=min(factor*duration, duration+extra), rule=f'min({factor:g}X, X+{extra:g})',
                    section='Q1E 2.4.1.2' if storage == 'room' else 'Q1E 2.5.1.1',
                    reason='Áp dụng có điều kiện: phân tích phù hợp và tài liệu hỗ trợ do người dùng xác nhận.')
    if storage == 'refrigerated' and accelerated == 'change':
        return dict(months=duration, rule='X', section='Q1E 2.5.1.2', reason='Có thay đổi đáng kể ở cấp tốc: không ngoại suy cho thuốc bảo quản lạnh.')
    if storage == 'room' and accelerated == 'change' and review.get('intermediate') == 'no_change' and intermediate_months >= 6:
        return dict(months=min(1.5*duration, duration+6), rule='min(1.5X, X+6)', section='Q1E 2.4.2.1',
                    reason='Cấp tốc có thay đổi, trung gian không thay đổi đáng kể; cần phân tích phù hợp và dữ liệu hỗ trợ.')
    return dict(months=duration, rule='X', section='Q1E 2.4.2 / 2.5', reason='Điều kiện ngoại suy chưa đầy đủ hoặc nghiên cứu hỗ trợ có thay đổi đáng kể.')


def analyze(rows, config, review=None):
    review = review or {}
    if not isinstance(rows, list) or not 3 <= len(rows) <= 10000:
        raise AnalysisError('Cần từ 3 đến 10.000 quan sát.')
    direction = config.get('direction', 'decrease')
    transform = config.get('transform', 'none')
    if direction not in ('decrease', 'increase', 'both') or transform not in ('none', 'log'):
        raise AnalysisError('Hướng biến đổi hoặc phép biến đổi dữ liệu không hợp lệ.')
    lower = None if config.get('lower') in (None, '') else number(config['lower'], 'Giới hạn dưới')
    upper = None if config.get('upper') in (None, '') else number(config['upper'], 'Giới hạn trên')
    if direction in ('decrease', 'both') and lower is None:
        raise AnalysisError('Cần giới hạn dưới cho phân tích giảm / hai phía.')
    if direction in ('increase', 'both') and upper is None:
        raise AnalysisError('Cần giới hạn trên cho phân tích tăng / hai phía.')
    if lower is not None and upper is not None and lower >= upper:
        raise AnalysisError('Giới hạn dưới phải nhỏ hơn giới hạn trên.')
    normalized = []
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            raise AnalysisError('Mỗi quan sát phải là một dòng dữ liệu.')
        b = str(row.get('batch', '')).strip()
        if not b or len(b) > 120:
            raise AnalysisError(f'Dòng {i+1}: mã lô trống hoặc quá dài.')
        time = number(row.get('time'), f'Dòng {i+1}, thời gian')
        value = number(row.get('value'), f'Dòng {i+1}, kết quả')
        if not 0 <= time <= 1200:
            raise AnalysisError(f'Dòng {i+1}: thời gian phải từ 0 đến 1.200 tháng.')
        normalized.append(dict(row_id=row.get('row_id', i+1), batch=b, time=time, value=value,
                               attribute=str(row.get('attribute', 'Chỉ tiêu')), condition=str(row.get('condition', 'Dài hạn'))))
    if len({(r['attribute'], r['condition']) for r in normalized}) != 1:
        raise AnalysisError('Mỗi phân tích chỉ được dùng một chỉ tiêu tại một điều kiện bảo quản. Không gộp dữ liệu cấp tốc với dài hạn.')
    batches = sorted({r['batch'] for r in normalized})
    if len(batches) > 30:
        raise AnalysisError('Phiên bản này hỗ trợ tối đa 30 lô trong một phân tích.')
    for b in batches:
        br = [r for r in normalized if r['batch'] == b]
        if len({r['time'] for r in br}) < 3:
            raise AnalysisError(f'Lô {b}: cần ít nhất 3 mốc thời gian khác nhau để đánh giá tuyến tính.')
    y_raw = np.array([r['value'] for r in normalized])
    time = np.array([r['time'] for r in normalized])
    if transform == 'log' and (np.any(y_raw <= 0) or any(v is not None and v <= 0 for v in (lower, upper))):
        raise AnalysisError('Biến đổi ln yêu cầu mọi kết quả và giới hạn đã nhập đều lớn hơn 0.')
    y = np.log(y_raw) if transform == 'log' else y_raw
    scale = float(max(time))
    z = time/scale
    onehot = np.array([[float(r['batch'] == b) for b in batches] for r in normalized])
    models = {
        'pooled': fit_ols(np.column_stack([np.ones(len(rows)), z]), y),
        'common_slope': fit_ols(np.column_stack([onehot, z]), y),
        'separate': fit_ols(np.column_stack([onehot, onehot*z[:, None]]), y),
    }
    slope_test = intercept_test = None
    mode = 'pooled'
    if len(batches) > 1:
        slope_test = nested_test(models['common_slope'], models['separate'])
        if slope_test['p'] is None or slope_test['p'] <= .25:
            mode = 'separate'
        else:
            intercept_test = nested_test(models['pooled'], models['common_slope'])
            mode = 'common_slope' if intercept_test['p'] is None or intercept_test['p'] <= .25 else 'pooled'
    model = models[mode]
    critical = float(stats.t.ppf(.975 if direction == 'both' else .95, model['df']))
    horizon = number(config.get('horizon', max(120., 4*scale)), 'Chân trời tính toán')
    if not scale <= horizon <= 1200:
        raise AnalysisError(f'Chân trời tính toán phải từ {scale:g} đến 1.200 tháng.')

    def design(t, batch):
        at = batches.index(batch)
        hot = np.eye(len(batches))[at]
        if mode == 'pooled':
            return np.array([1., t/scale])
        if mode == 'common_slope':
            return np.r_[hot, t/scale]
        return np.r_[hot, hot*t/scale]

    def point(t, batch):
        v = design(t, batch)
        mean = float(v@model['beta'])
        se = math.sqrt(max(0., float(v@model['covariance']@v)))
        a, c = mean-critical*se, mean+critical*se
        if transform == 'log':
            if max(mean, c) > 700 or min(mean, a) < -700:
                raise AnalysisError('Mô hình ln vượt phạm vi số ở chân trời đã chọn. Hãy giảm chân trời tính toán.')
            return dict(time=t, mean=math.exp(mean), lower=math.exp(a), upper=math.exp(c), se_transformed=se)
        return dict(time=t, mean=mean, lower=a, upper=c, se_transformed=se)

    def crossing(batch, side):
        limit = lower if side == 'lower' else upper
        def margin(t):
            v = design(t, batch)
            mean = float(v@model['beta'])
            se = math.sqrt(max(0., float(v@model['covariance']@v)))
            target = math.log(limit) if transform == 'log' else limit
            return mean-critical*se-target if side == 'lower' else target-mean-critical*se
        # The margin is concave (linear minus a norm): its nonnegative set is an interval.
        # If t=0 is acceptable there can be only one subsequent exit, so bracketing is safe.
        if margin(0) <= 0:
            return 0.
        if margin(horizon) > 0:
            return None
        return float(optimize.brentq(margin, 0, horizon, xtol=1e-10))

    sides = ['lower', 'upper'] if direction == 'both' else ['lower' if direction == 'decrease' else 'upper']
    warnings, blockers = [], []
    series, per_batch = [], []
    grid = np.linspace(0, horizon, 241)
    for b in batches:
        a = design(0,b)
        slope_vector = design(1,b)-a
        slope = float(slope_vector@model['beta'])
        roots = {side: crossing(b,side) for side in sides}
        finite = [r for r in roots.values() if r is not None]
        estimate = min(finite) if finite else None
        br = [r for r in normalized if r['batch']==b]
        per_batch.append(dict(batch=b, n=len(br), max_time=max(r['time'] for r in br),
                              intercept=float(a@model['beta']), slope=slope,
                              intercept_se=math.sqrt(max(0., float(a@model['covariance']@a))),
                              slope_se=math.sqrt(max(0., float(slope_vector@model['covariance']@slope_vector))),
                              crossing=estimate, crossing_by_limit=roots))
        if mode != 'pooled' or not series:
            series.append(dict(batch='Tất cả lô' if mode=='pooled' else b, points=[point(float(t),b) for t in grid]))
        if min(r['time'] for r in br) != 0:
            blockers.append(f'Lô {b} thiếu mốc ban đầu t=0.')
        if (direction == 'decrease' and slope > 0) or (direction == 'increase' and slope < 0):
            blockers.append(f'Lô {b}: hướng hệ số góc trái với hướng biến đổi đã chọn. Cần xem lại giả định hoặc dùng hai phía.')
    roots = [b['crossing'] for b in per_batch if b['crossing'] is not None]
    statistical = min(roots) if roots else None
    duration = min(b['max_time'] for b in per_batch)
    cap = extrapolation_cap(duration, review)
    numerical = min(statistical if statistical is not None else horizon, cap['months'])
    if max(b['max_time'] for b in per_batch) != duration:
        warnings.append('Thời gian theo dõi giữa các lô khác nhau. X dùng mốc cuối ngắn nhất của các lô để giới hạn ngoại suy bảo thủ.')
    if len(batches) < 3:
        blockers.append('Ít hơn 3 lô: kết quả mang tính thăm dò, chưa hỗ trợ đề xuất hạn dùng đăng ký theo phạm vi Q1E.')
    oos = [r['row_id'] for r in normalized if (lower is not None and r['value']<lower) or (upper is not None and r['value']>upper)]
    if oos:
        blockers.append('Có kết quả ngoài giới hạn ở dòng: '+', '.join(map(str,oos[:15]))+'. Cần điều tra OOS trước khi đề xuất.')
    if statistical == 0:
        blockers.append('Giới hạn tin cậy đã chạm/vượt tiêu chuẩn ở t=0. Mô hình không hỗ trợ một khoảng hạn dùng dương.')
    if model['mse'] <= 1e-24:
        blockers.append('Sai số dư gần bằng 0: không đủ thông tin thực nghiệm để diễn giải kiểm định và khoảng tin cậy.')
    fitted, residual = model['fitted'], model['residual']
    leverage = np.einsum('ij,jk,ik->i', model['X'], model['inverse'], model['X'])
    std = residual / np.sqrt(np.maximum(model['mse']*(1-leverage), 1e-30))
    cooks = (std**2)*leverage/(model['k']*np.maximum(1-leverage,1e-15))
    diagnostics = dict(shapiro_p=None, curvature=None, lack_of_fit=None, levene_p=None)
    if 3 <= len(rows) <= 5000 and model['mse'] > 1e-24:
        diagnostics['shapiro_p'] = float(stats.shapiro(residual).pvalue)
        if diagnostics['shapiro_p'] < .05:
            warnings.append('Shapiro–Wilk p<0,05: cần xem xét phân phối phần dư và tính phù hợp của suy luận.')
    groups = defaultdict(list)
    for r, yi in zip(normalized, y):
        groups[(r['batch'],r['time'])].append(float(yi))
    pe = sum(sum((v-np.mean(vals))**2 for v in vals) for vals in groups.values())
    df_pe = len(rows)-len(groups)
    df_lf = len(groups)-model['k']
    if df_pe>0 and df_lf>0:
        lfss=max(0.,model['sse']-pe)
        f=lfss/df_lf/(pe/df_pe) if pe>1e-24 else None
        prob=float(stats.f.sf(f,df_lf,df_pe)) if f is not None else (0. if lfss>1e-20 else None)
        diagnostics['lack_of_fit']=dict(f=f,p=prob,df1=df_lf,df2=df_pe,pure_error_ss=float(pe))
        if prob is not None and prob<.05:
            blockers.append('Kiểm định thiếu phù hợp (lack-of-fit) p<0,05. Không tự động đề xuất từ mô hình này.')
        warnings.append('Có lặp lại cùng lô và thời điểm. Chỉ dùng sai số thuần nếu đây là các quan sát độc lập, không phải phép tiêm lặp của cùng mẫu.')
    quad = onehot*z[:,None]**2 if mode=='separate' else z[:,None]**2
    if len(rows)>model['k']+quad.shape[1]:
        try:
            diagnostics['curvature']=nested_test(model,fit_ols(np.column_stack([model['X'],quad]),y))
            if diagnostics['curvature']['p'] is not None and diagnostics['curvature']['p']<.05:
                blockers.append('Kiểm tra số hạng bậc hai p<0,05: có dấu hiệu cong. Cần mô hình khác hoặc đánh giá chuyên môn.')
        except AnalysisError:
            pass
    batch_res=[residual[np.array([r['batch']==b for r in normalized])] for b in batches]
    if len(batches)>1 and all(len(v)>=3 and np.ptp(v)>1e-12 for v in batch_res):
        diagnostics['levene_p']=float(stats.levene(*batch_res,center='median').pvalue)
        if diagnostics['levene_p']<.05:
            blockers.append('Levene p<0,05: phương sai dư giữa các lô khác nhau. Giả định sai số chung cần đánh giá lại.')
    if any(abs(v)>3 for v in std):
        warnings.append('Có phần dư chuẩn hóa vượt ±3. Không tự động loại điểm; cần đánh giá nguyên nhân và tính toàn vẹn dữ liệu.')
    if any(c>4/len(rows) for c in cooks):
        warnings.append('Có điểm ảnh hưởng lớn theo ngưỡng sàng lọc Cook 4/n. Xem biểu đồ và hồ sơ mẫu.')
    if review.get('long_term_confirmed') is not True:
        blockers.append('Chưa xác nhận dữ liệu đã chọn là nghiên cứu dài hạn tại điều kiện bảo quản dự kiến.')
    if review.get('design_confirmed') is not True:
        blockers.append('Chưa xác nhận cùng sản phẩm, hàm lượng, bao bì và quan sát độc lập. Thiết kế đa yếu tố cần phân tích riêng.')
    if review.get('model_reviewed') is not True:
        blockers.append('Chưa xác nhận đã đánh giá phần dư, tính tuyến tính và độ phù hợp của phương pháp phân tích.')
    if review.get('other_attributes_reviewed') is not True:
        blockers.append('Chưa xem xét các chỉ tiêu chất lượng khác. Hạn dùng sản phẩm không chỉ dựa trên một chỉ tiêu.')
    if len(str(review.get('reviewer','')).strip())<2 or len(str(review.get('justification','')).strip())<15:
        blockers.append('Cần tên người đánh giá và giải trình khoa học trước khi tạo ứng viên đề xuất.')
    if not str(review.get('product','')).strip():
        blockers.append('Cần định danh sản phẩm / nghiên cứu.')
    if transform=='log':
        warnings.append('Hồi quy và giới hạn tin cậy trên thang ln. Đường đổi ngược là trung bình hình học, không phải trung bình số học của đáp ứng gốc.')
    if review.get('allow_extrapolation') and cap['months']>duration:
        warnings.append('Ngoại suy cần được xác nhận bằng dữ liệu dài hạn bổ sung. Phần mềm không kiểm chứng thay tài liệu hỗ trợ đã khai báo.')
    if cap['months']>horizon:
        warnings.append('Chân trời tìm giao điểm ngắn hơn giới hạn ngoại suy. Kết quả chỉ được hỗ trợ đến chân trời đã tính.')
    qq = stats.probplot(residual,dist='norm',fit=False)
    residual_rows=[]
    for i,r in enumerate(normalized):
        residual_rows.append(dict(**r,fitted_transformed=float(fitted[i]),residual=float(residual[i]),
                                  standardized=float(std[i]),leverage=float(leverage[i]),cooks_distance=float(cooks[i])))
    sst=float(np.sum((y-np.mean(y))**2))
    r2=1-model['sse']/sst if sst>1e-24 else None
    return dict(version=VERSION, n=len(rows), batches=batches, model=mode, model_name=MODEL_NAMES[mode],
                alpha_pooling=.25, confidence=.95, confidence_sides=2 if direction=='both' else 1,
                confidence_target='Fitted mean on analysis scale; not an individual prediction or tolerance interval',
                transform=transform, direction=direction, lower=lower, upper=upper,
                slope_test=slope_test, intercept_test=intercept_test, df_error=model['df'],
                sse=model['sse'], mse=model['mse'], rmse=math.sqrt(model['mse']), r_squared=r2,
                coefficients=per_batch, series=series, residuals=residual_rows,
                qq=[dict(theoretical=float(x),residual=float(y)) for x,y in zip(*qq)],
                diagnostics=diagnostics, statistical_months=statistical,
                statistical_status='crossing' if statistical is not None else 'beyond_search',
                search_horizon=horizon, observed_common_months=duration, observed_max_months=scale,
                extrapolation=cap, conditional_limit_months=numerical,
                candidate_months=math.floor(numerical) if not blockers else None,
                status='candidate_for_review' if not blockers else 'review_required',
                blockers=blockers, warnings=warnings, config=config, review=review)
