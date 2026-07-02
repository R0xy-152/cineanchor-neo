from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


class BirthdayUIContractTests(unittest.TestCase):
    def test_template_entry_and_required_inputs_exist(self) -> None:
        html = (REPO_ROOT / "apps" / "web" / "index.html").read_text(encoding="utf-8")
        for marker in (
            'data-template="character_birthday"',
            'id="characterNameInput"',
            'id="birthdayDateInput"',
            'id="birthdayDialogueInput"',
            'id="birthdayPrimaryColor"',
            'id="logoFileInput"',
        ):
            self.assertIn(marker, html)

    def test_ui_builds_v02_birthday_project(self) -> None:
        script = (REPO_ROOT / "apps" / "web" / "app.js").read_text(encoding="utf-8")
        self.assertIn('version: "0.2"', script)
        self.assertIn('id: "main_character"', script)
        self.assertIn('id: "logo"', script)
        self.assertIn("subtitle_lines", script)


if __name__ == "__main__":
    unittest.main()
