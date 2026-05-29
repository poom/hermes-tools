#!/usr/bin/env python3
"""Validate a skill folder against Jai's 10 skill creation gates."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


SCRIPT_EXTENSIONS = {".py", ".mjs", ".js", ".ts", ".sh", ".bash"}
IGNORED_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
    "tmp",
    "venv",
    ".venv",
}
REQUIRED_FRONTMATTER_KEYS = (
    "name",
    "description",
    "required-skills",
    "required-binaries",
)
FRONTMATTER_LIST_KEYS = ("required-skills", "required-binaries")
ALLOWED_FRONTMATTER_KEYS = {
    "name",
    "description",
    "version",
    "license",
    "allowed-tools",
    "metadata",
    "required-skills",
    "required-binaries",
    "required-env",
    "required-mcps",
    "mutates",
}
DEPENDENCY_NAME_RE = re.compile(r"^[A-Za-z0-9._-]+$")
LIST_ITEM_RE = re.compile(r"^\s*-\s+(.+?)\s*$")
FRAMEWORK_EVIDENCE_DIRS = (
    "04-integration-tests",
    "05-llm-evals",
    "07-resolver-evals",
    "09-e2e-smoke",
)
AUXILIARY_TOP_LEVEL_MARKDOWN = (
    "INSTALLATION",
    "QUICK_REFERENCE",
    "COMPLIANCE",
    "REPORT",
)
# README, CHANGELOG, LICENSE, and CONTRIBUTING are standard durable artifacts and
# are allowed at the skill root. The G10 rule targets scratch reports and
# compliance dumps, not conventional package documentation.


@dataclass
class GateResult:
    gate: int
    name: str
    status: str
    evidence: list[str]
    next_action: str


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(errors="ignore")


def iter_files(root: Path, *, include_ignored: bool = False) -> Iterable[Path]:
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if not include_ignored and any(part in IGNORED_DIRS for part in path.relative_to(root).parts):
            continue
        yield path


def parse_inline_list(value: str) -> list[str] | None:
    if not value.startswith("[") or not value.endswith("]"):
        return None

    inner = value[1:-1].strip()
    if not inner:
        return []

    return [item.strip().strip("\"'") for item in inner.split(",")]


def parse_frontmatter(skill_md: Path) -> tuple[dict[str, str | list[str]], str, list[str]]:
    if not skill_md.exists():
        return {}, "", ["SKILL.md not found"]
    text = read_text(skill_md)
    if not text.startswith("---\n"):
        return {}, text, ["SKILL.md does not start with YAML frontmatter"]
    end = text.find("\n---", 4)
    if end == -1:
        return {}, text, ["SKILL.md frontmatter is not closed"]
    raw = text[4:end]
    body = text[end + 4 :]
    data: dict[str, str | list[str]] = {}
    errors: list[str] = []
    current_list_key: str | None = None
    block_list_keys: set[str] = set()

    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        list_item = LIST_ITEM_RE.match(line)
        if list_item:
            if current_list_key is None:
                errors.append(f"frontmatter list item is not attached to a list key - {line}")
                continue
            item = list_item.group(1).strip().strip("\"'")
            existing = data.setdefault(current_list_key, [])
            if isinstance(existing, list):
                existing.append(item)
            continue

        current_list_key = None
        if ":" not in line:
            errors.append(f"frontmatter line lacks ':' - {line}")
            continue

        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        inline_list = parse_inline_list(value)
        if inline_list is not None:
            data[key] = inline_list
        elif value == "" and key in FRONTMATTER_LIST_KEYS:
            data[key] = []
            current_list_key = key
            block_list_keys.add(key)
        else:
            data[key] = value.strip("\"'")

    for key in sorted(block_list_keys):
        if data.get(key) == []:
            errors.append(f"frontmatter {key} block list is empty; use {key}: []")

    return data, body, errors


def frontmatter_scalar(frontmatter: dict[str, str | list[str]], key: str) -> str:
    value = frontmatter.get(key, "")
    return value if isinstance(value, str) else ""


def validate_frontmatter_schema(frontmatter: dict[str, str | list[str]], root: Path) -> list[str]:
    errors: list[str] = []

    for key in REQUIRED_FRONTMATTER_KEYS:
        if key not in frontmatter:
            errors.append(f"missing_required_frontmatter={key}")

    for key in FRONTMATTER_LIST_KEYS:
        value = frontmatter.get(key)
        if value is None:
            continue
        if not isinstance(value, list):
            errors.append(f"{key}_must_be_list")
            continue
        for item in value:
            if not DEPENDENCY_NAME_RE.fullmatch(item):
                errors.append(f"invalid_{key}_entry={item}")

    required_skills = frontmatter.get("required-skills", [])
    if isinstance(required_skills, list):
        known_skill_names = {
            path.name
            for path in root.parent.iterdir()
            if path.is_dir() and path.name not in IGNORED_DIRS
        }
        for required_skill in required_skills:
            if required_skill == root.name:
                errors.append(f"required_skills_self_reference={required_skill}")
            elif known_skill_names and required_skill not in known_skill_names:
                errors.append(f"required_skills_unknown={required_skill}")

    return errors


def is_test_script(path: Path) -> bool:
    name = path.name
    stem = path.stem
    return (
        name.startswith("test_")
        or stem.endswith("_test")
        or ".test." in name
        or path.parent.name in {"test", "tests"} and "test" in name
    )


def non_test_scripts(root: Path) -> list[Path]:
    scripts_dir = root / "scripts"
    if not scripts_dir.exists():
        return []
    return sorted(
        path
        for path in iter_files(scripts_dir)
        if path.suffix in SCRIPT_EXTENSIONS and not is_test_script(path)
    )


def test_candidates_for(script: Path) -> set[str]:
    stem = script.stem
    return {
        f"test_{stem}.py",
        f"{stem}_test.py",
        f"test_{stem}.mjs",
        f"{stem}.test.mjs",
        f"test_{stem}.js",
        f"{stem}.test.js",
        f"test_{stem}.ts",
        f"{stem}.test.ts",
        f"test_{stem}.sh",
        f"{stem}_test.sh",
        f"test_{stem}.bash",
        f"{stem}_test.bash",
    }


def has_matching_test(root: Path, script: Path) -> bool:
    candidates = test_candidates_for(script)
    return any(path.name in candidates for path in iter_files(root))


def markdown_files(root: Path) -> list[Path]:
    return sorted(path for path in iter_files(root) if path.suffix.lower() == ".md")


def skill_text(root: Path) -> str:
    parts: list[str] = []
    for path in iter_files(root):
        if path.suffix.lower() in {".md", ".py", ".mjs", ".js", ".ts", ".sh", ".yaml", ".yml", ".json"}:
            parts.append(read_text(path))
    return "\n".join(parts)


def evidence_text(root: Path) -> str:
    parts: list[str] = []
    for directory in ("references", "scripts", "test", "tests", *FRAMEWORK_EVIDENCE_DIRS):
        base = root / directory
        if not base.exists():
            continue
        for path in iter_files(base):
            if path.suffix.lower() in {".md", ".py", ".mjs", ".js", ".ts", ".sh", ".yaml", ".yml", ".json"}:
                parts.append(read_text(path))
    return "\n".join(parts)


def framework_files(root: Path, directory: str) -> list[Path]:
    base = root / directory
    if not base.exists():
        return []
    return sorted(
        path
        for path in iter_files(base)
        if path.suffix.lower() in {".md", ".py", ".mjs", ".js", ".ts", ".sh", ".yaml", ".yml", ".json"}
    )


def has_todo_marker(path: Path) -> bool:
    if not path.exists():
        return True
    return bool(re.search(r"(\[TODO\b|\bTODO\b)", read_text(path)))


def markdown_link_targets(path: Path) -> list[str]:
    text = read_text(path)
    links = re.findall(r"\[[^\]]+\]\(([^)]+)\)", text)
    return [
        link.split("#", 1)[0]
        for link in links
        if link
        and not link.startswith(("#", "http://", "https://", "mailto:", "app://", "plugin://"))
    ]


def referenced_paths(root: Path) -> set[Path]:
    found: set[Path] = set()
    for md in markdown_files(root):
        for target in markdown_link_targets(md):
            target_path = (md.parent / target).resolve()
            try:
                target_path.relative_to(root.resolve())
            except ValueError:
                continue
            found.add(target_path)
    return found


def missing_markdown_links(root: Path) -> list[str]:
    missing: list[str] = []
    for md in markdown_files(root):
        for target in markdown_link_targets(md):
            target_path = (md.parent / target).resolve()
            if not target_path.exists():
                missing.append(f"{md.relative_to(root)} -> {target}")
    return sorted(missing)


def unreferenced_references(root: Path) -> list[str]:
    refs_dir = root / "references"
    if not refs_dir.exists():
        return []
    referenced = referenced_paths(root)
    return sorted(
        str(path.relative_to(root))
        for path in refs_dir.glob("*.md")
        if path.resolve() not in referenced
    )


def unmentioned_scripts(root: Path, scripts: list[Path]) -> list[str]:
    text = "\n".join(read_text(path) for path in markdown_files(root))
    missing: list[str] = []
    for script in scripts:
        if script.name not in text and script.stem not in text:
            missing.append(str(script.relative_to(root)))
    return missing


def duplicate_headings(root: Path) -> list[str]:
    duplicates: list[str] = []
    for md in markdown_files(root):
        seen: set[str] = set()
        for heading in re.findall(r"^(#{1,6})\s+(.+)$", read_text(md), flags=re.MULTILINE):
            normalized = re.sub(r"\s+", " ", heading[1].strip().lower())
            if normalized in seen:
                duplicates.append(f"{md.relative_to(root)}: {heading[1].strip()}")
            seen.add(normalized)
    return duplicates


def file_has_smoke_command(path: Path) -> bool:
    text = read_text(path)
    path_has_smoke = bool(re.search(r"(smoke|e2e|end-to-end)", str(path), re.I))
    if path_has_smoke and re.search(r"(python3|npm|pytest|unittest|openclaw|\.\/)", text):
        return True
    if path.suffix.lower() != ".md":
        return False
    for match in re.finditer(r"(smoke test|e2e smoke|end-to-end smoke)", text, re.I):
        window = text[match.start() : match.start() + 500]
        if re.search(r"(python3|npm|pytest|unittest|openclaw|\.\/|command:)", window, re.I):
            return True
    return False


def gate(status: bool, number: int, name: str, evidence: list[str], next_action: str) -> GateResult:
    return GateResult(number, name, "PASS" if status else "FAIL", evidence, next_action)


def evaluate(root: Path) -> list[GateResult]:
    root = root.resolve()
    skill_md = root / "SKILL.md"
    frontmatter, body, frontmatter_errors = parse_frontmatter(skill_md)
    schema_errors = validate_frontmatter_schema(frontmatter, root)
    description = frontmatter_scalar(frontmatter, "description")
    name = frontmatter_scalar(frontmatter, "name")
    scripts = non_test_scripts(root)

    contract_checks = [
        skill_md.exists(),
        not frontmatter_errors,
        not schema_errors,
        bool(name and re.fullmatch(r"[a-z0-9-]{1,64}", name)),
        name == root.name,
        bool(description and len(description) >= 80),
        bool(re.search(r"\b(use when|triggered by|when creating|when asked)\b", description, re.I)),
        not (set(frontmatter) - ALLOWED_FRONTMATTER_KEYS),
        not has_todo_marker(skill_md),
        bool(re.search(r"\b(MUST|Protocol|Workflow|Contract|Rules|Gates|Failure)\b", body)),
    ]
    unexpected = sorted(set(frontmatter) - ALLOWED_FRONTMATTER_KEYS)
    contract_evidence = [
        f"name={name or '<missing>'}",
        f"description_length={len(description)}",
    ]
    if frontmatter_errors:
        contract_evidence.extend(frontmatter_errors)
    if schema_errors:
        contract_evidence.extend(schema_errors)
    if unexpected:
        contract_evidence.append(f"unexpected_frontmatter={','.join(unexpected)}")

    unit_missing = [str(script.relative_to(root)) for script in scripts if not has_matching_test(root, script)]

    integration_files = [
        str(path.relative_to(root))
        for path in framework_files(root, "04-integration-tests")
        if re.search(r"(integration|live|smoke|e2e)", str(path.relative_to(root)), re.I)
    ]
    integration_marker = re.search(
        r"(INTEGRATION_TEST|LIVE_TEST|requires live|live endpoint|integration test)",
        "\n".join(read_text(path) for path in framework_files(root, "04-integration-tests")),
        re.I,
    )

    llm_eval_files = []
    for path in framework_files(root, "05-llm-evals"):
        rel = str(path.relative_to(root))
        text = read_text(path) if path.suffix.lower() in {".py", ".md", ".json", ".yaml", ".yml"} else ""
        if re.search(r"(llm|judge)", rel, re.I) and re.search(
            r"(rubric|golden|expected|semantic|classification|judge)",
            text,
            re.I,
        ):
            llm_eval_files.append(rel)

    resolver_trigger = bool(
        re.search(r"\b(use when|triggered by)\b", description, re.I)
        and ((root / "agents" / "openai.yaml").exists() or (root / "AGENTS.md").exists())
    )

    resolver_eval_files = [
        str(path.relative_to(root))
        for path in framework_files(root, "07-resolver-evals")
        if re.search(r"(resolver|trigger|route|routing|dispatch)", str(path.relative_to(root)), re.I)
    ]
    resolver_eval_marker = re.search(
        r"(skill resolver|routes to this skill|should trigger|should not trigger)",
        "\n".join(read_text(path) for path in framework_files(root, "07-resolver-evals")),
        re.I,
    )

    missing_links = missing_markdown_links(root)
    orphan_refs = unreferenced_references(root)
    missing_script_mentions = unmentioned_scripts(root, scripts)
    duplicate_heading_hits = duplicate_headings(root)

    smoke_files = [
        str(path.relative_to(root))
        for path in framework_files(root, "09-e2e-smoke")
        if file_has_smoke_command(path)
    ]

    top_level_aux_md = [
        path.name
        for path in root.glob("*.md")
        if path.name != "SKILL.md" and any(token in path.name.upper() for token in AUXILIARY_TOP_LEVEL_MARKDOWN)
    ]
    gitignore_text = read_text(root / ".gitignore") if (root / ".gitignore").exists() else ""
    scratch_ok = True
    scratch_evidence: list[str] = []
    if (root / "tmp").exists():
        scratch_ok = scratch_ok and bool(re.search(r"(^|/)tmp/?$", gitignore_text, re.MULTILINE))
        scratch_evidence.append("tmp/ exists")
    if (root / "state").exists():
        scratch_ok = scratch_ok and bool(re.search(r"^state/?$", gitignore_text, re.MULTILINE))
        scratch_evidence.append("state exists")
    filing_ok = not top_level_aux_md and scratch_ok

    return [
        gate(
            all(contract_checks),
            1,
            "SKILL.md contract",
            contract_evidence,
            "Fix SKILL.md frontmatter/body so it is resolver-ready and free of TODO or unsupported metadata.",
        ),
        gate(
            bool(scripts),
            2,
            "Deterministic code",
            [f"{len(scripts)} non-test script(s) found"] + [str(path.relative_to(root)) for path in scripts[:8]],
            "Move repeated or fragile operations into scripts/ as deterministic code.",
        ),
        gate(
            bool(scripts) and not unit_missing,
            3,
            "Unit tests",
            ["all scripts have matching tests"] if not unit_missing and scripts else [f"missing tests: {', '.join(unit_missing) or 'no scripts'}"],
            "Add offline tests named test_<script>.py, <script>_test.py, or <script>.test.mjs next to the script or in a tests directory.",
        ),
        gate(
            bool(integration_files or integration_marker),
            4,
            "Integration tests",
            integration_files[:8] or (["durable integration marker found"] if integration_marker else ["no durable integration/live test marker found"]),
            "Add 04-integration-tests/ with an integration or live-test harness, explicit command, and credential skip behavior.",
        ),
        gate(
            bool(llm_eval_files),
            5,
            "LLM evals",
            llm_eval_files[:8] or ["no 05-llm-evals/* LLM judge with rubric/golden cases found"],
            "Add 05-llm-evals/<domain>_llm_judge.* with golden cases, expected outcomes, and a rubric.",
        ),
        gate(
            resolver_trigger,
            6,
            "Resolver trigger",
            [f"description={description[:160]}"] + (["agents/openai.yaml exists"] if (root / "agents" / "openai.yaml").exists() else []),
            "Make the description trigger-rich and add runtime resolver metadata where this environment requires it.",
        ),
        gate(
            bool(resolver_eval_files or resolver_eval_marker),
            7,
            "Resolver eval",
            resolver_eval_files[:8] or (["durable resolver marker found"] if resolver_eval_marker else ["no resolver/trigger routing eval found"]),
            "Add 07-resolver-evals/ cases proving realistic trigger prompts route to the skill and unrelated prompts do not.",
        ),
        gate(
            not missing_links and not orphan_refs and not missing_script_mentions and not duplicate_heading_hits,
            8,
            "Resolvable and DRY audit",
            [
                f"missing_links={len(missing_links)}",
                f"unreferenced_references={len(orphan_refs)}",
                f"unmentioned_scripts={len(missing_script_mentions)}",
                f"duplicate_headings={len(duplicate_heading_hits)}",
            ]
            + [f"duplicate: {item}" for item in duplicate_heading_hits[:3]]
            + [f"missing link: {item}" for item in missing_links[:3]]
            + [f"unreferenced ref: {item}" for item in orphan_refs[:3]],
            "Fix missing links, link every reference, mention every script in durable docs, and remove duplicate authority.",
        ),
        gate(
            bool(smoke_files),
            9,
            "E2E smoke test",
            smoke_files[:8] or ["no durable e2e/smoke command found"],
            "Add 09-e2e-smoke/ with a command that exercises the same operator/runtime path the skill is meant to support.",
        ),
        gate(
            filing_ok,
            10,
            "Filing rules",
            (scratch_evidence or ["no scratch dirs found"]) + ([f"top-level auxiliary markdown: {', '.join(top_level_aux_md)}"] if top_level_aux_md else []),
            "Move durable content into SKILL.md, references/, scripts/, numbered gate evidence folders, or assets/; keep scratch under ignored tmp/.",
        ),
    ]


def render_markdown(root: Path, results: list[GateResult]) -> str:
    overall = "PASS" if all(result.status == "PASS" for result in results) else "FAIL"
    lines = [f"# Skill Gate Check: {root.name}", "", f"Overall: **{overall}**", ""]
    failing = [result for result in results if result.status == "FAIL"]
    passing = [result for result in results if result.status == "PASS"]
    if failing:
        lines.extend(["## Failing gates", ""])
        for result in failing:
            lines.append(f"- G{result.gate} {result.name}: **FAIL**")
            lines.append(f"  Evidence: {'; '.join(result.evidence)}")
            lines.append(f"  Next: {result.next_action}")
        lines.append("")
    lines.extend(["## Passing gates", ""])
    for result in passing:
        lines.append(f"- G{result.gate} {result.name}: **PASS**")
        lines.append(f"  Evidence: {'; '.join(result.evidence)}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check a skill against the 10 pass/fail creation gates.")
    parser.add_argument("skill_root", help="Path to the skill folder")
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    args = parser.parse_args(argv)

    root = Path(args.skill_root).expanduser()
    if not root.exists() or not root.is_dir():
        print(f"error: skill root not found: {root}", file=sys.stderr)
        return 2

    results = evaluate(root)
    if args.format == "json":
        print(json.dumps({"skill": root.name, "overall": all(r.status == "PASS" for r in results), "gates": [asdict(r) for r in results]}, indent=2))
    else:
        print(render_markdown(root, results), end="")
    return 0 if all(result.status == "PASS" for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
