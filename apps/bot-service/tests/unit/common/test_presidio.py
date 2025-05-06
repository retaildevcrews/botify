import unittest

from pydantic import SecretStr
from common.presidio.anonymizer import Anonymizer, Deanonymizer
from app.settings import EnvironmentConfig, AppSettings
import secrets
import string
import time
import logging

logging.getLogger().setLevel(logging.DEBUG)
start_time = time.time()
initialization_time = time.time()-start_time
print(f"Initialization time: {initialization_time} seconds")
app_settings = AppSettings(load_environment_config=False)

data = [
    "My name is Johan Lunastis I am son of John Smith Lunastis who is found at 3333 Cranberry lane, New York, NY 10001. My phone number is 212-555-5555, my dl is TX-16565000 and my email is jolu@gen.com",
    "I have a new credit card and its number is: 4111 1111 1111 1111. I also have a US passport with number: 123456789",
    "We are now looking at new locations to move to. We are considering moving to 1234 Elm Street, Springfield, IL 62701. We are also considering moving to 1234 Elm Street, Springfield, IL 62701",
]


def random_secret_string(length: int = 32):
    return SecretStr(''.join(secrets.choice(string.ascii_uppercase + string.digits)
                             for i in range(length)))


class TestStringMethods(unittest.TestCase):
    anonymizer = Anonymizer(pii_entitities=app_settings.anonymizer_entities)

    def test_presidio_anonymizer(self):
        for text in data:
            call_start_time = time.time()
            anonymized_text = self.anonymizer.anonymize_text(text)
            end_time = time.time()
            ellapsed_time = end_time-call_start_time
            print(f"Anonymized text: {anonymized_text} in {
                  ellapsed_time} seconds")


class TestEncrypt(unittest.TestCase):
    anonymizer = Anonymizer(pii_entitities=app_settings.anonymizer_entities,
                            mode="ENCRYPT", crypto_key=random_secret_string())

    def test_presidio_anonymizer(self):
        for text in data:
            call_start_time = time.time()
            anonymized_text = self.anonymizer.anonymize_text(text)
            end_time = time.time()
            ellapsed_time = end_time-call_start_time
            print(f"Encrypted text: {anonymized_text} in {
                  ellapsed_time} seconds")


class TestDecrypt(unittest.TestCase):
    anonymizer = Anonymizer(pii_entitities=app_settings.anonymizer_entities,
                            mode="ENCRYPT", crypto_key=random_secret_string())
    deanonymizer = Deanonymizer(
        pii_entities=app_settings.anonymizer_entities, crypto_key=anonymizer.anonymizer_crypto_key)

    def test_presidio_anonymizer(self):
        for text in data:
            call_start_time = time.time()
            anonymized_text = self.anonymizer.anonymize_text(text).to_json()
            deanonymized_text = self.deanonymizer.deanonymize_result(
                anonymized_text)
            end_time = time.time()
            ellapsed_time = end_time-call_start_time
            print(f"Deanonymized text: {deanonymized_text} in {
                  ellapsed_time} seconds")


if __name__ == "__main__":
    unittest.main()
