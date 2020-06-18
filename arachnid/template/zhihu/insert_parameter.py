import os
import csv

from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError

# 通过这里配置插入参数的参数
SPIDER_ID = 0
TEMPLATE_ID = 8
FILE_PATH = "keyword.csv"


def read_csv_file(file_name):
    csv_list = []
    with open(file_name, newline='') as csvfile:
        spamreader = csv.reader(csvfile, delimiter=' ', quotechar='|')
        for row in spamreader:
            line_list = []
            for line in row:
                line_list.append(line)

            csv_list.append(line_list)

    return csv_list


def modify_csv_list(paras_list):
    header_list = []
    header_dict = {}

    for head in paras_list[0]:
        header_list.append(head)
        header_dict.update({head: []})

    for row in paras_list:
        for i, line in enumerate(row):
            header_dict[header_list[i]].append(line)

    paras_dict = {"headersList": header_list,
                  "parameterMap": header_dict,
                  "spiderId": SPIDER_ID,
                  "templateId": TEMPLATE_ID}

    return paras_dict


def insert_into_mongo(item_dict):
    mongo = MongoClient(
        host="localhost",
        port=27017,
        username="",
        password="",
        authSource="admin",
    )
    db = mongo.get_database("test")
    col = db.get_collection("parameters")
    try:
        col.insert_one(item_dict)
    except DuplicateKeyError:
        print("Parameters already exist.")

    print(item_dict)
    return str(item_dict["_id"])


if __name__ == "__main__":
    file_path = FILE_PATH
    para_list = read_csv_file(file_path)
    print(para_list)

    para_dict = modify_csv_list(para_list)
    print(para_dict)

    obj_id = insert_into_mongo(para_dict)
    print(obj_id)
