import pytest
from app.core.security.body_limit import BodyLimitMiddleware
def test_body_limit_constructs(): assert BodyLimitMiddleware(lambda s,r,se:None,10).max_bytes==10
