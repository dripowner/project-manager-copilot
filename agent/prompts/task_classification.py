"""Prompt for task classification (simple vs plan_execute)."""

TASK_CLASSIFICATION_PROMPT = """Classify this PM request into one of two execution modes:

1. "simple" - Straightforward single-step tasks:
   - List issues: "покажи все задачи", "список issues"
   - Create single issue: "создай issue с описанием X"
   - Search docs: "найди документацию", "search in Confluence"
   - Schedule meeting: "создай встречу на завтра"
   - Link meeting to issue: "свяжи встречу с задачей"
   - Single query operations

2. "plan_execute" - Multi-step complex workflows:
   - Sprint planning: "подготовь план спринта", "проанализируй backlog"
   - Status reports: "сгенерируй отчет по проекту", "статус всех задач"
   - Complex analysis: "какие задачи блокируются", "анализ рисков"
   - Multi-step operations: "создай задачи на основе документа"
   - Retrospective reviews: "проанализируй спринт"

Request: {request}

Guidelines:
- If request requires gathering data from multiple sources → plan_execute
- If request requires multiple sequential operations → plan_execute
- If request is a single straightforward operation → simple

Return ONLY ONE WORD: "simple" OR "plan_execute"
"""
