#!/usr/bin/env python3
"""Report K020 resumable search state from local SQLite, read-only."""
import json,sqlite3
from pathlib import Path
db_path=Path(__file__).resolve().parent.parent/"k001/private/runs/k020/search.sqlite3"
if not db_path.is_file():
 print("K020 STATUS: no database yet; start mutagenic_overnight_search.py")
 raise SystemExit(0)
db=sqlite3.connect(f"file:{db_path}?mode=ro",uri=True,timeout=10)
for status,count in db.execute("SELECT status,COUNT(*) FROM candidates GROUP BY status ORDER BY COUNT(*) DESC"):
 print("K020",status,count)
count=db.execute("SELECT COUNT(*) FROM tests").fetchone()[0]
print("K020 verifier_trials",count)
print("K020 TOP VERIFIED CANDIDATES (partial-domain tests only)")
rows=db.execute("""SELECT c.id,c.config,c.resources,c.proxy,
  COUNT(t.id) AS tests, MAX(CASE WHEN t.passed=1 THEN t.max_x ELSE 0 END) AS reach,
  SUM(CASE WHEN t.passed=0 THEN 1 ELSE 0 END) AS failed,
  c.status,c.path
 FROM candidates c JOIN tests t ON c.id=t.candidate_id
 GROUP BY c.id ORDER BY failed ASC,reach DESC,c.proxy ASC LIMIT 15""").fetchall()
for cid,config,res,proxy,tests,reach,failed,status,path in rows:
 print(json.dumps({"id":cid,"config":json.loads(config),"stats":json.loads(res) if res else None,
   "proxy":proxy,"tests":tests,"max_x_pass":reach,"failed_tests":failed,
   "status":status,"kmb":path},sort_keys=True))
print("K020 report",db_path.parent.parent.parent.parent/"k020/k020_status.json")
db.close()
