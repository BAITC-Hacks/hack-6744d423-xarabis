import type { DistrictId } from "./caseData";

/** Display-only street-network contract supplied by the city/data team. */
export type CityNode = {
  id: string;
  x: number;
  z: number;
  signal: boolean;
};

export type CityRoad = {
  from: string;
  to: string;
  type: "avenue" | "street" | "yard";
  lanes: 1 | 2 | 3;
  oneWay: boolean;
  bridge: boolean;
  busLane?: boolean;
};

export type CityPlace = {
  type: "home" | "school" | "office" | "park" | "shop" | "stop";
  x: number;
  z: number;
  radius: number;
  measure?: "transit" | "park" | "school" | "lights";
};

/** Coordinates are local to this district; its center is (0, 0). */
export type DistrictNetwork = {
  districtId: DistrictId;
  nodes: CityNode[];
  roads: CityRoad[];
  places: CityPlace[];
  busRoute: string[];
};
