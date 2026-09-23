export interface TrafficCar {
  id: number;
  distance: number;
  speed: number;
  lane: number;
}

export interface TrafficConfig {
  quality: number;
  repaired: boolean;
  signals: boolean;
  loopLength: number;
}

const clamp = (value: number, min: number, max: number) => Math.min(max, Math.max(min, value));
const wrap = (value: number, length: number) => ((value % length) + length) % length;
const score = (value: number) => clamp(Number.isFinite(value) ? value : 0, 0, 100);

/** Speeds are loop fractions/second; advanceTraffic returns scene units/second. */
export function trafficProfile(quality: number): { carCount: number; desiredSpeed: number; damage: number } {
  const healthy = score(quality) / 100;
  return { carCount: 10 + 2 * Math.round((1 - healthy) * 11), desiredSpeed: 0.025 + healthy * 0.065, damage: 1 - healthy };
}

export function createTraffic(quality: number, loopLength: number): TrafficCar[] {
  if (!(loopLength > 0) || !Number.isFinite(loopLength)) return [];
  const profile = trafficProfile(quality);
  const perLane = profile.carCount / 2;
  return Array.from({ length: profile.carCount }, (_, id) => ({
    id,
    lane: id < perLane ? 0 : 1,
    distance: ((id % perLane) + (id < perLane ? 0 : 0.5)) * loopLength / perLane,
    speed: profile.desiredSpeed * loopLength,
  }));
}

/** Both lane signals use a 12-second cycle: red for 5s, or 2s after upgrading. */
export function isSignalGreen(time: number, signals: boolean): boolean {
  return wrap(time, 12) >= (signals ? 2 : 5);
}

/**
 * Distance increases along each lane's own direction; render lane 1 in reverse.
 * Signals stand at 25% and 75%; damage occupies 45–60% of each lane's loop.
 * `time` is the interval start in seconds. Delays above 5s are capped to avoid
 * teleporting after a suspended tab; substeps preserve spacing across the seam.
 */
export function advanceTraffic(cars: TrafficCar[], config: TrafficConfig, dt: number, time: number): TrafficCar[] {
  const length = config.loopLength;
  if (!(length > 0) || !Number.isFinite(length)) return cars.map((car) => ({ ...car }));
  let next = cars.map((car) => ({ ...car, distance: wrap(car.distance, length) }));
  const duration = clamp(Number.isFinite(dt) ? dt : 0, 0, 5);
  if (duration === 0) return next;
  const steps = Math.ceil(duration / 0.05);
  const step = duration / steps;
  const profile = trafficProfile(config.quality);
  const minGap = length * 0.035;
  const desired = profile.desiredSpeed * length;

  for (let tick = 0; tick < steps; tick += 1) {
    const green = isSignalGreen(time + tick * step, config.signals);
    const previous = next;
    next = previous.map((car) => {
      const fraction = car.distance / length;
      const damaged = !config.repaired && fraction >= 0.45 && fraction <= 0.6;
      const targetSpeed = desired * (damaged ? 1 - profile.damage * 0.84 : 1);
      let movement = targetSpeed * step;

      // Use the leader's previous position, so simultaneous moves cannot
      // consume another car's reserved gap, including across the loop seam.
      for (const leader of previous) {
        if (leader.id === car.id || leader.lane !== car.lane) continue;
        const gap = wrap(leader.distance - car.distance, length);
        movement = Math.min(movement, Math.max(0, gap - minGap));
      }
      if (!green) {
        for (const stop of [length * 0.25, length * 0.75]) {
          const gap = Math.abs(stop - car.distance) < 1e-9 ? 0 : wrap(stop - car.distance, length);
          movement = Math.min(movement, gap);
        }
      }
      return { ...car, distance: wrap(car.distance + movement, length), speed: movement / step };
    });
  }
  return next;
}

/** Continuous 24h sky factors with a smooth twilight around sunrise/sunset. */
export function daylight(hour: number): { light: number; night: number; sunHeight: number } {
  const sunHeight = Math.cos((wrap(hour, 24) - 12) * Math.PI / 12);
  const twilight = clamp((sunHeight + 0.18) / 0.48, 0, 1);
  const light = twilight * twilight * (3 - 2 * twilight);
  return { light, night: 1 - light, sunHeight };
}

export function ratingCategory(value: number): 'critical' | 'warning' | 'good' {
  return score(value) < 40 ? 'critical' : score(value) < 65 ? 'warning' : 'good';
}

export function ratingColor(value: number): string {
  const anchors: [number, number[]][] = [
    [0, [190, 35, 50]], [39, [242, 93, 67]],
    [40, [239, 166, 45]], [64, [237, 213, 78]],
    [65, [111, 191, 95]], [100, [28, 143, 105]],
  ];
  const rating = score(value);
  const upper = anchors.findIndex(([position]) => position >= rating);
  const [end, endColor] = anchors[Math.max(0, upper)];
  const [start, startColor] = anchors[Math.max(0, upper - 1)];
  const blend = end === start ? 0 : (rating - start) / (end - start);
  return '#' + startColor.map((channel, index) => Math.round(channel + (endColor[index] - channel) * blend).toString(16).padStart(2, '0')).join('');
}
