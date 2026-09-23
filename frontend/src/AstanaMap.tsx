import { useEffect, useRef, useState } from "react";
import * as maplibregl from "maplibre-gl";
import type { LngLatBoundsLike, Map as MapLibreMap, Marker } from "maplibre-gl";
import workerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url";
import "maplibre-gl/dist/maplibre-gl.css";
import type { DistrictId } from "./caseData";
import type { CityLifeLayer, LifeOptions, LifeSummary } from "./CityLifeLayer";
import type { ParkCollection, RoadCollection } from "./cityLifeData";
import { offlineAstanaStyle } from "./offlineAstanaStyle";
import {
  DISTRICT_FOCUS,
  projectGeoJSON,
  type ProjectPreview,
} from "./projectPreview";

maplibregl.setWorkerUrl(workerUrl);

/** One-time OSM Nominatim lookups, 2026-09-23. These are district label points, not legal boundaries. */
const DISTRICTS: {
  id: DistrictId;
  name: string;
  coordinates: [number, number];
  focus: [number, number];
  localFocus: [number, number];
  osmRelation: number;
}[] = [
  {
    id: "saryarka",
    name: "Сарыарка",
    coordinates: [71.3226517, 51.1988462],
    focus: [71.37, 51.19],
    localFocus: [71.39, 51.19],
    osmRelation: 3486954,
  },
  {
    id: "baikonur",
    name: "Байконур",
    coordinates: [71.4580973, 51.226469],
    focus: [71.455, 51.192],
    localFocus: [71.45, 51.19],
    osmRelation: 8593081,
  },
  {
    id: "almaty",
    name: "Алматы",
    coordinates: [71.5473172, 51.1550554],
    focus: [71.505, 51.158],
    localFocus: [71.52, 51.15],
    osmRelation: 3482819,
  },
  {
    id: "nura",
    name: "Нура",
    coordinates: [71.3160362, 51.1008961],
    focus: [71.365, 51.116],
    localFocus: [71.35, 51.16],
    osmRelation: 20593940,
  },
  {
    id: "esil",
    name: "Есиль",
    coordinates: [71.4106032, 51.0592468],
    focus: [71.4305, 51.1283],
    localFocus: [71.43, 51.11],
    osmRelation: 3479876,
  },
];

const STYLE_URL = "https://tiles.openfreemap.org/styles/liberty";
const DISTRICT_BOUNDS: LngLatBoundsLike = [
  [71.25, 51.025],
  [71.61, 51.255],
];
const pluralBus = (value: number) =>
  value % 100 >= 11 && value % 100 <= 14 ? "автобусов" :
    value % 10 === 1 ? "автобус" :
      value % 10 >= 2 && value % 10 <= 4 ? "автобуса" : "автобусов";

function showCity(map: MapLibreMap, animate: boolean) {
  map.fitBounds(DISTRICT_BOUNDS, {
    padding: { top: 85, right: 88, bottom: 82, left: 68 },
    pitch: 28,
    bearing: 0,
    duration: animate ? 850 : 0,
    maxZoom: 11.2,
  });
}

function focusDistrict(map: MapLibreMap, district: (typeof DISTRICTS)[number]) {
  map.flyTo({
    center: DISTRICT_FOCUS[district.id],
    zoom: 15.1,
    pitch: 53,
    bearing: -18,
    duration: 850,
  });
}

function addBuildingExtrusions(map: MapLibreMap) {
  if (map.getLayer("building-3d")) {
    map.setPaintProperty("building-3d", "fill-extrusion-color", [
      "interpolate",
      ["linear"],
      ["to-number", ["get", "render_height"], 8],
      0,
      "#b9c7bd",
      40,
      "#dacbad",
      120,
      "#f0dfb9",
    ]);
    map.setPaintProperty("building-3d", "fill-extrusion-opacity", 0.94);
    return;
  }
  if (!map.getSource("openmaptiles") || map.getLayer("astana-3d-buildings"))
    return;
  const firstLabel = map
    .getStyle()
    .layers.find((layer) => layer.type === "symbol")?.id;
  map.addLayer(
    {
      id: "astana-3d-buildings",
      source: "openmaptiles",
      "source-layer": "building",
      type: "fill-extrusion",
      minzoom: 13,
      filter: ["!=", ["get", "hide_3d"], true],
      paint: {
        "fill-extrusion-color": [
          "interpolate",
          ["linear"],
          ["to-number", ["get", "render_height"], 0],
          0,
          "#91a6a2",
          40,
          "#bec8be",
          120,
          "#e1c49b",
        ],
        "fill-extrusion-height": [
          "max",
          8,
          ["to-number", ["get", "render_height"], 8],
        ],
        "fill-extrusion-base": ["to-number", ["get", "render_min_height"], 0],
        "fill-extrusion-opacity": 0.94,
      },
    },
    firstLabel,
  );
}

function addDistrictBoundaries(map: MapLibreMap, selectedDistrict: DistrictId) {
  const firstLabel = map
    .getStyle()
    .layers.find((layer) => layer.type === "symbol")?.id;
  map.addSource("astana-districts", {
    type: "geojson",
    data: `${import.meta.env.BASE_URL}data/astana/districts.geojson`,
  });
  map.addLayer(
    {
      id: "astana-district-fill",
      type: "fill",
      source: "astana-districts",
      paint: { "fill-color": "#2e8c71", "fill-opacity": 0.035 },
    },
    firstLabel,
  );
  map.addLayer(
    {
      id: "astana-district-outline",
      type: "line",
      source: "astana-districts",
      paint: {
        "line-color": "#327969",
        "line-width": ["interpolate", ["linear"], ["zoom"], 9, 1.2, 14, 2.2],
        "line-opacity": 0.75,
      },
    },
    firstLabel,
  );
  map.addLayer(
    {
      id: "astana-selected-fill",
      type: "fill",
      source: "astana-districts",
      filter: ["==", ["get", "districtId"], selectedDistrict],
      paint: { "fill-color": "#d6ab58", "fill-opacity": 0.11 },
    },
    firstLabel,
  );
  map.addLayer(
    {
      id: "astana-selected-outline",
      type: "line",
      source: "astana-districts",
      filter: ["==", ["get", "districtId"], selectedDistrict],
      paint: {
        "line-color": "#b77c30",
        "line-width": ["interpolate", ["linear"], ["zoom"], 9, 2, 14, 3],
        "line-opacity": 0.95,
      },
    },
    firstLabel,
  );
}

export function AstanaMap({
  selectedDistrict,
  onSelectDistrict,
  onFallback,
  projects = [],
  projectsVisible = true,
  focus = "overview",
  cameraRevision = 0,
  districtValues,
  onSelectProject,
}: {
  selectedDistrict: DistrictId;
  onSelectDistrict: (districtId: DistrictId) => void;
  onFallback: () => void;
  projects?: ProjectPreview[];
  projectsVisible?: boolean;
  focus?: "overview" | "detail";
  cameraRevision?: number;
  districtValues?: Partial<Record<DistrictId, number | null>>;
  onSelectProject?: (project: ProjectPreview) => void;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const markersRef = useRef<
    { id: DistrictId; element: HTMLButtonElement; marker: Marker }[]
  >([]);
  const selectionRef = useRef(selectedDistrict);
  const onSelectRef = useRef(onSelectDistrict);
  const projectMarkersRef = useRef<Marker[]>([]);
  const lifeLayerRef = useRef<CityLifeLayer | null>(null);
  const onProjectRef = useRef(onSelectProject);
  onProjectRef.current = onSelectProject;
  onSelectRef.current = onSelectDistrict;
  const [sourceMode, setSourceMode] = useState<"online" | "local">("online");
  const [status, setStatus] = useState<"loading" | "ready" | "error">(
    "loading",
  );
  const [lifeStatus, setLifeStatus] = useState<"loading" | "ready" | "unavailable">("loading");
  const [lifeSummary, setLifeSummary] = useState<LifeSummary | null>(null);
  const [lifePlaying, setLifePlaying] = useState(
    () => !window.matchMedia("(prefers-reduced-motion: reduce)").matches,
  );
  const lifeOptionsRef = useRef<LifeOptions>({
    districtId: selectedDistrict,
    playing: lifePlaying,
    active: focus === "detail",
    speed: 1,
    projects: projectsVisible ? projects : [],
  });
  lifeOptionsRef.current = {
    districtId: selectedDistrict,
    playing: lifePlaying,
    active: focus === "detail",
    speed: 1,
    projects: projectsVisible ? projects : [],
  };

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    setStatus("loading");
    setLifeStatus("loading");
    setLifeSummary(null);
    let disposed = false;
    const lifeController = new AbortController();

    let map: MapLibreMap;
    try {
      map = new maplibregl.Map({
        container,
        style:
          sourceMode === "online"
            ? STYLE_URL
            : offlineAstanaStyle(selectionRef.current),
        center: [71.4305, 51.1283],
        zoom: 10.8,
        pitch: 28,
        bearing: 0,
        maxPitch: 70,
        canvasContextAttributes: { antialias: true },
        // The workbench itself does not scroll; wheel gestures belong to the map.
        cooperativeGestures: false,
        locale: {
          "NavigationControl.ZoomIn": "Приблизить карту",
          "NavigationControl.ZoomOut": "Отдалить карту",
          "NavigationControl.ResetBearing": "Повернуть карту; нажать — вернуть север",
          "AttributionControl.ToggleAttribution": "Источники карты",
        },
      });
    } catch {
      setStatus("error");
      return;
    }
    mapRef.current = map;
    const resize = new ResizeObserver(() => map.resize());
    resize.observe(container);
    map.addControl(
      new maplibregl.NavigationControl({ showCompass: true }),
      "top-right",
    );
    map.setMissingStyleImageResolver((id) => {
      if (!map.hasImage(id))
        map.addImage(id, { width: 1, height: 1, data: new Uint8Array(4) });
    });
    const timeout = window.setTimeout(() => {
      if (sourceMode === "online") setSourceMode("local");
      else setStatus((current) => (current === "loading" ? "error" : current));
    }, 16000);

    map.on("load", () => {
      if (sourceMode === "online") {
        try {
          addDistrictBoundaries(map, selectionRef.current);
        } catch (error) {
          console.warn("District boundaries unavailable", error);
        }
        try {
          addBuildingExtrusions(map);
        } catch (error) {
          console.warn("3D buildings unavailable", error);
        }
      }
      if (map.getLayer("astana-district-fill")) {
        map.on("click", "astana-district-fill", (event) => {
          const district = DISTRICTS.find(
            (item) => item.id === event.features?.[0]?.properties?.districtId,
          );
          if (!district) return;
          onSelectRef.current(district.id);
        });
        map.on("mouseenter", "astana-district-fill", () => {
          map.getCanvas().style.cursor = "pointer";
        });
        map.on("mouseleave", "astana-district-fill", () => {
          map.getCanvas().style.cursor = "";
        });
      }
      for (const district of DISTRICTS) {
        const element = document.createElement("button");
        element.type = "button";
        element.className = "astana-district-pin";
        if (district.id === "esil" || district.id === "almaty")
          element.classList.add("is-east");
        element.setAttribute(
          "aria-label",
          `Показать район ${district.name} на карте`,
        );
        element.setAttribute(
          "title",
          `Район ${district.name} · OSM relation ${district.osmRelation}`,
        );
        const dot = document.createElement("span");
        dot.className = "astana-pin-dot";
        const name = document.createElement("span");
        name.textContent = district.name;
        element.append(dot, name);
        element.classList.toggle(
          "is-active",
          district.id === selectionRef.current,
        );
        element.addEventListener("click", (event) => {
          event.stopPropagation();
          onSelectRef.current(district.id);
        });
        const marker = new maplibregl.Marker({
          element,
          anchor:
            district.id === "esil" || district.id === "almaty"
              ? "bottom-right"
              : "bottom",
        })
          .setLngLat(district.coordinates)
          .addTo(map);
        markersRef.current.push({ id: district.id, element, marker });
      }
      map.addSource("akim-projects", {
        type: "geojson",
        data: projectGeoJSON([]),
      });
      map.addLayer({
        id: "akim-project-buildings",
        type: "fill-extrusion",
        source: "akim-projects",
        minzoom: 12,
        filter: ["==", ["geometry-type"], "Polygon"],
        paint: {
          "fill-extrusion-color": ["get", "color"],
          "fill-extrusion-height": ["get", "height"],
          "fill-extrusion-base": 0,
          "fill-extrusion-opacity": 0.9,
        },
      });
      map.addLayer({
        id: "akim-project-routes",
        type: "line",
        source: "akim-projects",
        minzoom: 12,
        filter: ["==", ["geometry-type"], "LineString"],
        paint: {
          "line-color": ["get", "color"],
          "line-width": 7,
          "line-dasharray": [2, 1],
        },
      });
      const loadLife = async () => {
        try {
          const [module, roadsResponse, parksResponse] = await Promise.all([
            import("./CityLifeLayer"),
            fetch(`${import.meta.env.BASE_URL}data/astana/roads.geojson`, { signal: lifeController.signal }),
            fetch(`${import.meta.env.BASE_URL}data/astana/parks.geojson`, { signal: lifeController.signal }),
          ]);
          if (!roadsResponse.ok || !parksResponse.ok) throw new Error("Локальные слои улиц и парков недоступны");
          const [roads, parks] = await Promise.all([
            roadsResponse.json() as Promise<RoadCollection>,
            parksResponse.json() as Promise<ParkCollection>,
          ]);
          if (disposed || mapRef.current !== map) return;
          if (!Array.isArray(roads.features) || !Array.isArray(parks.features)) throw new Error("Некорректные данные улиц или парков");
          map.addSource("akim-life-roads", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
          map.addLayer({
            id: "akim-life-streets",
            type: "line",
            source: "akim-life-roads",
            minzoom: 13.2,
            paint: {
              "line-color": "#d8c798",
              "line-width": ["interpolate", ["linear"], ["zoom"], 13, 1.5, 17, 5],
              "line-opacity": 0.26,
            },
          }, "akim-project-routes");
          map.addLayer({
            id: "akim-life-transit",
            type: "line",
            source: "akim-life-roads",
            minzoom: 13.2,
            filter: ["==", ["get", "transit"], true],
            paint: {
              "line-color": "#258bab",
              "line-width": ["interpolate", ["linear"], ["zoom"], 13, 2, 17, 6],
              "line-dasharray": [2, 1.5],
              "line-opacity": 0.8,
            },
          }, "akim-project-routes");
          const layer = new module.CityLifeLayer(roads, parks, lifeOptionsRef.current, (summary) => {
            if (!disposed) setLifeSummary(summary);
          });
          map.addLayer(layer);
          lifeLayerRef.current = layer;
          setLifeStatus("ready");
        } catch (reason) {
          if (!disposed && !(reason instanceof DOMException && reason.name === "AbortError")) {
            setLifeStatus("unavailable");
          }
        }
      };
      void loadLife();
      showCity(map, false);
      setStatus("ready");
      window.clearTimeout(timeout);
    });

    return () => {
      disposed = true;
      lifeController.abort();
      window.clearTimeout(timeout);
      resize.disconnect();
      for (const item of markersRef.current) item.marker.remove();
      markersRef.current = [];
      for (const marker of projectMarkersRef.current) marker.remove();
      projectMarkersRef.current = [];
      mapRef.current = null;
      map.remove();
      lifeLayerRef.current = null;
    };
  }, [sourceMode]);

  useEffect(() => {
    if (lifeStatus === "ready") lifeLayerRef.current?.update(lifeOptionsRef.current);
  }, [selectedDistrict, projects, projectsVisible, focus, lifePlaying, lifeStatus]);

  useEffect(() => {
    const media = window.matchMedia("(prefers-reduced-motion: reduce)");
    const stopMotion = () => { if (media.matches) setLifePlaying(false); };
    media.addEventListener("change", stopMotion);
    return () => media.removeEventListener("change", stopMotion);
  }, []);

  useEffect(() => {
    selectionRef.current = selectedDistrict;
    for (const item of markersRef.current)
      item.element.classList.toggle("is-active", item.id === selectedDistrict);
    const map = mapRef.current;
    if (map?.getLayer("astana-selected-fill")) {
      map.setFilter("astana-selected-fill", [
        "==",
        ["get", "districtId"],
        selectedDistrict,
      ]);
      map.setFilter("astana-selected-outline", [
        "==",
        ["get", "districtId"],
        selectedDistrict,
      ]);
    }
  }, [selectedDistrict, status]);

  useEffect(() => {
    const map = mapRef.current;
    const district = DISTRICTS.find((item) => item.id === selectedDistrict);
    if (map && district && status === "ready") {
      if (focus === "detail") focusDistrict(map, district);
      else showCity(map, true);
    }
  }, [selectedDistrict, focus, cameraRevision, status]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || status !== "ready") return;
    const source = map.getSource("akim-projects") as
      | maplibregl.GeoJSONSource
      | undefined;
    source?.setData(projectGeoJSON(projectsVisible ? projects : []));
    for (const marker of projectMarkersRef.current) marker.remove();
    projectMarkersRef.current = [];
    for (const project of projectsVisible && focus === "detail"
      ? projects.filter((item) => item.districtId === selectedDistrict)
      : []) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "project-map-pin";
      button.style.setProperty("--project-color", project.color);
      button.textContent = project.shortLabel;
      button.title = `${project.label} · проект, условное размещение`;
      button.setAttribute("aria-label", `Проект: ${project.label}`);
      button.addEventListener("click", (event) => {
        event.stopPropagation();
        onProjectRef.current?.(project);
      });
      projectMarkersRef.current.push(
        new maplibregl.Marker({
          element: button,
          anchor: "bottom",
          offset: [0, -10],
        })
          .setLngLat(project.coordinates)
          .addTo(map),
      );
    }
    for (const marker of markersRef.current) {
      const count = projectsVisible
        ? projects.filter((project) => project.districtId === marker.id).length
        : 0;
      const district = DISTRICTS.find((item) => item.id === marker.id)!;
      marker.element.children[1].textContent =
        district.name + (count ? ` · ${count}` : "");
      marker.element.title = `${district.name}${count ? ` · проектов: ${count}` : ""}`;
    }
  }, [projects, projectsVisible, focus, selectedDistrict, status]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || status !== "ready" || !map.getLayer("astana-district-fill"))
      return;
    const color = (value: number | null | undefined) =>
      value == null
        ? "#bdc7c3"
        : value < 40
          ? "#cd715a"
          : value < 60
            ? "#d6b266"
            : "#459d7d";
    const expression: maplibregl.ExpressionSpecification = [
      "match",
      ["get", "districtId"],
      "esil",
      color(districtValues?.esil),
      "almaty",
      color(districtValues?.almaty),
      "saryarka",
      color(districtValues?.saryarka),
      "baikonur",
      color(districtValues?.baikonur),
      "nura",
      color(districtValues?.nura),
      "#bdc7c3",
    ];
    map.setPaintProperty(
      "astana-district-fill",
      "fill-color",
      districtValues ? expression : "#2e8c71",
    );
    map.setPaintProperty(
      "astana-district-fill",
      "fill-opacity",
      districtValues ? 0.33 : 0.035,
    );
  }, [districtValues, status]);

  return (
    <div
      className="astana-map-shell"
      role="region"
      aria-label="Реальная карта Астаны с пятью районами из задания"
    >
      <div ref={containerRef} className="astana-map" />
      <div className="astana-map-label">
        <span className="astana-map-live" />{" "}
        <strong>
          {focus === "overview"
            ? "АСТАНА · ПЯТЬ РАЙОНОВ"
            : DISTRICTS.find(
                (district) => district.id === selectedDistrict,
              )?.name.toUpperCase()}
        </strong>
        <small>
          {projectsVisible && projects.length
            ? "Проекты: условное размещение"
            : sourceMode === "online"
              ? "География OpenStreetMap"
              : "Локальная карта · здания: выборка"}
        </small>
      </div>
      {status === "ready" && focus === "detail" && (
        <div className="astana-life-panel" aria-label="Жизнь района">
          <span className={`astana-life-indicator ${lifePlaying && lifeStatus === "ready" ? "is-moving" : ""}`} aria-hidden="true" />
          <div className="astana-life-copy">
            <strong>{lifeStatus === "loading" ? "Добавляем жизнь на карту…" : lifeStatus === "unavailable" ? "Движение пока недоступно" : lifePlaying ? "Город в движении" : "Движение на паузе"}</strong>
            <small>{lifeStatus === "ready" && lifeSummary
              ? `${lifeSummary.vehicles - lifeSummary.buses} машин · ${lifeSummary.buses} ${pluralBus(lifeSummary.buses)} · ${lifeSummary.trees} деревьев`
              : "Карта и проекты доступны"}</small>
            {lifeStatus === "ready" && <small className="astana-life-street">{lifeSummary?.street} · условная анимация по улицам OSM</small>}
          </div>
          {lifeStatus === "ready" && (
            <div className="astana-life-actions">
              <button type="button" onClick={() => setLifePlaying((playing) => !playing)} aria-pressed={!lifePlaying}>
                {lifePlaying ? "Пауза" : "Пуск"}
              </button>
              <button type="button" onClick={() => lifeLayerRef.current?.streetView()}>К улице</button>
            </div>
          )}
        </div>
      )}
      {status === "ready" && (
        <div className="astana-map-controls">
          <button
            type="button"
            className="astana-source-toggle"
            onClick={() =>
              setSourceMode((current) =>
                current === "online" ? "local" : "online",
              )
            }
          >
            {sourceMode === "online" ? "Локальная подложка" : "Онлайн-подложка"}
          </button>
          {districtValues && (
            <span className="map-value-legend">
              <span style={{ color: "#b34b3e" }}>● &lt;40</span>　
              <span style={{ color: "#976614" }}>● 40–60</span>　
              <span style={{ color: "#21765c" }}>● ≥60</span>
              {Object.values(districtValues).some((value) => value == null) &&
                "　○ Нет расчёта"}
            </span>
          )}
        </div>
      )}
      {sourceMode === "local" && (
        <a
          className="astana-local-credit"
          href="https://www.openstreetmap.org/copyright"
          target="_blank"
          rel="noreferrer"
        >
          © OpenStreetMap contributors · ODbL
        </a>
      )}
      {status === "loading" && (
        <div className="astana-map-state" role="status">
          <strong>Загружаем карту Астаны</strong>
          <span>
            {sourceMode === "online"
              ? "Улицы и здания приходят из OpenFreeMap. При отсутствии сети откроется локальная карта."
              : "Открываем локальные районы, дороги, реку, парки и выборку зданий."}
          </span>
        </div>
      )}
      {status === "error" && (
        <div className="astana-map-state is-error" role="alert">
          <strong>Карта временно недоступна</strong>
          <span>
            Локальные геоданные не загрузились. Схема районов доступна без них.
          </span>
          <button type="button" onClick={onFallback}>
            Открыть схему
          </button>
        </div>
      )}
    </div>
  );
}
