import os
import json

# デフォルトの解像度組み合わせリスト
DEFAULT_COMBOS = [
    # 正方形 1024～2048
    (1024, 1024), (1088, 1088), (1152, 1152), (1216, 1216),
    (1280, 1280), (1344, 1344), (1408, 1408), (1472, 1472),
    (1536, 1536), (1600, 1600), (1664, 1664), (1728, 1728),
    (1792, 1792), (1856, 1856), (1920, 1920), (1984, 1984),
    (2048, 2048),
    # 縦長パターン
    (896, 1152), (832, 1216), (768, 1280), (704, 1344),
    (640, 1408), (576, 1472), (512, 1536),
    (1408, 1664), (1344, 1728), (1280, 1792), (1216, 1856),
    (1152, 1920), (1088, 1984), (1024, 2048),
    (1920, 2048), (1856, 2048), (1792, 2048), (1728, 2048),
    (1664, 2048), (1600, 2048), (1536, 2048),
    # 横長パターン
    (1152, 896), (1216, 832), (1280, 768), (1344, 704),
    (1408, 640), (1472, 576), (1536, 512),
    (1664, 1408), (1728, 1344), (1792, 1280), (1856, 1216),
    (1920, 1152), (1984, 1088), (2048, 1024),
    (2048, 1920), (2048, 1856), (2048, 1792), (2048, 1728),
    (2048, 1664), (2048, 1600), (2048, 1536)
]

class HYBS_RandomResolutionSelector:

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff})
            }
        }

    RETURN_TYPES = ("INT", "INT")
    RETURN_NAMES = ("width", "height")
    FUNCTION = "random_resolution_selector"
    CATEGORY = "HYBS/ResolutionSelector"

    def random_resolution_selector(self, seed):
        combos = DEFAULT_COMBOS
        # JSON で上書き可能（config ディレクトリ内の resolution_combos.json）
        try:
            # config ディレクトリを参照
            script_dir = os.path.dirname(__file__)
            base_dir = os.path.dirname(script_dir)
            json_path = os.path.join(base_dir, "config", "resolution_combos.json")
            if os.path.isfile(json_path):
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                # 空リストや不正データを排除
                if isinstance(data, list) and len(data) > 0 and all(
                    isinstance(item, (list, tuple)) and len(item) == 2 for item in data
                ):
                    combos = [tuple(item) for item in data]
        except Exception:
            combos = DEFAULT_COMBOS

        # シード値に基づいて選択
        idx = seed % len(combos)
        return combos[idx]

NODE_CLASS_MAPPINGS = {
    "Random Resolution Selector": HYBS_RandomResolutionSelector,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "Random Resolution Selector": "Random Resolution Selector",
}