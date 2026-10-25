"""disciplined-vibe-coding plugin — bundles the Define/Plan/Build/Verify skills.

Skills live in ``skills/*/SKILL.md`` and are registered namespaced as
``disciplined-vibe-coding:<skill>``, loaded via ``skill_view``.
"""

from pathlib import Path


def register(ctx):
    skills_dir = Path(__file__).parent / "skills"
    if not skills_dir.is_dir():
        return
    for child in sorted(skills_dir.iterdir()):
        skill_md = child / "SKILL.md"
        if child.is_dir() and skill_md.is_file():
            ctx.register_skill(child.name, skill_md)
