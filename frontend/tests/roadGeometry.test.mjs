import {test} from 'node:test';
import assert from 'node:assert/strict';
import {roadPoint,signalPost} from '../src/roadGeometry.ts';
test('divider follows the middle of the road, not either driving lane',()=>{
  assert.equal(roadPoint(22,'center').z,9);
  assert.equal(roadPoint(22,0).z,9.62);
  assert.equal(roadPoint(66,1).z,8.38);
});
test('signal poles stand outside both lanes at every stop line',()=>{
  for(const lane of [0,1])for(const distance of [22,66]){
    const post=signalPost(distance,lane);
    assert.ok(Math.abs(post.z)>10.65,`pole in road: ${JSON.stringify(post)}`);
  }
});
test('opposing lanes face opposite directions at the same road side',()=>{
  assert.equal(roadPoint(22,0).angle,0);
  assert.equal(roadPoint(66,1).angle,Math.PI);
});
