import pytest
from fastapi import HTTPException

from src.Helper.ProductHelper import ProductHelper
from src.Model.ProductModel import ProductModel
from src.Model.DeleteProductModel import DeleteProductModel


# ================== FAKES DE CONEXÃO/CURSOR ==================


class FakeCursor:
    def __init__(self):
        # para create_product (fetchone)
        self.fetchone_results = []
        # para list_products (fetchall)
        self.fetchall_results = []
        # para delete_product (rowcount)
        self.rowcount = 0

        self.executed = []  # guarda os SQLs executados + params
        self.closed = False
        self.raise_on_execute: Exception | None = None

    def execute(self, sql, params=None):
        if self.raise_on_execute:
            raise self.raise_on_execute
        self.executed.append((sql, params))

    def fetchone(self):
        if self.fetchone_results:
            return self.fetchone_results.pop(0)
        return None

    def fetchall(self):
        return self.fetchall_results

    def close(self):
        self.closed = True


class FakeConnection:
    def __init__(self, cursor: FakeCursor):
        self._cursor = cursor
        self.committed = False
        self.rolled_back = False
        self.closed = False  # só pra conferência se alguém quiser usar

    def cursor(self):
        return self._cursor

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    # se em algum momento você passar a usar CloseConnection(connection)
    # com connection.close(), isso aqui garante que não quebre.
    def close(self):
        self.closed = True


# ================== TESTES DO create_product ==================


def test_create_product_success(monkeypatch):
    cursor = FakeCursor()
    # fetchone() deve retornar o id gerado
    cursor.fetchone_results = [(42,)]
    connection = FakeConnection(cursor)

    # mockar Connection() do helper
    monkeypatch.setattr(
        "src.Helper.ProductHelper.ProductHelper.Connection",
        lambda self: connection,
    )

    helper = ProductHelper()

    product = ProductModel(
        CauseId=10,
        Name="Camiseta Solidária",
        Description="Camiseta para arrecadar fundos",
        Value=79.9,
    )

    result = helper.create_product(product)

    # valida retorno
    assert result["message"] == "Created new product"
    assert result["ProductId"] == 42

    # valida que deu commit
    assert connection.committed is True
    # cursor foi fechado
    assert cursor.closed is True

    # checar que o INSERT foi executado
    assert len(cursor.executed) == 1
    sql, params = cursor.executed[0]
    assert "INSERT INTO produtos" in sql
    # params: (CauseId, Name, Description, Value, createdAt)
    assert params[0] == product.CauseId
    assert params[1] == product.Name
    assert params[2] == product.Description
    assert params[3] == product.Value
    # params[4] é o datetime gerado na hora → só checamos que não é None
    assert params[4] is not None


def test_create_product_error_rolls_back(monkeypatch):
    cursor = FakeCursor()
    cursor.raise_on_execute = Exception("DB error")
    connection = FakeConnection(cursor)

    monkeypatch.setattr(
        "src.Helper.ProductHelper.ProductHelper.Connection",
        lambda self: connection,
    )

    helper = ProductHelper()

    product = ProductModel(
        CauseId=10,
        Name="Produto com erro",
        Description="Vai falhar",
        Value=10.0,
    )

    with pytest.raises(HTTPException) as exc:
        helper.create_product(product)

    assert exc.value.status_code == 500
    assert "Error creating product" in exc.value.detail

    # deve ter dado rollback
    assert connection.rolled_back is True
    # cursor fechado
    assert cursor.closed is True


# ================== TESTES DO delete_product ==================


def test_delete_product_success(monkeypatch):
    cursor = FakeCursor()
    cursor.rowcount = 1  # indica que 1 linha foi deletada
    connection = FakeConnection(cursor)

    monkeypatch.setattr(
        "src.Helper.ProductHelper.ProductHelper.Connection",
        lambda self: connection,
    )

    helper = ProductHelper()
    delete_model = DeleteProductModel(ProductId=99)

    result = helper.delete_product(delete_model)

    assert result is True
    assert connection.committed is True
    assert cursor.closed is True

    # valida SQL e parâmetros
    assert len(cursor.executed) == 1
    sql, params = cursor.executed[0]
    assert "DELETE FROM produtos" in sql
    assert params == (99,)


def test_delete_product_not_found(monkeypatch):
    cursor = FakeCursor()
    cursor.rowcount = 0  # nada deletado
    connection = FakeConnection(cursor)

    monkeypatch.setattr(
        "src.Helper.ProductHelper.ProductHelper.Connection",
        lambda self: connection,
    )

    helper = ProductHelper()
    delete_model = DeleteProductModel(ProductId=12345)

    result = helper.delete_product(delete_model)

    # retorna False quando nenhum registro foi afetado
    assert result is False
    assert connection.committed is True
    assert cursor.closed is True


def test_delete_product_error_rolls_back(monkeypatch):
    cursor = FakeCursor()
    cursor.raise_on_execute = Exception("DB error")
    connection = FakeConnection(cursor)

    monkeypatch.setattr(
        "src.Helper.ProductHelper.ProductHelper.Connection",
        lambda self: connection,
    )

    helper = ProductHelper()
    delete_model = DeleteProductModel(ProductId=1)

    with pytest.raises(HTTPException) as exc:
        helper.delete_product(delete_model)

    assert exc.value.status_code == 500
    assert "Error deleting product" in exc.value.detail
    assert connection.rolled_back is True
    assert cursor.closed is True


# ================== TESTES DO list_products ==================


def test_list_products_all(monkeypatch):
    cursor = FakeCursor()
    cursor.fetchall_results = [
        (1, 10, "Produto A", "Desc A", 50.0),
        (2, 20, "Produto B", "Desc B", 100.0),
    ]
    connection = FakeConnection(cursor)

    monkeypatch.setattr(
        "src.Helper.ProductHelper.ProductHelper.Connection",
        lambda self: connection,
    )

    helper = ProductHelper()
    products = helper.list_products()

    # retorna lista de ListProductModel
    assert len(products) == 2

    p1 = products[0]
    assert p1.ProductId == 1
    assert p1.CauseId == 10
    assert p1.ProductName == "Produto A"
    assert p1.Description == "Desc A"
    assert p1.Value == 50.0

    p2 = products[1]
    assert p2.ProductId == 2
    assert p2.CauseId == 20
    assert p2.ProductName == "Produto B"
    assert p2.Description == "Desc B"
    assert p2.Value == 100.0

    # conferindo SQL
    assert len(cursor.executed) == 1
    sql, params = cursor.executed[0]
    assert "FROM produtos" in sql
    # sem filtro → params deve ser None ou não passado
    assert params is None


def test_list_products_filtered_by_user(monkeypatch):
    cursor = FakeCursor()
    cursor.fetchall_results = [
        (3, 99, "Produto X", "Desc X", 10.0),
    ]
    connection = FakeConnection(cursor)

    monkeypatch.setattr(
        "src.Helper.ProductHelper.ProductHelper.Connection",
        lambda self: connection,
    )

    helper = ProductHelper()
    products = helper.list_products(UserId=99)

    assert len(products) == 1
    p = products[0]
    assert p.ProductId == 3
    assert p.CauseId == 99
    assert p.ProductName == "Produto X"
    assert p.Description == "Desc X"
    assert p.Value == 10.0

    assert len(cursor.executed) == 1
    sql, params = cursor.executed[0]
    assert "FROM produtos" in sql
    assert "WHERE id_causa = %s" in sql
    assert params == (99,)
