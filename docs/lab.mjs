import {run, applyScenario, greedy, metrics} from './engine.mjs';

export const defaults = source => ({supplier:'S01',kind:'outage',capacity_percent:50,delay_days:8,
  budget:source.default_budget,assembly_capacity:source.assembly_capacity,demand_percent:100});

export function validateSettings(source, values) {
  const result = {...defaults(source), ...values};
  if (!source.suppliers.some(s=>s.id===result.supplier)) throw new Error('Choose a known supplier.');
  if (!['none','outage','capacity','delay'].includes(result.kind)) throw new Error('Choose a supported disruption.');
  const limits = {capacity_percent:[0,100],delay_days:[0,30],budget:[0,1000000000],
    assembly_capacity:[0,10000000],demand_percent:[50,150]};
  for (const [key,[min,max]] of Object.entries(limits)) {
    if (!Number.isInteger(result[key]) || result[key]<min || result[key]>max) {
      throw new Error(`${key.replaceAll('_',' ')} must be a whole number between ${min.toLocaleString()} and ${max.toLocaleString()}.`);
    }
  }
  return Object.fromEntries(Object.keys(defaults(source)).map(key=>[key,result[key]]));
}

export function settingsFromURL(source, url) {
  const result = defaults(source);
  const params = new URL(url).searchParams;
  for (const key of Object.keys(result)) {
    if (!params.has(key) || params.get(key).trim()==='') continue;
    const candidate = {...result,[key]:typeof result[key]==='number'?Number(params.get(key)):params.get(key)};
    try {Object.assign(result, validateSettings(source,candidate));} catch { /* Ignore invalid shared values. */ }
  }
  return result;
}

export function scenarioURL(base, settings) {
  const url = new URL(base); url.search=''; url.hash='lab';
  for (const [key,value] of Object.entries(settings)) url.searchParams.set(key,String(value));
  return url.href;
}

export function caseForDemand(source, percent) {
  if (!Number.isInteger(percent) || percent<50 || percent>150) throw new Error('Demand must be 50–150%.');
  const result = structuredClone(source);
  for (const order of result.orders) order.quantity=Math.max(1,Math.ceil(order.quantity*percent/100));
  result.demand_percent=percent;
  return result;
}

export function compareCase(source, settings) {
  const inputs = validateSettings(source,settings);
  const caseData = caseForDemand(source,inputs.demand_percent);
  const result = run(caseData,inputs);
  return {...result,settings:inputs,model_version:'browser-2.0',synthetic:true};
}

export function materialRows(result, policy=2) {
  const c=result.case, plan=result.plans[policy];
  return c.components.map(component=>{
    const required = c.bom.filter(b=>b.component===component.id);
    const demand = required.reduce((sum,b)=>sum+c.orders.filter(o=>o.product===b.product)
      .reduce((n,o)=>n+o.quantity*b.units,0),0);
    const consumed = required.reduce((sum,b)=>sum+c.orders.filter(o=>o.product===b.product)
      .reduce((n,o)=>n+(plan.fulfilled[o.id]??0)*b.units,0),0);
    const purchased=c.offers.filter(o=>o.component===component.id)
      .reduce((sum,o)=>sum+(plan.purchases[o.id]??0),0);
    return {...component,demand,consumed,purchased,stock:c.stock[component.id],
      remaining:c.stock[component.id]+purchased-consumed};
  });
}

export function orderRows(result, policy=2) {
  const products = Object.fromEntries(result.case.products.map(p=>[p.id,p]));
  return result.case.orders.map(order=>({...order,product_name:products[order.product].name,
    fulfilled:result.plans[policy].fulfilled[order.id]??0,
    unfilled:order.quantity-(result.plans[policy].fulfilled[order.id]??0)}));
}

function randomGenerator(seed) {
  let state=seed>>>0;
  return ()=>{state=(Math.imul(1664525,state)+1013904223)>>>0;return state/4294967296;};
}

export function stressFixedPlan(source, settings, plan, samples=50, seed=41) {
  validateSettings(source,settings);
  if (!Number.isInteger(samples)||samples<1||samples>200) throw new Error('Use 1–200 stress samples.');
  const random=randomGenerator(seed), outcomes=[];
  const selectedCase=caseForDemand(source,settings.demand_percent);
  const committedCost=selectedCase.offers.reduce((sum,o)=>sum+(plan.purchases[o.id]??0)*o.cost,0);
  for(let i=0;i<samples;i++) {
    const capacity=[0,50,100][Math.floor(random()*3)], delay=[0,3,8][Math.floor(random()*3)],
      demand=[80,100,120][Math.floor(random()*3)];
    const c=applyScenario(selectedCase,{...settings,kind:'capacity',capacity_percent:capacity,delay_days:0});
    const pools=Object.fromEntries(c.offers.map(o=>[`${o.supplier}/${o.component}`,o.capacity]));
    const inventory={...c.stock};let unavailable=0;
    for(const o of c.offers) {
      const requested=plan.purchases[o.id]??0, pool=`${o.supplier}/${o.component}`;
      const lead=o.lead_days+(o.supplier===settings.supplier?delay:0);
      const received=o.approved&&lead+c.assembly_reserve<=c.horizon?Math.min(requested,pools[pool]):0;
      pools[pool]-=received;inventory[o.component]+=received;unavailable+=requested-received;
    }
    const realized={...c,stock:inventory,offers:[],planned:{},budget:0,
      orders:c.orders.map(o=>({...o,quantity:Math.max(1,Math.ceil(o.quantity*demand/100))}))};
    const measured=metrics(realized,greedy(realized));
    outcomes.push({sample:i+1,capacity_percent:capacity,delay_days:delay,demand_percent:demand,
      fill_rate:measured.fill_rate,priority_fill:measured.weighted_fill_rate,fulfilled:measured.fulfilled,
      demand:measured.demand,committed_cost:committedCost,unavailable_units:unavailable});
  }
  const rates=outcomes.map(o=>o.fill_rate).sort((a,b)=>a-b);
  return {seed,samples,fixed_purchases:structuredClone(plan.purchases),perfect_information:false,outcomes,
    mean:rates.reduce((s,n)=>s+n,0)/rates.length,worst:rates[0],p10:rates[Math.floor((rates.length-1)*.1)],
    assumptions:'Independent uniform choices of 0/50/100% supplier capacity, 0/3/8 extra delay days, and 80/100/120% demand. Quantities round up per order. Assumptions, not estimated probabilities.',
    model_version:'browser-2.0',synthetic:true};
}

export function budgetPoints(source, settings) {
  const base=source.default_budget;
  return [...new Set([0,Math.floor(base/8),Math.floor(base/4),Math.floor(base/2),base,
    Math.min(1000000000,Math.max(Math.floor(base*1.5),settings.budget))])].sort((a,b)=>a-b);
}

export function csv(rows) {
  if (!rows.length) return '';
  const keys=Object.keys(rows[0]);
  const cell=value=>{let str=String(value??'');if(/^[=+@-]/.test(str))str="'"+str;
    return '"'+str.replaceAll('"','""')+'"';};
  return [keys.map(cell).join(','),...rows.map(row=>keys.map(key=>cell(row[key])).join(','))].join('\r\n');
}
