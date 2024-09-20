#!/usr/bin/env python3

import re
import argparse
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, List, Mapping, Optional

import requests

MGB_API_CLIENT = "MGBAHN"
MGB_API_LANGUAGE = "de"

MGB_API_ROOT = "https://api.buildup.group/api"


@dataclass
class MgbCategory:
    sid: str
    name: str
    children: List["MgbCategory"] = field(default_factory=list)

    def to_dict(self) -> Mapping[str, Any]:
        return asdict(self)


def _get_children(content: Iterable[Mapping[str, Any]]) -> List[MgbCategory]:
    children = [_create_category(child) for child in content]
    return [child for child in children if child is not None]


def _create_category(content: Mapping[str, Any]) -> Optional[MgbCategory]:
    if not all(key in content for key in ("sid", "name")):
        return None
    return MgbCategory(
        sid=content["sid"],
        name=content["name"],
        children=_get_children(
            content.get("children", []),
        ),
    )


MGB_API_CATEGORY = f"{MGB_API_ROOT}/{MGB_API_LANGUAGE}/category/{MGB_API_CLIENT}"
# https://api.buildup.group/api/de/category/MGBAHN/root_category?ipAddress=195.202.202.12


def get_category_url(category: Optional[str] = None) -> str:
    category = category or "root_category"
    return f"{MGB_API_CATEGORY}/{category}"


def get_root_category() -> Optional[MgbCategory]:
    response = requests.get(get_category_url())
    response.raise_for_status()
    content = response.json()
    return _create_category(content)


@dataclass
class MgbObjectCategory:
    sid: str
    name: str
    path_to_root: str
    children: List["MgbObjectCategory"] = field(default_factory=list)

    def to_dict(self) -> Mapping[str, Any]:
        return asdict(self)


def get_object_category_children(content: Iterable[Mapping[str, Any]]) -> List[MgbObjectCategory]:
    children = [create_object_category(child) for child in content]
    return [child for child in children if child is not None]


def create_object_category(content: Mapping[str, Any]) -> Optional[MgbObjectCategory]:
    if not all(key in content for key in ("sid", "name")):
        return None
    return MgbObjectCategory(
        sid=content["sid"],
        name=content["name"],
        path_to_root=content.get("pathToRoot", ""),
        children=get_object_category_children(
            content.get("children", []),
        ),
    )


def get_object_category() -> Optional[MgbObjectCategory]:
    response = requests.get(get_category_url())
    response.raise_for_status()
    content = response.json()
    return create_object_category(content)


@dataclass
class MgbProduct:
    data: Mapping[str, Any]

    @property
    def product_info(self) -> Mapping[str, Any]:
        return self.data.get("productInfo", {})

    @property
    def product_title(self) -> str:
        return self.product_info.get("title", "")

    def product_full_name(self, reverse: bool = False) -> str:
        names = [self.product_title, self.product_sid]
        if reverse is True:
            names.reverse()
        return " ".join(names)

    @property
    def product_sid(self) -> str:
        return self.product_info.get("productSid", "")

    @property
    def object_id(self) -> str:
        return self.product_info.get("articleNumber", "")

    @property
    def orga_info(self) -> Mapping[str, Any]:
        return self.data.get("orgaInfo", {})

    @property
    def orga_sid(self) -> str:
        return self.orga_info.get("sid", {})

    def _cateogories_map(self) -> Mapping[str, Any]:
        return self.data.get("categories", {})

    @property
    def category(self) -> MgbCategory:
        category = self._cateogories_map().get("mainCategory", {})
        return MgbCategory(
            sid=category["sid"],
            name=category["name"],
        )

    @property
    def image_paths(self) -> Iterable[str]:
        for image in self.data.get("images", []):
            yield image["path"]

    def to_dict(self) -> Mapping[str, Any]:
        return self.data


MGB_API_PRODUCT_IMAGE = f"https://buildup-assets-1500.s3.eu-central-1.amazonaws.com/category/products/{MGB_API_CLIENT}"
# https://buildup-assets-1500.s3.eu-central-1.amazonaws.com/FDK_Mattertal_Tunnel/Images/OBJ_FB_1.png


def get_image_url(product: MgbProduct, image_name: str) -> str:
    return f"{MGB_API_PRODUCT_IMAGE}/{product.orga_sid}/Images/{image_name}.png"


MGB_API_PRODUCT = f"{MGB_API_ROOT}/{MGB_API_CLIENT}/{MGB_API_LANGUAGE}/product"
# https://api.buildup.group/api/MGBAHN/de/product/FDK_Mattertal_Tunnel/OBJ_HB_525?ipAddress=195.202.202.12


def get_product_url(project: str, sid: str) -> str:
    # https://api.buildup.group/api/de/category/products/MGBAHN/mgbahn_Bauwerke?randomSeed=39
    return f"{MGB_API_PRODUCT}/{project}/{sid}"


def mgb_fdk_product_by(project_sid: str, product_sid: str) -> MgbProduct:
    response = requests.get(get_product_url(project_sid, product_sid))
    response.raise_for_status()
    content = response.json()
    return MgbProduct(data=content)


@dataclass
class ProjectInfo:
    sid: str
    name: str
    detail_visible: bool
    products: List["ProjectProduct"] = field(default_factory=list)


MGB_API_PROJECTS = f"{MGB_API_ROOT}/{MGB_API_CLIENT}/{MGB_API_LANGUAGE}/orga/short"
# https://api.buildup.group/api/MGBAHN/de/orga/short?page=0&size=21&ipAddress=195.202.202.12


def get_project_infos() -> Iterable[ProjectInfo]:
    response = requests.get(MGB_API_PROJECTS)
    response.raise_for_status()
    content = response.json()
    for project in content.get("content", []):
        yield ProjectInfo(
            sid=project["sid"],
            name=project["name"],
            detail_visible=project["orgaDetailsVisible"],
        )


@dataclass
class ProjectProduct:
    product_sid: str
    orga_sid: str
    orga_name: str
    title: str


MGB_API_PROJECT = f"{MGB_API_ROOT}/{MGB_API_CLIENT}/{MGB_API_LANGUAGE}/product"
# https://api.buildup.group/api/MGBAHN/de/product/FDK_Mattertal_Tunnel?page=55&size=21&ipAddress=195.202.202.12


def _get_roject_url(short: ProjectInfo, page_size: int = 1600) -> str:
    return f"{MGB_API_PRODUCT}/{short.sid}?size={page_size}"
    # https://api.buildup.group/api/MGBAHN/de/product/FDK_Mattertal_Tunnel?page=55&size=21&ipAddress=195.202.202.12


def project_product_by(short: ProjectInfo, page_size: int = 20) -> Iterable[ProjectProduct]:
    response = requests.get(_get_roject_url(short, page_size))
    response.raise_for_status()
    content = response.json()
    for prod_data in content.get("content", []):
        yield ProjectProduct(
            product_sid=prod_data.get("productSid"),
            orga_sid=prod_data.get("orgaSid"),
            orga_name=prod_data.get("orgaName"),
            title=prod_data.get("title"),
        )


def _parse_args():
    parser = argparse.ArgumentParser(description="Export MGB FDK to given directory")
    parser.add_argument("--dir", help="Path to export the json files.", default="USERHOME")
    return parser.parse_args()


def export_file_name(product: MgbProduct):
    file_name = product.product_full_name(reverse=True)
    regex = re.compile("[^a-zA-Z0-9_-]+")
    file_name = regex.sub("_", file_name)
    return f"{file_name}.json"


def export_json(export_path: Path, product: MgbProduct):
    file_path = export_path / export_file_name(product)
    with open(file_path, mode="w", encoding="utf-8") as file:
        json.dump(product.to_dict(), file, indent=4, ensure_ascii=False)
    print(f"- JSON: {file_path.name}")


def export_images(export_path: Path, product: MgbProduct):
    headers = {
        "Content-Type": "image/png",
        "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "de-DE,de;q=0.6",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Host": "buildup-assets-1500.s3.eu-central-1.amazonaws.com",
        "Pragma": "no-cache",
        "Referer": "https://mgbahn.buildup.group/",
        "Sec-Fetch-Dest": "image",
        "Sec-Fetch-Mode": "no-cors",
        "Sec-Fetch-Site": "cross-site",
        "Sec-GPC": "1",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    }
    for image_path in product.image_paths:
        image_url = get_image_url(product, image_path)
        img_data = requests.get(image_url, headers=headers).content
        file_path = export_path / image_path
        with open(file_path, "wb") as handler:
            handler.write(img_data)
        print(f"- IMAGE: {file_path.name}")


def main():
    args = _parse_args()
    export_path = Path(args.dir)
    if not export_path.exists():
        export_path.mkdir(parents=True, exist_ok=True)
    for proj_info in get_project_infos():
        info_path = export_path / proj_info.name
        if not info_path.exists():
            info_path.mkdir(parents=True, exist_ok=True)
        for proj_prod in project_product_by(proj_info, page_size=2000):
            product = mgb_fdk_product_by(proj_prod.orga_sid, proj_prod.product_sid)
            print()
            print("-----------------------------------------------")
            print("Exporting:", product.product_full_name(reverse=True))
            print("-----------------------------------------------")
            category_path = info_path / product.category.name
            if not category_path.exists():
                category_path.mkdir(parents=True, exist_ok=True)

            export_json(category_path, product)
            # export_images(category_path, product)


if __name__ == "__main__":
    main()
