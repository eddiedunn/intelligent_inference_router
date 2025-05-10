import pytest
import os
from router import secret_scrubber

# Set up environment variables for testing
def setup_module(module):
    os.environ['TEST_SECRET_KEY'] = 'supersecretkey1234567890'
    os.environ['NOT_A_CONF_XYZ123'] = 'justconfig' # Unique name, does not match secret patterns
    os.environ['JWT_TOKEN'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c'


def test_env_secret_detection():
    secrets = secret_scrubber.gather_env_secrets(debug=True)
    print("[DEBUG] Gathered secrets:", secrets)
    assert 'supersecretkey1234567890' in secrets
    assert os.environ['NOT_A_CONF_XYZ123'] not in secrets
    assert os.environ['JWT_TOKEN'] in secrets  # JWT_TOKEN value is detected as a secret due to env var name


def test_regex_secret_detection():
    text = 'Here is a JWT: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c'
    found = secret_scrubber.find_secrets(text, set())
    assert any('eyJhbGciOiJIUzI1Ni' in s for s in found)


def test_entropy_detection():
    high_entropy = 'z8J2l1kqP3s9v4tX7w6e5r8y2u1o0p9m'
    low_entropy = 'hellohellohello'
    assert secret_scrubber.shannon_entropy(high_entropy) > 4.0
    assert secret_scrubber.shannon_entropy(low_entropy) < 3.0
    found = secret_scrubber.find_secrets(high_entropy, set())
    assert high_entropy in found
    found = secret_scrubber.find_secrets(low_entropy, set())
    assert low_entropy not in found


def test_scrub_data():
    secrets = secret_scrubber.gather_env_secrets()
    input_data = {
        'prompt': f"My key is {os.environ['TEST_SECRET_KEY']} and my token is eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c",
        'list': [os.environ['TEST_SECRET_KEY'], 'no_secret_here', 'z8J2l1kqP3s9v4tX7w6e5r8y2u1o0p9m']
    }
    scrubbed = secret_scrubber.scrub_data(input_data, secrets)
    assert 'REDACTED' in scrubbed['prompt']
    assert 'REDACTED' in scrubbed['list'][0]
    assert 'REDACTED' in scrubbed['list'][2]
    assert 'no_secret_here' in scrubbed['list']
