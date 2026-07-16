import unittest

from netroute_diagnose.clash import classify_policy, match_domain


class ClashRuleTests(unittest.TestCase):
    def test_first_matching_rule_wins(self):
        rules = [
            "DOMAIN,api.openai.com,DIRECT",
            "DOMAIN-SUFFIX,openai.com,PROXY",
            "MATCH,DIRECT",
        ]
        result = match_domain("api.openai.com", rules)
        self.assertEqual(result.policy, "DIRECT")
        self.assertEqual(result.rule_index, 0)
        self.assertEqual(result.confidence, "high")

    def test_suffix_does_not_match_lookalike(self):
        rules = ["DOMAIN-SUFFIX,openai.com,PROXY", "MATCH,DIRECT"]
        result = match_domain("notopenai.com", rules)
        self.assertEqual(result.policy, "DIRECT")

    def test_rule_provider_reduces_confidence(self):
        rules = ["RULE-SET,apple,DIRECT", "DOMAIN-SUFFIX,apple.com,PROXY"]
        result = match_domain("apple.com", rules)
        self.assertEqual(result.route_class, "PROXY")
        self.assertEqual(result.confidence, "limited")

    def test_named_group_is_proxy(self):
        self.assertEqual(classify_policy("Auto Select"), "PROXY")
        self.assertEqual(classify_policy("REJECT"), "REJECT")


if __name__ == "__main__":
    unittest.main()
