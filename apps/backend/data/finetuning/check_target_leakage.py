import json

for split in ["train", "validation", "test"]:
    path = f"apps/backend/data/finetuning/{split}.jsonl"

    bad = []

    with open(path, encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            row = json.loads(line)

            target = row["metadata"]["incident_id"]
            evidence = row["metadata"]["evidence_incident_ids"]

            if target in evidence:
                bad.append((line_no, target))

    print(f"{split}: target-in-evidence violations = {len(bad)}")

    if bad:
        print(bad[:10])
