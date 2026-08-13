# SharePoint / Microsoft Lists setup

This guide creates the two Lists used by the call-center workforce dashboard:
`Channel Performance` and `SLA Recovery Actions`. Keep the SharePoint-generated
`Title` column (it can be hidden from forms and views); it is not part of either
CSV schema.

## Before importing

Use the CSV files in this folder as the import sources:

- `channel_performance_sample.csv` — 184 data rows (92 Voice and 92 Chat)
- `sla_recovery_actions_sample.csv` — 8 data rows

Create each list with **New > List > From CSV**, select the relevant file, and
set the list name exactly as shown below. After import, inspect and correct the
column settings to match this guide. Both supplied samples import directly.
Do not import percentage values as a SharePoint Percentage column: they are
decimal ratios. For example, `0.8` must remain `0.8`, not be converted to `80`.

## List: Channel Performance

Create the following columns in addition to the SharePoint `Title` field.

| Column | Type and configuration |
| --- | --- |
| PerformanceDate | Date only |
| MonthStart | Date only |
| Channel | Choice: `Voice`, `Chat` |
| OfferedContacts | Number, 0 decimal places |
| AnsweredWithinTarget | Number, 0 decimal places |
| AbandonedContacts | Number, 0 decimal places |
| SLA_TargetPct | Number, 2 decimal places |
| ACR_TargetPct | Number, 2 decimal places |
| Supervisor | Single line of text |
| ManagerEmail | Single line of text |

Import `channel_performance_sample.csv`. In the resulting list, verify:

- **Items count** is **184**.
- `PerformanceDate` and `MonthStart` display as dates, not text strings.
- `SLA_TargetPct` and `ACR_TargetPct` are Number values and preserve decimal
  targets such as `0.80` and `0.05`.
- `Channel` contains only `Voice` and `Chat`.

## List: SLA Recovery Actions

Create the following columns in addition to the SharePoint `Title` field.

| Column | Type and configuration |
| --- | --- |
| ActionID | Single line of text |
| PerformanceDate | Date only |
| Channel | Choice: `Voice`, `Chat` |
| SLA_Pct | Number, 4 decimal places |
| ACR_Pct | Number, 4 decimal places |
| BreachType | Choice: `SLA`, `ACR`, `Both` |
| RootCause | Multiple lines of text |
| RecoveryAction | Multiple lines of text |
| Owner | Single line of text |
| DueDate | Date only |
| Status | Choice: `Open`, `In Progress`, `Complete` |
| ManagerEmail | Single line of text |
| AlertSent | Yes/No; default `No` |
| AlertSentAt | Date and Time |

Import `sla_recovery_actions_sample.csv` directly. In the resulting list,
verify:

- **Items count** is **8**.
- `PerformanceDate` and `DueDate` are dates, and `AlertSentAt` is Date and
  Time.
- `SLA_Pct` and `ACR_Pct` are decimal Number values with four places (for
  example, `0.7583`), not values multiplied by 100.
- `BreachType` contains only `SLA`, `ACR`, or `Both`; `Status` contains only
  `Open`, `In Progress`, or `Complete`.
- SharePoint's generated `Created` Date and Time and numeric `ID` fields remain
  available. Power BI retains them to select the latest action by `Created`
  descending, then `ID` descending; they are not CSV columns.

## Recovery-action views and flow key

### Open Alerts

In `SLA Recovery Actions`, create a public view named **Open Alerts**:

1. Open the view menu, select **Create new view**, and name it `Open Alerts`.
2. Filter where `AlertSent` **is equal to** `No`.
3. Include at least `PerformanceDate`, `Channel`, `BreachType`, `Owner`,
   `DueDate`, `Status`, and `ManagerEmail`; sort by `PerformanceDate`
   descending.
4. Save the view.

### Automated Breach Key

Use this display/calculation convention in Power Automate when filtering or
checking for related automated actions:

```text
PerformanceDate | Channel | BreachType
```

For example: `2026-05-14 | Voice | Both`. Format `PerformanceDate` as
`yyyy-MM-dd` before constructing the key so that locale display settings do not
change it. This convention is intentionally **not** a unique SharePoint column:
manual action history can legitimately contain more than one record for the
same key.

The scheduled flow is serialized at concurrency `1`, so this display key does
not need a unique column when that flow is the only automated writer. If any
other writer can create automated actions, follow the Power Automate guide's
atomic option: add a Single line of text `AutomationKey` with **Enforce unique
values = Yes**, leave it blank for manual actions, and require every automated
writer to populate the normalized `yyyy-MM-dd|CHANNEL|BREACHTYPE` key.

## Permissions validation

For both lists, use **Settings > List settings > Permissions for this list**
(or the site permissions interface if the list inherits permissions) and confirm
the following access assignments:

| User group / account | Required access |
| --- | --- |
| Supervisors | Contribute |
| Managers | Read, for both lists |
| Power Automate flow connection owner | Edit |

Record the group/account names and validation date in the implementation
handoff. Test as a supervisor that an item can be created or updated, as a
manager that the lists can be read but not changed, and with the flow connection
that an automated update succeeds.
