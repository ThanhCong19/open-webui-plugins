"""Test kiểm ngoặc <script> của inline-visualizer (Fpt-Feature: viz-script-bracket-check).

    forks/open-webui/backend/.venv/bin/python -m pytest forks/open-webui-plugins/inline-visualizer -q

Ba ca lỗi dựng theo đúng cấu trúc ngoặc của ba biểu đồ trống gặp khi kiểm thử (22/10, 28/10), số
liệu là số giả.
"""

import asyncio
import importlib.util
from pathlib import Path

import pytest

_spec = importlib.util.spec_from_file_location("viz_tool", Path(__file__).with_name("tool.py"))
viz = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(viz)

CDN = '<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>'

# Thừa một "}" ở cuối options rồi mới tới ");" — new Chart(...) không bao giờ chạy.
EXTRA_BRACE_AFTER_OPTIONS = """
<canvas id="a"></canvas>
<script>
function makeBar(id, labels, values) {
  new Chart(document.getElementById(id), {
    type:'bar',
    data:{labels,datasets:[{data:values}]},
    options:{responsive:true,plugins:{legend:{display:false}},scales:{y:{ticks:{callback:v=>v+'%'}}}}
    }
  });
}
makeBar('a',['X','Y'],[1.5,2.5]);
</script>"""

# Thừa một "}" sau plugins: options đóng sớm, scales rơi ra ngoài.
EXTRA_BRACE_AFTER_PLUGINS = """
<canvas id="b"></canvas>
<script>
new Chart(document.getElementById('b'),{
  type:'bar',
  data:{labels:['X'],datasets:[{data:[3]}]},
  options:{responsive:true,
    plugins:{legend:{position:'bottom'},tooltip:{callbacks:{label:c=>c.parsed.y+'%'}}}}},
    scales:{y:{beginAtZero:true,max:5}}
  }
});
</script>"""

# Thiếu "}" đóng đối tượng trả về: cả hàm không đóng.
MISSING_BRACE_IN_RETURN = """
<script>
function datasetFor(key){
  const sorted = rows.slice().sort((a,b)=>b[key]-a[key]);
  return {sorted, data:{labels:sorted.map(x=>x.g), values:sorted.map(x=>x[key])};
}
</script>"""

VALID = f"""
<div id="c" style="height:200px"><canvas id="cv"></canvas></div>
{CDN}
<script>
// ngoặc trong comment không tính: ( [ {{
/* cả comment khối: }} ) ] */
const re = /[(]+\\/x/g, half = total / 2 / 1;
const s = "chuỗi có ngoặc ({{[", t = 'và ) ] }}';
const label = `Tổng ${{fmt({{a: 1, b: [2, 3]}})}} triệu — ${{`lồng ${{x}}`}}`;
if (re.test(s)) {{ console.log(label, t, half); }}
new Chart(document.getElementById('cv'), {{
  type: 'line',
  data: {{ labels: ['T1', 'T2'], datasets: [{{ data: [1, 2] }}] }},
  options: {{ plugins: {{ legend: {{ display: false }} }} }}
}});
</script>"""


@pytest.mark.parametrize("html, where", [
    (EXTRA_BRACE_AFTER_OPTIONS, "line 8: found '}' but the '(' opened on line 3"),
    (EXTRA_BRACE_AFTER_PLUGINS, "found '}' but the '(' opened on line 2"),
    (MISSING_BRACE_IN_RETURN, "'{' opened on line 2 is never closed"),
])
def test_unbalanced_scripts_are_reported(html, where):
    errors = viz._script_bracket_errors(html)
    assert len(errors) == 1 and where in errors[0], errors


def test_valid_script_with_strings_regex_template_comments_passes():
    assert viz._script_bracket_errors(VALID) == []


def test_external_and_non_js_scripts_are_skipped():
    html = CDN + '<script type="application/json">{"a": [1, 2</script><svg><g></g></svg>'
    assert viz._script_bracket_errors(html) == []


def test_unclosed_string_and_template_are_reported():
    assert "string opened on line 1" in viz._script_bracket_errors("<script>const a = 'x;</script>")[0]
    assert "template literal" in viz._script_bracket_errors("<script>const a = `x ${y}</script>")[0]


def test_render_refuses_broken_script_and_embeds_valid_one():
    tool = viz.Tools()
    refused = asyncio.run(tool.render_visualization(EXTRA_BRACE_AFTER_OPTIONS, title="Doanh thu"))
    assert isinstance(refused, str)
    assert "NOT rendered" in refused and "call render_visualization again" in refused
    response, context = asyncio.run(tool.render_visualization(VALID, title="Doanh thu"))
    assert "now rendered" in context
    assert b"new Chart" in response.body
