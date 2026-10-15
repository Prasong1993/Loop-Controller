import unittest
from nexus.review_gates import GATE_SEQUENCE, evaluate_gate_readiness, list_review_gates

class ReviewGateTests(unittest.TestCase):
    def evidence_for(self, gate_id):
        gate = next(item for item in list_review_gates() if item["gate_id"] == gate_id)
        return [{"criterion_id": item["id"], "status": "VERIFIED",
                 "evidence_ref": f"evidence://{gate_id}/{item['id']}",
                 "verification_method": "independent artifact inspection"} for item in gate["criteria"]]

    def test_catalog_is_ordered(self):
        gates = list_review_gates()
        self.assertEqual(tuple(item["gate_id"] for item in gates), GATE_SEQUENCE)
        self.assertEqual(gates[0]["gate_id"], "SRR")
        self.assertEqual(gates[-1]["gate_id"], "AR")
        self.assertTrue(all(item["criteria"] for item in gates))

    def test_ready_does_not_mean_approved(self):
        result = evaluate_gate_readiness("SRR", [], self.evidence_for("SRR"))
        self.assertEqual(result["status"], "READY_FOR_REVIEW")
        self.assertEqual(result["gate_approval"], "NOT_GRANTED")
        self.assertTrue(result["reviewer_action_required"])

    def test_missing_evidence_blocks_gate(self):
        evidence = self.evidence_for("SRR")
        evidence.pop()
        result = evaluate_gate_readiness("SRR", [], evidence)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertTrue(any(item.startswith("CRITERION_NOT_READY:") for item in result["blockers"]))

    def test_unknown_status_reference_or_method_blocks_gate(self):
        evidence = self.evidence_for("SRR")
        evidence[0]["status"] = "UNKNOWN"
        self.assertEqual(evaluate_gate_readiness("SRR", [], evidence)["status"], "BLOCKED")
        evidence = self.evidence_for("SRR"); evidence[0]["evidence_ref"] = " "
        self.assertEqual(evaluate_gate_readiness("SRR", [], evidence)["status"], "BLOCKED")
        evidence = self.evidence_for("SRR"); evidence[0]["verification_method"] = ""
        self.assertEqual(evaluate_gate_readiness("SRR", [], evidence)["status"], "BLOCKED")

    def test_predecessor_gate_must_be_approved(self):
        result = evaluate_gate_readiness("SFR", [], self.evidence_for("SFR"))
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("PREDECESSOR_GATE_NOT_APPROVED:SRR", result["blockers"])
        result = evaluate_gate_readiness("SFR", [{"gate_id": "SRR", "status": "APPROVED"}], self.evidence_for("SFR"))
        self.assertEqual(result["status"], "READY_FOR_REVIEW")

    def test_unknown_and_duplicate_criteria_are_rejected_or_blocked(self):
        with self.assertRaisesRegex(ValueError, "UNKNOWN_REVIEW_GATE"):
            evaluate_gate_readiness("UNKNOWN", [], [])
        evidence = self.evidence_for("SRR"); evidence.append(dict(evidence[0]))
        with self.assertRaisesRegex(ValueError, "DUPLICATE_CRITERION_EVIDENCE"):
            evaluate_gate_readiness("SRR", [], evidence)
        evidence = self.evidence_for("SRR")
        evidence.append({"criterion_id": "not_in_catalog", "status": "VERIFIED", "evidence_ref": "x", "verification_method": "manual"})
        self.assertEqual(evaluate_gate_readiness("SRR", [], evidence)["status"], "BLOCKED")

    def test_duplicate_prior_gate_status_is_rejected(self):
        rows = [{"gate_id": "SRR", "status": "APPROVED"}, {"gate_id": "SRR", "status": "APPROVED"}]
        with self.assertRaisesRegex(ValueError, "DUPLICATE_PRIOR_GATE_STATUS"):
            evaluate_gate_readiness("SFR", rows, self.evidence_for("SFR"))

if __name__ == "__main__":
    unittest.main()
