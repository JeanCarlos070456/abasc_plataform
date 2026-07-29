# ABASC MVP 1

Plataforma institucional da **Associação de Bacharéis em Saúde Coletiva (ABASC)**, construída com Django, CSS próprio, PostgreSQL/Supabase, Supabase Auth, Supabase Storage e preparada para deploy no Render.

## Entregas do MVP

- Portal público com página inicial, notícias, oportunidades e páginas institucionais.
- Identidade visual ABASC com a paleta `#04BC22`, `#9FBDE6`, `#04758A`, `#6CBC7C` e `#AACED8`.
- Autenticação por e-mail e senha no Supabase Auth.
- Fallback local opcional para desenvolvimento.
- Acessos: visitante, Associado, Executivo e Presidente.
- Área do associado com dados cadastrais, situação associativa e pagamentos.
- Painel executivo com indicadores e gestão de notícias, imagens e links.
- Painel da presidência com indicadores estratégicos, usuários, papéis e auditoria.
- Supabase Storage com fallback local para desenvolvimento.
- Django Admin, migrações, testes, CI, dados demonstrativos, Docker e Render Blueprint.

## Início rápido

### Windows PowerShell

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup_windows.ps1
```

### Linux/macOS

```bash
./scripts/setup_linux.sh
```

Ou execute manualmente:

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env               # Windows: copy .env.example .env
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

Acesse `http://127.0.0.1:8000/`.

## Contas demonstrativas

O comando `seed_demo` funciona somente com `DEBUG=True`.

| Perfil | E-mail | Senha |
|---|---|---|
| Presidente | `presidente@abasc.demo` | `Abasc@123` |
| Executivo | `executivo@abasc.demo` | `Abasc@123` |
| Associado | `associado@abasc.demo` | `Abasc@123` |

Exclua ou altere essas contas antes de usar dados reais.

## Configuração real

1. Copie `.env.example` para `.env`.
2. Configure `DATABASE_URL` com o pooler PostgreSQL do Supabase.
3. Configure as chaves do Supabase.
4. Crie os buckets executando `docs/supabase_storage.sql`.
5. Execute `python manage.py migrate`.
6. Defina o primeiro presidente conforme `docs/SUPABASE_SETUP.md`.

A identidade e senha ficam no Supabase Auth. O Django mantém a sessão web, as regras, os papéis e os relacionamentos do domínio.

## Validações locais

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

## Documentação

- [`docs/ARQUITETURA.md`](docs/ARQUITETURA.md)
- [`docs/SUPABASE_SETUP.md`](docs/SUPABASE_SETUP.md)
- [`docs/RENDER_DEPLOY.md`](docs/RENDER_DEPLOY.md)
- [`docs/ROADMAP.md`](docs/ROADMAP.md)

## Estrutura

```text
abasc_mvp1/
├── abasc_mvp1/             # configurações do projeto
├── apps/
│   ├── accounts/           # autenticação e usuários
│   ├── associates/         # associados e pagamentos
│   ├── core/               # portal, configuração e auditoria
│   ├── dashboards/         # painéis gerenciais
│   └── news/               # notícias e oportunidades
├── docs/
├── scripts/
├── static/
├── templates/
├── Dockerfile
├── render.yaml
└── requirements.txt
```
