import {compareCase, budgetPoints, stressFixedPlan} from './lab.mjs';

self.onmessage = ({data}) => {
  const {id,type,source,settings,plan}=data;
  try {
    if(type==='compare') self.postMessage({id,result:compareCase(source,settings)});
    else if(type==='explore') {
      const points=[],budgets=budgetPoints(source,settings);
      for(const budget of budgets) {
        const result=compareCase(source,{...settings,budget});
        points.push({budget,...result.metrics[2]});
        self.postMessage({id,progress:points.length/budgets.length});
      }
      self.postMessage({id,result:{points,stress:stressFixedPlan(source,settings,plan)}});
    } else throw new Error('Unknown planning request.');
  } catch(error) {self.postMessage({id,error:error.message});}
};
