#!/usr/bin/env python3
"""Read-only status of K026 overnight multi-method campaign."""
import json,sqlite3
from pathlib import Path
root=Path(__file__).resolve().parents[1]
db_path=root/"k001/private/runs/k026/campaign.sqlite3"
if not db_path.is_file():
 print("K026: no database yet; check qrr-k026 service and journal")
 raise SystemExit(0)
db=sqlite3.connect(f"file:{db_path}?mode=ro",uri=True,timeout=10)
print("K026 CANDIDATE STATES:")
for state,n in db.execute("SELECT status,COUNT(*) FROM candidates GROUP BY status ORDER BY COUNT(*) DESC"):
 print(f"  {state:28s} {n}")
print("K026 VERIFIER TEST COUNT",db.execute("SELECT COUNT(*) FROM tests").fetchone()[0])
rows=db.execute("""SELECT c.id,c.spec,c.resource_proxy,c.model_error,c.status,
 MAX(CASE WHEN t.verifier_pass=1 THEN t.level ELSE 0 END),
 SUM(CASE WHEN t.verifier_pass=0 THEN 1 ELSE 0 END)
 FROM candidates c JOIN tests t ON c.id=t.candidate
 GROUP BY c.id
 ORDER BY COALESCE(SUM(CASE WHEN t.verifier_pass=0 THEN 1 ELSE 0 END),0),
  MAX(CASE WHEN t.verifier_pass=1 THEN t.level ELSE 0 END) DESC,
  c.resource_proxy ASC LIMIT 15""").fetchall()
print("K026 VERIFIED FRONTIER (prefix tests only):")
for ident,spec,cost,model_error,status,reach,failed in rows:
 print(json.dumps({"id":ident,"spec":json.loads(spec),"cost_proxy":cost,
  "model_error":model_error,"state":status,"verified_through":reach,
  "failed_tests":failed or 0},sort_keys=True))
report=Path(__file__).resolve().parent/"k026_status.json"
if report.exists():
 d=json.loads(report.read_text())
 print("K026 RUN STATUS",d.get("status"),"GENERATION",d.get("generation"),
  "CANDIDATES",d.get("candidates_seen"))
db.close()
