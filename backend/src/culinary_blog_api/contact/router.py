from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from .schemas import ContactCreate, ContactReceipt
from .service import submit_contact

router = APIRouter(prefix="/api/v1/contact", tags=["contact"])


@router.post("", response_model=ContactReceipt, status_code=status.HTTP_202_ACCEPTED)
async def post_contact(
    data: ContactCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ContactReceipt:
    """Store a public contact message for durable asynchronous delivery."""
    return await submit_contact(session, data)
