# [OpenDiscourse] Predictive Modeling for Bill Passage

**Project Item Category**: Long Term

**Priority**: Medium

**Estimated Effort**: Large (> 2 weeks)

## Description

Build machine learning models to predict likelihood of bill passage based on historical data. This will help stakeholders understand which factors influence legislative success and forecast outcomes.

## Tasks

- [ ] Collect historical bill outcome data (10+ years)
- [ ] Engineer relevant features:
  - [ ] Bill characteristics (length, complexity, topic)
  - [ ] Sponsor characteristics (seniority, party, committee roles)
  - [ ] Co-sponsorship patterns (number, bipartisan support)
  - [ ] Timing features (session stage, election cycle)
  - [ ] Political context (party control, presidential alignment)
  - [ ] Text features (sentiment, readability, controversy)
- [ ] Split data into train/validation/test sets
- [ ] Train baseline models (logistic regression, decision trees)
- [ ] Train advanced models (Random Forest, XGBoost, Neural Networks)
- [ ] Implement feature importance analysis
- [ ] Evaluate model performance (accuracy, precision, recall, AUC)
- [ ] Create calibration and confidence intervals
- [ ] Build prediction API endpoint
- [ ] Add explainability (SHAP values, LIME)
- [ ] Create visualization of predictions and factors
- [ ] Write comprehensive model documentation

## Dependencies

- `scikit-learn` - ML algorithms
- `xgboost` or `lightgbm` - Gradient boosting
- `tensorflow` or `pytorch` - Neural networks (optional)
- `shap` - Model explainability
- `mlflow` - Experiment tracking
- Historical bill data (Congress.gov, GovTrack)
- Feature engineering pipeline

## Success Criteria

- Model achieves > 75% accuracy on test set
- Predictions are well-calibrated
- Feature importance makes intuitive sense
- Model generalizes across different congresses
- Explainability helps users understand predictions
- API returns predictions with confidence scores
- Documentation explains methodology and limitations
- Ethical considerations are addressed

## Related Documentation

- [OPENDISCOURSE_PROJECT.md](../../OPENDISCOURSE_PROJECT.md#11-predictive-modeling-for-bill-passage)
- [models/bill.py](../../models/bill.py)
- [analysis/](../../analysis/)

## Additional Context

Target variable:
- **Binary**: Bill passed (Yes/No)
- **Multi-class**: Introduced → Committee → Floor → Passed → Signed

Potential features:

**Bill Features**:
- Number of pages
- Readability score
- Topic category
- Amendment count
- Previous version history

**Sponsor Features**:
- Seniority (years in office)
- Committee leadership roles
- Party affiliation
- Historical success rate
- Fundraising strength

**Co-sponsorship Features**:
- Total number of co-sponsors
- Bipartisan ratio
- Average seniority of co-sponsors
- Speed of co-sponsor acquisition

**Timing Features**:
- Days until session end
- Distance to election
- Legislative calendar position

**Political Context**:
- Party control (House, Senate, Presidency)
- Partisan polarization index
- Public opinion polling
- Related news coverage

Model evaluation:
```
Accuracy: 78%
Precision: 0.72
Recall: 0.65
AUC-ROC: 0.83
```

Example prediction:
```
Bill: H.R. 1234 - Healthcare Reform Act
Predicted Probability of Passage: 62%

Top Contributing Factors:
1. Bipartisan co-sponsorship (+15%)
2. Sponsor is committee chair (+12%)
3. Similar bills passed recently (+8%)
4. Early in session (+5%)
5. Low text complexity (+3%)
```

Ethical considerations:
- Don't influence legislative process unfairly
- Acknowledge model limitations
- Avoid creating self-fulfilling prophecies
- Consider unintended consequences
- Be transparent about accuracy
