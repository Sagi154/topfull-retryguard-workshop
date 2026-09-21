"""
test_patch_locust_task_weights.py — Unit tests for the pure patch_text()
function in patch_locust_task_weights.py. No file I/O, no network.

Run:
    python experiments/test_patch_locust_task_weights.py
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import patch_locust_task_weights as patcher


# Minimal fixture matching the real locust_online_boutique.py's shape for
# the five decorated task methods this patcher targets (unrelated file
# content omitted — the patcher only ever matches on these anchor lines).
UNPATCHED_TEXT = """\
class OnlineBoutiqueUser(TaskSet):
    @tag('postcheckout')
    @task(50)
    def checkout_slow(self):
        pass

    @tag('getcart')
    @task(30)
    def viewCart_slow(self):
        pass

    @tag('postcart')
    @task(15)
    def addToCart_slow(self):
        pass

    @tag('emptycart')
    @task(15)
    def emptyCart_slow(self):
        pass

    @tag('getproduct')
    @task(150)
    def browseProduct_slow(self):
        pass
"""

PATCHED_TEXT = (
    UNPATCHED_TEXT
    .replace("@task(50)\n    def checkout_slow(self):", "@task(500)\n    def checkout_slow(self):")
    .replace("@task(30)\n    def viewCart_slow(self):", "@task(100)\n    def viewCart_slow(self):")
    .replace("@task(15)\n    def addToCart_slow(self):", "@task(1)\n    def addToCart_slow(self):")
    .replace("@task(15)\n    def emptyCart_slow(self):", "@task(1)\n    def emptyCart_slow(self):")
    .replace("@task(150)\n    def browseProduct_slow(self):", "@task(100)\n    def browseProduct_slow(self):")
)


class TestPatchText(unittest.TestCase):
    def test_patches_all_five_weights(self):
        result = patcher.patch_text(UNPATCHED_TEXT)
        self.assertEqual(result, PATCHED_TEXT)

    def test_idempotent_when_already_fully_patched(self):
        result = patcher.patch_text(PATCHED_TEXT)
        self.assertEqual(result, PATCHED_TEXT)

    def test_idempotent_on_second_call_chained(self):
        once = patcher.patch_text(UNPATCHED_TEXT)
        twice = patcher.patch_text(once)
        self.assertEqual(once, twice)

    def test_partial_prior_patch_is_completed(self):
        # Simulate a file where one weight was already hand-fixed to the
        # new value but the rest are still old — patch_text must finish
        # the job rather than bailing out or double-patching.
        partial = UNPATCHED_TEXT.replace(
            "@task(50)\n    def checkout_slow(self):",
            "@task(500)\n    def checkout_slow(self):",
        )
        result = patcher.patch_text(partial)
        self.assertEqual(result, PATCHED_TEXT)

    def test_missing_anchor_raises_system_exit(self):
        broken = UNPATCHED_TEXT.replace(
            "@task(50)\n    def checkout_slow(self):",
            "@task(999)\n    def checkout_slow(self):",
        )
        with self.assertRaises(SystemExit):
            patcher.patch_text(broken)


if __name__ == "__main__":
    unittest.main()
