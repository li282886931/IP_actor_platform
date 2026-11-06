def json_ok(data):
    return {"code": 0, "data": data, "message": "ok"}


def json_error(message, code=1):
    return {"code": code, "data": None, "message": message}
