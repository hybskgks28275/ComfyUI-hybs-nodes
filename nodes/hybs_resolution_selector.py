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

CONFIG_FILE_PATH = "config"
CONFIG_FILE_NAME ="resolution_combos.json"

def load_combos():
    """
    config/resolution_combos.json から解像度リストをロード。
    ファイル未存在時は DEFAULT_COMBOS を返す。
    JSONのパースエラーやフォーマット不正時は例外を投げる。
    """
    base_dir = os.path.dirname(os.path.dirname(__file__))
    json_path = os.path.join(base_dir, CONFIG_FILE_PATH, CONFIG_FILE_NAME)
    if os.path.isfile(json_path):
        # JSONファイルが存在する場合は読み込む
        with open(json_path, encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError as e:
                # JSONのパースエラー
                raise ValueError(f"Failed to parse {CONFIG_FILE_NAME}: {e}")
        # フォーマット検証
        if not (isinstance(data, list) and data and all(
            isinstance(item, (list, tuple)) and len(item) == 2 and
            isinstance(item[0], int) and isinstance(item[1], int)
            for item in data
        )):
            # フォーマットエラー
            raise ValueError(f"{CONFIG_FILE_NAME} must be a non-empty list of [width, height] integer pairs.")
        return [tuple(item) for item in data]
    # ファイル未存在時はデフォルトを使用
    return DEFAULT_COMBOS

class HYBS_ResolutionSelector:

    @classmethod
    def INPUT_TYPES(cls):
        return {
            # 解像度リストを取得して表示
            "required": {"resolution": ([f"{w}x{h}" for w, h in load_combos()],)}
        }
    
    RETURN_TYPES = ("INT", "INT")
    RETURN_NAMES = ("width", "height")
    FUNCTION = "resolution_selector"
    CATEGORY = "HYBS/ResolutionSelector"

    def resolution_selector(self, resolution):
        w, h = map(int, resolution.split("x"))
        return (w, h)

class HYBS_RandomResolutionSelector:

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                # seed値
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff})
            }
        }

    RETURN_TYPES = ("INT", "INT")
    RETURN_NAMES = ("width", "height")
    FUNCTION = "random_resolution_selector"
    CATEGORY = "HYBS/ResolutionSelector"

    def random_resolution_selector(self, seed):
        # 解像度リストを読み込み
        combos = load_combos()
        # seed に基づいて選択
        # random モジュールは再現性がなくなるため使用しない
        idx = seed % len(combos)
        return combos[idx]

NODE_CLASS_MAPPINGS = {
    "Resolution Selector": HYBS_ResolutionSelector,
    "Random Resolution Selector": HYBS_RandomResolutionSelector,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "Resolution Selector": "Resolution Selector",
    "Random Resolution Selector": "Random Resolution Selector",
}