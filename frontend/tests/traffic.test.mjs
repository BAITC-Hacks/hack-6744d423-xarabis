import test from 'node:test';
import assert from 'node:assert/strict';

const traffic = await import('../src/traffic.ts').catch((error) => {
  if (error.code !== 'ERR_MODULE_NOT_FOUND') throw error;
  return {};
});

test('traffic module exposes the pure simulation contract', () => {
  for (const name of ['createTraffic', 'advanceTraffic', 'trafficProfile', 'daylight', 'ratingColor', 'ratingCategory', 'isSignalGreen']) {
    assert.equal(typeof traffic[name], 'function', `${name} must be implemented`);
  }
});

function assertGaps(cars, length) {
  for (const lane of [0, 1]) {
    const ordered = cars.filter((car) => car.lane === lane).sort((a, b) => a.distance - b.distance);
    for (let index = 0; index < ordered.length; index += 1) {
      const next = ordered[(index + 1) % ordered.length];
      const gap = (next.distance - ordered[index].distance + length) % length;
      assert.ok(gap >= length * 0.035 - 1e-7, `unsafe lane ${lane} gap ${gap}`);
    }
  }
}

test('poor transport creates denser, slower traffic with no overlapping spawn positions', () => {
  const bad = traffic.createTraffic(10, 100);
  const good = traffic.createTraffic(90, 100);
  assert.ok(bad.length > good.length);
  assert.ok(traffic.trafficProfile(10).desiredSpeed < traffic.trafficProfile(90).desiredSpeed);
  assert.ok(traffic.trafficProfile(10).damage > traffic.trafficProfile(90).damage);
  assert.deepEqual(new Set(bad.map((car) => car.lane)), new Set([0, 1]));
  assert.equal(new Set(bad.map((car) => car.id)).size, bad.length);
  assertGaps(bad, 100);
  assert.deepEqual(traffic.createTraffic(10, 100), bad);
});

test('red light stops a car before the line and reports its actual stationary speed', () => {
  let cars = [{ id: 0, lane: 0, distance: 24, speed: 4 }];
  const config = { quality: 100, repaired: true, signals: false, loopLength: 100 };
  assert.equal(traffic.isSignalGreen(0, false), false);
  for (let frame = 0; frame < 20; frame += 1) cars = traffic.advanceTraffic(cars, config, 0.1, frame * 0.1);
  assert.ok(cars[0].distance <= 25);
  assert.ok(cars[0].distance >= 24);
  assert.equal(cars[0].speed, 0);
  const released = traffic.advanceTraffic(cars, config, 0.5, 7);
  assert.ok(released[0].distance > 25);
  assert.ok(released[0].speed > 0);
});

test('traffic queues remain separated through wraparound and a delayed frame', () => {
  let cars = traffic.createTraffic(0, 100);
  const original = structuredClone(cars);
  const config = { quality: 0, repaired: false, signals: false, loopLength: 100 };
  for (let frame = 0; frame < 200; frame += 1) {
    cars = traffic.advanceTraffic(cars, config, frame === 100 ? 4 : 0.2, frame * 0.2);
    assertGaps(cars, 100);
    assert.ok(cars.every((car) => car.distance >= 0 && car.distance < 100 && car.speed >= 0));
  }
  assert.notDeepEqual(cars, original);
});

test('road repair removes the damaged section slowdown', () => {
  const initial = [{ id: 0, lane: 1, distance: 50, speed: 0 }];
  const base = { quality: 10, signals: false, loopLength: 100 };
  const damaged = traffic.advanceTraffic(initial, { ...base, repaired: false }, 0.5, 7);
  const repaired = traffic.advanceTraffic(initial, { ...base, repaired: true }, 0.5, 7);
  assert.ok(repaired[0].distance - 50 > (damaged[0].distance - 50) * 2);
  assert.deepEqual(initial, [{ id: 0, lane: 1, distance: 50, speed: 0 }]);
});

test('upgraded signals spend less of each cycle red', () => {
  let normal = 0;
  let upgraded = 0;
  for (let time = 0; time < 120; time += 0.1) {
    normal += Number(traffic.isSignalGreen(time, false));
    upgraded += Number(traffic.isSignalGreen(time, true));
  }
  assert.ok(upgraded > normal);
});

test('daylight is bright at noon, dark at midnight, and continuous across midnight', () => {
  assert.ok(traffic.daylight(12).light > traffic.daylight(0).light);
  assert.ok(traffic.daylight(0).night > traffic.daylight(12).night);
  assert.ok(traffic.daylight(12).sunHeight > 0);
  assert.ok(traffic.daylight(0).sunHeight < 0);
  assert.deepEqual(traffic.daylight(24), traffic.daylight(0));
  assert.deepEqual(traffic.daylight(-1), traffic.daylight(23));
  assert.ok(Math.abs(traffic.daylight(23.999).light - traffic.daylight(0.001).light) < 0.001);
});

test('district ratings obey the critical and good boundaries with distinct colors', () => {
  for (const [value, expected] of [[0, 'critical'], [39.99, 'critical'], [40, 'warning'], [64.99, 'warning'], [65, 'good'], [100, 'good']]) {
    assert.equal(traffic.ratingCategory(value), expected);
  }
  assert.notEqual(traffic.ratingColor(39), traffic.ratingColor(40));
  assert.notEqual(traffic.ratingColor(64), traffic.ratingColor(65));
  const red = traffic.ratingColor(10).match(/[0-9a-f]{2}/gi).map((channel) => parseInt(channel, 16));
  const green = traffic.ratingColor(90).match(/[0-9a-f]{2}/gi).map((channel) => parseInt(channel, 16));
  assert.ok(red[0] > red[1]);
  assert.ok(green[1] > green[0]);
  assert.equal(traffic.ratingColor(-10), traffic.ratingColor(0));
  assert.equal(traffic.ratingColor(110), traffic.ratingColor(100));
});
