"""预览纸上的占位改成显眼标记。

三种状态分开：
  fill  待补   —— 程序给不出，要等 POCIB 生成单据或你自己决定（橙色虚线）
  miss  缺资料 —— 程序本该给出但档案里没有（红色虚线，指向去哪补）
  skip  不用填 —— 这栏本来就不用填（灰底，写明原因）

屏幕上看得很清楚；打印时自动隐藏底部提示条，纸面保持干净。
"""
import io

P = "D:/pocib-helper/app/index.html"
s = io.open(P, encoding="utf-8", newline=None).read()
assert "pvFill" not in s, "已改过"

# ---------------- 1) 样式 ----------------
s = s.replace(
    '''  .pvU{border-bottom:1px solid #333;text-decoration:none;padding:0 3px;
    display:inline-block;text-align:center;line-height:1.5}''',
    '''  .pvU{border-bottom:1px solid #333;text-decoration:none;padding:0 3px;
    display:inline-block;text-align:center;line-height:1.5}
  /* 待补：橙。缺资料：红。不用填：灰底 */
  .pvU.pvFill{color:#b45309;border-bottom:1px dashed #d97706;background:#fffbeb;
    border-radius:2px;font-size:13px;font-weight:600}
  .pvU.pvMiss{color:#b91c1c;border-bottom:1px dashed #dc2626;background:#fef2f2;
    border-radius:2px;font-size:13px;font-weight:600}
  .pvSkip{color:#64748b;background:#eef2f7;border-radius:3px;padding:1px 7px;
    font-size:12.5px;font-weight:600}
  .pvNote{color:#94a3b8;font-size:11.5px;margin-left:7px}
  .pvNeedTxt{color:#b45309;background:#fffbeb;padding:1px 7px;border-radius:3px;
    display:inline-block;border-left:2px solid #d97706}

  /* 底部填写提示：只在屏幕上显示，打印隐藏 */
  .pvTips{margin-top:26px;border-top:1px dashed #d7dde5;padding-top:12px;
    font-family:"Microsoft YaHei",sans-serif;font-size:12px;line-height:1.9;color:#4b5563}
  .pvTips b{font-weight:600}
  .pvTips .k1{color:#b45309}
  .pvTips .k2{color:#b91c1c}
  .pvTips .k3{color:#64748b}
  .pvTips .dot{display:inline-block;width:9px;height:9px;border-radius:2px;
    vertical-align:-1px;margin-right:5px}''', 1)

# 打印时隐藏提示条
s = s.replace(
    '''    #docPvMask .paper:last-child{page-break-after:auto}
  }''',
    '''    #docPvMask .paper:last-child{page-break-after:auto}
    #docPvMask .pvTips{display:none !important}
  }''', 1)

# ---------------- 2) 占位函数 ----------------
old_fn = '''const pvBlank=(w)=>'<u class="pvU" style="min-width:'+(w||90)+'px">&nbsp;</u>';
const pvVal=(v,w)=> v ? '<u class="pvU">'+escPv(v)+'</u>' : pvBlank(w||90);'''
new_fn = '''/* 纸上的占位分三种，颜色一眼能分：
   pvFill 待补（等单据 / 由你定）  橙色虚线
   pvMiss 缺资料（档案里没有）      红色虚线
   pvSkip 不用填                    灰底标签 + 原因 */
const pvBlank=(w)=>'<u class="pvU" style="min-width:'+(w||90)+'px">&nbsp;</u>';
const pvFill=(t,w)=>'<u class="pvU pvFill" style="min-width:'+(w||0)+'px">'+(t?escPv(t):"&nbsp;")+'</u>';
const pvMiss=(t,w)=>'<u class="pvU pvMiss" style="min-width:'+(w||0)+'px">'+escPv(t||"缺")+'</u>';
const pvSkip=(t)=>'<span class="pvSkip">'+escPv(t||"本栏不填")+'</span>';
/* v 有值 → 普通下划线；没有 → 红色「缺资料」并写清去哪补 */
const pvVal=(v,w,missHint)=> v ? '<u class="pvU">'+escPv(v)+'</u>'
                              : pvMiss(missHint||"缺·去公司档案补", w||110);'''
assert old_fn in s
s = s.replace(old_fn, new_fn, 1)

# ---------------- 3) 索赔书各处换成显眼占位 ----------------
reps = [
    # 保单号码
    ('<div class="pvNo">保单号码：${pvBlank(140)}</div>',
     '<div class="pvNo">保单号码：${pvFill("待补 · 见保险单右上角",150)}</div>'),
    # 装载于
    ('装载于${pvBlank(96)}轮，',
     '装载于${pvFill("待补 · 见提单船名航次",168)}轮，'),
    # 六个份数
    ('<span class="num">${pvBlank(46)} 份</span>',
     '<span class="num">${pvFill("填份数",46)} 份</span>'),
    # 日期
    ('<p class="pvDate">${pvBlank(52)} 年 ${pvBlank(34)} 月 ${pvBlank(34)} 日</p>',
     '<p class="pvDate">${pvFill("待补",46)} 年 ${pvFill("",30)} 月 ${pvFill("",30)} 日</p>'),
]
for a, b in reps:
    assert a in s, a[:40]
    s = s.replace(a, b, 1)

# 申请人 / 地址缺失时给具体指引
s = s.replace(
    '<p>申请人：${pvVal(d.claimant,240)}</p>',
    '<p>申请人：${pvVal(d.claimant,240,"缺 · 公司档案填中文全称")}</p>', 1)
s = s.replace(
    '<p>地&nbsp;&nbsp;址：${pvVal(d.addr,240)}</p>',
    '<p>地&nbsp;&nbsp;址：${pvVal(d.addr,240,"缺 · 公司档案填中文地址")}</p>', 1)

# ---------------- 4) 索赔书底部提示条 ----------------
old_tail = '''  <div class="pvSign">
    <p>申请人：${pvVal(d.claimant,240,"缺 · 公司档案填中文全称")}</p>
    <p>地&nbsp;&nbsp;址：${pvVal(d.addr,240,"缺 · 公司档案填中文地址")}</p>
    <p class="pvDate">${pvFill("待补",46)} 年 ${pvFill("",30)} 月 ${pvFill("",30)} 日</p>
  </div>
</div>`;'''
new_tail = '''  <div class="pvSign">
    <p>申请人：${pvVal(d.claimant,240,"缺 · 公司档案填中文全称")}</p>
    <p>地&nbsp;&nbsp;址：${pvVal(d.addr,240,"缺 · 公司档案填中文地址")}</p>
    <p class="pvDate">${pvFill("待补",46)} 年 ${pvFill("",30)} 月 ${pvFill("",30)} 日</p>
  </div>
  <div class="pvTips">
    <b>纸上标记怎么看</b><br>
    <span class="k1">■</span> <b class="k1">橙色虚线</b>＝这一格要你补，程序拿不到：
      保单号码（货物运输保险单右上角）、装载于（海运提单 Ocean Vessel Voy.No.／空运单 Flight）、
      随附单据份数（按需打○并填）、申请日期。<br>
    <span class="k2">■</span> <b class="k2">红色虚线</b>＝资料还没填，去「公司档案」补上就会自动出现。<br>
    <span class="k3">■</span> <b class="k3">灰色标签</b>＝这一栏不用填，标签里写了原因。<br>
    <span style="color:#64748b">黑色下划线是已经自动填好的值，照抄即可。此提示不会打印。</span>
  </div>
</div>`;'''
assert old_tail in s
s = s.replace(old_tail, new_tail, 1)

# ---------------- 5) 通用版式：留空 / 待确认也标出来 ----------------
old_gen = '''  const cells=(rows||[]).map(([k,v])=>{
    const t=String(v==null?"":v);
    const cls=/^（留空|（非|^空$/.test(t.trim())?"pvEmpty":"";
    return `<tr><th>${escPv(k)}</th><td class="${cls}">${escPv(t).replace(/\\n/g,"<br>")}</td></tr>`;
  }).join("");'''
new_gen = '''  const cells=(rows||[]).map(([k,v])=>{
    const t=String(v==null?"":v);
    const body=escPv(t).replace(/\\n/g,"<br>");
    /* 不用填的（原文写「留空/不填」）用灰标签 + 附上原文；
       要你补的（「待确认/自行填写/回填」）整段加橙底，扫一眼就能挑出来 */
    let td;
    if(/留空|不填/.test(t))      td=`<span class="pvSkip">本栏不填</span><span class="pvNote">${body}</span>`;
    else if(/待确认|待填|自行填写|回填|收到后/.test(t)) td=`<span class="pvNeedTxt">${body}</span>`;
    else if(!t.trim())           td=`<span class="pvSkip">本栏不填</span>`;
    else                         td=body;
    return `<tr><th>${escPv(k)}</th><td>${td}</td></tr>`;
  }).join("");'''
assert old_gen in s
s = s.replace(old_gen, new_gen, 1)

io.open(P, "w", encoding="utf-8", newline=None).write(s)
print("ok")
