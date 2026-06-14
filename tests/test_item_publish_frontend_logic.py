import json
import subprocess
import textwrap
import unittest
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
APP_JS = ROOT_DIR / "static" / "js" / "app.js"


def extract_js_function(source: str, name: str) -> str:
    marker = f"function {name}("
    start = source.find(marker)
    if start == -1:
        raise AssertionError(f"missing function {name}")
    brace_start = source.find("{", start)
    depth = 0
    for index in range(brace_start, len(source)):
        char = source[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
    raise AssertionError(f"unterminated function {name}")


class ItemPublishFrontendLogicTest(unittest.TestCase):
    def test_loaded_material_images_are_used_when_file_input_is_empty(self):
        source = APP_JS.read_text(encoding="utf-8")
        helper = extract_js_function(source, "getItemPublishImagesForSubmit")
        script = textwrap.dedent(
            f"""
            let itemPublishLoadedMaterialImages = [
              {{ data: "data:image/png;base64,ZmFrZQ==", filename: "cover.png" }}
            ];
            {helper}
            const result = getItemPublishImagesForSubmit({{ files: [] }});
            console.log(JSON.stringify(result));
            """
        )
        completed = subprocess.run(
            ["node", "-e", script],
            cwd=ROOT_DIR,
            check=True,
            capture_output=True,
            text=True,
        )

        result = json.loads(completed.stdout)
        self.assertEqual(result["mode"], "json")
        self.assertTrue(result["hasImages"])
        self.assertEqual(result["images"][0]["filename"], "cover.png")

    def test_selected_files_win_over_loaded_material_images(self):
        source = APP_JS.read_text(encoding="utf-8")
        helper = extract_js_function(source, "getItemPublishImagesForSubmit")
        script = textwrap.dedent(
            f"""
            let itemPublishLoadedMaterialImages = [
              {{ data: "data:image/png;base64,ZmFrZQ==", filename: "draft.png" }}
            ];
            {helper}
            const result = getItemPublishImagesForSubmit({{ files: [{{ name: "new.jpg" }}] }});
            console.log(JSON.stringify(result));
            """
        )
        completed = subprocess.run(
            ["node", "-e", script],
            cwd=ROOT_DIR,
            check=True,
            capture_output=True,
            text=True,
        )

        result = json.loads(completed.stdout)
        self.assertEqual(result["mode"], "multipart")
        self.assertTrue(result["hasImages"])
        self.assertEqual(result["images"][0]["name"], "new.jpg")


if __name__ == "__main__":
    unittest.main()
