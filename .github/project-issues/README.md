# OpenDiscourse Project Issues

This directory contains detailed specifications for planned features and enhancements for the OpenDiscourse.net project. These documents serve as the basis for creating GitHub issues and tracking development progress.

## Issue Files

### Short Term (Q4 2024)

1. **[01-legal-embeddings.md](01-legal-embeddings.md)** - Add Specialized Embedding Models for Legal Text
   - Priority: High
   - Effort: Medium (1-2 weeks)
   - Status: Open

2. **[02-topic-modeling.md](02-topic-modeling.md)** - Implement Topic Modeling (LDA, BERTopic)
   - Priority: High
   - Effort: Medium (1-2 weeks)
   - Status: Open

3. **[03-fact-checking.md](03-fact-checking.md)** - Add Fact-Checking Integration
   - Priority: Medium
   - Effort: Medium (1-2 weeks)
   - Status: Open

4. **[04-visualization-dashboards.md](04-visualization-dashboards.md)** - Create Visualization Dashboards
   - Priority: High
   - Effort: Large (> 2 weeks)
   - Status: Open

### Medium Term (Q1-Q2 2025)

5. **[05-bert-finetuning.md](05-bert-finetuning.md)** - Fine-tune BERT Models on Political Text
   - Priority: Medium
   - Effort: Large (> 2 weeks)
   - Status: Open

6. **[06-argument-mining.md](06-argument-mining.md)** - Add Argument Mining Capabilities
   - Priority: Medium
   - Effort: Large (> 2 weeks)
   - Status: Open

7. **[07-realtime-api.md](07-realtime-api.md)** - Implement Real-time Analysis API
   - Priority: High
   - Effort: Large (> 2 weeks)
   - Status: Open

8. **[08-alert-system.md](08-alert-system.md)** - Create Alert System for Position Changes
   - Priority: Medium
   - Effort: Medium (1-2 weeks)
   - Status: Open

### Long Term (Q3-Q4 2025)

9. **[09-multilingual.md](09-multilingual.md)** - Multi-lingual Support
   - Priority: Low
   - Effort: Large (> 2 weeks)
   - Status: Open

10. **[10-network-analysis.md](10-network-analysis.md)** - Advanced Network Analysis
    - Priority: Medium
    - Effort: Large (> 2 weeks)
    - Status: Open

11. **[11-predictive-modeling.md](11-predictive-modeling.md)** - Predictive Modeling for Bill Passage
    - Priority: Medium
    - Effort: Large (> 2 weeks)
    - Status: Open

12. **[12-external-factchecking.md](12-external-factchecking.md)** - Integration with External Fact-Checking Services
    - Priority: Low
    - Effort: Medium (1-2 weeks)
    - Status: Open

## Using These Specifications

### For Contributors

1. **Choose an Issue**: Review the list above and select an issue that matches your skills and interests
2. **Read the Full Spec**: Open the corresponding markdown file for detailed requirements
3. **Check Dependencies**: Ensure you have or can obtain the required tools and libraries
4. **Follow the Tasks**: Use the task list as a guide for implementation
5. **Meet Success Criteria**: Ensure your work meets all listed success criteria
6. **Update Status**: Mark tasks as complete and update the status in the issue

### For Project Managers

1. **Create GitHub Issues**: Convert these specs into GitHub issues using the template at `.github/ISSUE_TEMPLATE/opendiscourse_project_item.md`
2. **Track Progress**: Use GitHub Projects to track the status of each item
3. **Assign Labels**: Apply appropriate labels (OpenDiscourse, enhancement, priority level)
4. **Monitor Timeline**: Track progress against the roadmap timelines
5. **Update Roadmap**: Keep `OPENDISCOURSE_PROJECT.md` synchronized with actual progress

## Document Structure

Each issue specification includes:

- **Category**: Short Term / Medium Term / Long Term
- **Priority**: High / Medium / Low
- **Estimated Effort**: Small / Medium / Large
- **Description**: Overview of the feature
- **Tasks**: Detailed checklist of implementation steps
- **Dependencies**: Required libraries, services, or infrastructure
- **Success Criteria**: Measurable goals for completion
- **Related Documentation**: Links to relevant project docs
- **Additional Context**: Examples, challenges, and considerations

## Creating GitHub Issues

To convert these specs into GitHub issues:

```bash
# For each issue file, create a corresponding GitHub issue
# Example command (requires gh CLI):
gh issue create \
  --title "[OpenDiscourse] Add Specialized Embedding Models for Legal Text" \
  --label "OpenDiscourse,enhancement,high-priority" \
  --body-file .github/project-issues/01-legal-embeddings.md
```

Or use the GitHub web interface:
1. Go to repository → Issues → New Issue
2. Select "OpenDiscourse Project Item" template
3. Copy content from the relevant markdown file
4. Fill in the template fields
5. Add appropriate labels and assignees

## Updating Specifications

When updating these specifications:

1. Ensure changes are reflected in `OPENDISCOURSE_PROJECT.md`
2. Update any related documentation
3. Notify contributors working on related issues
4. Update GitHub issues if already created
5. Commit with descriptive message explaining changes

## Questions or Feedback

For questions about these specifications or the OpenDiscourse project:
- Open a discussion in the repository
- Contact the project owner: cbwinslow
- Review the main project documentation: [OPENDISCOURSE_PROJECT.md](../../OPENDISCOURSE_PROJECT.md)

---

*Last Updated: 2025-10-22*  
*Part of the OpenDiscourse.net project*
