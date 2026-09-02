import json
import os
from typing import List
from pathlib import Path
from app.models.product import RuleDefinition


class RuleLoader:
    def __init__(self, rules_filepath: str = None):
        if rules_filepath is None:
            # Default to rules.json in the same directory as this module
            current_dir = Path(__file__).parent
            self.rules_filepath = current_dir / "rules.json"
        else:
            self.rules_filepath = Path(rules_filepath)

    def load_rules(self) -> List[RuleDefinition]:
        """Loads and parses declarative rules from the rules.json file."""
        if not self.rules_filepath.exists():
            raise FileNotFoundError(f"Rules configuration file not found at: {self.rules_filepath}")

        with open(self.rules_filepath, "r", encoding="utf-8") as f:
            raw_rules = json.load(f)

        rules: List[RuleDefinition] = []
        for item in raw_rules:
            rules.append(RuleDefinition(**item))

        return rules
