# Power BI build guide

This guide builds the model from the SharePoint Online lists named **Channel
Performance** and **SLA Recovery Actions**. Use the SharePoint *site root* URL
(for example, `https://contoso.sharepoint.com/sites/Operations`), not a URL to
an individual list, view, or item.

## 1. Load and shape the SharePoint lists

1. In Power BI Desktop, choose **Get data > SharePoint Online List**.
2. Enter the site root URL and sign in with the organizational account that can
   read both lists.
3. In the Navigator, select **Channel Performance** and **SLA Recovery
   Actions**, then choose **Transform Data**.
4. Rename the two queries exactly to `Channel Performance` and `SLA Recovery
   Actions`.
5. In `Channel Performance`, retain only the business columns in its table
   below. In `SLA Recovery Actions`, retain its business columns plus the
   SharePoint-generated `Created` and `ID` fields used to select the latest
   action deterministically. Remove other system metadata such as
   `ContentType`, `Modified`, `Author`, `Editor`, attachments, versioning
   fields, and URLs. `Title` may also be removed because it is not part of
   either model schema. Do not remove or rename action `Created` or `ID`.
6. Set the column types exactly as listed, then select **Close & Apply**.

### Channel Performance types

| Column | Power Query type |
| --- | --- |
| PerformanceDate | Date |
| MonthStart | Date |
| Channel | Text |
| OfferedContacts | Whole Number |
| AnsweredWithinTarget | Whole Number |
| AbandonedContacts | Whole Number |
| SLA_TargetPct | Decimal Number |
| ACR_TargetPct | Decimal Number |
| Supervisor | Text |
| ManagerEmail | Text |

### SLA Recovery Actions types

| Column | Power Query type |
| --- | --- |
| ID | Whole Number |
| Created | Date/Time/Timezone |
| ActionID | Text |
| PerformanceDate | Date |
| Channel | Text |
| SLA_Pct | Decimal Number |
| ACR_Pct | Decimal Number |
| BreachType | Text |
| RootCause | Text |
| RecoveryAction | Text |
| Owner | Text |
| DueDate | Date |
| Status | Text |
| ManagerEmail | Text |
| AlertSent | Logical |
| AlertSentAt | Date/Time/Timezone |

The percentage columns must remain decimal ratios: `0.80` means 80%, not 0.8%.
For `AlertSent`, map SharePoint **Yes/No** to Power Query **Logical**; keep
blank `AlertSentAt` values as null.

### Copyable Power Query type steps

After removing the unused columns, add a type step to each query in **Advanced
Editor**. Replace the prior step name with the actual preceding step name (for
example, `#\"Removed Other Columns\"`). These steps use the SharePoint list
field names exactly.

```powerquery
// Channel Performance
= Table.TransformColumnTypes(
    #\"Previous Step\",
    {
        {\"PerformanceDate\", type date},
        {\"MonthStart\", type date},
        {\"Channel\", type text},
        {\"OfferedContacts\", Int64.Type},
        {\"AnsweredWithinTarget\", Int64.Type},
        {\"AbandonedContacts\", Int64.Type},
        {\"SLA_TargetPct\", type number},
        {\"ACR_TargetPct\", type number},
        {\"Supervisor\", type text},
        {\"ManagerEmail\", type text}
    }
)
```

```powerquery
// SLA Recovery Actions
= Table.TransformColumnTypes(
    #\"Previous Step\",
    {
        {\"ID\", Int64.Type},
        {\"Created\", type datetimezone},
        {\"ActionID\", type text},
        {\"PerformanceDate\", type date},
        {\"Channel\", type text},
        {\"SLA_Pct\", type number},
        {\"ACR_Pct\", type number},
        {\"BreachType\", type text},
        {\"RootCause\", type text},
        {\"RecoveryAction\", type text},
        {\"Owner\", type text},
        {\"DueDate\", type date},
        {\"Status\", type text},
        {\"ManagerEmail\", type text},
        {\"AlertSent\", type logical},
        {\"AlertSentAt\", type datetimezone}
    }
)
```

If Power Query presents `Created` or `AlertSentAt` without a timezone, use
`type datetime` for that field instead; do not coerce a blank `AlertSentAt`
value to a date. `ID` is SharePoint's generated numeric item ID; it is distinct
from the business `ActionID` GUID text field.

## 2. Calendar and model relationships

Create the following calculated table using **Modeling > New table**:

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

In Model view, create the following relationships. `Calendar` must actively
filter `Channel Performance`; leave the direct Calendar-to-actions relationship
inactive by default so a later date-plus-channel action relationship does not
create two active filter paths.

| From | To | Cardinality / direction / state |
| --- | --- | --- |
| `Calendar[Date]` | `Channel Performance[PerformanceDate]` | One-to-many, single-direction, **active** |
| `Calendar[Date]` | `SLA Recovery Actions[PerformanceDate]` | One-to-many, single-direction, **inactive by default** |

Keep the direct Calendar-to-actions relationship inactive for the supported
latest-action measures in section 5, and do not create an active
Channel-Performance-to-actions key relationship. The measures filter the
actions table explicitly by normalized key, while report filtering follows the
single active `Calendar -> Channel Performance` path. A separate action-only
page may activate the direct Calendar-to-actions relationship only after its
filter paths are reviewed independently; it is not active on Operations
Overview.

Select `Calendar[Month Label]`, choose **Column tools > Sort by column**, and
select `Calendar[Month Start]`. Mark `Calendar` as a date table using its
`Date` column.

## 3. Measures

Create the following measures on `Channel Performance`. The SLA and ACR
measures intentionally divide summed numerators by summed offered contacts in
the current filter context. This produces weighted monthly and multi-channel
results; it never averages daily percentages. `DIVIDE` returns blank when no
offered contacts are in scope.

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

Format `SLA %`, `ACR %`, `SLA Target %`, `ACR Target %`, `SLA Variance (pp)`,
and `ACR Variance (pp)` as **Percentage** with **one decimal place**. Leave the
three contact measures as whole numbers. The target measures match the list
configuration: targets are stored as decimal Number values, not SharePoint
Percentage values.

### Breach measures

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

Each breach measure counts a performance row. A row that breaches both SLA and
ACR is counted once by each individual breach measure and therefore twice by
`Total Breach Days`—one breach event for each KPI.

## 4. Validation before building report visuals

Use a table visual with `PerformanceDate`, `Channel`, all raw contact columns,
the target columns, and the measures above.

1. Filter to **2026-05-05 / Voice**. The row has 120 offered contacts, 91
   answered within target, and 5 abandoned contacts. Verify `SLA % = 75.8%`,
   `ACR % = 4.2%`, `SLA Target % = 80.0%`, `ACR Target % = 5.0%`, `SLA Breach
   Days = 1`, and `ACR Breach Days = 0`.
2. Filter to a whole calendar month (and, if desired, to a single channel).
   Independently calculate:

   ```text
   SLA % = SUM(AnsweredWithinTarget) / SUM(OfferedContacts)
   ACR % = SUM(AbandonedContacts) / SUM(OfferedContacts)
   ```

   Compare those results to the KPI cards. They must match. Do not use an
   average of the daily `SLA %` or `ACR %` values.
3. Clear filters and check that the model contains 184 `Channel Performance`
   rows and 8 `SLA Recovery Actions` rows for the supplied sample. Confirm the
   Calendar-to-Channel-Performance relationship is active and single-direction.
   Keep Calendar-to-actions inactive and confirm there is no active
   Channel-Performance-to-actions key relationship for the latest-action
   measures in section 5.
4. As an edge-case check, add or temporarily filter to a row with
   `OfferedContacts = 0`. Verify that `SLA %` and `ACR %` are blank, and that
   both `SLA Breach Days` and `ACR Breach Days` are zero. Zero-offered rows are
   deliberately excluded from breach evaluation.

The resulting `Channel Performance`, `SLA Recovery Actions`, and `Calendar`
model fields and measures are ready for the report and for selecting data to
pass to the embedded Power App.

## 5. Build the Operations Overview report page

Create a report page named **Operations Overview**. Use `Calendar[Month
Label]`, `Channel Performance[Channel]`, and `Channel Performance[Supervisor]`
as slicers. Configure each slicer to filter the page and retain the current
filter context when navigating or refreshing the report.

Add KPI card visuals for these measures:

| KPI card | Field |
| --- | --- |
| SLA performance | `[SLA %]` |
| SLA target | `[SLA Target %]` |
| ACR performance | `[ACR %]` |
| ACR target | `[ACR Target %]` |
| Total breaches | `[Total Breach Days]` |

Use the one-decimal percentage formatting configured in the model. Keep the
breach card as a whole-number count.

### Comparison and trend visuals

1. Add a clustered-column chart with `Channel Performance[Channel]` on the
   X-axis and `[SLA %]` plus `[SLA Target %]` in **Values**.
2. Add a second clustered-column chart with `Channel Performance[Channel]` on
   the X-axis and `[ACR %]` plus `[ACR Target %]` in **Values**.
3. Add a line chart with `Calendar[Date]` on the X-axis and `[SLA %]` plus
   `[ACR %]` in **Values**. Set the X-axis to continuous when daily trend
   detail is desired.
4. Use green for performance within target. Use red or orange for breach
   variance, and include a clear legend or title explaining the target
   comparison. For SLA, below target is a breach; for ACR, above target is a
   breach.

### Exception table

#### Match actions by date **and** channel

Never use `PerformanceDate` alone to associate an action with an exception:
two channels can have performance records on the same date. Create a
`PerformanceChannelKey` in **both** queries before loading the model. Add this
Power Query step after the `PerformanceDate` and `Channel` type step (replace
`#"Previous Step"` with the actual preceding step name):

```powerquery
= Table.AddColumn(
    #"Previous Step",
    "PerformanceChannelKey",
    each Date.ToText([PerformanceDate], "yyyy-MM-dd")
        & "|"
        & Text.Upper(Text.Trim([Channel])),
    type text
)
```

Apply the same normalization in both tables. For example, a Voice record on
2026-05-05 has the key `2026-05-05|VOICE`. Confirm that `Channel Performance`
has one row per key before using it as the one side of a relationship.

The supported contract keeps multiple manual and automated actions per
performance key and displays the **latest action**. Latest means greatest
SharePoint `Created`; if two items have the same `Created` timestamp, greatest
SharePoint numeric `ID` wins. Both values come from SharePoint and were retained
in section 1. `ActionID` is not an ordering key.

Do not add raw action-table columns to the exception table and do not create an
active `Channel Performance`-to-`SLA Recovery Actions` relationship. Keep the
direct `Calendar[Date]`-to-actions relationship inactive for this page. The
key-filtered measures below need no relationship and leave one unambiguous
active report path: `Calendar -> Channel Performance`.

Create these two measures. They intentionally repeat the same `TOPN` selector
so status and alert state always come from the same action row:

```DAX
Related Action Status =
VAR SelectedKey =
    SELECTEDVALUE('Channel Performance'[PerformanceChannelKey])
VAR LatestAction =
    TOPN(
        1,
        FILTER(
            ALL('SLA Recovery Actions'),
            'SLA Recovery Actions'[PerformanceChannelKey] = SelectedKey
        ),
        'SLA Recovery Actions'[Created], DESC,
        'SLA Recovery Actions'[ID], DESC
    )
RETURN
    IF(
        ISBLANK(SelectedKey),
        BLANK(),
        MAXX(LatestAction, 'SLA Recovery Actions'[Status])
    )
```

```DAX
Related Action AlertSent =
VAR SelectedKey =
    SELECTEDVALUE('Channel Performance'[PerformanceChannelKey])
VAR LatestAction =
    TOPN(
        1,
        FILTER(
            ALL('SLA Recovery Actions'),
            'SLA Recovery Actions'[PerformanceChannelKey] = SelectedKey
        ),
        'SLA Recovery Actions'[Created], DESC,
        'SLA Recovery Actions'[ID], DESC
    )
RETURN
    IF(
        ISBLANK(SelectedKey),
        BLANK(),
        MAXX(
            LatestAction,
            IF(
                ISBLANK('SLA Recovery Actions'[AlertSent]),
                BLANK(),
                IF('SLA Recovery Actions'[AlertSent], "Yes", "No")
            )
        )
    )
```

`Related Action AlertSent` is display text (`Yes`, `No`, or blank). When no
action matches the selected key, both measures return blank. The normalized
date-plus-channel key prevents an action for one channel from appearing on
another channel's same-date exception.

Create this breach-only helper measure:

```DAX
Exception Row =
VAR Offered =
    SELECTEDVALUE('Channel Performance'[OfferedContacts])
RETURN
    IF(
        Offered > 0
            &&
        (
            [SLA %] < [SLA Target %]
                ||
            [ACR %] > [ACR Target %]
        ),
        1,
        0
    )
```

Add a table visual that includes these fields in this order:

1. `Channel Performance[PerformanceDate]`
2. `Channel Performance[Channel]`
3. `[SLA %]`
4. `[SLA Target %]`
5. `[ACR %]`
6. `[ACR Target %]`
7. `Channel Performance[Supervisor]`
8. `Channel Performance[ManagerEmail]`
9. `[Related Action Status]`
10. `[Related Action AlertSent]`

For the final two columns, use only these measures, not the raw `SLA Recovery
Actions[Status]` or `[AlertSent]` columns. Validate the
`PerformanceChannelKey`, `Created`, and `ID` selection for every displayed
action; do not allow an action from another channel on the same date to appear
as related.

In the table visual's **Filters on this visual**, add `[Exception Row]` and set
it to **is 1**. This is a required breach-only filter, not optional formatting.
Verify a within-target row and a zero-offered row are absent from the table.
Keep the independent app-side breach check in place even though normal users
select the app context from this filtered table.

Apply conditional formatting to the measure columns:

- Format `[SLA %]` red when it is less than `[SLA Target %]`.
- Format `[ACR %]` red when it is greater than `[ACR Target %]`.

Use a rule, field-value measure, or equivalent conditional-formatting approach
that compares each row's performance value with its target in the same filter
context. Test a known SLA breach and a known ACR breach after applying the
rules.

## 6. Power Apps visual contract

Insert a **Power Apps** visual on the Operations Overview page. In the visual's
data pane, add the following fields in this exact order:

1. `PerformanceDate`
2. `Channel`
3. `Supervisor`
4. `ManagerEmail`
5. `[SLA %]`
6. `[ACR %]`
7. `[SLA Target %]`
8. `[ACR Target %]`

The Power Apps visual supplies the filtered rows through
`PowerBIIntegration.Data`. The fields passed are `PerformanceDate`, `Channel`,
`Supervisor`, `ManagerEmail`, and the named measures. In Power Fx, reference
the measure fields with quoted names because they contain spaces and percent
signs. For example:

```powerfx
First(PowerBIIntegration.Data).'SLA %'
First(PowerBIIntegration.Data).'ACR %'
First(PowerBIIntegration.Data).'SLA Target %'
First(PowerBIIntegration.Data).'ACR Target %'
```

Do not rename, substitute, or reorder these visual fields without updating the
Power App; the app depends on this contract. Visibility reads
`CountRows(PowerBIIntegration.Data)` directly, and read-only controls use
`First(PowerBIIntegration.Data)` only while exactly one row is visible. The
Submit button first requires `CountRows(PowerBIIntegration.Data) = 1`, then captures
`First(PowerBIIntegration.Data)` before validation and Patch. Zero-row and
multi-row contexts hide the form, show exact-selection guidance, and cannot
write. When testing a selected exception, select exactly one date/channel row
so `PowerBIIntegration.Data` identifies the intended performance record.

## 7. QA and test-workspace publication procedure

Use the companion checklist,
[`power-bi-qa-checklist.md`](power-bi-qa-checklist.md), to validate the report
before and after publishing it to a **test workspace**. The checklist covers
slicer cross-filtering, exception selection supplied to Power Apps, and refresh
authentication using the intended SharePoint credentials. It is a procedure for
an authorized report owner; this guide does not publish a report itself.
