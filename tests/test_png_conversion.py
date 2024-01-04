import json
from pathlib import Path

from cut_api.utils import geojson_to_rasterized_png

PNG_TEST_CASE = Path(__file__).parent / "test_cases" / "geojson_to_png_test_case.json"


def load_json_from_file(file_path):
    with open(file_path, "r") as file:
        data = json.load(file)
    return data


def test_png_conversion():
    test_case_data = load_json_from_file(PNG_TEST_CASE)
    expected_result = test_case_data["output"]
    converted = geojson_to_rasterized_png(test_case_data["input"])
    converted_encoded = json.dumps(converted).encode()
    assert json.loads(converted_encoded) == expected_result
