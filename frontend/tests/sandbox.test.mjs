import {test} from 'node:test';
import assert from 'node:assert/strict';
import {loadSandbox} from '../src/sandboxApi.ts';
test('new game reloads both catalogue and state after damaged replay failure', async t => {
  const original=globalThis.fetch;
  t.after(()=>globalThis.fetch=original);
  globalThis.fetch=async (url,init)=> {
    if (url.endsWith('/catalog')) return Response.json({city_name:'Новый Берег',improvements:[{id:'bus'}]});
    const {turns}=JSON.parse(init.body);
    return turns.length ? Response.json({error:{message:'Повреждённый ход'}},{status:422}) : Response.json({quarter:1,budget:100,built:[],turns:[]});
  };
  await assert.rejects(loadSandbox([['unknown']]), /Повреждённый ход/);
  const result=await loadSandbox([]);
  assert.equal(result.catalog.improvements[0].id,'bus');
  assert.equal(result.city.budget,100);assert.deepEqual(result.city.turns,[]);
});
