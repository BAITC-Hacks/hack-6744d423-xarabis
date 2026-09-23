import { useEffect, useRef, useState } from "react";
import type { DistrictId } from "./caseData";
import type { DistrictNetwork } from "./cityNetwork";

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

const UNITY_ROOT = "/unity";
const BUILD_ROOT = `${UNITY_ROOT}/Build`;
const BUILD_VERSION = "2.0.0";
const buildAssetUrl = (filename: string) => `${BUILD_ROOT}/${filename}?v=${BUILD_VERSION}`;
const LOADER_URL = buildAssetUrl("unity.loader.js");
let loaderPromise: Promise<void> | null = null;

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
  return typeof value === "string" && ["esil", "almaty", "saryarka", "baikonur", "nura"].includes(value);
}

export function UnityCityView({ selectedDistrict, districtName, onSelectDistrict, sceneData }: {
  selectedDistrict: DistrictId;
  districtName: string;
  onSelectDistrict: (districtId: DistrictId) => void;
  sceneData?: DistrictNetwork;
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
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let mounted = true;
    const canvas = canvasRef.current;
    if (!canvas) return;

    const onDistrictClick = (event: Event) => {
      const detail = (event as CustomEvent<{ districtId?: unknown }>).detail;
      if (isDistrictId(detail?.districtId)) onSelectDistrictRef.current(detail.districtId);
      else if (mounted) {
        setError("3D-сцена вернула неизвестный ID района. Продолжай через схему или список.");
        setStatus("error");
      }
    };

    const fail = (reason: unknown) => {
      if (!mounted) return;
      setError(reason instanceof Error ? reason.message : String(reason));
      setStatus("error");
    };

    const boot = async () => {
      try {
        await loadUnityLoader();
        if (!mounted) return;
        if (!window.createUnityInstance) throw new Error("Unity loader не создал функцию запуска.");

        const nextInstance = await window.createUnityInstance(canvas, {
          dataUrl: buildAssetUrl("unity.data"),
          frameworkUrl: buildAssetUrl("unity.framework.js"),
          codeUrl: buildAssetUrl("unity.wasm"),
          streamingAssetsUrl: `${UNITY_ROOT}/StreamingAssets`,
          companyName: "HackAlem",
          productName: "Аким — городская модель",
          productVersion: BUILD_VERSION,
          devicePixelRatio: Math.min(window.devicePixelRatio || 1, 1.5),
          matchWebGLToCanvasSize: true,
          showBanner: (message, type) => {
            if (type === "error") fail(new Error(message));
          },
        }, (value) => { if (mounted) setProgress(value); });

        if (!mounted) {
          await nextInstance.Quit().catch(() => undefined);
          return;
        }
        instanceRef.current = nextInstance;
        nextInstance.SendMessage("DistrictMap", "SetHighlightedDistrict", selectedDistrictRef.current);
        if (sceneDataRef.current?.districtId === selectedDistrictRef.current) {
          nextInstance.SendMessage("DistrictMap", "SetDistrictData", JSON.stringify(sceneDataRef.current));
        }
        setProgress(1);
        setStatus("ready");
      } catch (reason) {
        fail(reason);
      }
    };

    window.addEventListener("unity-district-click", onDistrictClick);
    void boot();

    return () => {
      mounted = false;
      window.removeEventListener("unity-district-click", onDistrictClick);
      const current = instanceRef.current;
      instanceRef.current = null;
      if (current) void current.Quit().catch(() => undefined);
    };
  }, [attempt]);

  useEffect(() => {
    if (status !== "ready") return;
    try {
      const instance = instanceRef.current;
      instance?.SendMessage("DistrictMap", "SetHighlightedDistrict", selectedDistrict);
      if (sceneData?.districtId === selectedDistrict) instance?.SendMessage("DistrictMap", "SetDistrictData", JSON.stringify(sceneData));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason));
      setStatus("error");
    }
  }, [sceneData, selectedDistrict, status]);

  return (
    <div className={`unity-city-view ${status === "ready" ? "is-ready" : ""}`}>
      <canvas
        ref={canvasRef}
        id="unity-canvas"
        className="unity-city-canvas"
        width={960}
        height={600}
        aria-label="Интерактивная 3D-сцена районов Астаны"
      />
      {status === "loading" && (
        <div className="unity-loading" role="status" aria-live="polite">
          <span className="unity-loading-mark" aria-hidden="true">3D</span>
          <strong>Подготавливаем городскую сцену</strong>
          <span>Это отдельная WebGL-сборка; схема остаётся доступной во время загрузки.</span>
          <div className="unity-progress"><i style={{ width: `${Math.round(progress * 100)}%` }} /></div>
          <small>{Math.round(progress * 100)}%</small>
        </div>
      )}
      {status === "error" && (
        <div className="unity-error" role="alert">
          <strong>3D-сцена пока недоступна</strong>
          <span>{error || "Можно продолжить работу по схеме и списку районов."}</span>
          <button type="button" onClick={() => { setError(""); setProgress(0); setStatus("loading"); setAttempt((value) => value + 1); }}>Попробовать снова</button>
        </div>
      )}
      {status === "ready" && <span className="unity-scene-badge"><i /> UNITY WEB · {districtName}</span>}
    </div>
  );
}
