# Choosing Between Streaming Python Rules and Scheduled SQL Rules in Panther

When converting Splunk SPL queries to Panther detections, it's important to select the right implementation approach. This guide will help you determine whether to use a streaming Python rule or a scheduled SQL rule.

## Key Insight: Streaming Rules Can Handle Simple Aggregations

Many SOC analysts assume that any SPL query using `stats` must be converted to a scheduled SQL rule. However, **Panther streaming Python rules can efficiently handle simple threshold-based aggregations** through the combination of:

- The `dedup()` function to group related events
- The `Threshold` parameter to set minimum occurrence counts
- The `DedupPeriodMinutes` parameter to define a time window

This means that many SPL queries that appear to require scheduled SQL can actually be implemented as more efficient streaming rules.

## Example Conversion

### SPL with stats for grouping and counting:
```
index=windows sourcetype=wineventlog EventCode=4625
| stats count by host, user, src_ip
| where count > 5
```

### Equivalent Panther Streaming Rule:
```python
def rule(event):
    return event.get('EventCode') == 4625

def dedup(event):
    return f"{event.get('host')}-{event.get('user')}-{event.get('src_ip')}"
```

With rule.yml configuration:
```yaml
LogTypes:
  - Windows.EventLogs
DedupPeriodMinutes: 60
Threshold: 5
```

## When to Use Streaming Python Rules

1. **Simple Event Filtering**: Direct conditions on individual events
2. **Simple Threshold Detection**: Counting occurrences of similar events
3. **Real-Time Detection Need**: Threats requiring immediate detection
4. **Individual Event Processing**: When you need to analyze each event separately
5. **Custom Field Extraction**: Complex field transformation easier in Python
6. **Low to Medium Event Volume**: Manageable number of events per time period
7. **Custom Deduplication Logic**: Flexible grouping based on event attributes

## When to Use Scheduled SQL Rules

1. **Complex Aggregations**: Multiple aggregation levels or mathematical operations
2. **Advanced Statistical Functions**: Beyond simple counting (stddev, percentiles)
3. **Window Functions**: Moving averages, cumulative sums, etc.
4. **Cross-Data Source Joins**: Correlations across different log types
5. **Time-Based Bucketing**: Specific time-window grouping not aligned with dedup periods
6. **Very High Volume Processing**: Billions of events where database optimization helps
7. **Historical Pattern Analysis**: Detecting anomalies against historical baselines

## Decision Framework

Ask yourself these questions:
1. Is the SPL just using `stats` for simple grouping and counting? → Consider streaming rule
2. Can the detection criteria be evaluated on individual events? → Consider streaming rule
3. Is the detection looking for complex patterns across time or data sources? → Use scheduled SQL
4. Does the rule need to process extremely high volumes of data? → Use scheduled SQL

## Performance Considerations

Streaming rules generally offer:
- Lower latency (near real-time detection)
- Less computational overhead
- Simpler maintenance

Scheduled SQL rules offer:
- More powerful analytical capabilities
- Better handling of very large datasets
- Ability to query across multiple data sources

## Best Practice

Start by considering a streaming rule implementation, and only move to scheduled SQL if you need functionality that can't be accomplished through deduplication and thresholding.
