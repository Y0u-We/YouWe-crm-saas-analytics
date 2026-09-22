# EDA Findings

- company_size_band missing in 5.6% of customers, acquisition_channel missing in 7.4% - both left as real NULLs per the Step 2 cleaning decision
- Median customer tenure: 12.7 months (mean 14.6, since the distribution is right-skewed by long-tenured active customers)
- Median ARPU: $72.87/month, mean $257.59/month - the gap between median and mean confirms a small number of high-value Enterprise accounts pull the average up
- 12-month retention across cohorts ranges 71%-84% (average 78%) - a steady drip rather than one bad cohort or a sharp cliff
- Average logins fall from 23.6/month (6 months out) to 6.9/month (final month) before a cancellation - a 71% decline, confirming usage decline is a genuine early-warning signal
- 701 invoices (1.5%) flagged as outliers (>5x or <0.2x expected plan price) - visible as the clear off-diagonal points in the chart
