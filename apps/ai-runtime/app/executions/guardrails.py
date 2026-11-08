"""Layered, heuristic text checks; capability checks remain authoritative."""
import re
from app.rag.context import assemble_context


class GuardrailViolation(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


_INJECTION = re.compile(r'ignore\s+(?:all\s+|the\s+)?(?:previous|prior|system)\s+instructions|ignora?r?\s+(?:as\s+)?instru[çc][õo]es|(?:reveal|exfiltrate|print)\s+(?:all\s+)?(?:secrets|credentials|system prompt)|(?:system|developer)\s*:\s*(?:override|ignore)|bypass\s+(?:approval|permissions)', re.I)
_SECRET_KEY = re.compile(r'^(?:password|passwd|secret|token|access_token|refresh_token|api[_-]?key|authorization|cpf|email)$', re.I)


def redact(value):
    if isinstance(value, dict):
        return {k: '[REDACTED]' if _SECRET_KEY.match(str(k)) else redact(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [redact(v) for v in value]
    if not isinstance(value, str):
        return value
    value = re.sub(r'\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b', '[REDACTED]', value)
    value = re.sub(r'\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b', '[REDACTED]', value)
    value = re.sub(r'(?i)\b(?:api[_-]?key|password|passwd|token|secret|authorization)\s*[=:]\s*["\']?[^\s,"\'}]+', '[REDACTED]', value)
    value = re.sub(r'(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+|\bsk-[A-Za-z0-9_-]{8,}', '[REDACTED]', value)
    return value


def check_request(text):
    if _INJECTION.search(text):
        raise GuardrailViolation('instruction_override')


def filter_evidence(result):
    hits = [redact(h) for h in result.get('results', []) if not _INJECTION.search(str(h))]
    return {**redact(result), 'results': hits, 'context': assemble_context(hits)}
