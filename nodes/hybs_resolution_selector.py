import os
import json
from comfy_api.latest import ComfyExtension, io

# 既定の解像度コンボ
DEFAULT_COMBOS = [
    (1024, 1024), (1088, 1088), (1152, 1152), (1216, 1216),
    (1280, 1280), (1344, 1344), (1408, 1408), (1472, 1472),
    (1536, 1536), (1600, 1600), (1664, 1664), (1728, 1728),
    (1792, 1792), (1856, 1856), (1920, 1920), (1984, 1984),
    (2048, 2048),
    (896, 1152), (832, 1216), (768, 1280), (704, 1344),
    (640, 1408), (576, 1472), (512, 1536),
    (1408, 1664), (1344, 1728), (1280, 1792), (1216, 1856),
    (1152, 1920), (1088, 1984), (1024, 2048),
    (1920, 2048), (1856, 2048), (1792, 2048), (1728, 2048),
    (1664, 2048), (1600, 2048), (1536, 2048),
    (1152, 896), (1216, 832), (1280, 768), (1344, 704),
    (1408, 640), (1472, 576), (1536, 512),
    (1664, 1408), (1728, 1344), (1792, 1280), (1856, 1216),
    (1920, 1152), (1984, 1088), (2048, 1024),
    (2048, 1920), (2048, 1856), (2048, 1792), (2048, 1728),
    (2048, 1664), (2048, 1600), (2048, 1536)
]

CONFIG_FILE_DIR = "config"
CONFIG_FILE_NAME = "resolution_combos.json"


def _load_combos():
    """
    config/resolution_combos.json から解像度リストをロード。
    ファイル未存在時は DEFAULT_COMBOS を返す。
    """
    base_dir = os.path.dirname(os.path.dirname(__file__))
    json_path = os.path.join(base_dir, CONFIG_FILE_DIR, CONFIG_FILE_NAME)
    if os.path.isfile(json_path):
        # JSONファイルが存在する場合は読み込む
        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)
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


class HYBS_ResolutionSelector(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        # 解像度リストを取得して表示
        options = [f"{w}x{h}" for (w, h) in _load_combos()]
        return io.Schema(
            node_id="HYBS_ResolutionSelector",
            display_name="Resolution Selector",
            category="HYBS/ResolutionSelector",
            inputs=[
                io.Combo.Input("resolution", options=options),
            ],
            outputs=[
                io.Int.Output(display_name="width"),
                io.Int.Output(display_name="height"),
            ],
            description="Select a resolution from predefined combos."
        )

    @classmethod
    def execute(cls, resolution: str) -> io.NodeOutput:
        w, h = map(int, resolution.split("x"))
        return io.NodeOutput(w, h)
