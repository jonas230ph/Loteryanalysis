# Call Center Workforce SLA Prototype Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver import-ready test data and complete build instructions for a Power BI monthly SLA/ACR dashboard with a Power Apps recovery-action form and Power Automate manager alerts.

**Architecture:** SharePoint/Microsoft Lists holds daily performance and recovery-action records. Power BI imports both lists, calculates weighted SLA and ACR from contact counts, and hosts a canvas Power App for exceptions. Two Power Automate flows notify managers from manually submitted actions and scheduled threshold checks.

**Tech Stack:** Power BI Desktop/Service, Power Query (M), DAX, SharePoint/Microsoft Lists, Power Apps canvas app, Power Automate, Microsoft Teams or Outlook.

## Global Constraints

- All artifacts for this work live in `/Users/jonasodones/Desktop/Dashboard`.
- Use SharePoint/Microsoft Lists only; no premium connector or Dataverse dependency.
- Calculate SLA and ACR from totals: never average daily percentages.
- Treat `OfferedContacts = 0` as blank for SLA and ACR.
- Initial targets: Voice SLA 80%, Voice ACR 5%, Chat SLA 85%, Chat ACR 4%.
- A breach is SLA below target or ACR above target.
- Avoid duplicate automated actions for the same performance date, channel, and breach type.

---

### Task 1: Create validated sample data files

**Files:**
- Create: `/Users/jonasodones/Desktop/Dashboard/channel_performance_sample.csv`
- Create: `/Users/jonasodones/Desktop/Dashboard/sla_recovery_actions_sample.csv`
- Create: `/Users/jonasodones/Desktop/Dashboard/README.md`

**Interfaces:**
- Produces `Channel Performance` import columns: `PerformanceDate`, `MonthStart`, `Channel`, `OfferedContacts`, `AnsweredWithinTarget`, `AbandonedContacts`, `SLA_TargetPct`, `ACR_TargetPct`, `Supervisor`, `ManagerEmail`.
- Produces `SLA Recovery Actions` import columns: `ActionID`, `PerformanceDate`, `Channel`, `SLA_Pct`, `ACR_Pct`, `BreachType`, `RootCause`, `RecoveryAction`, `Owner`, `DueDate`, `Status`, `ManagerEmail`, `AlertSent`, `AlertSentAt`.

- [ ] **Step 1: Define the deterministic performance sample**

Create daily Voice and Chat rows spanning May through July 2026. Include at least 10 breach rows across both channels, including individual SLA, ACR, and combined breaches. Ensure every row satisfies `AnsweredWithinTarget + AbandonedContacts <= OfferedContacts`.

- [ ] **Step 2: Add recovery-action sample rows**

Create action rows for a subset of breached days. Use `AlertSent` values `Yes` and `No`, open and completed statuses, and valid ISO date-time values for sent alerts.

- [ ] **Step 3: Validate source data before import**

Run this validation in Power Query or an equivalent local check:

```text
PerformanceDate is a valid Date
MonthStart equals the first day of PerformanceDate's month
Channel is Voice or Chat
OfferedContacts > 0
0 <= AnsweredWithinTarget <= OfferedContacts
0 <= AbandonedContacts <= OfferedContacts
AnsweredWithinTarget + AbandonedContacts <= OfferedContacts
SLA_TargetPct and ACR_TargetPct are decimal values from 0 to 1
```

- [ ] **Step 4: Document import mapping**

In `README.md`, provide a two-column mapping of CSV headers to SharePoint column type: Date, Number, Choice, Single line of text, Yes/No, and Date and Time. State that `ActionID` is a Single line of text, not SharePoint's generated ID.

- [ ] **Step 5: Verify sample calculations**

Hand-check one Voice and one Chat sample row with:

```text
SLA % = AnsweredWithinTarget / OfferedContacts
ACR % = AbandonedContacts / OfferedContacts
```

Expected: each marked breach is explained by the relevant target comparison.

### Task 2: Configure SharePoint/Microsoft Lists data storage

**Files:**
- Create: `/Users/jonasodones/Desktop/Dashboard/sharepoint-lists-setup.md`

**Interfaces:**
- Consumes: CSV schemas from Task 1.
- Produces two SharePoint lists named `Channel Performance` and `SLA Recovery Actions`, which Power BI, Power Apps, and Power Automate can access.

- [ ] **Step 1: Specify the `Channel Performance` list**

Document these exact columns in addition to the SharePoint `Title` field, which may be hidden:

```text
PerformanceDate (Date only)
MonthStart (Date only)
Channel (Choice: Voice, Chat)
OfferedContacts (Number, 0 decimals)
AnsweredWithinTarget (Number, 0 decimals)
AbandonedContacts (Number, 0 decimals)
SLA_TargetPct (Number, 2 decimals)
ACR_TargetPct (Number, 2 decimals)
Supervisor (Single line of text)
ManagerEmail (Single line of text)
```

- [ ] **Step 2: Specify the `SLA Recovery Actions` list**

Document these exact columns:

```text
ActionID (Single line of text)
PerformanceDate (Date only)
Channel (Choice: Voice, Chat)
SLA_Pct (Number, 4 decimals)
ACR_Pct (Number, 4 decimals)
BreachType (Choice: SLA, ACR, Both)
RootCause (Multiple lines of text)
RecoveryAction (Multiple lines of text)
Owner (Single line of text)
DueDate (Date only)
Status (Choice: Open, In Progress, Complete)
ManagerEmail (Single line of text)
AlertSent (Yes/No; default No)
AlertSentAt (Date and Time)
```

- [ ] **Step 3: Import and inspect the samples**

Use **New > List > From CSV** for each source. Confirm all dates are actual dates, percent targets remain decimal values (for example, `0.8`), and the row counts equal their CSV counts.

- [ ] **Step 4: Add duplicate-prevention views**

Create an `Open Alerts` view filtered to `AlertSent = No`, and an `Automated Breach Key` display convention of `PerformanceDate | Channel | BreachType` for flow filtering. The scheduled flow is serialized at concurrency `1`, so no unique column is needed when it is the only automated writer. If another automated writer exists, add a separately unique `AutomationKey` populated only by automated writers; manual action history may still contain multiple records.

- [ ] **Step 5: Validate list permissions**

Confirm supervisors have Contribute access; managers have Read access to performance and recovery action lists; the flow connection owner has Edit access.

### Task 3: Build the Power BI model and measures

**Files:**
- Create: `/Users/jonasodones/Desktop/Dashboard/power-bi-build-guide.md`

**Interfaces:**
- Consumes: the two SharePoint lists from Task 2.
- Produces: `Channel Performance`, `SLA Recovery Actions`, `Calendar`, and DAX measures used by Task 4 and passed to the embedded Power App.

- [ ] **Step 1: Connect with SharePoint Online List**

In Power BI Desktop, select **Get data > SharePoint Online List**, enter the site root URL, and select both lists. In Power Query, set field types exactly as documented in Task 2. Remove unused SharePoint system columns, but retain `SLA Recovery Actions[Created]` and numeric `[ID]` for deterministic latest-action selection.

- [ ] **Step 2: Create a calendar table and relationships**

Create this DAX table:

```DAX
Calendar =
ADDCOLUMNS(
    CALENDAR(
        MIN('Channel Performance'[PerformanceDate]),
        MAX('Channel Performance'[PerformanceDate])
    ),
    "Month Start", DATE(YEAR([Date]), MONTH([Date]), 1),
    "Month Label", FORMAT([Date], "yyyy-MM")
)
```

Create an active one-to-many, single-direction relationship from `Calendar[Date]` to `Channel Performance[PerformanceDate]`. Keep the direct Calendar-to-actions relationship inactive for Operations Overview and do not create an active performance-to-actions relationship; the latest-action measures filter actions explicitly by normalized date/channel key. Sort `Calendar[Month Label]` by `Calendar[Month Start]`.

- [ ] **Step 3: Create weighted KPI measures**

Add these measures:

```DAX
Offered Contacts = SUM('Channel Performance'[OfferedContacts])

Answered Within Target = SUM('Channel Performance'[AnsweredWithinTarget])

Abandoned Contacts = SUM('Channel Performance'[AbandonedContacts])

SLA % = DIVIDE([Answered Within Target], [Offered Contacts])

ACR % = DIVIDE([Abandoned Contacts], [Offered Contacts])

SLA Target % = AVERAGE('Channel Performance'[SLA_TargetPct])

ACR Target % = AVERAGE('Channel Performance'[ACR_TargetPct])

SLA Variance (pp) = [SLA %] - [SLA Target %]

ACR Variance (pp) = [ACR %] - [ACR Target %]
```

Format percentage measures as Percentage with one decimal place. `DIVIDE` returns blank for zero offered contacts.

- [ ] **Step 4: Create breach measures**

Add these measures:

```DAX
SLA Breach Days =
COUNTROWS(
    FILTER(
        'Channel Performance',
        'Channel Performance'[OfferedContacts] > 0
            &&
        DIVIDE(
            'Channel Performance'[AnsweredWithinTarget],
            'Channel Performance'[OfferedContacts]
        ) < 'Channel Performance'[SLA_TargetPct]
    )
)

ACR Breach Days =
COUNTROWS(
    FILTER(
        'Channel Performance',
        'Channel Performance'[OfferedContacts] > 0
            &&
        DIVIDE(
            'Channel Performance'[AbandonedContacts],
            'Channel Performance'[OfferedContacts]
        ) > 'Channel Performance'[ACR_TargetPct]
    )
)

Total Breach Days = [SLA Breach Days] + [ACR Breach Days]
```

- [ ] **Step 5: Test measure correctness**

Filter the model to one row and compare the report KPI values to the Task 1 calculation. Filter a whole month and verify SLA/ACR use total numerators and denominators rather than averages of daily percentages.

### Task 4: Assemble and publish the Power BI report

**Files:**
- Modify: `/Users/jonasodones/Desktop/Dashboard/power-bi-build-guide.md`
- Create: `/Users/jonasodones/Desktop/Dashboard/power-bi-qa-checklist.md`

**Interfaces:**
- Consumes: model tables and measures from Task 3.
- Produces: a published Power BI report with a filtered dataset supplied to the Power Apps visual.

- [ ] **Step 1: Create Operations Overview page**

Add slicers for `Calendar[Month Label]`, `Channel Performance[Channel]`, and `Channel Performance[Supervisor]`. Add KPI cards for `[SLA %]`, `[SLA Target %]`, `[ACR %]`, `[ACR Target %]`, and `[Total Breach Days]`.

- [ ] **Step 2: Add comparison and trend visuals**

Add a clustered-column chart with Channel on X-axis and `[SLA %]`, `[SLA Target %]` as values. Add a second with `[ACR %]`, `[ACR Target %]`. Add a line chart with `Calendar[Date]` on X-axis and `[SLA %]`, `[ACR %]` as values. Use green for within target and red/orange for breach variance.

- [ ] **Step 3: Add exception table**

Add a normalized `PerformanceChannelKey` to both queries. Create `[Related Action Status]` and `[Related Action AlertSent]` measures that select one action with `TOPN(1, ...)`, ordered by SharePoint `Created` descending and numeric `ID` descending. Add a table containing `PerformanceDate`, `Channel`, `[SLA %]`, `[SLA Target %]`, `[ACR %]`, `[ACR Target %]`, `Supervisor`, `ManagerEmail`, and those two measures. Add an `[Exception Row]` measure that returns `1` only when offered contacts are positive and SLA or ACR breaches its target; set the table's visual-level filter to `[Exception Row] is 1`. Apply conditional formatting: red SLA when below SLA target; red ACR when above ACR target.

- [ ] **Step 4: Add a Power Apps visual data contract**

Insert a Power Apps visual and pass these fields in this order: `PerformanceDate`, `Channel`, `Supervisor`, `ManagerEmail`, `[SLA %]`, `[ACR %]`, `[SLA Target %]`, `[ACR Target %]`. Document that live controls read `First(PowerBIIntegration.Data)` directly and quote measure names, such as `First(PowerBIIntegration.Data).'SLA %'`. Submit recaptures that record before validation and Patch.

- [ ] **Step 5: Publish and validate interactions**

Publish to a test workspace. Confirm every slicer cross-filters all visuals, a selected exception is supplied to Power Apps, and the report refresh uses the intended SharePoint credentials.

### Task 5: Create the embedded Power Apps recovery-action form

**Files:**
- Create: `/Users/jonasodones/Desktop/Dashboard/power-app-build-guide.md`

**Interfaces:**
- Consumes: Power BI field contract from Task 4 and `SLA Recovery Actions` list from Task 2.
- Produces: a canvas app that creates exactly one complete recovery action for the selected report context.

- [ ] **Step 1: Create the app from the Power BI visual**

Select **Create new** in the Power Apps visual and add `SLA Recovery Actions` as a SharePoint connection. Do not snapshot report context in `OnVisible`. Show `Select exactly one performance row in Power BI to create a recovery action.` rather than the form when:

```PowerFx
CountRows(PowerBIIntegration.Data) <> 1
```

Show the form only when `CountRows(PowerBIIntegration.Data) = 1`.

- [ ] **Step 2: Add controlled input fields**

Create input controls named `txtRootCause`, `txtRecoveryAction`, `txtOwner`, `dpDueDate`, and `ddStatus`. Show read-only labels for date, channel, SLA, and ACR directly from `First(PowerBIIntegration.Data)` so they recalculate with report selections. Set `ddStatus.Items` to `["Open", "In Progress", "Complete"]` and default it to `"Open"`.

- [ ] **Step 3: Calculate breach type and validate fields**

At the beginning of the Submit button's `OnSelect`, capture the live record,
then calculate and validate against only that captured record:

```PowerFx
Set(varSelectionCount, CountRows(PowerBIIntegration.Data));
Set(
    varSelectedPerformance,
    If(varSelectionCount = 1, First(PowerBIIntegration.Data), Blank())
);
Set(
    varIsBreach,
    !IsBlank(varSelectedPerformance.'SLA %') &&
    !IsBlank(varSelectedPerformance.'ACR %') &&
    !IsBlank(varSelectedPerformance.'SLA Target %') &&
    !IsBlank(varSelectedPerformance.'ACR Target %') &&
    (
        varSelectedPerformance.'SLA %' < varSelectedPerformance.'SLA Target %' ||
        varSelectedPerformance.'ACR %' > varSelectedPerformance.'ACR Target %'
    )
);
Set(
    varBreachType,
    If(
        !varIsBreach,
        Blank(),
        If(
            varSelectedPerformance.'SLA %' < varSelectedPerformance.'SLA Target %' &&
            varSelectedPerformance.'ACR %' > varSelectedPerformance.'ACR Target %',
            "Both",
            If(
                varSelectedPerformance.'SLA %' < varSelectedPerformance.'SLA Target %',
                "SLA",
                "ACR"
            )
        )
    )
);
Set(
    varIsValid,
    varSelectionCount = 1 &&
    varIsBreach &&
    !IsBlank(Trim(txtRootCause.Text)) &&
    !IsBlank(Trim(txtRecoveryAction.Text)) &&
    !IsBlank(Trim(txtOwner.Text)) &&
    !IsBlank(dpDueDate.SelectedDate) &&
    !IsBlank(varSelectedPerformance.PerformanceDate) &&
    !IsBlank(varSelectedPerformance.Channel) &&
    !IsBlank(varSelectedPerformance.'SLA %') &&
    !IsBlank(varSelectedPerformance.'ACR %') &&
    !IsBlank(varSelectedPerformance.'SLA Target %') &&
    !IsBlank(varSelectedPerformance.'ACR Target %') &&
    !IsBlank(varSelectedPerformance.ManagerEmail)
)
```

- [ ] **Step 4: Patch a recovery action**

Continue the same Submit button `OnSelect` with the guarded Patch below. The
complete production formula, including duplicate-click and error handling, is
in `power-app-build-guide.md`.

```PowerFx
If(
    varSelectionCount <> 1,
    Notify("Select exactly one performance row in Power BI. No recovery action was created.", NotificationType.Error),
    If(
        !varIsBreach,
        Notify("The selected performance row is within target. No recovery action was created.", NotificationType.Error),
        If(
            !varIsValid,
            Notify("Complete root cause, recovery action, owner, due date, and manager email.", NotificationType.Error),
            Patch(
                'SLA Recovery Actions',
                Defaults('SLA Recovery Actions'),
                {
                    Title: Text(varSelectedPerformance.PerformanceDate, "[$-en-US]yyyy-mm-dd") & " | " & varSelectedPerformance.Channel,
                    ActionID: Text(GUID()),
                    PerformanceDate: varSelectedPerformance.PerformanceDate,
                    Channel: {Value: varSelectedPerformance.Channel},
                    SLA_Pct: varSelectedPerformance.'SLA %',
                    ACR_Pct: varSelectedPerformance.'ACR %',
                    BreachType: {Value: varBreachType},
                    RootCause: txtRootCause.Text,
                    RecoveryAction: txtRecoveryAction.Text,
                    Owner: txtOwner.Text,
                    DueDate: dpDueDate.SelectedDate,
                    Status: {Value: ddStatus.Selected.Value},
                    ManagerEmail: varSelectedPerformance.ManagerEmail,
                    AlertSent: false
                }
            );
            Notify("Recovery action submitted. The manager alert will be sent automatically.", NotificationType.Success);
            Reset(txtRootCause); Reset(txtRecoveryAction); Reset(txtOwner); Reset(dpDueDate); Reset(ddStatus)
        )
    )
)
```

- [ ] **Step 5: Test manual submission**

In Power BI Service, select breach A, then change to a different breach B without reloading or reopening the visible app. Confirm its read-only context updates, submit a fully populated action, and confirm one list item appears with B's context (not A's), generated ActionID, `AlertSent = No`, and the success notification. In an isolated test path, supply a within-target row and confirm the explicit `varIsBreach` branch creates no action and sends no alert. Also test zero and multiple `PowerBIIntegration.Data` rows: the form stays hidden, selection guidance appears, and neither case creates an action or alert.

### Task 6: Build and test Power Automate notifications

**Files:**
- Create: `/Users/jonasodones/Desktop/Dashboard/power-automate-build-guide.md`
- Modify: `/Users/jonasodones/Desktop/Dashboard/power-bi-qa-checklist.md`

**Interfaces:**
- Consumes: recovery actions from Power Apps and performance rows from SharePoint.
- Produces: one action-triggered manager alert and one deduplicated daily breach-monitoring alert.

- [ ] **Step 1: Build the action-triggered alert flow**

Create an Automated cloud flow named `Notify manager of SLA recovery action` with trigger **When an item is created** on `SLA Recovery Actions`. Add condition `AlertSent` equals `false`. In the Yes branch, send a Teams chat/adaptive card or Outlook email to `ManagerEmail` with Date, Channel, BreachType, SLA_Pct, ACR_Pct, RootCause, RecoveryAction, Owner, DueDate, and Status. Then update the same item: `AlertSent = true`, `AlertSentAt = utcNow()`.

- [ ] **Step 2: Guard against repeated action-flow alerts**

Add a trigger condition to reduce unnecessary runs:

```text
@equals(triggerOutputs()?['body/AlertSent'], false)
```

Retain the post-send Update item step; it prevents later edits from being interpreted as a new alert because the trigger fires only on item creation.

- [ ] **Step 3: Build the scheduled threshold-monitoring flow**

Create a Scheduled cloud flow named `Detect daily SLA and ACR breaches`, recurring daily after the source data load. On the Recurrence trigger, enable Concurrency Control with degree `1`. Keep Apply to each sequential and keep the Get/filter/zero-match/create path in one branch. Get `Channel Performance` rows for the prior UTC day using a half-open UTC range. For each row, use numeric expressions:

```text
SLA = div(float(AnsweredWithinTarget), float(OfferedContacts))
ACR = div(float(AbandonedContacts), float(OfferedContacts))
```

Skip any row with `OfferedContacts` equal to zero. Determine `BreachType` as `Both`, `SLA`, `ACR`, or no breach based on the fixed target columns.

- [ ] **Step 4: Deduplicate automated actions**

Before `Create item`, run **Get items** against `SLA Recovery Actions` with an OData filter that matches the date and channel. In a Filter array or condition, require a matching `BreachType`. Create and notify only when the filtered array length is zero. Populate `ActionID` with `guid()`, set `RootCause` to `Automated threshold detection — review required`, `RecoveryAction` to `Assign recovery action`, `Owner` to `Supervisor`, `Status` to `Open`, and `AlertSent` to `No`; allow the action-triggered flow to handle the notification. If any other automated writer exists, use a unique normalized `AutomationKey` on every writer as the atomic guard.

- [ ] **Step 5: Test flow outcomes**

Test the action-triggered flow with a new manual action and verify exactly one manager alert and `AlertSentAt`. Verify Recurrence concurrency is `1`, then test the scheduled flow twice sequentially against the same known breach. Also force an overlap with a one-minute test recurrence and a two-minute test Delay: the second trigger must wait, and both runs together must produce exactly one action/alert. Remove the Delay and restore the daily schedule. Test a within-target row and a zero-offered row: both must produce neither action nor alert.

### Task 7: Run end-to-end acceptance and handoff

**Files:**
- Create: `/Users/jonasodones/Desktop/Dashboard/end-to-end-test-results.md`
- Modify: `/Users/jonasodones/Desktop/Dashboard/README.md`

**Interfaces:**
- Consumes: all previous deliverables.
- Produces: a reproducible operational demo and an evidence-based test record.

- [ ] **Step 1: Validate reporting scenarios**

Record results for Voice-only, Chat-only, and all-channel monthly filters. For each scenario, verify weighted SLA/ACR, correct targets, breach count, and visual interaction behavior.

- [ ] **Step 2: Validate the supervisor workflow**

Select a visible breach, submit a recovery action through the embedded Power App, then verify the action appears in SharePoint and follows the selected filter context.

- [ ] **Step 3: Validate manager notification workflow**

Verify the manager receives the message containing the actionable fields and the SharePoint action changes to `AlertSent = Yes` with a timestamp.

- [ ] **Step 4: Validate resilience cases**

Attempt submit with each required field blank and verify the app blocks submission. Test zero-offered contacts, duplicate scheduled breach processing, and invalid manager email. Record expected versus actual outcomes in `end-to-end-test-results.md`.

- [ ] **Step 5: Complete handoff documentation**

In `README.md`, link every guide, list the required Microsoft 365 permissions, describe refresh/flow ownership, and state that sample data uses fictional people and manager addresses. Add a short teardown section identifying the two test lists and test flows that can be removed after validation.
