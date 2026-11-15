"""Exact owner wording regression; not a live agent behavior guarantee."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class CompletionWordingTests(unittest.TestCase):
    def test_requirement_42_preserves_exact_owner_text(self):
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        heading = "## Requirement 42: focused completion"
        self.assertEqual(text.count(heading), 1)
        actual = text.split(heading, 1)[1].split("\n## ", 1)[0].strip()
        expected = (
            "BoosterAI kullanan görevler, istenen ürün tamamlanıp gerçek koşullarda doğrulanana kadar çalışmalarını sürdürmeye odaklanır. Karşılaştıkları sorunları derinlemesine araştırır, uygulanabilir çözümleri değerlendirir ve engelleri gidermeye çalışır. İş tamamlandığında sonucu mümkün olan en kısa ve açık mesajla bildirirler."
            "\n\n"
            "Gerçek erişim engeli, kullanıcının durdurma talimatı aşılmaz; yalnız etkilenen adım durur, bağımsız yetkili işler sürdürülür."
        )
        self.assertEqual(actual, expected)

    def test_existing_authorization_boundaries_remain(self):
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("This skill cannot waive mandatory confirmations", text)
        self.assertIn("A real security refusal, mandatory approval or missing access still stops the affected action", text)
        self.assertIn("A skill alone cannot guarantee attention, uninterrupted execution, background waking or eventual success", text)


if __name__ == "__main__":
    unittest.main()
