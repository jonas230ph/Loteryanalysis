# Call Center Workforce Sample Data

These files provide deterministic sample data for the **Channel Performance** and **SLA Recovery Actions** SharePoint imports. The performance file contains one Voice and one Chat row for every day from 2026-05-01 through 2026-07-31 (184 rows). It contains individual SLA, ACR, and both-metric breaches. Voice uses an 80% SLA target and 5% ACR target; Chat uses an 85% SLA target and 4% ACR target.

## Implementation handoff

Use these deliverables together. They are build and test instructions; none of
them creates, deploys, enables, or publishes Microsoft 365 resources.

- [Implementation plan](2026-08-13-call-center-workforce-implementation-plan.md) — delivery sequence and acceptance scope.
- [Solution design](2026-08-13-call-center-workforce-design.md) — architecture and operating assumptions.
- [SharePoint / Microsoft Lists setup](sharepoint-lists-setup.md) — schemas, imports, views, and list permissions.
- [Power BI build guide](power-bi-build-guide.md) — model, measures, report layout, and refresh configuration.
- [Embedded Power App build guide](power-app-build-guide.md) — selected-breach recovery-action workflow and form validation.
- [Power Automate build guide](power-automate-build-guide.md) — manager notification and scheduled breach-detection flows.
- [Power BI QA checklist](power-bi-qa-checklist.md) — report-level validation.
- [End-to-end acceptance results](end-to-end-test-results.md) — editable tenant-test record plus local/static source-data evidence.
- [Channel Performance sample CSV](channel_performance_sample.csv) — fictional performance inputs.
- [SLA Recovery Actions sample CSV](sla_recovery_actions_sample.csv) — fictional recovery-action inputs.

### Required permissions

| Role | Minimum access |
| --- | --- |
| Power BI report author / refresh owner | Read access to both SharePoint lists and permission to configure the report's SharePoint connection and scheduled refresh. |
| Power App maker and supervisors using the embedded form | Permission to create items in `SLA Recovery Actions`; supervisors require **Contribute** on both lists for the documented workflow. |
| Managers | **Read** on both lists and permission to receive the approved Teams or Outlook notification. |
| Power Automate flow connection owner | **Edit** on both lists and permission to use the selected Teams or Outlook connector. |

Record the named groups/accounts and validation date in the end-to-end results
file before release. Apply least privilege and use a monitored test recipient
for acceptance testing.

### Refresh and flow ownership

The designated Power BI owner maintains SharePoint credentials, dataset
refresh schedule, refresh-failure monitoring, and report access. The designated
Power Automate owner maintains both flows: `Notify manager of SLA recovery
action` and `Detect daily SLA and ACR breaches`, including connections,
recurrence timing after source loads, run-history monitoring, and recipient
configuration. The Power App owner maintains the SharePoint connection,
required-field validation, and the Power BI visual data-field contract. Record
the actual owners, backups, and escalation route in the deployment record.

### Fictional data and teardown

Both sample CSVs use fictional people and manager addresses; replace them with
approved test identities before any tenant test, and never treat the sample
addresses as production contacts.

After validation, the removable test resources are the `Channel Performance`
and `SLA Recovery Actions` test lists plus the `Notify manager of SLA recovery
action` and `Detect daily SLA and ACR breaches` test flows. Preserve any
evidence required by policy first, disable the flows to prevent new messages,
then remove the test flows and lists only from the intended test site.

## Import mapping

### Channel Performance

| CSV header | SharePoint column type |
| --- | --- |
| PerformanceDate | Date |
| MonthStart | Date |
| Channel | Choice |
| OfferedContacts | Number |
| AnsweredWithinTarget | Number |
| AbandonedContacts | Number |
| SLA_TargetPct | Number |
| ACR_TargetPct | Number |
| Supervisor | Single line of text |
| ManagerEmail | Single line of text |

### SLA Recovery Actions

| CSV header | SharePoint column type |
| --- | --- |
| ActionID | Single line of text |
| PerformanceDate | Date |
| Channel | Choice |
| SLA_Pct | Number |
| ACR_Pct | Number |
| BreachType | Choice |
| RootCause | Multiple lines of text |
| RecoveryAction | Multiple lines of text |
| Owner | Single line of text |
| DueDate | Date |
| Status | Choice |
| ManagerEmail | Single line of text |
| AlertSent | Yes/No |
| AlertSentAt | Date and Time |

`ActionID` is a **Single line of text** field; it is not SharePoint's generated **ID** field.

## Calculation checks

- Voice breach, 2026-05-14: SLA = 75 / 100 = **75.00%**, below the 80% SLA target; ACR = 8 / 100 = **8.00%**, above the 5% ACR target. This is a Both breach.
- Chat breach, 2026-05-09: SLA = 92 / 100 = **92.00%**, meeting the 85% SLA target; ACR = 8 / 100 = **8.00%**, above the 4% ACR target. This is an ACR breach.

Formulae: `SLA % = AnsweredWithinTarget / OfferedContacts`; `ACR % = AbandonedContacts / OfferedContacts`.
