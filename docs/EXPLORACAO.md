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

## Seletores e rotas verificados (scout das fatias 3-6, 2026-11-03, headless, só leitura)

Tudo abaixo foi lido da interface logada (PT-BR) sem gerar nada. Fonte dos textos: `aria_snapshot` do Playwright.

### Home (`https://flow.google.com/`)
- Cada projeto é um `a[href^="/project/"]` (aria-label "Abrir projeto"); o id é o UUID do href. O cartão mostra só a data ("nov. 03 - 15:49"), que é o título padrão. Os botões "Editar título do projeto" e "Excluir projeto" existem em cada cartão (o CLI nunca os usa).
- Botão "Novo projeto" (`get_by_role("button", name="Novo projeto")`) cria um projeto. Não testado ao vivo (cria dado na conta e o CLI não apaga).
- **Créditos:** o botão `get_by_role("button", name="Detalhes da conta")` abre o `dialog "Configurações da conta"`, que contém o link "1.050 créditos do Google Flow" e o texto "Redefinição do limite de uso: 20 de nov., 20:08". O número usa ponto como separador de milhar.

### Projeto (`/project/<uuid>`)
- Título: `heading level=1` (e `textbox "Texto editável"` para renomear).
- Menu lateral: botões "Todas as mídias", "Imagens" (só aparece quando há imagens), "Personagens", "Cenas"; links Biblioteca, `/tools`, `/create-tool`, `/trash`.
- Mídias: cada mídia é um `group` (aria-label = nome do arquivo ou prompt) com `img[data-media-id="<uuid>"]`, `src=https://flow.google.com/asb/...=s512-rw` (miniatura). Vídeos: não havia nenhum no projeto explorado; a distinção imagem/vídeo é feita pela presença de `<video>` ou ícone de play no cartão (**não verificado ao vivo**).
- Ao passar o mouse sobre a mídia aparecem "Favorito", "Reutilizar comando", "Mais opções".
- Clicar na mídia abre o detalhe **sem mudar a URL**, com os botões: "Botão \"Voltar\"...", "Mostrar informações do recurso", "Favorito", "Compartilhar mídia", "Mover para a lixeira", **"Baixar mídia"**, "Ocultar histórico".

### Caixa de prompt e chip de configuração
- `textbox "O que você quer criar?"`; botão enviar `button "Iniciar geração"` (desabilitado com prompt vazio). **O CLI só clica nele com `--yes`.**
- Chip: `button "Gatilho de configurações"` (texto: "🍌 Nano Banana 2.1 x2" ou "Vídeo · 720p · 8s x2"). A configuração fica memorizada pelo navegador.
- Popup: `radiogroup` com `radio "Imagem"`/`radio "Vídeo"`; proporção `radio "16:9"` etc.; `button "Selecionar família de modelos"` abre a lista de modelos; `radio "x1".."x4"`; texto "A geração vai usar N créditos" (link "N créditos").
- Imagem: proporções 16:9, 4:3, 1:1, 3:4, 9:16. **Modelos de imagem:** Nano Banana Pro, Nano Banana 2 Lite, Nano Banana 2.1.
- Vídeo: Modo `radio "Frames"`/`radio "Elementos"`, proporções 16:9 e 9:16, resolução `360p`/`720p`, duração `4s 6s 8s 10s`. **Modelos de vídeo:** Omni 1.1 Flash, Veo 3.1 - Lite, Veo 3.1 - Fast, Veo 3.1 - Quality.
- **Custo lido sem enviar** (Omni 1.1 Flash, 720p, 8s, x2 = 24 créditos). O texto "A geração vai usar N créditos" atualiza ao mudar qualquer opção, mesmo com prompt preenchido, então o dry-run é possível sem gastar. Matriz observada (Omni 1.1 Flash): 360p=12, 720p=24; 4s=14, 6s=20, 8s=24, 10s=30; x1=15, x2=30, x3=45, x4=60 (os valores variam conforme a combinação). Imagem Nano Banana 2.1 = 0 créditos nesta conta.

### Pontos em aberto (após esta exploração)
- Download: o botão "Baixar mídia" existe no detalhe; o CLI tenta o arquivo original pela URL `/asb/...` da miniatura, com cookies da sessão.
- Distinção imagem/vídeo na lista de mídias não verificada com vídeo real.
- Criar projeto e gerar de verdade não foram exercitados ao vivo (efeitos na conta/créditos).

### Custo ao vivo via `flow generate` (dry-run, verificado)
O dry-run lê o custo do `flow-prompt-box-settings` depois de ~1,5s e só aceita a leitura quando duas leituras seguidas coincidem (a UI atualiza com atraso). Exemplos medidos (720p): Omni 1.1 Flash 4s x1 = 7, 8s x2 = 24, 10s x1 = 15; Veo 3.1 - Fast 4s x1 = 20; Nano Banana 2.1 x2 = 0. Alguns modelos (ex. Veo 3.1 - Fast) não têm o radio de resolução; o CLI ignora a opção indisponível. O envio real (`--yes`) só foi exercitado com dupla de teste.
