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

Comandos da versão 0.1 (*marcados como stub na Fatia 1*):

- `flow auth login` *(stub)*: abre o navegador para login manual no Google Flow
- `flow auth status` *(stub)*: status da autenticação/perfil
- `flow auth logout` *(stub)*: limpa a sessão local
- `flow projects list` *(stub)*: lista projetos
- `flow projects create <nome>` *(stub)*: cria novo projeto
- `flow projects open <id>` *(stub)*: abre projeto no navegador
- `flow models list [--kind image|video]` *(stub)*: lista modelos disponíveis
- `flow credits` *(stub)*: exibe saldo de créditos
- `flow media list [--project ID] [--kind image|video]` *(stub)*: lista mídias geradas
- `flow media download <id> [--out DIR]` *(stub)*: baixa mídia por ID
- `flow generate image "<prompt>" [--aspect ...] [--model ...] [--count 1-4] [--project ID] [--yes]` *(stub)*: gera imagem (exige `--yes` para confirmar consumo de créditos)
- `flow generate video "<prompt>" [--aspect ...] [--model ...] [--resolution 360p|720p] [--duration 4|6|8|10] [--count 1-4] [--project ID] [--yes]` *(stub)*: gera vídeo (exige `--yes` para confirmar consumo de créditos)
- `flow repl` *(stub)*: modo interativo

