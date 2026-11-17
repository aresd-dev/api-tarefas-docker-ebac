# API de tarefas com Docker e Poetry

Aplicação FastAPI com SQLite, autenticação HTTP Basic, paginação e ordenação.
O código principal está em main.py. O banco e sua tabela são criados automaticamente.

## Pré-requisitos

- Docker com suporte a containers Linux e Docker Compose v2.
- Docker Desktop iniciado, se estiver usando Windows ou macOS.
- Porta 8000 disponível.
- Acesso à internet no primeiro build para baixar a imagem e as dependências.

## Obter o projeto

Se recebeu o ZIP, extraia-o e abra um terminal na pasta api-tarefas-docker.
Para clonar o repositório privado, use uma conta com acesso a ele.

```bash
git clone https://github.com/aresd-dev/api-tarefas-docker-ebac.git api-tarefas-docker
cd api-tarefas-docker
```

## Construir e iniciar

```bash
docker compose up --build -d
docker compose ps
docker compose logs -f api
```

Encerre a visualização dos logs com Ctrl+C. O serviço continua em segundo plano.
Em instalações com o comando legado, o equivalente é docker-compose up --build -d.

Abra http://localhost:8000/docs e clique em Authorize. Use o usuário admin e a
senha senha123. Expanda uma rota, clique em Try it out, preencha os campos e clique
em Execute.

## Testar as operações

1. Em POST /tarefas, envie o corpo abaixo. A resposta esperada é 201.

```json
{
  "nome": "Estudar",
  "descricao": "Praticar Docker",
  "concluida": false
}
```

2. Em GET /tarefas, informe page=1, size=10 e order_by=nome. A resposta 200 deve
   listar a tarefa. A ordenação crescente também aceita descricao e concluida.
3. Em PUT /tarefas/{nome}, informe Estudar. A resposta 200 deve ter concluida=true.
4. Execute docker compose down e depois docker compose up -d. Repita o GET e
   confirme que a tarefa continua concluída.
5. Em DELETE /tarefas/{nome}, informe Estudar. A resposta deve ser 204.
6. Repita o GET e confirme a lista vazia.

Credenciais ausentes ou incorretas retornam 401. Paginação inválida e campos de
ordenação desconhecidos retornam 422. Nomes duplicados retornam 409 e tarefas
inexistentes retornam 404.

## Volumes e recarregamento

O Compose monta main.py em /app/main.py. Ao salvar alterações no código local,
o Uvicorn recarrega a aplicação. O modo de polling permite detectar as mudanças
também nos volumes compartilhados pelo Docker Desktop.

O volume nomeado dados_tarefas guarda /data/tarefas.db e permanece após
docker compose down. Para apagar os dados intencionalmente, use docker compose down -v.

Ao mudar pyproject.toml ou poetry.lock, reconstrua a imagem com
docker compose up --build -d.

## Variáveis de ambiente

API_USER e API_PASSWORD têm os padrões admin e senha123 para o exercício.
Opcionalmente, crie um arquivo .env ao lado do Compose para substituí-los.

```dotenv
API_USER=meu_usuario
API_PASSWORD=minha_senha
```

O Compose define DATABASE_PATH=/data/tarefas.db e WATCHFILES_FORCE_POLLING=true.
O Dockerfile configura a saída imediata dos logs e instala as dependências com
Poetry em /app/.venv. A versão do Poetry é fixada em 2.2.1 e poetry.lock registra
as versões resolvidas das dependências.

## Parar a aplicação

```bash
docker compose down
```

O equivalente legado é docker-compose down.

## Referências

- [Instalação de dependências com Poetry](https://python-poetry.org/docs/cli/#install)
- [Documentação do Docker Compose](https://docs.docker.com/compose/)

## Validação realizada

O arquivo Compose passou em config --quiet, e poetry check --lock confirmou
a consistência do arquivo de dependências. A API foi testada localmente com
requisições HTTP para CRUD, autenticação, validação de entradas, paginação e
ordenação. O reinício real do servidor confirmou a persistência no SQLite.

## Integração contínua: testes e Docker

O projeto utiliza **Python 3.12** (>=3.12,<3.13) e **Poetry 2.2.1**.
O workflow `.github/workflows/python-app.yml` executa a cada push na `main`,
em `ubuntu-latest`, nesta ordem:

1. Checkout e instalação de Python e Poetry.
2. Restauração do cache `~/.cache/pypoetry` com `actions/cache@v4`.
   A chave inclui sistema operacional, Python, Poetry e hash de `poetry.lock`.
   O cache é salvo após uma execução bem-sucedida e reutilizado quando a chave coincidir.
3. `poetry install --no-root --no-interaction` e `poetry run pytest`.
4. `docker build -f Dockerfile -t "$IMAGE_NAME" .`, com `IMAGE_NAME=fastapi-app:latest`.
5. `docker run` e verificação HTTP de `/openapi.json` e `/tarefas` autenticado.
6. Exibição dos logs e remoção do container, inclusive em caso de falha.

Falhas nos testes, build, inicialização ou verificações fazem o job falhar.
Não há publicação da imagem nem deploy. Uma execução vermelha sinaliza o erro;
para bloquear merges, é necessário configurar este check como obrigatório
nas regras de proteção da branch.

O Docker local não é necessário para a execução do CI. Consulte os resultados
na [aba Actions](https://github.com/aresd-dev/api-tarefas-docker-ebac/actions).
