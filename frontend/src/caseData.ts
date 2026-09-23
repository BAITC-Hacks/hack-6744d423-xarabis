export const METRICS = ["T1", "T2", "E1", "E2", "S1", "S2", "B1", "B2", "C1", "C2"] as const;
export type MetricId = (typeof METRICS)[number];

export const CATEGORY_META = {
  transport: { name: "Транспорт", short: "ТР", color: "#257a78" },
  ecology: { name: "Экология", short: "ЭК", color: "#4e8e66" },
  social: { name: "Социальная сфера", short: "СО", color: "#b17b38" },
  safety: { name: "Безопасность", short: "БЕ", color: "#5677a2" },
  services: { name: "Сервисы", short: "СВ", color: "#8a68a3" },
} as const;

export type CategoryId = keyof typeof CATEGORY_META;
export type DistrictId = "esil" | "almaty" | "saryarka" | "baikonur" | "nura";

export type District = {
  id: DistrictId;
  name: string;
  score: number | null;
  values: Record<MetricId, number>;
  x: number;
  y: number;
  profile: string;
  accent: string;
  criticalMetrics: MetricId[];
};

export const DISTRICTS: District[] = [
  {
    id: "esil", name: "Есиль", score: 62.99, x: 377, y: 94, accent: "#a8c3b5",
    profile: "Высокий уровень сервиса, но перегруженные дороги и школы.", criticalMetrics: [],
    values: { T1: 45, T2: 62, E1: 68, E2: 72, S1: 48, S2: 55, B1: 78, B2: 60, C1: 75, C2: 70 },
  },
  {
    id: "almaty", name: "Алматы", score: 57.06, x: 169, y: 212, accent: "#c7bca9",
    profile: "Старые сети и нагрузка на дороги.", criticalMetrics: [],
    values: { T1: 40, T2: 75, E1: 50, E2: 55, S1: 60, S2: 65, B1: 62, B2: 52, C1: 50, C2: 60 },
  },
  {
    id: "saryarka", name: "Сарыарка", score: 54.65, x: 550, y: 208, accent: "#d2b99e",
    profile: "Частный сектор, смог и нехватка зелени.", criticalMetrics: [],
    values: { T1: 50, T2: 70, E1: 42, E2: 40, S1: 62, S2: 68, B1: 58, B2: 55, C1: 45, C2: 55 },
  },
  {
    id: "baikonur", name: "Байконур", score: 56.63, x: 278, y: 356, accent: "#b7bdac",
    profile: "Сбалансированный район без резких перекосов.", criticalMetrics: [],
    values: { T1: 52, T2: 68, E1: 55, E2: 50, S1: 58, S2: 60, B1: 52, B2: 58, C1: 55, C2: 58 },
  },
  {
    id: "nura", name: "Нура", score: 49.18, x: 492, y: 358, accent: "#bdc7b2",
    profile: "Самые слабые показатели транспорта и социальной инфраструктуры.", criticalMetrics: ["S1", "S2"],
    values: { T1: 55, T2: 40, E1: 45, E2: 65, S1: 38, S2: 35, B1: 55, B2: 50, C1: 60, C2: 50 },
  },
];

export const METRIC_META: Record<MetricId, { name: string; unit: string }> = {
  T1: { name: "Разгрузка дорог", unit: "Транспорт" },
  T2: { name: "Доступность транспорта", unit: "Транспорт" },
  E1: { name: "Озеленение", unit: "Экология" },
  E2: { name: "Качество воздуха", unit: "Экология" },
  S1: { name: "Школы и детсады", unit: "Социальная сфера" },
  S2: { name: "Поликлиники", unit: "Социальная сфера" },
  B1: { name: "Безопасность улиц", unit: "Безопасность" },
  B2: { name: "Безопасность движения", unit: "Безопасность" },
  C1: { name: "Надёжность ЖКХ", unit: "Сервисы" },
  C2: { name: "Ответы на обращения", unit: "Сервисы" },
};

export type Measure = {
  id: string;
  name: string;
  category: CategoryId;
  scope: "district" | "city";
  cost: number;
  lag: number;
  effects: Partial<Record<MetricId, number>>;
};

// Каталог — входные данные из задания, отображаемые интерфейсом.
export const MEASURES: Measure[] = [
  { id: "M1", name: "Выделенные полосы для автобусов", category: "transport", scope: "district", cost: 18, lag: 2, effects: { T1: 6, T2: 9 } },
  { id: "M2", name: "Умные светофоры", category: "transport", scope: "city", cost: 22, lag: 2, effects: { T1: 4, B2: 3 } },
  { id: "M3", name: "Расширение линии ЛРТ", category: "transport", scope: "district", cost: 30, lag: 4, effects: { T1: 16, T2: 20, E2: 4 } },
  { id: "M4", name: "Парк и сквер", category: "ecology", scope: "district", cost: 15, lag: 2, effects: { E1: 12, E2: 3, B1: 2 } },
  { id: "M5", name: "Чистое топливо в частном секторе", category: "ecology", scope: "district", cost: 25, lag: 3, effects: { E2: 14, C1: 4 } },
  { id: "M6", name: "Городское озеленение и ветрозащита", category: "ecology", scope: "city", cost: 20, lag: 4, effects: { E1: 5, E2: 3 } },
  { id: "M7", name: "Модульная школа и детсад", category: "social", scope: "district", cost: 24, lag: 3, effects: { S1: 16 } },
  { id: "M8", name: "Центр семейного здоровья", category: "social", scope: "district", cost: 20, lag: 3, effects: { S2: 14 } },
  { id: "M9", name: "Дворовые спортивные хабы", category: "social", scope: "district", cost: 10, lag: 1, effects: { S1: 3, S2: 3, B1: 3 } },
  { id: "M10", name: "Освещение и камеры", category: "safety", scope: "district", cost: 12, lag: 1, effects: { B1: 12, B2: 2 } },
  { id: "M11", name: "Безопасные переходы и школьные зоны", category: "safety", scope: "district", cost: 10, lag: 1, effects: { B2: 12, T1: -2 } },
  { id: "M12", name: "Цифровая платформа обращений", category: "services", scope: "city", cost: 14, lag: 1, effects: { C2: 5 } },
  { id: "M13", name: "Модернизация теплосетей и водосетей", category: "services", scope: "district", cost: 28, lag: 4, effects: { C1: 18, E2: 2 } },
  { id: "M14", name: "Аварийные бригады и раннее оповещение", category: "services", scope: "city", cost: 16, lag: 1, effects: { C1: 5, C2: 2 } },
];

export type Decision = { measureId: string; districtId?: DistrictId };

export const REFERENCE_DECISIONS: Decision[] = [
  { measureId: "M7", districtId: "nura" },
  { measureId: "M8", districtId: "nura" },
  { measureId: "M10", districtId: "nura" },
  { measureId: "M12" },
  { measureId: "M5", districtId: "saryarka" },
];

// Заранее заданный результат из контрольного примера в исходном DOCX.
// Это отображаемые demo-данные, не общий evaluator и не ответ сервера.
export const REFERENCE_RESULT = {
  scoreBefore: 52.55768,
  scoreAfter: 56.54307,
  scoreDelta: 3.98539,
  criticalBefore: 2,
  criticalAfter: 0,
  districts: [
    { districtId: "esil", scoreBefore: 62.99, scoreAfter: 63.4275, criticalMetrics: [], after: { T1: 45, T2: 62, E1: 68, E2: 72, S1: 48, S2: 55, B1: 78, B2: 60, C1: 75, C2: 74.375 } },
    { districtId: "almaty", scoreBefore: 57.06, scoreAfter: 57.4975, criticalMetrics: [], after: { T1: 40, T2: 75, E1: 50, E2: 55, S1: 60, S2: 65, B1: 62, B2: 52, C1: 50, C2: 64.375 } },
    { districtId: "saryarka", scoreBefore: 54.65, scoreAfter: 56.3, criticalMetrics: [], after: { T1: 50, T2: 70, E1: 42, E2: 48.75, S1: 62, S2: 68, B1: 58, B2: 55, C1: 47.5, C2: 59.375 } },
    { districtId: "baikonur", scoreBefore: 56.63, scoreAfter: 57.0675, criticalMetrics: [], after: { T1: 52, T2: 68, E1: 55, E2: 50, S1: 58, S2: 60, B1: 52, B2: 58, C1: 55, C2: 62.375 } },
    { districtId: "nura", scoreBefore: 49.18, scoreAfter: 52.9625, criticalMetrics: [], after: { T1: 55, T2: 40, E1: 45, E2: 65, S1: 48, S2: 43.75, B1: 67.5, B2: 51.75, C1: 60, C2: 54.375 } },
  ],
} as const;
