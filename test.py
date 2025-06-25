import json


def __main__():
    file = r"D:\PythonProject\fastApp\comfyUI_workflow\payload_debug.json"
    try:
        with open(file, "r", encoding="utf-8") as f:
            request_text = json.load(f)
    except FileNotFoundError:
        print(f"File {file} not found. Using empty request text.")
        request_text = {}
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
        request_text = {}
    print(
        "request_text loaded from file:\n"
        + json.dumps(request_text, ensure_ascii=False, indent=2)
    )

    import requests

    resp = requests.post(
        "http://127.0.0.1:8188/api/prompt",
        json=request_text,
        headers={"Content-Type": "application/json"},
        timeout=300,
    )
    if resp.status_code == 200:
        print("Request was successful.")
        print(resp.json())
    else:
        print(f"Request failed, status code: {resp.status_code}")
        print(resp.text)


if __name__ == "__main__":
    __main__()
