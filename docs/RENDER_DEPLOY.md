# Deploy no Render

## Pré-requisitos

- Projeto enviado para GitHub.
- Projeto Supabase configurado.
- Banco vazio ou compatível com as migrações do Django.

## Blueprint

O arquivo `render.yaml` cria um Web Service Python. O script `build.sh` instala dependências, coleta arquivos estáticos e executa as migrações.

## Variáveis obrigatórias

Preencha no Render:

- `DATABASE_URL`
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`

As demais já possuem valores no Blueprint, mas `ALLOWED_HOSTS` e `CSRF_TRUSTED_ORIGINS` devem ser atualizados quando houver domínio próprio.

## Primeiro deploy

1. No Render, escolha **New > Blueprint**.
2. Conecte o repositório.
3. Confirme o serviço `abasc-mvp1`.
4. Preencha as variáveis secretas.
5. Inicie o deploy.
6. Verifique `/health/`.

## Primeiro acesso presidencial

O plano Free não disponibiliza Shell. Para o primeiro presidente, defina `app_metadata.role = president` no Supabase antes do primeiro login.

Como alternativa operacional, depois que a conta fizer o primeiro login e for sincronizada, carregue localmente as variáveis de produção e execute:

```bash
python manage.py set_user_role presidente@dominio.org president --activate
```

Esse comando altera apenas o papel no banco Django e protege o último presidente ativo.

## Domínio próprio

Depois de configurar o domínio, ajuste:

```env
ALLOWED_HOSTS=seu-dominio.org.br,.onrender.com
CSRF_TRUSTED_ORIGINS=https://seu-dominio.org.br,https://*.onrender.com
```

## Observação sobre arquivos

O sistema envia imagens de produção ao Supabase Storage. O fallback de upload local é destinado ao desenvolvimento, pois o disco local do serviço não deve ser tratado como armazenamento permanente.
