"""选品参考：引入进出口税率做评判。

改动：
  1) 在 PNAME 之后插入 GHS 常量（商品编号 → 近似税则号 + 税率）
  2) 新增 goodTax()：取某商品的关税 / 增值税 / 退税 / 消费税
  3) pairCalc 增加税后口径
  4) renderPair 增列「税后毛利率」，排序加一项，「推荐」改按税后
  5) 表头 / 排序下拉 / 备注同步
"""
import io
import re

P = "D:/pocib-helper/app/index.html"
s = io.open(P, encoding="utf-8", newline=None).read()
orig_len = len(s)

# ---------------- 1) GHS 常量 ----------------
GHS_JS = io.open("D:/pocib-helper/scripts/_ghs.js", encoding="utf-8").read()
assert "const GHS=" not in s, "GHS 已插入过，先撤回再跑"
m = re.search(r'(const PNAME=\{"[^\n]*"\};)\n', s)
assert m, "找不到 PNAME 结尾"
s = s[:m.end(1)] + "\n" + GHS_JS + "\n" + s[m.end(1):]

# ---------------- 2) goodTax ----------------
TAX_FN = '''
/* 商品编号 → 近似税则信息（GHS 由 scripts/gen_goods_hs.py 生成，人工核定过一轮）。
   返回 null 表示该商品在税则里没有可靠对应，界面显示「税率待定」。
   [hs, 进口优惠税率%, 增值税%, 出口退税率%, 消费税从价%] */
function goodTax(code){
  const g=GHS[code];
  if(!g) return null;
  return {hs:g[0], imPref:g[1], vat:g[2], rebate:g[3], cs:g[4]};
}
'''
anchor = "/* 比价核心：出口国工厂价 vs 进口国市场价，统一折成美元后算价差与毛利率 */"
assert anchor in s
s = s.replace(anchor, TAX_FN.strip() + "\n\n" + anchor, 1)

# ---------------- 3) pairCalc 加税后 ----------------
old_calc = '''/* 比价核心：出口国工厂价 vs 进口国市场价，统一折成美元后算价差与毛利率 */
function pairCalc(from,to,fxv){
  const A=PRICE[from], B=PRICE[to];
  if(!A||!B) return [];
  const fa=fxUsd(A.cur,fxv), fb=fxUsd(B.cur,fxv);
  const rows=[];
  for(const code in A.f){
    const pm=B.m[code];
    if(pm==null || !A.f[code]) continue;
    const cost=A.f[code]*fa, sell=pm*fb;
    if(!(cost>0)) continue;
    rows.push({code,fPrice:A.f[code],fCur:A.cur,mPrice:pm,mCur:B.cur,
               cost,sell,diff:sell-cost,rate:(sell-cost)/cost});
  }
  return rows;
}'''

new_calc = '''/* 比价核心：出口国工厂价 vs 进口国市场价，统一折成美元后算价差与毛利率。
   税后口径（每单位，均已折 USD）：
     不含税售价 = 市场价 ÷ (1 + 增值税率)          —— 市场价是含税零售价
     进口关税   = 不含税售价 × 进口优惠税率         —— 以不含税售价当完税价近似，属保守估
     消费税     = (不含税售价 + 关税) × 消费税率 ÷ (1 − 消费税率)
     出口退税   = 工厂价 × 退税率 ÷ (1 + 增值税率)  —— POCIB 口径，仅出口国为中国时计
     税后毛利   = 不含税售价 − 工厂价 + 出口退税 − 关税 − 消费税
   进口增值税在销售环节可抵扣，不计入成本。 */
function pairCalc(from,to,fxv){
  const A=PRICE[from], B=PRICE[to];
  if(!A||!B) return [];
  const fa=fxUsd(A.cur,fxv), fb=fxUsd(B.cur,fxv);
  const rows=[];
  for(const code in A.f){
    const pm=B.m[code];
    if(pm==null || !A.f[code]) continue;
    const cost=A.f[code]*fa, sell=pm*fb;
    if(!(cost>0)) continue;
    const row={code,fPrice:A.f[code],fCur:A.cur,mPrice:pm,mCur:B.cur,
               cost,sell,diff:sell-cost,rate:(sell-cost)/cost,
               tax:null, netDiff:null, netRate:null};
    const t=goodTax(code);
    if(t){
      const vatR=(t.vat||0)/100, dutyR=(t.imPref||0)/100;
      const csR=(t.cs||0)/100, rebR=(from==="中国")?(t.rebate||0)/100:0;
      const netSell=sell/(1+vatR);
      const duty=netSell*dutyR;
      const cs=csR>0 ? (netSell+duty)*csR/(1-csR) : 0;
      const rebate=cost*rebR/(1+vatR);
      row.tax=t;
      row.netDiff=netSell-cost+rebate-duty-cs;
      row.netRate=row.netDiff/cost;
    }
    rows.push(row);
  }
  return rows;
}'''
assert old_calc in s
s = s.replace(old_calc, new_calc, 1)

# ---------------- 4) renderPair ----------------
old_render = s[s.index("function renderPair(){"):s.index('["pairFrom","pairTo"].forEach(id=>{')]
new_render = '''function renderPair(){
  const tbody=$("pairRows"); if(!tbody) return;
  const from=$("pairFrom").value, to=$("pairTo").value;
  const fxv=fxRead();
  const rows=pairCalc(from,to,fxv);
  if(!rows.length){
    tbody.innerHTML="";
    const A=PRICE[from], B=PRICE[to];
    let msg="请选择出口国与进口国。";
    if(A && B){
      const shared=Object.keys(A.f).filter(k=>B.m[k]!=null);
      if(!shared.length) msg=`${from} 与 ${to} 之间没有共同的商品编号，换一对试试。`;
      else if(!(fxUsd(A.cur,fxv)>0)) msg=`缺 ${A.cur} 的汇率，上面「汇率 1 USD =」里补上就能算（现有 ${Object.keys(FX_DEF).join(" / ")}）。`;
      else if(!(fxUsd(B.cur,fxv)>0)) msg=`缺 ${B.cur} 的汇率，上面「汇率 1 USD =」里补上就能算（现有 ${Object.keys(FX_DEF).join(" / ")}）。`;
      else msg="这两个国家之间没有可比的商品，换一对试试。";
    }
    $("pairNote").textContent=msg;
    $("pairHint").textContent=`${from||"?"} → ${to||"?"} · 无可比商品`;
    return;
  }
  const sort=$("pairSort").value;
  const hasNet=r=>r.netRate!=null;
  rows.sort((x,y)=>{
    if(sort==="net"){
      /* 有税率的排前面，税后毛利率高的在前 */
      if(hasNet(x)!==hasNet(y)) return hasNet(y)?1:-1;
      if(!hasNet(x)) return y.rate-x.rate;
      return y.netRate-x.netRate;
    }
    return sort==="diff" ? y.diff-x.diff
         : sort==="code" ? x.code.localeCompare(y.code)
         : y.rate-x.rate;
  });
  const top3=new Set(rows.filter(hasNet).filter(r=>r.netDiff>0)
                     .slice(0,3).map(r=>r.code));
  tbody.innerHTML=rows.map((r,i)=>{
    const cls=r.diff>=0?"pm":"pn";
    const pct=r.rate*100;
    const tag=(sort==="net" && top3.has(r.code) && i<3)?'<span class="pairTag">推荐</span>'
             :(sort==="rate" && i<3 && r.diff>0)?'<span class="pairTag">推荐</span>':"";
    const t=r.tax;
    const taxLine=t
      ? `<div class="usd" title="近似税号 ${t.hs}：关税 ${t.imPref}% · 增值税 ${t.vat}%${t.cs?" · 消费税 "+t.cs+"%":""} · 出口退税 ${from==="中国"?t.rebate+"%":"不适用"}">关税 ${t.imPref}% · 增值税 ${t.vat}%${t.cs?" · 消费税 "+t.cs+"%":""}</div>`
      : `<div class="usd" style="color:#b8bfc9" title="该商品在税则里没有可靠对应，正式报关以 POCIB 商品资料里的 HS 为准">税率待定</div>`;
    const netCell = hasNet(r)
      ? `<td class="num ${r.netDiff>=0?"pm":"pn"}">${r.netDiff>=0?"+":"−"}${n2(Math.abs(r.netDiff))}
           <div class="usd">${(r.netRate*100>=0?"+":"")+(r.netRate*100).toFixed(1)}%</div></td>`
      : `<td class="num" style="color:#b8bfc9">—</td>`;
    return `<tr>
      <td>${r.code}</td>
      <td>${PNAME[r.code]||""}${tag}${taxLine}</td>
      <td class="num">${money(r.fPrice,r.fCur)}<div class="usd">≈ USD ${n2(r.cost)}</div></td>
      <td class="num">${money(r.mPrice,r.mCur)}<div class="usd">≈ USD ${n2(r.sell)}</div></td>
      <td class="num ${cls}">${r.diff>=0?"+":"−"}${n2(Math.abs(r.diff))}</td>
      <td class="num ${cls}">${pct>=0?"+":""}${pct.toFixed(1)}%</td>
      ${netCell}
    </tr>`;
  }).join("") || `<tr><td colspan="7" style="color:#8b95a3">这两个国家之间没有共同的商品编号，换一对试试。</td></tr>`;
  const profit=rows.filter(r=>r.diff>0).length;
  const taxed=rows.filter(hasNet).length;
  const netPos=rows.filter(r=>hasNet(r)&&r.netDiff>0).length;
  $("pairNote").innerHTML=`${from} 工厂 → ${to} 市场：可比较 ${rows.length} 个商品，${profit} 个税前有正价差，`
    +`${netPos} 个扣掉关税与消费税后仍有正毛利（已计入税率 ${taxed} 个）。`
    +`<br><b>税后口径</b>：不含税售价 = 市场价 ÷ (1+增值税率)；关税按不含税售价估（到岸价更低，属保守估）；`
    +`进口增值税在销售环节可抵扣，不计入成本；出口退税按 POCIB「收购价 × 退税率 ÷ (1+增值税率)」计，`
    +`仅出口国为中国时计。`
    +`<br><b>税率来源</b>：按商品名匹配海关税则的同类条目（鼠标停在「关税 x%」上可看税号），`
    +`不是 POCIB 商品资料里的真实 HS，<b>只作选品参考，正式报关以 POCIB 查到的 HS 为准</b>；`
    +`标「税率待定」的商品不参与税后排序。运费与保险仍未计入。`;
  $("pairHint").textContent=`${from} → ${to} · 共 ${rows.length} 项 · 已计税率 ${taxed} 项`;
}

'''
s = s.replace(old_render, new_render, 1)

# ---------------- 5) 表头 ----------------
old_thead = '''            <th style="width:120px">价差（USD）</th>
            <th style="width:88px">毛利率</th>
          </tr></thead>'''
new_thead = '''            <th style="width:116px">价差（USD）</th>
            <th style="width:82px">毛利率</th>
            <th style="width:104px" title="扣掉进口关税与消费税、加回出口退税后的毛利，按工厂价算比率">税后毛利率</th>
          </tr></thead>'''
assert old_thead in s
s = s.replace(old_thead, new_thead, 1)

# ---------------- 6) 排序下拉 ----------------
old_sort = '''          <option value="rate">毛利率 高 → 低</option>
          <option value="diff">价差 大 → 小</option>
          <option value="code">商品编号</option>'''
new_sort = '''          <option value="net">税后毛利率 高 → 低</option>
          <option value="rate">税前毛利率 高 → 低</option>
          <option value="diff">价差 大 → 小</option>
          <option value="code">商品编号</option>'''
assert old_sort in s
s = s.replace(old_sort, new_sort, 1)

# 默认排序改成税后，最能体现「引入税率做评判」
s = s.replace('<select id="pairSort">\n          <option value="net">',
              '<select id="pairSort">\n          <option value="net">', 1)
# 把 net 设为默认（移到第一项已经默认选中）

# ---------------- 7) 标题提示 ----------------
s = s.replace('<h2>选品参考 <span id="pairHint">进口国市场价 − 出口国工厂价，未计关税与运费</span></h2>',
              '<h2>选品参考 <span id="pairHint">进口国市场价 − 出口国工厂价，已计关税与增值税</span></h2>', 1)

io.open(P, "w", encoding="utf-8", newline=None).write(s)
print("写入完成：%d → %d 字节（+%d）" % (orig_len, len(s), len(s) - orig_len))
