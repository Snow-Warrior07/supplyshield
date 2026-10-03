// Exact, bounded browser planner for the shipped three-SKU fixture.
// Python/OR-Tools remains the extensible server implementation.
export function applyScenario(source, scenario) {
  const c = structuredClone(source);
  c.budget = scenario.budget ?? c.default_budget;
  c.assembly_limit = scenario.assembly_capacity ?? c.assembly_capacity;
  c.scenario = scenario;
  for (const o of c.offers) {
    if (o.supplier === scenario.supplier) {
      if (scenario.kind === 'outage') o.capacity = 0;
      if (scenario.kind === 'capacity') o.capacity = Math.floor(o.capacity * scenario.capacity_percent / 100);
      if (scenario.kind === 'delay') o.lead_days += scenario.delay_days;
    }
    o.eligible = o.approved && o.lead_days + c.assembly_reserve <= c.horizon;
  }
  return c;
}
const reqs = c => Object.fromEntries(c.products.map(p => [p.id, Object.fromEntries(c.bom.filter(b => b.product === p.id).map(b => [b.component, b.units]))]));
const empty = (c, policy) => ({policy, purchases: Object.fromEntries(c.offers.map(o => [o.id, 0])), fulfilled: Object.fromEntries(c.orders.map(o => [o.id, 0])), status:'FEASIBLE', seconds:0});
const poolKey = o => `${o.supplier}/${o.component}`;
const orderSort = (a, b) => b.priority - a.priority || a.id.localeCompare(b.id);
export function greedy(c, existing = false) {
  const started = performance.now(), plan = empty(c, existing ? 'Existing sourcing' : 'Greedy recovery'), req = reqs(c);
  const offers = [...c.offers].sort((a,b) => a.cost - b.cost || a.id.localeCompare(b.id));
  let stock = {...c.stock}, pools = Object.fromEntries(offers.map(o => [poolKey(o), o.capacity]));
  let budget = c.budget, assembly = c.assembly_limit;
  const minutes = Object.fromEntries(c.products.map(p => [p.id, p.assembly_minutes]));
  for (const order of [...c.orders].sort(orderSort)) for (let unit = 0; unit < order.quantity; unit++) {
    if (assembly < minutes[order.product]) break;
    const ts = {...stock}, tp = {...pools}, purchases = {...plan.purchases}; let spent = 0, ok = true;
    for (const [component, count] of Object.entries(req[order.product])) {
      let need = Math.max(0, count - ts[component]);
      for (const offer of offers) {
        if (!need) break;
        if (offer.component !== component || !offer.eligible) continue;
        let allowed = tp[poolKey(offer)];
        if (existing) allowed = Math.min(allowed, Math.max(0,(c.planned[offer.id] ?? 0) - purchases[offer.id]));
        const affordable = offer.cost ? Math.max(0, Math.floor((budget-spent)/offer.cost)) : need;
        const n = Math.min(need, allowed, affordable);
        purchases[offer.id] += n; tp[poolKey(offer)] -= n; ts[component] += n; spent += n*offer.cost; need -= n;
      }
      if (need) {ok = false; break;}
      ts[component] -= count;
    }
    if (!ok) break;
    stock = ts; pools = tp; plan.purchases = purchases; budget -= spent;
    assembly -= minutes[order.product]; plan.fulfilled[order.id]++;
  }
  plan.seconds = (performance.now()-started)/1000;
  return plan;
}
export function check(c, plan) {
  const errors = [], pools = {}, arrivals = {}, used = {}, req = reqs(c);
  let cost = 0, assembly = 0;
  for (const o of c.offers) {
    const n = plan.purchases[o.id] ?? 0;
    if (!Number.isInteger(n) || n < 0) {errors.push('Invalid purchase'); continue;}
    if (n && !o.eligible) errors.push('Ineligible arrival');
    pools[poolKey(o)] = (pools[poolKey(o)] ?? 0) + n;
    arrivals[o.component] = (arrivals[o.component] ?? 0) + n; cost += n*o.cost;
  }
  for (const o of c.offers) if ((pools[poolKey(o)] ?? 0) > o.capacity) errors.push('Shared capacity');
  const minutes = Object.fromEntries(c.products.map(p => [p.id, p.assembly_minutes]));
  for (const o of c.orders) {
    const n = plan.fulfilled[o.id] ?? 0;
    if (!Number.isInteger(n) || n < 0 || n > o.quantity) {errors.push('Invalid fulfillment');continue;}
    assembly += n*minutes[o.product];
    for (const [part,count] of Object.entries(req[o.product])) used[part] = (used[part] ?? 0) + n*count;
  }
  for (const [part,n] of Object.entries(used)) if (n > c.stock[part]+(arrivals[part] ?? 0)) errors.push('Material shortage');
  if (cost > c.budget) errors.push('Budget exceeded');
  if (assembly > c.assembly_limit) errors.push('Assembly capacity');
  return {valid:!errors.length, errors:[...new Set(errors)], cost, assembly_used:assembly};
}
export function metrics(c, plan) {
  const validation = check(c,plan); if (!validation.valid) throw new Error(validation.errors.join(', '));
  const demand = c.orders.reduce((a,o)=>a+o.quantity,0), fulfilled = Object.values(plan.fulfilled).reduce((a,n)=>a+n,0);
  const score = c.orders.reduce((a,o)=>a+o.priority*(plan.fulfilled[o.id]??0),0);
  const maximum = c.orders.reduce((a,o)=>a+o.priority*o.quantity,0);
  return {policy:plan.policy, demand, fulfilled, fill_rate:demand?fulfilled/demand:null,
    weighted_fill_rate:maximum?score/maximum:null, score, unfulfilled:demand-fulfilled,
    cost:validation.cost, sales_exposure:c.orders.reduce((a,o)=>a+o.price*(o.quantity-(plan.fulfilled[o.id]??0)),0),
    status:plan.status, seconds:plan.seconds, feasible:true};
}
export function optimize(c, maxMillis = 5000) {
  const start = performance.now(), req = reqs(c), products = c.products;
  if (products.length > 3) throw new Error('Browser fixture supports up to three SKUs; use the Python API for larger cases.');
  const sortedOffers = [...c.offers].filter(o=>o.eligible).sort((a,b)=>a.cost-b.cost||a.id.localeCompare(b.id));
  const groups = products.map(p=>[...c.orders].filter(o=>o.product===p.id).sort(orderSort));
  const scores = groups.map(orders=>{const s=[0];for(const o of orders) for(let i=0;i<o.quantity;i++)s.push(s.at(-1)+o.priority);return s;});
  let best = greedy(c), bestMetric = metrics(c,best), examined = 0, timedOut = false;
  const totals = Array(products.length).fill(0);
  function evaluate(score) {
    if (score < bestMetric.score) return;
    const need = {...c.stock};for(const key in need)need[key]=-need[key];
    for(let i=0;i<products.length;i++)for(const [part,n] of Object.entries(req[products[i].id]))need[part]+=totals[i]*n;
    const candidate = empty(c,'Optimized recovery'), pools=Object.fromEntries(sortedOffers.map(o=>[poolKey(o),o.capacity]));let cost=0;
    for(const component of c.components){let missing=Math.max(0,need[component.id]);
      for(const offer of sortedOffers){if(!missing)break;if(offer.component!==component.id)continue;
        const n=Math.min(missing,pools[poolKey(offer)]);candidate.purchases[offer.id]=n;
        pools[poolKey(offer)]-=n;cost+=n*offer.cost;missing-=n;}
      if(missing || cost>c.budget)return;
    }
    if(score===bestMetric.score && cost>=bestMetric.cost)return;
    for(let i=0;i<groups.length;i++){let n=totals[i];for(const o of groups[i]){const f=Math.min(n,o.quantity);candidate.fulfilled[o.id]=f;n-=f;}}
    best=candidate;bestMetric={score,cost};
  }
  function visit(index,score,assembly){
    if(timedOut)return;
    if((++examined % 1024)===0 && performance.now()-start>maxMillis){timedOut=true;return;}
    if(index===products.length){evaluate(score);return;}
    const upper=score+scores.slice(index).reduce((s,a)=>s+a.at(-1),0);if(upper<bestMetric.score)return;
    const p=products[index],limit=Math.min(scores[index].length-1,Math.floor((c.assembly_limit-assembly)/p.assembly_minutes));
    for(let n=limit;n>=0;n--){totals[index]=n;visit(index+1,score+scores[index][n],assembly+n*p.assembly_minutes);}
  }
  visit(0,0,0);best.policy='Optimized recovery';best.status=timedOut?'FEASIBLE':'OPTIMAL';
  best.seconds=(performance.now()-start)/1000;best.examined=examined;
  if(!check(c,best).valid)throw new Error('Independent browser verification failed');
  return best;
}
export function run(source,scenario){const c=applyScenario(source,scenario);const plans=[greedy(c,true),greedy(c),optimize(c)];
 return {case:c,plans,metrics:plans.map(p=>metrics(c,p)),checks:plans.map(p=>check(c,p))};}
