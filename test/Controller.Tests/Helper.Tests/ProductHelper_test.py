import pytest
from typing import Any, Callable
from src.Model.ProductModel import ProductModel
from src.Helper.ProductHelper import ProductHelper

class MockConnection:
    def __init__(self, mock_cursor: Any):
        self.mock_cursor = mock_cursor
        self.commit_called = False
        self.rollback_called = False
        self.close_called = False

    def cursor(self):
        return self.mock_cursor
    
    def commit(self):
        self.commit_called = True
        
    def rollback(self):
        self.rollback_called = True
        
    def close(self):
        self.close_called = True

class MockConnectionHelper:
    def __init__(self, mock_conn: MockConnection):
        self._mock_conn = mock_conn

    def get_connection(self):
        return self._mock_conn
    

@pytest.fixture
def product_helper_setup(monkeypatch, mocker):
    
    mock_cursor = mocker.Mock()
    
    mock_conn = MockConnection(mock_cursor)
    
    mock_conn_helper_instance = MockConnectionHelper(mock_conn)
    
    def mock_connection_helper_init(*args, **kwargs):
        return mock_conn_helper_instance

    monkeypatch.setattr(
        'src.Helper.ProductHelper.ConnectionHelper', 
        mock_connection_helper_init
    )
    
    helper = ProductHelper()
    
    yield helper, mock_cursor, mock_conn 

def test_create_product_success(product_helper_setup):
    """Testa a criação de um produto e verifica se o SQL e o commit foram chamados."""

    helper, mock_cursor, mock_conn = product_helper_setup
    
    test_product = ProductModel(
        causeId=101, 
        name="Produto Teste", 
        description="Descrição para teste", 
        value=50.00
    )

    mock_cursor.fetchone.return_value = (1,)
    
    new_id = helper.create_product(test_product)
    
    assert mock_cursor.execute.called 
    assert mock_conn.commit_called 
    assert new_id == 1 
    assert mock_conn.close_called 

def test_update_product_success(product_helper_setup):
    """Testa se o produto é alterado com sucesso e retorna True."""

    helper, mock_cursor, mock_conn = product_helper_setup
    
    test_product_update = ProductModel(
        productId=5, causeId=101, name="Produto Atualizado",
        description="Nova descrição", value=75.50
    )
    
    mock_cursor.rowcount = 1
    
    result = helper.update_product(test_product_update)
    
    assert mock_cursor.execute.called
    assert mock_conn.commit_called
    assert result is True 
    assert mock_conn.close_called

def test_get_product_by_id_found(product_helper_setup):
    """Testa a busca de produto quando o ID é encontrado."""

    helper, mock_cursor, mock_conn = product_helper_setup

    # Simula o registro do banco: (id, id_causa, nome, descricao, valor, data_cadastro)
    db_record = (5, 101, "Produto X", "Detalhes X", 99.99, '2023-01-01')
    mock_cursor.fetchone.return_value = db_record
    
    product = helper.get_product_by_id(5)
    
    assert mock_cursor.execute.called
    assert isinstance(product, ProductModel)
    assert product.value == 99.99
    assert product.productId == 5
    assert mock_cursor.close.called
    assert mock_conn.close_called 
    
def test_get_product_by_id_not_found(product_helper_setup):
    """Testa a busca de produto quando o ID não é encontrado."""

    helper, mock_cursor, mock_conn = product_helper_setup

    mock_cursor.fetchone.return_value = None
    
    product = helper.get_product_by_id(999)
    
    assert mock_cursor.execute.called
    assert product is None
    assert mock_cursor.close.called
    assert mock_conn.close_called