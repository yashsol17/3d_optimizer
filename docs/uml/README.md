# UML Diagrams

Vector diagrams (SVG) for the project report. Word, PowerPoint and Google Slides
all import SVG directly and keep it sharp at any zoom or print size.

| File | Diagram | Shows |
|---|---|---|
| `01-use-case.svg` | Use case | Who uses the system and what they can do — the artist in the browser, a game engine through the REST API, and Blender as the external system that performs the decimation |
| `02-component.svg` | Component | How the parts fit together — clients, FastAPI backend, shared pipeline, feature extraction, Blender and the storage folders |
| `03-sequence.svg` | Sequence | One optimization request end to end, from upload through Blender to the measured result, plus the failure paths and their HTTP codes |
| `04-class.svg` | Class | The modules and their operations — Pipeline, FeatureExtractor, API router, web app, schemas, config and the exception hierarchy |

All four reflect the code as it stands: the routes in `backend/api.py`, the
orchestration in `backend/core/pipeline.py` and the clients under `clients/`.
Update them when those change.
