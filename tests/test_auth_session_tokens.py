import unittest
from types import SimpleNamespace

import reply_server


class AuthSessionTokenTest(unittest.TestCase):
    def setUp(self):
        self._original_tokens = dict(reply_server.SESSION_TOKENS)
        self._original_revoked = set(getattr(reply_server, "REVOKED_SESSION_TOKENS", set()))
        reply_server.SESSION_TOKENS.clear()
        if hasattr(reply_server, "REVOKED_SESSION_TOKENS"):
            reply_server.REVOKED_SESSION_TOKENS.clear()

    def tearDown(self):
        reply_server.SESSION_TOKENS.clear()
        reply_server.SESSION_TOKENS.update(self._original_tokens)
        if hasattr(reply_server, "REVOKED_SESSION_TOKENS"):
            reply_server.REVOKED_SESSION_TOKENS.clear()
            reply_server.REVOKED_SESSION_TOKENS.update(self._original_revoked)

    def test_login_token_survives_process_memory_loss(self):
        token = reply_server.create_session_token(
            {
                "user_id": 1,
                "username": "admin",
                "is_admin": True,
            }
        )
        reply_server.SESSION_TOKENS.clear()

        user_info = reply_server.verify_token(SimpleNamespace(credentials=token))

        self.assertIsNotNone(user_info)
        self.assertEqual(user_info["user_id"], 1)
        self.assertEqual(user_info["username"], "admin")
        self.assertTrue(user_info["is_admin"])
        self.assertIn(token, reply_server.SESSION_TOKENS)


if __name__ == "__main__":
    unittest.main()
