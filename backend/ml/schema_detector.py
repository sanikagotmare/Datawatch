import pandas as pd
import json
from typing import Optional, List, Dict, Any


PII_PATTERNS = {
    "email":       r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+",
    "phone":       r"(\+?\d{1,3}[\s-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}",
    "aadhaar":     r"\d{4}\s?\d{4}\s?\d{4}",
    "pan":         r"[A-Z]{5}[0-9]{4}[A-Z]{1}",
    "credit_card": r"\b(?:\d[ -]?){13,16}\b",
}
PII_COLUMN_HINTS = [
    "email","phone","mobile","ssn","aadhaar","pan","passport",
    "dob","birth","address","zip","pincode","credit","card",
    "account","password","secret","token","cvv","ip","national_id"
]


class SchemaDetector:

    def get_schema(self, df: pd.DataFrame) -> Dict[str, str]:
        return {col: str(dtype) for col, dtype in df.dtypes.items()}

    def detect_drift(self, df: pd.DataFrame, previous_schema: Optional[Dict]) -> List[Dict]:
        if not previous_schema:
            return []
        current = self.get_schema(df)
        issues  = []
        for col in previous_schema:
            if col not in current:
                issues.append({"type":"column_removed","column":col,"severity":"high",
                    "detail":f"Column '{col}' was present before but is missing now",
                    "previous_type":previous_schema[col],"current_type":None})
        for col in current:
            if col not in previous_schema:
                issues.append({"type":"column_added","column":col,"severity":"medium",
                    "detail":f"New column '{col}' appeared",
                    "previous_type":None,"current_type":current[col]})
        for col in previous_schema:
            if col in current and previous_schema[col] != current[col]:
                issues.append({"type":"type_changed","column":col,"severity":"high",
                    "detail":f"Type changed: {previous_schema[col]} → {current[col]}",
                    "previous_type":previous_schema[col],"current_type":current[col]})
        return issues

    def detect_pii(self, df: pd.DataFrame) -> List[Dict]:
        found = []
        for col in df.columns:
            col_lower = col.lower()
            for hint in PII_COLUMN_HINTS:
                if hint in col_lower:
                    found.append({"column":col,"pii_type":hint,"detection_method":"column_name","risk":"high"})
                    break
            if pd.api.types.is_object_dtype(df[col]):
                sample = df[col].dropna().head(20).astype(str)
                for pii_type, pattern in PII_PATTERNS.items():
                    if sample.str.contains(pattern, regex=True, na=False).sum() > 2:
                        if not any(p["column"] == col for p in found):
                            found.append({"column":col,"pii_type":pii_type,"detection_method":"pattern_match","risk":"high"})
        return found
