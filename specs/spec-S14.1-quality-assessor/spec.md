# Spec S14.1 -- Quality Assessor

## Overview
Quality scoring module for analysis verdicts. Evaluates data completeness (did all agents contribute?), signal consensus (do agents agree?), and confidence calibration (are confidence values well-distributed and justified?). Returns a quality grade from A to F, enabling users and the system to assess how trustworthy a given analysis is.

## Dependencies
- S10.1 (Full pipeline wiring -- ensures FinalVerdict and all agent reports are available)

## Target Location
- `evaluation/quality_assessor.py`

---

## Functional Requirements

### FR-1: Data Completeness Scoring
- **What**: Score how many of the expected agent signals are present in a FinalVerdict. Each missing agent reduces completeness.
- **Inputs**: `FinalVerdict` (specifically `analyst_signals` dict and `risk_summary`)
- **Outputs**: `float` completeness score in [0.0, 1.0]. 1.0 = all 6 agents reported, each missing agent deducts proportionally (~0.167 per missing agent)
- **Edge cases**: Empty analyst_signals -> 0.0. Extra/unknown agent keys ignored.

### FR-2: Signal Consensus Scoring
- **What**: Measure agreement among agent signals. If all agents agree (all BUY or all SELL), consensus is high. Mixed signals reduce consensus.
- **Inputs**: `analyst_signals` dict (agent_name -> signal string)
- **Outputs**: `float` consensus score in [0.0, 1.0]. 1.0 = unanimous, lower values for more disagreement.
- **Edge cases**: Single agent -> 1.0 (trivial consensus). No agents -> 0.0.

### FR-3: Confidence Calibration Scoring
- **What**: Assess whether the overall confidence is well-calibrated relative to individual agent confidences. Flags when overall confidence is much higher than the average agent confidence (overconfident) or much lower (underconfident).
- **Inputs**: `FinalVerdict` (overall_confidence + individual agent confidence values from analyst_signals)
- **Outputs**: `float` calibration score in [0.0, 1.0]. 1.0 = well-calibrated, lower for large deviation between overall and mean agent confidence.
- **Edge cases**: No agent confidences available -> 0.5 (neutral). All confidences identical -> 1.0.

### FR-4: Overall Quality Grade
- **What**: Combine completeness, consensus, and calibration into a single letter grade (A-F).
- **Inputs**: The three sub-scores from FR-1, FR-2, FR-3
- **Outputs**: `QualityAssessment` Pydantic model containing:
  - `completeness_score: float`
  - `consensus_score: float`
  - `calibration_score: float`
  - `overall_score: float` (weighted average of three sub-scores)
  - `grade: str` (A/B/C/D/F)
  - `issues: list[str]` (human-readable descriptions of quality problems)
- **Grading thresholds**: A >= 0.90, B >= 0.75, C >= 0.60, D >= 0.40, F < 0.40
- **Weighting**: completeness 0.40, consensus 0.30, calibration 0.30
- **Edge cases**: All scores 0.0 -> grade F with appropriate issues listed.

### FR-5: Issue Detection
- **What**: Identify specific quality problems and return human-readable descriptions.
- **Inputs**: Sub-scores and FinalVerdict data
- **Outputs**: List of issue strings appended to `QualityAssessment.issues`
- **Issue types**:
  - Missing agents (completeness < 1.0): "Missing agent signals: {names}"
  - Low consensus (consensus < 0.50): "Low signal consensus -- agents disagree significantly"
  - Overconfidence (overall_confidence > mean_agent_confidence + 0.20): "Overall confidence may be inflated"
  - Underconfidence (overall_confidence < mean_agent_confidence - 0.20): "Overall confidence may be deflated"
  - Few data points (< 3 agents): "Insufficient agent coverage for reliable analysis"

---

## Tangible Outcomes

- [ ] **Outcome 1**: `evaluation/quality_assessor.py` exists with `QualityAssessor` class and `QualityAssessment` Pydantic model
- [ ] **Outcome 2**: `assess(verdict: FinalVerdict) -> QualityAssessment` returns correct grade for various scenarios
- [ ] **Outcome 3**: Perfect verdict (all agents, unanimous, well-calibrated) scores grade A
- [ ] **Outcome 4**: Verdict missing 3+ agents scores grade D or F
- [ ] **Outcome 5**: Mixed BUY/SELL signals reduce consensus score below 0.50
- [ ] **Outcome 6**: Issues list correctly identifies all quality problems
- [ ] **Outcome 7**: All scores clamped to [0.0, 1.0], grade always one of A/B/C/D/F

---

## Test-Driven Requirements

### Tests to Write First (Red -> Green)
1. **test_completeness_all_agents**: All 6 agent signals present -> completeness 1.0
2. **test_completeness_missing_agents**: 3 agents missing -> completeness ~0.50
3. **test_completeness_no_agents**: Empty signals -> completeness 0.0
4. **test_consensus_unanimous_buy**: All agents signal BUY -> consensus 1.0
5. **test_consensus_unanimous_sell**: All agents signal SELL -> consensus 1.0
6. **test_consensus_mixed_signals**: 3 BUY + 3 SELL -> low consensus
7. **test_consensus_single_agent**: One agent -> consensus 1.0
8. **test_calibration_well_calibrated**: Overall close to mean agent confidence -> high score
9. **test_calibration_overconfident**: Overall much higher than mean -> low score
10. **test_calibration_no_agent_confidences**: No data -> 0.5 neutral
11. **test_grade_a**: High scores across all dimensions -> grade A
12. **test_grade_f**: Low scores -> grade F
13. **test_grade_boundaries**: Scores at exact thresholds map correctly
14. **test_issues_missing_agents**: Missing agents listed in issues
15. **test_issues_low_consensus**: Low consensus flagged
16. **test_issues_overconfidence**: Overconfidence flagged
17. **test_issues_underconfidence**: Underconfidence flagged
18. **test_assess_full_verdict**: End-to-end with realistic FinalVerdict

### Mocking Strategy
- No external services to mock -- QualityAssessor operates on in-memory FinalVerdict objects
- Create helper functions to build test FinalVerdict instances with controlled signals/confidences

### Coverage Expectation
- All public methods have at least one test; edge cases covered
- Grade boundary tests ensure no off-by-one errors

---

## References
- roadmap.md (Phase 14, S14.1)
- design.md (evaluation framework)
- config/data_contracts.py (FinalVerdict, AnalystReport schemas)
