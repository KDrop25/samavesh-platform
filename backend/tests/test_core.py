from datetime import UTC

import pytest
from cryptography.exceptions import InvalidTag
from sqlalchemy import Column, Integer, MetaData, Table, insert, select, text

from app.crypto import EncryptedJSON, EncryptedText, decrypt, encrypt
from app.db import UTCDateTime, make_engine, utcnow


def test_encrypt_roundtrip_and_tamper_detection():
    blob = encrypt(b"scribe needed")
    assert b"scribe" not in blob
    assert decrypt(blob) == b"scribe needed"
    assert encrypt(b"scribe needed") != blob  # fresh nonce every time
    with pytest.raises(InvalidTag):
        decrypt(blob[:-1] + bytes([blob[-1] ^ 1]))


def test_encrypted_columns_store_ciphertext_and_utc_is_aware():
    engine = make_engine("sqlite://")
    t = Table(
        "t",
        MetaData(),
        Column("id", Integer, primary_key=True),
        Column("needs", EncryptedText),
        Column("cats", EncryptedJSON),
        Column("at", UTCDateTime),
    )
    t.create(engine)
    with engine.begin() as conn:
        conn.execute(insert(t).values(needs="low vision", cats=["blindness"], at=utcnow()))
        row = conn.execute(select(t)).one()
        raw = conn.execute(text("SELECT needs, cats FROM t")).one()
    assert (row.needs, row.cats) == ("low vision", ["blindness"])
    assert row.at.tzinfo is UTC
    assert b"low vision" not in raw.needs and b"blindness" not in raw.cats
