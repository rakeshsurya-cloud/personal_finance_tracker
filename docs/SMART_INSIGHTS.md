# Smart Insights Overview

The Smart Insights tab brings together categorization, budgets, anomaly detection, cash-flow outlooks, goal planning, and a conversational assistant in one view. Key behaviors implemented in the current codebase:

## Automated Categorization
* Unlabeled transactions are passed through the trained classifier when a model file is available.
* User corrections can be fed back through `feedback_map` so suggested labels reflect the latest feedback.

## Personalized Budgeting & Tracking
* Suggested budgets are derived from historical averages and an adjustable savings rate.
* Live month-to-date tracking compares current spend to suggested limits and surfaces overspend risk.

## Anomaly & Overspend Detection
* Spending spikes use z-scores on recent expenses.
* Duplicate charges are flagged when the same merchant/amount repeats within seven days.
* Overspend pacing estimates month-end totals per category versus suggested limits.

## Cash-Flow Forecasting
* Uses recent daily net flows plus known recurring expenses to project 30/60/90-day balances.

## Goal-Based Savings Plans
* Computes monthly and "safe" contribution targets based on remaining time, amount, and projected cash flow.

## Predictive Nudges
* Suggests subscription reviews, duplicate checks, budget pacing alerts, and cash-flow safety suggestions.

## AI Insights Assistant
* Summarizes highlights, forecasts, budget status, anomalies, cash runway, and goal plans in natural language in response to user questions.
