"""Live end-to-end run through the HTTP API (needs the backend running + a Groq key): prints step timing and quality counts."""
import json, sys, time, urllib.request, uuid
sys.path.insert(0, __file__.rsplit("scripts", 1)[0])
from pathlib import Path
B = "http://127.0.0.1:8000/api"
name = sys.argv[1] if len(sys.argv) > 1 else "IR-B-26-093_Omeprazole_Stage4.pdf"
S = Path(__file__).resolve().parents[2] / "samples" / name
def call(path, data=None, method=None, headers=None):
    return json.load(urllib.request.urlopen(urllib.request.Request(B + path, data=data, method=method, headers=headers or {})))
inv = call("/investigations", method="POST"); iid = inv["id"]; form = inv["form_data"]
bd = uuid.uuid4().hex
body = (f'--{bd}\r\nContent-Disposition: form-data; name="investigation_id"\r\n\r\n{iid}\r\n--{bd}\r\nContent-Disposition: form-data; name="file"; filename="{name}"\r\n\r\n').encode() + S.read_bytes() + f"\r\n--{bd}--\r\n".encode()
call("/documents", body, "POST", {"Content-Type": f"multipart/form-data; boundary={bd}"})
req = urllib.request.Request(B + "/ai/run", data=json.dumps({"investigation_id": iid, "intent": "full_analysis", "form": form, "provenance": {}}).encode(), headers={"Content-Type": "application/json"})
t0 = time.time(); ev = None; waits = 0
with urllib.request.urlopen(req, timeout=900) as r:
    for raw in r:
        line = raw.decode().rstrip()
        if line.startswith("event:"): ev = line[6:].strip()
        elif line.startswith("data:"):
            d = json.loads(line[5:])
            if ev == "step" and d["status"] != "running": print(f"{time.time()-t0:5.0f}s {d['node']:16} {d['status']:5} {d.get('model','')} | {d.get('detail')}")
            elif ev == "wait": waits += d["seconds"]
            elif ev in ("warning", "error"): print(ev.upper(), d.get("text"))
            elif ev == "patch":
                from app.forms import set_path
                set_path(form, d["patch"]["path"], d["patch"]["value"])
            elif ev == "done": print("DONE tokens", d["tokens"], "patches", d["patches"], "models", d["models"])
print(f"total {time.time()-t0:.0f}s (rate-limit waiting ~{waits}s)")
print("requirements:", [(x["requirement"], x["actual"], x["status"]) for x in form["problem"]["requirements"]])
print("RC:", [(x["certainty"], x["statement"][:110]) for x in form["root_causes"]])
print("CAPA:", [(x["type"], x["strength"]) for x in form["capa"]])
print("gaps:", len(form["evidence_gaps"]), "| other batches:", len(form["impact"]["other_batches"]))
