"""单据预览第 2 部分：按钮、浮层、纸样样式、打印规则。"""
import io

P = "D:/pocib-helper/app/index.html"
s = io.open(P, encoding="utf-8", newline=None).read()
assert 'id="docPvBtn"' not in s

# ---------------- 1) 单据卡加按钮（和 chips 同一行） ----------------
old_chips = '''    <div class="body" id="docChips" style="padding:8px 14px 0"></div>
    <div style="padding:6px 14px 0;font-size:11.5px;color:#8b95a3">点任意一行的「值」即可复制该项</div>'''
new_chips = '''    <div class="body" style="padding:8px 14px 0;display:flex;align-items:center;gap:10px">
      <div id="docChips" style="flex:1"></div>
      <span class="mini ghost" id="docPvBtn" title="按这张单据的版式铺成一张填好的纸，可打印">预览单据</span>
    </div>
    <div style="padding:6px 14px 0;font-size:11.5px;color:#8b95a3">点任意一行的「值」即可复制该项</div>'''
assert old_chips in s
s = s.replace(old_chips, new_chips, 1)

# ---------------- 2) 浮层结构（放在 coMask 之前） ----------------
anchor = '<div class="mask" id="coMask">'
assert anchor in s
mask_html = '''<div class="mask" id="docPvMask">
  <div class="modal pv">
    <header>
      <h3 id="pvTitle">单据预览</h3>
      <span id="pvSub" style="font-size:11.5px;color:#8b95a3"></span>
      <span style="flex:1"></span>
      <button class="mini ghost" id="pvPrint" title="按当前预览打印（会隐藏页面其余部分）">打印</button>
      <span class="x" id="pvClose">×</span>
    </header>
    <div class="pvWrap" id="pvBody"></div>
  </div>
</div>

''' + anchor
s = s.replace(anchor, mask_html, 1)

# ---------------- 3) 样式 ----------------
css_anchor = "  .mask{position:fixed;inset:0;"
assert css_anchor in s
pv_css = '''  /* ---- 单据预览 ---- */
  .modal.pv{width:min(960px,100%)}
  .pvWrap{background:#e9edf2;padding:20px;overflow:auto;max-height:78vh}
  .paper{background:#fff;width:794px;min-height:1080px;margin:0 auto;padding:66px 76px 60px;
    box-shadow:0 8px 28px rgba(16,24,40,.14);color:#15181d;box-sizing:border-box;
    font-family:"Songti SC","SimSun","Source Han Serif SC",serif;font-size:14.5px;line-height:2.05}
  .paper p{margin:0 0 2px}
  .paper .pvHead{position:relative;text-align:center;margin-bottom:22px}
  .paper .pvTtl{font-size:25px;letter-spacing:10px;font-weight:700;
    color:#1b4bd0;border-bottom:2px solid #1b4bd0;display:inline-block;padding:0 10px 6px;
    font-family:"Heiti SC","Microsoft YaHei",sans-serif}
  .paper .pvTtl.sm{font-size:21px;letter-spacing:6px}
  .paper .pvNo{position:absolute;right:-10px;top:2px;font-size:13px;color:#25303d}
  .paper .pvSub{text-align:center;font-size:11.5px;color:#8a94a3;margin:-10px 0 16px;
    font-family:"Microsoft YaHei",sans-serif}
  .paper .pvLb{display:inline-block;width:70px}
  .paper .pvInd{padding-left:70px}
  .paper .pvInd3{padding-left:8px}
  .paper .pvGap{height:34px}
  .pvU{border-bottom:1px solid #333;text-decoration:none;padding:0 3px;
    display:inline-block;text-align:center;line-height:1.5}
  .pvCkList{margin:4px 0 0 18px}
  .pvCk{display:flex;align-items:baseline;gap:2px;line-height:1.75}
  .pvCk i{font-style:normal;flex:0 0 46px;color:#25303d}
  .pvCk .cn{flex:0 0 232px}
  .pvCk .cn.en2{flex:1;font-size:12.5px;letter-spacing:.3px}
  .pvCk .en{flex:0 0 235px;font-size:12.5px;letter-spacing:.3px}
  .pvCk .en2{font-size:12.5px;letter-spacing:.3px;margin-left:4px}
  .pvCk .num{margin-left:auto;flex:0 0 108px;text-align:right;font-size:13px}
  .pvSeal{margin:26px 0 0 232px}
  .pvSeal span{display:inline-block;border:1px dashed #b9c0ca;border-radius:4px;
    padding:26px 34px;font-size:12.5px;color:#8a94a3}
  .pvSign{margin-top:44px;text-align:right}
  .pvSign p{margin:0 0 6px}
  .pvSign .pvDate{margin-top:12px}
  .pvTable{width:100%;border-collapse:collapse;margin-top:6px;font-size:13px;
    font-family:"Microsoft YaHei",sans-serif}
  .pvTable th{width:34%;text-align:left;vertical-align:top;font-weight:400;color:#4b5563;
    padding:7px 10px 7px 0;border-bottom:1px solid #eef0f3}
  .pvTable td{padding:7px 0;border-bottom:1px solid #eef0f3;word-break:break-word;line-height:1.65}
  .pvTable td.pvEmpty{color:#98a1ae}

  @media print{
    @page{size:A4;margin:12mm}
    body>*:not(#docPvMask){display:none !important}
    #docPvMask{position:static !important;display:block !important;background:#fff !important;padding:0 !important}
    #docPvMask .modal.pv{box-shadow:none;width:auto;max-height:none;border-radius:0}
    #docPvMask .modal.pv header{display:none}
    #docPvMask .pvWrap{background:#fff;padding:0;max-height:none;overflow:visible}
    #docPvMask .paper{box-shadow:none;width:auto;min-height:auto;padding:0;margin:0}
  }

''' + css_anchor
s = s.replace(css_anchor, pv_css, 1)

# ---------------- 4) 事件绑定 ----------------
ev_anchor = '''$("liveSyncChk").onchange=()=>setLive($("liveSyncChk").checked);'''
assert ev_anchor in s
ev = ev_anchor + '''
/* 单据预览 */
$("docPvBtn").onclick=()=>{ try{ openDocPreview(); }catch(e){ console.warn(e); toast("预览生成失败："+e.message); } };
$("pvClose").onclick=()=>$("docPvMask").classList.remove("on");
$("pvPrint").onclick=()=>window.print();
$("docPvMask").onclick=(e)=>{ if(e.target.id==="docPvMask") $("docPvMask").classList.remove("on"); };'''
s = s.replace(ev_anchor, ev, 1)

# Esc 关闭
old_esc = '''  if($("coMask").classList.contains("on")) closeCo();'''
new_esc = '''  if($("docPvMask").classList.contains("on")) $("docPvMask").classList.remove("on");
  else if($("coMask").classList.contains("on")) closeCo();'''
assert old_esc in s
s = s.replace(old_esc, new_esc, 1)

io.open(P, "w", encoding="utf-8", newline=None).write(s)
print("浮层与样式完成")
