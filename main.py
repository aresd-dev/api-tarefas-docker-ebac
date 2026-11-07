from contextlib import asynccontextmanager, contextmanager
from pathlib import Path
from secrets import compare_digest
import sqlite3
import os
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, HTTPException, Query, Response
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel


class Tarefa(BaseModel):
    nome: str
    descricao: str
    concluida: bool = False


# O Compose aponta o banco para um volume persistente.
BANCO = Path(os.getenv("DATABASE_PATH", str(Path(__file__).resolve().with_name("tarefas.db"))))


@contextmanager
def conectar():
    conexao = sqlite3.connect(BANCO, timeout=10)
    conexao.row_factory = sqlite3.Row
    try:
        with conexao:
            yield conexao
    finally:
        conexao.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    BANCO.parent.mkdir(parents=True, exist_ok=True)
    with conectar() as conexao:
        conexao.execute("""
            CREATE TABLE IF NOT EXISTS tarefas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL UNIQUE CHECK (length(trim(nome)) > 0),
                descricao TEXT NOT NULL,
                concluida INTEGER NOT NULL DEFAULT 0 CHECK (concluida IN (0, 1))
            )
        """)
    yield


seguranca = HTTPBasic()


def autenticar(
    credenciais: Annotated[HTTPBasicCredentials, Depends(seguranca)],
) -> str:
    # Valores padrão para o exercício, configuráveis pelo ambiente.
    usuario_valido = compare_digest(credenciais.username.encode("utf-8"), os.getenv("API_USER", "admin").encode("utf-8"))
    senha_valida = compare_digest(credenciais.password.encode("utf-8"), os.getenv("API_PASSWORD", "senha123").encode("utf-8"))
    if not (usuario_valido and senha_valida):
        raise HTTPException(
            status_code=401,
            detail="Usuário ou senha inválidos",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credenciais.username


app = FastAPI(
    title="Lista de tarefas",
    dependencies=[Depends(autenticar)],
    lifespan=lifespan,
)


@app.post("/tarefas", status_code=201)
def adicionar_tarefa(tarefa: Tarefa) -> Tarefa:
    if not tarefa.nome.strip():
        raise HTTPException(422, "Informe um nome não vazio")
    try:
        with conectar() as conexao:
            conexao.execute(
                "INSERT INTO tarefas (nome, descricao, concluida) VALUES (?, ?, ?)",
                (tarefa.nome, tarefa.descricao, tarefa.concluida),
            )
    except sqlite3.IntegrityError as erro:
        if erro.sqlite_errorcode == sqlite3.SQLITE_CONSTRAINT_UNIQUE:
            raise HTTPException(409, "Já existe uma tarefa com esse nome") from erro
        raise
    return tarefa


@app.get("/tarefas")
def listar_tarefas(
    page: Annotated[int, Query(ge=1, description="Número da página, a partir de 1")] = 1,
    size: Annotated[int, Query(ge=1, description="Quantidade de tarefas por página")] = 10,
    order_by: Annotated[
        Literal["nome", "descricao", "concluida"] | None,
        Query(description="Campo para ordenação crescente"),
    ] = None,
) -> list[Tarefa]:
    # Somente identificadores desta lista fixa entram no SQL.
    ordenacao = {
        None: "id",
        "nome": "nome, id",
        "descricao": "descricao, id",
        "concluida": "concluida, id",
    }[order_by]
    inicio = (page - 1) * size
    # SQLite aceita inteiros de até 64 bits nos parâmetros LIMIT/OFFSET.
    if inicio > 9223372036854775807:
        return []
    with conectar() as conexao:
        registros = conexao.execute(
            f"SELECT nome, descricao, concluida FROM tarefas ORDER BY {ordenacao} LIMIT ? OFFSET ?",
            (min(size, 9223372036854775807), inicio),
        ).fetchall()
    return [Tarefa(**dict(registro)) for registro in registros]


@app.put("/tarefas/{nome:path}")
def concluir_tarefa(nome: str) -> Tarefa:
    with conectar() as conexao:
        resultado = conexao.execute(
            "UPDATE tarefas SET concluida = 1 WHERE nome = ?", (nome,)
        )
        if resultado.rowcount == 0:
            raise HTTPException(404, "Tarefa não encontrada")
        registro = conexao.execute(
            "SELECT nome, descricao, concluida FROM tarefas WHERE nome = ?", (nome,)
        ).fetchone()
    return Tarefa(**dict(registro))


@app.delete("/tarefas/{nome:path}", status_code=204)
def remover_tarefa(nome: str):
    with conectar() as conexao:
        resultado = conexao.execute("DELETE FROM tarefas WHERE nome = ?", (nome,))
        if resultado.rowcount == 0:
            raise HTTPException(404, "Tarefa não encontrada")
    return Response(status_code=204)

