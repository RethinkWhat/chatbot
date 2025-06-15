import yaml
from pathlib import Path
from collections import defaultdict

domain_dir = Path("domain")
output_file = Path("domain.yml")

merged = defaultdict(list)
merged["responses"] = {}
merged["session_config"] = {
    "session_expiration_time": 60,
    "carry_over_slots_to_new_session": True
}

for file in domain_dir.glob("*.yml"):
    with open(file, "r", encoding="utf-8") as f:
        part = yaml.safe_load(f)

        if not part:
            continue

        for key, value in part.items():
            if key == "responses":
                merged["responses"].update(value)
            elif key == "session_config":
                merged["session_config"].update(value)
            elif isinstance(value, list):
                merged[key].extend(value)
            elif isinstance(value, dict):
                merged[key].update(value)

# Deduplicate list-type values (like intents, actions)
for key in merged:
    if isinstance(merged[key], list):
        merged[key] = sorted(list(set(merged[key])))

# Insert version at the top
final_output = {"version": "3.1"}
final_output.update(merged)

# Save merged domain.yml
with open(output_file, "w", encoding="utf-8") as f:
    yaml.dump(final_output, f, sort_keys=False, allow_unicode=True)

print("Merged domain saved to domain.yml with version 3.1")
