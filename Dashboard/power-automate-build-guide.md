# Power Automate notification build guide

This guide configures two standard-connector Power Automate flows for the
`Channel Performance` and `SLA Recovery Actions` SharePoint lists. It is a
build and test procedure only; it does not create, deploy, enable, or publish
flows in any tenant.

## Before building

1. Confirm the two lists and columns match
   [sharepoint-lists-setup.md](sharepoint-lists-setup.md). The flow connection
   owner needs **Edit** permission to both lists, and must be permitted to send
   the selected Teams or Outlook notification.
2. In each list, open **List settings > Columns** and record the *internal
   names*. Power Automate OData filters and trigger-condition expressions must
   use those names, not necessarily the labels displayed in SharePoint. Names
   created exactly as documented normally remain `PerformanceDate`, `Channel`,
   `BreachType`, and `AlertSent`; renamed or recreated columns can differ.
3. This guide uses `Channel`, `BreachType`, and `Status` as SharePoint Choice
   columns. In action fields choose the matching **Value** dynamic-content
   token, and when creating an item choose the listed choice value. If the
   connector exposes a different internal name or Choice representation, use
   its column metadata rather than copying a display label.

## Flow 1 — notify a manager when an action is created

Create an **Automated cloud flow** named `Notify manager of SLA recovery action`.

1. Add SharePoint **When an item is created**. Select the site and the `SLA
   Recovery Actions` list.
2. Open the trigger's **Settings** and add this trigger condition exactly:

   ```text
   @equals(triggerOutputs()?['body/AlertSent'], false)
   ```

   Replace `AlertSent` only if the recorded internal name differs. This is an
   optimization: the flow still retains the explicit condition below. Because
   the trigger is *created* (not created-or-modified), the later update does
   not create a second alert.
3. Add a **Condition**. Select `AlertSent` from the trigger and test **is equal
   to** `false` (or use `@equals(triggerBody()?['AlertSent'], false)`). Leave
   the No branch empty/terminated.
4. In the Yes branch, add one notification action:

   - **Teams option:** Microsoft Teams **Post adaptive card in a chat or
     channel** (or the tenant's approved chat action), addressed to
     `ManagerEmail`.
   - **Outlook alternative:** Office 365 Outlook **Send an email (V2)**, with
     **To** set to `ManagerEmail` and subject `SLA recovery action — <Channel>
     — <PerformanceDate>`.

   Include these trigger values in the card or email body: `PerformanceDate`,
   `Channel` (Value), `BreachType` (Value), `SLA_Pct`, `ACR_Pct`, `RootCause`,
   `RecoveryAction`, `Owner`, `DueDate`, and `Status` (Value). Format the two
   ratios as percentages for readability if desired, but do not multiply the
   values stored back to SharePoint: they are decimal ratios.
5. After the notification action, add SharePoint **Update item** for the same
   site/list. Set **Id** to the trigger item's `ID`, set `AlertSent` to **Yes**,
   and set `AlertSentAt` with this expression:

   ```text
   utcNow()
   ```

   Supply any other required list fields from the trigger item, preserving
   existing values. Save the flow.

## Flow 2 — detect the previous UTC day's breaches

Create a **Scheduled cloud flow** named `Detect daily SLA and ACR breaches`.
Set **Recurrence** to daily at a time after the source-data load completes.
The schedule and both date filters use UTC; choose a later UTC time if the
source load is defined in local time.

Open the **Recurrence** trigger's **Settings**, turn **Concurrency Control**
on, and set **Degree of Parallelism** to `1`. Save the flow and reopen the
trigger settings to verify the value persisted. This serializes overlapping
runs of this scheduled flow, which is required because the deduplication path
below is a check followed by a create rather than one atomic SharePoint
operation.

Keep the keyed create path sequential inside each run as well. On **Apply to
each**, leave **Concurrency Control** off (the default) or turn it on with
degree `1`; do not process performance rows in parallel. Keep **Get items ->
Filter array -> zero-match Condition -> Create item** in one branch with no
parallel branch around those actions.

### Establish a date-only UTC range

Immediately after Recurrence add these **Compose** actions:

| Action name | Expression |
| --- | --- |
| `TargetDate` | `formatDateTime(addDays(utcNow(), -1), 'yyyy-MM-dd')` |
| `TargetDayStartUtc` | `concat(outputs('TargetDate'), 'T00:00:00Z')` |
| `TargetDayEndUtc` | `concat(formatDateTime(utcNow(), 'yyyy-MM-dd'), 'T00:00:00Z')` |

Use the half-open range `[TargetDayStartUtc, TargetDayEndUtc)` below. Do not
compare a SharePoint Date-only field to a bare `yyyy-MM-dd` string or an exact
midnight timestamp: SharePoint/OData serialization can introduce a time-zone
component and make logically identical dates fail to match.

### Read the performance rows and classify each result

1. Add SharePoint **Get items** for `Channel Performance`. In **Filter Query**
   enter the following expression, replacing `PerformanceDate` only with its
   recorded internal name:

   ```text
   concat(
     'PerformanceDate ge ''', outputs('TargetDayStartUtc'),
     ''' and PerformanceDate lt ''', outputs('TargetDayEndUtc'), ''''
   )
   ```

   Turn on pagination if the normal daily volume can exceed the connector's
   default page limit.
2. Add **Apply to each** over `value` from that Get items action. The following
   steps are inside this loop.
3. Add a Condition that skips the row when `OfferedContacts` is zero. Use this
   expression in the condition's advanced mode:

   ```text
   @greater(float(items('Apply_to_each')?['OfferedContacts']), 0)
   ```

   Leave the No branch empty. Put all remaining steps in Yes.
4. In the Yes branch, add these Compose actions. Use the performance list's
   internal names if they differ:

   ```text
   SLA: div(float(items('Apply_to_each')?['AnsweredWithinTarget']), float(items('Apply_to_each')?['OfferedContacts']))
   ACR: div(float(items('Apply_to_each')?['AbandonedContacts']), float(items('Apply_to_each')?['OfferedContacts']))
   ```

5. Add a Compose action named `BreachType` with:

   ```text
   if(
     and(
       less(outputs('SLA'), float(items('Apply_to_each')?['SLA_TargetPct'])),
       greater(outputs('ACR'), float(items('Apply_to_each')?['ACR_TargetPct']))
     ),
     'Both',
     if(
       less(outputs('SLA'), float(items('Apply_to_each')?['SLA_TargetPct'])),
       'SLA',
       if(
         greater(outputs('ACR'), float(items('Apply_to_each')?['ACR_TargetPct'])),
         'ACR',
         ''
       )
     )
   )
   ```

6. Add a Condition that continues only when `BreachType` is not empty:

   ```text
   @not(empty(outputs('BreachType')))
   ```

### Deduplicate before creating an automated action

Inside the breach condition's Yes branch, add SharePoint **Get items** for
`SLA Recovery Actions`. Its OData filter should restrict only date and channel;
the subsequent Filter array checks the Choice value. This deliberately avoids
an exact Date-only/date-time comparison.

```text
concat(
  'PerformanceDate ge ''', outputs('TargetDayStartUtc'),
  ''' and PerformanceDate lt ''', outputs('TargetDayEndUtc'),
  ''' and Channel eq ''',
  replace(items('Apply_to_each')?['Channel']?['Value'], '''', ''''''),
  ''''
)
```

If `Channel` is exposed as text rather than a Choice object, use
`items('Apply_to_each')?['Channel']` in the expression. Replace both
`PerformanceDate` and `Channel` with the action-list internal names where
needed.

Then add **Filter array**:

- **From:** `value` from the action-list Get items action.
- **Advanced mode:**

  ```text
  @equals(item()?['BreachType']?['Value'], outputs('BreachType'))
  ```

  If the connector returns this Choice as plain text, use
  `@equals(item()?['BreachType'], outputs('BreachType'))` instead. Validate
  this once with a real item before enabling the schedule.

Add a Condition with:

```text
@equals(length(body('Filter_array')), 0)
```

Only in its Yes branch, add SharePoint **Create item** in `SLA Recovery
Actions`, mapping the following values:

| Column | Value |
| --- | --- |
| Title | `TargetDate | Channel Value` |
| ActionID | `guid()` |
| PerformanceDate | `TargetDate` |
| Channel | performance row's Channel Value |
| SLA_Pct / ACR_Pct | outputs of the `SLA` / `ACR` Compose actions |
| BreachType | output of `BreachType` |
| RootCause | `Automated threshold detection — review required` |
| RecoveryAction | `Assign recovery action` |
| Owner | `Supervisor` |
| DueDate | `TargetDate` (or replace with the approved operational due-date rule) |
| Status | `Open` |
| ManagerEmail | performance row's `ManagerEmail` |
| AlertSent | `No` |

Do **not** send a second message in this scheduled flow. The newly created
item enters Flow 1, which is the single notification path and sets its sent
timestamp. Existing manual actions intentionally participate in the same
date/channel/breach-type deduplication check; the convention is not a unique
SharePoint constraint, so manual action history remains allowed.

Serialization protects this path only when this scheduled flow is the sole
writer of automated breach actions. If another flow, app, script, or service
can create automated actions, add an `AutomationKey` Single line of text column
with **Enforce unique values = Yes**. Leave it blank for manual actions, and
require every automated writer to set the same normalized
`yyyy-MM-dd|CHANNEL|BREACHTYPE` value. Treat a duplicate-key Create item failure
as an already-created result. The unique SharePoint constraint is the atomic
guard in that multi-writer design; recurrence serialization alone is not.

## Required tests

Run these tests in a test site/list with a monitored test manager address;
record the flow run links, item IDs, and results in the QA checklist.

1. Create one new manual recovery action with `AlertSent = No`. Verify exactly
   one Teams/Outlook alert is received, then verify that same action has
   `AlertSent = Yes` and a nonblank `AlertSentAt`.
2. Verify the saved **Recurrence** settings show Concurrency Control on with
   degree `1`, and verify **Apply to each** is sequential. Select a known
   breached performance row and run the scheduled flow twice sequentially. The
   first run must create one automated action and produce one alert through
   Flow 1. The second must create no action and produce no alert.
3. Run against a row within both targets: no action and no alert. Run against a
   row with `OfferedContacts = 0`: no action and no alert. Confirm the run
   history shows the zero-offered branch was skipped before division.
4. If a notification send fails, verify the item remains `AlertSent = No` with
   no `AlertSentAt`; repair the recipient/connection and retry with a new test
   action. Do not mark an alert as sent before the send action succeeds.
5. Exercise a real overlap in the isolated test flow: temporarily set
   Recurrence to every minute and add a test-only two-minute **Delay**
   immediately after the trigger. Start with no action for the chosen known
   breach. Let a second recurrence fire while the first run is delayed. Verify
   in run history that the second run does not execute the keyed path
   concurrently; it waits until the first run finishes, then observes the
   existing action. Across both runs, verify exactly one automated action, one
   `ActionID`, and one Flow 1 notification. Record both run URLs, start/end
   times, and the item ID. Remove the test Delay and restore the approved daily
   recurrence after the test.
