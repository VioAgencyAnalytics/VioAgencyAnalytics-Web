"""Financial precision and transparent report meaning, without provider reads."""
import pytest

from app.customer_data import display
from app.customer_report_view import build
from test_customer_auth import stack
from test_customer_data import prepare, report


@pytest.mark.parametrize('value,unit,currency,expected',[
    (.25,'number','VND','0,25'), (6.5,'number','VND','6,5'),
    (.125,'number','VND','0,12'), (.00125,'percent','VND','0,12%'),
    ('9007199254740993.25','currency','USD','9.007.199.254.740.993,25 USD'),
    ('0.000001','currency','USD','<0,01 USD'), ('0.4','currency','VND','<1 VND'),
    (.0000001,'percent',None,'<0,01%'), (.000001,'number',None,'<0,01'),
    (0,'percent',None,'0%'), ('0.00','currency','USD','0,00 USD'),
    (None,'count',None,'—'), (True,'number',None,'—'),
])
def test_report_precision_preserves_fractions_and_missingness(value,unit,currency,expected):
    assert display(value,unit,currency)==expected


def test_report_glossary_and_observation_dates_do_not_invent_period_comparisons():
    value=report();value['source']='google_ads'
    value['metrics']=[{'key':'conversions','label':'Chuyển đổi','value':.25,'aggregation':'sum','grain':'day'}]
    view=build(value)
    assert 'phần thập phân' in view['definitions'][0]['description']
    assert view['latest_observation']=='01/10/2026'
    assert view['observed_days']==1 and view['available']==1
    assert 'comparison' not in view and 'growth' not in view


def test_report_renders_glossary_reference_and_safe_small_value_label(stack):
    client,_,state,_=stack;prepare(state)
    value=report();value['metrics'][1]['value']=.000001
    state['source_data']=value
    response=client.get('/workspace/reports/data?source=ga4')
    assert response.status_code==200,response.text
    assert 'Định nghĩa KPI' in response.text and 'Bản lưu' in response.text
    assert '&lt;0,01' in response.text
    assert '<script>inert</script>' not in response.text
