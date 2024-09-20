#!/usr/bin/env python3


JSON_SCHEMA = {
    "general_keys": {
        "key_name": ["key1", "key2"],
    },
    "objects": {
        "object_id": {
            "uniq_name": ["key1", "key2"],
            "uniq_name1": ["key1", "key2"],
        },
        "object_id1": {
            "uniq_name": {
                "default": None,
                "path": ["key1", 5],
                "header": "Excel/CSV Header",
            },
            "uniq_name1": {
                "path": ["key1", "key2"],
            },
        },
    },
}
