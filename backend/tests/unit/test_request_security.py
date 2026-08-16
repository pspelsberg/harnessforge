from app.core.security.request import valid_host,valid_origin
def test_request_validation_is_exact():
 assert valid_host("127.0.0.1:8000") and not valid_host("127.0.0.1:9999") and not valid_host("127.0.0.1@evil")
 assert valid_origin(None) and not valid_origin("https://evil.example")
