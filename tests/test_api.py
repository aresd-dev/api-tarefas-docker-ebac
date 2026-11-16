"""Testes da aplicação real, usando um SQLite temporário por cenário."""
import pytest
from fastapi.testclient import TestClient
import main


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Isola banco e credenciais sem substituir a lógica dos endpoints."""
    monkeypatch.setattr(main, "BANCO", tmp_path / "tarefas.db")
    monkeypatch.setenv("API_USER", "admin")
    monkeypatch.setenv("API_PASSWORD", "senha-teste")
    with TestClient(main.app) as client:
        client.auth = ("admin", "senha-teste")
        yield client


def test_crud(client):
    # Criação: o status de conclusão começa como falso.
    tarefa = {"nome": "Estudar", "descricao": "Praticar pytest", "concluida": False}
    resposta = client.post("/tarefas", json=tarefa)
    assert resposta.status_code == 201, resposta.text
    assert resposta.json() == tarefa, "A criação deve preservar os dados enviados"
    # Listagem: a tarefa criada precisa vir do banco.
    resposta = client.get("/tarefas")
    assert resposta.status_code == 200, resposta.text
    assert resposta.json() == [tarefa], "A tarefa criada deve aparecer na listagem"
    # Conclusão: o PUT altera o estado armazenado.
    resposta = client.put("/tarefas/Estudar")
    assert resposta.status_code == 200, resposta.text
    assert resposta.json() == {**tarefa, "concluida": True}
    assert client.get("/tarefas").json()[0]["concluida"] is True
    # Exclusão: remove o registro e retorna um corpo vazio.
    resposta = client.delete("/tarefas/Estudar")
    assert resposta.status_code == 204, resposta.text
    assert resposta.content == b""
    assert client.get("/tarefas").json() == []


@pytest.mark.parametrize("method,path", [
    ("GET", "/tarefas"), ("POST", "/tarefas"),
    ("PUT", "/tarefas/inexistente"), ("DELETE", "/tarefas/inexistente"),
])
def test_credenciais_invalidas(client, method, path):
    # Todas as operações devem recusar credenciais incorretas.
    resposta = client.request(method, path, auth=("admin", "errada"),
                              json={"nome": "Teste", "descricao": "Teste"})
    assert resposta.status_code == 401, resposta.text
    assert resposta.json() == {"detail": "Usuário ou senha inválidos"}


@pytest.mark.parametrize("method", ["PUT", "DELETE"])
def test_tarefa_inexistente(client, method):
    # Atualizar ou excluir um registro ausente deve informar 404.
    resposta = client.request(method, "/tarefas/inexistente")
    assert resposta.status_code == 404, resposta.text
    assert resposta.json() == {"detail": "Tarefa não encontrada"}


@pytest.mark.parametrize("query", ["page=0", "size=-1", "page=abc", "order_by=invalido"])
def test_parametros_invalidos(client, query):
    # Paginação e ordenação inválidas são rejeitadas antes da consulta.
    resposta = client.get(f"/tarefas?{query}")
    assert resposta.status_code == 422, resposta.text
    assert isinstance(resposta.json()["detail"], list)


def test_nome_em_branco(client):
    # Espaços sozinhos não representam um nome de tarefa válido.
    resposta = client.post("/tarefas", json={"nome": "   ", "descricao": "Teste"})
    assert resposta.status_code == 422, resposta.text
    assert resposta.json() == {"detail": "Informe um nome não vazio"}
