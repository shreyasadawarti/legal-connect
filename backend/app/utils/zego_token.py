"""ZEGOCLOUD room-join token generation (token04).

Ported from the official zego_server_assistant token04 implementation
(https://github.com/ZEGOCLOUD/zego_server_assistant). The ServerSecret is
read from settings and must never be returned to any client.
"""

import base64
import json
import secrets
import struct
import time
from dataclasses import dataclass

from Crypto.Cipher import AES

ERROR_CODE_SUCCESS = 0
ERROR_CODE_APP_ID_INVALID = 1
ERROR_CODE_USER_ID_INVALID = 3
ERROR_CODE_SECRET_INVALID = 5
ERROR_CODE_EFFECTIVE_TIME_IN_SECONDS_INVALID = 6


@dataclass
class TokenInfo:
    token: str
    error_code: int
    error_message: str


def _pkcs5_pad(text: str) -> str:
    block_size = 16
    padding = block_size - len(text.encode("utf-8")) % block_size
    return text + chr(padding) * padding


def generate_token04(
    app_id: int,
    user_id: str,
    secret: str,
    effective_time_in_seconds: int,
    payload: str,
) -> TokenInfo:
    if not isinstance(app_id, int) or app_id == 0:
        return TokenInfo("", ERROR_CODE_APP_ID_INVALID, "appID invalid")
    if not isinstance(user_id, str) or user_id == "":
        return TokenInfo("", ERROR_CODE_USER_ID_INVALID, "userID invalid")
    if not isinstance(secret, str) or len(secret) != 32:
        return TokenInfo("", ERROR_CODE_SECRET_INVALID, "secret must be a 32 byte string")
    if not isinstance(effective_time_in_seconds, int) or effective_time_in_seconds <= 0:
        return TokenInfo(
            "", ERROR_CODE_EFFECTIVE_TIME_IN_SECONDS_INVALID, "effective_time_in_seconds invalid"
        )

    create_time = int(time.time())
    expire_time = create_time + effective_time_in_seconds
    nonce = secrets.randbits(31)

    token_data = {
        "app_id": app_id,
        "user_id": user_id,
        "nonce": nonce,
        "ctime": create_time,
        "expire": expire_time,
        "payload": payload,
    }
    plain_text = json.dumps(token_data, separators=(",", ":"), ensure_ascii=False)

    iv = "".join(secrets.choice("0123456789abcdefghijklmnopqrstuvwxyz") for _ in range(16))
    cipher = AES.new(secret.encode("utf-8"), AES.MODE_CBC, iv.encode("utf-8"))
    encrypted = cipher.encrypt(_pkcs5_pad(plain_text).encode("utf-8"))

    result = bytearray(len(encrypted) + 28)
    result[0:8] = struct.pack("!q", expire_time)
    result[8:10] = struct.pack("!h", len(iv))
    result[10:10 + len(iv)] = iv.encode("utf-8")
    result[26:28] = struct.pack("!h", len(encrypted))
    result[28:28 + len(encrypted)] = encrypted

    token = "04" + base64.b64encode(bytes(result)).decode()
    return TokenInfo(token, ERROR_CODE_SUCCESS, "success")
