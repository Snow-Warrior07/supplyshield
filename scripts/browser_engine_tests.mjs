import fs from 'node:fs';
import assert from 'node:assert/strict';
import {run} from '../docs/engine.mjs';
const data=JSON.parse(fs.readFileSync('docs/sample.json','utf8'));
const reference=JSON.parse(fs.readFileSync('docs/reference.json','utf8'));
const fixtures=JSON.parse(fs.readFileSync('test-results/parity.json','utf8'));
const checks=[];
for(const f of fixtures){const start=performance.now(),r=run(data,f.scenario);
 for(let i=0;i<3;i++){assert.equal(r.metrics[i].score,f.expected[i].score);assert.equal(r.metrics[i].cost,f.expected[i].cost);assert.ok(r.checks[i].valid);}
 checks.push({scenario:f.scenario,passed:true,seconds:(performance.now()-start)/1000});}
const r=run(reference,{supplier:'S1',kind:'outage'});assert.equal(r.metrics.at(-1).fulfilled,15);assert.equal(r.metrics.at(-1).cost,200);
checks.push({name:'Hand-calculated reference',passed:true});
const summary={tested_at_utc:new Date().toISOString(),passed:checks.length,total:checks.length,
 description:'Browser engine vs Python CP-SAT: priority objective, purchase cost, and feasibility',checks};
fs.writeFileSync('test-results/browser-parity.json',JSON.stringify(summary,null,2));
console.log(JSON.stringify({passed:checks.length,total:checks.length,description:summary.description}));
