# ar-hud — AR-HUD Simulator

Симуляция AR-HUD: видео с камеры (или файла) + наложение модулей (часы, мониторинг системы, погода, детекция лиц).

## Запуск

```bash
pip install -r requirements.txt
python main.py                            # с config/default.yaml
python main.py --config path/to/cfg.yaml  # со своим конфигом
```

Конфиг переключает источник видео и состав модулей без правок кода:

```yaml
camera:
  type: webcam | file          # переключатель источника
  source: 0 | 'path/to/video.mp4'

modules:
  - type: clock | system_monitor | weather | face_detection
    name: <уникальное имя>
    enabled: true | false
    params: { ... }
```

## Архитектура

```
src/core/        Frame, ICameraSource, IHUDModule, Clock, Pipeline, реестр модулей
src/camera/      CameraStream, VideoFileSource, factory (webcam ↔ file одной строкой YAML)
src/rendering/   HUDOverlay, draw_utils, IDisplaySink + OpenCVDisplaySink
src/modules/     clock, system_monitor, weather, face_detection (добавляются без правок ядра)
config/          default.yaml + Pydantic-схема
tests/           36 тестов: unit, integration, graceful degradation
```

Ключевые решения:
- **update() vs render()** разделены в `IHUDModule` — частоты логики и дисплея можно развести.
- **dt** считается только в `Clock` — ни одного `time.time()` больше нигде в проекте.
- **FaceDetection** работает в отдельном `multiprocessing`-процессе; основной FPS не падает при медленной детекции (graceful degradation).
- **`IDisplaySink`** абстрагирует вывод — замена `cv2.imshow` на фреймбуфер AR-устройства не трогает ядро.

## Добавление нового модуля

1. Создайте `src/modules/my_module.py` с классом, наследующим `AbstractHUDModule`.
2. Зарегистрируйте его: `@register_module("my_type")` на классе.
3. Добавьте в `config/default.yaml`:
   ```yaml
   modules:
     - type: my_type
       name: my_instance
       enabled: true
       params: { ... }
   ```

`main.py` и `src/core/pipeline.py` не меняются.

## Тесты

```bash
pytest                    # все 36 тестов
pytest tests/test_clock.py -v
```

## Acceptance

| Phase | Acceptance | Проверено |
|---|---|---|
| 0 | 50 кадров с видеофайла без падений | `test_video_file_source_smoke_50_frames` |
| 1 | Clock: первый tick=0, max_dt clamp | `test_first_tick_returns_zero`, `test_max_dt_clamp` |
| 2 | Factory: webcam/file swap строкой конфига | `test_factory_webcam`, `test_factory_file` |
| 3 | Новый модуль подключается без правок pipeline/main | `test_new_module_builds_without_touching_pipeline` |
| 4 | FPS видео не падает > 30% при медленном воркере | `test_graceful_degradation_fps_drop_under_threshold` |
| 4 | Простые модули < 5 мс/кадр | `test_simple_modules_under_5ms_per_frame` |
| 5 | Конфиг → pipeline → shutdown без висящих потоков/процессов | `test_pipeline_from_config_runs_and_exits_cleanly` |

## План развития

Из плана не сделано (по запросу): реальный вывод на AR-устройство, полноценная обработка отказа сети в Weather, DNN-вариант FaceDetection. Архитектура их не блокирует.