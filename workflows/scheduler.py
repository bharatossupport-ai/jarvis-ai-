"""User workflows: a prompt run on a schedule, with status, pause/cancel and run history."""
import json
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from storage.db import db, audit


class WorkflowEngine:
    def __init__(self, run_prompt):
        self.run_prompt = run_prompt  # callable(prompt, companion) -> str
        self.sched = BackgroundScheduler()

    def start(self):
        self.sched.start()
        for wf in self.list():
            if wf["enabled"]:
                self._schedule(wf)

    def shutdown(self):
        if self.sched.running:
            self.sched.shutdown(wait=False)

    def _trigger(self, trigger, spec):
        spec = json.loads(spec) if isinstance(spec, str) else spec
        if trigger == "interval":
            return IntervalTrigger(minutes=int(spec.get("minutes", 60)))
        return CronTrigger(hour=spec.get("hour", 9), minute=spec.get("minute", 0),
                           day_of_week=spec.get("day_of_week", "*"))

    def _schedule(self, wf):
        self.sched.add_job(self.run_now, self._trigger(wf["trigger"], wf["spec"]), args=[wf["id"]],
                           id=f"wf{wf['id']}", replace_existing=True)

    def create(self, name, prompt, trigger="daily", spec=None, companion="JARVIS"):
        spec = spec or {"hour": 9, "minute": 0}
        with db() as c:
            wid = c.execute("INSERT INTO workflows(name, prompt, trigger, spec, companion) VALUES(?,?,?,?,?)",
                            (name, prompt, trigger, json.dumps(spec), companion)).lastrowid
        audit("workflow_created", name)
        self._schedule(self.get(wid))
        return wid

    def get(self, wid):
        with db() as c:
            return dict(c.execute("SELECT * FROM workflows WHERE id=?", (wid,)).fetchone())

    def list(self):
        with db() as c:
            return [dict(r) for r in c.execute("SELECT * FROM workflows ORDER BY id")]

    def next_run(self, wid):
        job = self.sched.get_job(f"wf{wid}")
        return job.next_run_time.strftime("%Y-%m-%d %H:%M") if job and job.next_run_time else "paused"

    def pause(self, wid):
        with db() as c:
            c.execute("UPDATE workflows SET enabled=0 WHERE id=?", (wid,))
        if self.sched.get_job(f"wf{wid}"):
            self.sched.pause_job(f"wf{wid}")

    def resume(self, wid):
        with db() as c:
            c.execute("UPDATE workflows SET enabled=1 WHERE id=?", (wid,))
        if self.sched.get_job(f"wf{wid}"):
            self.sched.resume_job(f"wf{wid}")
        else:
            self._schedule(self.get(wid))

    def delete(self, wid):
        if self.sched.get_job(f"wf{wid}"):
            self.sched.remove_job(f"wf{wid}")
        with db() as c:
            c.execute("DELETE FROM workflows WHERE id=?", (wid,))

    def run_now(self, wid):
        wf = self.get(wid)
        with db() as c:
            rid = c.execute("INSERT INTO workflow_runs(workflow_id, status) VALUES(?, 'running')", (wid,)).lastrowid
        try:
            out, status = self.run_prompt(wf["prompt"], wf["companion"]), "done"
        except Exception as e:
            out, status = str(e), "failed"
        with db() as c:
            c.execute("UPDATE workflow_runs SET status=?, output=? WHERE id=?", (status, out, rid))
        audit("workflow_run", f"{wf['name']}: {status}")
        return out

    def runs(self, wid=None, limit=50):
        q = "SELECT r.*, w.name FROM workflow_runs r LEFT JOIN workflows w ON w.id=r.workflow_id"
        args = ()
        if wid:
            q, args = q + " WHERE workflow_id=?", (wid,)
        with db() as c:
            return [dict(r) for r in c.execute(q + " ORDER BY r.id DESC LIMIT ?", args + (limit,))]
