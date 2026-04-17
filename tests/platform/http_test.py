from application.platform.http import oauth1_sign
from application.platform.processes import on_separate_process_async


async def test_oauth1_sign_produces_consistent_signature():
    """Same inputs must always produce the same signature."""
    sig1 = oauth1_sign(
        "POST", "https://api.twitter.com/2/tweets",
        {"oauth_consumer_key": "key123", "oauth_nonce": "abc", "oauth_timestamp": "1000", "oauth_token": "tok123",
         "oauth_signature_method": "HMAC-SHA1", "oauth_version": "1.0"},
        "consumer_secret", "token_secret",
    )
    sig2 = oauth1_sign(
        "POST", "https://api.twitter.com/2/tweets",
        {"oauth_consumer_key": "key123", "oauth_nonce": "abc", "oauth_timestamp": "1000", "oauth_token": "tok123",
         "oauth_signature_method": "HMAC-SHA1", "oauth_version": "1.0"},
        "consumer_secret", "token_secret",
    )
    assert sig1 == sig2
    assert len(sig1) > 0


async def test_oauth1_sign_changes_with_different_secrets():
    """Different secrets must produce different signatures."""
    params = {"oauth_consumer_key": "key", "oauth_nonce": "n", "oauth_timestamp": "1", "oauth_token": "t",
              "oauth_signature_method": "HMAC-SHA1", "oauth_version": "1.0"}
    sig1 = oauth1_sign("POST", "https://example.com", params, "secret_a", "token_a")
    sig2 = oauth1_sign("POST", "https://example.com", params, "secret_b", "token_b")
    assert sig1 != sig2


async def test_oauth1_sign_changes_with_different_methods():
    """GET and POST on the same URL must produce different signatures."""
    params = {"oauth_consumer_key": "key", "oauth_nonce": "n", "oauth_timestamp": "1", "oauth_token": "t",
              "oauth_signature_method": "HMAC-SHA1", "oauth_version": "1.0"}
    sig_get = oauth1_sign("GET", "https://example.com", params, "s", "t")
    sig_post = oauth1_sign("POST", "https://example.com", params, "s", "t")
    assert sig_get != sig_post


async def test_oauth1_sign_is_base64_encoded():
    """Signature must be valid base64 producing 20 bytes (SHA1)."""
    import base64
    sig = oauth1_sign(
        "GET", "https://example.com",
        {"oauth_consumer_key": "k", "oauth_nonce": "n", "oauth_timestamp": "1", "oauth_token": "t",
         "oauth_signature_method": "HMAC-SHA1", "oauth_version": "1.0"},
        "cs", "ts",
    )
    decoded = base64.b64decode(sig)
    assert len(decoded) == 20


async def test_oauth1_request_sends_authorization_header():
    """The request must include an OAuth Authorization header with all required params."""
    def isolated():
        from application.platform import http

        def run(url):
            return http.oauth1_request(
                method="POST",
                url=f"{url}/2/tweets",
                body='{"text": "test"}',
                consumer_key="ck", consumer_secret="cs",
                access_token="at", access_token_secret="ats",
            )

        def validate(received):
            auth = received.get("headers", {}).get("Authorization", "")
            assert auth.startswith("OAuth "), f"Expected OAuth header, got: {auth}"
            for param in ["oauth_consumer_key", "oauth_nonce", "oauth_signature_method",
                          "oauth_timestamp", "oauth_token", "oauth_version", "oauth_signature"]:
                assert param in auth, f"Missing {param} in Authorization header"

        http.assert_call(run=run, validate=validate)

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
