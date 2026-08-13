# End-to-end acceptance results

**Status:** Tenant execution pending. This document separates repeatable local
sample-data checks from Microsoft 365 tenant validation. Do not change a
tenant-test row to Pass without recording the run evidence below.

## Test environment and evidence

| Field | Value |
| --- | --- |
| Test operator | `<name>` |
| Test date/time (UTC) | `<yyyy-mm-ddThh:mm:ssZ>` |
| SharePoint site / test tenant | `<URL or identifier>` |
| Power BI report URL / version | `<URL or version>` |
| Power App URL / version | `<URL or version>` |
| Test manager mailbox or Teams recipient | `<test address>` |
| Flow run URLs | `<Flow 1 URL>`; `<Flow 2 URL>` |
| Screenshots / exported evidence location | `<location>` |

## Local/static evidence — completed from supplied sample data

Source: [`channel_performance_sample.csv`](channel_performance_sample.csv),
filtered to `MonthStart = 2026-05-01`. Results were calculated as summed
numerators divided by summed `OfferedContacts`; targets are the row-level
target average for the selected channel context. A breach event is one SLA or
ACR breach per performance row, so a both-metric row contributes two events.
These checks validate the deterministic source data and expected measures;
they do **not** prove a Power BI report, Power App, SharePoint list, or flow
has been deployed.

| Scenario | Offered | Weighted SLA / target | Weighted ACR / target | SLA / ACR / total breach events | Evidence status |
| --- | ---: | --- | --- | ---: | --- |
| Voice, May 2026 | 3,375 | 85.78% / 80.00% | 3.41% / 5.00% | 2 / 1 / 3 | Verified locally |
| Chat, May 2026 | 2,844 | 90.08% / 85.00% | 2.99% / 4.00% | 1 / 2 / 3 | Verified locally |
| All channels, May 2026 | 6,219 | 87.75% / 82.50% | 3.22% / 4.50% | 3 / 3 / 6 | Verified locally |

## Tenant acceptance record — pending execution

Enter `Pass`, `Fail`, or `Blocked` in **Actual result/status**, then add
specific links, IDs, screenshots, and notes. `Pending` is intentional until
the test is performed in a test tenant.

| ID | Scenario / action | Expected result | Actual result/status | Evidence / notes |
| --- | --- | --- | --- | --- |
| R-01 | In Power BI select May 2026 and `Voice`. | SLA, ACR, targets, and breach cards match the Voice static row above; visual cross-filtering/highlighting remains coherent. | Pending | `<report URL; screenshot>` |
| R-02 | Select May 2026 and `Chat`. | SLA, ACR, targets, and breach cards match the Chat static row above; visual interactions remain coherent. | Pending | `<report URL; screenshot>` |
| R-03 | Select May 2026 with all channels. | Weighted measures and breach cards match the all-channel static row; values are not averages of daily percentages. | Pending | `<report URL; screenshot>` |
| R-04 | Select one visible breached date/channel row, open the embedded Power App, and submit a valid recovery action. | The app creates one action with the selected `PerformanceDate`, `Channel`, manager, SLA, and ACR context. | Pending | `<action item URL/ID; screenshot>` |
| R-05 | Inspect the created SharePoint action under the same report filters. | The action appears in `SLA Recovery Actions` and its date/channel context matches the selected breach. | Pending | `<item URL/ID>` |
| R-06 | For one date/channel key with at least two actions, inspect the exception table and the source actions' `Created` and numeric SharePoint `ID`. | `[Related Action Status]` and `[Related Action AlertSent]` both come from the row with greatest `Created`, then greatest `ID` on a tie; neither value comes from another action or same-date channel. | Pending | `<report screenshot; source item IDs/Created values>` |
| N-01 | Create a manual recovery action with `AlertSent = No`. | Flow 1 sends exactly one notification containing date, channel, breach type, SLA, ACR, root cause, recovery action, owner, due date, and status. | Pending | `<message screenshot; Flow 1 run URL>` |
| N-02 | Reopen that action after a successful notification. | `AlertSent = Yes` and `AlertSentAt` is populated; the timestamp follows the notification send. | Pending | `<item URL/ID; timestamp>` |
| X-01 | Submit the Power App form with each required editable field blank, one field per attempt. | Submission is blocked and a visible validation message identifies the missing field; no action is created. | Pending | `<fields tested; screenshots>` |
| X-02 | Run Flow 2 against a performance row with `OfferedContacts = 0`. | The row is skipped before division; no action or notification is created. | Pending | `<Flow 2 run URL; item search>` |
| X-03 | With Recurrence concurrency set to `1`, run the documented one-minute recurrence/two-minute Delay overlap test for one scheduled breach. | A second trigger occurs while the first run is active but does not execute the keyed path concurrently. Across both runs exactly one action, one ActionID, and one alert are created. | Pending | `<both run URLs and timestamps; action ID; notification evidence>` |
| X-04 | Submit/create an action with an invalid manager email in the isolated test path. | Notification fails visibly; `AlertSent` remains `No` and `AlertSentAt` remains blank. Repair the address and retest with a new action. | Pending | `<run URL; item URL/ID; failure detail>` |
| X-05 | In the published report, select breach A, then change to breach B without reloading, reopening, or reselecting the visible Power App; submit one valid action. | Read-only context changes to B before submission, and the created action's date, channel, SLA, ACR, breach type, and manager all match B with no values retained from A. | Pending | `<A/B screenshots; item URL/ID and fields>` |
| X-06 | Through an isolated test path, supply a known within-target date/channel row to the Power Apps visual and submit otherwise valid action details. | The app displays the within-target block, creates no SharePoint action, and sends no manager alert. | Pending | `<KPI/target screenshot; item-list search; notification evidence>` |
| X-07 | Supply zero rows and then multiple rows to `PowerBIIntegration.Data`; attempt Submit through the isolated test path for each case. | For both row counts the form is hidden, exact-one-selection guidance appears, and no SharePoint action or manager alert is produced. | Pending | `<row-count/screenshots; item-list searches; notification evidence>` |

## Acceptance decision

| Decision | Owner | Date | Rationale / remaining blockers |
| --- | --- | --- | --- |
| Pending | `<name>` | `<yyyy-mm-dd>` | Complete all tenant acceptance rows before approving production use. |
