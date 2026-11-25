"""给「入境货物检验检疫申请」做精排版预览（按 POCIB 原表单）。

数据直接读 LAST_ROWS（字段表那一份），保证纸上和列表完全一致。
表格用 8 列固定栅格（各 12.5%），colspan 控制跨列。
"""
import io

P = "D:/pocib-helper/app/index.html"
s = io.open(P, encoding="utf-8", newline=None).read()
assert "paperQuarantine" not in s

# ---------------- 1) 样式 ----------------
css_anchor = "  /* 底部填写提示：只在屏幕上显示，打印隐藏 */"
assert css_anchor in s
q_css = '''  /* ---- 入境货物检验检疫申请（表格式版式）---- */
  .paper.pvQ{padding:42px 40px 34px}
  .pvQ .qTtl{text-align:center;font-size:19px;font-weight:700;color:#1b4bd0;
    letter-spacing:3px;margin-bottom:10px;font-family:"Heiti SC","Microsoft YaHei",sans-serif}
  .qT{width:100%;border-collapse:collapse;table-layout:fixed;
    font-family:"Microsoft YaHei",sans-serif;font-size:10.5px;line-height:1.42}
  .qT td{border:1px solid #3a3f47;padding:2px 4px;vertical-align:middle;
    word-break:break-word;overflow-wrap:anywhere}
  .qT .lb{background:#f2f4f7;font-size:10px;color:#2b3038;text-align:center;
    line-height:1.32;padding:2px 3px}
  .qT .sub{background:#fafbfc;font-size:9.5px;color:#4b5563;text-align:center}
  .qT .ct{text-align:center}
  .qT .sm{font-size:9.5px;line-height:1.55}
  .qT .fill{color:#b45309;font-weight:600;background:#fffbeb}
  .qT .skip{color:#7b8794;font-size:9.5px}
  .qT .ck{font-size:9.5px;line-height:1.62;letter-spacing:0}
  .qT .sign{height:34px;vertical-align:bottom}
  .pvQ .qFoot{font-size:9px;color:#5b6675;margin-top:5px;font-family:"Microsoft YaHei",sans-serif}

''' + css_anchor
s = s.replace(css_anchor, q_css, 1)

# ---------------- 2) 渲染函数，插在 paperGeneric 之后 ----------------
anchor_fn = "function openDocPreview(){"
assert anchor_fn in s

q_fn = '''/* 入境货物检验检疫申请：照 POCIB 那张表排，8 列栅格 */
function paperQuarantine(){
  const R=LAST_ROWS||[];
  const pick=(k)=>{ const r=R.find(x=>String(x[0]).indexOf(k)===0); return r?[String(r[1]),String(r[2])]:["",""]; };
  /* 值太长塞不进格子时换成短提示 */
  const SHORT={
    "（提货单 / 运单上的编号）":"待补·见提货单",
    "（到货通知邮件上的日期）":"待补·见到货通知",
    "（按合同索赔条款的截止日期）":"待补·按合同条款",
    "（质量 / 卫生等特殊条款；无则填「无」）":"待补·无则填「无」",
    "（须申请人亲笔签名）":"亲笔签名",
    "（一般商品可空白）":"可空白",
    "（未卸毕可暂不填，卸毕后补）":"待补·卸毕后填",
    "（直航不填）":"直航不填",
    "（POCIB 可不填，留空）":"可不填",
    "（如 加工 / 销售；用途明确的商品可不填）":"可不填",
    "（由海关填写）":"",
    "（海关受理申请日现场填写）":"现场填写"
  };
  const SHORT_KEY=[
    ["参考提货单（B/L）上的船名（只填船名，不带航次）","待补·见提货单船名"],
    ["参考航空运单（AWB）上的航班号（只填航班号，不带航次）","待补·见运单航班号"]
  ];
  /* 一个格子：自动填好的照抄，要补的标橙，不用填的标灰 */
  const cell=(k,opt)=>{
    let [v,tag]=pick(k);
    const hit=SHORT_KEY.find(x=>v===x[0]);
    if(hit) return `<span class="fill">${hit[1]}</span>`;
    if(v in SHORT){
      const t=SHORT[v];
      return t ? `<span class="fill">${escPv(t)}</span>` : `<span class="skip">海关填写</span>`;
    }
    if(tag==="空") return `<span class="skip">${escPv(opt==="skipText"?"":"")||"本栏不填"}</span>`;
    if(tag==="待确认") return `<span class="fill">${escPv(v)}</span>`;
    if(!v.trim()) return `<span class="skip">本栏不填</span>`;
    return escPv(v).replace(/\\n/g,"<br>");
  };
  const c2=(k)=>cell(k);
  /* 日期拆成 年 / 月 / 日 */
  const dateCell=()=>{
    const [v]=pick("申请日期");
    const m=String(v||"").match(/^(\\d{4})-(\\d{1,2})-(\\d{1,2})$/);
    if(m) return `${m[1]} 年 ${m[2]} 月 ${m[3]} 日`;
    return v? escPv(v) : '<span class="fill">待补</span>';
  };
  const goods=pick("货物名称（中/外文）")[0];
  const [gCn,gEn]=String(goods).split("\\n");
  const ent=pick("企业性质（按收货人性质勾选）")[0];
  const att=pick("随附单据（打√，合同/发票/提运单/装箱单必须）")[0];

  return `<div class="paper pvQ">
  <div class="qTtl">入境货物检验检疫申请</div>
  <table class="qT">
    <tr>
      <td class="lb" style="width:12.5%">申请单位<br>（加盖公章）</td>
      <td colspan="6">${c2("申请单位名称")}</td>
      <td class="lb" style="width:12.5%">*编&nbsp;号</td>
    </tr>
    <tr>
      <td class="lb">申请单位登记号</td>
      <td colspan="2">${c2("申请单位登记号")}</td>
      <td class="lb" style="width:8%">联系人</td>
      <td>${c2("申请单位联系人")}</td>
      <td class="lb" style="width:8%">电话</td>
      <td colspan="2">${c2("申请单位电话")}</td>
    </tr>
    <tr>
      <td class="lb">申请日期</td>
      <td colspan="7">${dateCell()}</td>
    </tr>
    <tr>
      <td class="lb" rowspan="2">收货人</td>
      <td class="sub" style="width:6%">（中文）</td>
      <td colspan="3">${c2("收货人（中文）")}</td>
      <td class="lb" rowspan="2" style="width:11%">企业性质<br>（划"√"）</td>
      <td colspan="2" rowspan="2" class="ck">${escPv(ent).replace(/\\s{2,}/g,"<br>")}</td>
    </tr>
    <tr>
      <td class="sub">（英文）</td>
      <td colspan="3">${c2("收货人（英文）")}</td>
    </tr>
    <tr>
      <td class="lb" rowspan="2">发货人</td>
      <td class="sub">（中文）</td>
      <td colspan="5">${c2("发货人（中文）")}</td>
    </tr>
    <tr>
      <td class="sub">（英文）</td>
      <td colspan="5">${c2("发货人（英文）")}</td>
    </tr>
    <tr>
      <td class="lb">选择</td>
      <td class="lb" colspan="2">货物名称（中/外文）</td>
      <td class="lb">H.S.编码</td>
      <td class="lb">原产国<br>（地区）</td>
      <td class="lb">数/重量</td>
      <td class="lb">货物总值</td>
      <td class="lb">包装种类<br>及数量</td>
    </tr>
    <tr>
      <td class="ct">□</td>
      <td colspan="2">${gCn?escPv(gCn):'<span class="fill">缺·商品档案填中文名</span>'}<br>${gEn?escPv(gEn):'<span class="fill">缺·商品档案填英文名</span>'}</td>
      <td class="ct">${c2("H.S.编码")}</td>
      <td class="ct">${c2("原产国（地区）")}</td>
      <td class="ct">${c2("数/重量")}</td>
      <td class="ct">${c2("货物总值")}</td>
      <td class="ct">${c2("包装种类及数量")}</td>
    </tr>
    <tr>
      <td class="lb">运输工具名称号码</td>
      <td colspan="3">${c2("运输工具名称号码")}</td>
      <td class="lb">合同号</td>
      <td colspan="3">${c2("合同号")}</td>
    </tr>
    <tr>
      <td class="lb">提/运单号</td>
      <td colspan="3">${c2("提单/运单号")}</td>
      <td class="lb">贸易国别<br>（地区）</td>
      <td colspan="3">${c2("贸易国别（地区）")}</td>
    </tr>
    <tr>
      <td class="lb">许可证/审批号</td>
      <td colspan="3">${c2("许可证/审批号")}</td>
      <td class="lb">启运国家<br>（地区）</td>
      <td colspan="3">${c2("启运国家（地区）")}</td>
    </tr>
    <tr>
      <td class="lb">到货日期</td>
      <td colspan="3">${c2("到货日期")}</td>
      <td class="lb">卸毕日期</td>
      <td colspan="3">${c2("卸毕日期")}</td>
    </tr>
    <tr>
      <td class="lb">启运口岸</td>
      <td colspan="3">${c2("启运口岸")}</td>
      <td class="lb">入境口岸</td>
      <td colspan="3">${c2("入境口岸")}</td>
    </tr>
    <tr>
      <td class="lb">索赔有效期至</td>
      <td colspan="3">${c2("索赔有效期至")}</td>
      <td class="lb">经停口岸</td>
      <td colspan="3">${c2("经停口岸")}</td>
    </tr>
    <tr>
      <td class="lb">目的地</td>
      <td colspan="3">${c2("目的地")}</td>
      <td class="lb">贸易方式</td>
      <td colspan="3">${c2("贸易方式")}</td>
    </tr>
    <tr>
      <td class="lb">集装箱规格、<br>数量及号码</td>
      <td colspan="7">${c2("集装箱规格、数量及号码")}</td>
    </tr>
    <tr>
      <td class="lb">合同订立的<br>特殊条款</td>
      <td colspan="4">${c2("合同订立的特殊条款以及其他要求")}</td>
      <td class="lb">货物存放地点</td>
      <td colspan="2">${c2("货物存放地点")}</td>
    </tr>
    <tr>
      <td class="lb">用途</td>
      <td colspan="7">${c2("用途")}</td>
    </tr>
    <tr>
      <td class="lb">随附单据<br>（划"√"或补填）</td>
      <td colspan="3" class="ck">${escPv(String(att||"").split("\\n").filter(x=>x.indexOf("（除")<0).join("<br>")).replace(/&lt;br&gt;/g,"<br>")}</td>
      <td class="lb">标记及号码</td>
      <td colspan="3">${c2("标记及号码")}</td>
    </tr>
    <tr>
      <td class="lb">*检验检疫费</td>
      <td colspan="3"><span class="skip">由海关填写</span></td>
      <td class="lb">计费人</td>
      <td><span class="skip">海关</span></td>
      <td class="lb" style="width:8%">收费人</td>
      <td><span class="skip">海关</span></td>
    </tr>
    <tr>
      <td class="lb">申请人<br>郑重声明</td>
      <td colspan="3" class="sm">1. 本人被授权申请检疫。<br>2. 上列填写内容正确属实。</td>
      <td class="lb">签名</td>
      <td colspan="3" class="sign"><span class="fill">亲笔签名</span></td>
    </tr>
    <tr>
      <td class="lb">领取证单</td>
      <td colspan="3"><span class="skip">海关受理申请日现场填写</span></td>
      <td class="lb">日期 / 签名</td>
      <td colspan="3" class="sign"></td>
    </tr>
  </table>
  <div class="qFoot">注：有"*"栏由海关填写。</div>
</div>`;
}

function openDocPreview(){'''
s = s.replace(anchor_fn, q_fn, 1)

# ---------------- 3) 分发 ----------------
old_dispatch = '''  $("pvBody").innerHTML = (doc==="索赔申请书") ? paperClaim() : paperGeneric(doc,LAST_ROWS);'''
new_dispatch = '''  $("pvBody").innerHTML = (doc==="索赔申请书") ? paperClaim()
                       : (doc==="入境货物检验检疫申请") ? paperQuarantine()
                       : paperGeneric(doc,LAST_ROWS);'''
assert old_dispatch in s
s = s.replace(old_dispatch, new_dispatch, 1)

io.open(P, "w", encoding="utf-8", newline=None).write(s)
print("ok")
