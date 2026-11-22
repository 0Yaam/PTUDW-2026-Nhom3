import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from .model import ContactMessage
from .schemas import ContactCreate, ContactReceipt

logger = structlog.get_logger()


async def submit_contact(session: AsyncSession, data: ContactCreate) -> ContactReceipt:
    contact = ContactMessage(
        full_name=data.full_name,
        email=data.email,
        message=data.message,
    )
    session.add(contact)
    await session.commit()
    logger.info("contact_message_accepted", contact_id=str(contact.id))
    return ContactReceipt(id=contact.id)
