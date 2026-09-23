import { useEffect, useRef, useState } from "react";
import type { DistrictId } from "./caseData";
import type { DistrictNetwork } from "./cityNetwork";
import type { ProjectPreview } from "./projectPreview";

type UnityInstance = {
  SendMessage: (objectName: string, methodName: string, value: string) => void;
  Quit: () => Promise<void>;
  SetFullscreen: (fullscreen: number) => void;
};

type UnityConfig = {
  dataUrl: string;
  frameworkUrl: string;
  codeUrl: string;
  streamingAssetsUrl: string;
  companyName: string;
  productName: string;
  productVersion: string;
  devicePixelRatio: number;
  matchWebGLToCanvasSize: boolean;
  showBanner: (message: string, type: "error" | "warning") => void;
};

declare global {
  interface Window {
    createUnityInstance?: (
      canvas: HTMLCanvasElement,
      config: UnityConfig,
      onProgress?: (progress: number) => void,
    ) => Promise<UnityInstance>;
  }
}

const UNITY_ROOT = `${import.meta.env.BASE_URL}unity`;
const BUILD_ROOT = `${UNITY_ROOT}/Build`;
const BUILD_VERSION = "projects-v1";
const ATLAS_URL = `${UNITY_ROOT}/geo/astana-atlas.json?v=${BUILD_VERSION}`;
const buildAssetUrl = (filename: string) =>
  `${BUILD_ROOT}/${filename}?v=${BUILD_VERSION}`;
const LOADER_URL = buildAssetUrl("unity.loader.js");
let loaderPromise: Promise<void> | null = null;
// Wait for the previous player to quit before reusing Unity's browser runtime.
let runtimeQueue: Promise<void> = Promise.resolve();

function loadUnityLoader() {
  if (window.createUnityInstance) return Promise.resolve();
  if (!loaderPromise) {
    loaderPromise = new Promise<void>((resolve, reject) => {
      const script = document.createElement("script");
      script.src = LOADER_URL;
      script.async = true;
      script.onload = () => resolve();
      script.onerror = () => {
        script.remove();
        loaderPromise = null;
        reject(new Error("Не удалось загрузить WebGL-сборку."));
      };
      document.head.appendChild(script);
    });
  }
  return loaderPromise;
}

function isDistrictId(value: unknown): value is DistrictId {
  return (
    typeof value === "string" &&
    ["esil", "almaty", "saryarka", "baikonur", "nura"].includes(value)
  );
}

async function loadGeoAtlas(signal: AbortSignal) {
  const response = await fetch(ATLAS_URL, { signal });
  if (!response.ok)
    throw new Error(
      `Не удалось загрузить геоданные Астаны (HTTP ${response.status}).`,
    );
  const json = await response.text();
  const atlas = JSON.parse(json) as {
    districts?: { id?: unknown; boundary?: { v?: unknown; t?: unknown } }[];
  };
  if (
    !Array.isArray(atlas.districts) ||
    atlas.districts.length !== 5 ||
    new Set(atlas.districts.map((district) => district.id)).size !== 5 ||
    atlas.districts.some(
      (district) =>
        !isDistrictId(district.id) ||
        !Array.isArray(district.boundary?.v) ||
        !Array.isArray(district.boundary?.t),
    )
  ) {
    throw new Error(
      "Геоатлас не содержит границы пяти районов. Попробуй обновить страницу.",
    );
  }
  return json;
}

export function UnityCityView({
  selectedDistrict,
  districtName,
  onSelectDistrict,
  sceneData,
  projects = [],
  projectsVisible = true,
  initialFocus = "overview",
  onFocusChange,
}: {
  selectedDistrict: DistrictId;
  districtName: string;
  onSelectDistrict: (districtId: DistrictId) => void;
  sceneData?: DistrictNetwork;
  projects?: ProjectPreview[];
  projectsVisible?: boolean;
  initialFocus?: "overview" | "detail";
  onFocusChange?: (focus: "overview" | "detail") => void;
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const instanceRef = useRef<UnityInstance | null>(null);
  const selectedDistrictRef = useRef(selectedDistrict);
  const onSelectDistrictRef = useRef(onSelectDistrict);
  const sceneDataRef = useRef(sceneData);
  selectedDistrictRef.current = selectedDistrict;
  onSelectDistrictRef.current = onSelectDistrict;
  sceneDataRef.current = sceneData;
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState<"loading" | "ready" | "error">(
    "loading",
  );
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);
  const [focus, setFocus] = useState<"overview" | "detail">(initialFocus);
  const [supportsProjects, setSupportsProjects] = useState(false);
  const projectsRef = useRef({ projects, visible: projectsVisible });
  projectsRef.current = { projects, visible: projectsVisible };
  const focusRef = useRef(focus);
  focusRef.current = focus;

  useEffect(() => {
    let mounted = true;
    let ownedInstance: UnityInstance | null = null;
    const controller = new AbortController();
    const canvas = canvasRef.current;
    if (!canvas) return;

    const onDistrictClick = (event: Event) => {
      const detail = (event as CustomEvent<{ districtId?: unknown }>).detail;
      if (isDistrictId(detail?.districtId))
        onSelectDistrictRef.current(detail.districtId);
      else if (mounted) {
        setError(
          "3D-сцена вернула неизвестный ID района. Продолжай через схему или список.",
        );
        setStatus("error");
      }
    };

    const fail = (reason: unknown) => {
      if (!mounted) return;
      setError(reason instanceof Error ? reason.message : String(reason));
      setStatus("error");
    };

    const boot = async () => {
      if (!mounted) return;
      const atlasTimeout = window.setTimeout(() => controller.abort(), 25_000);
      try {
        const [, atlasJson, manifest] = await Promise.all([
          loadUnityLoader(),
          loadGeoAtlas(controller.signal),
          fetch(`${UNITY_ROOT}/build-manifest.json`, {
            signal: controller.signal,
            cache: "no-store",
          }).then((response) =>
            response.ok ? response.json() : null,
          ) as Promise<{ version?: string; capabilities?: string[] } | null>,
        ]);
        window.clearTimeout(atlasTimeout);
        if (!mounted) return;
        if (!window.createUnityInstance)
          throw new Error("Unity loader не создал функцию запуска.");

        const nextInstance = await window.createUnityInstance(
          canvas,
          {
            dataUrl: `${BUILD_ROOT}/unity.data?v=${encodeURIComponent(manifest?.version ?? BUILD_VERSION)}`,
            frameworkUrl: `${BUILD_ROOT}/unity.framework.js?v=${encodeURIComponent(manifest?.version ?? BUILD_VERSION)}`,
            codeUrl: `${BUILD_ROOT}/unity.wasm?v=${encodeURIComponent(manifest?.version ?? BUILD_VERSION)}`,
            streamingAssetsUrl: `${UNITY_ROOT}/StreamingAssets`,
            companyName: "HackAlem",
            productName: "Аким — городская модель",
            productVersion: BUILD_VERSION,
            devicePixelRatio: Math.min(window.devicePixelRatio || 1, 1.5),
            matchWebGLToCanvasSize: true,
            showBanner: (message, type) => {
              if (type === "error") fail(new Error(message));
            },
          },
          (value) => {
            if (mounted) setProgress(value);
          },
        );
        ownedInstance = nextInstance;
        // Unity resolves its loader before MonoBehaviour.Start has necessarily run.
        // Let the player initialize its scene/camera before sending the first atlas.
        await new Promise<void>((resolve) =>
          requestAnimationFrame(() => requestAnimationFrame(() => resolve())),
        );
        if (!mounted) return;
        instanceRef.current = nextInstance;
        if (sceneDataRef.current?.districtId === selectedDistrictRef.current) {
          nextInstance.SendMessage(
            "DistrictMap",
            "SetDistrictData",
            JSON.stringify(sceneDataRef.current),
          );
        }
        nextInstance.SendMessage("DistrictMap", "SetGeoAtlas", atlasJson);
        nextInstance.SendMessage(
          "DistrictMap",
          "SetHighlightedDistrict",
          selectedDistrictRef.current,
        );
        nextInstance.SendMessage(
          "DistrictMap",
          "SetMapFocus",
          focusRef.current,
        );
        const hasProjects =
          manifest?.capabilities?.includes("project-previews") ?? false;
        setSupportsProjects(hasProjects);
        if (hasProjects)
          nextInstance.SendMessage(
            "DistrictMap",
            "SetProjectPreviews",
            JSON.stringify(projectsRef.current),
          );
        setProgress(1);
        setStatus("ready");
      } catch (reason) {
        fail(
          reason instanceof DOMException && reason.name === "AbortError"
            ? new Error(
                "Геоданные не загрузились за 25 секунд. Проверь соединение и повтори попытку.",
              )
            : reason,
        );
      } finally {
        window.clearTimeout(atlasTimeout);
      }
    };

    window.addEventListener("unity-district-click", onDistrictClick);
    const bootPromise = runtimeQueue.then(boot);
    runtimeQueue = bootPromise.catch(() => undefined);

    return () => {
      mounted = false;
      controller.abort();
      window.removeEventListener("unity-district-click", onDistrictClick);
      instanceRef.current = null;
      runtimeQueue = bootPromise
        .then(async () => {
          if (ownedInstance) await ownedInstance.Quit();
        })
        .catch(() => undefined);
    };
  }, [attempt]);

  useEffect(() => {
    if (status !== "ready") return;
    try {
      const instance = instanceRef.current;
      instance?.SendMessage(
        "DistrictMap",
        "SetHighlightedDistrict",
        selectedDistrict,
      );
      if (sceneData?.districtId === selectedDistrict)
        instance?.SendMessage(
          "DistrictMap",
          "SetDistrictData",
          JSON.stringify(sceneData),
        );
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason));
      setStatus("error");
    }
  }, [sceneData, selectedDistrict, status]);

  useEffect(() => {
    if (status !== "ready") return;
    instanceRef.current?.SendMessage("DistrictMap", "SetMapFocus", focus);
  }, [focus, status]);

  useEffect(() => {
    setFocus(initialFocus);
  }, [initialFocus]);
  useEffect(() => {
    if (status === "ready" && supportsProjects)
      instanceRef.current?.SendMessage(
        "DistrictMap",
        "SetProjectPreviews",
        JSON.stringify({ projects, visible: projectsVisible }),
      );
  }, [projects, projectsVisible, status, supportsProjects]);

  return (
    <div className={`unity-city-view ${status === "ready" ? "is-ready" : ""}`}>
      <div className="unity-stage">
        <canvas
          ref={canvasRef}
          id="unity-canvas"
          className="unity-city-canvas"
          width={960}
          height={600}
          aria-label={`3D-макет Астаны, ${focus === "overview" ? "обзор пяти районов" : `крупный план района ${districtName}`}. Район также можно выбрать в списке.`}
        />
        {status === "loading" && (
          <div className="unity-loading" role="status" aria-live="polite">
            <span className="unity-loading-mark" aria-hidden="true">
              3D
            </span>
            <strong>Загружаем 3D-макет Астаны</strong>
            <span>
              Границы районов, дороги, парки и здания. Первая загрузка — около
              10,8 МиБ.
            </span>
            <div className="unity-progress">
              <i style={{ width: `${Math.round(progress * 100)}%` }} />
            </div>
            <small>{Math.round(progress * 100)}%</small>
          </div>
        )}
        {status === "error" && (
          <div className="unity-error" role="alert">
            <strong>3D-сцена пока недоступна</strong>
            <span>
              {error || "Можно продолжить работу по схеме и списку районов."}
            </span>
            <button
              type="button"
              onClick={() => {
                setError("");
                setProgress(0);
                setStatus("loading");
                setAttempt((value) => value + 1);
              }}
            >
              Попробовать снова
            </button>
          </div>
        )}
        {status === "ready" && (
          <span className="unity-scene-badge">
            <i /> {districtName} ·{" "}
            {focus === "overview" ? "ОБЗОР" : "ЗДАНИЯ: ВЫБОРКА"}
          </span>
        )}
      </div>
      <div className="unity-map-toolbar">
        <div
          className="unity-focus-controls"
          role="group"
          aria-label="Масштаб 3D-макета"
        >
          <button
            type="button"
            disabled={status !== "ready"}
            aria-pressed={focus === "overview"}
            onClick={() => {
              setFocus("overview");
              onFocusChange?.("overview");
            }}
          >
            Обзор районов
          </button>
          <button
            type="button"
            disabled={status !== "ready"}
            aria-pressed={focus === "detail"}
            onClick={() => {
              setFocus("detail");
              onFocusChange?.("detail");
            }}
          >
            Приблизить район
          </button>
        </div>
        {!supportsProjects && projects.length > 0 && (
          <small className="unity-project-note">
            Проекты плана доступны в виде «Карта и проекты».
          </small>
        )}
        <a
          href="https://www.openstreetmap.org/copyright"
          target="_blank"
          rel="noreferrer"
        >
          © OpenStreetMap contributors · ODbL
        </a>
      </div>
    </div>
  );
}
