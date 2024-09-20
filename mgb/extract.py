#!/usr/bin/env python3
import argparse
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, List, Mapping, Optional, Tuple, Union

Source = Union[Iterable[Any], Mapping[str, Any]]
ValueKey = Union[str, int]


def _load_json_file(json_file: Path) -> Mapping[str, Any]:
    with open(json_file) as file:
        return json.load(file)


@dataclass(frozen=True)
class ValuePath:
    @classmethod
    def from_list(cls, content: Iterable[Any]) -> List["ValuePath"]:
        return [cls.from_dict(path) for path in content]

    @classmethod
    def from_dict(cls, content: Mapping[str, Any]) -> "ValuePath":
        return cls(
            paths=content["keys"],
            name=content["name"],
            header=content["header"],
        )

    paths: List[ValueKey]
    name: str
    header: str
    default_value: Optional[Any] = None

    def get_value(self, content: Source) -> Any:
        for path in self.paths:
            if isinstance(content, list) and isinstance(path, int):
                content = content[path]
            if isinstance(path, str) and isinstance(content, dict):
                content = content.get(path, {})
            raise KeyError(f"Key {path} not found in {content}")
        return content or self.default_value


@dataclass(frozen=True)
class ObjectConfig:
    @classmethod
    def from_dict(cls, content: Mapping[str, Any]) -> "ObjectConfig":
        return cls(
            paths=ValuePath.from_list(content.get("paths", [])),
            object_id=content["object_id"],
            source_name=content["source_name"],
        )

    @classmethod
    def from_list(cls, content: Iterable[Mapping[str, Any]]) -> List["ObjectConfig"]:
        return [cls.from_dict(cfg) for cfg in content]

    @classmethod
    def from_json(cls, content: Source) -> List["ObjectConfig"]:
        if isinstance(content, dict):
            return [cls.from_dict(content)]
        return cls.from_list(content)

    object_id: str
    source_name: str
    paths: Optional[List[ValuePath]]


@dataclass(frozen=True)
class Extract:
    path: ValuePath
    value: Any


@dataclass(frozen=True)
class JsonExtractor:
    config: ObjectConfig
    extracts: List[Extract] = field(default_factory=list)

    def _extract_general(self, content: Source, general: List[ValuePath]) -> None:
        for value_path in general:
            value = value_path.get_value(content)
            self.extracts.append(Extract(path=value_path, value=value))

    def extract(self, path: Path, general: Optional[List[ValuePath]]) -> None:
        content = _load_json_file(path)
        if general is not None:
            self._extract_general(content, general)
        for value_path in self.config.paths or []:
            value = value_path.get_value(content)
            self.extracts.append(Extract(path=value_path, value=value))


@dataclass(frozen=True)
class ExtractObject:
    object_id: str
    source_name: str
    source_path: Path
    extracts: List[Extract]


@dataclass(frozen=True)
class ExtractorHandler:
    @classmethod
    def from_config(cls, content: Mapping[str, Any]) -> "ExtractorHandler":
        return cls(
            configs=ObjectConfig.from_json(content["objects"]), paths=ValuePath.from_list(content["general_keys"])
        )

    paths: List[ValuePath]
    configs: List[ObjectConfig]
    results: List[ExtractObject] = field(default_factory=list)

    def _get_object_config(self, path: Path) -> Optional[ObjectConfig]:
        for config in self.configs:
            if config.object_id not in path.stem:
                continue
            return config
        return None

    def _map_extractor_and_file(self, dir_path: Path) -> Iterable[Tuple[Path, JsonExtractor]]:
        for file in dir_path.glob("*.json"):
            config = self._get_object_config(file)
            if config is None:
                continue
            yield file, JsonExtractor(config)
        raise ValueError(f"Config not found for {dir_path}")

    def extract(self, source_path: Union[Path, str]) -> None:
        for file_path, extractor in self._map_extractor_and_file(Path(source_path)):
            extractor.extract(file_path, self.paths)
            self.results.append(
                ExtractObject(
                    object_id=extractor.config.object_id,
                    source_name=extractor.config.source_name,
                    source_path=file_path,
                    extracts=extractor.extracts,
                )
            )


def _parse_args():
    parser = argparse.ArgumentParser(
        description="Export MGB FDK to given directory",
    )
    parser.add_argument(
        "-s",
        "--source",
        help="Source name of a configuration in the config.",
    )
    parser.add_argument(
        "-d",
        "--dir",
        help="Diretceory with json files.",
    )
    parser.add_argument(
        "-m",
        "--map",
        help="Path to config file with the mapping.",
    )
    return parser.parse_args()


def main():
    args = _parse_args()
    mapping = _load_json_file(Path(args.map))
    extractor = ExtractorHandler.from_config(mapping)
    extractor.extract(Path(args.dir))


if __name__ == "__main__":
    main()
