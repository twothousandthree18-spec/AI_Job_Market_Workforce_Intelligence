"""Quick verification that the pipeline framework and configs load correctly."""
import sys
sys.path.insert(0, "src")

from pipeline.config import (
    RunManifest, load_source_config, load_skill_lexicon,
    load_title_map, load_schema_manifest, PROJECT_ROOT
)

m = RunManifest(run_type="test", source="framework_check")
m.logger.info("Pipeline framework loaded OK")
m.finish("completed")
print(f"Run ID: {m.run_id}")
print(f"Log: {m.run_dir / 'pipeline.log'}")
print(f"Manifest: {m.run_dir / 'manifest.json'}")

cfg = load_source_config()
print(f"Sources: {list(cfg['sources'].keys())}")

lex = load_skill_lexicon()
total_skills = sum(len(v) for v in lex["categories"].values())
print(f"Skill categories: {list(lex['categories'].keys())} ({total_skills} skills total)")

titles = load_title_map()
print(f"Role categories: {list(titles['role_categories'].keys())}")

schema = load_schema_manifest()
print(f"Schema fields: {len(schema['canonical_fields'])}")

print("\nAll framework checks passed.")
