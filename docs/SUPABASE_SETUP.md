# Configuração do Supabase

## 1. Banco PostgreSQL

No painel do Supabase, copie a URL do pooler e preencha `DATABASE_URL` no `.env`.

Exemplo de formato:

```env
DATABASE_URL=postgresql://USUARIO:SENHA@HOST:6543/postgres?sslmode=require
DB_SSL_REQUIRE=True
```

Não versione o arquivo `.env`.

## 2. Authentication

Ative autenticação por e-mail e senha. Crie os usuários pelo painel ou por um fluxo administrativo futuro.

O Django sincroniza o usuário no primeiro login. Para definir o papel inicial privilegiado, use exclusivamente o `app_metadata` administrado pelo backend antes desse primeiro acesso:

```json
{
  "role": "executive"
}
```

Valores aceitos:

- `associate`
- `executive`
- `president`

O sistema ignora papéis enviados em `user_metadata`, evitando autoelevação de privilégio.

## 3. Storage

Execute o conteúdo de `docs/supabase_storage.sql` no SQL Editor. Os buckets são públicos para leitura, mas os uploads da aplicação usam a Service Role Key somente no servidor.

Variáveis:

```env
SUPABASE_URL=https://SEU-PROJETO.supabase.co
SUPABASE_ANON_KEY=SUA_CHAVE_ANON
SUPABASE_SERVICE_ROLE_KEY=SUA_SERVICE_ROLE
SUPABASE_STORAGE_BUCKET_NEWS=abasc-news
SUPABASE_STORAGE_BUCKET_AVATARS=abasc-avatars
```

A `SUPABASE_SERVICE_ROLE_KEY` nunca deve ser incluída no HTML, JavaScript, repositório ou logs.

## 4. Migrações

Com o `.env` configurado:

```bash
python manage.py migrate
```

## 5. Primeiro presidente

Antes do primeiro login, defina `app_metadata.role = president` para a conta escolhida no Supabase. No primeiro acesso, o Django criará a conta local já com o papel presidencial.

Caso a conta já tenha entrado como associado, configure localmente o `.env` com o banco de produção e execute:

```bash
python manage.py set_user_role presidente@dominio.org president --activate
```

Após o primeiro acesso, o papel passa a ser administrado no Django pela interface da presidência. Alterações posteriores em `app_metadata` não sobrescrevem decisões locais.
