import json
import google.generativeai as genai
from core.config import get_settings

settings = get_settings()
genai.configure(api_key=settings.gemini_api_key)


class LLMService:
    def __init__(self):
        self.model = genai.GenerativeModel("gemini-2.5-flash")

    def _call(self, prompt: str) -> str:
        response = self.model.generate_content(prompt)
        text = response.text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return text.strip()

    def diagnose(self, df_sample: dict, stats: dict, anomalies: list,
                 schema_issues: list, pii_fields: list,
                 past_fixes: list, ml_results: dict) -> dict:

        past_ctx = f"\nPAST SIMILAR FIXES (RAG memory):\n{json.dumps(past_fixes[:3], indent=2)}" if past_fixes else ""
        ml_ctx   = f"\nML DETECTION RESULTS (Isolation Forest):\n{json.dumps(ml_results, indent=2)}" if ml_results else ""

        prompt = f"""You are a senior data scientist and AI explainability expert.
Analyze this dataset and produce a detailed, actionable report.

DATASET: rows={stats['total_rows']}, cols={stats['total_columns']}
SAMPLE DATA: {json.dumps(df_sample, indent=2)}
STATISTICAL ANOMALIES: {json.dumps(anomalies, indent=2)}
SCHEMA ISSUES: {json.dumps(schema_issues, indent=2)}
PII FIELDS: {json.dumps(pii_fields, indent=2)}
{ml_ctx}
{past_ctx}

Respond ONLY with valid JSON (no markdown, no extra text):
{{
  "summary": "2-3 sentence plain English summary of data quality situation",
  "severity": "low|medium|high|critical",
  "overall_data_health_score": 0-100,
  "issues": [
    {{
      "title": "Short title",
      "description": "Plain English explanation of why this is a problem",
      "column": "column name or multiple",
      "type": "anomaly|schema_drift|pii|duplicate|ml_anomaly",
      "impact": "Downstream business impact if not fixed"
    }}
  ],
  "recommended_fixes": [
    {{
      "issue": "Which issue this fixes",
      "action": "Plain English action",
      "python_code": "df.dropna() — runnable pandas code",
      "confidence": 0.0,
      "auto_applicable": true
    }}
  ],
  "explainability": [
    {{
      "anomaly_type": "Type of anomaly",
      "root_cause": "Why this likely happened in the data pipeline",
      "business_impact": "What breaks downstream if not fixed",
      "severity": "low|medium|high|critical",
      "suggested_resolution": "Step-by-step fix instructions",
      "confidence_score": 0.0
    }}
  ],
  "pii_risk_summary": "Plain English PII risk assessment"
}}"""
        try:
            return json.loads(self._call(prompt))
        except Exception as e:
            return {
                "summary": f"AI analysis error: {e}",
                "severity": "unknown",
                "overall_data_health_score": 0,
                "issues": [], "recommended_fixes": [],
                "explainability": [], "pii_risk_summary": ""
            }

    def explain_schema_drift(self, current: dict, previous: dict, drift: list) -> str:
        prompt = f"""Explain this schema drift in 2-3 plain English sentences.
Previous: {json.dumps(previous)}
Current: {json.dumps(current)}
Changes: {json.dumps(drift)}
No markdown."""
        try:
            return self.model.generate_content(prompt).text.strip()
        except Exception as e:
            return f"Could not generate explanation: {e}"
