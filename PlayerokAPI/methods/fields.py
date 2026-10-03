"""Наборы полей GraphQL, общие для запросов и подписок.

Подписка обязана просить ровно те же поля, что и запрос, иначе модель
из события окажется беднее модели из выборки.
"""

from __future__ import annotations

__all__ = [
    "CHAT",
    "DEAL",
    "ITEM",
    "ITEM_PROFILE",
    "MESSAGE",
    "PAGE_INFO",
    "TESTIMONIAL",
    "TRANSACTION",
    "USER",
]

PAGE_INFO = "startCursor endCursor hasNextPage hasPreviousPage"

USER = "id username avatarURL role isOnline"

MESSAGE = f"""
    id text createdAt deletedAt isRead isEdited isSuspicious
    isBulkMessaging isAutoResponse event imageLinks plTokenAmount
    file {{ id url }} images {{ id url }}
    user {{ {USER} }}
    eventByUser {{ id username }} eventToUser {{ id username }}
    buttons {{ text type url }}
    deal {{ id status direction hasProblem }}
"""

CHAT = f"""
    id type status unreadMessagesCounter bookmarked isTextingAllowed
    startedAt finishedAt
    lastMessage {{ id text createdAt isRead event user {{ id username }} }}
    participants {{ {USER} }}
    owner {{ {USER} }} agent {{ {USER} }}
    deals {{ id status direction hasProblem }}
"""

DEAL = """
    id status prevStatus statusDescription direction hasProblem obtaining
    commentFromBuyer isAutomated createdAt completedAt statusExpirationDate
    item { __typename id name price }
    user { id username avatarURL }
    completedBy { id username }
    chat { id }
    transaction { id value fee status operation providerId createdAt }
    testimonial { id rating text status }
"""

TRANSACTION = """
    id operation direction providerId status statusDescription
    statusExpirationDate value fee createdAt completedAt isSuspicious
    user { id username avatarURL }
"""

TESTIMONIAL = """
    id status text rating createdAt updatedAt
    deal { id status direction }
    creator { id username avatarURL }
    user { id username avatarURL }
"""

ITEM_PROFILE = """
    __typename id slug name price rawPrice status priority
    game { id slug name type }
    category { id slug name }
    user { id username avatarURL }
    attachment { id url }
"""

ITEM = """
    __typename id slug name description price rawPrice status priority
    game { id slug name type }
    category { id slug name }
    user { id username avatarURL }
    attachments { id url }
"""
