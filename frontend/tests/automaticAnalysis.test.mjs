import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createAutomaticAnalysis,getScenarioAutomaticAnalysis} from '../src/automaticAnalysis.ts';

test('rerenders and repeated calculation of the same version share one AI request', async()=>{
  const runner=createAutomaticAnalysis();let calls=0,finish;
  const request=()=>{calls++;return new Promise(resolve=>finish=resolve);};
  const first=runner.run('scenario-a:1',request);
  const second=runner.run('scenario-a:1',request);
  await Promise.resolve();assert.equal(calls,1);
  finish({answer:'report'});
  assert.deepEqual(await first,await second);
  await runner.run('scenario-a:1',request);
  assert.equal(calls,1);
});
test('changed plan or another scenario gets its own report',async()=>{
  const runner=createAutomaticAnalysis();let calls=0;
  const request=async()=>++calls;
  assert.equal(await runner.run('scenario-a:1',request),1);
  assert.equal(await runner.run('scenario-a:2',request),2);
  assert.equal(await runner.run('scenario-b:1',request),3);
});
test('failed autoanalysis is not retried by rerendering',async()=>{
  const runner=createAutomaticAnalysis();let calls=0;
  const request=async()=>{calls++;throw new Error('AI unavailable');};
  await assert.rejects(runner.run('scenario-a:1',request),/unavailable/);
  await assert.rejects(runner.run('scenario-a:1',request),/unavailable/);
  assert.equal(calls,1);
});
test('new panel instance after switching modes retains attempted scenario versions',async()=>{
  let calls=0;
  await getScenarioAutomaticAnalysis().run('restored-scenario:7',async()=>{calls++;});
  await getScenarioAutomaticAnalysis().run('restored-scenario:7',async()=>{calls++;});
  assert.equal(calls,1);
});
