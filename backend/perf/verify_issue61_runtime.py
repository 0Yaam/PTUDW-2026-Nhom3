"""Verify recipe cache and resize on the isolated Issue #61 Compose project.

Start api and an api-peer process first; this script only stops/starts that
project's Redis service. It creates and then deletes one temporary recipe.
"""

import argparse
import json
import subprocess
import time
import uuid
from io import BytesIO
from pathlib import Path

import httpx
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]


def _compose(project: str, *arguments: str) -> None:
    subprocess.run(
        [
            "docker", "compose", "-p", project, "-f", "compose.yaml",
            "-f", "backend/perf/compose.issue61.yaml", *arguments,
        ],
        check=True, capture_output=True, text=True, cwd=ROOT,
    )


def _request(
    client: httpx.Client, method: str, url: str, expected: int, **kwargs: object
) -> httpx.Response:
    response = client.request(method, url, **kwargs)
    if response.status_code != expected:
        raise AssertionError(
            f"{method} {url}: expected {expected}, got {response.status_code}; "
            f"body={response.text[:500]}"
        )
    return response


def _contains(response: httpx.Response, recipe_id: str) -> bool:
    return any(row["id"] == recipe_id for row in response.json()["items"])


def _image_bytes() -> bytes:
    output = BytesIO()
    Image.new("RGB", (1200, 900), (150, 75, 30)).save(output, format="PNG")
    return output.getvalue()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", default="culinary-issue61")
    parser.add_argument("--api", default="http://127.0.0.1:18061")
    parser.add_argument("--peer", default="http://127.0.0.1:18062")
    args = parser.parse_args()

    unique = uuid.uuid4().hex[:12]
    title = f"Testcache{unique}"
    recipe_id = None
    auth = None
    redis_stopped = False
    with httpx.Client(timeout=15) as client:
        try:
            _request(client, "GET", f"{args.api}/health", 200)
            _request(client, "GET", f"{args.peer}/health", 200)
            categories = _request(
                client, "GET", f"{args.api}/api/v1/categories", 200
            ).json()
            assert categories, "Seed must provide a category"
            category_id = categories[0]["id"]
            registered = _request(
                client, "POST", f"{args.api}/api/v1/auth/register", 201,
                json={
                    "fullName": "Issue 61 Verification",
                    "email": f"issue61-{unique}@example.com",
                    "userName": f"issue61{unique}",
                    "password": "StrongPass1!",
                },
            ).json()
            auth = {"Authorization": f"Bearer {registered['accessToken']}"}
            created = _request(
                client, "POST", f"{args.api}/api/v1/recipes", 201,
                headers=auth,
                json={
                    "title": title, "description": "Temporary runtime verification recipe.",
                    "instructions": "Cook the ingredients.", "categoryId": category_id,
                    "prepTimeMinutes": 10, "cookTimeMinutes": 10,
                    "servings": 2, "difficulty": 1,
                },
            ).json()
            recipe_id = created["id"]
            slug = created["slug"]
            root = f"{args.api}/api/v1/recipes/{recipe_id}"
            _request(
                client, "POST", f"{root}/ingredients", 201, headers=auth,
                json={"ingredientName": f"Ingredient {unique}", "quantity": 1, "unit": "g"},
            )
            _request(
                client, "POST", f"{root}/steps", 201, headers=auth,
                json={"instruction": "Cook it."},
            )
            _request(client, "PATCH", f"{root}/publish", 200, headers=auth)

            image = _request(
                client, "POST", f"{root}/images", 201, headers=auth,
                files={"file": ("verify.png", _image_bytes(), "image/png")},
            ).json()
            assert image["originalUrl"] and image["mediumUrl"] is None
            detail_url = f"{args.peer}/api/v1/recipes/{slug}"
            for _ in range(30):
                detail = _request(client, "GET", detail_url, 200).json()
                images = detail["images"]
                if images and images[0]["mediumUrl"] and images[0]["thumbnailUrl"]:
                    break
                time.sleep(1)
            else:
                raise AssertionError("Image worker did not finish within 30 seconds")
            for size, dimensions in (("medium", (800, 600)), ("thumbnail", (300, 300))):
                variant = _request(client, "GET", images[0][f"{size}Url"], 200)
                with Image.open(BytesIO(variant.content)) as rendered:
                    assert rendered.size == dimensions and rendered.format == "WEBP"

            list_url = (
                f"{args.peer}/api/v1/recipes?categoryId={category_id}"
                "&sort=title&pageSize=50"
            )
            search_url = f"{args.peer}/api/v1/recipes/search?q={title}"
            for url in (list_url, search_url, detail_url):
                first = _request(client, "GET", url, 200)
                second = _request(client, "GET", url, 200)
                assert second.headers["X-Recipe-Cache"] == "HIT", url
                if url != detail_url:
                    assert _contains(first, recipe_id)

            _compose(args.project, "stop", "redis")
            redis_stopped = True
            _request(client, "PATCH", f"{root}/archive", 200, headers=auth)
            for url in (list_url, search_url):
                uncached = _request(client, "GET", url, 200)
                assert uncached.headers["X-Recipe-Cache"] == "BYPASS"
                assert not _contains(uncached, recipe_id)
            _request(client, "GET", detail_url, 403)

            _compose(args.project, "start", "redis")
            redis_stopped = False
            for _ in range(15):
                try:
                    response = _request(client, "GET", list_url, 200)
                    if response.headers["X-Recipe-Cache"] == "MISS":
                        break
                except httpx.HTTPError:
                    pass
                time.sleep(1)
            else:
                raise AssertionError("Redis did not recover to an active cache")
            assert not _contains(response, recipe_id)
            search = _request(client, "GET", search_url, 200)
            assert search.headers["X-Recipe-Cache"] == "MISS"
            assert not _contains(search, recipe_id)
            _request(client, "GET", detail_url, 403)
            print(json.dumps({
                "result": "pass", "recipeId": recipe_id,
                "checks": ["variants", "two_api_cache_hit", "redis_outage", "peer_recovery"],
            }))
        finally:
            if redis_stopped:
                _compose(args.project, "start", "redis")
            if recipe_id and auth:
                _request(
                    client, "DELETE", f"{args.api}/api/v1/recipes/{recipe_id}",
                    204, headers=auth,
                )


if __name__ == "__main__":
    main()
