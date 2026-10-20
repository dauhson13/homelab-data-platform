"""Build dbt/seeds/workloads.csv from a folder of Kubernetes manifests.

Usage: python scripts/build_inventory.py /path/to/k8s-deployments

Only names, sizes and image repositories are written. Hostnames, addresses and
anything from env or secret fields are ignored.
"""
import csv
import re
import sys
from pathlib import Path

import yaml

KINDS = {"Deployment", "StatefulSet", "DaemonSet"}
SKIP_NAMESPACE_PREFIXES = ("customer-",)  # client work stays out of the public dataset
SEED = Path(__file__).resolve().parent.parent / "dbt" / "seeds" / "workloads.csv"


def to_mb(value):
    if value is None:
        return None
    m = re.fullmatch(r"(\d+(?:\.\d+)?)(Ki|Mi|Gi|Ti|K|M|G|T)?", str(value))
    if not m:
        return None
    factor = {None: 1 / 1048576, "Ki": 1 / 1024, "Mi": 1, "Gi": 1024, "Ti": 1048576, "K": 1 / 1048.576, "M": 0.953674, "G": 953.674, "T": 953674}[m.group(2)]
    return round(float(m.group(1)) * factor)


def to_millicores(value):
    if value is None:
        return None
    s = str(value)
    return int(s[:-1]) if s.endswith("m") else int(float(s) * 1000)


def split_image(image):
    name, _, tag = image.rpartition(":") if ":" in image.split("/")[-1] else (image, "", "")
    parts = name.split("/")
    if len(parts) > 1 and ("." in parts[0] or ":" in parts[0]):
        parts = parts[1:]  # drop the registry host
    return "/".join(parts), tag or "latest"


def main(root):
    docs = []
    for path in sorted(Path(root).rglob("*.y*ml")):
        try:
            docs += [d for d in yaml.safe_load_all(path.read_text()) if isinstance(d, dict)]
        except yaml.YAMLError:
            continue
    ingress = {(d["metadata"].get("namespace"), b["backend"]["service"]["name"])
               for d in docs if d.get("kind") == "Ingress"
               for r in d.get("spec", {}).get("rules", [])
               for p in r.get("http", {}).get("paths", []) for b in [p]}
    rows = []
    for d in docs:
        if d.get("kind") not in KINDS:
            continue
        meta, spec = d["metadata"], d.get("spec", {})
        if re.fullmatch(r"[A-Z][A-Z_]+", meta.get("name", "")):
            continue  # template placeholder, not a real workload
        containers = spec.get("template", {}).get("spec", {}).get("containers", [])
        if not containers:
            continue
        image, tag = split_image(containers[0].get("image", ""))
        mem = sum(to_mb(c.get("resources", {}).get("requests", {}).get("memory")) or 0 for c in containers)
        cpu = sum(to_millicores(c.get("resources", {}).get("requests", {}).get("cpu")) or 0 for c in containers)
        ns = meta.get("namespace", "default")
        if ns.startswith(SKIP_NAMESPACE_PREFIXES):
            continue
        rows.append({
            "namespace": ns, "name": meta["name"], "kind": d["kind"],
            "replicas": spec.get("replicas", 1), "image": image, "image_tag": tag,
            "containers": len(containers), "memory_request_mb": mem, "cpu_request_m": cpu,
            "exposed": int((ns, meta["name"]) in ingress),
        })
    rows.sort(key=lambda r: (r["namespace"], r["name"]))
    with SEED.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} workloads in {len({r['namespace'] for r in rows})} namespaces -> {SEED}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else ".")
