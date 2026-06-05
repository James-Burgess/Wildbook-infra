# ADR-0003: pyhesaff SIFT for Feature Extraction

**Status:** Accepted  
**Date:** 2026-06-04  
**Author:** OpenCode (AI Agent)

## Context

Feature extraction in WBIA uses `pyhesaff.detect_feats_in_image()`, a Hesaff-SIFT implementation. This is a critical dependency that we must preserve for algorithmic determinism.

## Decision

`wbia_core.features` wraps `pyhesaff.detect_feats_in_image()` with a clean, typed interface.

```python
def extract_features(image: np.ndarray, config: SiftConfig = SiftConfig()) -> FeatureSet:
    keypoints, descriptors = hesaff.detect_feats_in_image(image, **config.to_hesaff_kwargs())
    return FeatureSet(keypoints=keypoints, descriptors=descriptors)
```

Output shape:

- **keypoints**: `[N, 6]` — `(x, y, a, b, c, orient)`
- **descriptors**: `[N, 128]` — `uint8` L2-normalized SIFT descriptors

## Rationale

- **Determinism**: `pyhesaff` is the exact library used in production; replacing it would change feature values and break match reproducibility.
- **Simplicity**: The wrapper handles the legacy `**kwargs` interface and returns a typed `FeatureSet`.
- **Portability**: If we swap to `cv2.SIFT_create()` in the future, only this module changes.

## Consequences

### Positive
- Feature extraction is a single function call.
- `FeatureSet` is JSON-serializable for caching.
- Easy to mock in tests.

### Negative
- `pyhesaff` is a Cython extension; requires a compiler at pip-install time.
- No GPU acceleration (SIFT is CPU-only).
- The `[N, 6]` keypoint shape is unusual; we document it explicitly.

## Alternatives Considered

| Alternative | Rejected Because |
|---|---|
| `cv2.SIFT_create()` | Different feature values → different match results |
| `cv2.ORB_create()` | Binary descriptors, not compatible with LNBNN scoring |
| Learned features (SuperPoint, etc.) | Changes the algorithm entirely; out of scope for v1 |
| Precompute and store features | That's `wildlife-id`'s job; `wbia-core` is the algorithm, not the database |

## References

- pyhesaff source: `wildbook-ia/wbia/algo/hots/pyhesaff/` (git module)
- Integration point: `wildbook-ia/wbia/algo/hots/core_annots.py` (`get_hesaff_desc`)
- Design doc: `wildbook-docs/docs/ml-modernization/wbia-core.md#feature-extraction-and-representation`
