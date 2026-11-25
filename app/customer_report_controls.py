"""Allowlisted reporting calendar and KPI-plan DTOs; no provider access."""
from datetime import date
from decimal import Decimal, localcontext
import re
from urllib.parse import urlencode

from app.customer_auth import CustomerError
from app.customer_metric_semantics import goal_assessment


TARGET_STATUSES = {'not_set','no_data','currency_mismatch','met','below_target','within_limit','over_limit'}
CONTENT_GOALS = [{'key': key, 'label': label, 'unit': 'count', 'grain': grain} for key, label, grain in (
    ('posts_published', 'Bài đăng trong kỳ', 'day'), ('post_views_lifetime', 'Lượt xem tích lũy các bài', 'snapshot'),
    ('reactions_lifetime', 'Cảm xúc', 'snapshot'), ('comments_lifetime', 'Bình luận', 'snapshot'),
    ('shares_lifetime', 'Chia sẻ', 'snapshot'),
)]


def invalid():
    raise CustomerError(502,'Dữ liệu kỳ báo cáo hoặc mục tiêu không hợp lệ.','snapshot_invalid')


def stamp(value):
    try:
        if not isinstance(value,str) or date.fromisoformat(value).isoformat()!=value:
            raise ValueError()
        return value
    except ValueError:
        invalid()


def decimal(value, optional=True):
    if value is None and optional:
        return None
    if not isinstance(value,str) or len(value)>180 or not re.fullmatch(r'(?:0|[1-9]\d*)(?:\.\d+)?',value):
        invalid()
    return value


def query(request, *, include_source=False, include_template=False):
    from app.customer_comparisons import PARAMETERS, parameters
    allowed={'snapshot','start','end'} | PARAMETERS | ({'source'} if include_source else set())
    if include_template:
        allowed.update(('template', 'style', 'palette', 'order', 'hidden'))
    values=request.query_params
    if set(values)-allowed or any(len(values.getlist(key))!=1 for key in values):
        raise CustomerError(422,'Bộ lọc báo cáo không hợp lệ.','snapshot_input')
    parameters(values)
    snapshot=values.get('snapshot');start,end=values.get('start'),values.get('end')
    if snapshot is not None:
        if not re.fullmatch(r'[a-f0-9]{32}',snapshot):
            raise CustomerError(422,'Mã snapshot không hợp lệ.','snapshot_input')
        if start is not None or end is not None:
            raise CustomerError(422,'Chọn bản lưu hoặc khoảng ngày, không dùng đồng thời.','report_period_input')
        return '?'+urlencode({'snapshot':snapshot})
    if start is not None or end is not None:
        try:
            first,last=date.fromisoformat(start),date.fromisoformat(end)
            if first.isoformat()!=start or last.isoformat()!=end or first>last or (last-first).days>89:
                raise ValueError()
        except (ValueError,TypeError):
            raise CustomerError(422,'Chọn kỳ hợp lệ, tối đa 90 ngày.','report_period_input') from None
        return '?'+urlencode({'start':start,'end':end})
    return ''


def project(payload, specs, actuals, asset, snapshot):
    cal=payload.get('calendar')
    if cal is not None:
        if not isinstance(cal,dict) or cal.get('max_days')!=90 or not isinstance(cal.get('timezone'),str) or len(cal['timezone'])>100:
            invalid()
        cal={key:stamp(cal.get(key)) for key in ('today','latest_closed_date')} | {'timezone':cal['timezone'],'max_days':90}
    period=payload.get('period')
    if period is not None:
        if not isinstance(period,dict) or type(period.get('is_open')) is not bool or period.get('mode') not in ('latest','snapshot','custom'):
            invalid()
        first,last=stamp(period.get('start')),stamp(period.get('end'))
        if first>last or (date.fromisoformat(last)-date.fromisoformat(first)).days>89:
            invalid()
        data_start,data_end=period.get('data_start'),period.get('data_end')
        if (data_start is None)!=(data_end is None):
            invalid()
        if data_start is not None:
            stamp(data_start);stamp(data_end)
            if data_start!=first or data_end<data_start or data_end>last or cal and data_end>cal['latest_closed_date']:
                invalid()
        if cal and (period['is_open']!=(last>cal['latest_closed_date'])
                    or data_end!=(min(last,cal['latest_closed_date']) if first<=cal['latest_closed_date'] else None)):
            invalid()
        period={'start':first,'end':last,'data_start':data_start,'data_end':data_end,'is_open':period['is_open'],'mode':period['mode']}
        if snapshot and (snapshot.get('start_date')!=data_start or snapshot.get('end_date')!=data_end):
            invalid()
    elif snapshot:
        period={'start':snapshot['start_date'],'end':snapshot['end_date'],'data_start':snapshot['start_date'],
                'data_end':snapshot['end_date'],'is_open':False,'mode':'snapshot'}
    targets=payload.get('targets')
    safe={'asset_id':asset['id'] if asset else None,'start':period['start'] if period else None,'end':period['end'] if period else None,
          'can_manage':False,'updated_at':None,'items':[]}
    if targets is not None:
        if (not isinstance(targets,dict) or targets.get('asset_id')!=safe['asset_id'] or not period
                or targets.get('start')!=period['start'] or targets.get('end')!=period['end']
                or not isinstance(targets.get('items'),list) or len(targets['items'])>20):
            invalid()
        safe['can_manage']=targets.get('can_manage') is True and asset is not None
        updated=targets.get('updated_at')
        if updated is not None and (not isinstance(updated,str) or len(updated)>50):
            invalid()
        safe['updated_at']=updated
        known={item['key']:item for item in specs};measured={item['key']:item for item in actuals};seen=set()
        for item in targets['items']:
            if not isinstance(item,dict) or not isinstance(item.get('key'),str) or item['key'] not in known or item['key'] in seen:
                invalid()
            key=item['key'];seen.add(key);spec=known[key]
            if (item.get('unit')!=spec['unit'] or item.get('direction') not in ('at_least','at_most')
                    or not isinstance(item.get('status'),str) or item['status'] not in TARGET_STATUSES or item.get('relation') not in (None,'above','below','equal')
                    or type(item.get('version')) is not int or item['version']<0):
                invalid()
            value=decimal(item.get('value'));input_value=decimal(item.get('input_value'))
            currency=item.get('currency')
            if currency is not None and (not isinstance(currency,str) or not re.fullmatch('[A-Z]{3}',currency)):
                invalid()
            if value is not None and spec['unit']=='currency' and currency is None:
                invalid()
            if value is not None and spec['unit']=='percent' and Decimal(value)>1:
                invalid()
            with localcontext() as context:
                context.prec=100
                if ((value is None)!=(input_value is None) or value is not None
                        and Decimal(value)*(100 if spec['unit']=='percent' else 1)!=Decimal(input_value)):
                    invalid()
            metric=measured.get(key,{})
            actual=metric.get('value')
            if item.get('actual')!=actual or type(item.get('actual')) is bool:
                invalid()
            safe['items'].append({'key':key,'label':spec['label'],'unit':spec['unit'],'grain':spec.get('grain'),
                'direction':item['direction'],'version':item['version'],'status':item['status'],'value':value,
                'input_value':input_value,'currency':currency,'actual':actual,'actual_currency':metric.get('currency'),
                'ratio':decimal(item.get('ratio')),
                'difference':decimal(item.get('difference')),'relation':item.get('relation'),
                'assessment':goal_assessment(item['status'], period.get('is_open', False))})
    permissions=payload.get('permissions',{})
    if not isinstance(permissions,dict):
        invalid()
    return {'calendar':cal,'period':period,'targets':safe,'permissions':{'sync':permissions.get('sync') is True}}
