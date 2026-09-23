import type { StyleSpecification } from "maplibre-gl";
import type { DistrictId } from "./caseData";

const asset = (name: string) => `${import.meta.env.BASE_URL}data/astana/${name}.geojson`;

/** Local OSM extract: five districts, arterial roads, water, parks and a building sample. */
export function offlineAstanaStyle(selectedDistrict: DistrictId): StyleSpecification {
  const selected = ["==", ["get", "districtId"], selectedDistrict];
  return {
    version: 8,
    name: "Астана · локальная геоподложка OSM",
    sources: {
      "astana-districts": { type: "geojson", data: asset("districts") },
      "astana-roads": { type: "geojson", data: asset("roads") },
      "astana-rivers": { type: "geojson", data: asset("rivers") },
      "astana-parks": { type: "geojson", data: asset("parks") },
      "astana-buildings": { type: "geojson", data: asset("buildings") },
    },
    layers: [
      { id: "local-ground", type: "background", paint: { "background-color": "#f4f4e9" } },
      { id: "astana-district-fill", type: "fill", source: "astana-districts", paint: { "fill-color": "#d5e8d8", "fill-opacity": 0.78 } },
      { id: "astana-selected-fill", type: "fill", source: "astana-districts", filter: selected, paint: { "fill-color": "#e6c67f", "fill-opacity": 0.35 } },
      { id: "astana-parks-fill", type: "fill", source: "astana-parks", paint: { "fill-color": "#a8ceb0", "fill-opacity": 0.9 } },
      { id: "astana-rivers-line", type: "line", source: "astana-rivers", paint: { "line-color": "#75adc2", "line-width": ["interpolate", ["linear"], ["zoom"], 9, 2.2, 15, 7], "line-opacity": 0.92 } },
      { id: "astana-road-casing", type: "line", source: "astana-roads", paint: { "line-color": "#c5bfa7", "line-width": ["interpolate", ["linear"], ["zoom"], 9, 1.7, 15, 8], "line-opacity": 0.88 } },
      { id: "astana-roads-line", type: "line", source: "astana-roads", paint: { "line-color": "#fff6dc", "line-width": ["interpolate", ["linear"], ["zoom"], 9, 0.8, 15, 6], "line-opacity": 0.98 } },
      { id: "astana-buildings-3d", type: "fill-extrusion", source: "astana-buildings", minzoom: 12,
        paint: { "fill-extrusion-color": ["interpolate", ["linear"], ["to-number", ["get", "levels"], 2], 0, "#a2b7a8", 8, "#d1c4a5", 20, "#f0d9ad"],
          "fill-extrusion-height": ["max", 7, ["to-number", ["get", "height"], ["*", ["to-number", ["get", "levels"], 2], 3]]],
          "fill-extrusion-base": 0, "fill-extrusion-opacity": 0.94 } },
      { id: "astana-district-outline", type: "line", source: "astana-districts", paint: { "line-color": "#3b776a", "line-width": ["interpolate", ["linear"], ["zoom"], 9, 1.4, 14, 2.4], "line-opacity": 0.88 } },
      { id: "astana-selected-outline", type: "line", source: "astana-districts", filter: selected, paint: { "line-color": "#b77c30", "line-width": ["interpolate", ["linear"], ["zoom"], 9, 2.5, 14, 3.6], "line-opacity": 0.98 } },
    ],
  } as StyleSpecification;
}
