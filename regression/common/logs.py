"""Execution completion and simulation diagnostics are separate results."""
import re


def audit(text):
    fatal = re.compile(r"\b(?:ERROR|FATAL)\s*\(|convergence failure|segmentation fault", re.I)
    errors = [line for line in text.splitlines() if fatal.search(line)]
    warnings = [line for line in text.splitlines() if re.search(r"\bWARNING\s*\(", line, re.I)]
    complete = bool(re.search(r"spectre completes with 0 errors", text, re.I))
    return {"pass": complete and not errors, "clean_completion": complete,
            "errors": errors, "warnings": warnings}
