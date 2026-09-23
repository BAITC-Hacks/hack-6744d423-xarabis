import type { Feature, FeatureCollection, Geometry } from "geojson";
import {
  DISTRICTS,
  type Decision,
  type DistrictId,
  type Measure,
} from "./caseData";

export const DISTRICT_FOCUS: Record<DistrictId, [number, number]> = {
  esil: [71.43, 51.11],
  almaty: [71.52, 51.15],
  saryarka: [71.39, 51.19],
  baikonur: [71.45, 51.19],
  nura: [71.35, 51.16],
};
const KINDS = [
  "bus",
  "signals",
  "lrt",
  "park",
  "cleanAir",
  "greenery",
  "school",
  "clinic",
  "sport",
  "lighting",
  "crossing",
  "digital",
  "utilities",
  "emergency",
] as const;
export type ProjectKind = (typeof KINDS)[number];
const SHORT_NAMES = [
  "Автобусы",
  "Светофоры",
  "ЛРТ",
  "Парк",
  "Чистый воздух",
  "Озеленение",
  "Школа",
  "Поликлиника",
  "Спорт",
  "Освещение",
  "Переход",
  "Обращения",
  "Сети ЖКХ",
  "Бригады",
];
const COLORS = {
  transport: "#247eac",
  ecology: "#2e925b",
  social: "#c27b27",
  safety: "#b26e43",
  services: "#4e7192",
};
export type ProjectPreview = {
  id: string;
  measureId: string;
  districtId: DistrictId;
  kind: ProjectKind;
  label: string;
  shortLabel: string;
  color: string;
  coordinates: [number, number];
};

/** Display-only placements around OSM samples, never proposed cadastral addresses. */
export function buildProjectPreviews(
  decisions: Decision[],
  measures: Measure[],
): ProjectPreview[] {
  return decisions.flatMap((decision) => {
    const measure = measures.find((item) => item.id === decision.measureId);
    if (!measure) return [];
    const index = Number(measure.id.slice(1)) - 1;
    const kind = KINDS[index];
    if (!kind) return [];
    const ids = decision.districtId
      ? [decision.districtId]
      : DISTRICTS.map((district) => district.id);
    return ids.map((districtId) => {
      const [lon, lat] = DISTRICT_FOCUS[districtId];
      const angle = index * 2.39996;
      const radius = 150 + (index % 3) * 65;
      return {
        id: `${measure.id}:${districtId}`,
        measureId: measure.id,
        districtId,
        kind,
        label: measure.name,
        shortLabel: SHORT_NAMES[index],
        color: COLORS[measure.category],
        coordinates: [
          lon + (Math.cos(angle) * radius) / 69800,
          lat + (Math.sin(angle) * radius) / 111320,
        ] as [number, number],
      };
    });
  });
}

export function projectGeoJSON(projects: ProjectPreview[]): FeatureCollection {
  const features: Feature<Geometry>[] = [];
  for (const project of projects) {
    const [x, y] = project.coordinates;
    const properties = {
      id: project.id,
      color: project.color,
      districtId: project.districtId,
      label: project.label,
    };
    const green = project.kind === "park" || project.kind === "greenery";
    const height = green
      ? 3
      : project.kind === "school" || project.kind === "clinic"
        ? 24
        : project.kind === "sport"
          ? 5
          : 9;
    const dx = green ? 0.00065 : 0.0003;
    const dy = green ? 0.0004 : 0.0002;
    features.push({
      type: "Feature",
      properties: { ...properties, height },
      geometry: {
        type: "Polygon",
        coordinates: [
          [
            [x - dx, y - dy],
            [x + dx, y - dy],
            [x + dx, y + dy],
            [x - dx, y + dy],
            [x - dx, y - dy],
          ],
        ],
      },
    });
    if (["bus", "lrt", "utilities"].includes(project.kind)) {
      features.push({
        type: "Feature",
        properties,
        geometry: {
          type: "LineString",
          coordinates: [
            [x - 0.0017, y - 0.0007],
            [x, y],
            [x + 0.0015, y + 0.0008],
          ],
        },
      });
    }
    if (green) {
      for (let i = 0; i < 5; i++) {
        const tx = x + ((i % 3) - 1) * 0.00032,
          ty = y + (Math.floor(i / 3) - 0.5) * 0.0003;
        features.push({
          type: "Feature",
          properties: { ...properties, color: "#246e46", height: 11 },
          geometry: {
            type: "Polygon",
            coordinates: [
              [
                [tx - 0.00009, ty - 0.00006],
                [tx + 0.00009, ty - 0.00006],
                [tx + 0.00009, ty + 0.00006],
                [tx - 0.00009, ty + 0.00006],
                [tx - 0.00009, ty - 0.00006],
              ],
            ],
          },
        });
      }
    }
  }
  return { type: "FeatureCollection", features };
}
