# React ↔ Unity: projects-v1

Импортирована сборка из `/private/tmp/hackalem-unity-spike/web/unity/Build/`, Unity 6000.6.2f1. Исходный Unity-проект основной задачей не менялся. Пересборка: `sh build-web.sh` в изолированном проекте. Версия и возможности — `public/unity/build-manifest.json`.

## Инициализация

`UnityCityView` загружает loader, атлас и manifest, запускает Unity, пропускает два animation frame для `MonoBehaviour.Start`, затем отправляет:

```js
instance.SendMessage("DistrictMap", "SetGeoAtlas", atlasJson);
instance.SendMessage("DistrictMap", "SetHighlightedDistrict", "nura");
instance.SendMessage("DistrictMap", "SetMapFocus", "detail"); // либо overview
instance.SendMessage("DistrictMap", "SetProjectPreviews", JSON.stringify({
  projects: [{ id: "M4:nura", measureId: "M4", districtId: "nura",
    kind: "park", label: "Парк и сквер" }],
  visible: true
}));
```

Ранний `SendMessage` до инициализации сцены мог оставлять пустой canvas; порядок запуска проверен в основном приложении. Предыдущий экземпляр завершается через `Quit()` до создания следующего.

`SetProjectPreviews` — полная замена, не добавление. Пустой массив удаляет всё, `visible:false` скрывает слой. Общегородская мера передаётся пятью элементами с уникальными IDs `M12:esil`, `M12:almaty` и т. д. Python получает одну меру M12. MapLibre использует ту же модель проектов, но условные позиции не обязаны совпадать с Unity.

Соответствие M1–M14 по порядку: `bus`, `signals`, `lrt`, `park`, `cleanAir`, `greenery`, `school`, `clinic`, `sport`, `lighting`, `crossing`, `digital`, `utilities`, `emergency`.

## События и ограничения

- `unity-district-click`: `event.detail.districtId`. React проверяет известный ID, выбирает район и приближает камеру.
- `unity-project-previews-applied`: `{count, visible}` — подтверждение для внешнего QA; основной UI пока не использует его как состояние.
- `SetDistrictData(json)` сохранён для старого сетевого контракта. Расчётов на C# нет.
- Итоговые показатели Unity не пересчитывает. Цветовые слои результата показываются географическим видом.
- Все проекты иллюстративны. OSM-здания — выборка, Сарайшык отсутствует. Лицензии: OSM ODbL и Noto Sans SIL OFL.

## Обновление

Копируйте вместе `unity.data.gz`, `unity.framework.js.gz`, `unity.wasm.gz`, `unity.loader.js`, `unity.loader.js.gz` и manifest. Обновите версию loader в `UnityCityView.tsx`, чтобы исключить старый кеш. Атлас хранится отдельно в `public/unity/geo/`.

После `npm run build` проверьте production: MIME WASM `application/wasm`, JS `application/javascript`, data `application/octet-stream`, атлас `application/json`; compressed-ответы с `Content-Encoding: gzip`. Нельзя смешивать разные сборки или отдавать HTML по адресам Unity-ресурсов.
