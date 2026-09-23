import type { DistrictId } from "./caseData";
import type { DistrictNetwork } from "./cityNetwork";

/** Synthetic map data for the visual demo only; Python/backend data replaces this at API integration. */
const DEMO_NETWORKS: Record<DistrictId, DistrictNetwork> = {
  esil: {
    districtId: "esil",
    nodes: [
      { id: "e1", x: -3.2, z: -1.8, signal: false },
      { id: "e2", x: -1.1, z: -0.6, signal: true },
      { id: "e3", x: 1, z: 0.6, signal: true },
      { id: "e4", x: 3.2, z: 1.5, signal: false },
      { id: "e5", x: -1.1, z: 2.2, signal: false },
    ],
    roads: [
      { from: "e1", to: "e2", type: "avenue", lanes: 3, oneWay: false, bridge: false, busLane: true },
      { from: "e2", to: "e3", type: "street", lanes: 2, oneWay: true, bridge: true, busLane: false },
      { from: "e3", to: "e4", type: "avenue", lanes: 3, oneWay: false, bridge: false, busLane: true },
      { from: "e2", to: "e5", type: "yard", lanes: 1, oneWay: false, bridge: false, busLane: false },
    ],
    places: [
      { type: "stop", x: -1.45, z: -1.15, radius: 0.16 },
      { type: "school", x: -1.8, z: 2.1, radius: 0.32, measure: "school" },
      { type: "park", x: 2.45, z: 0.45, radius: 0.38 },
    ],
    busRoute: ["e1", "e2", "e3", "e4"],
  },
  almaty: {
    districtId: "almaty",
    nodes: [
      { id: "a1", x: -3, z: 1.9, signal: false },
      { id: "a2", x: -0.9, z: 0.5, signal: true },
      { id: "a3", x: 1.4, z: -0.3, signal: true },
      { id: "a4", x: 3.1, z: -1.7, signal: false },
      { id: "a5", x: 0.2, z: 2.5, signal: false },
    ],
    roads: [
      { from: "a1", to: "a2", type: "street", lanes: 2, oneWay: false, bridge: false, busLane: true },
      { from: "a2", to: "a3", type: "avenue", lanes: 3, oneWay: false, bridge: true, busLane: false },
      { from: "a3", to: "a4", type: "street", lanes: 2, oneWay: true, bridge: false, busLane: false },
      { from: "a2", to: "a5", type: "yard", lanes: 1, oneWay: false, bridge: false, busLane: false },
    ],
    places: [
      { type: "home", x: -2.2, z: 1.1, radius: 0.28 },
      { type: "stop", x: 1, z: -0.6, radius: 0.16 },
      { type: "shop", x: 0.5, z: 2.3, radius: 0.24 },
    ],
    busRoute: ["a1", "a2", "a3", "a4"],
  },
  saryarka: {
    districtId: "saryarka",
    nodes: [
      { id: "s1", x: -3.1, z: -1.7, signal: false },
      { id: "s2", x: -1.2, z: 0.2, signal: true },
      { id: "s3", x: 0.8, z: 1.6, signal: false },
      { id: "s4", x: 3, z: 0.8, signal: true },
      { id: "s5", x: -0.5, z: -2.3, signal: false },
    ],
    roads: [
      { from: "s1", to: "s2", type: "street", lanes: 2, oneWay: false, bridge: false, busLane: false },
      { from: "s2", to: "s3", type: "avenue", lanes: 3, oneWay: false, bridge: false, busLane: true },
      { from: "s3", to: "s4", type: "street", lanes: 2, oneWay: true, bridge: false, busLane: false },
      { from: "s2", to: "s5", type: "yard", lanes: 1, oneWay: false, bridge: false, busLane: false },
    ],
    places: [
      { type: "park", x: 2.1, z: 1.9, radius: 0.35, measure: "park" },
      { type: "office", x: -2.3, z: -1.4, radius: 0.27 },
      { type: "stop", x: 0.3, z: 1.1, radius: 0.16 },
    ],
    busRoute: ["s1", "s2", "s3", "s4"],
  },
  baikonur: {
    districtId: "baikonur",
    nodes: [
      { id: "b1", x: -3, z: 0.5, signal: false },
      { id: "b2", x: -1, z: -1, signal: true },
      { id: "b3", x: 1, z: 0.5, signal: true },
      { id: "b4", x: 3, z: -0.8, signal: false },
      { id: "b5", x: 0, z: 2.5, signal: false },
    ],
    roads: [
      { from: "b1", to: "b2", type: "avenue", lanes: 2, oneWay: false, bridge: false, busLane: true },
      { from: "b2", to: "b3", type: "street", lanes: 2, oneWay: false, bridge: false, busLane: false },
      { from: "b3", to: "b4", type: "avenue", lanes: 3, oneWay: true, bridge: true, busLane: false },
      { from: "b3", to: "b5", type: "yard", lanes: 1, oneWay: false, bridge: false, busLane: false },
    ],
    places: [
      { type: "office", x: -2.2, z: 1.5, radius: 0.28 },
      { type: "stop", x: 1.6, z: -0.3, radius: 0.16 },
      { type: "school", x: 0.4, z: 2.1, radius: 0.3 },
    ],
    busRoute: ["b1", "b2", "b3", "b4"],
  },
  nura: {
    districtId: "nura",
    nodes: [
      { id: "n1", x: -3.1, z: -1.7, signal: false },
      { id: "n2", x: -1, z: -0.4, signal: true },
      { id: "n3", x: 1, z: 0.7, signal: true },
      { id: "n4", x: 3.2, z: 1.8, signal: false },
      { id: "n5", x: 0.1, z: -2.4, signal: false },
    ],
    roads: [
      { from: "n1", to: "n2", type: "avenue", lanes: 3, oneWay: false, bridge: false, busLane: true },
      { from: "n2", to: "n3", type: "street", lanes: 2, oneWay: true, bridge: true, busLane: false },
      { from: "n3", to: "n4", type: "avenue", lanes: 2, oneWay: false, bridge: false, busLane: true },
      { from: "n2", to: "n5", type: "yard", lanes: 1, oneWay: false, bridge: false, busLane: false },
    ],
    places: [
      { type: "home", x: -2.1, z: -1.3, radius: 0.3 },
      { type: "stop", x: -0.2, z: -0.85, radius: 0.16, measure: "transit" },
      { type: "school", x: 1.7, z: 2.1, radius: 0.32 },
    ],
    busRoute: ["n1", "n2", "n3", "n4"],
  },
};

export function getCityNetworkDemo(districtId: DistrictId): DistrictNetwork {
  return DEMO_NETWORKS[districtId];
}
