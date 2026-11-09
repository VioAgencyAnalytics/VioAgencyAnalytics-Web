"""Read-only display math never fabricates totals from incomplete or unique data."""
import copy
import pytest

from app.customer_content_view import amount, build_view, chart, post_url


def content():
    return {'asset':{'external_id':'1234'}, 'snapshot':{'start_date':'2026-10-01','end_date':'2026-10-02'},
        'metrics':[{'key':'posts_published','value':2},{'key':'reactions_lifetime','value':0},
                   {'key':'comments_lifetime','value':1},{'key':'shares_lifetime','value':None,
                    'coverage':{'available':1,'expected':2}}],
        'posts':[{'post_id':'1234_5678','date':'2026-10-01','message':'Nội dung <script>inert</script>',
                  'format':'photo','post_media_view_lifetime':0},
                 {'post_id':'1234_5679','date':'2026-10-02','message':'Bài mới','format':'video','post_media_view_lifetime':4}],
        'daily_posts':[{'date':'2026-10-01','posts_published':1},{'date':'2026-10-02','posts_published':1}],
        'insights':[{'metric':'page_follows','value':None,'report_status':'available',
                     'values':[{'end_time':'2026-10-02T08:00:00+00:00','value':100},
                               {'end_time':'2026-10-03T08:00:00+00:00','value':101}]},
                    {'metric':'page_total_media_view_unique','value':None,'report_status':'available',
                     'values':[{'end_time':'2026-10-02T08:00:00+00:00','value':40},
                               {'end_time':'2026-10-03T08:00:00+00:00','value':42}]},
                    {'metric':'page_media_view','value':None,'report_status':'period_boundary_mismatch',
                     'values':[{'end_time':'2026-10-02T08:00:00+00:00','value':50},
                               {'end_time':'2026-10-03T08:00:00+00:00','value':60}]}]}


def test_lifetime_views_sum_requires_every_post_and_preserves_observed_zero():
    data=content();before=copy.deepcopy(data)
    view=build_view(data,{})
    assert view['cards'][1]['value']==4
    assert view['cards'][2]['value']==0 and amount(0)=='0'
    assert data==before and view['shares']['value'] is None
    data['posts'][0]['post_media_view_lifetime']=None
    assert build_view(data,{})['cards'][1]['value'] is None
    assert amount(None)=='Chưa có số liệu'


def test_daily_unique_and_follower_stock_are_not_summed_or_changed_into_new_followers():
    view=build_view(content(),{})
    assert [m['value'] for m in view['observations']]==[101,42]
    assert view['observations'][0]['date']=='2026-10-03T08:00:00+00:00'
    assert view['cards'][1]['value']!=110  # Page daily views are a different scope.
    assert any('Mốc ngày Meta' in issue['title'] for issue in view['issues'])
    meta=next(c for c in view['charts'] if c['key']=='page_media_view')
    assert [p['value'] for p in meta['points']]==[50,60] and meta['meta']


def test_links_use_exact_page_post_pair_even_if_old_permalink_was_dropped():
    post={'post_id':'1234_5678','permalink_url':None}
    assert post_url(post,'1234')=='https://www.facebook.com/permalink.php?story_fbid=5678&id=1234'
    post['permalink_url']='https://evil.test/redirect?token=SYNTHETIC'
    assert 'evil.test' not in post_url(post,'1234')
    assert post_url(post,'9999') is None


@pytest.mark.parametrize('post_id',['1234_bad','1234_5678/../x','javascript:alert(1)','9999_5678',None,1234])
def test_malformed_or_foreign_post_ids_cannot_create_a_link(post_id):
    assert post_url({'post_id':post_id},'1234') is None


def test_chart_renders_real_nonzero_columns_and_does_not_turn_missing_into_zero():
    view=chart('test','Test',[{'date':'2026-10-01','value':0},{'date':'2026-10-02','value':2},
                              {'date':'2026-10-03','value':None}],'Test')
    assert view['points'][0]['height']==0 and view['points'][1]['height']>0
    assert view['points'][2]['value'] is None and view['coverage']==2
    assert len({t['label'] for t in view['ticks']})==4


def test_single_business_brand_is_simplified_without_affecting_agency_scope():
    details={'workspace':{'kind':'business'},'clients':[{'id':'a'}]}
    assert build_view(content(),details)['single_brand']
    details['workspace']['kind']='agency'
    assert not build_view(content(),details)['single_brand']
