import os, tempfile, threading, time, unittest
from ciwarden import runner, policy


class KillMidRun(unittest.TestCase):
    def test_kill_cancels_running_command(self):
        d = tempfile.mkdtemp(); repo = os.path.join(d, "r"); os.makedirs(repo)
        kf = os.path.join(d, "KILL"); ks = policy.KillSwitch(kf)
        runner.KILL_CHECK = ks.check
        threading.Timer(0.6, lambda: open(kf, "w").close()).start()
        t0 = time.time()
        try:
            with self.assertRaises(policy.PolicyError):
                runner.run_command(repo, "python3 -c 'import time; time.sleep(30)'", timeout=30)
        finally:
            runner.KILL_CHECK = None
        self.assertLess(time.time() - t0, 5)
