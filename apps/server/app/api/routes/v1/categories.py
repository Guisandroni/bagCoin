"""REST routes for BagCoin category CRUD.

Requires API Key authentication (same as webhook endpoints).
Phone number identifies the BagCoin user whose categories are being managed.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.agents.persistence import (
    create_category,
    delete_category,
    list_categories,
    rename_category,
)
from app.api.deps import CurrentUser, DBSession
from app.api.deps import verify_api_key as require_api_key
from app.core.exceptions import NotFoundError, ValidationError
from app.services.category_rest import (
    create_category_for_user,
    delete_category_for_user,
    fallback_default_categories,
    list_categories_for_user,
    update_category_for_user,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/categories", tags=["categories"])


class WebCategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    type: str | None = Field(default=None, max_length=30)
    color: str | None = Field(default=None, max_length=30)


class WebCategoryUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    type: str | None = Field(default=None, max_length=30)
    color: str | None = Field(default=None, max_length=30)


@router.get("", response_model=list[dict])
async def get_web_categories(
    current_user: CurrentUser,
    db: DBSession,
):
    """List categories for the authenticated web user."""
    try:
        return await list_categories_for_user(db, current_user)
    except Exception as exc:
        logger.exception("Error listing web categories for user %s", current_user.id)
        await db.rollback()
        return fallback_default_categories()


@router.post("", status_code=201)
async def add_web_category(
    current_user: CurrentUser,
    db: DBSession,
    body: WebCategoryCreate,
):
    """Create a category for the authenticated web user."""
    result = await create_category_for_user(db, current_user, body.name)
    if result is None:
        raise HTTPException(status_code=409, detail=f"Category '{body.name}' already exists")
    return result


@router.patch("/{category_id:int}")
async def update_web_category(
    category_id: int,
    current_user: CurrentUser,
    db: DBSession,
    body: WebCategoryUpdate,
):
    """Update a category owned by the authenticated web user."""
    try:
        return await update_category_for_user(db, current_user, category_id, body.name)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=409, detail=exc.message) from exc


@router.delete("/{category_id:int}", status_code=204)
async def delete_web_category(
    category_id: int,
    current_user: CurrentUser,
    db: DBSession,
):
    """Delete a category owned by the authenticated web user when it is unused."""
    try:
        await delete_category_for_user(db, current_user, category_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=409, detail=exc.message) from exc


@router.get("/", response_model=list[dict])
async def get_categories(
    phone_number: str = Query(..., description="BagCoin user phone number"),
    api_key: str = Depends(require_api_key),
):
    """List all categories for a BagCoin user."""
    try:
        cats = list_categories(phone_number)
        return cats
    except Exception as e:
        logger.error(f"Error listing categories: {e}")
        raise HTTPException(status_code=500, detail="Error listing categories")


@router.post("/", status_code=201)
async def add_category(
    phone_number: str = Query(..., description="BagCoin user phone number"),
    name: str = Query(..., description="Category name"),
    api_key: str = Depends(require_api_key),
):
    """Create a new category for a BagCoin user."""
    try:
        result = create_category(phone_number, name)
        if result is None:
            raise HTTPException(status_code=409, detail=f"Category '{name}' already exists")
        return {"message": f"Category '{name}' created", "category": result}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating category: {e}")
        raise HTTPException(status_code=500, detail="Error creating category")


@router.patch("/{old_name}")
async def update_category(
    old_name: str,
    phone_number: str = Query(..., description="BagCoin user phone number"),
    new_name: str = Query(..., description="New category name"),
    api_key: str = Depends(require_api_key),
):
    """Rename a category for a BagCoin user."""
    try:
        if rename_category(phone_number, old_name, new_name):
            return {"message": f"Category '{old_name}' renamed to '{new_name}'"}
        raise HTTPException(status_code=404, detail=f"Category '{old_name}' not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error renaming category: {e}")
        raise HTTPException(status_code=500, detail="Error renaming category")


@router.delete("/{name}")
async def remove_category(
    name: str,
    phone_number: str = Query(..., description="BagCoin user phone number"),
    api_key: str = Depends(require_api_key),
):
    """Delete a category for a BagCoin user."""
    try:
        if delete_category(phone_number, name):
            return {"message": f"Category '{name}' deleted"}
        raise HTTPException(status_code=404, detail=f"Category '{name}' not found or is default")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting category: {e}")
        raise HTTPException(status_code=500, detail="Error deleting category")
