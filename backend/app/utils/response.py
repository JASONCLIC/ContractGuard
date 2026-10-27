from flask import jsonify, g


def success(data=None, message="success", code=0, status=200):
    request_id = getattr(g, "request_id", None)
    payload = {
        "code": code,
        "message": message,
        "data": data,
        "request_id": request_id,
    }
    return jsonify(payload), status


def fail(code, message, status=400, data=None):
    request_id = getattr(g, "request_id", None)
    payload = {
        "code": code,
        "message": message,
        "data": data,
        "request_id": request_id,
    }
    return jsonify(payload), status
