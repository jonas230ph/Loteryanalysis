# Power BI report QA checklist

Use this checklist after building the report in Power BI Desktop and again
after an authorized report owner publishes it to a test workspace. Record the
tester, test date, workspace, dataset/report name, and result for every item.
This document is a validation procedure; it does not publish a report.

## Test setup

- [ ] Confirm the model contains `Channel Performance`, `SLA Recovery Actions`,
  and `Calendar`. Confirm `Calendar -> Channel Performance` is active and
  single-direction; do not assume `Calendar -> SLA Recovery Actions` is active.
- [ ] Confirm these measures exist and retain their exact names: `[SLA %]`,
  `[ACR %]`, `[SLA Target %]`, `[ACR Target %]`, `[Total Breach Days]`,
  `[Related Action Status]`, `[Related Action AlertSent]`, and `[Exception
  Row]`.
- [ ] In `SLA Recovery Actions`, confirm SharePoint `Created` is retained as
  Date/Time/Timezone (or Date/Time if that is what the connector exposes) and
  generated `ID` is retained as Whole Number. Confirm `ActionID` remains a
  separate Text field and is not used to order actions.
- [ ] Confirm the tester can read the source SharePoint site using the intended
  organizational account. Do not use a personal or unintended cached account.
- [ ] Identify one known SLA-breach row and one known ACR-breach row for visual
  and Power Apps testing. The supplied sample's **2026-05-05 / Voice** row is
  an SLA breach: 75.8% SLA versus an 80.0% target.

## Desktop visual QA

- [ ] On **Operations Overview**, confirm slicers exist for
  `Calendar[Month Label]`, `Channel Performance[Channel]`, and
  `Channel Performance[Supervisor]`.
- [ ] Clear all slicers and record the five KPI card values for `[SLA %]`,
  `[SLA Target %]`, `[ACR %]`, `[ACR Target %]`, and `[Total Breach Days]`.
- [ ] Select one month, then verify every KPI, both clustered-column charts,
  the line chart, exception table, and Power Apps visual update to the same
  context.
- [ ] Add a Channel selection and repeat the check. Clear it, select a
  Supervisor, and repeat. Check **Format > Edit interactions** if any visual
  does not filter as intended.
- [ ] In the SLA comparison chart, verify Channel is the X-axis and `[SLA %]`
  and `[SLA Target %]` are the values. In the ACR comparison chart, verify the
  corresponding ACR measures are used.
- [ ] In the trend chart, verify `Calendar[Date]` is the X-axis and `[SLA %]`
  and `[ACR %]` are the values.
- [ ] Verify the visual language identifies green as within target and
  red/orange as breach variance. Confirm SLA below target and ACR above target
  are treated as breaches.

## Exception-table QA

- [ ] In both queries, confirm `PerformanceChannelKey` uses the same normalized
  `yyyy-MM-dd|CHANNEL` format. Confirm every `Channel Performance` key is
  unique.
- [ ] Confirm the history-preserving multi-action route is in use: no active
  `Channel Performance`-to-`SLA Recovery Actions` relationship, the direct
  `Calendar`-to-actions relationship is inactive on Operations Overview, and
  the table uses `[Related Action Status]` and `[Related Action AlertSent]`
  rather than raw action columns.
- [ ] Confirm the table exposes `PerformanceDate`, `Channel`, `[SLA %]`, `[SLA
  Target %]`, `[ACR %]`, `[ACR Target %]`, `Supervisor`, `ManagerEmail`, and
  related action `Status` and `AlertSent`.
- [ ] Confirm `[Exception Row]` exists and is applied under **Filters on this
  visual** as **is 1**. Verify a within-target row and an `OfferedContacts = 0`
  row are absent from the exception table, while known SLA and ACR breaches
  remain visible.
- [ ] Select two different channels on the same `PerformanceDate` where at
  least one has an action. For each exception, confirm `Status` and `AlertSent`
  come only from the matching `PerformanceChannelKey`; an action from the
  other same-date channel must never appear.
- [ ] Create or identify two action records sharing one normalized key but with
  different `Status` and `AlertSent` values. Confirm both displayed measures
  come from the row with greatest `Created`; if `Created` ties, greatest numeric
  SharePoint `ID` wins. Capture both source IDs/timestamps and the displayed
  pair to prove the measures did not mix records.
- [ ] Filter to the known SLA-breach row and verify `[SLA %]` is formatted red
  when below `[SLA Target %]`.
- [ ] Filter to the known ACR-breach row and verify `[ACR %]` is formatted red
  when above `[ACR Target %]`.
- [ ] Confirm a non-breach row cannot be selected from the exception table.

## Power Apps visual QA

- [ ] Open the Power Apps visual data pane and verify the fields appear in this
  exact order: `PerformanceDate`, `Channel`, `Supervisor`, `ManagerEmail`,
  `[SLA %]`, `[ACR %]`, `[SLA Target %]`, `[ACR Target %]`.
- [ ] Select exactly one exception row (or filter to one date/channel record)
  and open the embedded app. Confirm the selected record is present in
  `PowerBIIntegration.Data` and `CountRows(PowerBIIntegration.Data) = 1`.
- [ ] Confirm the app reads measure fields using Power Fx quoted names, for
  example `First(PowerBIIntegration.Data).'SLA %'` and the corresponding ACR
  and target fields. Confirm read-only controls and visibility do not read a
  variable captured in `OnVisible`.
- [ ] Change the month, channel, and supervisor slicers one at a time and
  verify the app receives only records matching the report's current filter
  context.
- [ ] Select breach A, then change to a different breach B without reloading,
  reopening, or reselecting the Power Apps visual. Confirm all displayed
  context changes to B. Submit once and verify the created action's date,
  channel, KPI values, breach type, and manager all match B and none match A;
  this proves Submit recaptured `First(PowerBIIntegration.Data)` before
  validation and Patch.
- [ ] Through an isolated test path, supply a known within-target row to the
  Power Apps visual and enter otherwise valid fields. Confirm Submit's explicit
  `varIsBreach` branch shows the within-target message, creates no SharePoint
  action, and produces no Teams/Outlook alert.
- [ ] Supply zero rows, then at least two rows, to
  `PowerBIIntegration.Data`. For each case verify the form is hidden, the
  `Select exactly one performance row` guidance is visible, and an attempted
  Submit through the isolated test path follows the cardinality-error branch
  before breach validation or `Patch`. Confirm no SharePoint action and no
  Teams/Outlook alert for either row count.

## Power Automate notification QA

- [ ] Record the SharePoint site, test-list names, flow owner/connection, and
  whether the alert uses Teams or Outlook. Verify the connection owner has Edit
  access to both lists and permission to send the selected notification.
- [ ] Verify that the flow configuration uses the actual SharePoint **internal
  names** for `AlertSent`, `PerformanceDate`, `Channel`, and `BreachType`.
  Display names are not a safe substitute if a column was renamed or recreated.
- [ ] Create one new manual `SLA Recovery Actions` item with `AlertSent = No`
  and a monitored manager address. Verify exactly one manager alert contains
  date, channel, breach type, SLA/ACR, root cause, recovery action, owner, due
  date, and status. Verify that exact item is updated to `AlertSent = Yes` with
  a nonblank `AlertSentAt`.
- [ ] Verify the action-triggered flow uses the `When an item is created`
  trigger and the `AlertSent = false` trigger condition. Edit the sent item and
  verify the edit produces no second alert.
- [ ] Run the scheduled breach flow twice for one known breached date/channel.
  Verify the first run creates one automated action and one alert through the
  action-triggered flow; verify the second creates neither action nor alert.
- [ ] In the Recurrence trigger settings, verify **Concurrency Control** is on
  with degree `1`. Verify the performance-row **Apply to each** is sequential
  and the Get/filter/zero-match/create path has no parallel branch.
- [ ] Run the documented overlap test with a temporary two-minute Delay and
  one-minute test recurrence. Verify the second trigger fires while the first
  run is active but does not enter the keyed path concurrently. Across both run
  URLs, confirm exactly one automated action, one ActionID, and one alert; then
  remove the Delay and restore the approved daily recurrence.
- [ ] Inspect the scheduled-flow filters: both the performance query and the
  recovery-action deduplication query must use a UTC day range (`>=` day start,
  `<` next-day start), not an exact Date-only/date-time equality. Verify that
  deduplication also matches the same `BreachType` after the date/channel
  query.
- [ ] Test a within-target row and an `OfferedContacts = 0` row. Confirm neither
  creates an action or alert, and confirm the zero-offered path is skipped
  before SLA/ACR division.
- [ ] Force or use an invalid test recipient once. Verify a failed send leaves
  `AlertSent = No` and `AlertSentAt` blank; do not sign off until a repaired
  test send succeeds exactly once.

## Test-workspace publication and refresh QA

- [ ] Save the validated `.pbix` with the documented model and visual field
  contract intact.
- [ ] An authorized report owner publishes the report to the designated **test
  workspace** and records the resulting dataset/report links and timestamp.
- [ ] In the test workspace, open the published report and repeat the slicer,
  exception-table, and Power Apps checks above.
- [ ] Open the dataset's settings and inspect **Data source credentials**.
  Confirm the configured SharePoint Online credentials are the intended
  organizational account and authentication method for the source site.
- [ ] Run or wait for a dataset refresh in the test workspace. Confirm it
  completes successfully, the refresh history identifies no credential error,
  and refreshed data is visible in the report.
- [ ] If credentials, source URL, or owner differ from the intended production
  configuration, stop sign-off and correct the test-workspace configuration
  before proceeding.

## Sign-off

- [ ] All checks passed, or every exception is documented with an owner and
  remediation date.
- [ ] Report QA approved by: ____________________  Date: ____________________
