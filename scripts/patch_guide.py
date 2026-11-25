# -*- coding: utf-8 -*-
"""在首页顶部加「上手说明书」：四步 + 箭头指向 + 三栏图例，鲜艳配色。"""
import io
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = os.path.join(ROOT, "app", "index.html")
s = io.open(P, encoding="utf-8", newline=None).read()
assert 'id="guide"' not in s, "说明书已经存在"

CSS = '''
  /* ===== 上手说明书（首页顶部） ===== */
  #guide{margin:12px 12px 0;border:2px solid #FFC069;border-radius:12px;overflow:hidden;
    background:linear-gradient(105deg,#FFF6E5 0%,#FFEEDC 38%,#EAF7FF 100%);
    box-shadow:0 2px 10px rgba(255,122,69,.12)}
  .gd-top{display:flex;align-items:center;gap:10px;padding:10px 14px 8px}
  .gd-badge{background:linear-gradient(135deg,#FF7A45,#F5222D);color:#fff;font-size:11.5px;
    font-weight:700;letter-spacing:1px;padding:4px 10px;border-radius:20px;flex:none;
    box-shadow:0 2px 6px rgba(245,34,45,.25)}
  .gd-top b{font-size:14px;color:#7A3E00;letter-spacing:.5px}
  .gd-sub{font-size:11.5px;color:#9A5C1E}
  .gd-btn{margin-left:auto;flex:none;border:1px solid #FFB066;background:#fff;color:#C2410C;
    font-size:11.5px;padding:3px 12px;border-radius:14px;cursor:pointer}
  .gd-btn:hover{background:#FFF3E6}

  .gd-steps{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;padding:2px 14px 6px}
  .gd-step{position:relative;background:#fff;border:1px solid #FFE0B8;border-radius:10px;
    padding:10px 12px 8px;transition:transform .16s,box-shadow .16s}
  .gd-step:hover{transform:translateY(-2px);box-shadow:0 6px 16px rgba(255,122,69,.16)}
  .gd-no{position:absolute;left:-1px;top:-1px;width:26px;height:26px;border-radius:9px 0 12px 0;
    color:#fff;font-size:13px;font-weight:700;display:flex;align-items:center;justify-content:center}
  .gd-step.s1{border-color:#FFC9A8}.gd-step.s1 .gd-no{background:linear-gradient(135deg,#FF7A45,#FA541C)}
  .gd-step.s2{border-color:#FFE08A}.gd-step.s2 .gd-no{background:linear-gradient(135deg,#FAAD14,#D48806)}
  .gd-step.s3{border-color:#A9E7E3}.gd-step.s3 .gd-no{background:linear-gradient(135deg,#13C2C2,#08979C)}
  .gd-step.s4{border-color:#B7D4FB}.gd-step.s4 .gd-no{background:linear-gradient(135deg,#2563EB,#1D4ED8)}
  .gd-t{margin:4px 0 0 34px;font-size:13px;font-weight:700;color:#1F2937}
  .gd-d{font-size:11.5px;color:#6B7280;line-height:1.55;margin-top:3px;min-height:34px}
  .gd-arrow{display:flex;align-items:center;gap:6px;margin-top:6px;padding-top:6px;
    border-top:1px dashed #FFD8B0}
  .gd-arrow i{font-style:normal;font-size:15px;line-height:1;color:#FF7A45;font-weight:700}
  .gd-arrow em{font-style:normal;font-size:10.5px;letter-spacing:.5px;color:#C2410C;
    background:#FFF3E6;border-radius:10px;padding:2px 8px}
  .gd-step.s2 .gd-arrow i{color:#D48806}.gd-step.s2 .gd-arrow em{color:#8A5A00;background:#FFF8E1}
  .gd-step.s3 .gd-arrow i{color:#08979C}.gd-step.s3 .gd-arrow em{color:#006D75;background:#E6FFFB}
  .gd-step.s4 .gd-arrow i{color:#1D4ED8}.gd-step.s4 .gd-arrow em{color:#1E3A8A;background:#E8F1FF}

  .gd-legend{display:grid;grid-template-columns:330px 268px 1fr;gap:12px;
    padding:0 14px 10px;align-items:stretch}
  .lg{border-radius:8px;padding:5px 10px;font-size:11.5px;font-weight:600;display:flex;
    align-items:baseline;gap:8px;border:1px dashed}
  .lg span{font-weight:400;font-size:10.5px;opacity:.85}
  .lg.l1{background:#FEF3C7;border-color:#FBBF24;color:#92400E}
  .lg.l2{background:#EDE9FE;border-color:#A78BFA;color:#5B21B6}
  .lg.l3{background:#DCFCE7;border-color:#4ADE80;color:#166534}
  .lg b{font-variant-numeric:tabular-nums;opacity:.7}
'''

HTML = '''
<section id="guide">
  <div class="gd-top">
    <span class="gd-badge">上手说明书</span>
    <b>四步填完一整套单据</b>
    <span class="gd-sub">先填源头数据 → 中间看流程 → 右边取单据；改一个数字，后面全跟着变</span>
    <button class="gd-btn" id="gdToggle">收起</button>
  </div>

  <div id="gdBody">
    <div class="gd-steps">
      <div class="gd-step s1">
        <div class="gd-no">1</div>
        <div class="gd-t">填公司档案</div>
        <div class="gd-d">我方 / 对方各一键，23 个栏位与 POCIB 注册页一一对应，可存为常用。</div>
        <div class="gd-arrow"><i>↓</i><em>指向 左栏 · 公司档案</em></div>
      </div>
      <div class="gd-step s2">
        <div class="gd-no">2</div>
        <div class="gd-t">定术语与结算</div>
        <div class="gd-d">贸易术语 × 结算方式，直接决定每一步要交哪张单、由谁交。</div>
        <div class="gd-arrow"><i>↓</i><em>指向 左栏 · 贸易与结算</em></div>
      </div>
      <div class="gd-step s3">
        <div class="gd-no">3</div>
        <div class="gd-t">填商品与数量</div>
        <div class="gd-d">选预置商品或自填 HS 编码；名称、箱装量、毛净重、体积自动带出。</div>
        <div class="gd-arrow"><i>↓</i><em>指向 左栏 · 商品 / 数量单价</em></div>
      </div>
      <div class="gd-step s4">
        <div class="gd-no">4</div>
        <div class="gd-t">点环节，取单据</div>
        <div class="gd-d">点中间任一步，右边列出该单据每个栏位的值与来源，点值即复制。</div>
        <div class="gd-arrow"><i>↓</i><em>指向 中栏 → 右栏</em></div>
      </div>
    </div>

    <div class="gd-legend">
      <div class="lg l1"><b>①</b>交易剖面<span>数据只在这里填一次</span></div>
      <div class="lg l2"><b>②</b>履约流程<span>21 步，点一步看单据</span></div>
      <div class="lg l3"><b>③</b>派生值 · 一致性校验 · 单据字段<span>自动算，点值复制</span></div>
    </div>
  </div>
</section>
'''

JS = '''
<script>
(function(){
  const btn=document.getElementById("gdToggle"), body=document.getElementById("gdBody");
  if(!btn||!body) return;
  const KEY="pocib_guide_hidden";
  const apply=(hidden)=>{
    body.style.display=hidden?"none":"";
    btn.textContent=hidden?"展开说明":"收起";
    try{ localStorage.setItem(KEY,hidden?"1":"0"); }catch(e){}
  };
  btn.addEventListener("click",()=>apply(body.style.display!=="none"));
  try{ if(localStorage.getItem(KEY)==="1") apply(true); }catch(e){}
})();
</script>
'''

# CSS 插到 </style> 前（第一个，即主样式表）
i = s.find("</style>")
assert i > 0
s = s[:i] + CSS + s[i:]

# HTML 插到 <main> 前
j = s.find("<main>")
assert j > 0
s = s[:j] + HTML + s[j:]

# JS 插到 </body> 前
k = s.rfind("</body>")
assert k > 0
s = s[:k] + JS + s[k:]

io.open(P, "w", encoding="utf-8", newline=None).write(s)
print("已插入说明书，文件 %d 字节" % len(s.encode("utf-8")))
