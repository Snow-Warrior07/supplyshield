import {run,check} from './engine.mjs';
import {defaults,validateSettings,settingsFromURL,scenarioURL,orderRows,materialRows,csv} from './lab.mjs';

const $=id=>document.getElementById(id);
const money=n=>new Intl.NumberFormat('en-US',{style:'currency',currency:'JPY',maximumFractionDigits:0}).format(n);
const percent=n=>n===null?'N/A':`${(n*100).toFixed(1)}%`;
const escape=value=>String(value).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#39;');
const storageKey='supplyshield-scenarios-v2';
let source,reference,result,experiments,selectedPolicy=2,activeNode={type:'supplier',id:'S01'},timer;
let dirty=true,compareGeneration=0,experimentGeneration=0,saved=[];
const actionIds=['save','share','download-report','download-json','download-purchases','download-orders','explore-run','selftest'];

class Planner {
  cancel(){if(this.worker)this.worker.terminate();this.worker=null;
    if(this.reject)this.reject(new Error('Cancelled'));this.reject=null;}
  execute(payload,onProgress){this.cancel();return new Promise((resolve,reject)=>{
    this.reject=reject;
    const worker=this.worker=new Worker(new URL('./planner-worker.mjs?v=2',import.meta.url),{type:'module'});
    const cleanup=()=>{worker.terminate();if(this.worker===worker){this.worker=null;this.reject=null;}};
    worker.onmessage=({data})=>{if(data.progress!==undefined){onProgress?.(data.progress);return;}
      cleanup();data.error?reject(new Error(data.error)):resolve(data.result);};
    worker.onerror=()=>{cleanup();reject(new Error('The planning worker could not start. Reload the page or check that all project files are available.'));};
    worker.postMessage({...payload,id:1});
  });}
}
const planner=new Planner(),experimentPlanner=new Planner();

function inputs(){
  for(const id of ['budget','assembly'])if($(id).value.trim()==='')throw new Error('Enter a budget and assembly capacity, including zero if appropriate.');
  return validateSettings(source,{supplier:$('supplier').value,kind:$('kind').value,
    capacity_percent:Number($('capacity').value),delay_days:Number($('delay').value),budget:Number($('budget').value),
    assembly_capacity:Number($('assembly').value),demand_percent:Number($('demand').value)});
}
function putInputs(s){$('supplier').value=s.supplier;$('kind').value=s.kind;$('capacity').value=s.capacity_percent;
  $('delay').value=s.delay_days;$('budget').value=s.budget;$('assembly').value=s.assembly_capacity;
  $('demand').value=s.demand_percent;syncControls();}
function syncControls(){
  $('cap-value').textContent=$('capacity').value+'%';$('delay-value').textContent=$('delay').value+' days';
  $('demand-value').textContent=$('demand').value+'%';$('capacity-control').hidden=$('kind').value!=='capacity';
  $('delay-control').hidden=$('kind').value!=='delay';
}
function scenarioName(s){
  if(s.kind==='none')return 'No supplier disruption';
  if(s.kind==='outage')return s.supplier==='S01'?'Main chip supplier outage':s.supplier==='S08'?'Sole-source seal outage':`${s.supplier} supplier outage`;
  if(s.kind==='delay')return `${s.supplier} delayed by ${s.delay_days} days`;
  return `${s.supplier} at ${s.capacity_percent}% capacity`;
}
function available(ready){for(const id of actionIds)$(id).disabled=!ready;
  document.querySelectorAll('.policy-card').forEach(b=>b.disabled=!ready);}
function clearExperiments(){experimentGeneration++;experimentPlanner.cancel();experiments=null;
  $('explore-results').hidden=true;$('explore-run').disabled=dirty||!result;
  $('explore-status').textContent='Run experiments to calculate six budget choices and 50 possible futures.';}
function markDirty(){dirty=true;available(false);$('verification').classList.add('pending');
  $('verification').textContent='Inputs changed';$('run-state').textContent='Inputs changed. Compare to refresh the displayed plans.';}
function changed(){syncControls();document.querySelectorAll('[data-preset]').forEach(b=>b.classList.remove('active'));
  markDirty();clearExperiments();clearTimeout(timer);planner.cancel();compareGeneration++;$('results').setAttribute('aria-busy','false');$('run').disabled=false;
  if($('auto-run').checked)timer=setTimeout(compare,350);}

async function compare(){
  clearTimeout(timer);const generation=++compareGeneration;planner.cancel();clearExperiments();
  markDirty();$('results').setAttribute('aria-busy','true');$('run').disabled=true;
  $('run-state').textContent='Comparing three policies and checking every allocation…';$('verification').textContent='Calculating…';
  try{
    const settings=inputs();
    const next=await planner.execute({type:'compare',source,settings});
    if(generation!==compareGeneration)return;
    result=next;dirty=false;activeNode={type:'supplier',id:settings.supplier};
    render();available(true);
    $('run-state').textContent=`Verified · ${next.metrics[2].seconds.toFixed(3)}s optimization · ${next.metrics[2].demand} demand units`;
    $('verification').classList.remove('pending');$('verification').textContent=`✓ ${next.checks.filter(c=>c.valid).length} / 3 plans verified`;
    $('share-panel').hidden=true;
  }catch(error){if(generation!==compareGeneration||error.message==='Cancelled')return;
    $('run-state').textContent=error.message;$('verification').textContent='Review inputs';}
  finally{if(generation===compareGeneration){$('run').disabled=false;$('results').setAttribute('aria-busy','false');}}
}

function render(){
  const m=result.metrics[selectedPolicy],base=result.metrics[0],s=result.settings;
  $('scenario-title').textContent=scenarioName(s);
  $('scenario-meta').textContent=`${result.case.orders.length} orders · ${m.demand} units · ${money(s.budget)} budget · ${s.demand_percent}% sample demand`;
  const deltas=[`${m.fulfilled} of ${m.demand} units`,`${m.score} weighted units`,`${money(s.budget-m.cost)} budget remains`,`${m.unfulfilled?orderRows(result,selectedPolicy).filter(o=>o.unfilled).length:0} orders with shortfall`];
  $('kpis').innerHTML=[['On-time unit fill',percent(m.fill_rate)],['Priority fulfillment',percent(m.weighted_fill_rate)],
    ['Recovery purchases',money(m.cost)],['Unfilled units',m.unfulfilled]].map(([label,value],i)=>
      `<div class="kpi"><span>${label}</span><strong>${value}</strong><small>${deltas[i]}</small></div>`).join('');
  const optimized=result.metrics[2],greedy=result.metrics[1];
  if(selectedPolicy===2&&greedy.score===optimized.score&&greedy.cost===optimized.cost){
    $('plan-note').textContent='Greedy matches the optimized priority score and cost in this scenario. A tie is a useful result.';
  }else if(selectedPolicy===0){$('plan-note').textContent='Inspecting existing sourcing. This policy can only use the planned suppliers and quantities.';}
  else{$('plan-note').textContent=`Inspecting ${m.policy.toLowerCase()} · ${((m.weighted_fill_rate-base.weighted_fill_rate)*100).toFixed(1)} percentage-point change in priority fulfillment versus existing sourcing.`;}
  $('hero-fill').textContent=percent(optimized.fill_rate);$('hero-ring').style.setProperty('--fill',`${(optimized.fill_rate??0)*100}%`);
  $('hero-scenario').textContent=scenarioName(s);$('hero-summary').textContent=`${optimized.fulfilled} of ${optimized.demand} units fulfilled with ${money(optimized.cost)} in recovery purchases.`;
  $('policy-cards').innerHTML=result.metrics.map((p,i)=>`<button class="policy-card ${i===selectedPolicy?'selected':''}" data-policy="${i}" aria-pressed="${i===selectedPolicy}"><span>${p.policy}</span><strong>${percent(p.fill_rate)}</strong><small>${p.fulfilled}/${p.demand} units · ${money(p.cost)}</small>${i===selectedPolicy?'<em>✓</em>':''}</button>`).join('');
  $('bars').innerHTML=result.metrics.map((p,i)=>`<div class="bar-row"><span>${p.policy}</span><div class="bar-track"><div class="bar ${i===2?'opt':''}" style="width:${(p.fill_rate??0)*100}%"></div></div><span>${percent(p.fill_rate)}</span></div>`).join('');
  $('policy-table').innerHTML=result.metrics.map(p=>`<tr><td>${p.policy}</td><td>${p.fulfilled} / ${p.demand}</td><td>${percent(p.weighted_fill_rate)}</td><td>${money(p.cost)}</td><td><span class="tag ${p.status==='OPTIMAL'?'':'warning'}">${p.status}</span></td></tr>`).join('');
  renderOrders();renderRecovery();renderNetwork();renderChecks();
}

function renderOrders(){if(!result)return;const all=orderRows(result,selectedPolicy),term=$('order-search').value.trim().toLowerCase(),filter=$('order-filter').value;
  const rows=all.filter(o=>(`${o.id} ${o.product} ${o.product_name}`).toLowerCase().includes(term)&&
    (filter==='all'||filter==='unfilled'&&o.unfilled>0||filter==='fulfilled'&&o.unfilled===0));
  $('orders-summary').textContent=`${result.metrics[selectedPolicy].policy} · ${all.filter(o=>o.unfilled).length} of ${all.length} orders have a shortfall. Showing ${rows.length}.`;
  $('order-table').innerHTML=rows.map(o=>`<tr><td>${escape(o.id)}<small>${escape(o.product_name)}</small></td><td>${o.priority}</td><td class="fulfillment-cell">${o.fulfilled} / ${o.quantity}<div class="order-progress" aria-hidden="true"><span style="width:${o.fulfilled/o.quantity*100}%"></span></div></td><td class="${o.unfilled?'shortfall':''}">${o.unfilled||'—'}</td></tr>`).join('')||'<tr><td colspan="4" class="empty-row">No orders match this filter.</td></tr>';
}
function purchases(){const plan=result.plans[selectedPolicy];return result.case.offers.filter(o=>plan.purchases[o.id]>0)
  .map(o=>({supplier:o.supplier,component:o.component,mode:o.mode,units:plan.purchases[o.id],arrival_day:o.lead_days,cost:plan.purchases[o.id]*o.cost}));}
function renderRecovery(){const m=result.metrics[selectedPolicy],rows=purchases();
  $('recommendation').textContent=`${m.policy} fulfills ${m.fulfilled} of ${m.demand} units and ${percent(m.weighted_fill_rate)} of weighted demand. ${m.unfulfilled} units remain unfilled. Review the quantities and arrival assumptions before acting.`;
  $('purchase-summary').innerHTML=[['Selected policy',selectedPolicy===0?'Existing':selectedPolicy===1?'Greedy':'Optimized'],
    ['Suppliers used',new Set(rows.map(o=>o.supplier)).size],['Purchase spend',money(m.cost)]].map(([label,value])=>`<div><span>${label}</span><strong>${value}</strong></div>`).join('');
  $('purchases').innerHTML=rows.map(o=>`<tr><td>${escape(o.supplier)}<small>${escape(o.component)}</small></td><td>${escape(o.mode)}</td><td>${o.units}</td><td>Day ${o.arrival_day}</td><td>${money(o.cost)}</td></tr>`).join('')||'<tr><td colspan="5" class="empty-row">No purchases under this selected plan. Only opening stock is available.</td></tr>';
  $('materials').innerHTML=materialRows(result,selectedPolicy).map(c=>`<tr><td>${escape(c.id)}<small>${escape(c.name)}</small></td><td>${c.stock}</td><td>${c.purchased}</td><td>${c.consumed}</td><td>${c.remaining}</td></tr>`).join('');
}

function exposure(supplier){const parts=new Set(source.offers.filter(o=>o.supplier===supplier).map(o=>o.component));
  return {parts,products:new Set(source.bom.filter(b=>parts.has(b.component)).map(b=>b.product))};}
function renderNetwork(){const affected=result.settings.kind==='none'?{parts:new Set(),products:new Set()}:exposure(result.settings.supplier);
  const pos=new Map(),nodes=[];
  for(const [rows,x,type,width] of [[source.suppliers,35,'supplier',69],[source.components,265,'component',70],[source.products,475,'product',75]]){
    rows.forEach((row,i)=>{const node={...row,x,y:43+i*418/Math.max(1,rows.length-1),type,width};pos.set(row.id,node);nodes.push(node);});
  }
  const edges=[...new Set(source.offers.map(o=>`${o.supplier}|${o.component}`)),...source.bom.map(b=>`${b.component}|${b.product}`)];
  $('graph').innerHTML=`<svg viewBox="0 0 590 495" aria-label="Interactive supplier, component and product network"><text x="28" y="17" font-size="9" fill="#6b7b72">SUPPLIERS</text><text x="246" y="17" font-size="9" fill="#6b7b72">COMPONENTS</text><text x="454" y="17" font-size="9" fill="#6b7b72">PRODUCTS</text>${edges.map(edge=>{const [a,b]=edge.split('|'),p=pos.get(a),q=pos.get(b);const hot=affected.parts.has(b)||affected.parts.has(a)&&affected.products.has(b);return `<path d="M${p.x+p.width} ${p.y} C${p.x+p.width+55} ${p.y},${q.x-55} ${q.y},${q.x} ${q.y}" fill="none" stroke="${hot?'#d8ae93':'#e0e7d8'}" stroke-width="${hot?1.3:.8}"/>`;}).join('')}${nodes.map(n=>{const hot=n.type==='supplier'?n.id===result.settings.supplier&&result.settings.kind!=='none':n.type==='component'?affected.parts.has(n.id):affected.products.has(n.id),selected=activeNode.id===n.id;
    return `<g class="network-node" role="button" tabindex="0" aria-label="Inspect ${n.type} ${escape(n.id)}" data-node-type="${n.type}" data-node-id="${escape(n.id)}"><title>${escape(n.name)}</title><rect x="${n.x}" y="${n.y-8}" width="${n.width}" height="17" rx="4" fill="${hot?'#faf0e5':'#eff4e8'}" stroke="${selected?'#217965':hot?'#d8ae93':'#dce5d3'}" stroke-width="${selected?2:1}"/><circle cx="${n.x+9}" cy="${n.y}" r="2.5" fill="${hot?'#cb7149':'#217965'}"/><text x="${n.x+19}" y="${n.y+3}" font-size="8.5" fill="#143e39">${escape(n.id)}</text></g>`;}).join('')}</svg>`;
  renderInspector();
  $('parts').innerHTML=`<div class="component-pills">${materialRows(result,selectedPolicy).map(c=>`<span><b>${escape(c.id)}</b>${c.consumed} allocated / ${c.stock+c.purchased} available</span>`).join('')}</div>`;
}
function renderInspector(){const {type,id}=activeNode;
  if(type==='supplier'){const supplier=source.suppliers.find(s=>s.id===id),offers=result.case.offers.filter(o=>o.supplier===id),parts=[...new Set(offers.map(o=>o.component))],dependent=exposure(id);
    $('node-inspector').innerHTML=`<span class="small-label">SUPPLIER / ${escape(id)}</span><h4>${escape(supplier.name)}</h4><p>${escape(supplier.location)} · display label</p><span class="inspector-value">${parts.length}</span><p>components offered · ${dependent.products.size} dependent SKUs</p><ul class="inspector-list">${parts.map(part=>`<li>${escape(part)} · ${offers.filter(o=>o.component===part&&o.eligible).length} eligible shipping offers</li>`).join('')}</ul><button class="button primary" data-model-supplier="${escape(id)}">Model this supplier ↗</button>`;
  }else if(type==='component'){const component=materialRows(result,selectedPolicy).find(c=>c.id===id),suppliers=new Set(source.offers.filter(o=>o.component===id&&o.approved).map(o=>o.supplier));
    $('node-inspector').innerHTML=`<span class="small-label">COMPONENT / ${escape(id)}</span><h4>${escape(component.name)}</h4><span class="inspector-value">${component.demand}</span><p>units required across all demand</p><ul class="inspector-list"><li>Opening stock: ${component.stock}</li><li>Purchased: ${component.purchased}</li><li>Allocated: ${component.consumed}</li><li>Remaining: ${component.remaining}</li><li>${suppliers.size} approved supplier${suppliers.size===1?'':'s'}</li></ul>`;
  }else{const product=source.products.find(p=>p.id===id),orders=orderRows(result,selectedPolicy).filter(o=>o.product===id);
    $('node-inspector').innerHTML=`<span class="small-label">PRODUCT / ${escape(id)}</span><h4>${escape(product.name)}</h4><span class="inspector-value">${orders.reduce((n,o)=>n+o.fulfilled,0)} / ${orders.reduce((n,o)=>n+o.quantity,0)}</span><p>units fulfilled · ${product.assembly_minutes} assembly minutes per unit</p><ul class="inspector-list">${source.bom.filter(b=>b.product===id).map(b=>`<li>${escape(b.component)} × ${b.units} per product</li>`).join('')}</ul>`;}
}
function renderChecks(){const m=result.metrics[selectedPolicy],checked=result.checks[selectedPolicy];
  const valid=checked.valid;
  $('live-checks').innerHTML=[['Material conservation',materialRows(result,selectedPolicy).every(c=>c.remaining>=0)],
    ['Budget respected',m.cost<=result.case.budget],['Shared supplier capacity',valid],['Assembly capacity',checked.assembly_used<=result.case.assembly_limit]]
    .map(([label,passed])=>`<div class="check-item"><span>${passed?'✓':'×'}</span>${label}</div>`).join('');
  $('solver-details').textContent=`Selected policy: ${m.policy}. Status: ${m.status}. Runtime: ${m.seconds.toFixed(3)} seconds. Browser optimization budget: five seconds. ${result.plans[2].examined} search nodes. Synthetic sample seed: ${source.seed}.`;
}

function showView(view,focus=false){for(const button of document.querySelectorAll('[data-view]')){const active=button.dataset.view===view;
  button.classList.toggle('active',active);button.setAttribute('aria-selected',String(active));button.tabIndex=active?0:-1;$(button.dataset.view).hidden=!active;
  if(active&&focus)button.focus();}}
document.querySelectorAll('[data-view]').forEach(button=>button.addEventListener('click',()=>showView(button.dataset.view)));
document.querySelector('.tabs').addEventListener('keydown',event=>{if(!['ArrowLeft','ArrowRight','Home','End'].includes(event.key))return;
  const buttons=[...document.querySelectorAll('[data-view]')],index=buttons.indexOf(document.activeElement);if(index<0)return;event.preventDefault();
  const next=event.key==='Home'?0:event.key==='End'?buttons.length-1:(index+(event.key==='ArrowRight'?1:-1)+buttons.length)%buttons.length;
  showView(buttons[next].dataset.view,true);});
$('policy-cards').addEventListener('click',event=>{const button=event.target.closest('[data-policy]');if(!button||dirty)return;
  selectedPolicy=Number(button.dataset.policy);clearExperiments();render();});
$('graph').addEventListener('click',event=>{const node=event.target.closest('[data-node-id]');if(!node)return;
  const retainFocus=document.activeElement===node;
  activeNode={type:node.dataset.nodeType,id:node.dataset.nodeId};renderNetwork();
  if(retainFocus)$('graph').querySelector(`[data-node-id="${CSS.escape(activeNode.id)}"]`)?.focus();});
$('graph').addEventListener('keydown',event=>{if(['Enter',' '].includes(event.key)&&event.target.matches('[data-node-id]')){event.preventDefault();event.target.dispatchEvent(new MouseEvent('click',{bubbles:true}));}});
$('node-inspector').addEventListener('click',event=>{const button=event.target.closest('[data-model-supplier]');if(!button)return;
  $('supplier').value=button.dataset.modelSupplier;if($('kind').value==='none')$('kind').value='outage';
  document.querySelectorAll('[data-preset]').forEach(b=>b.classList.remove('active'));syncControls();compare();});
$('order-search').addEventListener('input',renderOrders);$('order-filter').addEventListener('change',renderOrders);

for(const id of ['supplier','kind','capacity','delay','budget','assembly','demand'])$(id).addEventListener('input',changed);
$('auto-run').addEventListener('change',()=>{clearTimeout(timer);if($('auto-run').checked&&dirty)compare();});
$('run').addEventListener('click',compare);
document.querySelectorAll('[data-preset]').forEach(button=>{button.disabled=true;button.addEventListener('click',()=>{
  const preset=button.dataset.preset,settings=defaults(source);settings.supplier=preset==='sole'?'S08':'S01';
  settings.kind=preset==='none'?'none':preset==='delay'?'delay':preset==='capacity'?'capacity':'outage';
  if(preset==='budget')settings.budget=Math.floor(source.default_budget/8);
  putInputs(settings);changed();document.querySelectorAll('[data-preset]').forEach(b=>b.classList.toggle('active',b===button));
  if($('auto-run').checked)compare();else markDirty();
});});
$('reset').addEventListener('click',()=>{putInputs(defaults(source));selectedPolicy=2;
  document.querySelectorAll('[data-preset]').forEach(b=>b.classList.toggle('active',b.dataset.preset==='outage'));compare();});

function saveStorage(){try{localStorage.setItem(storageKey,JSON.stringify(saved));return true;}catch{return false;}}
function renderSaved(){
  $('saved-scenarios').innerHTML=saved.map((item,i)=>`<button class="saved-item" data-saved="${i}">${escape(scenarioName(item.settings))}<small>${money(item.settings.budget)} budget · ${item.settings.demand_percent}% demand</small></button>`).join('')||'<p class="input-note">Save inputs to revisit a decision. Up to five scenarios.</p>';
  $('clear-saved').hidden=!saved.length;
}
$('save').addEventListener('click',()=>{if(dirty||!result)return;
  const signature=JSON.stringify(result.settings);saved=saved.filter(item=>JSON.stringify(item.settings)!==signature);
  saved.unshift({settings:{...result.settings}});saved=saved.slice(0,5);const stored=saveStorage();renderSaved();
  $('run-state').textContent=stored?'Scenario saved on this device.':'Scenario saved for this session; browser storage is unavailable.';});
$('saved-scenarios').addEventListener('click',event=>{const button=event.target.closest('[data-saved]');if(!button)return;
  putInputs(saved[Number(button.dataset.saved)].settings);document.querySelectorAll('[data-preset]').forEach(b=>b.classList.remove('active'));compare();});
$('clear-saved').addEventListener('click',()=>{saved=[];saveStorage();renderSaved();});
$('share').addEventListener('click',()=>{if(dirty||!result)return;$('share-panel').hidden=false;
  $('share-url').value=scenarioURL(window.location.href,result.settings);$('share-status').textContent='Anyone opening this link can recompute these sample inputs.';$('share-url').focus();$('share-url').select();});
$('copy-share').addEventListener('click',async()=>{try{await navigator.clipboard.writeText($('share-url').value);$('share-status').textContent='Scenario link copied.';}
  catch{$('share-url').focus();$('share-url').select();$('share-status').textContent='Select and copy the link above. Clipboard access is unavailable.';}});

function download(name,text,type){const url=URL.createObjectURL(new Blob([text],{type})),anchor=document.createElement('a');
  anchor.href=url;anchor.download=name;document.body.append(anchor);anchor.click();anchor.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);}
function exported(){return {...result,selected_policy:selectedPolicy,exported_at_utc:new Date().toISOString(),experiments};}
$('download-json').addEventListener('click',()=>download('supplyshield-scenario.json',JSON.stringify(exported(),null,2),'application/json'));
$('download-purchases').addEventListener('click',()=>download('supplyshield-purchases.csv',csv(purchases()),'text/csv'));
$('download-orders').addEventListener('click',()=>download('supplyshield-orders.csv',csv(orderRows(result,selectedPolicy).map(o=>({order:o.id,product:o.product,priority:o.priority,demand:o.quantity,fulfilled:o.fulfilled,unfilled:o.unfilled}))),'text/csv'));
$('download-report').addEventListener('click',()=>download('supplyshield-recommendation.md',`# SupplyShield recovery recommendation\n\nSynthetic experiment. Human review required; no purchases are executed.\n\nInputs: ${JSON.stringify(result.settings)}\n\nSelected policy: ${result.metrics[selectedPolicy].policy}\n\n${$('recommendation').textContent}\n\n${result.metrics.map(m=>`${m.policy}: ${m.fulfilled}/${m.demand} units; ${money(m.cost)} purchases; ${m.status}.`).join('\n')}\n\nAll plans independently checked: ${result.checks.every(c=>c.valid)}.\n\nModel: common seven-day horizon; start-of-horizon purchases; one-day assembly/delivery reserve; shared supplier/component capacity. Simulated fulfillment is not realized savings.\n`,'text/markdown'));

function renderExperiments(){
  const {points,stress}=experiments,maximum=Math.max(...points.map(p=>p.budget)),width=680,height=265,pad={left:50,right:25,top:25,bottom:50};
  const x=value=>pad.left+value/maximum*(width-pad.left-pad.right),y=value=>height-pad.bottom-value*(height-pad.top-pad.bottom);
  const path=points.map((p,i)=>`${i?'L':'M'}${x(p.budget).toFixed(1)},${y(p.weighted_fill_rate).toFixed(1)}`).join(' ');
  $('budget-chart').innerHTML=`<svg class="chart-svg" viewBox="0 0 ${width} ${height}" role="img" aria-label="Priority fulfillment versus procurement budget"><title>Measured priority fulfillment at six procurement budgets</title>${[0,.25,.5,.75,1].map(v=>`<line x1="50" x2="655" y1="${y(v)}" y2="${y(v)}" stroke="#e0e7d8"/><text x="39" y="${y(v)+3}" text-anchor="end" fill="#6b7b72" font-size="10">${v*100}%</text>`).join('')}<path d="${path} L${x(maximum)},${y(0)} L50,${y(0)} Z" fill="#dfecc9" opacity=".5"/><path d="${path}" stroke="#217965" stroke-width="2.5" fill="none"/>${points.map(p=>`<g role="button" tabindex="0" class="budget-point" data-budget="${p.budget}" aria-label="Apply budget ${p.budget} yen, ${percent(p.weighted_fill_rate)} priority fill"><title>${money(p.budget)} budget · ${percent(p.weighted_fill_rate)} priority fill · ${p.status}</title><circle cx="${x(p.budget)}" cy="${y(p.weighted_fill_rate)}" r="12" fill="transparent"/><circle cx="${x(p.budget)}" cy="${y(p.weighted_fill_rate)}" r="4.5" fill="#217965" stroke="#fffefb" stroke-width="2"/></g>`).join('')}<text x="50" y="${height-22}" font-size="10" fill="#6b7b72">¥0</text><text x="655" y="${height-22}" font-size="10" text-anchor="end" fill="#6b7b72">${money(maximum)}</text><text x="350" y="${height-7}" font-size="9" text-anchor="middle" fill="#6b7b72">PROCUREMENT BUDGET / JPY</text></svg>`;
  $('budget-choices').innerHTML=points.map(p=>`<button class="budget-choice ${p.budget===result.settings.budget?'selected':''}" data-budget="${p.budget}"><strong>${money(p.budget)}</strong><span>${percent(p.weighted_fill_rate)} priority · ${p.fulfilled} units</span><span>${p.status}</span></button>`).join('');
  $('frontier-note').textContent='Each point is an independent optimized rerun under the same disruption. Status is shown for each point; a time-limited FEASIBLE point is an incumbent, not proof of the exact frontier.';
  $('stress-kpis').innerHTML=[['Mean unit fill',stress.mean],['Worst observed',stress.worst],['10th percentile',stress.p10]]
    .map(([label,value])=>`<div><span>${label}</span><strong>${percent(value)}</strong></div>`).join('');
  const bins=Array(10).fill(0);for(const outcome of stress.outcomes)bins[Math.min(9,Math.floor(outcome.fill_rate*10))]++;
  const maxCount=Math.max(...bins),barWidth=47;
  $('stress-chart').innerHTML=`<svg class="chart-svg" viewBox="0 0 680 210" role="img" aria-label="Distribution of service levels across 50 fixed-purchase stress outcomes"><title>Stress distribution; number of outcomes in each ten-percentage-point unit fill band</title>${bins.map((count,i)=>{const h=count/maxCount*120;return `<rect x="${47+i*60}" y="${157-h}" width="${barWidth}" height="${h}" rx="3" fill="${i<5?'#c08a65':'#83a475'}"/><text x="${70+i*60}" y="${147-h}" text-anchor="middle" font-size="10" fill="#143e39">${count||''}</text><text x="${70+i*60}" y="177" text-anchor="middle" font-size="8" fill="#6b7b72">${i*10}–${(i+1)*10}%</text>`;}).join('')}<text x="345" y="198" text-anchor="middle" font-size="9" fill="#6b7b72">ON-TIME UNIT FILL / 50 OUTCOMES</text></svg>`;
  $('stress-assumptions').textContent=`Stress policy: ${result.metrics[selectedPolicy].policy}. Browser seed ${stress.seed}. ${stress.assumptions} These are synthetic sensitivity results, not real supplier-risk predictions.`;
  $('explore-results').hidden=false;
}
$('explore-run').addEventListener('click',async()=>{if(dirty||!result)return;const generation=++experimentGeneration;
  $('explore-run').disabled=true;$('explore-results').hidden=true;$('explore-status').textContent='Evaluating the budget choices in the background…';
  try{const next=await experimentPlanner.execute({type:'explore',source,settings:result.settings,plan:result.plans[selectedPolicy]},
    progress=>{if(generation===experimentGeneration)$('explore-status').textContent=`Calculating budget choices · ${Math.round(progress*100)}%`;});
    if(generation!==experimentGeneration)return;experiments=next;renderExperiments();
    $('explore-status').textContent=`Complete · ${next.points.length} budget choices · ${next.stress.samples} seeded outcomes · fixed purchases`;
  }catch(error){if(generation===experimentGeneration&&error.message!=='Cancelled')$('explore-status').textContent=error.message;}
  finally{if(generation===experimentGeneration)$('explore-run').disabled=false;}});
function applyBudget(event){const point=event.target.closest('[data-budget]');if(!point)return;
  $('budget').value=point.dataset.budget;document.querySelectorAll('[data-preset]').forEach(b=>b.classList.remove('active'));compare();}
$('budget-chart').addEventListener('click',applyBudget);$('budget-choices').addEventListener('click',applyBudget);
$('budget-chart').addEventListener('keydown',event=>{if(['Enter',' '].includes(event.key)&&event.target.matches('[data-budget]')){event.preventDefault();applyBudget(event);}});
$('download-experiments').addEventListener('click',()=>{if(experiments)download('supplyshield-experiments.json',JSON.stringify({settings:result.settings,policy:result.metrics[selectedPolicy].policy,...experiments},null,2),'application/json');});

$('selftest').addEventListener('click',()=>{const lines=[],assert=(condition,message)=>{if(!condition)throw new Error(message);};
  const test=(name,fn)=>{try{fn();lines.push(`PASS ${name}`);}catch(error){lines.push(`FAIL ${name}: ${error.message}`);}};
  test('Hand-calculated outage: 15 / 20, JPY 200',()=>{const r=run(reference,{supplier:'S1',kind:'outage'});assert(r.metrics[2].fulfilled===15&&r.metrics[2].cost===200,'Reference mismatch');});
  test('Zero budget uses only stock',()=>assert(run(reference,{supplier:'S1',kind:'outage',budget:0}).metrics[2].fulfilled===10,'Budget violation'));
  test('All displayed plans independently feasible',()=>assert(result.checks.every(c=>c.valid),'Constraint violation'));
  test('Late alternate supply rejected',()=>{const c=structuredClone(reference);c.offers[1].lead_days=7;assert(run(c,{supplier:'S1',kind:'outage'}).metrics[2].fulfilled===10,'Late arrival counted');});
  test('Missing BOM part stops assembly',()=>{const c=structuredClone(reference);c.stock.housing=0;assert(run(c,{supplier:'S1',kind:'outage'}).metrics[2].fulfilled===0,'Invented housing');});
  test('Corrupted allocation rejected',()=>{const p=structuredClone(result.plans[2]);p.fulfilled[result.case.orders[0].id]=100000;assert(!check(result.case,p).valid,'Corruption accepted');});
  $('test-output').textContent=lines.join('\n')+`\n\n${lines.filter(l=>l.startsWith('PASS')).length} / ${lines.length} live checks passed.`;
});

const tourSteps=[
  {title:'One disruption. A real decision.',copy:'You are planning for a fictional electronics assembler. A supplier outage puts customer orders at risk. Your job is to protect service within purchasing and assembly limits.',visual:'20 suppliers <span>→</span> 8 parts <span>→</span> 3 products'},
  {title:'Change the situation.',copy:'Start with a preset, then adjust the affected supplier, disruption, procurement budget, assembly time, or demand. Automatic updates recompute the plans as you explore.',visual:'Supplier shock <span>+</span> Budget <span>+</span> Demand'},
  {title:'Compare the response.',copy:'Existing sourcing, greedy recovery, and optimized recovery share the same constraints. Choose a policy to inspect its fulfilled orders and material balances. A tie is reported honestly.',visual:'Existing <span>→</span> Greedy <span>→</span> Optimized'},
  {title:'Review, stress-test, and share.',copy:'Explore budget choices and 50 assumed futures, inspect independent checks, and export the recommendation. Saved inputs stay on this device. No actual purchase is executed.',visual:'Verify <span>→</span> Review <span>→</span> Export'}
];let tourStep=0;
function renderTour(){const step=tourSteps[tourStep];$('tour-step').textContent=`QUICK TOUR / 0${tourStep+1} OF 04`;
  $('tour-title').textContent=step.title;$('tour-copy').textContent=step.copy;$('tour-visual').innerHTML=step.visual;
  $('tour-back').disabled=tourStep===0;$('tour-next').textContent=tourStep===3?'Open the lab ↗':'Next →';
  $('tour-dots').textContent=tourSteps.map((_,i)=>i===tourStep?'●':'○').join('');}
$('tour-open').addEventListener('click',()=>{tourStep=0;renderTour();$('tour-dialog').showModal();});
$('tour-back').addEventListener('click',()=>{if(tourStep>0){tourStep--;renderTour();}});
$('tour-next').addEventListener('click',()=>{if(tourStep<3){tourStep++;renderTour();}else{$('tour-dialog').close();$('lab').scrollIntoView({behavior:'smooth'});$('lab-heading').setAttribute('tabindex','-1');$('lab-heading').focus({preventScroll:true});}});

async function initialize(){
  try{
    const load=async file=>{const response=await fetch(file);if(!response.ok)throw new Error('The sample is unavailable. Reload to retry.');return response.json();};
    [source,reference]=await Promise.all([load('sample.json'),load('reference.json')]);
    for(const supplier of source.suppliers){const option=document.createElement('option');option.value=supplier.id;option.textContent=`${supplier.id} · ${supplier.name}`;$('supplier').append(option);}
    putInputs(settingsFromURL(source,window.location.href));
    for(const id of ['supplier','kind','budget','assembly','demand','reset'])$(id).disabled=false;
    document.querySelectorAll('[data-preset]').forEach(b=>{b.disabled=false;b.classList.toggle('active',!window.location.search&&b.dataset.preset==='outage');});
    try{const stored=JSON.parse(localStorage.getItem(storageKey)||'[]');if(Array.isArray(stored))
      saved=stored.slice(0,5).flatMap(item=>{try{return [{settings:validateSettings(source,item.settings)}];}catch{return [];}});
    }catch{/* Storage can be unavailable in private browsing. */}renderSaved();await compare();
  }catch(error){$('run-state').textContent=error.message;$('verification').textContent='Sample unavailable';
    $('results').setAttribute('aria-busy','false');$('hero-summary').textContent='The sample could not load. Reload the page to retry.';}
}
initialize();
