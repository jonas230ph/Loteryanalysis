# Embedded Power Apps recovery-action form

This guide builds a canvas app inside the **Power Apps** visual on the
Operations Overview report page. The app creates one new `SLA Recovery Actions`
item for the single date/channel row selected in Power BI. It does not publish
or deploy the app.

## Prerequisites and data contract

Before creating the app, create the `SLA Recovery Actions` SharePoint list and
its columns as specified in
[`sharepoint-lists-setup.md`](sharepoint-lists-setup.md). The app maker must
have permission to create list items.

In the report's Power Apps visual, add these fields in this exact order:

1. `PerformanceDate`
2. `Channel`
3. `Supervisor`
4. `ManagerEmail`
5. `[SLA %]`
6. `[ACR %]`
7. `[SLA Target %]`
8. `[ACR Target %]`

The visual supplies these values through the live, context-aware
`PowerBIIntegration.Data` data source. Read-only controls and visibility rules
must read that data source directly so they recalculate when the report
selection changes. The four measures are named fields, not source-table
columns, and their names must stay quoted in Power Fx. For example, a live
control can use:

```powerfx
First(PowerBIIntegration.Data).'SLA %'
First(PowerBIIntegration.Data).'ACR %'
First(PowerBIIntegration.Data).'SLA Target %'
First(PowerBIIntegration.Data).'ACR Target %'
```

Do not reorder, rename, or substitute the visual fields without revising the
app. The app accepts exactly one row from the visual; it must never silently
use the first row when zero or multiple rows are supplied.

## Create the embedded app

1. Insert a **Power Apps** visual on the Operations Overview page and add the
   fields above to its data pane.
2. Select **Create new**, which opens the canvas app associated with this
   visual.
3. In the canvas app, add the SharePoint connection for the `SLA Recovery
   Actions` list. Use the same SharePoint site that hosts the dashboard lists.
4. Do not snapshot `PowerBIIntegration.Data` in the screen's **OnVisible**
   property. A behavior variable does not automatically recalculate when a
   report selection changes while the screen remains visible.
5. Add a label above the form with this **Visible** property:

   ```powerfx
   CountRows(PowerBIIntegration.Data) <> 1
   ```

   Set its **Text** property to `Select exactly one performance row in Power BI
   to create a recovery action.` Set the form container's **Visible** property
   to:

   ```powerfx
   CountRows(PowerBIIntegration.Data) = 1
   ```

This hides the form for both zero-row and multi-row contexts. Because these
formulas read `PowerBIIntegration.Data` directly, the visible context follows
slicer and row changes without reloading or reopening the visual. The Submit
formula below independently captures the current row count first and captures
a record only when that count is exactly one.

## Add form controls

Place these editable controls inside the form container and preserve their
names exactly:

| Control name | Suggested control | Required configuration |
| --- | --- | --- |
| `txtRootCause` | Text input | Enable multiline input for the SharePoint Multiple lines of text field. |
| `txtRecoveryAction` | Text input | Enable multiline input for the SharePoint Multiple lines of text field. |
| `txtOwner` | Text input | Single-line text input. |
| `dpDueDate` | Date picker | The user chooses the recovery due date. |
| `ddStatus` | Dropdown | **Items** is `["Open", "In Progress", "Complete"]`; **Default** is `"Open"`. |

Add read-only labels for the selected context. Example **Text** properties:

```powerfx
Text(First(PowerBIIntegration.Data).PerformanceDate, "[$-en-US]yyyy-mm-dd")
First(PowerBIIntegration.Data).Channel
Text(First(PowerBIIntegration.Data).'SLA %', "0.0%")
Text(First(PowerBIIntegration.Data).'ACR %', "0.0%")
```

It is also useful to display `First(PowerBIIntegration.Data).Supervisor`, the
two targets, and the manager email as read-only context; do not let these
values be edited in the form. Every read-only context control must use
`First(PowerBIIntegration.Data)` rather than `varSelectedPerformance`.

## Calculate and validate before saving

Add a Submit button. Its complete formula in the next section calculates
`varBreachType` and `varIsValid` before it can write to SharePoint.

The report table is filtered to breach rows, but the app must not rely on that
filter as its only guard. The captured record must independently satisfy at
least one breach predicate before the app classifies or saves it.

## Submit a new recovery action

The following **OnSelect** formula creates one list item only when validation
succeeds; it never updates an existing action.

Set the Submit button's **DisplayMode** property so it cannot be selected again
while a write is underway:

```powerfx
If(varSubmitting, DisplayMode.Disabled, DisplayMode.Edit)
```

Before its first use, `varSubmitting` is blank and therefore behaves as false.
The submit formula explicitly sets it to true immediately before `Patch` and
clears it for both the success and error paths. Replace the button's complete
**OnSelect** formula with:

```powerfx
If(
    !varSubmitting,
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
    );
    If(
        varSelectionCount <> 1,
        Notify("Select exactly one performance row in Power BI. No recovery action was created.", NotificationType.Error),
        If(
            !varIsBreach,
            Notify("The selected performance row is within target. No recovery action was created.", NotificationType.Error),
            If(
                !varIsValid,
                Notify("Complete root cause, recovery action, owner, due date, and manager email.", NotificationType.Error),
                Set(varSubmitting, true);
                IfError(
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
                    Reset(txtRootCause); Reset(txtRecoveryAction); Reset(txtOwner); Reset(dpDueDate); Reset(ddStatus);
                    Set(varSubmitting, false),
                    Notify("Recovery action could not be submitted. Check your list permissions and try again.", NotificationType.Error);
                    Set(varSubmitting, false)
                )
            )
        )
    )
)
```

The first statement inside the `!varSubmitting` branch captures cardinality.
Only `varSelectionCount = 1` permits `First(PowerBIIntegration.Data)` to be
stored. The cardinality-error branch precedes the breach and validation
branches, so zero or multiple rows never reach `Patch`. Do not move either
capture back to `OnVisible` or below validation.

`varIsBreach` is the independent submit guard. A within-target record sets
`varBreachType` to blank, follows the first notification branch, never reaches
`Patch`, creates no SharePoint item, and therefore triggers no manager alert.

`Channel`, `BreachType`, and `Status` are SharePoint Choice fields, so their
values are patched as `{Value: ...}` records. `SLA_Pct` and `ACR_Pct` stay as
decimal numbers (for example, `0.7583`), and `AlertSent: false` writes **No**.
`ActionID` is generated for each successful new action. The success message and
input resets occur only after a successful Patch. A failed Patch keeps the
entered values, displays an error, and re-enables the button.

## Manual test procedure

1. Save the app, return to the report, and use the Power BI Service test
   workspace to select one known breach row.
2. Confirm the app displays the selected date, channel, SLA, and ACR. Confirm
   it does not display the form when no row is selected.
3. Enter root cause, recovery action, owner, a due date, and retain the Open
   status. Select **Submit** once.
4. In `SLA Recovery Actions`, confirm exactly one new item has the selected
   `PerformanceDate`, `Channel`, `SLA_Pct`, and `ACR_Pct`; a generated
   `ActionID`; the calculated `BreachType`; `Status = Open`; and `AlertSent =
   No`.
5. Confirm the success notification is displayed and that the editable fields
   reset. Test a missing required field separately and confirm that no list item
   is created and the error notification is shown.
6. While a valid submission is in progress, try selecting **Submit** again.
   Confirm the button is disabled and that the list contains only one new item.
7. Test a failed write (for example, using a test account without Contribute
   access to the list). Confirm that the app shows the failed-submission error,
   re-enables Submit, preserves all entered values, and creates no item. Restore
   the account's expected permissions after this test.
8. In the published report, select breach A and confirm its date, channel, SLA,
   and ACR appear. Without reloading, reopening, or reselecting the Power Apps
   visual, change to a different breach B. Confirm every read-only value changes
   to B, enter valid action details, and select **Submit**. Verify the new list
   item's `PerformanceDate`, `Channel`, `SLA_Pct`, `ACR_Pct`, `BreachType`, and
   `ManagerEmail` all match B and none match A. Record both selections, the new
   SharePoint item ID, and screenshots in the end-to-end acceptance record.
9. In an isolated test path, supply one known within-target date/channel record
   to the Power Apps visual and enter otherwise valid action details. Select
   **Submit** and verify the within-target message appears, no SharePoint action
   is created, and no Teams/Outlook manager alert is sent. Record the selected
   KPI/target values, item-list search, and notification evidence.
10. Test selection cardinality twice: first supply zero rows, then supply at
    least two rows in `PowerBIIntegration.Data`. In both cases confirm the form
    is hidden, the `Select exactly one performance row` guidance is visible,
    and an attempted Submit through the isolated test path produces the same
    selection error. Verify neither case creates a SharePoint action or sends a
    manager alert. Record the row counts, screenshots, item-list searches, and
    notification evidence.

The manager alert is handled by the companion Power Automate flow after the
item is created; this app only writes the recovery action.
