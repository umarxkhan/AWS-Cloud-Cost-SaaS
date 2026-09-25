import json


def gw(method, path, sub=None, query=None, body=None, path_params=None, claims=None):
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
    return event


def call(method, path, sub=None, **kw):
    from api.handler import lambda_handler

    return lambda_handler(gw(method, path, sub=sub, **kw))


def body(resp):
    return json.loads(resp["body"])
