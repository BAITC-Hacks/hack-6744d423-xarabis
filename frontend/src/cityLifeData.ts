import type { FeatureCollection, LineString, Polygon, MultiPolygon } from "geojson";
import type { DistrictId } from "./caseData";
import { DISTRICT_FOCUS } from "./projectPreview";

export type XY = [number, number];
export const MAP_ORIGIN: XY = [71.43, 51.14];
const EARTH_CIRCUMFERENCE = 40075016.68557849;
export const MERCATOR_SCALE = 1 / (EARTH_CIRCUMFERENCE * Math.cos(MAP_ORIGIN[1] * Math.PI / 180));
const mercator = ([lon, lat]: XY): XY => [(lon + 180) / 360, (1 - Math.log(Math.tan(Math.PI / 4 + lat * Math.PI / 360)) / Math.PI) / 2];
export const MERCATOR_ORIGIN = mercator(MAP_ORIGIN);
export function localPoint(coordinates: XY): XY {
  const point = mercator(coordinates);
  return [(point[0] - MERCATOR_ORIGIN[0]) / MERCATOR_SCALE, (MERCATOR_ORIGIN[1] - point[1]) / MERCATOR_SCALE];
}
export function geographicPoint([x, y]: XY): XY {
  const mx = MERCATOR_ORIGIN[0] + x * MERCATOR_SCALE;
  const my = MERCATOR_ORIGIN[1] - y * MERCATOR_SCALE;
  return [mx * 360 - 180, Math.atan(Math.sinh(Math.PI * (1 - 2 * my))) * 180 / Math.PI];
}

export type RoadProperties = { districtId: DistrictId; osmId: number; name?: string; oneway?: string; bridge?: string; highway?: string };
export type RoadCollection = FeatureCollection<LineString, RoadProperties>;
export type ParkCollection = FeatureCollection<Polygon | MultiPolygon, { districtId: DistrictId }>;
export type TravelRoute = { id: number; districtId: DistrictId; name: string; points: XY[]; cumulative: number[]; length: number; oneWay: boolean; bridge: boolean };

export function prepareRoutes(data: RoadCollection): TravelRoute[] {
  return data.features.flatMap((feature) => {
    if (feature.geometry?.type !== "LineString" || !feature.properties) return [];
    let coordinates = feature.geometry.coordinates.filter((point) => point.length >= 2 && point.slice(0,2).every(Number.isFinite));
    if (feature.properties.oneway === "-1") coordinates = [...coordinates].reverse();
    const points: XY[] = [];
    for (const coordinate of coordinates) {
      const p = localPoint(coordinate.slice(0,2) as XY), previous = points.at(-1);
      if (!previous || Math.hypot(p[0]-previous[0], p[1]-previous[1]) > .5) points.push(p);
    }
    if (points.length < 2) return [];
    const cumulative = [0];
    for (let index=1; index<points.length; index++) cumulative.push(cumulative[index-1] + Math.hypot(points[index][0]-points[index-1][0],points[index][1]-points[index-1][1]));
    const length = cumulative.at(-1)!;
    if (length < 70) return [];
    return [{ id: feature.properties.osmId, districtId: feature.properties.districtId,
      name: feature.properties.name || "Улица района", points, cumulative, length,
      oneWay: ["yes", "1", "true", "-1"].includes(feature.properties.oneway ?? ""),
      bridge: Boolean(feature.properties.bridge && feature.properties.bridge !== "no"),
    }];
  });
}

export function sampleRoute(route: TravelRoute, distance: number, direction = 1, lane = 2.4) {
  const d = Math.max(0, Math.min(route.length - .001, distance));
  let index = 1;
  while (index < route.cumulative.length - 1 && route.cumulative[index] < d) index++;
  const a = route.points[index-1], b = route.points[index];
  const segmentLength = route.cumulative[index]-route.cumulative[index-1];
  const t = (d-route.cumulative[index-1])/segmentLength;
  const angle = Math.atan2(b[1]-a[1], b[0]-a[0]) + (direction < 0 ? Math.PI : 0);
  return { x: a[0]+(b[0]-a[0])*t+Math.sin(angle)*lane, y: a[1]+(b[1]-a[1])*t-Math.cos(angle)*lane, angle };
}

export function neighborhoodRoutes(routes: TravelRoute[], districtId: DistrictId, count=14): TravelRoute[] {
  const center = localPoint(DISTRICT_FOCUS[districtId]);
  const distance = (route: TravelRoute) => {
    let minimum = Infinity;
    for (let index = 1; index < route.points.length; index++) {
      const a = route.points[index-1], b = route.points[index];
      const dx = b[0] - a[0], dy = b[1] - a[1];
      const projection = Math.max(0, Math.min(1,
        ((center[0] - a[0]) * dx + (center[1] - a[1]) * dy) / (dx * dx + dy * dy),
      ));
      minimum = Math.min(minimum, Math.hypot(
        a[0] + dx * projection - center[0],
        a[1] + dy * projection - center[1],
      ));
    }
    return minimum;
  };
  return routes
    .filter((route)=>route.districtId===districtId)
    .map((route)=>({route, distance: distance(route)}))
    .sort((a,b)=>a.distance-b.distance)
    .slice(0,count)
    .map(({route})=>route);
}

export function pointInRing([x,y]: XY, ring: XY[]) {
  let inside=false;
  for(let i=0,j=ring.length-1;i<ring.length;j=i++) {
    const a=ring[i],b=ring[j];
    if((a[1]>y)!==(b[1]>y) && x < (b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]) inside=!inside;
  }
  return inside;
}

/** Decorative tree locations inside OSM park footprints, not a tree inventory. */
export function parkTrees(parks: ParkCollection, districtId: DistrictId): XY[] {
  const center=localPoint(DISTRICT_FOCUS[districtId]);
  const candidates: XY[]=[];
  for(const feature of parks.features.filter((f)=>f.properties?.districtId===districtId)) {
    const polygons=feature.geometry.type==="Polygon"?[feature.geometry.coordinates]:feature.geometry.coordinates;
    for(const polygon of polygons) {
      const rings=polygon.map((ring)=>ring.map((p)=>localPoint(p as XY)));
      const outer=rings[0]; if(!outer?.length) continue;
      const minX=Math.max(center[0]-2600,Math.min(...outer.map(p=>p[0]))),maxX=Math.min(center[0]+2600,Math.max(...outer.map(p=>p[0])));
      const minY=Math.max(center[1]-2600,Math.min(...outer.map(p=>p[1]))),maxY=Math.min(center[1]+2600,Math.max(...outer.map(p=>p[1])));
      // Bounded sampling also protects against accidentally huge polygons.
      const step=Math.max(28,Math.sqrt(Math.max(0,(maxX-minX)*(maxY-minY))/180));
      for(let x=minX+step/2;x<maxX;x+=step) for(let y=minY+step/2;y<maxY;y+=step) {
        const p:XY=[x+Math.sin(x+y)*4,y+Math.cos(x-y)*4];
        if(pointInRing(p,outer)&&!rings.slice(1).some((hole)=>pointInRing(p,hole))) candidates.push(p);
      }
    }
  }
  return candidates.sort((a,b)=>Math.hypot(a[0]-center[0],a[1]-center[1])-Math.hypot(b[0]-center[0],b[1]-center[1])).slice(0,180);
}
