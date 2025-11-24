import pytest

if __name__ == "__main__":
    pytest_args = [
        "-vv",
        "--cov=src",                # mede cobertura da pasta src
        "--cov-report=term-missing",  # mostra linhas não cobertas
        "-m", "not integration",    # NÃO roda os testes de integração por padrão
    ]

    raise SystemExit(pytest.main(pytest_args))
