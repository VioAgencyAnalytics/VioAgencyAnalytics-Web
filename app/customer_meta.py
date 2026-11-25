"""Customer Meta presentation reads snapshots only; no provider transport."""
import re
import math
from urllib.parse import urlencode

from fastapi.responses import JSONResponse,RedirectResponse
from app.customer_auth import (BINDING,HEADERS,CustomerError,backend,browser_binding,
    configuration,error_response,set_cookie)
from app.routes.pages import templates
import secrets
from app.customer_content_view import build_view, amount, day
from app.customer_data import display


def query(request, *, report=False):
    from app.customer_report_controls import query as report_query
    return report_query(request, include_template=report)


def project(payload,workspace_id):
    if (not isinstance(payload,dict) or not isinstance(payload.get('scope'),dict)
            or payload.get('schema_version')!=1 or payload.get('source')!='facebook_content'
            or payload.get('scope',{}).get('workspace_id')!=workspace_id
            or payload.get('state') not in ('no_client','not_connected','select_asset','syncing','sync_error','empty','ready','future_period')):
        raise CustomerError(502,'Dữ liệu nguồn trả về không đúng phạm vi.','snapshot_scope')
    result={key:payload.get(key) for key in ('schema_version','source','scope','state')}
    for key,fields in {
        'client':('id','name'),'asset':('id','name','external_id'),'connection':('id','version','status'),
        'snapshot':('id','created_at','start_date','end_date','fetched_at','timezone'),
        'latest_sync':('id','status','start_date','end_date','created_at','finished_at','error_code'),
    }.items():
        value=payload.get(key)
        result[key]={field:value.get(field) for field in fields} if isinstance(value,dict) else None
    result['scope']={key:payload['scope'].get(key) for key in ('workspace_id','client_id')}
    for key,fields in {
        'periods':('id','created_at','start_date','end_date'),
        'metrics':('key','label','unit','value','status','reason','coverage','grain','aggregation'),
        'daily_posts':('date','posts_published'),
        'posts':('post_id','date','title','message','permalink_url','format','reactions_lifetime','comments_lifetime','shares_lifetime','post_media_view_lifetime','post_total_media_view_unique_lifetime'),
        'insights':('metric','label','period','aggregation','value','report_status','reason','coverage','values'),
    }.items():
        values=payload.get(key,[])
        if not isinstance(values,list) or len(values)>10000 or any(not isinstance(row,dict) for row in values):
            raise CustomerError(502,'Cấu trúc snapshot không hợp lệ.','snapshot_invalid')
        result[key]=[{field:row.get(field) for field in fields} for row in values]
    for metric in result['metrics']+result['insights']:
        coverage=metric.get('coverage')
        metric['coverage']={key:coverage.get(key) for key in ('available','expected','unit')} if isinstance(coverage,dict) else None
    for metric in result['insights']:
        values=metric.get('values')
        if not isinstance(values,list) or len(values)>200:
            raise CustomerError(502,'Chuỗi Insights không hợp lệ.','snapshot_invalid')
        metric['values']=[{key:point.get(key) for key in ('value','end_time')} for point in values if isinstance(point,dict)]
    result['published']=False;result['comparison_available']=False
    if (result['client']['id'] if result['client'] else None)!=result['scope']['client_id']:
        raise CustomerError(502,'Khách hàng của snapshot không hợp lệ.','snapshot_scope')
    if result['state']=='ready' and not all(result[key] for key in ('client','asset','snapshot')):
        raise CustomerError(502,'Snapshot chưa đủ thông tin phạm vi.','snapshot_scope')
    numeric=lambda value:value is None or (type(value) in (int,float) and math.isfinite(value))
    if (any(not numeric(row.get('value')) for row in result['metrics']+result['insights'])
            or any(type(row.get('posts_published')) is not int or row['posts_published']<0 for row in result['daily_posts'])
            or any(not numeric(point.get('value')) for metric in result['insights'] for point in metric['values'])):
        raise CustomerError(502,'Chỉ số snapshot không hợp lệ.','snapshot_invalid')
    for post in result['posts']:
        if (not isinstance(post.get('post_id'),str) or not isinstance(post.get('date'),str)
                or any(post.get(key) is not None and not isinstance(post[key],str)
                       for key in ('title','message','permalink_url','format'))
                or any(not numeric(post.get(key)) or (post.get(key) is not None and post[key] < 0)
                       for key in ('reactions_lifetime','comments_lifetime','shares_lifetime',
                                   'post_media_view_lifetime','post_total_media_view_unique_lifetime'))):
            raise CustomerError(502,'Chỉ số bài viết không hợp lệ.','snapshot_invalid')
    from app.customer_report_controls import project as controls, CONTENT_GOALS
    result.update(controls(payload,CONTENT_GOALS,result['metrics'],result['asset'],result['snapshot']))
    return result


async def read(request,workspace_id):
    try:
        if not re.fullmatch(r'[a-f0-9]{32}',workspace_id):
            raise CustomerError(404,'Không tìm thấy Workspace.')
        payload=await backend(request,'GET','/workspaces/'+workspace_id+'/channels/facebook-content'+query(request))
        result=project(payload,workspace_id)
        from app.customer_comparisons import assert_period, attach
        assert_period(result,{key:request.query_params[key] for key in ('start','end') if key in request.query_params})
        await attach(request,result,'/workspaces/'+workspace_id+'/channels/facebook-content',project)
        return JSONResponse(result,headers=HEADERS)
    except CustomerError as error:
        return error_response(error)


async def page(request, report=False):
    try:
        settings=configuration(request)
        try:
            account=await backend(request,'GET','/session')
        except CustomerError as error:
            if error.status==401:
                return RedirectResponse('/workspace/login',303,headers=HEADERS)
            raise
        if not account.get('workspace'):
            return RedirectResponse('/workspace/onboarding',303,headers=HEADERS)
        workspace_id=account['workspace']['id']
        details=await backend(request,'GET','/workspaces/'+workspace_id)
        suffix = query(request, report=report)
        from app.customer_report_presets import get_preset
        from app.customer_report_styles import style_context
        preset = get_preset('facebook_content', request.query_params.get('template')) if report else None
        styling = style_context(request.query_params.get('style'), request.query_params.get('palette'), preset,
                                request.query_params.get('order'), request.query_params.get('hidden')) if report else {}
        payload=project(await backend(request,'GET','/workspaces/'+workspace_id+'/channels/facebook-content'+suffix),workspace_id)
        selected=details.get('selected_client')
        if details.get('workspace',{}).get('id')!=workspace_id or (selected['id'] if selected else None)!=payload['scope']['client_id']:
            raise CustomerError(409,'Khách hàng đã thay đổi. Vui lòng tải lại trang.','client_changed')
        from app.customer_comparisons import assert_period, attach
        assert_period(payload,{key:request.query_params[key] for key in ('start','end') if key in request.query_params})
        await attach(request,payload,'/workspaces/'+workspace_id+'/channels/facebook-content',project)
        metrics={metric['key']:metric for metric in payload['metrics']}
        view = build_view(payload, details)
        review = None
        focus = None
        if report:
            from app.customer_report_layouts import build_layout
            from app.customer_report_notes import attach as attach_notes, platform_reference
            from app.report_commentary import facebook_content
            layout = build_layout(payload)
            if preset:
                from app.customer_report_focus import focus_report
                focus, sections = focus_report(preset, payload, layout, view)
            else:
                sections = facebook_content(payload, view, layout)
            review = await attach_notes(request, settings, payload['scope'], platform_reference(payload, 'facebook_content', preset), sections)
        response=templates.TemplateResponse(request=request,name='customer/live/facebook-content-report.html' if report else 'customer/live/facebook-content.html',
            context={'title':'Báo cáo Facebook Content' if report else 'Phân tích Facebook Content',
                     'customer_page':'reports' if report else 'channels','customer_live':True,
                     'customer_meta_live':True,'customer_meta_report':report,
                     'account':account,'details':details,'content':payload,'metrics':metrics,
                     'view':view,'fc_amount':amount,'fc_day':day,'display':display,'report_review':review,
                     'report_preset': preset, 'report_focus': focus, **styling},headers=HEADERS)
        if not browser_binding(request):
            set_cookie(response,BINDING,secrets.token_urlsafe(48),settings)
        return response
    except CustomerError as error:
        return templates.TemplateResponse(request=request,name='customer/live/error.html',
            context={'title':'Facebook Content','customer_page':'error','customer_live':True,'message':error.message},
            status_code=error.status,headers=HEADERS)
