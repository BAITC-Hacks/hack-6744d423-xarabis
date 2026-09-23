import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {once} from 'node:events';
import {proxyRequest} from '../proxy.mjs';

async function listen(server) {server.listen(0,'127.0.0.1');await once(server,'listening');return `http://127.0.0.1:${server.address().port}`;}
test('proxy forwards JSON route and preserves HTTP errors', async t => {
  let received;
  const upstream=createServer(async(req,res)=>{let body='';for await(const chunk of req)body+=chunk;received={path:req.url,body:JSON.parse(body)};res.writeHead(422,{'Content-Type':'application/json'}).end('{"error":{"message":"invalid"}}');});
  const origin=await listen(upstream);
  const front=createServer((req,res)=>proxyRequest(req,res,origin,req.url.replace('/api/ai','')));
  const url=await listen(front);
  t.after(()=>{front.closeAllConnections();front.close();upstream.closeAllConnections();upstream.close();});
  const response=await fetch(url+'/api/ai/sandbox/chat',{method:'POST',body:JSON.stringify({message:'hello'}),headers:{'Content-Type':'application/json'}});
  assert.equal(response.status,422);assert.deepEqual(received,{path:'/sandbox/chat',body:{message:'hello'}});
  assert.equal((await response.json()).error.message,'invalid');
});
test('proxy delivers SSE before upstream closes, and aborts upstream on browser disconnect', {timeout:5000}, async t => {
  let disconnectedResolve;
  const disconnected=new Promise(resolve=>disconnectedResolve=resolve);
  const upstream=createServer((req,res)=>{req.resume();res.writeHead(200,{'Content-Type':'text/event-stream'});res.write('event: answer_delta\ndata: {"delta":"Hi"}\n\n');res.on('close',disconnectedResolve);});
  const origin=await listen(upstream);const front=createServer((req,res)=>proxyRequest(req,res,origin,'/chat/stream'));
  const url=await listen(front);t.after(()=>{front.closeAllConnections();front.close();upstream.closeAllConnections();upstream.close();});
  const response=await fetch(url+'/api/ai/chat/stream');assert.equal(response.status,200);
  const reader=response.body.getReader();const {value}=await reader.read();assert.match(new TextDecoder().decode(value),/answer_delta/);
  await reader.cancel();await disconnected;
});
test('proxy refuses a path that changes configured upstream origin', async t => {
  const front=createServer((req,res)=>proxyRequest(req,res,'http://127.0.0.1:1','//127.0.0.1:2/private'));
  const url=await listen(front);t.after(()=>{front.closeAllConnections();front.close();});
  const response=await fetch(url+'/api/ai//127.0.0.1:2/private');assert.equal(response.status,400);
});
