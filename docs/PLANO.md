# Plano do flow-cli

CLI **não oficial** para o Google Flow, no estilo CLI-Anything (Python, Click, saída `--json`, modo REPL, testes). O CLI-Anything padrão exige código-fonte do app; o Flow é um site fechado, então a base é o mapeamento por navegador (ver `EXPLORACAO.md`).

## Decisões
1. **Backend por navegador (Playwright) com perfil persistente.** Dirige a interface do Flow e usa o login salvo. É mais estável que replicar o `batchexecute` e passa pelo reCAPTCHA como o próprio site.
2. **Leituras podem migrar depois para `batchexecute`** (listar projetos e mídias), dentro da página logada, quando os IDs forem decifrados. Primeiro versão: leitura pela interface.
3. **Login manual.** `flow auth login` abre o navegador visível; a pessoa entra sozinha. O CLI nunca pede nem guarda senha ou token; só reutiliza o perfil do navegador em `~/.config/flow-cli/profile`.
4. **Segurança de crédito.** Todo comando que gera mídia mostra o custo (lido da interface), roda por padrão como `--dry-run` e só gasta com `--yes`.
5. **Saída dupla.** Tabela legível por padrão, `--json` para agentes.
6. **Python 3.11+**, pacote `flow_cli`, comando `flow`.

## Comandos (versão 0.1)
```
flow auth login | status | logout
flow projects list | create <nome> | open <id>
flow models list [--kind image|video]
flow credits
flow media list [--project ID] [--kind image|video]
flow media download <id> [--out DIR]
flow generate image "<prompt>" [--aspect 16:9] [--model ...] [--count 1-4] [--project ID] [--yes]
flow generate video "<prompt>" [--aspect 16:9|9:16] [--model ...] [--resolution 360p|720p] [--duration 4|6|8|10] [--count 1-4] [--project ID] [--yes]
flow repl
```
Fora da 0.1: apagar projeto, Personagens, Cenas, Ferramentas, modo Agente.

## Fatias (plan-big-execute-small)
| # | Fatia | Modelo |
|---|---|---|
| 1 | Esqueleto: `pyproject.toml`, pacote, Click, `--json`, pytest, README | gemini-3.8-flash-low |
| 2 | Backend Playwright: perfil persistente, `auth login/status`, helpers de espera e clique | gemini-3.8-flash-medium |
| 3 | Leituras: `projects list`, `models list`, `credits`, `media list` | gemini-3.8-flash-medium |
| 4 | `generate image` e `generate video` com dry-run, custo e `--yes` | gemini-3.8-flash-medium |
| 5 | `media download`, `projects create/open`, REPL | gemini-3.8-flash-medium |
| 6 | Testes de integração (marcados, opt-in, sem gastar crédito), README final | gemini-3.8-flash-low |

Cada fatia: teste primeiro, `pytest` verde, commit convencional só com os arquivos da fatia.

## Regras de teste
- Testes unitários não tocam na rede nem no navegador (backend com dupla de teste).
- Testes de integração só com `FLOW_CLI_LIVE=1` e nunca geram mídia sem `--yes` explícito.
