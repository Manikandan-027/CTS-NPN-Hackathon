from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from typing import Iterable

from .models import CodeFinding, RepositoryEvidence, SourceFile
from .sources import LocalRepositorySource


# ============================================================
# WORDS THAT GENERALLY DO NOT HELP LOCATE CODE
# ============================================================

STOP_WORDS = {
    "the",
    "and",
    "for",
    "with",
    "from",
    "this",
    "that",
    "was",
    "were",
    "are",
    "is",
    "has",
    "have",
    "had",
    "into",
    "after",
    "before",
    "during",
    "when",
    "while",
    "error",
    "errors",
    "failed",
    "failure",
    "issue",
    "incident",
    "production",
    "service",
    "request",
    "requests",
    "returned",
    "returns",
    "response",
    "user",
    "users",
    "customer",
    "customers",
    "new",
    "immediately",
    "occurred",
    "occur",
    "occurs",
}


# ============================================================
# TOKENIZER
# ============================================================

TOKEN_RE = re.compile(
    r"[A-Za-z_][A-Za-z0-9_./:-]*|\b\d{3,}\b"
)


# ============================================================
# HTTP ERROR SEMANTICS
# ============================================================

HTTP_SEMANTICS: dict[str, list[str]] = {

    "400": [
        "bad",
        "request",
        "validation",
        "validate",
        "invalid",
        "payload",
        "missing",
        "required",
        "schema",
        "malformed",
        "parameter",
        "parameters",
        "body",
        "input",
    ],

    "401": [
        "authentication",
        "authenticate",
        "authorization",
        "authorize",
        "token",
        "jwt",
        "credential",
        "credentials",
        "login",
        "unauthorized",
        "access",
        "api_key",
        "apikey",
        "secret",
    ],

    "402": [
        "payment",
        "payment_required",
        "billing",
        "balance",
        "funds",
        "amount",
        "transaction",
        "card",
        "charge",
        "currency",
    ],

    "403": [
        "forbidden",
        "permission",
        "permissions",
        "access",
        "authorization",
        "role",
        "roles",
        "privilege",
        "admin",
    ],

    "404": [
        "not_found",
        "notfound",
        "missing",
        "resource",
        "endpoint",
        "route",
        "path",
    ],

    "408": [
        "timeout",
        "timed_out",
        "deadline",
        "request_timeout",
    ],

    "409": [
        "conflict",
        "duplicate",
        "already_exists",
        "exists",
        "concurrent",
        "transaction",
    ],

    "429": [
        "rate",
        "limit",
        "limiter",
        "throttle",
        "throttling",
        "too_many_requests",
        "quota",
    ],

    "500": [
        "exception",
        "traceback",
        "crash",
        "internal",
        "server",
        "runtime",
        "database",
        "db",
        "connection",
        "null",
        "none",
    ],

    "502": [
        "bad_gateway",
        "gateway",
        "upstream",
        "proxy",
        "connection",
        "service",
    ],

    "503": [
        "unavailable",
        "availability",
        "health",
        "upstream",
        "service",
        "dependency",
        "database",
        "connection",
        "timeout",
    ],

    "504": [
        "gateway",
        "timeout",
        "upstream",
        "deadline",
        "service",
        "dependency",
        "response_timeout",
    ],
}


# ============================================================
# DOMAIN TERMS
# ============================================================

DOMAIN_TERMS = {
    "payment": [
        "payment",
        "payments",
        "pay",
        "transaction",
        "transactions",
        "charge",
        "charges",
        "billing",
        "invoice",
        "amount",
        "currency",
        "card",
        "checkout",
        "gateway",
        "merchant",
        "refund",
    ],

    "authentication": [
        "authentication",
        "authenticate",
        "authorization",
        "authorize",
        "token",
        "jwt",
        "credential",
        "credentials",
        "api_key",
        "apikey",
        "login",
    ],

    "validation": [
        "validation",
        "validate",
        "validator",
        "invalid",
        "required",
        "missing",
        "schema",
        "payload",
        "malformed",
    ],

    "database": [
        "database",
        "db",
        "postgres",
        "postgresql",
        "mysql",
        "sqlite",
        "query",
        "connection",
        "cursor",
        "transaction",
    ],

    "network": [
        "timeout",
        "upstream",
        "gateway",
        "http",
        "request",
        "response",
        "connection",
        "socket",
        "network",
    ],

    "rate_limit": [
        "rate",
        "limit",
        "limiter",
        "throttle",
        "quota",
    ],
}


# ============================================================
# CANDIDATE
# ============================================================

@dataclass(frozen=True)
class _Candidate:
    source: SourceFile
    score: float
    terms: tuple[str, ...]


# ============================================================
# INVESTIGATOR
# ============================================================

class RepositoryInvestigator:
    """
    Scan a local repository and identify source-code locations
    relevant to a production incident.

    The investigator is intentionally deterministic.

    It does NOT invent a line number.

    The line number is calculated directly from the source file
    using enumerate(..., start=1).
    """

    def __init__(
        self,
        source: LocalRepositorySource,
    ) -> None:

        self.source = source

        # Read complete repository once.
        self.files = source.files()


    # ========================================================
    # TOKENIZATION
    # ========================================================

    @staticmethod
    def _tokens(
        text: str,
    ) -> list[str]:

        return [
            token.lower()
            for token in TOKEN_RE.findall(text)
        ]


    # ========================================================
    # EXTRACT HTTP STATUS CODES
    # ========================================================

    @staticmethod
    def _status_codes(
        text: str,
    ) -> list[str]:

        codes = re.findall(
            r"\b(?:400|401|402|403|404|408|409|429|500|502|503|504)\b",
            text,
        )

        return list(
            dict.fromkeys(codes)
        )


    # ========================================================
    # ERROR SIGNALS
    # ========================================================

    @staticmethod
    def _error_signals(
        error: str,
        stack_trace: str | None,
    ) -> list[str]:

        text = (
            f"{error}\n"
            f"{stack_trace or ''}"
        ).lower()

        signals: list[str] = []

        # ----------------------------------------------------
        # Normal tokens from incident
        # ----------------------------------------------------

        for token in RepositoryInvestigator._tokens(
            text
        ):

            if token in STOP_WORDS:
                continue

            if len(token) < 2:
                continue

            if token not in signals:
                signals.append(token)


        # ----------------------------------------------------
        # HTTP codes
        # ----------------------------------------------------

        status_codes = (
            RepositoryInvestigator._status_codes(
                text
            )
        )

        for code in status_codes:

            if code not in signals:
                signals.append(code)


        # ----------------------------------------------------
        # HTTP semantic terms
        # ----------------------------------------------------

        for code in status_codes:

            for term in HTTP_SEMANTICS.get(
                code,
                [],
            ):

                if term not in signals:
                    signals.append(term)


        # ----------------------------------------------------
        # Domain-specific terms
        # ----------------------------------------------------

        for terms in DOMAIN_TERMS.values():

            for term in terms:

                if term in text:

                    if term not in signals:
                        signals.append(term)


        return signals


    # ========================================================
    # NORMALIZE SEARCH TERMS
    # ========================================================

    @staticmethod
    def _term_variants(
        term: str,
    ) -> list[str]:

        variants = {
            term,
        }

        variants.add(
            term.replace(
                "_",
                " ",
            )
        )

        variants.add(
            term.replace(
                "-",
                " ",
            )
        )

        return list(
            variants
        )


    # ========================================================
    # SCORE FILE
    # ========================================================

    @staticmethod
    def _score_file(
        source: SourceFile,
        signals: Iterable[str],
    ) -> _Candidate:

        content_lower = (
            source.content.lower()
        )

        path_lower = (
            source.path.lower()
        )

        counts = Counter()

        score = 0.0

        signals = list(
            dict.fromkeys(signals)
        )


        # ----------------------------------------------------
        # Signal occurrences
        # ----------------------------------------------------

        for signal in signals:

            occurrences = 0

            for variant in (
                RepositoryInvestigator
                ._term_variants(signal)
            ):

                occurrences += (
                    content_lower.count(
                        variant
                    )
                )

            if occurrences <= 0:
                continue

            counts[signal] += occurrences

            # Cap repeated matches so huge files don't
            # automatically dominate.
            score += min(
                occurrences,
                8,
            ) * 1.5


            # Filename/path relevance
            if (
                signal in path_lower
                or signal.replace(
                    "_",
                    "",
                ) in path_lower.replace(
                    "_",
                    "",
                )
            ):

                score += 5.0


        # ----------------------------------------------------
        # HTTP status + code response patterns
        # ----------------------------------------------------

        status_codes = [
            code
            for code in signals
            if code.isdigit()
            and len(code) == 3
        ]

        for code in status_codes:

            response_patterns = [

                rf"\b{re.escape(code)}\b",

                rf"status_code\s*=\s*{re.escape(code)}",

                rf"status_code\s*[:=]\s*{re.escape(code)}",

                rf"status\s*[:=]\s*{re.escape(code)}",

                rf"HTTPException\s*\([^)]*{re.escape(code)}",

                rf"return\s+[^,\n]+,\s*{re.escape(code)}",

                rf"return\s+[^,\n]+,\s*HTTPStatus\.[A-Z_]+",

            ]

            for pattern in response_patterns:

                if re.search(
                    pattern,
                    source.content,
                    flags=re.IGNORECASE,
                ):

                    score += 10.0

                    counts[
                        f"http-{code}-implementation"
                    ] += 1


        # ----------------------------------------------------
        # Payment-specific source files
        # ----------------------------------------------------

        payment_signals = {
            "payment",
            "payments",
            "transaction",
            "transactions",
            "charge",
            "billing",
            "checkout",
            "card",
        }

        if (
            payment_signals
            & set(signals)
        ):

            if any(
                term in path_lower
                for term in (
                    "payment",
                    "transaction",
                    "checkout",
                    "billing",
                    "charge",
                )
            ):

                score += 15.0

                counts[
                    "payment-source-file"
                ] += 1


        # ----------------------------------------------------
        # Validation source files
        # ----------------------------------------------------

        validation_terms = {
            "validation",
            "validate",
            "validator",
            "invalid",
            "required",
            "payload",
            "schema",
        }

        if (
            validation_terms
            & set(signals)
        ):

            if any(
                term in path_lower
                for term in (
                    "validation",
                    "validator",
                    "schema",
                    "request",
                    "payment",
                )
            ):

                score += 8.0

                counts[
                    "validation-source-file"
                ] += 1


        # ----------------------------------------------------
        # Authentication source files
        # ----------------------------------------------------

        auth_terms = {
            "authentication",
            "authorization",
            "token",
            "jwt",
            "credential",
            "credentials",
            "apikey",
            "api_key",
        }

        if (
            auth_terms
            & set(signals)
        ):

            if any(
                term in path_lower
                for term in (
                    "auth",
                    "security",
                    "token",
                    "jwt",
                    "credential",
                )
            ):

                score += 12.0

                counts[
                    "authentication-source-file"
                ] += 1


        # ----------------------------------------------------
        # Database source files
        # ----------------------------------------------------

        database_terms = {
            "database",
            "db",
            "postgres",
            "postgresql",
            "mysql",
            "sqlite",
            "query",
            "connection",
        }

        if (
            database_terms
            & set(signals)
        ):

            if any(
                term in path_lower
                for term in (
                    "database",
                    "db",
                    "repository",
                    "storage",
                    "model",
                )
            ):

                score += 10.0

                counts[
                    "database-source-file"
                ] += 1


        # ----------------------------------------------------
        # Rate limiter support
        # ----------------------------------------------------

        rate_terms = {
            "429",
            "rate",
            "limit",
            "limiter",
            "throttle",
            "quota",
        }

        if (
            rate_terms
            & set(signals)
        ):

            if re.search(
                r"(?i)"
                r"rate.?limit|"
                r"rate.?limiter|"
                r"throttl|"
                r"quota|"
                r"requests?.{0,30}"
                r"(per|window)",
                source.content,
            ):

                score += 15.0

                counts[
                    "rate-limiter-config"
                ] += 1


        return _Candidate(
            source=source,
            score=score,
            terms=tuple(
                counts.keys()
            ),
        )


    # ========================================================
    # EXTRACT LINE FINDINGS
    # ========================================================

    @staticmethod
    def _extract_findings(
        source: SourceFile,
        signals: list[str],
        file_score: float,
    ) -> list[CodeFinding]:

        lines = (
            source.content.splitlines()
        )

        findings: list[CodeFinding] = []


        # ----------------------------------------------------
        # Status codes
        # ----------------------------------------------------

        status_codes = [
            signal
            for signal in signals
            if signal.isdigit()
            and len(signal) == 3
        ]


        # ----------------------------------------------------
        # Patterns that indicate actual error generation
        # ----------------------------------------------------

        error_patterns: list[
            tuple[str, re.Pattern[str]]
        ] = []


        for code in status_codes:

            error_patterns.extend(
                [

                    (
                        f"http-{code}",
                        re.compile(
                            rf"\b{re.escape(code)}\b",
                            re.IGNORECASE,
                        ),
                    ),

                    (
                        f"status-code-{code}",
                        re.compile(
                            rf"status_code\s*[:=]\s*{re.escape(code)}",
                            re.IGNORECASE,
                        ),
                    ),

                    (
                        f"http-exception-{code}",
                        re.compile(
                            rf"HTTPException\s*\([^)]*{re.escape(code)}",
                            re.IGNORECASE,
                        ),
                    ),

                    (
                        f"return-status-{code}",
                        re.compile(
                            rf"return\s+[^,\n]+,\s*{re.escape(code)}",
                            re.IGNORECASE,
                        ),
                    ),
                ]
            )


        # ----------------------------------------------------
        # Domain patterns
        # ----------------------------------------------------

        semantic_patterns = [

            (
                "payment",
                re.compile(
                    r"(?i)\b"
                    r"payment|payments|"
                    r"transaction|transactions|"
                    r"charge|billing|checkout|"
                    r"card|merchant"
                    r"\b"
                ),
            ),

            (
                "validation",
                re.compile(
                    r"(?i)"
                    r"validation|validate|validator|"
                    r"invalid|required|missing|"
                    r"payload|schema|malformed"
                ),
            ),

            (
                "authentication",
                re.compile(
                    r"(?i)"
                    r"authentication|authenticate|"
                    r"authorization|authorize|"
                    r"token|jwt|credential|"
                    r"api[_ -]?key|unauthorized"
                ),
            ),

            (
                "database",
                re.compile(
                    r"(?i)"
                    r"database|postgres|postgresql|"
                    r"mysql|sqlite|query|"
                    r"connection|cursor"
                ),
            ),

            (
                "timeout",
                re.compile(
                    r"(?i)"
                    r"timeout|timed[_ -]?out|"
                    r"deadline|upstream"
                ),
            ),

            (
                "rate-limit",
                re.compile(
                    r"(?i)"
                    r"rate.?limit|rate.?limiter|"
                    r"throttl|quota"
                ),
            ),

        ]


        # ----------------------------------------------------
        # Process each source line
        # ----------------------------------------------------

        for index, line in enumerate(
            lines,
            start=1,
        ):

            line_lower = (
                line.lower()
            )

            matched: list[str] = []

            evidence: list[str] = []

            line_score = 0.0


            # ------------------------------------------------
            # Direct signal matches
            # ------------------------------------------------

            for signal in signals:

                variants = (
                    RepositoryInvestigator
                    ._term_variants(
                        signal
                    )
                )

                if any(
                    variant.lower()
                    in line_lower
                    for variant in variants
                ):

                    matched.append(
                        signal
                    )

                    line_score += 2.0


            # ------------------------------------------------
            # HTTP status implementation
            # ------------------------------------------------

            for label, pattern in error_patterns:

                if pattern.search(line):

                    matched.append(
                        label
                    )

                    line_score += 8.0

                    evidence.append(
                        f"Matched {label}: "
                        f"{line.strip()}"
                    )


            # ------------------------------------------------
            # Semantic patterns
            # ------------------------------------------------

            for label, pattern in semantic_patterns:

                if not pattern.search(line):
                    continue

                # Only count semantic terms strongly when
                # they are relevant to the incident.
                if (
                    label in signals
                    or label in {
                        "payment",
                        "validation",
                        "authentication",
                        "database",
                        "timeout",
                        "rate-limit",
                    }
                ):

                    matched.append(
                        label
                    )

                    line_score += 3.0

                    evidence.append(
                        f"Matched {label}: "
                        f"{line.strip()}"
                    )


            # ------------------------------------------------
            # Strong combinations
            # ------------------------------------------------

            has_status = any(
                code in line_lower
                for code in status_codes
            )

            has_payment = bool(
                re.search(
                    r"(?i)"
                    r"payment|transaction|"
                    r"charge|billing|checkout",
                    line,
                )
            )

            has_validation = bool(
                re.search(
                    r"(?i)"
                    r"validation|validate|"
                    r"invalid|required|"
                    r"payload|schema",
                    line,
                )
            )

            has_auth = bool(
                re.search(
                    r"(?i)"
                    r"authentication|authorization|"
                    r"token|jwt|credential|"
                    r"api[_ -]?key|unauthorized",
                    line,
                )
            )

            has_database = bool(
                re.search(
                    r"(?i)"
                    r"database|postgres|postgresql|"
                    r"mysql|sqlite|query|connection",
                    line,
                )
            )


            # ------------------------------------------------
            # Make error-producing lines stronger
            # ------------------------------------------------

            if has_status:

                line_score += 12.0

                evidence.append(
                    "HTTP status code appears "
                    "directly on this line."
                )


            if has_status and has_payment:

                line_score += 12.0

                evidence.append(
                    "Payment-related code and "
                    "HTTP status occur together."
                )


            if has_status and has_validation:

                line_score += 12.0

                evidence.append(
                    "Validation-related code and "
                    "HTTP status occur together."
                )


            if has_status and has_auth:

                line_score += 12.0

                evidence.append(
                    "Authentication-related code and "
                    "HTTP status occur together."
                )


            if has_status and has_database:

                line_score += 10.0

                evidence.append(
                    "Database-related code and "
                    "HTTP status occur together."
                )


            # ------------------------------------------------
            # Do not create weak findings
            # ------------------------------------------------

            if not matched:
                continue


            # A plain word like "payment" should not by itself
            # become the final exact location.
            #
            # Require either:
            #
            # 1. strong line score
            # 2. HTTP status
            # 3. multiple relevant signals
            #

            if (
                line_score < 5.0
                and not has_status
                and len(set(matched)) < 2
            ):

                continue


            # ------------------------------------------------
            # Context around exact line
            # ------------------------------------------------

            start = max(
                1,
                index - 3,
            )

            end = min(
                len(lines),
                index + 3,
            )

            context = "\n".join(
                f"{line_no}: "
                f"{lines[line_no - 1]}"
                for line_no in range(
                    start,
                    end + 1,
                )
            )


            # ------------------------------------------------
            # Final score
            # ------------------------------------------------

            final_score = (
                file_score
                + line_score
                + min(
                    len(set(matched)),
                    10,
                )
            )


            findings.append(
                CodeFinding(
                    file_path=source.path,
                    line_start=index,
                    line_end=index,
                    score=round(
                        final_score,
                        3,
                    ),
                    matched_terms=sorted(
                        set(matched)
                    ),
                    evidence=list(
                        dict.fromkeys(
                            evidence
                        )
                    ),
                    context=context,
                )
            )


        return findings


    # ========================================================
    # MAIN INVESTIGATION
    # ========================================================

    def investigate(
        self,
        error: str,
        stack_trace: str | None = None,
        max_files: int = 5,
        max_findings: int = 12,
    ) -> RepositoryEvidence:

        if not error or not error.strip():

            raise ValueError(
                "error cannot be empty"
            )

        if (
            max_files <= 0
            or max_findings <= 0
        ):

            raise ValueError(
                "max_files and max_findings "
                "must be greater than zero"
            )


        # ----------------------------------------------------
        # Build incident signals
        # ----------------------------------------------------

        signals = (
            self._error_signals(
                error,
                stack_trace,
            )
        )


        # ----------------------------------------------------
        # Score every source file
        # ----------------------------------------------------

        candidates = [

            self._score_file(
                source,
                signals,
            )

            for source in self.files

        ]


        # ----------------------------------------------------
        # Select relevant files
        # ----------------------------------------------------

        relevant = sorted(

            (
                candidate
                for candidate in candidates
                if candidate.score > 0
            ),

            key=lambda item: (
                -item.score,
                item.source.path,
            ),
        )


        selected = relevant[
            :max_files
        ]


        # ----------------------------------------------------
        # Find exact source lines
        # ----------------------------------------------------

        findings: list[
            CodeFinding
        ] = []


        for candidate in selected:

            findings.extend(

                self._extract_findings(
                    candidate.source,
                    signals,
                    candidate.score,
                )

            )


        # ----------------------------------------------------
        # Highest-confidence findings first
        # ----------------------------------------------------

        findings.sort(

            key=lambda item: (
                -item.score,
                item.file_path,
                item.line_start,
            )

        )


        findings = findings[
            :max_findings
        ]


        # ----------------------------------------------------
        # Summary
        # ----------------------------------------------------

        if findings:

            summary = (

                f"Scanned "
                f"{len(self.files)} source files. "

                f"Found "
                f"{len(findings)} relevant code findings "

                f"across "
                f"{len({item.file_path for item in findings})} files."

            )

        else:

            summary = (

                f"Scanned "
                f"{len(self.files)} source files "

                "but found no code evidence "
                "matching the supplied incident signals."

            )


        # ----------------------------------------------------
        # Return structured evidence
        # ----------------------------------------------------

        return RepositoryEvidence(

            source_type=(
                self.source.source_type
            ),

            repository=(
                self.source.describe()
            ),

            scanned_files=(
                len(self.files)
            ),

            skipped_files=0,

            total_lines=sum(
                source.line_count
                for source in self.files
            ),

            relevant_files=list(
                dict.fromkeys(
                    item.file_path
                    for item in findings
                )
            ),

            findings=findings,

            investigation_summary=summary,

        )