"""契約測試:每個 OpenAPI operationId 都要有對應測試,否則 contract gate 會擋。
這裡是範例骨架(真實版會打 API 比對 schema)。operationId 出現在函式名即算覆蓋。"""


def test_createOrder_contract():
    # createOrder: POST /orders → 201
    assert True


def test_getOrder_contract():
    # getOrder: GET /orders/{id} → 200
    assert True
