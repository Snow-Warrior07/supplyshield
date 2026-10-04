import fs from 'node:fs';
import assert from 'node:assert/strict';
import {run} from '../docs/engine.mjs';
import {defaults,validateSettings,settingsFromURL,scenarioURL,caseForDemand,compareCase,materialRows,orderRows,stressFixedPlan,budgetPoints,csv} from '../docs/lab.mjs';

const source=JSON.parse(fs.readFileSync('docs/sample.json','utf8'));
const reference=JSON.parse(fs.readFileSync('docs/reference.json','utf8'));
const checks=[];
function test(name,fn){const start=performance.now();try{fn();checks.push({name,passed:true,seconds:(performance.now()-start)/1000});}
  catch(error){checks.push({name,passed:false,error:error.message});}}
test('Default website result matches the hand-checked sample',()=>{const r=compareCase(source,defaults(source));
  assert.equal(r.metrics[2].fulfilled,138);assert.equal(r.metrics[2].cost,119420);assert.ok(r.checks.every(c=>c.valid));});
test('Demand scaling does not mutate the source; quantities remain whole units',()=>{const copy=JSON.stringify(source),c=caseForDemand(source,130);
  assert.equal(JSON.stringify(source),copy);assert.ok(c.orders.every((o,i)=>o.quantity===Math.ceil(source.orders[i].quantity*1.3)));});
test('High demand preserves material, capacity, budget and assembly feasibility',()=>{
  const r=compareCase(source,{...defaults(source),demand_percent:150,budget:60000});assert.ok(r.checks.every(c=>c.valid));
  assert.ok(materialRows(r).every(c=>c.remaining>=0));assert.equal(orderRows(r).reduce((s,o)=>s+o.fulfilled,0),r.metrics[2].fulfilled);});
test('Zero budget leaves all three policies with no purchases',()=>{const r=compareCase(source,{...defaults(source),budget:0});
  assert.ok(r.metrics.every(m=>m.cost===0));assert.equal(r.metrics[2].fulfilled,24);});
test('Shared URLs reproduce valid inputs',()=>{const s={...defaults(source),supplier:'S08',demand_percent:120,budget:50000};
  assert.deepEqual(settingsFromURL(source,scenarioURL('https://example.com/supplyshield/?unrelated=1',s)),s);});
test('Untrusted URL values are ignored; oversized, fractional and negative controls rejected',()=>{
  const parsed=settingsFromURL(source,'https://example.com/?supplier=%3Cscript%3E&budget=-1&demand_percent=999&kind=surprise');
  assert.deepEqual(parsed,defaults(source));for(const values of [{budget:-1},{budget:1.5},{budget:1e12},{demand_percent:0},{supplier:'unknown'}])
    assert.throws(()=>validateSettings(source,values));});
test('Fixed-policy stress is reproducible and retains the original purchases',()=>{
  const settings={...defaults(reference),supplier:'S1',kind:'none'},plan=run(reference,settings).plans[2],initial=JSON.stringify(plan);
  const one=stressFixedPlan(reference,settings,plan,50,41),two=stressFixedPlan(reference,settings,plan,50,41);
  assert.deepEqual(one,two);assert.equal(JSON.stringify(plan),initial);assert.equal(one.perfect_information,false);
  assert.deepEqual(one.fixed_purchases,plan.purchases);assert.ok(one.worst<=one.mean);
  assert.equal(new Set(one.outcomes.map(o=>o.committed_cost)).size,1);});
test('Stress outcomes cannot reprocure after committed chips fail to arrive',()=>{
  const settings={...defaults(reference),supplier:'S1',kind:'none'},plan=run(reference,settings).plans[2];
  const sampled=stressFixedPlan(reference,settings,plan,100,41);
  const bad=sampled.outcomes.filter(o=>o.unavailable_units>0);assert.ok(bad.length>0);
  const chips=reference.offers.filter(o=>o.component==='chip').reduce((sum,o)=>sum+(plan.purchases[o.id]??0),0);
  assert.ok(bad.every(o=>o.fulfilled*2<=reference.stock.chip+chips-o.unavailable_units));
  assert.ok(bad.filter(o=>o.capacity_percent===0||o.delay_days===8).every(o=>o.fulfilled<=10));});
test('Budget points include zero and the requested budget without duplicates',()=>{
  const points=budgetPoints(source,{...defaults(source),budget:500000});
  assert.equal(points[0],0);assert.equal(points.at(-1),500000);assert.equal(points.length,new Set(points).size);});
test('CSV exports escape formula text and embedded quotes',()=>{
  const output=csv([{supplier:'=HYPERLINK("x")',units:2}]);assert.ok(output.includes("'=HYPERLINK"));assert.ok(output.includes('""x""'));});
const summary={tested_at_utc:new Date().toISOString(),passed:checks.filter(c=>c.passed).length,total:checks.length,
  scope:'Website model, validation, sharing, exports and fixed-policy stress',checks};
fs.writeFileSync('test-results/website-unit.json',JSON.stringify(summary,null,2));
console.log(JSON.stringify(summary,null,2));if(summary.passed!==summary.total)process.exitCode=1;
