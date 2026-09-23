export const ROAD_LENGTH=88;
// Each lane has an increasing distance; lane 1 travels in the opposite direction.
export function roadPoint(distance:number,lane:number|'center'):{x:number;z:number;angle:number}{
  let t=((lane===1?ROAD_LENGTH-distance:distance)%ROAD_LENGTH+ROAD_LENGTH)%ROAD_LENGTH;
  const offset=lane==='center'?0:lane===1?-.62:.62,w=13+offset,h=9+offset;
  if(t<26)return{x:-w+2*w*t/26,z:h,angle:lane===1?Math.PI:0};
  t-=26;if(t<18)return{x:w,z:h-2*h*t/18,angle:lane===1?-Math.PI/2:Math.PI/2};
  t-=18;if(t<26)return{x:w-2*w*t/26,z:-h,angle:lane===1?0:Math.PI};
  t-=26;return{x:-w,z:-h+2*h*t/18,angle:lane===1?Math.PI/2:-Math.PI/2};
}
export function signalPost(distance:number,lane:number):{x:number;z:number}{
  const p=roadPoint(distance,lane);
  const horizontal=Math.abs(Math.sin(p.angle))<.5;
  return horizontal?{x:p.x,z:Math.sign(p.z)*11.3}:{x:Math.sign(p.x)*15.3,z:p.z};
}
