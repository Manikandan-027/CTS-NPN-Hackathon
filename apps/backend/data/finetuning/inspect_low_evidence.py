import json

path = "apps/backend/data/finetuning/train.jsonl"

shown = 0

with open(path, encoding="utf-8") as f:
    for line in f:
        row = json.loads(line)

        evidence = row["metadata"]["evidence_incident_ids"]

        if len(evidence) <= 2:
            print(json.dumps(row["metadata"], indent=2))
            print("-" * 80)

            shown += 1

            if shown >= 10:
                break
