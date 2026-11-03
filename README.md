# flow-cli

CLI **não oficial** para o [Google Flow](https://flow.google.com), no estilo CLI-Anything. Em construção.

- `docs/EXPLORACAO.md`: como o Flow funciona por baixo e o mapa da interface.
- `docs/PLANO.md`: decisões, comandos e fatias de desenvolvimento.

> Projeto pessoal e sem ligação com o Google. Automatizar o site pode ir contra os termos de uso; use por sua conta e risco, só na sua própria conta. Nenhuma senha ou token é guardado pelo projeto.

## Instalação

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
playwright install chromium
```

## Uso

Todos os comandos aceitam `--json` global para saída estruturada em JSON.

Comandos da versão 0.1 (todos implementados):

- `flow auth login`: abre o navegador para login manual no Google Flow
- `flow auth status`: status da autenticação/perfil
- `flow auth logout [--yes]`: encerra a sessão ativa e remove o diretório do perfil
- `flow projects list`: lista projetos
- `flow projects create <nome>`: cria novo projeto
- `flow projects open <id> [--browser]`: imprime a URL do projeto (e abre no navegador com `--browser`)
- `flow models list [--kind image|video]`: lista modelos disponíveis
- `flow credits`: exibe saldo de créditos
- `flow media list [--project ID] [--kind image|video]`: lista mídias geradas
- `flow media download <id> [--out DIR] [--project ID]`: baixa mídia por ID
- `flow generate image "<prompt>" [--aspect ...] [--model ...] [--count 1-4] [--project ID] [--yes]`: gera imagem (exige `--yes` para confirmar consumo de créditos)
- `flow generate video "<prompt>" [--aspect ...] [--model ...] [--resolution 360p|720p] [--duration 4|6|8|10] [--count 1-4] [--project ID] [--yes]`: gera vídeo (exige `--yes` para confirmar consumo de créditos)
- `flow repl`: modo interativo


## Testes

```bash
.venv/bin/pytest -q                 # unitários (sem rede/navegador)
FLOW_CLI_LIVE=1 .venv/bin/pytest -m live -q   # integração ao vivo (somente leitura, opt-in)
```

Os testes `live` usam o perfil logado em `~/.config/flow-cli/profile`, só leem (auth, credits, projects, models, media) e nunca geram mídia.
