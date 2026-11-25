"""单据预览：把当前单据渲染成一张「填好的纸」。

第一步只做「索赔申请书」的精排版，其余单据用通用版式（字段速览），
后续可以逐个替换成官方版式。

改动：
  1) 抽出 claimData()：索赔申请书的所有取值，字段表与预览共用
  2) docFields 的索赔分支改为调用它
  3) 单据卡加「预览单据」按钮 + 预览浮层
  4) 渲染：paperClaim() 精排版 / paperGeneric() 通用版式
  5) 打印样式
"""
import io

P = "D:/pocib-helper/app/index.html"
s = io.open(P, encoding="utf-8", newline=None).read()
assert 'id="docPvMask"' not in s, "预览已存在"

# ---------------- 1) claimData + 版式，插在 renderFields 之前 ----------------
anchor = "let DOCI=0;\nfunction renderFields(step,di){"
assert anchor in s

claim_js = '''/* ================= 单据预览 =================
   把当前单据按「填好的纸」渲染出来，便于对照 POCIB 页面逐格填。
   索赔申请书是精排版（按 POCIB 原表单复刻），其余单据先用字段速览版式。 */

/* 索赔申请书的全部取值：字段表与预览共用同一份，避免两处各算一套 */
function claimData(){
  const c=CASES[CASE], D=derived();
  const my=CO(c.my), cp=CO(c.cp);
  /* 申请人固定是进口商：CIF/CIP 下出口商投保后把保单背书转让，索赔权在进口商手上 */
  const buyer=c.role==="出口商"?cp:my;
  const portCn=portZh(c.port_load)||portShort(c.port_load);
  const goodsCn=c.hs_zh||(GD(c.goods_no)||{}).name_zh||c.goods;
  return {
    c,D,buyer,
    portCn, goodsCn,
    sea: c.transport!=="空运",
    insured: n2(D.insured),
    amt: "USD "+n2(D.insured),
    claimant: buyer.name_zh||"",
    addr: buyer.address_zh||""
  };
}

/* 待填的空：值没拿到就画一条下划线，别留空白让人以为是漏了 */
const pvBlank=(w)=>'<u class="pvU" style="min-width:'+(w||90)+'px">&nbsp;</u>';
const pvVal=(v,w)=> v ? '<u class="pvU">'+escPv(v)+'</u>' : pvBlank(w||90);
function escPv(v){ return String(v==null?"":v).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;"); }

function paperClaim(){
  const d=claimData();
  const CK=[["保险单正本","ORIGINAL POLICY"],
            ["提单正反面","BILL OF LODING"],
            ["商业发票","COMMERCIAL INVOICE"],
            ["装箱单","PACKING LIST"]];
  const ckRow=(cn,en)=>`<div class="pvCk"><i>（　）</i><span class="cn">${cn}</span><span class="en">${en}</span><span class="num">${pvBlank(46)} 份</span></div>`;
  return `<div class="paper">
  <div class="pvHead">
    <div class="pvTtl">索 赔 申 请 书</div>
    <div class="pvNo">保单号码：${pvBlank(140)}</div>
  </div>
  <p><span class="pvLb">受文者：</span>${pvVal("国际保险公司")}</p>
  <p><span class="pvLb">主&nbsp;&nbsp;旨：</span>向贵公司投保之进出口货物发生损失，兹请予以理赔。</p>
  <p><span class="pvLb">说&nbsp;&nbsp;明：</span>一、本公司自${pvVal(d.portCn,110)}港，进出口${pvVal(d.goodsCn,150)}货物，
     装载于${pvBlank(120)}轮，</p>
  <p class="pvInd">因货物发生损失，请依保险契约的约定予以理赔。</p>
  <p class="pvInd">二、前项损失共计损失${pvVal(d.amt,140)}元经计算如后：</p>
  <div class="pvGap"></div>
  <p class="pvInd3">三、随附有关之索赔文件如下（打○者）</p>
  <div class="pvCkList">
    ${CK.map(([cn,en])=>ckRow(cn,en)).join("")}
    <div class="pvCk"><i>（　）</i><span class="cn">与运送人之损失追偿往来函件</span><span class="num">${pvBlank(46)} 份</span></div>
    <div class="pvCk"><i></i><span class="cn en2">CORRESPONDENCES EXCHANGED WITH</span></div>
    <div class="pvCk"><i></i><span class="cn en2">CARRIERS REGARDING THEIR LIABILITY</span></div>
    <div class="pvCk"><i>（　）</i><span class="cn">其他证明文件（索赔清单/报价单）<span class="en2"> OTHER CERTIFICATES</span></span><span class="num">${pvBlank(46)} 份</span></div>
    <div class="pvCk"><i></i><span class="cn">${pvBlank(380)}</span></div>
  </div>
  <div class="pvSeal"><span>（请加盖贵公司大小章）</span></div>
  <div class="pvSign">
    <p>申请人：${pvVal(d.claimant,240)}</p>
    <p>地&nbsp;&nbsp;址：${pvVal(d.addr,240)}</p>
    <p class="pvDate">${pvBlank(52)} 年 ${pvBlank(34)} 月 ${pvBlank(34)} 日</p>
  </div>
</div>`;
}

/* 通用版式：其他单据先用这个，标题 + 字段两列，够对照着填 */
function paperGeneric(doc, rows){
  const cells=(rows||[]).map(([k,v])=>{
    const t=String(v==null?"":v);
    const cls=/^（留空|（非|^空$/.test(t.trim())?"pvEmpty":"";
    return `<tr><th>${escPv(k)}</th><td class="${cls}">${escPv(t).replace(/\\n/g,"<br>")}</td></tr>`;
  }).join("");
  return `<div class="paper">
  <div class="pvHead"><div class="pvTtl sm">${escPv(doc||"单据")}</div></div>
  <div class="pvSub">POCIB 填单助手 · 字段速览（版式非官方，按 POCIB 页面逐格填）</div>
  <table class="pvTable">${cells || `<tr><td class="pvEmpty">该环节没有字段</td></tr>`}</table>
</div>`;
}

function openDocPreview(){
  const doc=LAST_DOC||"";
  if(!doc){ toast("先在左边点一个环节"); return; }
  $("pvTitle").textContent=doc;
  $("pvSub").textContent="第 "+LAST_STEP+" 步 · "+(rows0(LAST_STEP)||"");
  $("pvBody").innerHTML = (doc==="索赔申请书") ? paperClaim() : paperGeneric(doc,LAST_ROWS);
  $("docPvMask").classList.add("on");
}
function rows0(step){ const f=FLOW.find(x=>x.s===step); return f?f.n:""; }

let DOCI=0;
function renderFields(step,di){'''

s = s.replace(anchor, claim_js, 1)

# ---------------- 2) 索赔分支改为用 claimData ----------------
# 找到索赔分支整块替换
start = s.index('''  // —— 索赔申请书（第 17 步：进口商持保单等单据向保险公司索赔）——''')
end = s.index('''  // —— 报关单 ——''')
new_branch = '''  // —— 索赔申请书（第 17 步：进口商持保单等单据向保险公司索赔）——
  else if(doc==="索赔申请书"){
    const q=claimData();
    G("保单号码","（抄货物运输保险单右上角的保单号）","待确认");
    G("受文者","国际保险公司","固定");
    G("出口港（起运港，中文）",q.portCn,"自动");
    G("货物名称（中文）",q.goodsCn,"自动");
    G("装载于",q.sea
        ? "抄海运提单的 Ocean Vessel Voy.No.（船名 + 航次）"
        : "抄航空运单（AWB）的 Flight 栏位（航班号 + 日期）","待确认");
    G("损失金额及币别",q.amt+"（＝保单上的保险金额）","自动");
    G("随附单据 · 保险单正本 ORIGINAL POLICY","__ 份（打○）","待确认");
    G("随附单据 · 提单正反面 BILL OF LODING","__ 份（打○，空运改填航空运单）","待确认");
    G("随附单据 · 商业发票 COMMERCIAL INVOICE","__ 份（打○）","待确认");
    G("随附单据 · 装箱单 PACKING LIST","__ 份（打○）","待确认");
    G("随附单据 · 与运送人损失追偿往来函件","__ 份（有则打○）","待确认");
    G("随附单据 · 其他证明文件（索赔清单 / 报价单）","__ 份（有则打○）","待确认");
    G("加盖印章","（请加盖贵公司大小章）","待确认");
    G("申请人",q.claimant||"（先在公司档案填中文全称）","自动");
    G("地址",q.addr||"（先在公司档案填中文地址）","自动");
    G("申请日期","____ 年 __ 月 __ 日（须为日期格式）","待确认");
    G("正文（点一下整段复制）",
      "本公司向贵公司投保之进出口货物发生损失，兹请予以理赔。\\n"
      +"一、本公司自"+q.portCn+"港，进出口"+q.goodsCn+"货物，装载于____轮，"
      +"因货物发生损失，请依保险契约的约定予以理赔。\\n"
      +"二、前项损失共计损失"+q.amt+"元经计算如后：","自动");
    note="申请人固定是进口商（保单已背书转让，索赔权在进口商手上），地址填进口商中文地址，"
        +"两者都取自「公司档案」的中文字段。\\n"
        +"「装载于」与「保单号码」要等 POCIB 生成单据之后才拿得到："
        +"船名航次见海运提单的 Ocean Vessel Voy.No.（空运见航空运单的 Flight），保单号见货物运输保险单右上角。\\n"
        +"「损失金额」按保单上的保险金额填（不是发票金额，也不是 CIF 价）。"
        +"随附单据按实际需要打○并填份数，通常六项各 1 份；索赔清单/报价单没有就不打○。\\n"
        +"同一步的「出险通知书」本工具未收录官方填写说明，按 POCIB 页面上的栏位自行填。";
  }

'''
s = s[:start] + new_branch + s[end:]

io.open(P, "w", encoding="utf-8", newline=None).write(s)
print("数据函数与分支完成")
