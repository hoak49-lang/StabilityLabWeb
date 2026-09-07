import assert from 'node:assert/strict';import {createDesign,designSheets} from './public/design-engine.mjs';
const base={name:'Study',mode:'full',strengths:[50,75,100].map((x,i)=>({label:x+' mg',batches:['B'+x+'-1','B'+x+'-2','B'+x+'-3'],selected:i!==1})),packs:[30,60,100].map((x,i)=>({label:'P'+x,system:'HDPE/PP',size:x+' mL',fill:x+' tablets',selected:i!==1})),attributes:['Assay','Impurity'],conditions:[{label:'Long term',kind:'longterm',times:[0,3,6,9,12,18,24,36],partial:true,submission:12}],reduction:'half',formulation:'related',variability:'low',predictable:true,packEvidence:true,extremes:true,rationale:'Development batch comparisons',packRationale:'Permeation and headspace study',combinedRationale:'Independent assessment of combined reduction'};
const full=createDesign(base);assert.equal(full.full,216);assert.equal(full.selected,216);assert.equal(full.reduction,0);
const bracket=createDesign({...base,mode:'bracket'});assert.equal(bracket.selected,96);assert.equal(bracket.omitted.length,5);assert.ok(bracket.studies[0].rows.every(r=>r.tests.every(Boolean)));
for(const mode of ['matrix','combined'])for(const reduction of ['half','third']){
 const d=createDesign({...base,mode,reduction,conditions:[...base.conditions,{label:'Accelerated',kind:'accelerated',times:[0,3,6]}]});
 assert.ok(d.selected<d.full);assert.equal(d.eligible,true);
 for(const study of d.studies)for(const row of study.rows){assert.equal(row.tests[0],true);assert.equal(row.tests.at(-1),true);if(study.kind==='longterm'){assert.equal(row.tests[study.times.indexOf(12)],true);assert.ok(study.times.filter((t,i)=>t<=12&&row.tests[i]).length>=3);}else assert.equal(row.tests.filter(Boolean).length,3);}
 assert.equal(designSheets(d)[2][1].length,1+d.selected*2);
}
const high=createDesign({...base,mode:'matrix',variability:'high'});assert.equal(high.eligible,false);
const unknown=createDesign({...base,mode:'combined',extremes:false,rationale:'',combinedRationale:''});assert.ok(unknown.blockers.length>=3);
assert.equal(createDesign({...base,mode:'bracket',formulation:'different'}).eligible,false);
assert.equal(createDesign({...base,mode:'matrix',variability:'moderate',statisticalEvidence:''}).eligible,false);
const added=createDesign({...base,mode:'matrix',conditions:[{label:'LT',kind:'longterm',times:[0,3,6,18,24],partial:true,submission:9}]});assert.ok(added.studies[0].times.includes(12));assert.ok(added.studies[0].forced.includes(9));assert.ok(added.studies[0].rows.every(r=>r.tests[added.studies[0].times.indexOf(9)]));
assert.throws(()=>createDesign({...base,conditions:[{label:'LT',kind:'longterm',times:[0,3,3]}]}),/trùng/);
assert.throws(()=>createDesign({...base,mode:'matrix',conditions:[{label:'LT',kind:'longterm',times:[0,18,24]}]}),/3 mốc/);
assert.throws(()=>createDesign({...base,strengths:[{label:'50 mg',batches:['B','B']}]}),/trùng/);
assert.equal(createDesign({...base,mode:'bracket',strengths:base.strengths.map((s,i)=>({...s,selected:i===0}))}).eligible,false);
console.log('PASS: full/bracket/matrix/combined counts; condition separation; endpoints, 12-month and submission protection; minimum observations; workbook dimensions; missing evidence and invalid inputs.');
