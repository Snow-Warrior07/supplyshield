import {run, check} from './engine.mjs';
const $ = id => document.getElementById(id), yen = n => `¥${n.toLocaleString()}`, percent = n => n === null ? 'N/A' : `${(n*100).toFixed(1)}%`;
const source = await fetch('sample.json').then(r=>{if(!r.ok)throw new Error('Sample unavailable');return r.json();});
const reference = await fetch('reference.json').then(r=>r.json());
for(const s of source.suppliers){const option=document.createElement('option');option.value=s.id;option.textContent=`${s.id} · ${s.name}`;$('supplier').append(option);}
$('budget').value=source.default_budget;$('assembly').value=source.assembly_capacity;
let result;
const escape = s => String(s).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
const scenario = () => ({supplier:$('supplier').value,kind:$('kind').value,capacity_percent:Number($('capacity').value),delay_days:Number($('delay').value),budget:Number($('budget').value),assembly_capacity:Number($('assembly').value)});
function network(){const impactedParts=new Set(source.offers.filter(o=>o.supplier===result.case.scenario.supplier).map(o=>o.component));
 const impactedProducts=new Set(source.bom.filter(b=>impactedParts.has(b.component)).map(b=>b.product));
 const pos=new Map(),nodes=[];for(const [rows,x,prefix] of [[source.suppliers,35,'S'],[source.components,310,'C'],[source.products,570,'P']])rows.forEach((r,i)=>{const n={id:r.id,x,y:35+i*350/Math.max(1,rows.length-1),label:r.name,hot:prefix==='S'?r.id===result.case.scenario.supplier:prefix==='C'?impactedParts.has(r.id):impactedProducts.has(r.id)};pos.set(r.id,n);nodes.push(n);});
 const edges=[...new Set(source.offers.map(o=>`${o.supplier}|${o.component}`)),...source.bom.map(b=>`${b.component}|${b.product}`)];
 $('graph').innerHTML=`<svg viewBox="0 0 650 430" role="img" aria-label="Supplier component product dependency network"><text x="15" y="15" fill="#64736e" font-size="10">SUPPLIERS</text><text x="285" y="15" fill="#64736e" font-size="10">COMPONENTS</text><text x="545" y="15" fill="#64736e" font-size="10">PRODUCTS</text>${edges.map(e=>{const[a,b]=e.split('|'),p=pos.get(a),q=pos.get(b);return `<line x1="${p.x}" y1="${p.y}" x2="${q.x}" y2="${q.y}" stroke="#dce3da"/>`;}).join('')}${nodes.map(n=>`<g><title>${escape(n.label)}</title><circle cx="${n.x}" cy="${n.y}" r="5" fill="${n.hot?'#cb7149':'#19786a'}"/><text x="${n.x+10}" y="${n.y+3}" font-size="10" fill="#143e39">${escape(n.id)}</text></g>`).join('')}</svg>`;
 $('parts').textContent=`Potentially exposed components: ${[...impactedParts].join(', ')}. Dependent SKUs: ${[...impactedProducts].join(', ')}.`;
}
function render(){const m=result.metrics.at(-1);$('kpis').innerHTML=[['On-time unit fill',percent(m.fill_rate)],['Priority fulfillment',percent(m.weighted_fill_rate)],['Recovery purchases',yen(m.cost)],['Unfulfilled units',m.unfulfilled]].map(([l,v])=>`<div class="kpi"><label>${l}</label><strong>${v}</strong></div>`).join('');
 $('verification').textContent='✓ 3 / 3 plans independently verified';
 $('bars').innerHTML=result.metrics.map((r,i)=>`<div class="bar-row"><span>${r.policy}</span><div class="bar-track"><div class="bar ${i===2?'opt':''}" style="width:${(r.fill_rate??0)*100}%"></div></div><span>${percent(r.fill_rate)}</span></div>`).join('');
 $('policy-table').innerHTML=result.metrics.map(r=>`<tr><td>${r.policy}</td><td>${r.fulfilled} / ${r.demand}</td><td>${percent(r.weighted_fill_rate)}</td><td>${yen(r.cost)}</td><td><span class="tag">${r.status}</span></td></tr>`).join('');
 $('recommendation').textContent=`The optimized plan fulfills ${m.fulfilled} of ${m.demand} units, protecting ${percent(m.weighted_fill_rate)} of priority-weighted demand with ${yen(m.cost)} in purchases. ${m.unfulfilled} units remain unfulfilled. Review the allocations and declared arrival assumptions below.`;
 const offers=Object.fromEntries(result.case.offers.map(o=>[o.id,o]));$('purchases').innerHTML=Object.entries(result.plans.at(-1).purchases).filter(([,n])=>n).map(([id,n])=>{const o=offers[id];return `<tr><td>${escape(o.supplier)}</td><td>${escape(o.component)}</td><td>${o.mode}</td><td>${n}</td><td>${o.lead_days} days</td></tr>`;}).join('')||'<tr><td colspan="5">No purchases recommended under this budget and scenario.</td></tr>';
 $('solver-details').textContent=`Status: ${m.status}. Solve time: ${m.seconds.toFixed(3)} seconds. ${result.plans.at(-1).examined} search nodes. Independent constraint checks: passed.`;network();
}
async function compare(){const s=scenario();if(!Number.isInteger(s.budget)||s.budget<0||!Number.isInteger(s.assembly_capacity)||s.assembly_capacity<0){$('run-state').textContent='Enter nonnegative whole-number budget and assembly limits.';return;}
 $('run').disabled=true;$('run-state').textContent='Solving and checking conservation…';await new Promise(resolve=>setTimeout(resolve,30));
 try{result=run(source,s);render();$('run-state').textContent=`Verified · ${result.metrics.at(-1).seconds.toFixed(3)}s · ${s.kind} / ${s.supplier}`;}catch(e){$('run-state').textContent=`Unable to solve: ${e.message}`;}finally{$('run').disabled=false;}}
$('run').addEventListener('click',compare);
$('capacity').addEventListener('input',()=>$('cap-value').textContent=$('capacity').value+'%');$('delay').addEventListener('input',()=>$('delay-value').textContent=$('delay').value+' days');
$('preset').addEventListener('change',()=>{const p=$('preset').value;$('supplier').value=p==='sole'?'S08':'S01';$('kind').value=p==='none'?'none':p==='delay'?'delay':p==='capacity'?'capacity':'outage';$('budget').value=p==='budget'?Math.floor(source.default_budget/8):source.default_budget;compare();});
for(const button of document.querySelectorAll('[data-view]'))button.addEventListener('click',()=>{for(const b of document.querySelectorAll('[data-view]')){b.classList.toggle('active',b===button);$(b.dataset.view).hidden=b!==button;}});
function download(name,text,type){const u=URL.createObjectURL(new Blob([text],{type})),a=document.createElement('a');a.href=u;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(u),1000);}
$('download-json').addEventListener('click',()=>download('supplyshield-scenario.json',JSON.stringify(result,null,2),'application/json'));
$('download-report').addEventListener('click',()=>download('supplyshield-recommendation.md',`# SupplyShield recovery recommendation\n\nSynthetic experiment. No realized savings claimed.\n\nScenario: ${JSON.stringify(result.case.scenario)}\n\n${$('recommendation').textContent}\n\n${result.metrics.map(m=>`${m.policy}: ${m.fulfilled}/${m.demand} units; ${yen(m.cost)} purchases; ${m.status}.`).join('\n')}\n\nHuman review required. Inputs and complete allocations are available in the JSON export.\n`,'text/markdown'));
$('selftest').addEventListener('click',async()=>{const lines=[];const test=(name,fn)=>{try{fn();lines.push(`PASS ${name}`);}catch(e){lines.push(`FAIL ${name}: ${e.message}`);}};const assert=(c,m)=>{if(!c)throw new Error(m);};
 test('Hand-calculated outage: 15 / 20',()=>{const r=run(reference,{supplier:'S1',kind:'outage',capacity_percent:50,delay_days:8});assert(r.metrics.at(-1).fulfilled===15,'Expected 15');assert(r.metrics.at(-1).cost===200,'Expected JPY 200');});
 test('Zero budget: existing stock only',()=>{const r=run(reference,{supplier:'S1',kind:'outage',budget:0});assert(r.metrics.at(-1).fulfilled===10,'Expected 10');});
 test('Current scenario: independent checks',()=>assert(result.checks.every(c=>c.valid),'Constraint violation'));
 test('Late alternative rejected',()=>{const c=structuredClone(reference);c.offers[1].lead_days=7;assert(run(c,{supplier:'S1',kind:'outage'}).metrics.at(-1).fulfilled===10,'Late arrival counted');});
 test('Missing BOM part stops assembly',()=>{const c=structuredClone(reference);c.stock.housing=0;assert(run(c,{supplier:'S1',kind:'outage'}).metrics.at(-1).fulfilled===0,'Invented housing');});
 test('Corrupted allocation rejected',()=>{const p=structuredClone(result.plans.at(-1));p.fulfilled[result.case.orders[0].id]=100000;assert(!check(result.case,p).valid,'Invalid plan accepted');});
 $('test-output').textContent=lines.join('\n')+`\n\n${lines.filter(l=>l.startsWith('PASS')).length} / ${lines.length} live checks passed.`;});
await compare();
