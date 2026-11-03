# Exploração do Google Flow (2026-11-03)

Mapeamento feito pelo navegador, com conta PRO logada, **sem gerar nada** (só abrir menus).

## Como o site funciona por baixo
- Frontend Angular do "AI Sandbox" do Google (`boq_labs-ai-sandbox-frontend`), servido em `https://flow.google.com`.
- **Não há API pública.** O site fala com o servidor por `batchexecute`, o RPC interno do Google:
  `POST /_/AiSandboxAngularFrontend/data/batchexecute?rpcids=<ID>&bl=<versão>&f.sid=<sessão>&hl=pt&_reqid=<n>&rt=c`
- IDs de RPC vistos ao abrir a tela inicial: `o30O0e`, `cPZSdc`, `nzlxg`, `NfrxTb`, `Yizz8d`, `KV2T2d`, `xI9TVb`, `UpteDb`. Os nomes das ações ainda não foram decifrados.
- Exige cookies da conta Google, o `bl` (versão do build, muda a cada release) e o `f.sid`. A geração usa **reCAPTCHA Enterprise**.
- Imagens e vídeos servidos em `https://flow.google.com/asb/...`.
- Consequência: chamar o RPC direto é frágil (o `bl` e os parâmetros mudam) e o reCAPTCHA atrapalha a geração.

## Mapa da interface
**Tela inicial:** lista de projetos (cartões com data), botão "Novo projeto", links para Flow Music e Flow TV, crédito diário.

**Projeto** (`/project/<uuid>`), menu lateral:
Todas as mídias, Imagens, Personagens, Cenas, Biblioteca (com "+"), Ferramentas, Criar ferramenta, Lixeira.
Barra superior: busca, filtro, "+", ajuda, configurações.

**Caixa de prompt** ("O que você quer criar?"): botão "+" (anexar), modo "Agente", chip de configuração e seta de enviar.

**Chip de configuração:**
| | Imagem | Vídeo |
|---|---|---|
| Proporção | 16:9, 4:3, 1:1, 3:4, 9:16 | 16:9, 9:16 |
| Modelo | Nano Banana 2.1 (lista a confirmar) | Omni 1.1 Flash, Veo 3.1 Lite, Veo 3.1 Fast, Veo 3.1 Quality |
| Modo | | Frames, Elementos |
| Resolução | | 360p, 720p |
| Duração | | 4s, 6s, 8s, 10s |
| Quantidade | x1, x2, x3, x4 | x1, x2, x3, x4 |

**Custo:** o chip mostra "A geração vai usar N créditos" antes de enviar (imagem Nano Banana 2.1 x2 = 0 créditos; vídeo Omni 1.1 Flash 720p 8s x2 = 24 créditos). Isso permite um `--dry-run` que informa o custo.

## Pontos em aberto
- Lista completa de modelos de imagem.
- Como funcionam "Frames" e "Elementos" (anexos de entrada).
- Personagens, Cenas, Biblioteca, Ferramentas: o que cada um guarda.
- Como baixar uma mídia (menu de contexto ou botão).
- Fluxo "Agente".
- Decifrar os IDs de `batchexecute` para as leituras (listar projetos e mídias).

## Riscos
- Site sem API oficial: o CLI pode quebrar quando o Google mudar a interface.
- Automatizar a interface pode ir contra os termos de uso do Google. Uso pessoal, na própria conta.
- Geração gasta crédito: todo comando que gera exige confirmação explícita.
