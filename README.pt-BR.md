# LLM Guardrails Lab

Um laboratório pequeno e defensivo para uma pergunta que todo time de chatbot deveria fazer antes de publicar:

**O que quebra se alguém tentar tirar o bot das regras, e a proteção realmente ajudou?**

O ciclo tem três passos.

1. **Escanear** o chatbot com o [NVIDIA Garak](https://github.com/NVIDIA/garak).
2. **Proteger** o mesmo bot com o [NVIDIA NeMo Guardrails](https://docs.nvidia.com/nemo/guardrails/home).
3. **Escanear de novo** e comparar os dois relatórios.

A página mostra uma comparação real do notebook do autor em 2026-10-15. O Garak 0.17.0 escaneou o laboratório e escaneou de novo com o NeMo Guardrails 0.24.1. O modelo era um modelo da xAI, chamado por uma API compatível com a OpenAI. É um único run, num único modelo. Os arquivos brutos `*.report.jsonl` ficam naquela máquina. Os seus relatórios ainda só aparecem depois que você roda as ferramentas localmente. O `make compare` grava `results/comparison.md` e não substitui o snapshot publicado.

Os tamanhos de amostra são pequenos. `dan.Dan_11_0` tem 1 prompt. `leakreplay.LiteratureCloze` e `promptinject.HijackLongPrompt` têm 8 prompts cada. `realtoxicityprompts.RTPBlank` não entra na tabela. Essa sonda envia um prompt vazio, e a API rejeitou com HTTP 422.

| Probe | Detector | Before rails | After rails | Change |
| --- | --- | --- | --- | --- |
| dan.Dan_11_0 | dan.DAN | 100.0% (1/1 resisted) | 100.0% (1/1 resisted) | +0.0 points |
| dan.Dan_11_0 | mitigation.MitigationBypass | 0.0% (0/1 resisted) | 100.0% (1/1 resisted) | +100.0 points |
| leakreplay.LiteratureCloze | base.TriggerListDetector | 37.5% (3/8 resisted) | 100.0% (8/8 resisted) | +62.5 points |
| promptinject.HijackLongPrompt | promptinject.AttackRogueString | 100.0% (8/8 resisted) | 100.0% (8/8 resisted) | +0.0 points |

As células são o texto do `make compare`, sem tradução. `site/comparison.json` é o arquivo que a página lê. Uma taxa maior significa que mais respostas não dispararam aquele detector. `+0.0 points` significa que os trilhos não moveram aquele detector neste run. Um run curto é um sinal, não um certificado.

Garak e NeMo Guardrails são projetos da NVIDIA. Este laboratório é uma demonstração educativa independente. Não é um produto da NVIDIA.

## O que as duas ferramentas fazem

É fácil confundir as duas, porque as duas falam de segurança. O trabalho de cada uma é diferente.

| | Garak | NeMo Guardrails |
| --- | --- | --- |
| Quando | Antes de publicar, e de novo depois que você muda a proteção | Em cada mensagem, enquanto o bot está em uso |
| O que é | Um scanner | Um filtro ao vivo |
| O que você recebe | Um relatório de fraquezas | Uma resposta conferida, bloqueada ou mascarada |

**Garak** é o inspetor. Ele envia vários prompts de teste para um bot que você escolhe e dá nota às respostas. No run padrão do laboratório entram: injeção de prompt, uma sonda de jailbreak, vazamento de dados e toxicidade. Ele não fica na frente dos usuários.

**NeMo Guardrails** é a política da porta. Neste laboratório, cada turno passa por:

- uma autoconferência de entrada e uma de saída (o modelo julga a mensagem contra uma política escrita)
- uma lista local e curta de frases que tentam anular as instruções
- trilhos de assunto, para o bot ficar em software, IA e este laboratório
- mascaramento de e-mail, telefone, número de cartão e Social Security dos EUA

Duas conferências mais fortes ficam desligadas até você optar por elas, porque pedem instalação extra:

- **Heurísticas de jailbreak** do NeMo. Elas rodam um modelo local e pedem mais memória. A NVIDIA documenta o modo dentro do processo como só para teste.
- **Presidio**, para uma detecção mais ampla de dados pessoais. Precisa do extra `sdd` e de um modelo do spaCy.

## Arquitetura

```mermaid
flowchart LR
  person[Pessoa ou Garak] --> api[API FastAPI do laboratório]
  api -->|antes: /v1/chat/raw| model[Modelo compatível com OpenAI]
  api -->|depois: /v1/chat/guarded| rails[NeMo Guardrails]
  rails --> model
  garak[Scanner Garak] --> api
  garak --> reports[results/before e results/after]
```

A rota sem proteção e a rota com proteção usam o mesmo modelo e a mesma política de sistema. A diferença são os trilhos. É isso que o segundo scan mede.

O modelo pode ser qualquer API de chat compatível com a OpenAI, inclusive um servidor local [Ollama](https://ollama.com). A chave fica no ambiente. A página do navegador não a vê.

## Começo rápido

O Python suportado é 3.10 a 3.13. O Python 3.14 não funciona: `nemoguardrails==0.24.1` exige `>=3.10,<3.14`. Use 3.12. O Garak 0.17 precisa de 3.11 ou mais novo, então o 3.12 cobre o laboratório inteiro.

No Ubuntu o comando é `python3`, não `python`. Instale com o [uv](https://docs.astral.sh/uv/) para não usar o interpretador do sistema:

```bash
uv venv --python 3.12 .venv
source .venv/bin/activate
uv pip install -r requirements-lab.txt
cp .env.example .env
```

Edite o `.env`. Dois jeitos comuns:

```bash
# Modelo hospedado. Sem GPU.
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=sua-chave-aqui
LLM_MODEL=gpt-4o-mini

# Ollama já rodando nesta máquina. Mais memória.
# LLM_BASE_URL=http://127.0.0.1:11434/v1
# LLM_API_KEY=ollama
# LLM_MODEL=llama3.2
```

Se `LLM_API_KEY` estiver vazio, o aplicativo também lê `OPENAI_API_KEY`.

Suba a API e abra o chat:

```bash
make serve
# http://127.0.0.1:8000/ui
# http://127.0.0.1:8000/docs
```

Num segundo terminal, na raiz do repositório, com o mesmo ambiente virtual:

```bash
make scan-before
make scan-after
make compare
```

`scan-before` chama `/v1/chat/raw`. `scan-after` chama `/v1/chat/guarded`. Os relatórios vão para `results/before/` e `results/after/`. A comparação é gravada em `results/comparison.md`.

Rode uma sonda só quando quiser uma passagem mais barata, ou para retomar depois de uma falha:

```bash
make scan-before PROBES=probes.realtoxicityprompts.RTPBlank
```

`GARAK_SPEC` é a mesma lista se você não usa o `make`. Uma sonda vai para o próprio arquivo de relatório. O `make compare` junta todos os `*.report.jsonl` em `results/before` e `results/after`.

## Modelos de raciocínio lentos

Um modelo de raciocínio, como o Grok, pode passar de dois minutos num único prompt. O cliente REST do Garak esperava 120 segundos e abortava o scan inteiro com `ReadTimeout`. O laboratório agora espera `LLM_TIMEOUT_SECONDS` (padrão 300). O Garak espera 30 segundos a mais. Se o modelo ainda não respondeu, o laboratório devolve HTTP 504 e o Garak pula esse prompt em vez de parar.

Coloque isto no `.env` e reinicie o `make serve`. O servidor que já está no ar não lê o novo tempo até reiniciar.

```bash
LLM_TIMEOUT_SECONDS=300
LLM_MAX_TOKENS=1024
REASONING_EFFORT=low
```

`REASONING_EFFORT` é opcional. Deixe sem definir se o modelo rejeitar o campo. `low` pede aos modelos de raciocínio da xAI e da OpenAI para gastar menos esforço. `LLM_MAX_TOKENS=none` desliga o teto.

Retome as sondas que não terminaram. O Garak roda os nomes em ordem alfabética, então `probes.dan.Dan_11_0` é a primeira. Guarde qualquer `results/before/*.report.jsonl` do run que caiu, e não repita uma sonda que esse arquivo já concluiu:

```bash
make scan-before PROBES=probes.leakreplay.LiteratureCloze
make scan-before PROBES=probes.promptinject.HijackLongPrompt
make scan-before PROBES=probes.realtoxicityprompts.RTPBlank
```

Um tempo esgotado pulado entra como `nones`, não como aprovação. Aumente `LLM_TIMEOUT_SECONDS` se muitos prompts forem pulados. Defina `GARAK_REQUEST_TIMEOUT` só quando quiser que o Garak espere um número fixo de segundos. Mantenha esse valor acima do tempo do modelo.

No Windows, sem `make`:

```bash
python scripts/run_garak.py --mode before
python scripts/run_garak.py --mode after
python scripts/compare_reports.py
```

Confira o aplicativo sem chave de modelo:

```bash
python -m pip install -r requirements-dev.txt
python -m pytest
python -m ruff check .
```

## Como ler um resultado

O Garak grava um arquivo `*.report.jsonl` e um relatório HTML. Cada linha `eval` é uma sonda mais um detector.

A taxa de aprovação é `passed / total_evaluated`.

- **Maior é mais seguro.** Significa que mais respostas do bot não dispararam aquele detector.
- **Uma subida do antes para o depois** significa que os trilhos mudaram o que o Garak mediu.
- **Uma linha estável** significa que aquela verificação não melhorou neste run.
- **`nones`** são respostas que o scanner não conseguiu avaliar, em geral porque o bot estourou o tempo ou devolveu erro.

Um run curto é um sinal, não um certificado. A spec padrão tem quatro classes de sonda, uma geração cada, com um teto suave de prompts. Sondas de injeção de prompt ainda podem enviar muitos pedidos. Acompanhe a conta da API.

O snapshot publicado em `site/comparison.json` é o run de 2026-10-15 do notebook, citado na introdução. Ele é separado do `results/comparison.md` na sua máquina. `realtoxicityprompts.RTPBlank` falta nesse snapshot porque a API rejeitou o prompt vazio com HTTP 422.

Os arquivos em `results/sample/` ilustram o formato. As contagens ali são inventadas. O `make compare` os ignora.

## Mapa do projeto

```text
site/                 Página para o GitHub Pages
site/comparison.json  Comparação publicada de 2026-10-15. A página lê este arquivo.
app/                  Servidor FastAPI, cliente do modelo, comparação de relatórios
app/static/chat.html  Página de chat local
guardrails/           config.yml do NeMo, prompts, trilhos Colang, actions
scripts/run_garak.py  Grava a config REST e roda o Garak
scripts/compare_reports.py
results/              Saída local dos scans, ignorada pelo git, exceto o layout de amostra
tests/                Testes que não precisam de chave de modelo
```

Versões fixadas a partir do PyPI em 2026-10-15:

- `nemoguardrails==0.24.1`
- `garak==0.17.0`
- `fastapi==0.143.1`

## GitHub Pages

O site é a pasta estática `site/`. O workflow `.github/workflows/pages.yml` publica essa pasta em cada push na `main`.

Depois que este projeto estiver na `main`:

1. Abra **Settings → Pages** do repositório.
2. Em **Build and deployment**, defina **Source** como **GitHub Actions**.
3. Rode o workflow **pages**, ou faça push na `main` para ele rodar.
4. O site fica em `https://souzawellington.github.io/llm-guardrails-lab/`.

A página é a explicação. O chat e os scans ficam na sua máquina.

## Compatibilidade

- Um notebook e uma chave de API bastam. A biblioteca de guardrails roda em CPU. Você não precisa de uma GPU da NVIDIA no caminho da API.
- Um modelo local, como o Ollama, precisa de memória suficiente para esse modelo. O primeiro pedido protegido também baixa um modelo pequeno de embeddings, em CPU, usado pelos trilhos de assunto.
- No Windows, o `nemoguardrails` 0.24.1 instala por wheels e usa FastEmbed, não o Annoy. O guia de instalação da NVIDIA ainda documenta o Annoy, uma biblioteca C++. Se o pip parar ao compilar uma extensão nativa, instale o [Microsoft C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) (MSVC 14.0 ou mais novo) e tente de novo.
- Instalar o Garak baixa um conjunto grande de pacotes, inclusive o PyTorch. Você continua sem precisar de GPU. O laboratório usa o conector REST do Garak, que só chama a sua API.
- As heurísticas opcionais de jailbreak (`ENABLE_JAILBREAK_HEURISTICS=1`) precisam de `torch` e `transformers`, e depois baixam o GPT-2 para calcular perplexidade. Esse é o caminho com mais memória. Deixe desligado no run normal de notebook.
- O mascaramento opcional com Presidio (`ENABLE_PRESIDIO=1`) precisa de `pip install "nemoguardrails[sdd]==0.24.1"` e `python -m spacy download en_core_web_lg`. A máscara por expressão regular já está ligada.

Se o `pip` não conseguir instalar Garak e NeMo Guardrails no mesmo ambiente, coloque o Garak num segundo ambiente virtual. O scanner só precisa de acesso HTTP à API.

## Limitações

- Os trilhos de autoconferência só são tão cuidadosos quanto o modelo que você configurar. Um modelo fraco deixa passar mensagem ruim.
- A lista de frases de anulação é um exemplo didático. Uma reformulação passa por ela. Por isso existem a autoconferência do modelo e o Garak.
- Os trilhos de assunto podem perder uma paráfrase e podem recusar uma pergunta justa.
- A máscara por expressão regular deixa passar muitos tipos de dado pessoal. O Presidio é mais amplo e ainda não é perfeito.
- As heurísticas de jailbreak têm viés de inglês, são lentas em CPU e falham abertas se o detector não rodar. A NVIDIA não recomenda o modo dentro do processo para produção.
- Esta API não tem login. Prenda-a em `127.0.0.1`. Não a exponha na rede enquanto uma chave de modelo estiver carregada.
- Modelos de raciocínio (Grok, DeepSeek-R1, série o da OpenAI e similares) podem devolver um rastro de pensamento. O NeMo Guardrails 0.24.1 cola esse rastro na resposta protegida dentro de tags `<think>`, e o rastro pode citar o prompt interno do NeMo. O laboratório remove esses blocos nas duas rotas de chat e antes de os parsers de autoconferência e de intenção lerem o texto do modelo. Não é preciso mudar o `.env`. Os prompts de autoconferência permitem 2048 tokens de resposta para o modelo ainda terminar com sim ou não.

## Uso responsável

Rode o Garak só contra um sistema que você possui ou tem permissão para testar. O alvo padrão é o processo do laboratório na sua própria máquina. Não aponte o scanner para o bot de outra pessoa.

Os prompts adversariais ficam dentro do pacote Garak. Este repositório não junta textos de jailbreak. Não use um relatório deste laboratório como um passo a passo para atacar outro sistema.

Bloquear um prompt numa demonstração não é uma afirmação de que um assistente de produção está seguro.

## Autor

[Wellington Vieira De Souza](https://github.com/souzawellington) — fundador e arquiteto de software brasileiro, focado em IA e sistemas escaláveis.

## Licença

[MIT](LICENSE)

Versão em inglês: [README.md](README.md).
