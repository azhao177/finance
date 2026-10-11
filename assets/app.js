'use strict';
const $ = id => document.getElementById(id);
const csrf = document.querySelector('meta[name="csrf-token"]').content;
let data = null, mode = 'monthly', activeCategory = '', activeSub = '', activeKind = '', staged = null, mappingControls = null;
const money = cents => new Intl.NumberFormat('zh-CN', {style:'currency',currency:$('currency').value || 'CAD'}).format(cents/100);
const el = (tag, text, cls) => {const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;};
const notice = message => {$('notice').textContent=message;};
async function api(path, options={}) {
  const headers = {'X-CSRF-Token':csrf,...options.headers};
  if(options.body && !(options.body instanceof FormData)) {headers['Content-Type']='application/json';options.body=JSON.stringify(options.body);}
  const response=await fetch(path,{...options,headers});
  if(response.status===401){location.href='/login';throw new Error('登录已过期');}
  const result=await response.json();if(!response.ok)throw new Error(result.error || '加载失败，请重试');return result;
}
function options(select, entries, selected) {select.replaceChildren(...entries.map(([value,label])=>{const o=el('option',label);o.value=value;return o;}));if(entries.some(e=>e[0]===selected))select.value=selected;}
async function reload() {
  data=await api('/api/data');
  const prior=$('account').value, currency=$('currency').value;
  options($('account'),[['','全部账户'],...data.accounts.map(a=>[a.id,a.name])],prior);
  options($('currency'),[...new Set(data.accounts.map(a=>a.currency))].sort().map(c=>[c,c]),currency);
  if(!$('currency').options.length)options($('currency'),[['CAD','CAD']], 'CAD');
  options($('import-account'),data.accounts.map(a=>[a.id,`${a.name} · ${a.currency}`]),$('import-account').value);
  rebuildPeriods();render();renderSettings();
}
function baseRows(){return data.transactions.filter(t=>(!$('account').value||t.account_id===$('account').value)&&t.currency===$('currency').value);}
function rebuildPeriods(){
  const prior=$('period').value;
  const values=[...new Set(baseRows().map(t=>t.transaction_date.slice(0,mode==='monthly'?7:4)))].sort().reverse();
  options($('period'),values.length?values.map(v=>[v,mode==='monthly'?v.replace('-',' 年 ')+' 月':v+' 年']):[['','暂无记录']],prior);
}
function rangeRows(){const period=$('period').value;return baseRows().filter(t=>period&&t.transaction_date.startsWith(period));}
function totals(rows){const result={income:0,expense:0,pending:0};for(const k of Object.keys(data.types))result[k]=0;for(const r of rows)result[r.status==='pending'?'pending':r.type]+=r.amount;result.balance=result.income-result.expense;return result;}
function render(){
  const rows=rangeRows(), sums=totals(rows), period=$('period').value;
  for(const key of ['income','expense','balance'])$(key).textContent=money(sums[key]);
  const dates=rows.map(t=>t.transaction_date).sort();
  $('range-title').textContent=period?(mode==='monthly'?`${period} 月度账目`:`${period} 年累计 · 已导入交易至 ${dates.at(-1)}`):'暂无账目';
  $('monthly').setAttribute('aria-pressed',String(mode==='monthly'));$('yearly').setAttribute('aria-pressed',String(mode==='yearly'));
  $('special').replaceChildren();
  for(const [kind,title] of [...Object.entries(data.types).filter(([k])=>!['income','expense'].includes(k)),['pending','Pending']]){
    const b=el('button');b.append(el('span',title),el('strong',money(sums[kind]||0)));
    b.addEventListener('click',()=>{activeKind=kind;activeCategory='';activeSub='';renderTransactions();$('transactions-title').scrollIntoView({block:'start'});});$('special').append(b);
  }
  renderCoverage(rows);renderCategories(rows);renderTransactions();renderTrend();
  if(!data.accounts.length)notice('欢迎。先在「账户与分类」添加独立账户，再导入自己的文件；examples/demo.csv 是完全虚构的可选演示。');
}
function renderCoverage(rows){
  const content=$('coverage-content');content.replaceChildren();
  const relevant=data.accounts.filter(a=>(!$('account').value||a.id===$('account').value)&&a.currency===$('currency').value);
  const dates=rows.map(t=>t.transaction_date).sort();
  content.append(el('p',dates.length?`观察到交易日期：${dates[0]} — ${dates.at(-1)}。交易日期不等于完整资料覆盖。`:'当前范围无交易；不能推断没有消费。','muted'));
  const ul=el('ul');let missing=0;
  const period=$('period').value;
  for(const account of relevant){
    const files=data.files.filter(f=>f.account_id===account.id);
    const ranges=files.filter(f=>f.coverage_start&&f.coverage_end);
    let gaps=[];
    if(period){const start=period+(mode==='monthly'?'-01':'-01-01');let end;
      if(mode==='monthly'){const [y,m]=period.split('-').map(Number);end=period+'-'+new Date(Date.UTC(y,m,0)).getUTCDate();}
      else end=dates.at(-1)||period+'-12-31';
      let cursor=start,open=null;
      while(cursor<=end){const covered=ranges.some(f=>f.coverage_start<=cursor&&f.coverage_end>=cursor);if(!covered&&!open)open=cursor;
        if(covered&&open){const d=new Date(cursor+'T12:00:00Z');d.setUTCDate(d.getUTCDate()-1);gaps.push(open+' — '+d.toISOString().slice(0,10));open=null;}
        const next=new Date(cursor+'T12:00:00Z');next.setUTCDate(next.getUTCDate()+1);cursor=next.toISOString().slice(0,10);
      }if(open)gaps.push(open+' — '+end);
    }
    if(gaps.length||!files.length)missing++;
    ul.append(el('li',`${account.name}：${ranges.length?ranges.map(f=>`${f.coverage_start} — ${f.coverage_end}`).join('；'):'覆盖范围未知'}。${gaps.length?'缺失／未确认：'+gaps.join('；'):'当前范围无已声明覆盖缺口'}。${files.filter(f=>!f.coverage_start).length} 个文件未填写覆盖范围。`));
  }
  content.append(ul,el('p','覆盖声明不等于审核完成；按账户分别核对，不以 statement 周期替代交易月份。','muted'));
  $('coverage-count').textContent=missing?`· ${missing} 个账户资料缺失／未知`:'· 以文件声明为准';
}
function expenseGroups(rows){const map=new Map();for(const r of rows.filter(t=>t.type==='expense'&&t.status==='posted'))map.set(r.category,(map.get(r.category)||0)+r.amount);return [...map].sort((a,b)=>b[1]-a[1]);}
function renderCategories(rows){
  const groups=expenseGroups(rows), total=groups.reduce((sum,r)=>sum+r[1],0),list=$('category-list'),svg=$('pie');list.replaceChildren();svg.replaceChildren();
  if(!total){list.append(el('div','当前范围没有已入账消费。可导入文件或调整筛选。','empty'));const t=document.createElementNS('http://www.w3.org/2000/svg','text');t.setAttribute('x','240');t.setAttribute('y','200');t.setAttribute('text-anchor','middle');t.textContent='暂无消费';svg.append(t);$('drill').hidden=true;return;}
  let start=-Math.PI/2;const ns='http://www.w3.org/2000/svg';const labels=[];
  for(const [name,amount] of groups){
    const pct=amount/total, end=start+pct*Math.PI*2, middle=(start+end)/2, color=data.categories.find(c=>c.name===name)?.color||'#d3dce0';
    const polar=(a,r)=>[240+Math.cos(a)*r,200+Math.sin(a)*r];
    const path=document.createElementNS(ns,'path');
    if(pct===1)path.setAttribute('d','M240 80 A120 120 0 1 1 239.99 80 Z');
    else{const p1=polar(start,120),p2=polar(end,120);path.setAttribute('d',`M240 200 L${p1.join(' ')} A120 120 0 ${pct>.5?1:0} 1 ${p2.join(' ')} Z`);}
    path.setAttribute('fill',color);path.setAttribute('tabindex','0');path.setAttribute('role','button');path.setAttribute('aria-label',`${name} ${money(amount)} ${(pct*100).toFixed(1)}%，展开二级分类`);
    const title=document.createElementNS(ns,'title');title.textContent=`${name} ${(pct*100).toFixed(1)}%`;path.append(title);
    const open=()=>selectCategory(name);path.addEventListener('click',open);path.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();open();}});svg.append(path);
    if(pct>=.03){const [x,y]=polar(middle,142);labels.push({name,pct,x,y,side:x<240?'left':'right',anchor:polar(middle,122)});}
    const button=el('button');const swatch=el('span',undefined,'swatch');swatch.style.backgroundColor=color;swatch.setAttribute('aria-hidden','true');button.append(swatch,el('span',name),el('strong',money(amount)),el('span',(pct*100).toFixed(1)+'%','pct'));button.addEventListener('click',open);list.append(button);start=end;
  }
  // Separate labels on each side, bounded within the viewBox; small sectors have no label or leader.
  for(const side of ['left','right']){
    const group=labels.filter(l=>l.side===side).sort((a,b)=>a.y-b.y);
    group.forEach((l,i)=>l.y=Math.max(22+i*44,l.y,i?group[i-1].y+44:22));
    for(let i=group.length-1;i>=0;i--)group[i].y=Math.min(378-(group.length-1-i)*44,group[i].y);
    for(const l of group){const x=side==='left'?112:368;
      const line=document.createElementNS(ns,'line');for(const [k,v] of Object.entries({x1:l.anchor[0],y1:l.anchor[1],x2:x,y2:l.y}))line.setAttribute(k,v);svg.append(line);
      const t=document.createElementNS(ns,'text');t.setAttribute('x',x+(side==='left'?-4:4));t.setAttribute('y',l.y+4);t.setAttribute('text-anchor',side==='left'?'end':'start');
      const a=document.createElementNS(ns,'tspan');a.setAttribute('x',x+(side==='left'?-4:4));a.textContent=l.name.length>5?l.name.slice(0,5)+'…':l.name;
      const b=document.createElementNS(ns,'tspan');b.setAttribute('x',x+(side==='left'?-4:4));b.setAttribute('dy','18');b.textContent=(l.pct*100).toFixed(1)+'%';t.append(a,b);svg.append(t);
    }
  }
  renderDrill();
}
function selectCategory(name){activeCategory=name;activeSub='';activeKind='';renderDrill();renderTransactions();}
function renderDrill(){
  const d=$('drill');d.replaceChildren();d.hidden=!activeCategory;if(!activeCategory)return;
  const groups=new Map();for(const t of rangeRows().filter(t=>t.type==='expense'&&t.status==='posted'&&t.category===activeCategory))groups.set(t.subcategory,(groups.get(t.subcategory)||0)+t.amount);
  d.append(el('h3',`${activeCategory} · ${money([...groups.values()].reduce((a,b)=>a+b,0))}`));
  for(const [sub,amount] of [...groups].sort((a,b)=>b[1]-a[1])){const b=el('button',`${sub} · ${money(amount)}`);b.setAttribute('aria-pressed',String(activeSub===sub));b.addEventListener('click',()=>{activeSub=sub;renderDrill();renderTransactions();$('transactions-title').scrollIntoView({block:'start'});});d.append(b);}
}
function renderTransactions(){
  const query=$('search').value.trim().toLowerCase();let rows=rangeRows().filter(t=>!query||[t.description,t.category,t.subcategory,t.notes,t.id].join(' ').toLowerCase().includes(query));
  if(activeKind)rows=rows.filter(t=>activeKind==='pending'?t.status==='pending':t.type===activeKind&&t.status==='posted');
  if(activeCategory)rows=rows.filter(t=>t.type==='expense'&&t.status==='posted'&&t.category===activeCategory&&(!activeSub||t.subcategory===activeSub));
  const sort=$('sort').value;rows.sort((a,b)=>(sort.startsWith('date')?a.transaction_date.localeCompare(b.transaction_date):a.amount-b.amount)*(sort.endsWith('desc')?-1:1));
  $('transactions-title').textContent='交易明细'+(activeKind?' · '+(data.types[activeKind]||'Pending'):activeCategory?' · '+activeCategory+(activeSub?' / '+activeSub:''):'');
  $('transaction-count').textContent=`${rows.length} 笔`;const container=$('transaction-list');container.replaceChildren();
  if(!rows.length){container.append(el('div','没有符合条件的记录。可调整搜索、月份或账户，或导入资料。','empty'));return;}
  for(const t of rows){const b=el('button',undefined,'transaction-row');const desc=el('div');desc.append(el('span',t.description,'description'),el('small',`${t.account} · ${t.category} / ${t.subcategory} · ${data.types[t.type]}${t.status==='pending'?' · Pending':''}`));
    b.append(el('span',t.transaction_date,'date'),desc,el('span',money(t.amount),'amount'));b.addEventListener('click',()=>openDetail(t));container.append(b);}
}
function renderTrend(){
  $('trend-section').hidden=mode!=='yearly';if(mode!=='yearly')return;const target=$('trend');target.replaceChildren();const year=$('period').value;if(!year)return;
  const rows=rangeRows(), max=Math.max(1,...Array.from({length:12},(_,i)=>totals(rows.filter(t=>t.transaction_date.slice(5,7)===String(i+1).padStart(2,'0'))).expense));
  for(let i=1;i<=12;i++){const month=String(i).padStart(2,'0'),r=rows.filter(t=>t.transaction_date.slice(5,7)===month),s=totals(r);const cell=el('div',undefined,'trend-cell');cell.append(el('span',`${i} 月`));if(r.length){cell.append(el('strong','消费 '+money(s.expense)));const bar=el('div',undefined,'trend-bar');bar.style.width=Math.max(1,s.expense/max*100)+'%';cell.append(bar,el('span','收入 '+money(s.income)));}else cell.append(el('p','资料缺失／无记录'));target.append(cell);}
}
function categoryFields(category,subcategory){
  const wrapper=el('div',undefined,'two-col'),catLabel=el('label','大类'),subLabel=el('label','二级分类'),cat=el('select'),sub=el('select');cat.name='category';sub.name='subcategory';
  options(cat,data.categories.map(c=>[c.name,c.name]),category);const fill=()=>options(sub,(data.categories.find(c=>c.name===cat.value)?.children||[]).map(c=>[c,c]),subcategory);fill();cat.addEventListener('change',fill);catLabel.append(cat);subLabel.append(sub);wrapper.append(catLabel,subLabel);return {wrapper,cat,sub};
}
function typeSelect(type){const label=el('label','交易类型'),select=el('select');select.name='type';options(select,type==='unconfirmed'?[['unconfirmed','待确认：请选择明确类型'],...Object.entries(data.types)]:Object.entries(data.types),type);label.append(select);return {label,select};}
function openDetail(t){
  const content=$('detail-content');content.replaceChildren();const dl=el('dl');
  for(const [name,value] of [['稳定 ID',t.id],['交易日期',t.transaction_date],['入账日期',t.posting_date||'未提供'],['账户',t.account],['原始描述',t.description],['账单本币',`${t.currency} ${(t.amount/100).toFixed(2)}`],['原币',t.original_currency?`${t.original_currency} ${(t.original_amount/100).toFixed(2)}`:'未提供'],['状态',t.status],['分类来源',t.manual?'手工修改（优先保留）':'导入／规则']])dl.append(el('dt',name),el('dd',value));content.append(dl);
  const sources=el('div');sources.append(el('h3','来源文件'));for(const s of t.sources){const p=el('p');const a=el('a',s.name);a.href='/files/'+s.file_id;p.append(a,el('span',` · ${s.page?'页 '+s.page+' · ':''}行 ${s.line}`));sources.append(p);}content.append(sources);
  const form=el('form'),fields=categoryFields(t.category,t.subcategory),type=typeSelect(t.type);form.append(type.label,fields.wrapper);const noteLabel=el('label','备注'),notes=el('textarea');notes.value=t.notes;noteLabel.append(notes);form.append(noteLabel);
  const ruleLabel=el('label',undefined,'checkbox'),rule=el('input');rule.type='checkbox';ruleLabel.append(rule,el('span','明确建立未来规则：只匹配完全相同原始描述'));form.append(ruleLabel,el('p','默认只修改这笔，不影响同商户其他记录。','muted'));
  const save=el('button','保存修改','primary');save.type='submit';const error=el('p',undefined,'error');error.setAttribute('role','alert');form.append(save,error);
  form.addEventListener('submit',async e=>{e.preventDefault();save.disabled=true;try{await api('/api/transactions/'+t.id,{method:'PATCH',body:{category:fields.cat.value,subcategory:fields.sub.value,type:type.select.value,notes:notes.value,future_rule:rule.checked}});$('detail-dialog').close();await reload();notice('已保存，月度、年度、分类和下一次 Excel 导出已同步。');}catch(e){error.textContent=e.message;}finally{save.disabled=false;}});content.append(form);$('detail-dialog').showModal();$('detail-dialog').scrollTop=0;
}
function renderSettings(){
  $('settings-accounts').replaceChildren(...data.accounts.map(a=>el('p',`${a.name} · ${a.kind} · ${a.currency}`,'muted')));
  $('category-names').replaceChildren(...data.categories.map(c=>{const o=el('option');o.value=c.name;return o;}));
  $('rules-list').replaceChildren();for(const r of data.rules){const p=el('div',undefined,'compact-list');p.append(el('p',`${r.description} → ${r.category} / ${r.subcategory} · ${data.types[r.type]}`));const b=el('button','删除未来规则');b.addEventListener('click',async()=>{try{await api('/api/rules/'+r.id,{method:'DELETE'});await reload();}catch(e){$('settings-error').textContent=e.message;}});p.append(b);$('rules-list').append(p);}if(!data.rules.length)$('rules-list').append(el('p','尚无自动规则。','muted'));
}
for(const [formId,path] of [['account-form','/api/accounts'],['category-form','/api/categories']])$(formId).addEventListener('submit',async e=>{e.preventDefault();const b=e.target.querySelector('button');b.disabled=true;try{await api(path,{method:'POST',body:Object.fromEntries(new FormData(e.target))});e.target.reset();if(formId==='account-form')e.target.currency.value='CAD';await reload();$('settings-error').textContent='已保存';}catch(e){$('settings-error').textContent=e.message;}finally{b.disabled=false;}});
function renderMapping(headers, aliases={}) {
  const box=$('import-mapping');box.hidden=false;box.replaceChildren();mappingControls={columns:{}};
  box.append(el('h3','选择文件各列的含义'),el('p','只映射列含义，不修改原文件。未知收支类型会要求逐笔确认；不会根据商户名称或金额符号自行分类。','muted'));
  if(headers.length===1)box.append(el('p','只读到一列：请检查 CSV 分隔符，选择逗号、Tab 或分号后重新读取标题。','error'));
  const labels={transaction_date:'交易日期（必选）',posting_date:'入账日期（缺失可留空）',description:'原始描述（必选）',amount:'账单本币金额（必选）',currency:'本币（留空使用账户币种）',type:'交易类型列（可逐笔确认）',status:'状态列（posted／pending）',external_id:'银行稳定交易 ID',original_amount:'原币金额',original_currency:'原币币种',category:'大类',subcategory:'二级分类',notes:'备注'};
  const required=['transaction_date','description','amount'];
  const grid=el('div',undefined,'two-col');
  for(const [key,title] of Object.entries(labels)){
    const label=el('label',title),select=el('select');select.id='map-'+key;select.name='map-'+key;select.required=required.includes(key);
    const selected=headers.find(h=>(aliases[h]||h)===key)||'';
    options(select,[['',required.includes(key)?'请选择来源列':'未提供／不使用此列'],...headers.map(h=>[h,h])],selected);label.append(select);grid.append(label);mappingControls.columns[key]=select;
  }
  box.append(grid);
  function setting(key,title,entries,selected){const label=el('label',title),select=el('select');select.id='map-'+key;options(select,entries,selected);label.append(select);box.append(label);mappingControls[key]=select;}
  setting('date_format','日期格式（请按原文件确认，不猜月／日）',[['iso','YYYY-MM-DD'],['ymd_slash','YYYY/MM/DD'],['mdy','MM/DD/YYYY（月／日／年）'],['dmy','DD/MM/YYYY（日／月／年）']],'iso');
  setting('amount_mode','金额方向模式',[['positive','全部为正数，方向由类型确定'],['signed','正负金额：保留原件，将绝对金额入账']],'positive');
  const kinds=[['unconfirmed','逐笔确认，不自动判断'],...Object.entries(data.types)];
  setting('type_default','没有选择类型列时，统一类型（混合账单请逐笔确认）',kinds,'unconfirmed');
  const directions=el('div',undefined,'two-col');
  for(const [key,title] of [['positive_type','正数表示'],['negative_type','负数表示']]){const label=el('label',title),select=el('select');select.id='map-'+key;options(select,kinds,'unconfirmed');label.append(select);directions.append(label);mappingControls[key]=select;}
  box.append(directions,el('p','明确类型列优先于正负号规则。银行的正负惯例不同；还款、退款、转账不能都当消费。日期须含四位年份，金额须为不含货币符号和千分位的数字。','muted'));
  mappingControls.amount_mode.addEventListener('change',()=>directions.hidden=mappingControls.amount_mode.value!=='signed');directions.hidden=true;
  box.append(el('p','选好后点击下方「解析并预览」，核对每笔记录，再确认入账。','muted'));
}
function importPayload(inspect=false){
  const body=new FormData($('import-form'));
  if(inspect)body.set('inspect','1');
  else if(mappingControls){const mapping={columns:Object.fromEntries(Object.entries(mappingControls.columns).map(([k,s])=>[k,s.value]))};for(const key of ['date_format','amount_mode','type_default','positive_type','negative_type'])mapping[key]=mappingControls[key].value;body.set('mapping',JSON.stringify(mapping));}
  return body;
}
async function parseImport(inspect=false){
  const form=$('import-form'),button=inspect?$('inspect-columns'):form.querySelector('button[type=submit]');button.disabled=true;$('import-error').textContent='';$('import-preview').hidden=true;staged=null;
  try{
    const result=await api('/api/import/preview',{method:'POST',body:importPayload(inspect)});
    if(result.duplicate_file){$('import-error').textContent='该账户已导入完全相同文件，没有增加交易。';return;}
    if(result.mapping_required){renderMapping(result.headers,result.aliases);return;}
    staged=result;renderPreview();
  }catch(e){$('import-error').textContent=e.message;}finally{button.disabled=false;}
}
$('import-form').addEventListener('submit',e=>{e.preventDefault();parseImport();});
$('inspect-columns').addEventListener('click',()=>parseImport(true));
$('import-form').addEventListener('change',e=>{staged=null;$('import-preview').hidden=true;if(e.target.type==='file'||e.target.id==='csv-delimiter'){mappingControls=null;$('import-mapping').hidden=true;$('import-mapping').replaceChildren();}});
function renderPreview(){
  const target=$('import-preview');target.hidden=false;target.replaceChildren();const summary=staged.summary.totals;
  target.append(el('h3',`${staged.rows.length} 笔 · 待核对`),el('p',`仅已确认类型的文件行小计（含重复，非入账增量）：收入 ${money(summary.income)}；消费 ${money(summary.expense)}；pending ${money(summary.pending)}。${summary.unconfirmed||0} 笔类型待确认，未计入上述小计。`),el('p',staged.warning,'muted'));
  const form=el('form'),controls=[];
  staged.rows.forEach((r,i)=>{const panel=el('div',undefined,'preview-row');const titles={new:'新增',duplicate:'重复：保留原 ID 与手工修改',update:'临时 → 正式：保留原 ID',review:'银行 ID 信息变化：须确认'};
    panel.append(el('p',`${r.transaction_date} · ${r.description} · ${r.currency} ${(r.amount/100).toFixed(2)}`),el('p',`${titles[r.action]} · ${r.status} · ${r.page?'页 '+r.page+' · ':''}行 ${r.line}`,'muted'));
    if(r.type==='unconfirmed')panel.append(el('p',`原文件类型：${r.original_type||'未提供'}。必须选择明确类型或跳过，不能直接入账。`,'error'));
    const fields=categoryFields(r.category,r.subcategory),type=typeSelect(r.type);panel.append(type.label,fields.wrapper);
    const skipLabel=el('label',undefined,'checkbox'),skip=el('input');skip.type='checkbox';skipLabel.append(skip,el('span','跳过此行'));panel.append(skipLabel);
    let match=null,confirm=null;
    if(r.candidates.length){const label=el('label','临时记录匹配'),select=el('select');options(select,[['','确认为独立新记录'],...r.candidates.map(c=>[c.id,`${c.transaction_date} ${c.description} · ${c.id}`])]);label.append(select);panel.append(label);match=select;}
    if(r.action==='review'||r.candidates.length){const label=el('label',undefined,'checkbox');confirm=el('input');confirm.type='checkbox';label.append(confirm,el('span','已核对上述信息，同意所选处理'));panel.append(label);}
    controls.push({fields,type,skip,match,confirm});form.append(panel);
  });
  const commit=el('button','确认核对并追加到账本','primary');commit.type='submit';form.append(commit);form.addEventListener('submit',async e=>{e.preventDefault();commit.disabled=true;try{
    const decisions={};controls.forEach((c,i)=>{const d={},r=staged.rows[i];if(c.skip.checked)d.skip=true;if(c.match?.value)d.match_id=c.match.value;if(c.confirm?.checked)d.confirm=true;for(const [k,v] of [['category',c.fields.cat.value],['subcategory',c.fields.sub.value],['type',c.type.select.value]])if(v!==r[k])d[k]=v;if(Object.keys(d).length)decisions[i]=d;});
    const result=await api('/api/import/commit',{method:'POST',body:{token:staged.token,decisions}});$('import-dialog').close();await reload();notice(`导入完成：新增 ${result.added}，更新 ${result.updated}，重复 ${result.duplicates}。`);staged=null;target.hidden=true;
  }catch(e){$('import-error').textContent=e.message;$('import-error').scrollIntoView({block:'center'});}finally{commit.disabled=false;}});target.append(form);
}
$('open-import').addEventListener('click',()=>{if(!data.accounts.length){$('settings-dialog').showModal();$('settings-error').textContent='先添加独立账户，再导入文件。';return;}$('import-dialog').showModal();});
$('open-settings').addEventListener('click',()=>$('settings-dialog').showModal());
document.querySelectorAll('[data-close]').forEach(b=>b.addEventListener('click',()=>$(b.dataset.close).close()));
for(const id of ['monthly','yearly'])$(id).addEventListener('click',()=>{mode=id;activeCategory='';activeSub='';activeKind='';rebuildPeriods();render();});
for(const id of ['account','currency'])$(id).addEventListener('change',()=>{if(id==='account'&&$('account').value)$('currency').value=data.accounts.find(a=>a.id===$('account').value).currency;activeCategory='';activeSub='';activeKind='';rebuildPeriods();render();});
$('period').addEventListener('change',()=>{activeCategory='';activeSub='';activeKind='';render();});
for(const id of ['search','sort'])$(id).addEventListener(id==='search'?'input':'change',renderTransactions);
$('clear-drill').addEventListener('click',()=>{activeCategory='';activeSub='';activeKind='';renderDrill();renderTransactions();});
reload().catch(e=>{notice('账本加载失败：'+e.message);const retry=el('button','重新加载');retry.addEventListener('click',()=>location.reload());$('notice').append(retry);});
