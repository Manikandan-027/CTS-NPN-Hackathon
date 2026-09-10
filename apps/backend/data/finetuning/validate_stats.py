import json

path = "apps/backend/data/finetuning/dataset_statistics.json"

with open(path, encoding="utf-8") as f:
    data = json.load(f)

splits = data["split_root_cause_distribution"]

roots = sorted(
    set(splits["train"])
    | set(splits["validation"])
    | set(splits["test"])
)

print(f"{'ROOT CAUSE':60} {'TRAIN':>8} {'VAL':>8} {'TEST':>8}")
print("-" * 90)

for root in roots:
    print(
        f"{root[:60]:60} "
        f"{splits['train'].get(root, 0):8} "
        f"{splits['validation'].get(root, 0):8} "
        f"{splits['test'].get(root, 0):8}"
    )
