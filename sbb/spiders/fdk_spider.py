import html
from io import BytesIO
import json
import os
from enum import Enum
from pathlib import Path
from typing import Optional

import PIL.Image as Image

import scrapy
from sbb_fdk.reader.json_reader import write_json
from scrapy.http import TextResponse

SBB_FDK_URL = 'https://bim-fdk-api.app.sbb.ch'
EXPORT_PATH = Path('C:/workspace/python/rsrg-bim-python/fdk')


def fdk_objects_url(object_id: Optional[str] = None) -> str:
    fdk_url = f'{SBB_FDK_URL}/objects'
    if object_id is not None:
        fdk_url = f'{fdk_url}/{object_id}'
    return fdk_url


def fdk_images_url(image_name: str) -> str:
    return f'{SBB_FDK_URL}/images/objects/{image_name}'


def create_if_not_exists(path: Path) -> None:
    if path.parent.exists():
        return
    os.makedirs(path.parent)


def url_name(response: TextResponse) -> str:
    url = response.url.split('/')[-1]
    url = html.unescape(url)
    if '%' in url:
        url = url.replace('%20', '')
        print(url)
    return url


def path_from_url(response: TextResponse, trade: str, extension: Optional[str] = None) -> Path:
    file_path = EXPORT_PATH / trade / url_name(response)
    if extension is None:
        create_if_not_exists(file_path)
        return file_path
    file_path = file_path.with_suffix(extension)
    create_if_not_exists(file_path)
    return file_path


class FdkJsonKeys(str, Enum):
    OBJECTS = "objects"
    IFC_ASSIGNMENTS = "ifcClassAssignments"
    VERSION = "version"
    IFC_CLASS = "ifcClass"
    OBJECT_ID = "ID_OBJ"
    NAME_DE = "name_DE"
    TRADE_NAME = "name_SYS"
    OBJECT_GRP = "name_OGRP"
    SUB_GROUP = "name_SGRP"
    IMG_LINK = "img_link"


class FdkSpider(scrapy.Spider):
    name = "fdk"

    def start_requests(self):
        urls = [fdk_objects_url()]
        for url in urls:
            yield scrapy.Request(url=url, callback=self.parse)

    def parse(self, response: TextResponse):
        json_data = json.loads(response.text)
        json_data = json_data[FdkJsonKeys.OBJECTS]
        for fdk_obj in json_data:
            object_id = fdk_obj.get(FdkJsonKeys.OBJECT_ID)
            yield scrapy.Request(url=fdk_objects_url(object_id),
                                 callback=self.parse_fdk_object)

        for fdk_obj in json_data:
            object_id = fdk_obj.get(FdkJsonKeys.OBJECT_ID)
            trade_name = fdk_obj.get(FdkJsonKeys.TRADE_NAME)

            def parse_object_image(response: TextResponse):
                image = Image.open(BytesIO(response.body))
                image.save(path_from_url(response, trade_name))

            yield scrapy.Request(url=fdk_images_url(fdk_obj[FdkJsonKeys.IMG_LINK]),
                                 callback=parse_object_image)

    def parse_fdk_object(self, response: TextResponse):
        json_data = json.loads(response.text)
        trade_name = json_data[FdkJsonKeys.TRADE_NAME]
        write_json(path_from_url(response, trade_name, '.json'), json_data)
