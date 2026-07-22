"""Legibility rule implementations."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from sqlfluff.core.parser import BaseSegment
from sqlfluff.core.rules import BaseRule, LintResult, RuleContext
from sqlfluff.core.rules.crawlers import RootOnlyCrawler

UNMATCHED_MESSAGE = "Remove this comment or match the configured comment policy."
ADDITIONAL_MESSAGE = "Keep at most one regex-matched comment per top-level statement."
STACKED_MESSAGE = "Do not stack comments on consecutive lines."


@dataclass(frozen=True)
class Comment:
    """A physical source comment and its lint anchor."""

    segment: BaseSegment
    body: str
    start: int
    end: int


def _split_config(value: str | list[str] | None) -> tuple[str, ...]:
    if not value:
        return ()
    if isinstance(value, list):
        return tuple(item.strip() for item in value if item.strip())
    return tuple(item.strip() for item in value.split(",") if item.strip())


def _compile_patterns(values: tuple[str, ...]) -> tuple[re.Pattern[str], ...]:
    patterns = []
    for value in values:
        try:
            pattern = re.compile(value, re.IGNORECASE)
        except (re.error, OverflowError):
            continue
        patterns.append(pattern)
    return tuple(patterns)


def _strip_comment_markers(raw: str) -> str:
    value = raw.strip()
    markers = (("{#-", "-#}"), ("{#", "#}"), ("/*", "*/"))
    for opening, closing in markers:
        if value.startswith(opening) and value.endswith(closing):
            return value[len(opening) : -len(closing)].strip()
    if value.startswith("--"):
        return value[2:].strip()
    if value.startswith("#"):
        return value[1:].strip()
    return value


def _source_bounds(segment: BaseSegment) -> tuple[int, int] | None:
    if not segment.pos_marker:
        return None
    source_slice = segment.pos_marker.source_slice
    return source_slice.start, source_slice.stop


def _to_comment(segment: BaseSegment, raw: str) -> Comment | None:
    bounds = _source_bounds(segment)
    if not bounds:
        return None
    start, end = bounds
    body = _strip_comment_markers(raw)
    return Comment(segment=segment, body=body, start=start, end=end)


def _inline_comments(root: BaseSegment) -> tuple[Comment, ...]:
    comments = []
    for segment in root.raw_segments:
        if not segment.is_comment or segment.is_type("block_comment"):
            continue
        comment = _to_comment(segment, segment.raw)
        if comment:
            comments.append(comment)
    return tuple(comments)


def _block_comments(root: BaseSegment, source: str) -> tuple[Comment, ...]:
    comments = []
    anchor = None
    start = 0
    for segment in root.raw_segments:
        if not segment.is_type("block_comment"):
            continue
        bounds = _source_bounds(segment)
        if not bounds:
            continue
        if anchor is None:
            anchor = segment
            start = bounds[0]
        if not segment.raw.rstrip().endswith("*/"):
            continue
        raw = source[start : bounds[1]]
        comments.append(Comment(anchor, _strip_comment_markers(raw), start, bounds[1]))
        anchor = None
    return tuple(comments)


def _sql_comments(root: BaseSegment, source: str) -> tuple[Comment, ...]:
    return _inline_comments(root) + _block_comments(root, source)


def _template_comments(root: BaseSegment) -> tuple[Comment, ...]:
    comments = []
    for segment in root.recursive_crawl("placeholder"):
        if getattr(segment, "block_type", "") != "comment":
            continue
        source = getattr(segment, "source_str", "")
        comment = _to_comment(segment, source)
        if comment:
            comments.append(comment)
    return tuple(comments)


def _comments(root: BaseSegment, source: str) -> tuple[Comment, ...]:
    comments = _sql_comments(root, source) + _template_comments(root)
    return tuple(sorted(comments, key=lambda comment: comment.start))


def _matches(patterns: tuple[re.Pattern[str], ...], value: str) -> bool:
    return any(pattern.search(value) for pattern in patterns)


def _has_boundary(value: str, index: int) -> bool:
    if index < 0 or index >= len(value):
        return True
    character = value[index]
    return character != "_" and not character.isalnum()


def _matches_prefix(value: str, identifiers: tuple[str, ...]) -> bool:
    normalized = value.strip().casefold()
    for identifier in identifiers:
        prefix = identifier.casefold()
        has_prefix = normalized.startswith(prefix)
        has_boundary = _has_boundary(normalized, len(prefix))
        if has_prefix and has_boundary:
            return True
    return False


def _matches_suffix(value: str, identifiers: tuple[str, ...]) -> bool:
    normalized = value.strip().casefold()
    for identifier in identifiers:
        suffix = identifier.casefold()
        start = len(normalized) - len(suffix)
        has_suffix = normalized.endswith(suffix)
        has_boundary = _has_boundary(normalized, start - 1)
        if has_suffix and has_boundary:
            return True
    return False


def _comment_blocks(comments: tuple[Comment, ...], source: str) -> tuple[tuple[Comment, ...], ...]:
    blocks: list[tuple[Comment, ...]] = []
    for comment in comments:
        separator = ""
        if blocks:
            previous_end = blocks[-1][-1].end
            separator = source[previous_end : comment.start]
        has_only_spacing = not separator.strip()
        has_no_blank_line = separator.count("\n") <= 1
        is_contiguous = bool(blocks) and has_only_spacing and has_no_blank_line
        if is_contiguous:
            blocks[-1] += (comment,)
            continue
        blocks.append((comment,))
    return tuple(blocks)


def _matches_identifier(
    comment: Comment,
    prefixes: tuple[str, ...],
    suffixes: tuple[str, ...],
) -> bool:
    has_prefix = _matches_prefix(comment.body, prefixes)
    has_suffix = _matches_suffix(comment.body, suffixes)
    return has_prefix or has_suffix


def _stacked_comments(comments: tuple[Comment, ...], source: str) -> tuple[Comment, ...]:
    stacked = []
    for block in _comment_blocks(comments, source):
        stacked.extend(block[1:])
    return tuple(stacked)


def _is_builtin_directive(comment: Comment) -> bool:
    value = comment.body.casefold()
    raw = getattr(comment.segment, "raw", "").lstrip()
    is_noqa = bool(re.search(r"(?:^|\s)noqa(?:\s*:|\s*$)", value))
    is_config = value.startswith("sqlfluff:")
    is_dbt_dependency = value.startswith("depends_on:")
    is_executable = raw.startswith(("/*+", "/*!"))
    return is_noqa or is_config or is_dbt_dependency or is_executable


def _top_level_statements(root: BaseSegment) -> tuple[BaseSegment, ...]:
    statements = []
    pending = list(root.segments)
    while pending:
        segment = pending.pop(0)
        if segment.is_type("statement"):
            statements.append(segment)
            continue
        pending[0:0] = segment.segments
    return tuple(statements)


def _statement_spans(root: BaseSegment) -> tuple[tuple[int, int], ...]:
    spans = []
    for statement in _top_level_statements(root):
        bounds = _source_bounds(statement)
        if bounds:
            spans.append(bounds)
    return tuple(spans)


def _follows_previous_statement(
    comment: Comment,
    index: int,
    spans: tuple[tuple[int, int], ...],
    source: str,
) -> bool:
    if index == 0:
        return False
    previous_end = spans[index - 1][1]
    separator = source[previous_end : comment.start]
    return "\n" not in separator


def _statement_index(
    comment: Comment,
    spans: tuple[tuple[int, int], ...],
    source: str,
) -> int:
    for index, (start, end) in enumerate(spans):
        is_inside = start <= comment.start < end
        if is_inside:
            return index
        is_before = comment.start < start
        if not is_before:
            continue
        follows_previous = _follows_previous_statement(comment, index, spans, source)
        if follows_previous:
            return index - 1
        return index
    return max(len(spans) - 1, 0)


class Rule_Legibility_L001(BaseRule):
    """Comments must match the configured policy."""

    name = "legibility.no_unmatched_comments"
    groups = ("all", "legibility")
    config_keywords = [
        "comment_matchers",
        "comment_prefix_identifiers",
        "comment_suffix_identifiers",
        "directive_matchers",
    ]
    crawl_behaviour = RootOnlyCrawler()
    targets_templated = True
    is_fix_compatible = False

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        comment_matchers = _split_config(self.comment_matchers)
        directive_matchers = _split_config(self.directive_matchers)
        self._comment_patterns = _compile_patterns(comment_matchers)
        self._directive_patterns = _compile_patterns(directive_matchers)
        self._prefixes = _split_config(self.comment_prefix_identifiers)
        self._suffixes = _split_config(self.comment_suffix_identifiers)

    def _eval(self, context: RuleContext) -> list[LintResult]:
        source = context.segment.raw
        if context.templated_file:
            source = context.templated_file.source_str
        comments = _comments(context.segment, source)
        spans = _statement_spans(context.segment)
        counts: dict[int, int] = {}
        results = []
        for comment in comments:
            result = self._check_comment(comment, spans, counts, source)
            if result:
                results.append(result)
        return results

    def _check_comment(
        self,
        comment: Comment,
        spans: tuple[tuple[int, int], ...],
        counts: dict[int, int],
        source: str,
    ) -> LintResult | None:
        matches_directive = _matches(self._directive_patterns, comment.body)
        is_directive = _is_builtin_directive(comment) or matches_directive
        matches_identifier = _matches_identifier(comment, self._prefixes, self._suffixes)
        if is_directive or matches_identifier:
            return None
        if not _matches(self._comment_patterns, comment.body):
            return LintResult(anchor=comment.segment, description=UNMATCHED_MESSAGE)
        statement = _statement_index(comment, spans, source)
        counts[statement] = counts.get(statement, 0) + 1
        if counts[statement] == 1:
            return None
        return LintResult(anchor=comment.segment, description=ADDITIONAL_MESSAGE)


class Rule_Legibility_L002(BaseRule):
    """Comments must not be stacked on consecutive lines."""

    name = "legibility.no_stacked_comments"
    groups = ("all", "legibility")
    crawl_behaviour = RootOnlyCrawler()
    targets_templated = True
    is_fix_compatible = False

    def _eval(self, context: RuleContext) -> list[LintResult]:
        source = context.segment.raw
        if context.templated_file:
            source = context.templated_file.source_str
        comments = _comments(context.segment, source)
        stacked = _stacked_comments(comments, source)
        return [
            LintResult(anchor=comment.segment, description=STACKED_MESSAGE) for comment in stacked
        ]
