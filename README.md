# sqlfluff-plugin-legibility

![CI](/yowainwright/sqlfluff-plugin-legibility/actions/workflows/ci.yml/badge.svg)
![Codecov](https://codecov.io/gh/yowainwright/sqlfluff-plugin-legibility/graph/badge.svg)
![PyPI](https://img.shields.io/pypi/v/sqlfluff-plugin-legibility)
![Python](https://img.shields.io/pypi/pyversions/sqlfluff-plugin-legibility)

A small SQLFluff plugin for keeping comments scarce and intentional.

Ordinary SQL and Jinja comments are reported. Projects may explicitly allow
traceable or marked comments. Machine directives remain allowed. Consecutive
physical comments are always reported.

It adds two non-fixing rules.

| Rule | Name | Behavior |
| --- | --- | --- |
| `Legibility_L001` | `legibility.no_unmatched_comments` | Reports comments unless explicitly allowed. |
| `Legibility_L002` | `legibility.no_stacked_comments` | Reports consecutive physical comments. |

SQLFluff's built-in [`LT05`](https://docs.sqlfluff.com/en/stable/reference/rules.html#rule-LT05)
handles line length. This plugin does not duplicate it.

## Quick start

Add the plugin to a SQL project managed with uv:

```console
uv add --dev sqlfluff-plugin-legibility
```

Projects not using uv can install the same package with pip:

```console
pip install sqlfluff-plugin-legibility
```

SQLFluff discovers the installed plugin automatically. Configure the rules in an
existing `.sqlfluff` file. Choose the dialect that matches your project; the plugin
does not set one.

```diff
 [sqlfluff]
 dialect = ansi
+warnings = Legibility_L001, LT05
+max_line_length = 80
```

`Legibility_L002` is omitted from `warnings`, so stacked comments are errors.

Run SQLFluff:

```console
uv run sqlfluff lint path/to/query.sql
```

Codes listed in `warnings` are reported but do not themselves make lint fail. Remove
a code from `warnings` to enforce it as a failure. To limit linting to these rules,
add the following.

```diff
 [sqlfluff]
+rules = Legibility_L001, Legibility_L002, LT05
```

## Behavior

| Comment | Result |
| --- | --- |
| Ordinary SQL or Jinja comment | Reported |
| Traceable comment | Reported until `comment_matchers` allows it |
| Additional matched comment in the same statement | Reported |
| Marked comment | Reported until a prefix or suffix identifier allows it |
| Consecutive physical comments | Reported by `Legibility_L002` |
| Built-in machine directive | Allowed |
| Other machine directive | Reported until `directive_matchers` allows it |

In the examples below, `-` is discouraged and `+` is recommended.

## Keep lines readable

`LT05` reports lines longer than the configured limit. Wrap long selections so each
column is easy to scan.

```diff
-SELECT customer_id, customer_name, billing_account_id, billing_account_status FROM customers;
+SELECT
+    customer_id,
+    customer_name,
+    billing_account_id,
+    billing_account_status
+FROM customers;
```

## Remove ordinary comments

No comment configuration is required. By default, each ordinary SQL or Jinja
comment reports `Legibility_L001`.

```diff
--- Explain the join.
 SELECT customers.id
 FROM customers;
```

```diff
-SELECT customers.id /* Keep this stable. */
+SELECT customers.id
 FROM customers;
```

```diff
-{# Explain the model. #}
 SELECT customers.id
 FROM customers;
```

The rule never edits, moves, or deletes a comment.

## Allow one traceable comment

Use a regex when a ticket, decision record, or other traceable identifier makes a
comment useful.

```diff
 [sqlfluff:rules:legibility.no_unmatched_comments]
+comment_matchers = \b(ENG|OPS)-[0-9]+\b
```

If a comment contains information the SQL cannot express, connect it to a durable
record:

```diff
--- Provider retries must remain ordered.
+-- ENG-481: Provider retries must remain ordered.
 SELECT retry_id
 FROM retries;
```

Only one regex-matched physical comment is allowed per top-level statement. The
limit resets for each new statement. A comment after a semicolon belongs to the
statement on that line; a comment on the next line belongs to the next statement.

## Reject stacked comments

`Legibility_L002` reports every physical comment after the first in a consecutive
stack. Matchers, identifiers, and machine directives do not bypass this rule.

```diff
 -- ENG-481: Provider retries must remain ordered.
--- ENG-481: Do not reorder these retries.
 SELECT retry_id
 FROM retries;
```

A blank line between comments ends the stack. One multiline block comment is one
physical comment.

## Allow a marked comment

Prefix and suffix identifiers allow individual comments. Start without identifiers
and add only those required by a repository policy.

```diff
 [sqlfluff:rules:legibility.no_unmatched_comments]
+comment_prefix_identifiers = APPROVED
+comment_suffix_identifiers = @approved
```

The prefix must begin the comment.

```diff
--- The provider requires this ordering.
+-- APPROVED: The provider requires this ordering.
 SELECT retry_id FROM retries;
```

The suffix must end the comment.

```diff
--- The provider requires this ordering.
+-- The provider requires this ordering. @approved
 SELECT retry_id FROM retries;
```

Identifiers are case-insensitive and require a word boundary. `APPROVEDLY` does not
match `APPROVED`.

## Machine directives are exempt

The rule recognizes common directives without configuration:

```sql
-- sqlfluff:dialect:postgres
SELECT customer_id FROM customers;
```

```sql
-- depends_on: {{ ref('upstream_model') }}
SELECT customer_id FROM customers;
```

```sql
SELECT /*+ INDEX(customers customers_pk) */ customer_id
FROM customers; -- noqa: LT05
```

Projects can allow another directive syntax:

```diff
 [sqlfluff:rules:legibility.no_unmatched_comments]
+directive_matchers = ^generated:
```

```sql
-- generated: do not edit
SELECT customer_id FROM customers;
```

## Configuration reference

| Setting | Default | Purpose |
| --- | --- | --- |
| `comment_matchers` | Empty | Comma-separated, case-insensitive regular expressions; allows one matched comment per top-level statement |
| `comment_prefix_identifiers` | Empty | Comma-separated identifiers allowed at the start of a comment |
| `comment_suffix_identifiers` | Empty | Comma-separated identifiers allowed at the end of a comment |
| `directive_matchers` | Empty | Comma-separated, case-insensitive regular expressions for additional machine directives |

## Severity

SQLFluff treats enabled rules as errors unless their codes appear in `warnings`.
Agent sessions and CI must leave `Legibility_L002` out of `warnings`. Developers
may add it to `warnings` for non-blocking local feedback.

```diff
 [sqlfluff]
-warnings = Legibility_L001, LT05
+warnings = Legibility_L001, Legibility_L002, LT05
```

## Agent policy

Agents should not add or update comments. They may remove or move comments. They
must treat `Legibility_L002` as an error and must not add a marker or directive to
bypass `Legibility_L001`.

## License

MIT
