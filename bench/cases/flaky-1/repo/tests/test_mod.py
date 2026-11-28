import os, tempfile, unittest
from src.mod import f
class T(unittest.TestCase):
    def test_f(self):
        p = os.path.join(tempfile.gettempdir(), 'ciw_flaky_' + os.environ.get('CIW_CASE', 'x') + '.cnt')
        n = int(open(p).read()) + 1 if os.path.exists(p) else 1
        open(p, 'w').write(str(n))
        self.assertEqual(f() + (n % 2), 1)
