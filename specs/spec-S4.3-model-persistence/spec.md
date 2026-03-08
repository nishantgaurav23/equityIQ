# Spec S4.3 -- Model Persistence

## Overview
Save and load trained XGBoost SignalFusionModel instances using joblib. Models are stored in `data/models/` with version tracking via timestamps. This enables persistence across server restarts and supports model versioning for rollback.

## Dependencies
- S4.1 (SignalFusionModel class in `models/signal_fusion.py`)

## Target Location
`models/model_store.py`

---

## Functional Requirements

### FR-1: Save Model
- **What**: `save_model(model: SignalFusionModel, tag: str | None = None) -> Path` -- serializes a trained SignalFusionModel to disk using joblib.
- **Inputs**: A trained `SignalFusionModel` instance and an optional tag string (e.g., "v1", "production").
- **Outputs**: Returns the `Path` to the saved model file. File is named `signal_fusion_{timestamp}.joblib` (or `signal_fusion_{tag}_{timestamp}.joblib` if tag provided).
- **Side effects**: Creates `data/models/` directory if it doesn't exist. Writes model file to disk.
- **Edge cases**:
  - Model not trained (`is_trained=False`) -> raise `ValueError("Cannot save untrained model")`
  - Invalid tag (contains path separators or special chars) -> raise `ValueError`
  - Disk write failure -> propagate `OSError`

### FR-2: Load Model
- **What**: `load_model(path: str | Path | None = None) -> SignalFusionModel` -- deserializes a SignalFusionModel from disk.
- **Inputs**: Optional path to a specific model file. If `None`, loads the latest model from `data/models/`.
- **Outputs**: A `SignalFusionModel` instance with `is_trained=True` and all internal state restored.
- **Edge cases**:
  - Path doesn't exist -> raise `FileNotFoundError`
  - No models in `data/models/` when path is None -> raise `FileNotFoundError("No saved models found")`
  - Corrupted file -> propagate joblib/pickle error
  - Loaded object is not a SignalFusionModel -> raise `TypeError`

### FR-3: List Models
- **What**: `list_models() -> list[ModelInfo]` -- lists all saved models with metadata.
- **Inputs**: None.
- **Outputs**: List of `ModelInfo` dataclass instances sorted by timestamp (newest first). Each contains: `path`, `filename`, `tag`, `timestamp`, `size_bytes`.
- **Edge cases**: No models directory or no models -> return empty list.

### FR-4: Delete Model
- **What**: `delete_model(path: str | Path) -> bool` -- deletes a saved model file.
- **Inputs**: Path to model file.
- **Outputs**: `True` if deleted, `False` if file didn't exist.
- **Edge cases**: Path outside `data/models/` -> raise `ValueError("Can only delete models from data/models/")`

### FR-5: Get Latest Model Path
- **What**: `get_latest_model_path() -> Path | None` -- returns the path to the most recently saved model.
- **Inputs**: None.
- **Outputs**: `Path` to latest model file, or `None` if no models exist.

### FR-6: ModelInfo Dataclass
- **What**: Simple dataclass for model metadata.
- **Fields**: `path: Path`, `filename: str`, `tag: str | None`, `timestamp: datetime`, `size_bytes: int`.
- **Parsing**: Timestamp and tag extracted from filename pattern `signal_fusion_{tag}_{timestamp}.joblib` or `signal_fusion_{timestamp}.joblib`.

### FR-7: ModelStore Class
- **What**: Encapsulates all model persistence operations.
- **Constructor**: `__init__(base_dir: str | Path = "data/models")` -- configurable storage directory.
- **Methods**: `save()`, `load()`, `list()`, `delete()`, `get_latest_path()`.
- **Thread safety**: Not required for initial implementation (single-process Cloud Run).

---

## Tangible Outcomes

- [ ] **Outcome 1**: `from models.model_store import ModelStore` works
- [ ] **Outcome 2**: `save_model()` writes a `.joblib` file to `data/models/` with timestamp in filename
- [ ] **Outcome 3**: `load_model()` restores a fully functional trained model that can call `predict()`
- [ ] **Outcome 4**: `load_model()` without args loads the latest saved model
- [ ] **Outcome 5**: `list_models()` returns sorted ModelInfo list with correct metadata
- [ ] **Outcome 6**: Saving untrained model raises ValueError
- [ ] **Outcome 7**: Loading from empty directory raises FileNotFoundError
- [ ] **Outcome 8**: Round-trip save -> load -> predict produces same results as original model

---

## Test-Driven Requirements

### Tests to Write First (Red -> Green)
1. **test_model_store_import**: ModelStore can be imported from models.model_store
2. **test_save_trained_model**: Saving a trained model creates a .joblib file in the target directory
3. **test_save_untrained_model_raises**: Saving untrained model raises ValueError
4. **test_save_with_tag**: Saved filename includes the tag string
5. **test_save_invalid_tag_raises**: Tag with path separators raises ValueError
6. **test_load_specific_path**: Loading from a specific path restores the model
7. **test_load_latest**: Loading without path gets the most recent model
8. **test_load_nonexistent_raises**: Loading from nonexistent path raises FileNotFoundError
9. **test_load_empty_dir_raises**: Loading latest from empty dir raises FileNotFoundError
10. **test_load_wrong_type_raises**: Loading a non-SignalFusionModel joblib raises TypeError
11. **test_round_trip_predict**: Save -> load -> predict gives same results as original
12. **test_list_models_empty**: list_models on empty dir returns empty list
13. **test_list_models_sorted**: list_models returns models newest-first
14. **test_list_models_metadata**: ModelInfo has correct filename, tag, timestamp, size
15. **test_delete_model**: delete_model removes the file and returns True
16. **test_delete_nonexistent**: delete_model on nonexistent file returns False
17. **test_delete_outside_base_dir_raises**: Deleting outside base_dir raises ValueError
18. **test_get_latest_path**: Returns path to most recent model
19. **test_get_latest_path_empty**: Returns None when no models exist
20. **test_creates_directory**: save_model creates data/models/ if it doesn't exist

### Mocking Strategy
- No external services to mock -- this is pure filesystem + joblib
- Use `tmp_path` pytest fixture for isolated test directories
- Create real trained SignalFusionModel instances for save/load tests (small training data)

### Coverage Expectation
- All public methods have at least one test
- Edge cases: empty dirs, invalid inputs, round-trip integrity
- 20 tests covering all FRs

---

## References
- roadmap.md (S4.3 row), design.md
- models/signal_fusion.py (SignalFusionModel class)
- joblib documentation for serialization
