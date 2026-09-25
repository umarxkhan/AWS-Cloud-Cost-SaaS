import json

import jwtkit


def gw(method, path, sub=None, query=None, body=None, path_params=None, claims=None, token=None):
    claims = dict(claims) if claims else {}
    if sub:
        claims["sub"] = sub
    event = {
        "httpMethod": method,
        "path": path,
        "queryStringParameters": query or {},
        "pathParameters": path_params or {},
        "requestContext": {"authorizer": {"claims": claims}},
    }
    if body is not None:
        event["body"] = json.dumps(body)
    headers = {}
    if token:
        headers["Authorization"] = "Bearer " + token
    elif sub:
        headers["Authorization"] = "Bearer " + jwtkit.mint(sub)
    if headers:
        event["headers"] = headers
    return event


def call(method, path, sub=None, token=None, **kw):
    from api.handler import lambda_handler

    return lambda_handler(gw(method, path, sub=sub, token=token, **kw))


def body(resp):
    return json.loads(resp["body"])
