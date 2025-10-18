import re
from typing import List, Dict, Tuple


class PIIRedactor:
    def __init__(self):
        self.patterns = {
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'phone': r'\b(\+\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b',
            'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
            'credit_card': r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
            'ip_address': r'\b(?:\d{1,3}\.){3}\d{1,3}\b',
        }

    def detect_pii(self, text: str) -> List[Dict[str, str]]:
        findings = []
        for pii_type, pattern in self.patterns.items():
            matches = re.finditer(pattern, text)
            for match in matches:
                findings.append({
                    'type': pii_type,
                    'value': match.group(),
                    'start': match.start(),
                    'end': match.end()
                })
        return findings

    def redact(self, text: str, replacement: str = "[REDACTED]") -> Tuple[str, List[Dict]]:
        findings = []
        redacted_text = text

        for pii_type, pattern in self.patterns.items():
            matches = list(re.finditer(pattern, redacted_text))
            for match in reversed(matches):
                findings.append({
                    'type': pii_type,
                    'original_position': (match.start(), match.end())
                })
                redacted_text = (
                    redacted_text[:match.start()] +
                    f"{replacement}_{pii_type.upper()}" +
                    redacted_text[match.end():]
                )

        return redacted_text, findings


pii_redactor = PIIRedactor()
