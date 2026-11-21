"""Transactional experiment registry. A single controller owns a database lock."""
import json
import sqlite3
import time
from pathlib import Path
from .core import sha


class Store:
    def __init__(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.executescript('''
        PRAGMA journal_mode=WAL;
        PRAGMA foreign_keys=ON;
        CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS candidates(
            sha TEXT PRIMARY KEY, parent TEXT, path TEXT NOT NULL,
            proof TEXT NOT NULL, official_status TEXT NOT NULL DEFAULT 'NOT_RUN',
            score REAL, metrics TEXT, created REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS experiments(
            key TEXT PRIMARY KEY, parent TEXT NOT NULL, method TEXT NOT NULL,
            config TEXT NOT NULL, region TEXT NOT NULL, canonical TEXT NOT NULL,
            seed INTEGER NOT NULL, status TEXT NOT NULL, equivalence TEXT,
            candidate TEXT, verifier_result TEXT, score REAL, reason TEXT,
            seconds REAL NOT NULL DEFAULT 0, detail TEXT);
        CREATE INDEX IF NOT EXISTS experiment_method ON experiments(method,status);
        CREATE TABLE IF NOT EXISTS verification_queue(
            candidate TEXT PRIMARY KEY, priority INTEGER NOT NULL,
            FOREIGN KEY(candidate) REFERENCES candidates(sha));
        CREATE TABLE IF NOT EXISTS synthesis_cache(
            key TEXT PRIMARY KEY, outcome TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS history(
            key TEXT PRIMARY KEY, method TEXT, configuration TEXT, candidate TEXT,
            equivalence_status TEXT, verifier_result TEXT, score REAL,
            reason TEXT, provenance TEXT NOT NULL, raw TEXT NOT NULL);
        ''')
        self.db.commit()

    def get(self, key, default=None):
        row=self.db.execute('SELECT value FROM meta WHERE key=?',(key,)).fetchone()
        return json.loads(row[0]) if row else default

    def set(self, key, value):
        self.db.execute('INSERT OR REPLACE INTO meta VALUES (?,?)',(key,json.dumps(value)))
        self.db.commit()

    def recover(self):
        self.db.execute("UPDATE experiments SET status='PENDING',reason='Recovered interrupted task' WHERE status='RUNNING'")
        self.db.commit()

    def add(self, parent, method, config, region, canonical, seed, commit=True):
        # Canonical no-result experiments are shared across wire renaming.
        key=sha(json.dumps([method,config,canonical,seed],sort_keys=True))
        # Successful jobs are reapplied on new parents/occurrences, without
        # suppressing a useful repeated motif as an 'equivalent experiment'.
        row=self.db.execute('SELECT status FROM experiments WHERE key=?',(key,)).fetchone()
        if row and row[0]=='PENDING':
            self.db.execute('UPDATE experiments SET parent=?,region=? WHERE key=?',(parent,json.dumps(region),key))
        if row and row[0]=='LOCAL_IMPROVEMENT':
            key=sha(key+parent+json.dumps(region))
        self.db.execute('INSERT OR IGNORE INTO experiments(key,parent,method,config,region,canonical,seed,status) VALUES (?,?,?,?,?,?,?,?)',
            (key,parent,method,json.dumps(config,sort_keys=True),json.dumps(region),canonical,seed,'PENDING'))
        if commit: self.db.commit()
        return key

    def finish(self,key,status,reason,seconds=0,equivalence=None,candidate=None,detail=None):
        self.db.execute('UPDATE experiments SET status=?,reason=?,seconds=?,equivalence=?,candidate=?,detail=? WHERE key=?',
            (status,reason,seconds,json.dumps(equivalence),candidate,json.dumps(detail),key))
        if candidate:
            receipt=self.db.execute('SELECT metrics,score FROM candidates WHERE sha=?',(candidate,)).fetchone()
            if receipt and receipt[0]:
                self.db.execute('UPDATE experiments SET verifier_result=?,score=? WHERE key=?',(receipt[0],receipt[1],key))
        self.db.commit()

    def candidate(self, digest, parent, path, proof):
        self.db.execute('INSERT OR IGNORE INTO candidates(sha,parent,path,proof,created) VALUES (?,?,?,?,?)',
            (digest,parent,str(path),json.dumps(proof),time.time()))
        self.db.commit()

    def receipt(self, digest, result):
        self.db.execute('UPDATE candidates SET official_status=?,score=?,metrics=? WHERE sha=?',
            (result['status'],result.get('score'),json.dumps(result),digest))
        self.db.execute('UPDATE experiments SET verifier_result=?,score=? WHERE candidate=?',
            (json.dumps(result),result.get('score'),digest))
        self.db.commit()

    def queue_verification(self, digest, priority):
        self.db.execute('INSERT INTO verification_queue VALUES (?,?) ON CONFLICT(candidate) '
                        'DO UPDATE SET priority=max(priority,excluded.priority)', (digest, priority))
        self.db.commit()

    def pending_verifications(self):
        return self.db.execute("""
            SELECT c.sha,q.priority FROM verification_queue q JOIN candidates c ON c.sha=q.candidate
            WHERE c.official_status IN ('NOT_RUN','TIMEOUT','BUDGET_EXHAUSTED')
            ORDER BY q.priority DESC,c.created ASC
        """).fetchall()

    def cached_synthesis(self, key):
        row = self.db.execute('SELECT outcome FROM synthesis_cache WHERE key=?', (key,)).fetchone()
        return json.loads(row[0]) if row else None

    def remember_synthesis(self, key, outcome):
        self.db.execute('INSERT OR IGNORE INTO synthesis_cache VALUES (?,?)',
                        (key, json.dumps(outcome)))
        self.db.commit()

    def export(self, path):
        with Path(path).open('w') as stream:
            stream.write('{')
            for i,table in enumerate(('meta','experiments','candidates','history','synthesis_cache','verification_queue')):
                if i: stream.write(',')
                stream.write(json.dumps(table)+':[')
                first=True
                for row in self.db.execute('SELECT * FROM '+table):
                    if not first: stream.write(',')
                    stream.write(json.dumps(dict(row)));first=False
                stream.write(']')
            stream.write('}\n')

    def close(self):
        self.db.execute('PRAGMA wal_checkpoint(TRUNCATE)')
        self.db.close()
