# Inkbind

API assíncrona para converter o conteúdo textual de páginas web em arquivos PDF.

> **Estado:** reconstrução inicial em andamento. Os arquivos foram restaurados em uma branch isolada e ainda precisam ser executados e validados no GitHub Codespaces antes de considerar a versão pronta.

## Estrutura

```text
inkbind/
├── docker-compose.yml
├── .env.example
└── backend/
    ├── Dockerfile
    ├── requirements.txt
    ├── app/
    │   ├── __init__.py
    │   ├── main.py
    │   ├── celery_app.py
    │   ├── tasks.py
    │   ├── scraper.py
    │   └── builder.py
    └── tests/
        └── test_security.py
```

## Como funciona

1. `POST /convert` envia uma URL para uma tarefa Celery.
2. O worker valida a URL, obtém uma página HTML e extrai título e parágrafos.
3. O conteúdo textual é escapado antes da geração do PDF.
4. `GET /status/{task_id}` informa o estado da tarefa.
5. Quando a tarefa termina, `GET /download/{file_id}` entrega o PDF.
6. `GET /health` verifica se a API responde.

## Executar localmente com Docker Compose

1. Copie `.env.example` para `.env` e ajuste a senha de desenvolvimento.
2. Execute:

   ```bash
   docker compose up --build
   ```

3. Verifique a API:

   ```bash
   curl http://127.0.0.1:8000/health
   ```

4. Envie uma página pública que você tenha autorização para processar:

   ```bash
   curl -X POST http://127.0.0.1:8000/convert \
     -H 'Content-Type: application/json' \
     -d '{"url":"https://example.org/"}'
   ```

5. Consulte o estado usando o `task_id` retornado:

   ```bash
   curl http://127.0.0.1:8000/status/SEU_TASK_ID
   ```

6. Quando o estado for `SUCCESS`, copie o `file_id` retornado em `result` e baixe o arquivo:

   ```bash
   curl -fL -o artigo.pdf http://127.0.0.1:8000/download/SEU_FILE_ID
   ```

A página escolhida precisa retornar HTML e conter pelo menos um parágrafo. Os identificadores nos exemplos devem ser substituídos pelos valores reais da resposta da API.

## Executar os testes

No Codespaces, entre na pasta `backend` e execute:

```bash
python -m pip install -r requirements.txt
pytest -q
```

Se a instalação do WeasyPrint reclamar de bibliotecas de sistema, usaremos o Docker Compose para executar a validação no ambiente previsto pelo projeto.

## Segurança: o que já foi incluído nesta reconstrução

- Permite apenas URLs HTTP/HTTPS e rejeita credenciais embutidas na URL.
- Rejeita endereços IP não públicos e hosts locais após resolução DNS.
- Valida novamente os destinos de redirecionamento e limita a quantidade de redirecionamentos.
- Limita o tempo de requisição e o conteúdo baixado a 5 MB.
- Aceita somente respostas HTML/XHTML e exige parágrafos extraídos.
- Escapa título, parágrafos e fonte antes de inserir conteúdo em HTML para PDF.
- Desativa o carregamento de recursos externos durante a renderização do PDF.
- Restringe identificadores de tarefas e arquivos e não devolve detalhes internos de falhas ao cliente.
- Executa os contêineres da API e do worker como usuário sem privilégios e limita a exposição local das portas de desenvolvimento.

### Limitações que ainda exigem atenção

- Validação DNS na aplicação, isoladamente, **não elimina completamente DNS rebinding**. Antes de disponibilizar o serviço publicamente, configure regras de saída de rede para bloquear redes privadas, loopback, link-local e serviços de metadados.
- Esta versão ainda não implementa autenticação, autorização, rate limiting, quotas ou política de retenção/limpeza de PDFs. Não exponha a API publicamente antes dessas etapas.
- PostgreSQL está disponível no Compose, mas a API ainda não usa o banco para persistir dados de negócio.
- As variáveis de ambiente e senhas de exemplo são apenas para desenvolvimento; use segredos próprios em qualquer ambiente compartilhado.

## Próximas etapas

1. Executar testes automatizados e corrigir eventuais falhas de ambiente.
2. Acrescentar testes reais para SSRF, redirecionamentos, escaping do PDF e endpoints.
3. Validar o fluxo completo de conversão e download com Docker Compose.
4. Adicionar autenticação, limites de uso e limpeza segura de arquivos antes de qualquer implantação pública.
