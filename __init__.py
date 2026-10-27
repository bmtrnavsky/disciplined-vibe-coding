"""disciplined-vibe-coding plugin — bundles the Define/Plan/Teardown/Build/Verify skills.

Skills live in ``skills/*/SKILL.md`` and the pipeline orchestrator lives in
``plugins/disciplined-vibe-coding/SKILL.md``; both are registered namespaced
as ``disciplined-vibe-coding:<skill>``, loaded via ``skill_view``.
"""

from pathlib import Path


def register(ctx):
    skills_dir = Path(__file__).parent / "skills"
    if skills_dir.is_dir():
        for child in sorted(skills_dir.iterdir()):
            skill_md = child / "SKILL.md"
            if child.is_dir() and skill_md.is_file():
                ctx.register_skill(child.name, skill_md)
    pipeline_md = (
        Path(__file__).parent
        / "plugins"
        / "disciplined-vibe-coding"
        / "SKILL.md"
    )
    if pipeline_md.is_file():
        ctx.register_skill("disciplined-vibe-coding", pipeline_md)
