import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readReportStream } from '../src/reportStream.ts';

const report = {answer:'Привет 🌿', strengths:[], risks:[], recommendations:[], follow_up_question:null};
function response(text, size = 1) {
  const bytes = new TextEncoder().encode(text);
  return new Response(new ReadableStream({start(controller) {
    for (let i=0;i<bytes.length;i+=size) controller.enqueue(bytes.slice(i,i+size));
    controller.close();
  }}), {headers:{'Content-Type':'text/event-stream'}});
}
test('stream decodes split Unicode and CRLF, then returns authoritative report', async () => {
  let text='';
  const result=await readReportStream(response(': connected\r\n\r\nevent: answer_delta\r\ndata: {"delta":"Привет 🌿"}\r\n\r\nevent: complete\r\ndata: '+JSON.stringify(report)+'\r\n\r\n'), delta=>text+=delta);
  assert.equal(text,report.answer); assert.deepEqual(result,report);
});
test('abrupt EOF does not turn partial text into a completed report', async () => {
  await assert.rejects(readReportStream(response('event: answer_delta\ndata: {"delta":"часть"}\n\n'),()=>{}), /оборвался/);
});
test('server stream error reaches the caller', async () => {
  await assert.rejects(readReportStream(response('event: error\ndata: {"error":{"message":"Модель недоступна"}}\n\n'),()=>{}), /Модель недоступна/);
});
test('malformed complete report is rejected', async () => {
  await assert.rejects(readReportStream(response('event: complete\ndata: {"answer":"ok"}\n\n'),()=>{}), /Некорректный/);
});
