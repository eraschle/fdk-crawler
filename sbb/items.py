# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

from dataclasses import dataclass

import scrapy


@dataclass
class IfcClassAssignmentsItem(scrapy.Item):
    version: str
    ifcClass: str


@dataclass
class FdkObjectTypeItems(scrapy.Item):
    id_obj: str
    name_DE: str
    name_SYS: str
    object_group: str
    sub_group: str
    img_link: str
    ifc_class: IfcClassAssignmentsItem
