from biogestor.core.security import hash_password, verify_password


def test_hash_and_verify_password() -> None:
    password = "super-secret"
    hashed = hash_password(password)

    assert hashed != password
    assert verify_password(password, hashed)
    assert not verify_password("wrong-password", hashed)

