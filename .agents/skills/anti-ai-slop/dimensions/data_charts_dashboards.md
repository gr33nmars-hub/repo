# Dimension Review: Data, Charts, and Dashboards

Use for charts, dashboards, analytics reports, BI mockups, KPI screenshots, metric cards, and data-heavy slide sections.

## Purpose

Data visuals should make a decision, pattern, risk, or tradeoff easier to see. They should not merely signal analytical sophistication.

## Common generic / AI-smell patterns

| Pattern | Visible sign | Risk |
|---|---|---|
| Decorative chart | Chart is present but no decision depends on it | Adds authority without information |
| Fake-looking sample data | Perfect curves, round numbers, repeated labels, impossible distribution | Reduces trust in the product or analysis |
| Metric-definition drift | Same KPI label means different things across cards, slides, or sections | Makes comparison invalid |
| Over-precise benchmark | “37.8% improvement” without source, method, denominator, or period | Creates false specificity |
| Missing axis or unit | Chart lacks unit, baseline, denominator, or time period | Prevents interpretation |
| Mismatched chart type | Pie for trends, line for categories, dual axes without explanation | Distorts the point |
| Dashboard wallpaper | Many widgets with no hierarchy, owner, or next action | Looks complete but is not usable |

## Review checklist

- What decision or monitoring job does the chart support?
- Are metric names, units, time periods, and denominators defined?
- Is the source, method, or mock-data status visible?
- Are axes, legends, labels, and comparisons readable?
- Does the visual show realistic data variation?
- Are empty, loading, error, stale-data, and permission states needed?
- Does the dashboard identify owner, refresh cadence, and next action when relevant?

## Repair patterns

| Weak pattern | Better direction |
|---|---|
| KPI card with “98% accuracy” | Define the task, dataset, period, denominator, and evaluation method. |
| Decorative line chart | Replace with the one trend that changes the recommendation. |
| Six equal widgets | Rank by decision priority and remove metrics nobody acts on. |
| Generic sample dashboard | Use realistic labels, plausible values, and state markers such as stale, loading, or unavailable. |
| Unsourced benchmark | Add source/date/scope or downgrade to a hypothesis. |

## Acceptance criteria

- Every metric has a definition, source or mock-data label, and time scope.
- Chart type matches the comparison or trend.
- Data does not imply unsupported precision.
- Dashboard hierarchy maps to user decisions.
- The viewer knows what to inspect or do next.
