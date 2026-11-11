# CineRepertório

Aplicação web em **Flask + SQLite** que reúne filmes utilizáveis como **repertório sociocultural**
na redação do ENEM: nota do IMDb, sinopse, temas, parágrafo ideal, citação pronta,
links para assistir, **assistente de redação com IA**, contas com **verificação em duas etapas**,
anotações pessoais por usuário e um painel de **acessibilidade**.

Projeto da **UC35 — Projeto Integrador Back-end**.

## Como executar no Windows (recomendado)

1. Extraia o ZIP inteiro para uma pasta simples, por exemplo `C:\CineRepertorio`.
2. Abra essa pasta e dê dois cliques em `INICIAR_CINEREPERTORIO.bat`.
3. O inicializador usa o Flask do Python detectado; se não encontrar, cria um ambiente `.venv` e instala `requirements.txt`.
4. Abra `http://127.0.0.1:5000` no navegador. Mantenha a janela preta aberta enquanto estiver usando o site.

Para iniciar manualmente, abra o terminal **nesta pasta**, e execute:

```powershell
python -m pip install -r requirements.txt
python app.py
```

> Importante: o Flask precisa estar instalado no mesmo Python usado para executar `app.py`. Confira com `python -c "import sys, flask; print(sys.executable); print(flask.__version__)"`.

## Atualização visual — experiência streaming (11/11/2026)

- A página inicial ganhou uma parede de cartazes do próprio catálogo, em três faixas
  translúcidas que se movem lentamente em direções alternadas.
- As setas do carrossel agora usam uma transição de deslocamento com aceleração e
  desaceleração, avançando por grupos de cartazes e mantendo o loop infinito.
- Os cartazes receberam zoom, elevação, brilho violeta e entrada gradual da sobreposição.
- O fundo e as animações respeitam a preferência do sistema por movimento reduzido.

Para atualizar uma instalação existente, substitua `templates/index.html`,
`templates/base.html`, `static/estilo.css` e `static/script.js`. Preserve o seu
`.env`, `banco.db` e `.venv`. Depois reinicie o Flask e atualize o navegador com
`Ctrl + F5`.

## Como executar no Linux/macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
```

Acesse: http://127.0.0.1:5000

## Banco de dados (SQLite)

Todos os dados ficam em `banco.db`.
As tabelas são criadas por `sql/schema.sql` — o app também as cria sozinho se o arquivo
estiver vazio — e os 112 filmes de exemplo estão em `sql/dados_iniciais.sql`.

```
filmes       (id PK, titulo, ano, diretor, imdb, sinopse, como_usar, citacao, parte, cor, cartaz)
temas        (id PK, nome UNIQUE)
filme_temas  (filme_id FK → filmes, tema_id FK → temas, PK composta)      -- N:N filmes x temas
usuarios     (id PK, nome, sobrenome, email UNIQUE, salt, senha_hash, a2f, iniciais, criado_em)
anotacoes    (id PK, usuario_id FK→usuarios, filme_id FK→filmes, parte, texto, criado_em)
```

- **CRUD completo:** anotações do usuário (criar, listar, editar, excluir) e cadastro de usuários.
- **JOINs:** catálogo com temas, filmes relacionados por tema e anotações com o título do filme.
- **Senhas:** guardadas apenas como hash PBKDF2-SHA256 com salt; a senha original nunca é gravada.

Para recriar o banco do zero:

```bash
rm banco.db
sqlite3 banco.db < sql/schema.sql
sqlite3 banco.db < sql/dados_iniciais.sql
```

## Estrutura do projeto

```
cinerepertorio/
├── app.py              # rotas e regras da aplicação
├── banco.py            # conexão e criação do banco SQLite
├── contas.py           # cadastro, login e verificação em duas etapas (A2F)
├── ia.py               # roteamento do assistente Briggs e recursos de redação
├── br_local.py         # motor offline de respostas combinatórias e base temática
├── banco.db            # banco SQLite com dados de exemplo
├── sql/
│   ├── schema.sql          # criação das tabelas
│   └── dados_iniciais.sql  # INSERTs dos 112 filmes
├── requirements.txt    # flask, gunicorn
├── Procfile            # web: gunicorn app:app  (Render)
├── testes.py           # testes automatizados (usam cópia do banco)
├── testes_briggs_local.py # testes do modo offline, sem acesso externo
├── static/
│   ├── estilo.css
│   ├── script.js
│   ├── icon/           # favicon (svg, ico, png) e apple-touch-icon
│   └── img/
└── templates/          # base.html + páginas (herança Jinja2)
```

## Rotas

| Rota | Métodos | Função |
|---|---|---|
| `/` | GET | Página inicial com vitrine do dia e esteiras de cartazes |
| `/filmes` | GET | Catálogo com busca, filtro por tema/parágrafo e ordenação |
| `/filmes/<id>` | GET | Detalhe do filme, relacionados (JOIN) e suas anotações |
| `/conta/criar` | GET, POST | Cadastro de usuário (CREATE) |
| `/conta/entrar` | GET, POST | Login e troca de conta |
| `/conta/verificar` | POST | Código da verificação em duas etapas |
| `/conta/sair` | GET | Encerrar a sessão |
| `/anotacoes` | GET, POST | Listar e criar anotações (exige login) |
| `/anotacoes/<id>/editar` | POST | Editar anotação (UPDATE) |
| `/anotacoes/<id>/excluir` | POST | Excluir anotação (DELETE) |
| `/assistente` | GET | Página do assistente de redação |
| `/api/assistente` | POST | **JSON**: resposta do assistente de IA |
| `/api/filmes` | GET | **JSON**: lista de filmes (`?busca=`, `?tema=`, `?parte=`, `?ordem=`) |
| `/api/filmes/<id>` | GET | **JSON**: um filme com seus temas |
| `/estrutura` | GET | Guia da estrutura da redação |
| `/acessibilidade` | GET | Recursos de acessibilidade |
| `/sobre` | GET | Documentação |

## Diagnóstico e testes

Com Flask instalado no Python que será usado para executar o site:

```bash
python diagnostico.py
python testes.py
python testes_email.py
```

Os testes de e-mail simulam o servidor SMTP e não enviam mensagens reais. No Windows, também é possível executar `TESTAR_CINEREPERTORIO.bat`.

## Deploy no Render

1. Suba o projeto para um repositório no GitHub (com `banco.db`, `requirements.txt` e `Procfile`).
2. No Render: **New → Web Service**, conecte o repositório.
3. Build command: `pip install -r requirements.txt` · Start command: `gunicorn app:app`.
4. (Opcional) Defina a variável `CINE_SECRET` com uma chave secreta própria.

> No plano gratuito do Render o disco é temporário: contas e anotações criadas online voltam
> ao estado do `banco.db` do repositório quando o serviço reinicia ou é publicado de novo.

## Acessibilidade

Link "pular para o conteúdo", HTML semântico, `alt` nas imagens, `label` em todos os campos,
avisos com `aria-live`, foco visível, alto contraste, modos para daltonismo, fonte ampliada,
redução de animações, leitura da página em voz alta, tradutor de Libras (VLibras) e respeito a
`prefers-reduced-motion`.

## Cartazes pelo TMDB
`python buscar.py` (teste, não grava cartazes) e `python buscar.py --aplicar` (grava no banco). Configure `TMDB_KEY` no `.env` antes de executar.


## Configuração do envio de mensagens

A página `/notificacoes` encaminha os contatos para `cinerepertorio@gmail.com`. O envio usa
SMTP autenticado com TLS e aceita Gmail pela porta `587` (STARTTLS) ou `465` (SSL).

### Gmail

1. Copie `.env.example` e renomeie a cópia para `.env`, na mesma pasta de `app.py`. Escolha a conta que será usada pelo site para enviar as mensagens. Ela pode ser
   `cinerepertorio@gmail.com`; nesse caso, as mensagens serão enviadas e recebidas pela mesma conta.
2. Na Conta Google, ative a verificação em duas etapas e gere uma senha de app, caso essa opção
   esteja disponível para a conta. A senha normal do Google não deve ser usada no SMTP.
3. Preencha os valores no arquivo `.env` para execução local ou configure as mesmas variáveis no serviço de hospedagem:

   | Variável | Valor para Gmail |
   |---|---|
   | `SMTP_HOST` | `smtp.gmail.com` |
   | `SMTP_PORT` | `587` |
   | `SMTP_USER` | endereço Gmail completo que autentica o envio |
   | `SMTP_PASSWORD` | senha de app da conta (esta implementação SMTP não autentica com OAuth) |
   | `SMTP_FROM` | o mesmo endereço de `SMTP_USER` |
   | `SMTP_USE_SSL` | `false` (use `true` com a porta `465`) |
   | `SMTP_TIMEOUT` | `20` |

   O destino já está definido no código como `cinerepertorio@gmail.com`. O campo `Reply-To`
   recebe o e-mail informado pela pessoa no formulário, para facilitar a resposta.

### Configuração local no Windows

Na pasta do projeto, execute `Copy-Item .env.example .env` no PowerShell e abra o arquivo `.env` no Bloco de Notas. Preencha `SMTP_PASSWORD` com a senha de app do Gmail e confira `SMTP_USER`/`SMTP_FROM`. O `app.py` carrega esse arquivo automaticamente. Não publique o valor real de `SMTP_PASSWORD`, não o coloque no GitHub e não o envie por mensagem. Para o Render, cadastre os mesmos nomes em **Dashboard → seu serviço → Environment** e faça novo deploy.

### Testes de e-mail

Os testes usam um servidor SMTP simulado e **não enviam e-mails reais**:

```bash
python testes_email.py
```

A suíte geral do projeto continua disponível em `python testes.py`. Um teste real de entrega só
pode ser confirmado depois que as credenciais SMTP forem configuradas no computador ou na hospedagem.

> Nota de segurança: senhas de app dependem da verificação em duas etapas e podem não estar
disponíveis em algumas contas. Para integrações de produção, o Google recomenda autenticação OAuth 2.0.

## Identidade visual roxa

A versão atual utiliza fundo escuro com roxo/violeta como cor principal, brilhos discretos e dourado reservado a pequenos detalhes cinematográficos, como avaliações. As páginas e funcionalidades do sistema foram preservadas.

## Carrossel infinito e animação dos cartazes

A página inicial duplica visualmente as duas faixas de cartazes antes e depois da lista original. Assim, as setas e o gesto de arrastar continuam funcionando em loop, sem desativar as setas nas extremidades. O reposicionamento acontece somente depois que a rolagem termina, para preservar a animação suave.

Ao passar o mouse ou navegar até um cartaz pelo teclado, o cartão ganha elevação e brilho violeta, a imagem recebe um zoom discreto e a camada de informações aparece gradualmente. Em dispositivos com toque, as informações permanecem visíveis. As animações respeitam a preferência do sistema por movimento reduzido.


## Briggs: parceiro de cinema e organização das redações

O assistente se chama Briggs e usa o personagem masculino enviado para o projeto: um cavalheiro com cabeça de câmera, traje elegante e claquete. Ele atua como parceiro de cinema e escrita: confiante, espirituoso, observador e prestativo, com humor leve, comunicação direta e referências cinematográficas. A imagem original está em `static/img/assistente-cinema.jpg`. A área de redação mantém recursos locais de estrutura e catálogo. Com a configuração opcional da API descrita abaixo, Briggs também passa a conversar livremente sobre assuntos gerais com um modelo generativo.

Ao solicitar uma redação-modelo, Briggs organiza a resposta nesta ordem:

1. Projeto de texto: recorte, tese, dois argumentos e repertório relacionado quando disponível.
2. Introdução: contextualização, tema e tese.
3. Desenvolvimento 1: primeiro argumento com explicação.
4. Desenvolvimento 2: segundo argumento com análise e repertório complementar, quando houver.
5. Conclusão: proposta de intervenção e identificação de agente, ação, meio, finalidade e detalhamento.

A página `/estrutura` também inclui um roteiro de planejamento e checklist de revisão. A análise automática de redação é indicativa e não substitui uma correção oficial do ENEM.


## Briggs — modo offline expandido e conversa local

O Briggs funciona por padrão sem API, sem chave, sem conexão externa e sem cobrança. O motor local combina uma biblioteca temática de conhecimento, estruturas de resposta, variações de linguagem, exemplos, perspectivas, níveis de detalhe e encerramentos. A capacidade teórica é superior a 500 milhões de combinações possíveis; isso não significa que haja 500 milhões de textos completos guardados no projeto. As respostas são montadas dinamicamente com a base local.

O modo offline inclui apoio a estudos, matemática, biologia, física, química, história, geografia, português, inglês, tecnologia, inteligência artificial, programação, filosofia, literatura, meio ambiente, cinema, redação, planejamento, criatividade e outros temas gerais. Mantém o histórico recente da conversa na aba atual do navegador, para ajudar em perguntas de acompanhamento. Como não consulta a internet, não deve ser tratado como fonte de notícias ou informações atuais; assuntos muito específicos podem exigir conferência externa.

A integração remota com a OpenAI permanece opcional. Para ativá-la futuramente, um responsável adulto deve administrar a conta, a chave e qualquer cobrança. Preencha `OPENAI_API_KEY` no `.env` e defina `BRIGGS_USE_API=true`. Sem essa ativação explícita, o aplicativo permanece no modo offline, mesmo que uma chave esteja presente no ambiente. Nunca coloque a chave no HTML, JavaScript ou no chat.

O endpoint limita mensagens a 5.000 caracteres, mantém no máximo 12 mensagens anteriores enviadas pelo navegador e aplica um limite básico de frequência por endereço IP. No modo remoto, o pedido usa `store: false`; no modo offline, nenhuma mensagem é enviada a um serviço externo.

## Carrossel

As setas apenas controlam a navegação. A animação é aplicada ao trilho inteiro de cartazes com uma curva ease-in-out suave; os botões não fazem movimentos ou efeitos de destaque durante o clique. O loop infinito e a preferência `prefers-reduced-motion` são preservados.

## Ampliar a janela de conversa do Briggs

Ao abrir o assistente flutuante, use o botão de ampliar (ícone de quatro cantos) no cabeçalho da conversa para fazê-la ocupar quase toda a tela. O mesmo botão restaura o painel ao tamanho compacto. No modo ampliado, a rolagem da página fica bloqueada para manter o foco na conversa; ao fechar ou restaurar a janela, a rolagem volta ao normal. O controle funciona em desktop e celular e possui rótulos acessíveis para leitores de tela.


## Atualização do Briggs — interface e materiais externos

- O cabeçalho da conversa mostra apenas **Briggs**; durante a resposta, o estado muda para **Briggs respondendo...**.
- Ao ampliar a conversa, o retrato pequeno do personagem no cabeçalho é ocultado para liberar espaço para as mensagens.
- Quando o usuário pede explicitamente vídeos, videoaulas, tutoriais, links ou materiais de estudo, o modo offline exibe cartões para buscas no YouTube e em fontes educacionais.
- Esses cartões abrem resultados de busca, não vídeos individuais verificados. O Briggs informa isso com transparência porque o modo offline não navega nem confirma a qualidade ou a atualidade de cada resultado.
- Os links são abertos em nova aba e a interface aceita apenas destinos HTTPS do YouTube e do Google.

Para experimentar, abra o Briggs e pergunte, por exemplo: **“Me mande vídeos sobre fotossíntese”** ou **“Quero links para aprender Python”**.
