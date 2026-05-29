#!/usr/bin/env python3
"""Offline health checks for the codex-daily-usage-record skill package."""
from __future__ import annotations

import argparse
import re
from pathlib import Path


SKILL_NAME = 'codex-daily-usage-record'
REQUIRED_DIRS = (
    '04-integration-tests',
    '05-llm-evals',
    '07-resolver-evals',
    '09-e2e-smoke',
    'references',
)


def read_text(path: Path) -> str:
    return path.read_text(encoding='utf-8')


def markdown_links(path: Path) -> list[str]:
    return re.findall(r'\[[^\]]+\]\(([^)#?]+\.md)(?:#[^)]+)?\)', read_text(path))


def check_skill(root: Path) -> list[str]:
    errors: list[str] = []
    skill_md = root / 'SKILL.md'
    if not skill_md.exists():
        return ['SKILL.md is missing']
    text = read_text(skill_md)
    if f'name: {SKILL_NAME}' not in text:
        errors.append(f'frontmatter name must be {SKILL_NAME}')
    for directory in REQUIRED_DIRS:
        if not (root / directory).exists():
            errors.append(f'{directory}/ is missing')
    for link in markdown_links(skill_md):
        if not (skill_md.parent / link).exists():
            errors.append(f'broken SKILL.md link: {link}')
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=f'Validate {SKILL_NAME} skill support files.')
    parser.add_argument('skill_root', nargs='?', default='.', help='Path to the skill root')
    args = parser.parse_args()
    errors = check_skill(Path(args.skill_root))
    if errors:
        for error in errors:
            print(error)
        return 1
    print(f'{SKILL_NAME} skill health ok')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
