import json
import random

def main():
    # 用户输入五个分片的文件数量
    numbers = []
    for i in range(5):
        while True:
            try:
                num = int(input(f"请输入第{i+1}个分片的文件数量: "))
                if num <= 0:
                    raise ValueError("请输入大于0的整数")
                numbers.append(num)
                break
            except ValueError as e:
                print(e)

    # JSON 数据
    data = [
  {
    "_id": "00000988d53864ab82260415c21c0b704c62da7f",
    "mtime": 1726459400,
    "path": "00000988d53864ab82260415c21c0b704c62da7f",
    "size": 346008,
    "url": "https://edge.forgecdn.net/files/3951/752/projectvibrantjourneys-1.18.2-4.0.0-BETA2.jar"
  },
  {
    "_id": "000071853752df339428b91ca839ab45962cd1e0",
    "mtime": 1725767710,
    "path": "000071853752df339428b91ca839ab45962cd1e0",
    "size": 731749,
    "url": "https://edge.forgecdn.net/files/2290/73/RouterReborn-1.9-4.0.1.5b_universal.jar"
  },
  {
    "_id": "000076a3763a126f995267c715f9658e070205d2",
    "mtime": 1726460313,
    "path": "000076a3763a126f995267c715f9658e070205d2",
    "size": 734355,
    "url": "https://edge.forgecdn.net/files/5676/542/farmingforblockheads-neoforge-1.21.1-21.1.2.jar"
  },
  {
    "_id": "0000835490dd85ec4e3b19fdaff1c0468a8d6c67",
    "mtime": 1726225001,
    "path": "0000835490dd85ec4e3b19fdaff1c0468a8d6c67",
    "size": 16816,
    "url": "https://cdn.modrinth.com/data/eRGeQXjD/versions/1.3.3/mod-remapping-api-1.3.3-sources.jar"
  },
  {
    "_id": "00009bc8e13a08b149a9a7893056442b3be75f1f",
    "mtime": 1726280129,
    "path": "00009bc8e13a08b149a9a7893056442b3be75f1f",
    "size": 10872,
    "url": "https://edge.forgecdn.net/files/3217/972/giantspawn_1.14.4-2.3.jar"
  },
  {
    "_id": "0000a3329655eef156eb5a64ea45c15eb7823186",
    "mtime": 1726410017,
    "path": "0000a3329655eef156eb5a64ea45c15eb7823186",
    "size": 906911,
    "url": "https://cdn.modrinth.com/data/JOGZQCse/versions/40biFTzX/MagicLib-mc1.21.1-neoforge-0.8.597-beta.jar"
  },
  {
    "_id": "0000a388015e6521d887c4f7e35aa8cf659c196b",
    "mtime": 1725767710,
    "path": "0000a388015e6521d887c4f7e35aa8cf659c196b",
    "size": 213611,
    "url": "https://cdn.modrinth.com/data/9gx5Xvc5/versions/VQJmzhFK/simply-no-shading-6.1.1-alpha.publish.14-mc1.20.2.jar"
  },
  {
    "_id": "0001115044fac90700d3fcc73af4039cd3df3060",
    "mtime": 1725767710,
    "path": "0001115044fac90700d3fcc73af4039cd3df3060",
    "size": 209167,
    "url": "https://cdn.modrinth.com/data/Nt23S9h7/versions/sZ95Qaaa/custom_crafting_by_selah_a41.0.0_nametag.zip"
  },
  {
    "_id": "000122cf8a4db05f472a5ad8800dee3c93fe77bb",
    "mtime": 1726465499,
    "path": "000122cf8a4db05f472a5ad8800dee3c93fe77bb",
    "size": 163429,
    "url": "https://cdn.modrinth.com/data/VX3TgwQh/versions/ywBdooxp/carpet-extra-21w13a-1.4.30.jar"
  },
  {
    "_id": "0001262ebaf39e1c296aa0cbfb88d27938a32bc5",
    "mtime": 1726017925,
    "path": "0001262ebaf39e1c296aa0cbfb88d27938a32bc5",
    "size": 15948,
    "url": "https://edge.forgecdn.net/files/2921/411/Pokecube Pack-4.0.5.zip"
  }
]

    # 计算总文件数
    total_files = len(data)

    # 计算每个分片的文件数量
    slice_sizes = numbers[:5]

    # 初始化分片
    slices = {f"slice_{i+1}": [] for i in range(len(slice_sizes))}
    default_slice = "center"
    slices[default_slice] = []  # 初始化 center 分片

    # 将文件随机分配到分片中
    all_slices = list(slices.keys())
    for entry in data:
        assigned = False
        for _ in range(len(slice_sizes)):
            slice_name = random.choice(all_slices)
            if len(slices[slice_name]) < slice_sizes[int(slice_name.split('_')[1]) - 1]:
                slices[slice_name].append(entry["_id"])
                assigned = True
                break
        
        if not assigned:
            slices[default_slice].append(entry["_id"])

    # 将分配结果转换为字典形式
    result_slices = {}
    for slice_name, entries in slices.items():
        for entry_id in entries:
            if entry_id not in result_slices:
                result_slices[entry_id] = [slice_name]
            else:
                result_slices[entry_id].append(slice_name)

    # 查询特定文件的分片
    query_id = input("请输入要查询的文件ID: ")
    print(f"文件 {query_id} 属于分片: {', '.join(result_slices.get(query_id, ['center']))}")

if __name__ == "__main__":
    main()