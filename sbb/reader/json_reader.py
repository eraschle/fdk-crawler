import codecs
import json
from pathlib import Path
from typing import Any, Dict


def read_json(path: Path) -> Dict[str, Any]:
    with open(path, mode='r', encoding='utf8') as file:
        return json.loads(file.read())


def write_json(path: Path, context: Dict[str, Any]) -> None:
    with codecs.open(str(path), mode='w', encoding='utf8') as file:
        json.dump(context, file, indent=4, ensure_ascii=False)
