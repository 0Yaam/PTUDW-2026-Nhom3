import uuid

import pytest
from pydantic import ValidationError

from culinary_blog_api.main import app
from culinary_blog_api.recipes.schemas import RecipeCreateRequest

VALID_PAYLOAD = {
    "title": "Gỏi cuốn tôm thịt",
    "description": "Món gỏi cuốn kiểu Việt Nam.",
    "categoryId": str(uuid.uuid4()),
    "prepTimeMinutes": 20,
    "cookTimeMinutes": 0,
    "servings": 4,
    "difficulty": 1,
    "instructions": "Chuẩn bị nguyên liệu trước khi cuốn.",
    "nutrition": {"calories": 210, "protein": 8},
}


def test_create_recipe_request_accepts_agreed_contract() -> None:
    request = RecipeCreateRequest.model_validate(VALID_PAYLOAD)

    assert request.title == "Gỏi cuốn tôm thịt"
    assert request.category_id == uuid.UUID(VALID_PAYLOAD["categoryId"])
    assert request.cook_time_minutes == 0


@pytest.mark.parametrize("field", ["authorId", "slug", "status", "steps", "ingredients"])
def test_create_recipe_rejects_fields_outside_base_contract(field: str) -> None:
    payload = {**VALID_PAYLOAD, field: "not-client-controlled"}

    with pytest.raises(ValidationError):
        RecipeCreateRequest.model_validate(payload)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("title", "bad"),
        ("prepTimeMinutes", 0),
        ("cookTimeMinutes", -1),
        ("servings", 0),
        ("difficulty", 5),
    ],
)
def test_invalid_recipe_fields_are_rejected(field: str, value: object) -> None:
    payload = {**VALID_PAYLOAD, field: value}

    with pytest.raises(ValidationError):
        RecipeCreateRequest.model_validate(payload)


def test_negative_nutrition_is_rejected() -> None:
    payload = {**VALID_PAYLOAD, "nutrition": {"calories": -1}}

    with pytest.raises(ValidationError):
        RecipeCreateRequest.model_validate(payload)


def test_openapi_contains_create_recipe_contract() -> None:
    operation = app.openapi()["paths"]["/api/v1/recipes"]["post"]

    assert operation["responses"].keys() >= {"201", "401", "403", "409", "422"}
    request_schema = operation["requestBody"]["content"]["application/json"]["schema"]
    assert request_schema["$ref"].endswith("/RecipeCreateRequest")
    for status_code in ("401", "403", "409", "422"):
        content = operation["responses"][status_code]["content"]
        assert content["application/json"]["schema"]["$ref"].endswith(
            "/ProblemDetails"
        )
