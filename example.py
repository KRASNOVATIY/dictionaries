import json
from example.telegram import TeleData

print("\n{} data1 {}".format("*"*20, "*"*20))
cell_obj = TeleData(open("example/data1", "rb").read())
constructor = cell_obj.read_int32
cell_data = cell_obj.message_deserialize(constructor)
print(json.dumps(cell_data, sort_keys=True, indent=4))
site_name_ways = list(cell_data.find_key("location"))
for way in site_name_ways:
    print(cell_data.get_value(way), way)

print("\n{} data2 {}".format("*"*20, "*"*20))
cell_obj = TeleData(open("example/data2", "rb").read())
constructor = cell_obj.read_int32
cell_data = cell_obj.message_deserialize(constructor)
site_name_ways = list(cell_data.find_key("site_name"))
for way in site_name_ways:
    print(cell_data.get_value(way), way)


