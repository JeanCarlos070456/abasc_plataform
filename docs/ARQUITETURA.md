# Arquitetura — ABASC MVP 1

## Visão geral

O ABASC MVP 1 usa uma arquitetura modular monolítica. O Django concentra regras de negócio, autorização, renderização de páginas e administração. O Supabase fornece PostgreSQL, identidade e armazenamento de arquivos. O Render executa a aplicação web.

```text
Navegador
   │ HTTPS
   ▼
Django no Render
   ├── Templates + CSS + JavaScript
   ├── Sessão e RBAC
   ├── Regras de negócio
   ├── Auditoria
   ├── Supabase Auth REST API
   ├── PostgreSQL do Supabase
   └── Supabase Storage
```

## Aplicações Django

- `core`: portal institucional, configuração do site, páginas públicas, health check e auditoria.
- `accounts`: usuário customizado, autenticação Supabase, sessão Django, perfil e papéis.
- `news`: categorias, notícias, oportunidades, publicação e imagens.
- `associates`: área do associado e pagamentos.
- `dashboards`: painéis executivo e presidencial, indicadores e gestão de usuários.

## Perfis e permissões

| Acesso | Capacidades principais |
|---|---|
| Visitante | Conteúdo público, notícias, oportunidades e páginas institucionais |
| Associado | Conteúdo público/restrito, dados pessoais e situação de pagamentos |
| Executivo | Tudo do associado, publicação de conteúdo e indicadores operacionais |
| Presidente | Visão completa, gestão de papéis, pagamentos, auditoria e indicadores estratégicos |

A hierarquia é aplicada por decorators e propriedades do modelo `User`. A interface nunca é a única barreira: as views também validam o papel necessário.

## Autenticação

1. O navegador envia e-mail e senha ao Django.
2. O Django autentica pela API do Supabase Auth.
3. O usuário é sincronizado na tabela local `accounts_user` pelo UUID do Supabase.
4. O Django cria sua própria sessão segura.
5. O papel inicial privilegiado só pode vir de `app_metadata.role`; depois da criação, a presidência controla o papel no Django. `user_metadata` nunca concede privilégios.

## Dados principais

- `accounts_user`: identidade local, papel, número e situação associativa.
- `news_category`: categorias editoriais.
- `news_post`: notícias, oportunidades, links, visibilidade e publicação.
- `associates_payment`: mensalidades e situação de pagamento.
- `core_auditlog`: trilha de ações importantes.
- `core_siteconfiguration`: dados institucionais editáveis.

## Segurança aplicada

- Senhas permanecem no Supabase Auth em produção.
- Service Role Key usada apenas no backend.
- Proteção CSRF, cookies seguros, HSTS em produção e bloqueio de iframe.
- Redirecionamento pós-login validado contra open redirect.
- Upload limitado a imagens e 5 MB no formulário.
- RBAC validado no backend.
- Proteção contra remoção do último presidente ativo.
- Auditoria de login, logout, criação, atualização, exclusão e alteração de papel.

## Evolução prevista

A arquitetura permite incluir documentos, assembleias, notificações, cobrança integrada, importação de associados, API REST e dashboards avançados sem separar microserviços prematuramente.
