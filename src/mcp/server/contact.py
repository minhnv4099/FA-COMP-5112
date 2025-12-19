#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
from __future__ import annotations

import logging
import re
import json
import pickle
from typing import Any, Optional, AsyncIterator, Literal
from typing_extensions import Annotated, override
from contextlib import asynccontextmanager
from pydantic import BaseModel, field_validator, model_validator, Field
from mcp.server.fastmcp.server import FastMCP, Context
from dataclasses import dataclass
from pathlib import Path

from src.mcp.server.utils import require_human_confirm, HumanAbortedException, NeedHumanConfirmException


logger = logging.getLogger("ContactManager")
DEFAULT_CONTACT_FILE = "data/contacts.json"
ValidFields = Literal[
    'name',
    'age',
    'phone_number',
    'address',
    'email',
    'linkedin',
    'facebook',
    'location',
    'job',
    'company'
]


class ContactRecord(BaseModel):
    name: str = Field(..., description="Name")
    """Name of the person."""
    age: Optional[int] = Field(None, description="Age")
    """Age of the person."""
    phone_number: Optional[str] = Field(None, description="Phone number")
    """Phone number of the person."""
    address: Optional[str] = Field(None, description="Address")
    """Address of the person."""
    email: Optional[str] = Field(None, description="Email address")
    "Personal email."
    linkedin: Optional[str] = Field(None, description="Linkined link")
    """Link to LinkedIn website."""
    facebook: Optional[str] = Field(None, description="Facebook link")
    """Like to Facebook."""
    location: Optional[str] = Field(None, description="Current location")
    """The current location."""
    job: Optional[list[str]] = Field(None, description="Current jobs")
    """Jobs."""
    company: Optional[list[str]] = Field(None, description="Companies")
    """Companies working."""

    @field_validator('name', mode="before")
    @classmethod
    def _validate_name(cls, value: str) -> str:
        return value.title()

    @field_validator('email', mode="before")
    @classmethod
    def _check_email(cls, value: str | None) -> str | None:
        """Check if email is valid.

        Return None if not valid.
        """
        if value is None:
            return value

        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        match = re.match(
            pattern=pattern,
            string=value,
        )

        if not match:
            logger.warning(f"The given email isn't valid: {value!r}. Set None by default")
            return None

        return value

    @field_validator('phone_number', mode="before")
    @classmethod
    def _validate_phone_number(cls, value: str | None) -> str | None:
        """Check if phone number is valid.

        Return None if not valid.
        """
        if value is None:
            return value

        pattern = r"^\s*(?:\+?(\d{1,3}))?[-. (]*(\d{3})[-. )]*(\d{3})[-. ]*(\d{4})(?: *x(\d+))?\s*$"
        if not re.match(pattern, value):
            logger.warning(f"The given phone number isn't valid: {value!r}. Set None by default")
            return None

        return value

    @model_validator(mode='before')
    @classmethod
    def _validate_model_before(cls, value: dict[str, Any]):
        for k in value:
            try:
                value[k] = value['k'].strip()
            except:
                continue

        return value

    @override
    def __setattr__(self, key: str, value: Any):
        if key == 'name':
            value = value.title()

        super().__setattr__(key, value)

    @override
    def __eq__(self, other: ContactRecord):
        """Compare with self with other's name, phone_number and email."""
        exist_name = other.name and other.name == self.name
        exist_email = other.email and other.email == self.email
        exist_number = other.phone_number and other.phone_number == self.phone_number

        return exist_name or exist_email or exist_number

    def get_serializable(self) -> dict[str, Any]:
        """Get a dictionary of data ready to serialize (save)."""
        return self.model_dump(by_alias=True)


@dataclass(kw_only=True)
class ContactManager:
    contacts: Annotated[list[ContactRecord], "List of contacts."]
    """List of contacts at that time."""

    def __contains__(self, item: ContactRecord) -> bool:
        """Check if the item is already in contacts.

        The logic is defined in special method `__eq__` in class `ContactRecord`.
        """
        for con in self.contacts:
            if con == item:
                return True

        return False

    def _checking_existing(self, contact: ContactRecord) -> bool:
        """Check if essential information of contact exists.

        Args:
            contact: Contact need to check.

        Returns:
            Type:
                - `True`: If exist.
                - `False`: Otherwise.
        """
        return contact in self

    def add(self, contact: ContactRecord) -> bool:
        """Add a new contact.

        Args:
            contact: Contact want to add.

        Returns:
            Type:
                - `True`: If added successfully.
                - `False`: Otherwise (essential fields exist).
        """
        if not self._checking_existing(contact):
            self.contacts.append(contact)
            return True

        return False

    def look_up(self, name: str) -> ContactRecord | None:
        """Look up the contact based on name.

        Args:
            name: Name of contact. Exactly name.

        Returns:
            Type:
                - `Contact`: If found contact.
                - `None`: Otherwise.
        """
        name = name.strip()
        for con in self.contacts:
            if con.name == name:
                return con

        return None

    def update(self, contact: ContactRecord, field: str, value: Any) -> tuple[bool, Any]:
        """Update contact's filed to value.

        Args:
            contact: Contact to update.
            field: Field to update.
            value: Value to update.

        Returns:
            Type:
                - `(True, old_value)`
                - `(False, None)`
        """
        if self._checking_existing(contact):
            old_value = contact.__getattribute__(field)
            contact.__setattr__(field, value)
            return True, old_value

        return False, None

    def remove(self, contact: ContactRecord):
        """Remove the contact from list.

        Returns:
            Either:
                - `True`: If removed.
                - `False`: Otherwise.
        """
        try:
            self.contacts.remove(contact)
            return True
        except Exception:
            return False

    def get_contacts(self):
        """Get available contacts sort by name."""
        return sorted(self.contacts, key=lambda x: x.name, reverse=True)

    @classmethod
    def load_contacts(cls, import_file: Optional[str] = None) -> ContactManager:
        """Load contacts from file into contact managers."""
        import_file = import_file or DEFAULT_CONTACT_FILE

        try:
            logger.info(f"Try import contacts from {import_file!r}")
            if import_file.endswith(".json"):
                with open(import_file, "r") as f:
                    contacts = json.load(f)
            elif import_file.endswith(".pkl"):
                with open(import_file, 'rb') as f:
                    contacts = pickle.load(f)
            else:
                contacts = []

            contacts = [ContactRecord(**conc) for conc in contacts]
            return ContactManager(contacts=contacts)
        except Exception as e:
            logger.error(f"Error importing contacts: {e}")
            return ContactManager(contacts=[])

    def serialize(self, save_file: Optional[str] = None) -> Path:
        """Serialize (save) contacts into a file."""
        save_file = save_file or DEFAULT_CONTACT_FILE

        if self.contacts:
            serializable_contacts = [conc.get_serializable() for conc in self.contacts]
            if save_file.endswith(".json"):
                with open(save_file, "w") as f:
                    json.dump(serializable_contacts, fp=f, indent=3)
            elif save_file.endswith(".pkl"):
                with open(save_file, 'wb') as f:
                    pickle.dump(serializable_contacts, f)

            logger.info(f"Export contacts to {save_file!r}")

        return Path(save_file)


@asynccontextmanager
async def server_lifespan(server: FastMCP) -> AsyncIterator[dict[str, Any]]:
    # Setting something here
    try:
        yield {}
    finally:
        global mcp_server, contact_manager

        if contact_manager:
            contact_manager.serialize()

        if mcp_server:
            logger.info(f'MCP Server {mcp_server.name!r} shut down.')

mcp_server = FastMCP(
    name="Contact Manager",
    lifespan=server_lifespan
)

contact_manager: Optional[ContactManager] = None


def get_contact_manager():
    """Get or create contact manager."""
    global contact_manager

    if contact_manager is None:
        contact_manager = ContactManager.load_contacts()

    return contact_manager


@mcp_server.tool()
def get_contacts(file_path: Optional[str] = None):
    """Get current contacts or contacts from a file.
    Useful to get when you need to know name, age, job, email address, (demographic information) of someone.

    Args:
        file_path: File containing contacts data. Set None when no mentioned any source file.
    """
    try:
        manager = get_contact_manager()

        if file_path:
            contacts = ContactManager.load_contacts(file_path).get_contacts()
        else:
            contacts = manager.get_contacts()

        logger.info(f"There are {len(contacts)} contacts.")
        return (f"Existing contacts:\n"
                f"{contacts}")
    except Exception as e:
        msg = f"Error getting current contacts: {e}"
        logger.error(msg)
        return msg


@mcp_server.tool()
def add_contact(contact: ContactRecord):
    """Add/Create a new contact.

    Args:
        contact: A new contact to add.
    """
    try:
        manager = get_contact_manager()
        is_added = manager.add(contact)

        if is_added:
            msg = f"Successfully! Added contact with name {contact.name!r}."
        else:
            msg = f"Cannot add contact as some essential values exist."

        logger.info(msg)
        return msg
    except Exception as e:
        msg = f"Error adding contact: {e}"
        logger.error(msg)
        return msg


@mcp_server.tool()
def update(name: str, field: ValidFields, value: Any):
    """Update field of contact with name to new value.

    Args:
        name: Name of contact.
        field: Field need to update (e.g. address, name, jobs...)
        value: Value update to field.
    """
    try:
        manager = get_contact_manager()
        contact = manager.look_up(name)

        if contact is None:
            existing_names = [con.name for con in manager.get_contacts()]
            msg = f"No found contact named {name!r}, existing name: {existing_names}"
        else:
            is_updated, old_value = manager.update(contact, field=field, value=value)
            if is_updated:
                msg = f"Successfully! Updated {field!r} of {name!r} from {old_value!r} to {value!r}."
            else:
                msg = f"Failed update {field!r} of {name!r} to {value!r}."

        logger.info(msg)
        return msg
    except Exception as e:
        msg = f"Error updating {field!r} of {name!r}: {e}"
        logger.error(msg)
        return msg


@mcp_server.tool()
def remove(name: str, aux_kwargs: Optional[dict[str, Any]] = None):
    """Remove contact based on name.
    If the given name was not perfect, freely get current contacts to get the most matched name.

    Args:
        name: Exact name.
    """
    try:
        manager = get_contact_manager()
        contact = manager.look_up(name)

        if contact is None:
            existing_names = [con.name for con in manager.get_contacts()]
            msg = f"No found contact named {name!r}, existing name: {existing_names}"
            logger.info(msg)
            return msg

        asking_prompt = f"""
Confirm remove contact:
    ---------------------------
{json.dumps(contact.model_dump(), indent=7)}
    ---------------------------
Proceed this operation? (y/n): """.lstrip()

        require_human_confirm(asking_prompt=asking_prompt, kwargs=aux_kwargs)

        is_removed = manager.remove(contact)

        if is_removed:
            msg = f"Successfully! Removed contact name {name!r}."
        else:
            msg = f"Failed remove contact name {name!r}."

        logger.info(msg)
        return msg
    except NeedHumanConfirmException as e:
        return e.kwargs
    except HumanAbortedException as e:
        return str(e)
    except Exception as e:
        msg = f"Error removing contact name {name!r}: {e}"
        logger.error(msg)
        return msg


def main():
    transport: Literal["stdio", "sse", "streamable-http"] = "stdio"
    logger.info(f'MCP Server Contact Manager is running on transport {transport!r}.')
    mcp_server.run(transport=transport)


if __name__ == '__main__':
    main()
