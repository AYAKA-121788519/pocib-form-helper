"""保费加成 / 保险费率 主面板 ↔ 函电 双向同步。

问题：主面板「交易剖面 · 运费与保险」里的「加成 %」「费率 ‰」只往下读、从不被写，
在函电里改了险别或加成，切回主面板还是旧值，两边对不上。

做法：
  · 函电 → 主面板：新增 LETTERS_ADOPT_INS(加成小数, 费率‰)，函电在
    加成 / 基本险 / 附加险变化时调用；主面板收到后写 #markup 与 #rate 并重算。
  · 主面板 → 函电：bridgeToLetters 末尾调 applyInsFromMain(加成%, 费率‰)；
    加成对齐 #bZ1（下拉里没有的值动态补一项），费率与险别算出的不同时
    写 #bZ2 并标记为手填，免得险别一改就被覆盖。
"""
import io

# ---------------- 函电侧 ----------------
PL = "D:/pocib-helper/app/_letters_src.html"
s = io.open(PL, encoding="utf-8", newline=None).read()
assert "applyInsFromMain" not in s, "函电侧已打过补丁"

old = '''/* 基本险 / 特殊附加险变化 → 重算总保费率并刷新预算与参考报价 */
["bInsBase","bInsWar","bInsStrike"].forEach(id=>{
  const el=document.getElementById(id); if(!el) return;
  el.addEventListener("change",()=>{
    setv("bZ2", insRateCalc()+"%");
    if(document.getElementById("bResult").style.display==="block") calcBudget();
    refQuote();
  });
});'''

new = '''/* ---- 保险费：加成 / 费率 与主面板双向同步 ----
   主面板「交易剖面 · 运费与保险」的「加成 %」「费率 ‰」和这里是同一笔交易的两个视图。
   以前只做了主面板→函电（而且根本没推这两项），在函电里改险别，切回主面板还是旧值。
   INS_MANUAL=true 表示费率是主面板手填进来的，险别再变化时不再覆盖它。 */
let INS_MANUAL=false, INS_HOLD=false;

function notifyIns(){
  if(INS_HOLD) return;
  try{
    const P=window.parent;
    if(P && P!==window && typeof P.LETTERS_ADOPT_INS==="function"){
      const up=parseFloat(document.getElementById("bZ1").value)||0;
      P.LETTERS_ADOPT_INS(up, insRateCalc());
    }
  }catch(e){}
}

/* 主面板推过来：up 是加成小数（1.1），rate 是总费率（‰） */
function applyInsFromMain(up, rate){
  INS_HOLD=true;
  try{
    const z1=document.getElementById("bZ1");
    if(z1 && up>0){
      const v=String(Math.round(up*100)/100);
      if(![...z1.options].some(o=>Number(o.value)===Number(v))){
        /* 主面板填了 105% 这种下拉里没有的数，补一项并选中 */
        const o=document.createElement("option");
        o.value=v; o.textContent=Math.round(up*100)+"%（手填）";
        z1.appendChild(o);
      }
      z1.value=v;
    }
    const calc=insRateCalc();
    if(Math.abs(calc-(+rate||0))>0.005){
      INS_MANUAL=true;
      setv("bZ2", (Math.round(rate*100)/100)+"%");
    }else if(INS_MANUAL){
      /* 主面板的值又和险别算出来的一致了，恢复自动 */
      INS_MANUAL=false;
      setv("bZ2", calc+"%");
    }
    if(document.getElementById("bResult").style.display==="block") calcBudget();
    refQuote();
  }catch(e){}
  finally{ setTimeout(()=>{ INS_HOLD=false; }, 60); }
}
window.applyInsFromMain=applyInsFromMain;

/* 基本险 / 特殊附加险变化 → 重算总保费率并刷新预算与参考报价 */
["bInsBase","bInsWar","bInsStrike"].forEach(id=>{
  const el=document.getElementById(id); if(!el) return;
  el.addEventListener("change",()=>{
    INS_MANUAL=false;                    /* 用户自己选了险别，费率回到自动 */
    setv("bZ2", insRateCalc()+"%");
    if(document.getElementById("bResult").style.display==="block") calcBudget();
    refQuote();
    notifyIns();                         /* 回传主面板「费率 ‰」 */
  });
});

/* 投保加成改了也回传，主面板「加成 %」跟着变 */
(function bindInsAdd(){
  const el=document.getElementById("bZ1"); if(!el) return;
  const push=()=>notifyIns();
  el.addEventListener("change",push);
  el.addEventListener("input",push);
})();'''

assert old in s, "找不到险别事件绑定"
s = s.replace(old, new, 1)
io.open(PL, "w", encoding="utf-8", newline="\r\n").write(s)
print("函电侧完成")

# ---------------- 主面板侧 ----------------
PM = "D:/pocib-helper/app/index.html"
h = io.open(PM, encoding="utf-8", newline=None).read()
assert "LETTERS_ADOPT_INS" not in h, "主面板侧已打过补丁"

# 1) 新增桥接函数，放在 LETTERS_ADOPT_DEAL 之后
anchor = "window.LETTERS_ADOPT_DEAL=adoptDeal;"
assert anchor in h
ins_bridge = anchor + '''
/* 函电里改投保加成 / 险别 → 回传主程序「交易剖面 · 运费与保险」的加成与费率。
   up 是加成小数（1.1 = 110%），rate 是总保费率（‰）。 */
function adoptIns(up, rate){
  if(!liveOn()) return -1;
  const num=v=>{ const n=parseFloat(String(v==null?"":v)); return isFinite(n)?n:NaN; };
  const u=num(up), r=num(rate);
  const curM=+$("markup").value||0, curR=+$("rate").value||0;
  const nM = u>0 ? Math.round(u*10000)/100 : curM;      /* 1.1 → 110 */
  const nR = r>0 ? Math.round(r*100)/100 : curR;
  if(Math.abs(nM-curM)<1e-6 && Math.abs(nR-curR)<1e-6) return 0;
  $("markup").value = nM;
  $("rate").value = nR;
  LSYNC_HOLD=Date.now()+1500;      /* 这次以函电为准，别马上把主面板旧值推回去 */
  compute();
  return 1;
}
window.LETTERS_ADOPT_INS=adoptIns;'''
h = h.replace(anchor, ins_bridge, 1)

# 2) bridgeToLetters 里推过去（放在税率之后，autoFactoryPrice 之前）
anchor2 = '''  // 税率：函电预算里的进口税率 / 增值税 / 消费税 / 退税按当前商品的 HS 码自动带
  if(w && typeof w.applyTaxFromGoods==="function"){ try{ w.applyTaxFromGoods(); }catch(e){} }'''
assert anchor2 in h
ins_push = '''  // 保险费：加成与费率推给函电（函电侧改了会回传，两边保持同一笔交易的口径）
  if(w && typeof w.applyInsFromMain==="function"){
    try{ w.applyInsFromMain((+$("markup").value||0)/100, +$("rate").value||0); }catch(e){}
  }
''' + anchor2
h = h.replace(anchor2, ins_push, 1)

io.open(PM, "w", encoding="utf-8", newline=None).write(h)
print("主面板侧完成")
