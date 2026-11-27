# Escalation: needs a human

reason: model unsure

sign(0) in src/mod.py returns -1 while test_zero_positive expects 1, and test_zero_negative passed; without tests/test_mod.py it is unclear whether the defect is in src/mod.py or the test expectations.
