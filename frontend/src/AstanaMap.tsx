import { useEffect, useRef, useState } from "react";
import * as maplibregl from "maplibre-gl";
import type { LngLatBoundsLike, Map as MapLibreMap, Marker } from "maplibre-gl";
import workerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url";
import "maplibre-gl/dist/maplibre-gl.css";
import type { DistrictId } from "./caseData";
import { offlineAstanaStyle } from "./offlineAstanaStyle";

maplibregl.setWorkerUrl(workerUrl);

/** One-time OSM Nominatim lookups, 2026-09-23. These are district label points, not legal boundaries. */
const DISTRICTS: { id: DistrictId; name: string; coordinates: [number, number]; focus: [number, number]; localFocus: [number, number]; osmRelation: number }[] = [
  { id: "saryarka", name: "Сарыарка", coordinates: [71.3226517, 51.1988462], focus: [71.370, 51.190], localFocus: [71.39, 51.19], osmRelation: 3486954 },
  { id: "baikonur", name: "Байконур", coordinates: [71.4580973, 51.2264690], focus: [71.455, 51.192], localFocus: [71.45, 51.19], osmRelation: 8593081 },
  { id: "almaty", name: "Алматы", coordinates: [71.5473172, 51.1550554], focus: [71.505, 51.158], localFocus: [71.52, 51.15], osmRelation: 3482819 },
  { id: "nura", name: "Нура", coordinates: [71.3160362, 51.1008961], focus: [71.365, 51.116], localFocus: [71.35, 51.16], osmRelation: 20593940 },
  { id: "esil", name: "Есиль", coordinates: [71.4106032, 51.0592468], focus: [71.4305, 51.1283], localFocus: [71.43, 51.11], osmRelation: 3479876 },
];

const STYLE_URL = "https://tiles.openfreemap.org/styles/liberty";
const DISTRICT_BOUNDS: LngLatBoundsLike = [[71.25, 51.025], [71.61, 51.255]];

function showCity(map: MapLibreMap, animate: boolean) {
  map.fitBounds(DISTRICT_BOUNDS, {
    padding: { top: 85, right: 88, bottom: 82, left: 68 },
    pitch: 28,
    bearing: 0,
    duration: animate ? 850 : 0,
    maxZoom: 11.2,
  });
}

function focusDistrict(map: MapLibreMap, district: (typeof DISTRICTS)[number], local: boolean) {
  map.flyTo({ center: local ? district.localFocus : district.focus, zoom: local ? 14.65 : 14.25, pitch: 58, bearing: -24, duration: 900, essential: true });
}

function showCenter(map: MapLibreMap, local: boolean) {
  map.flyTo({ center: local ? [71.52, 51.15] : [71.4305, 51.1283], zoom: 15.3, pitch: 62, bearing: -24, duration: 1000, essential: true });
}

function addBuildingExtrusions(map: MapLibreMap) {
  if (map.getLayer("building-3d")) {
    map.setPaintProperty("building-3d", "fill-extrusion-color", [
      "interpolate", ["linear"], ["to-number", ["get", "render_height"], 8],
      0, "#b9c7bd", 40, "#dacbad", 120, "#f0dfb9",
    ]);
    map.setPaintProperty("building-3d", "fill-extrusion-opacity", 0.94);
    return;
  }
  if (!map.getSource("openmaptiles") || map.getLayer("astana-3d-buildings")) return;
  const firstLabel = map.getStyle().layers.find((layer) => layer.type === "symbol")?.id;
  map.addLayer({
    id: "astana-3d-buildings",
    source: "openmaptiles",
    "source-layer": "building",
    type: "fill-extrusion",
    minzoom: 13,
    filter: ["!=", ["get", "hide_3d"], true],
    paint: {
      "fill-extrusion-color": [
        "interpolate", ["linear"], ["to-number", ["get", "render_height"], 0],
        0, "#91a6a2", 40, "#bec8be", 120, "#e1c49b",
      ],
      "fill-extrusion-height": ["max", 8, ["to-number", ["get", "render_height"], 8]],
      "fill-extrusion-base": ["to-number", ["get", "render_min_height"], 0],
      "fill-extrusion-opacity": 0.94,
    },
  }, firstLabel);
}

function addDistrictBoundaries(map: MapLibreMap, selectedDistrict: DistrictId) {
  const firstLabel = map.getStyle().layers.find((layer) => layer.type === "symbol")?.id;
  map.addSource("astana-districts", {
    type: "geojson",
    data: `${import.meta.env.BASE_URL}data/astana/districts.geojson`,
  });
  map.addLayer({
    id: "astana-district-fill", type: "fill", source: "astana-districts",
    paint: { "fill-color": "#2e8c71", "fill-opacity": 0.035 },
  }, firstLabel);
  map.addLayer({
    id: "astana-district-outline", type: "line", source: "astana-districts",
    paint: { "line-color": "#327969", "line-width": ["interpolate", ["linear"], ["zoom"], 9, 1.2, 14, 2.2], "line-opacity": 0.75 },
  }, firstLabel);
  map.addLayer({
    id: "astana-selected-fill", type: "fill", source: "astana-districts",
    filter: ["==", ["get", "districtId"], selectedDistrict],
    paint: { "fill-color": "#d6ab58", "fill-opacity": 0.11 },
  }, firstLabel);
  map.addLayer({
    id: "astana-selected-outline", type: "line", source: "astana-districts",
    filter: ["==", ["get", "districtId"], selectedDistrict],
    paint: { "line-color": "#b77c30", "line-width": ["interpolate", ["linear"], ["zoom"], 9, 2, 14, 3], "line-opacity": 0.95 },
  }, firstLabel);
}

export function AstanaMap({ selectedDistrict, onSelectDistrict, onFallback }: {
  selectedDistrict: DistrictId;
  onSelectDistrict: (districtId: DistrictId) => void;
  onFallback: () => void;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const markersRef = useRef<{ id: DistrictId; element: HTMLButtonElement; marker: Marker }[]>([]);
  const selectionRef = useRef(selectedDistrict);
  const onSelectRef = useRef(onSelectDistrict);
  const initialSelectionRef = useRef(true);
  onSelectRef.current = onSelectDistrict;
  const [sourceMode, setSourceMode] = useState<"online" | "local">("online");
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    setStatus("loading");

    let map: MapLibreMap;
    try {
      map = new maplibregl.Map({
        container,
        style: sourceMode === "online" ? STYLE_URL : offlineAstanaStyle(selectionRef.current),
        center: [71.4305, 51.1283],
        zoom: 10.8,
        pitch: 28,
        bearing: 0,
        maxPitch: 70,
        canvasContextAttributes: { antialias: true },
        cooperativeGestures: true,
      });
    } catch {
      setStatus("error");
      return;
    }
    mapRef.current = map;
    map.addControl(new maplibregl.NavigationControl({ showCompass: true }), "top-right");
    map.on("styleimagemissing", ({ id }) => {
      if (!map.hasImage(id)) map.addImage(id, { width: 1, height: 1, data: new Uint8Array(4) });
    });
    const timeout = window.setTimeout(() => {
      if (sourceMode === "online") setSourceMode("local");
      else setStatus((current) => current === "loading" ? "error" : current);
    }, 16000);

    map.on("load", () => {
      if (sourceMode === "online") {
        try { addDistrictBoundaries(map, selectionRef.current); } catch (error) { console.warn("District boundaries unavailable", error); }
        try { addBuildingExtrusions(map); } catch (error) { console.warn("3D buildings unavailable", error); }
      }
      if (map.getLayer("astana-district-fill")) {
        map.on("click", "astana-district-fill", (event) => {
          const district = DISTRICTS.find((item) => item.id === event.features?.[0]?.properties?.districtId);
          if (!district) return;
          if (selectionRef.current === district.id) focusDistrict(map, district, sourceMode === "local");
          onSelectRef.current(district.id);
        });
        map.on("mouseenter", "astana-district-fill", () => { map.getCanvas().style.cursor = "pointer"; });
        map.on("mouseleave", "astana-district-fill", () => { map.getCanvas().style.cursor = ""; });
      }
      for (const district of DISTRICTS) {
        const element = document.createElement("button");
        element.type = "button";
        element.className = "astana-district-pin";
        if (district.id === "esil" || district.id === "almaty") element.classList.add("is-east");
        element.setAttribute("aria-label", `Показать район ${district.name} на карте`);
        element.setAttribute("title", `Район ${district.name} · OSM relation ${district.osmRelation}`);
        const dot = document.createElement("span");
        dot.className = "astana-pin-dot";
        const name = document.createElement("span");
        name.textContent = district.name;
        element.append(dot, name);
        element.classList.toggle("is-active", district.id === selectionRef.current);
        element.addEventListener("click", (event) => {
          event.stopPropagation();
          if (selectionRef.current === district.id) focusDistrict(map, district, sourceMode === "local");
          onSelectRef.current(district.id);
        });
        const marker = new maplibregl.Marker({ element, anchor: district.id === "esil" || district.id === "almaty" ? "bottom-right" : "bottom" }).setLngLat(district.coordinates).addTo(map);
        markersRef.current.push({ id: district.id, element, marker });
      }
      showCity(map, false);
      setStatus("ready");
      window.clearTimeout(timeout);
    });

    return () => {
      window.clearTimeout(timeout);
      for (const item of markersRef.current) item.marker.remove();
      markersRef.current = [];
      mapRef.current = null;
      map.remove();
    };
  }, [sourceMode]);

  useEffect(() => {
    selectionRef.current = selectedDistrict;
    for (const item of markersRef.current) item.element.classList.toggle("is-active", item.id === selectedDistrict);
    const map = mapRef.current;
    if (map?.getLayer("astana-selected-fill")) {
      map.setFilter("astana-selected-fill", ["==", ["get", "districtId"], selectedDistrict]);
      map.setFilter("astana-selected-outline", ["==", ["get", "districtId"], selectedDistrict]);
    }
    if (initialSelectionRef.current) {
      initialSelectionRef.current = false;
      return;
    }
    const district = DISTRICTS.find((item) => item.id === selectedDistrict);
    if (map && district && status === "ready") {
      focusDistrict(map, district, sourceMode === "local");
    }
  }, [selectedDistrict]);

  return <div className="astana-map-shell" role="region" aria-label="Реальная карта Астаны с пятью районами из задания">
    <div ref={containerRef} className="astana-map" />
    <div className="astana-map-label"><span className="astana-map-live" /> <strong>АСТАНА · РЕАЛЬНАЯ КАРТА</strong><small>{sourceMode === "online" ? "OSM / OpenFreeMap · актуальные границы · 3D-здания" : "Локальные OSM-слои · здания: демовыборка"}</small></div>
    {status === "ready" && <div className="astana-map-controls"><button type="button" onClick={() => mapRef.current && showCity(mapRef.current, true)}>Весь город</button><button type="button" onClick={() => mapRef.current && showCenter(mapRef.current, sourceMode === "local")}>3D квартал</button><button type="button" className="astana-source-toggle" onClick={() => setSourceMode((current) => current === "online" ? "local" : "online")}>{sourceMode === "online" ? "Локальная карта" : "Онлайн-карта"}</button></div>}
    {sourceMode === "local" && <a className="astana-local-credit" href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">© OpenStreetMap contributors · ODbL</a>}
    {status === "loading" && <div className="astana-map-state" role="status"><strong>Загружаем карту Астаны</strong><span>{sourceMode === "online" ? "Улицы и здания приходят из OpenFreeMap. При отсутствии сети откроется локальная карта." : "Открываем локальные районы, дороги, реку, парки и выборку зданий."}</span></div>}
    {status === "error" && <div className="astana-map-state is-error" role="alert"><strong>Карта временно недоступна</strong><span>Локальные геоданные не загрузились. Схема районов доступна без них.</span><button type="button" onClick={onFallback}>Открыть схему</button></div>}
  </div>;
}
