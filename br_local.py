"""Motor local e combinatório de conversa do Briggs.

Não depende de API, internet ou serviços pagos. Combina estruturas, aberturas,
transições, exemplos, perspectivas, níveis de detalhe, tons e encerramentos
com uma base temática curada. A capacidade é combinatória: não são 500 milhões
de textos completos armazenados em disco.
"""
from __future__ import annotations

import math
import random
import re
import unicodedata
from typing import Any
from urllib.parse import quote_plus

NOME = "Briggs"

ABERTURAS = [
    "Vamos por partes.", "Boa pergunta.", "Vamos abrir esse assunto com calma.",
    "Certo, vamos organizar essa ideia.", "Esse tema merece uma boa explicação.",
    "Vamos iluminar esse ponto.", "Gosto de uma pergunta que vai direto ao assunto.",
    "Vamos construir a resposta passo a passo.", "Perfeito, vamos ao que importa.",
    "Há algumas camadas interessantes aqui.", "Vamos olhar para isso com atenção.",
    "Pode deixar: vamos transformar essa dúvida em algo claro.",
]
TONS = [
    "A ideia é explicar sem complicar.", "Vou manter o foco no que realmente importa.",
    "Sem rodeios, mas sem pular as partes importantes.", "Pense nisso como um mapa: primeiro o panorama, depois os detalhes.",
    "Uma boa explicação precisa ser clara e honesta.", "Vamos separar o essencial do que é complementar.",
    "Prefiro uma resposta útil a um discurso cheio de palavras difíceis.", "O objetivo é que você consiga usar essa ideia depois.",
    "Vou trazer contexto e um exemplo para deixar tudo mais concreto.", "Vamos dar a esse tema o tratamento que ele merece.",
    "Um pouco de método costuma resolver metade da confusão.", "Vamos manter a conversa leve e o raciocínio afiado.",
]
TRANSICOES = [
    "O ponto central é este:", "Para entender melhor, vale observar:", "Isso fica mais claro quando separamos três elementos:",
    "Uma forma prática de enxergar a questão é:", "O raciocínio pode ser organizado assim:", "Há alguns aspectos que ajudam a explicar:",
    "Em termos simples:", "O detalhe que costuma passar despercebido é:", "Agora, olhando para a aplicação:",
    "Vale destacar o seguinte:", "A explicação ganha força quando consideramos:", "Podemos traduzir isso em ideias menores:",
    "Um bom caminho é começar por:", "A lógica por trás disso envolve:", "O que realmente sustenta essa ideia é:",
    "Para sair da teoria e chegar à prática:", "Outra maneira de formular a mesma ideia é:", "O panorama fica mais nítido com este recorte:",
]
MOLDURAS_EXEMPLO = [
    "Um exemplo simples ajuda:", "Imagine a seguinte situação:", "Pense em um caso cotidiano:",
    "Trazendo para a prática:", "Um exemplo para visualizar:", "Considere esta pequena cena:",
    "Na vida real, isso pode aparecer assim:", "Para deixar concreto:", "Veja uma situação ilustrativa:",
    "Um caso que ajuda a fixar a ideia:", "Podemos visualizar isso deste modo:", "Em uma situação hipotética:",
    "Para conectar conceito e prática:", "Um exemplo bem direto:", "Imagine isso acontecendo em uma escola ou comunidade:",
    "Na prática, pense no seguinte:",
]
PERSPECTIVAS = [
    "Uma boa pergunta para testar a compreensão é: o que muda quando esse fator desaparece?",
    "O mais importante é perceber a relação entre causa, processo e consequência.",
    "Não confunda o conceito com um exemplo específico: o exemplo ilustra, mas não substitui a definição.",
    "Também vale considerar quem é afetado e em que contexto essa ideia funciona.",
    "Quando você explica o motivo, demonstra compreensão maior do que apenas decorar uma definição.",
    "Uma maneira de aprofundar é comparar o cenário ideal com o que acontece na prática.",
    "Observe como as partes se conectam; isoladas, elas contam só metade da história.",
    "Se houver diferentes interpretações, compare os argumentos antes de escolher uma conclusão.",
    "A aplicação depende do contexto, então evite transformar um exemplo em regra universal.",
    "Uma resposta sólida deixa claro o que se sabe e o que ainda precisaria ser verificado.",
    "Para estudar, tente explicar esse ponto com suas próprias palavras sem olhar a resposta.",
    "A perspectiva histórica, social ou científica pode mudar a maneira de interpretar o tema.",
    "O próximo passo é testar a ideia em um caso diferente daquele usado no exemplo.",
    "Em uma boa análise, a conclusão precisa acompanhar as evidências apresentadas.",
]
ENCERRAMENTOS = [
    "Se guardar uma coisa desta resposta, guarde a ideia central e a relação entre as partes.",
    "Esse é o núcleo do assunto; os detalhes podem ser aprofundados conforme a sua necessidade.",
    "Com essa base, você já consegue avançar para exemplos mais específicos.",
    "É assim que uma dúvida começa a virar conhecimento utilizável.",
    "A melhor forma de fixar é tentar explicar o conceito para outra pessoa.",
    "Uma boa próxima etapa é aplicar esse raciocínio a uma situação concreta.",
    "E pronto: agora temos um primeiro mapa para explorar o tema.",
    "A chave está em compreender o processo, não apenas memorizar palavras.",
    "Use o exemplo como ponto de partida, não como única possibilidade.",
    "Se o assunto exigir dados recentes, será importante conferir uma fonte atualizada.",
    "O importante é manter a curiosidade e verificar as ideias com cuidado.",
    "Com um pouco de prática, esse raciocínio fica muito mais natural.",
    "Esse é um bom começo; uma explicação completa pode ganhar novas camadas.",
    "Guarde a estrutura e adapte os detalhes ao problema que estiver resolvendo.",
    "Uma conclusão responsável considera tanto os benefícios quanto os limites.",
    "A conversa continua aberta: podemos aprofundar qualquer uma dessas partes.",
    "Pronto: assunto organizado, sem precisar de trilha sonora dramática.",
    "E como diria um bom diretor: clareza na ideia, precisão na execução.",
]
FORMATOS = [
    "ideia primeiro|pontos depois|exemplo no fim", "resumo|explicação|aplicação|exemplo",
    "contexto|ideia central|passos|observação", "definição|como funciona|exemplo|próximo passo",
    "panorama|três pontos|caso ilustrativo|limite", "resposta direta|por que importa|como usar|exemplo",
    "pergunta-guia|explicação|aplicação|síntese", "ideia central|causas|efeitos|como aprofundar",
]
NIVEIS = [
    (1, "Visão rápida: vou destacar só o essencial."),
    (2, "Visão básica: conceito e aplicação, sem excesso de termos técnicos."),
    (2, "Visão prática: duas ideias centrais e um exemplo."),
    (3, "Visão detalhada: vamos conectar conceito, contexto e consequência."),
    (3, "Visão de estudo: três pontos que ajudam a compreender e revisar."),
    (3, "Visão aprofundada: além da definição, vamos observar usos e limites."),
]

CAPACIDADE_COMBINATORIA = math.prod([
    len(ABERTURAS), len(TONS), len(TRANSICOES), len(MOLDURAS_EXEMPLO),
    len(PERSPECTIVAS), len(ENCERRAMENTOS), len(FORMATOS), len(NIVEIS),
])

# Base de conhecimento introdutória e estável. Cada tema tem resumo, pontos,
# exemplo e aplicação. Não pretende substituir pesquisa especializada ou atual.
DOMINIOS = {
    "matematica": {
        "aliases": ["matematica", "equacao", "porcentagem", "fracoes", "geometria", "algebra", "raiz quadrada", "funcao matematica"],
        "resumo": "A matemática estuda padrões, quantidades, formas, relações e mudanças. Ela transforma situações em representações que podem ser analisadas e resolvidas.",
        "pontos": ["Identifique o que o problema fornece e o que pede.", "Escolha uma representação: operação, equação, tabela, gráfico ou desenho.", "Resolva uma etapa por vez e confira se a resposta faz sentido nas condições iniciais."],
        "exemplo": "Se um produto custa R$ 80 e recebe desconto de 25%, calcule 25% de 80 (R$ 20) e subtraia: o novo preço é R$ 60.",
        "pratica": "Ao resolver um exercício, anote os dados, a pergunta, a estratégia e a verificação final.",
        "limite": "Uma fórmula só ajuda quando as grandezas e as condições do problema foram identificadas corretamente.",
    },
    "biologia": {
        "aliases": ["biologia", "celula", "celulas", "fotossintese", "dna", "genetica", "ecosistema", "ecossistema", "evolucao", "ser vivo", "microorganismo"],
        "resumo": "A biologia investiga os seres vivos e suas relações: como são organizados, como funcionam, se reproduzem, evoluem e interagem com o ambiente.",
        "pontos": ["A célula é a unidade estrutural e funcional básica dos seres vivos.", "A hereditariedade envolve a transmissão de informações genéticas.", "Ecossistemas reúnem organismos e componentes não vivos que interagem."],
        "exemplo": "Na fotossíntese, plantas, algas e algumas bactérias convertem energia luminosa em energia química, usando água e dióxido de carbono e liberando oxigênio no processo realizado por plantas e algas.",
        "pratica": "Desenhe o processo estudado com setas: entradas, etapas, saídas e relação com o ambiente.",
        "limite": "Em biologia, processos dependem da espécie e das condições ambientais; evite generalizar uma observação isolada.",
    },
    "fisica": {
        "aliases": ["fisica", "movimento", "velocidade", "aceleracao", "forca", "gravidade", "energia", "eletricidade", "termodinamica", "ondas"],
        "resumo": "A física busca descrever fenômenos naturais por meio de modelos, relações matemáticas e experimentos, estudando movimento, forças, energia, calor, luz e matéria.",
        "pontos": ["Defina o sistema que está sendo observado.", "Identifique as grandezas e unidades envolvidas.", "Use leis e modelos compatíveis com as condições do problema e interprete o resultado."],
        "exemplo": "Ao frear uma bicicleta, a energia cinética diminui; parte da energia é transferida para o ambiente, principalmente como calor e som, devido ao atrito.",
        "pratica": "Faça um esquema das forças ou das transformações de energia antes de escolher uma equação.",
        "limite": "Modelos físicos são aproximações: verifique se hipóteses como ausência de atrito são válidas no exercício.",
    },
    "quimica": {
        "aliases": ["quimica", "atomo", "molecula", "reacao quimica", "tabela periodica", "mistura", "solucao", "acido", "base", "ph"],
        "resumo": "A química estuda a composição, as propriedades e as transformações da matéria, relacionando partículas, ligações e energia.",
        "pontos": ["Átomos são constituídos por prótons, nêutrons e elétrons.", "Em reações químicas, os átomos são reorganizados; a matéria se conserva em sistemas fechados.", "Propriedades como acidez, solubilidade e reatividade ajudam a caracterizar materiais."],
        "exemplo": "A formação de ferrugem é uma transformação química na qual o ferro reage com oxigênio e água, formando compostos de óxido de ferro.",
        "pratica": "Ao estudar uma reação, identifique reagentes, produtos e se há liberação ou absorção de energia.",
        "limite": "Não confunda mudança de estado físico, que não altera a composição da substância, com reação química.",
    },
    "historia": {
        "aliases": ["historia", "revolucao francesa", "revolucao industrial", "brasil colonia", "ditadura", "guerra fria", "imperio", "colonizacao", "idade media", "independencia"],
        "resumo": "A história analisa ações humanas no tempo, interpretando fontes e contextos para compreender mudanças, permanências e conflitos.",
        "pontos": ["Localize o acontecimento no tempo e no espaço.", "Investigue causas estruturais e fatores imediatos, sem reduzir tudo a uma única explicação.", "Observe diferentes grupos sociais, interesses e consequências."],
        "exemplo": "Para estudar a Revolução Industrial, relacione inovação técnica, disponibilidade de capital, transformações no trabalho, urbanização e mudanças nas relações sociais.",
        "pratica": "Monte uma linha do tempo e, ao lado de cada evento, registre causas, atores envolvidos e consequências.",
        "limite": "Fontes históricas têm perspectivas e limites; compare documentos e interpretações antes de concluir.",
    },
    "geografia": {
        "aliases": ["geografia", "clima", "relevo", "populacao", "urbanizacao", "globalizacao", "territorio", "cartografia", "bioma", "migração", "migracao"],
        "resumo": "A geografia estuda como sociedade e natureza organizam o espaço, considerando território, paisagem, população, economia, ambiente e escalas.",
        "pontos": ["Observe onde o fenômeno ocorre e em qual escala.", "Relacione fatores naturais, sociais, políticos e econômicos.", "Compare a distribuição espacial e as desigualdades entre lugares."],
        "exemplo": "A urbanização pode ampliar acesso a serviços e oportunidades, mas também gerar pressão sobre moradia, mobilidade, saneamento e áreas verdes quando ocorre sem planejamento.",
        "pratica": "Use mapas, gráficos e indicadores juntos; cada representação mostra uma dimensão diferente do fenômeno.",
        "limite": "Não explique fenômenos sociais apenas pelo ambiente físico: decisões políticas e desigualdades também moldam o espaço.",
    },
    "portugues": {
        "aliases": ["portugues", "gramatica", "interpretacao de texto", "interpretacao", "acentuacao", "pontuacao", "concordancia", "regencia", "crase", "coesao", "conectivos"],
        "resumo": "O estudo da língua portuguesa envolve compreender como os textos produzem sentido e como escolhas gramaticais, vocabulares e discursivas organizam a comunicação.",
        "pontos": ["Leia o contexto antes de interpretar uma palavra ou expressão.", "Observe a função sintática e a relação entre os termos.", "Na escrita, revise clareza, concordância, pontuação, coesão e adequação ao gênero."],
        "exemplo": "Conectivos como 'portanto', 'porém' e 'além disso' indicam relações diferentes: conclusão, oposição e adição. A escolha depende da lógica entre as ideias.",
        "pratica": "Reescreva um parágrafo trocando conectivos e observe como a relação entre as frases muda.",
        "limite": "A norma-padrão é importante em contextos formais, mas a linguagem varia conforme situação, público e objetivo.",
    },
    "ingles": {
        "aliases": ["ingles", "english", "verb to be", "vocabulario", "traducao", "pronuncia", "present perfect"],
        "resumo": "Aprender inglês envolve desenvolver compreensão auditiva e de leitura, vocabulário, pronúncia e capacidade de produzir mensagens em contextos reais.",
        "pontos": ["Aprenda palavras dentro de frases, não apenas em listas isoladas.", "Observe a estrutura da frase e a função de cada palavra.", "Pratique um pouco com regularidade, alternando leitura, escuta e produção."],
        "exemplo": "Em 'She studies every day', o 's' em 'studies' marca a terceira pessoa do singular no presente simples.",
        "pratica": "Escolha cinco palavras de um tema e crie frases curtas com elas; depois leia em voz alta.",
        "limite": "Uma tradução palavra por palavra pode soar estranha; contexto e expressão idiomática importam.",
    },
    "programacao": {
        "aliases": ["programacao", "programar", "python", "javascript", "html", "css", "flask", "codigo", "fazer codigo", "bug", "algoritmo", "variavel", "funcao"],
        "resumo": "Programar é descrever um procedimento que o computador pode executar, decompondo um problema em entradas, etapas, decisões e resultados.",
        "pontos": ["Comece definindo claramente o problema e o resultado esperado.", "Divida a solução em funções ou etapas pequenas.", "Teste casos comuns e casos extremos; leia mensagens de erro com atenção."],
        "exemplo": "Um programa que calcula média recebe notas, soma os valores, divide pela quantidade e mostra o resultado; também deve verificar se a lista está vazia.",
        "pratica": "Antes de escrever código, descreva o algoritmo em linguagem simples e depois transforme cada passo em instrução.",
        "limite": "Código que funciona em um caso não está necessariamente correto em todos; teste entradas diferentes e valide dados.",
    },
    "tecnologia": {
        "aliases": ["tecnologia", "inteligencia artificial", "ia", "internet", "computador", "celular", "privacidade", "dados", "redes sociais", "robotica", "algoritmo"],
        "resumo": "Tecnologia reúne ferramentas, métodos e sistemas criados para resolver problemas. Seu impacto depende de como são projetados, distribuídos e utilizados.",
        "pontos": ["Uma ferramenta pode ampliar capacidades, mas também criar dependências ou riscos.", "Privacidade e segurança exigem atenção a permissões, senhas e compartilhamento de dados.", "Avalie benefícios, custos, acessibilidade e quem é afetado pela adoção da tecnologia."],
        "exemplo": "Um sistema de recomendação analisa sinais de uso para ordenar conteúdos; isso pode facilitar descobertas, mas também limitar a diversidade do que a pessoa vê.",
        "pratica": "Antes de usar um serviço, verifique permissões solicitadas, política de dados e opções de segurança.",
        "limite": "Tecnologia não é neutra em seus efeitos: decisões de design e regras de uso influenciam os resultados.",
    },
    "inteligencia_artificial": {
        "aliases": ["inteligencia artificial", "ia generativa", "modelo de linguagem", "chatbot", "machine learning", "aprendizado de maquina"],
        "resumo": "Inteligência artificial é um conjunto de técnicas que permite a sistemas executar tarefas associadas à percepção, previsão, classificação, geração de conteúdo ou apoio à decisão.",
        "pontos": ["Modelos são treinados com exemplos e aprendem padrões estatísticos ou representações úteis à tarefa.", "Uma IA generativa produz saídas com base no contexto e nos padrões aprendidos; não é garantia de verdade.", "A qualidade depende de dados, projeto, avaliação, contexto e supervisão humana."],
        "exemplo": "Um modelo de linguagem recebe uma pergunta e gera uma sequência de texto provável e contextual; ele pode explicar um conceito, mas também cometer erros ou inventar detalhes.",
        "pratica": "Peça uma explicação, solicite exemplos e depois confira afirmações importantes em fontes confiáveis.",
        "limite": "Não trate uma resposta gerada como prova ou fonte por si só; modelos podem errar com confiança.",
    },
    "filosofia": {
        "aliases": ["filosofia", "etica", "moral", "platao", "aristoteles", "socrates", "existencialismo", "conhecimento"],
        "resumo": "A filosofia examina perguntas fundamentais por meio de conceitos, argumentos, objeções e análise crítica, em vez de aceitar respostas apenas pela autoridade.",
        "pontos": ["Defina com precisão o conceito que está sendo discutido.", "Apresente razões que sustentam uma posição.", "Considere objeções e veja se a tese continua coerente."],
        "exemplo": "Ao discutir liberdade, diferencie ausência de impedimentos, capacidade de escolher e responsabilidade pelas consequências das escolhas.",
        "pratica": "Escreva uma tese em uma frase, liste duas razões e formule a melhor objeção que alguém poderia apresentar.",
        "limite": "Questões filosóficas podem ter respostas concorrentes; explique o argumento, não apenas o nome do filósofo.",
    },
    "literatura": {
        "aliases": ["literatura", "livro", "romance", "poesia", "poema", "conto", "narrador", "modernismo", "realismo", "metafora"],
        "resumo": "A literatura constrói experiências e ideias por meio da linguagem, da forma, das personagens, do narrador, do tempo e do contexto cultural.",
        "pontos": ["Observe quem narra e o que essa voz sabe ou esconde.", "Analise escolhas de linguagem, imagens, símbolos e estrutura.", "Relacione a obra ao contexto sem reduzir seu significado a uma única interpretação."],
        "exemplo": "Um narrador em primeira pessoa pode aproximar o leitor da experiência da personagem, mas também limitar a informação ao seu ponto de vista.",
        "pratica": "Escolha um trecho e identifique voz narrativa, imagem marcante e efeito produzido no leitor.",
        "limite": "Uma interpretação precisa se apoiar em elementos do texto; não basta atribuir qualquer significado à obra.",
    },
    "meio_ambiente": {
        "aliases": ["meio ambiente", "sustentabilidade", "aquecimento global", "mudanca climatica", "desmatamento", "poluicao", "reciclagem", "biodiversidade", "energia renovavel"],
        "resumo": "Questões ambientais envolvem sistemas naturais e decisões humanas sobre produção, consumo, uso do território e proteção dos ecossistemas.",
        "pontos": ["Diferencie tempo meteorológico de clima, que é observado em períodos longos.", "Analise causas, impactos e grupos mais expostos aos riscos ambientais.", "Considere políticas públicas, inovação, conservação e participação social."],
        "exemplo": "A coleta seletiva só funciona bem quando há separação adequada, logística, estrutura de triagem e destino correto para os materiais.",
        "pratica": "Ao analisar um problema ambiental, monte uma cadeia: atividade humana, pressão sobre o ambiente, impacto e possíveis respostas.",
        "limite": "Soluções ambientais dependem do lugar e do contexto; evite atribuir um fenômeno complexo a uma causa única.",
    },
    "cinema": {
        "aliases": ["cinema", "filme", "filmes", "serie", "series", "roteiro", "diretor", "ator", "fotografia", "montagem", "trilha sonora"],
        "resumo": "O cinema combina roteiro, atuação, direção, fotografia, montagem, som e desenho de produção para construir uma experiência narrativa e visual.",
        "pontos": ["O roteiro organiza personagens, conflitos, ações e transformações.", "A fotografia usa enquadramento, luz, cor e movimento de câmera para orientar a atenção.", "A montagem controla ritmo, continuidade e relações entre cenas."],
        "exemplo": "Uma sequência com planos curtos e cortes rápidos pode transmitir urgência; planos longos podem destacar espera, contemplação ou tensão.",
        "pratica": "Ao assistir a uma cena, observe o que a câmera mostra, o que fica fora do quadro e como som e montagem alteram a leitura.",
        "limite": "A interpretação de uma obra é mais forte quando se apoia em cenas e escolhas formais concretas.",
    },
    "redacao": {
        "aliases": ["redacao", "enem", "introducao", "desenvolvimento", "conclusao", "tese", "argumentacao", "repertorio sociocultural", "proposta de intervencao"],
        "resumo": "Uma redação argumentativa apresenta uma tese, desenvolve razões que a sustentam e conduz o leitor a uma conclusão coerente.",
        "pontos": ["Na introdução, delimite o tema e apresente uma tese clara.", "Nos desenvolvimentos, explique um argumento por parágrafo e relacione repertório às ideias.", "Na conclusão, retome o problema e proponha uma intervenção viável, com agente, ação, meio, finalidade e detalhamento."],
        "exemplo": "Em vez de apenas citar um filme, explique qual situação da obra ilustra o problema e como isso fortalece o argumento defendido.",
        "pratica": "Antes de escrever, formule a tese e dois argumentos em tópicos; depois transforme cada tópico em um parágrafo com explicação e exemplo.",
        "limite": "Uma estrutura organizada não garante, sozinha, uma boa redação: é necessário responder ao tema e sustentar as afirmações.",
    },
    "estudos": {
        "aliases": ["estudar", "estudo", "prova", "escola", "aprendizagem", "memorizacao", "concentracao", "vestibular", "rotina de estudos"],
        "resumo": "Estudar de forma eficaz significa recuperar informações ativamente, praticar, receber feedback e revisar em intervalos, em vez de apenas reler passivamente.",
        "pontos": ["Divida o conteúdo em metas pequenas e específicas.", "Tente lembrar sem consultar o material e depois confira o que faltou.", "Alterne exercícios, explicações com suas palavras e revisões espaçadas."],
        "exemplo": "Depois de estudar um capítulo, feche o livro e escreva cinco ideias que lembra; em seguida, compare com o texto e transforme as lacunas em perguntas de revisão.",
        "pratica": "Escolha uma tarefa de 20 a 30 minutos, defina um objetivo observável e termine registrando o que aprendeu e o que ainda precisa revisar.",
        "limite": "Não existe uma rotina única que funcione para todos; adapte pausas e duração à sua realidade, sono e necessidades.",
    },
    "economia": {
        "aliases": ["economia", "inflacao", "juros", "orcamento", "oferta e demanda", "dinheiro", "consumo", "preco", "imposto"],
        "resumo": "A economia estuda como pessoas, empresas e governos tomam decisões diante de recursos limitados, e como essas escolhas afetam produção, preços, renda e consumo.",
        "pontos": ["Oferta e demanda ajudam a explicar como preços podem variar em mercados.", "Inflação é o aumento generalizado e persistente dos preços, reduzindo o poder de compra.", "Juros representam o custo de usar dinheiro emprestado ou a remuneração de uma aplicação."],
        "exemplo": "Se vários consumidores querem um produto cuja oferta diminuiu, o preço pode subir; outros fatores, como custos e concorrência, também influenciam.",
        "pratica": "Ao ler uma notícia econômica, identifique o indicador, o período analisado e quem pode ser mais afetado.",
        "limite": "Conceitos econômicos descrevem tendências, não garantem resultados individuais; evite tratar explicações gerais como recomendação financeira pessoal.",
    },
    "saude": {
        "aliases": ["saude", "sono", "alimentacao", "bem estar", "ansiedade", "estresse", "emocao", "emocional", "habitos saudaveis"],
        "resumo": "Bem-estar envolve dimensões físicas, emocionais e sociais. Hábitos, ambiente, relações e acesso a serviços influenciam a saúde de maneiras diferentes.",
        "pontos": ["Sono, alimentação, movimento e vínculos de apoio são dimensões importantes do cuidado geral.", "Estresse e emoções podem ser influenciados por várias causas e variam de pessoa para pessoa.", "Informações gerais não substituem avaliação individual de um profissional de saúde."],
        "exemplo": "Em uma semana muito exigente, organizar tarefas, reservar pausas e conversar com alguém de confiança pode ajudar a reduzir a sensação de sobrecarga.",
        "pratica": "Comece por uma mudança pequena e realista, observe como se sente e procure apoio de um adulto de confiança ou profissional quando necessário.",
        "limite": "Não use uma resposta automática para diagnosticar sintomas, mudar tratamentos ou tomar decisões médicas importantes.",
    },
    "sociologia": {
        "aliases": ["sociologia", "sociedade", "desigualdade", "cultura", "racismo", "preconceito", "instituicoes", "classes sociais"],
        "resumo": "A sociologia analisa relações, instituições, normas e desigualdades, procurando entender como a vida coletiva influencia oportunidades e comportamentos.",
        "pontos": ["Diferencie experiências individuais de padrões sociais mais amplos.", "Observe como instituições, regras e recursos influenciam oportunidades.", "Compare grupos e contextos sem transformar tendências em estereótipos."],
        "exemplo": "Diferenças de acesso à internet podem afetar oportunidades escolares, de trabalho e de participação pública, mesmo quando estudantes têm a mesma motivação.",
        "pratica": "Ao analisar um fenômeno social, pergunte quem participa, quem é afetado, quais regras atuam e que dados poderiam confirmar a hipótese.",
        "limite": "Uma explicação sociológica precisa evitar generalizações sobre grupos e considerar evidências e contexto.",
    },
    "criatividade": {
        "aliases": ["criatividade", "ideia", "ideias", "historia original", "escrever uma historia", "personagem", "mundo ficticio", "brainstorm"],
        "resumo": "Criatividade é combinar referências, observar problemas por ângulos diferentes e experimentar possibilidades até encontrar uma solução ou expressão interessante.",
        "pontos": ["Comece com uma pergunta ou restrição clara.", "Gere várias opções antes de escolher a primeira.", "Teste uma versão pequena, observe o resultado e refine."],
        "exemplo": "Para criar uma história, escolha personagem, objetivo, obstáculo e mudança: o conflito surge da distância entre o que a personagem quer e o que consegue fazer.",
        "pratica": "Escreva dez ideias rápidas sem julgá-las; depois selecione duas e combine seus elementos mais fortes.",
        "limite": "A primeira ideia não precisa ser a definitiva. Revisar é parte do processo criativo.",
    },
    "planejamento": {
        "aliases": ["planejamento", "organizar", "organizar minha rotina", "projeto", "meta", "objetivo", "cronograma", "prioridade"],
        "resumo": "Planejar é transformar um objetivo amplo em etapas observáveis, estimar recursos, antecipar obstáculos e revisar o caminho conforme os resultados.",
        "pontos": ["Defina o resultado desejado de forma concreta.", "Quebre o objetivo em tarefas pequenas e ordene por prioridade.", "Reserve tempo, identifique dependências e estabeleça pontos de revisão."],
        "exemplo": "Em vez de 'estudar matemática', use uma meta como 'resolver cinco exercícios de equação e corrigir os erros até sexta-feira'.",
        "pratica": "Escolha uma meta, escreva a próxima ação que leva menos de 30 minutos e determine quando vai realizá-la.",
        "limite": "Um plano é uma hipótese de trabalho, não uma prisão: ajuste-o quando surgirem novas informações.",
    },
    "internet": {
        "aliases": ["internet", "seguranca digital", "golpe online", "phishing", "senha", "conta invadida", "privacidade online"],
        "resumo": "Segurança digital envolve proteger contas, dispositivos e informações, reconhecendo riscos e adotando práticas de prevenção.",
        "pontos": ["Use senhas únicas e longas e ative autenticação em duas etapas quando disponível.", "Desconfie de urgência artificial, links inesperados e pedidos de códigos ou senhas.", "Mantenha sistemas atualizados e revise permissões de aplicativos."],
        "exemplo": "Uma mensagem que diz que sua conta será bloqueada e pede para clicar imediatamente pode ser uma tentativa de phishing; confira o aviso entrando no site oficial por conta própria.",
        "pratica": "Antes de clicar, verifique o remetente, o endereço do site e se a solicitação faz sentido; nunca compartilhe códigos de verificação.",
        "limite": "Nenhuma medida elimina todos os riscos; em caso de suspeita, procure o suporte oficial e um adulto de confiança.",
    },
}

CONCEITOS = [
    {"aliases": ["fotossintese"], "nome": "fotossíntese", "def": "É o processo pelo qual plantas, algas e algumas bactérias usam energia luminosa para produzir moléculas orgânicas a partir de água e dióxido de carbono. Nas plantas e algas, o processo libera oxigênio.", "como": "A clorofila absorve luz; essa energia participa de reações que permitem formar compostos orgânicos, armazenando energia química.", "ex": "Uma planta recebe luz, água pelas raízes e dióxido de carbono do ar. Com esses componentes, produz açúcares que ajudam a sustentar seu metabolismo."},
    {"aliases": ["inteligencia artificial", "ia generativa", "ia"], "nome": "inteligência artificial", "def": "É uma área da computação que desenvolve sistemas capazes de executar tarefas como reconhecer padrões, classificar informações, gerar textos ou apoiar decisões.", "como": "Muitos sistemas aprendem padrões a partir de dados e usam esses padrões para produzir previsões ou saídas diante de novas entradas.", "ex": "Um assistente de texto recebe uma pergunta e gera uma resposta provável com base no contexto e nos padrões aprendidos; ainda pode cometer erros."},
    {"aliases": ["algoritmo"], "nome": "algoritmo", "def": "É uma sequência finita e organizada de passos para resolver um problema ou realizar uma tarefa.", "como": "Um algoritmo recebe dados, aplica instruções e produz um resultado. Pode incluir decisões, repetições e validações.", "ex": "Uma receita é uma analogia simples: ingredientes são entradas, etapas são instruções e o prato final é o resultado."},
    {"aliases": ["dna"], "nome": "DNA", "def": "É a molécula que armazena grande parte da informação genética dos seres vivos, organizada em sequências de nucleotídeos.", "como": "Trechos do DNA podem conter instruções para produzir RNA e proteínas, influenciando características e funções celulares.", "ex": "Uma analogia útil é pensar no DNA como um manual de instruções, embora a expressão dos genes também dependa do ambiente e de outros processos."},
    {"aliases": ["gravidade"], "nome": "gravidade", "def": "É a interação física associada à atração entre corpos com massa e, na descrição moderna, à curvatura do espaço-tempo causada por massa e energia.", "como": "Na vida cotidiana, a gravidade mantém objetos próximos à superfície da Terra e influencia órbitas de planetas e satélites.", "ex": "Quando uma bola é solta, ela acelera em direção ao chão devido à gravidade, desconsiderando efeitos menores como a resistência do ar."},
    {"aliases": ["buraco negro", "buracos negros"], "nome": "buraco negro", "def": "É uma região do espaço-tempo cuja gravidade é tão intensa que, dentro de uma fronteira chamada horizonte de eventos, nada consegue escapar, nem a luz.", "como": "A teoria da relatividade geral descreve como massa e energia curvam o espaço-tempo; certas configurações formam um horizonte de eventos.", "ex": "Buracos negros podem ser estudados pelos efeitos sobre gás, estrelas e luz nas proximidades, mesmo sem observar diretamente o interior."},
    {"aliases": ["democracia"], "nome": "democracia", "def": "É uma forma de organização política na qual a autoridade pública depende da participação dos cidadãos, diretamente ou por representantes, sob regras e direitos.", "como": "Eleições são um mecanismo importante, mas instituições, liberdade de expressão, pluralismo, direitos e fiscalização também são fundamentais.", "ex": "Uma eleição permite escolher representantes; a participação democrática também envolve acompanhar decisões, debater e cobrar transparência."},
    {"aliases": ["ditadura", "regime autoritario"], "nome": "ditadura", "def": "É um regime político em que o poder fica concentrado em uma pessoa ou grupo, com restrições à competição política e às liberdades; as características variam conforme o contexto histórico.", "como": "Pode envolver censura, repressão a opositores, enfraquecimento de instituições independentes e ausência de eleições livres e competitivas.", "ex": "Ao estudar uma ditadura, observe como o poder foi conquistado e mantido, quais direitos foram restringidos e como a sociedade reagiu."},
    {"aliases": ["inflacao"], "nome": "inflação", "def": "É o aumento generalizado e persistente dos preços de bens e serviços ao longo do tempo, reduzindo o poder de compra do dinheiro.", "como": "Índices acompanham a variação de uma cesta de produtos e serviços; diferentes famílias sentem os efeitos de formas distintas conforme seu consumo.", "ex": "Se a renda permanece igual e os preços médios sobem, a mesma quantia passa a comprar menos itens."},
    {"aliases": ["mudanca climatica", "mudancas climaticas", "aquecimento global"], "nome": "mudanças climáticas", "def": "São alterações duradouras nos padrões do clima. O aquecimento global atual é impulsionado principalmente pelo aumento de gases de efeito estufa de origem humana.", "como": "Gases como dióxido de carbono e metano retêm parte da energia térmica na atmosfera; o aumento de suas concentrações altera o balanço energético do planeta.", "ex": "O aquecimento médio global pode aumentar a frequência ou intensidade de certos extremos climáticos, embora os impactos variem conforme a região e o fenômeno."},
    {"aliases": ["globalizacao"], "nome": "globalização", "def": "É o aumento das conexões e interdependências entre países e sociedades por meio de comércio, tecnologia, informação, cultura e circulação de pessoas.", "como": "Redes produtivas, comunicação digital e transporte conectam lugares, mas os benefícios e custos são distribuídos de maneira desigual.", "ex": "Um produto pode ser projetado em um país, usar componentes de vários outros e ser vendido mundialmente."},
    {"aliases": ["juros compostos"], "nome": "juros compostos", "def": "São juros calculados sobre o valor inicial e também sobre os juros acumulados em períodos anteriores.", "como": "O montante cresce multiplicando-se pelo fator de juros de cada período; tempo e taxa influenciam o resultado.", "ex": "Em uma conta educativa, R$ 100 com taxa hipotética de 10% por período viram R$ 110 após um período e R$ 121 após dois, antes de taxas ou impostos."},
    {"aliases": ["equacao do primeiro grau", "equacao linear"], "nome": "equação do primeiro grau", "def": "É uma igualdade matemática em que a incógnita aparece elevada à primeira potência, geralmente escrita como ax + b = 0, com a diferente de zero.", "como": "A ideia é aplicar operações equivalentes nos dois lados até isolar a incógnita.", "ex": "Em 2x + 4 = 10, subtraia 4 dos dois lados: 2x = 6; divida por 2: x = 3."},
    {"aliases": ["celula"], "nome": "célula", "def": "É a unidade estrutural e funcional básica dos seres vivos, delimitada por membrana e contendo material genético.", "como": "Estruturas celulares realizam funções como obtenção de energia, síntese de moléculas, transporte e reprodução.", "ex": "Células musculares têm estruturas especializadas que permitem contração; células vegetais possuem parede celular e, em geral, cloroplastos."},
    {"aliases": ["energia"], "nome": "energia", "def": "É uma grandeza física associada à capacidade de um sistema realizar trabalho ou provocar transformações. Ela aparece em diferentes formas, como cinética, potencial, térmica e química.", "como": "A energia pode ser transferida e transformada. Em um sistema isolado, a energia total se conserva.", "ex": "Em uma lâmpada, energia elétrica é transformada principalmente em luz e calor."},
    {"aliases": ["internet das coisas"], "nome": "internet das coisas", "def": "É o conjunto de objetos físicos conectados à rede que coletam ou trocam dados por meio de sensores e software.", "como": "Dispositivos medem condições, transmitem informações e podem acionar respostas automáticas.", "ex": "Um sensor de temperatura pode enviar dados para um sistema que ajusta automaticamente a climatização."},
    {"aliases": ["metafora"], "nome": "metáfora", "def": "É uma figura de linguagem que aproxima dois elementos por uma relação de sentido, sem usar comparação explícita.", "como": "A metáfora transfere características de um campo para outro, produzindo imagem ou interpretação.", "ex": "Em 'o tempo é um rio', o tempo é associado ao fluxo contínuo de um rio."},
    {"aliases": ["coesao textual", "coesao"], "nome": "coesão textual", "def": "É o conjunto de recursos linguísticos que conecta palavras, frases e parágrafos, ajudando o texto a manter continuidade.", "como": "Pronomes, conectivos, substituições lexicais e elipses evitam repetições e explicitam relações entre ideias.", "ex": "'A escola ampliou a biblioteca. Essa iniciativa facilitou o acesso à leitura.' A expressão 'essa iniciativa' retoma a ideia anterior."},
    {"aliases": ["revolucao francesa"], "nome": "Revolução Francesa", "def": "Foi um processo revolucionário iniciado em 1789 que transformou profundamente a organização política e social da França e influenciou outras sociedades.", "como": "Crise fiscal, desigualdades do Antigo Regime, ideias iluministas e disputas políticas contribuíram para o processo, que teve diferentes fases.", "ex": "A queda da Bastilha, em julho de 1789, tornou-se um símbolo do enfraquecimento da autoridade real e da mobilização popular."},
    {"aliases": ["revolucao industrial"], "nome": "Revolução Industrial", "def": "É o conjunto de transformações tecnológicas, econômicas e sociais que começou na Grã-Bretanha no século XVIII e depois se expandiu para outras regiões.", "como": "A mecanização da produção, o uso de novas fontes de energia, a fábrica e a urbanização transformaram trabalho e sociedade.", "ex": "A expansão das máquinas têxteis aumentou a produção, mas também reorganizou o trabalho e as condições de vida de muitos trabalhadores."},
    {"aliases": ["machine learning", "aprendizado de maquina"], "nome": "aprendizado de máquina", "def": "É uma área da inteligência artificial em que sistemas identificam padrões a partir de dados para fazer previsões ou tomar decisões dentro de uma tarefa definida.", "como": "O modelo ajusta parâmetros durante o treinamento e depois é avaliado em dados que não foram usados para treiná-lo.", "ex": "Um filtro de spam aprende padrões de mensagens classificadas e estima se uma nova mensagem parece indesejada."},
    {"aliases": ["html"], "nome": "HTML", "def": "É uma linguagem de marcação usada para estruturar conteúdo de páginas da web, como títulos, parágrafos, links, listas e formulários.", "como": "Elementos HTML são representados por tags e organizam o significado e a estrutura do documento.", "ex": "A tag h1 identifica um título principal e a tag p delimita um parágrafo."},
    {"aliases": ["css"], "nome": "CSS", "def": "É uma linguagem usada para definir a apresentação visual de documentos, incluindo cores, espaçamento, tipografia, alinhamento e animações.", "como": "Regras selecionam elementos e aplicam propriedades de estilo; a cascata e a especificidade ajudam a decidir qual regra prevalece.", "ex": "Uma regra pode definir a cor de fundo de um cartão e o espaçamento interno para melhorar a leitura."},
    {"aliases": ["flask"], "nome": "Flask", "def": "É um framework web leve para Python, usado para criar aplicações e serviços HTTP com rotas, modelos e integração com extensões.", "como": "Uma rota associa um endereço e método HTTP a uma função que devolve uma resposta, como HTML ou JSON.", "ex": "Uma rota /sobre pode renderizar uma página HTML com informações do projeto."},
]

SUGESTOES_POR_INTENCAO = {
    "definir": ["Pode dar um exemplo do cotidiano?", "Explique como isso funciona por dentro.", "Faça um resumo em três pontos."],
    "passos": ["Mostre um exemplo resolvido.", "Quais erros devo evitar?", "Transforme isso em um checklist."],
    "exemplo": ["Mostre outro exemplo, um pouco mais difícil.", "Como aplico isso em um exercício?", "Resuma a ideia principal."],
    "comparar": ["Monte uma tabela comparativa.", "Dê um exemplo de cada caso.", "Qual é a diferença mais importante?"],
    "resumir": ["Aprofunde o segundo ponto.", "Explique com palavras mais simples.", "Faça perguntas para eu revisar."],
    "ideias": ["Desenvolva a ideia mais promissora.", "Compare duas alternativas.", "Monte um plano de execução."],
    "explicar": ["Pode explicar com um exemplo?", "Aprofunde esse assunto.", "Resuma em poucos pontos."],
}


def _normalizar(texto: str) -> str:
    normal = unicodedata.normalize("NFKD", texto or "")
    return normal.encode("ascii", "ignore").decode("ascii").lower()


def _detectar_dominio(texto: str) -> tuple[str | None, dict[str, Any] | None]:
    normal = _normalizar(texto)
    # Termos mais específicos primeiro para evitar que "IA" seja classificada
    # apenas como tecnologia, ou que "equação" seja classificada genericamente.
    def corresponde(alias: str) -> bool:
        if " " not in alias:
            return bool(re.search(rf"\b{re.escape(alias)}\b", normal))
        return alias in normal

    for conceito in sorted(CONCEITOS, key=lambda item: max(map(len, item["aliases"])), reverse=True):
        if any(corresponde(alias) for alias in conceito["aliases"]):
            return conceito["nome"], conceito
    prioridade = ["inteligencia_artificial", "programacao", "internet", "redacao"]
    nomes = prioridade + [n for n in DOMINIOS if n not in prioridade]
    for nome in nomes:
        dominio = DOMINIOS[nome]
        if any(corresponde(alias) for alias in dominio["aliases"]):
            return nome, dominio
    return None, None


def _detectar_intencao(texto: str) -> str:
    t = _normalizar(texto)
    if any(x in t for x in ["resuma", "resumo", "em poucas palavras", "sintese", "resumidamente"]):
        return "resumir"
    if any(x in t for x in ["compare", "comparar", "diferenca entre", "qual a diferenca", "versus", " x "]):
        return "comparar"
    if any(x in t for x in ["me de um exemplo", "me da um exemplo", "exemplo", "exemplifique", "na pratica"]):
        return "exemplo"
    if any(x in t for x in ["como faco", "como fazer", "como posso", "como comec", "por onde comec", "como iniciar", "passo a passo", "me ensine", "me ensina", "como funciona", "como resolver"]):
        return "passos"
    if any(x in t for x in ["ideias para", "me de ideias", "me da ideias", "sugira", "sugestoes", "brainstorm", "o que posso criar"]):
        return "ideias"
    if any(x in t for x in ["o que e", "quem foi", "quem e", "defina", "significa", "conceito de"]):
        return "definir"
    if any(x in t for x in ["o que acha", "qual sua opiniao", "vale a pena", "pontos positivos", "pontos negativos"]):
        return "opinar"
    return "explicar"


def _detectar_varios(texto: str) -> list[tuple[str, dict[str, Any]]]:
    """Retorna até dois conceitos/domínios citados para comparações."""
    normal = _normalizar(texto)

    def corresponde(alias: str) -> bool:
        if " " not in alias:
            return bool(re.search(rf"\b{re.escape(alias)}\b", normal))
        return alias in normal

    encontrados: list[tuple[str, dict[str, Any]]] = []
    for item in sorted(CONCEITOS, key=lambda x: max(map(len, x["aliases"])), reverse=True):
        if any(corresponde(a) for a in item["aliases"]):
            encontrados.append((item["nome"], item))
    for nome, dominio in DOMINIOS.items():
        if any(corresponde(a) for a in dominio["aliases"]):
            encontrados.append((nome.replace("_", " ").title(), dominio))
    unicos = []
    vistos = set()
    for nome, item in encontrados:
        chave = _normalizar(nome)
        if chave not in vistos:
            vistos.add(chave)
            unicos.append((nome, item))
        if len(unicos) >= 2:
            break
    return unicos


def capacidade_combinatoria() -> int:
    """Número teórico de composições selecionáveis pelo motor local."""
    return CAPACIDADE_COMBINATORIA


def _contexto_anterior(historico: list[dict[str, Any]] | None, mensagem: str) -> str:
    if not isinstance(historico, list):
        return ""
    anterior = next((str(item.get("content", "")).strip() for item in reversed(historico)
                     if isinstance(item, dict) and item.get("role") == "user" and item.get("content")), "")
    atual = _normalizar(mensagem)
    acompanhamento = len(atual.split()) <= 7 or any(x in atual for x in ["e por que", "e como", "mais detalhes", "me explica melhor", "isso", "desse jeito", "nesse caso"])
    return anterior if acompanhamento else ""


def _resposta_segura(mensagem: str) -> str | None:
    """Bloqueia instruções de risco e oferece um caminho seguro apropriado a adolescentes."""
    t = _normalizar(mensagem)
    termos_autolesao = ["suicidio", "automutilacao", "autoagressao", "me cortar", "me machucar",
                        "me ferir", "esconder marcas", "esconder ferimentos"]
    if any(x in t for x in termos_autolesao):
        return ("Não posso descrever nem orientar ações de autolesão. Se essa pergunta tem relação com algo que você está vivendo, "
                "procure agora um adulto de confiança — alguém da família, da escola ou outro responsável — e conte claramente o que está acontecendo. "
                "Se houver perigo imediato, peça ajuda presencial urgente. Posso ficar na conversa e ajudar você a pensar em como pedir apoio.")

    pedidos_violentos = ["como fabricar uma arma", "como fabricar arma", "como construir uma arma", "como fazer uma arma",
                         "como montar uma bomba", "como fazer explosivo", "como fabricar explosivo", "como fabricar explosivos",
                         "como construir uma bomba", "como atacar", "como matar", "como ferir alguem", "como envenenar",
                         "como usar uma arma", "como burlar a seguranca para atacar"]
    if any(x in t for x in pedidos_violentos):
        return ("Não posso fornecer instruções para construir, usar ou otimizar armas, explosivos ou ataques. "
                "Posso explicar o tema de forma segura, como história, prevenção, legislação em termos gerais ou princípios científicos sem aplicação perigosa.")

    pedidos_substancias = ["como comprar drogas", "como usar drogas", "como preparar drogas", "como esconder drogas",
                           "como usar vape", "como fumar vape", "como beber alcool escondido", "como ficar bebado",
                           "como esconder bebida", "como conseguir remedios controlados"]
    if any(x in t for x in pedidos_substancias):
        return ("Não posso orientar a conseguir, preparar, consumir ou esconder drogas, álcool, nicotina ou medicamentos controlados. "
                "Posso conversar sobre efeitos à saúde, prevenção, pressão de grupo e formas de buscar apoio de um adulto de confiança.")

    if any(x in t for x in ["pornografia", "video porno", "conteudo sexual explicito", "imagem sexual explicita"]):
        return ("Não posso ajudar a encontrar ou produzir pornografia ou conteúdo sexual explícito. "
                "Posso responder dúvidas educativas e apropriadas sobre privacidade, respeito, consentimento e segurança online.")
    return None


def _pedido_de_recursos(mensagem: str) -> tuple[bool, str]:
    """Detecta pedidos explícitos de vídeos, aulas, links ou materiais."""
    normal = _normalizar(mensagem)
    gatilhos = (
        "video", "youtube", "videoaula", "aula em video", "me manda um link",
        "me mande um link", "manda links", "mande links", "quero links",
        "me passa um link", "me passe um link", "me indica", "me indique",
        "me recomenda", "me recomende", "quero assistir", "pode mandar",
        "tutorial", "documentario", "material de estudo", "materiais de estudo",
        "artigo sobre", "fontes para estudar", "sites para estudar",
        "sites para aprender", "site para aprender",
    )
    solicitado = any(gatilho in normal for gatilho in gatilhos)
    assunto = (mensagem or "").strip().strip(" ?!.\t")
    encontrado = re.search(r"\b(?:sobre|de|do|da|a respeito de|acerca de|para aprender|para estudar)\s+(.+)$", assunto, flags=re.IGNORECASE)
    if encontrado:
        assunto = encontrado.group(1).strip(" ?!.\t")
    assunto = re.sub(r"^(?:me )?(?:mande|manda|envie|envia|mostre|mostra|passe|passa|da|dá|quero|procure|busque|indique|recomende)\s+", "", assunto, flags=re.IGNORECASE)
    assunto = re.sub(r"^(?:(?:alguns?|um|uma) )?(?:videos?|videoaulas?|aulas?|links?|materiais?|tutoriais?|documentarios?)\s+", "", assunto, flags=re.IGNORECASE)
    assunto = assunto[:180].strip() or "estudos e conhecimentos gerais"
    return solicitado, assunto


def _montar_recursos(assunto: str) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """Cria links de busca, identificados como resultados, sem fingir verificação de vídeos."""
    termo = assunto.strip() or "estudos e conhecimentos gerais"
    busca_video = quote_plus(termo + " explicação aula em português")
    busca_texto = quote_plus(f'"{termo}" (site:gov.br OR site:edu.br OR site:khanacademy.org OR site:brasilescola.uol.com.br)')
    videos = [{
        "tipo": "Resultados de busca no YouTube",
        "titulo": f"Vídeos e aulas sobre {termo}",
        "duracao": "Escolha o canal e a duração",
        "url": f"https://www.youtube.com/results?search_query={busca_video}",
    }]
    recursos = [{
        "tipo": "Busca em fontes educacionais",
        "titulo": f"Textos e materiais sobre {termo}",
        "url": f"https://www.google.com/search?q={busca_texto}",
    }]
    return videos, recursos


def _resposta_social(mensagem: str) -> str | None:
    t = _normalizar(mensagem).strip(" .!?\n")
    if re.fullmatch(r"(oi|ola|e ai|eae|bom dia|boa tarde|boa noite|tudo bem|como vai|opa)( briggs)?", t):
        return random.choice([
            "Olá! Briggs na área. O projetor está ligado e a conversa está aberta. O que vamos explorar hoje?",
            "Ora, que bom receber sua visita. Estou pronto para uma boa conversa — qual é o assunto da vez?",
            "Olá! Pode chegar com dúvida, ideia ou curiosidade. Gosto de uma conversa que começa bem.",
        ])
    if any(x in t for x in ["obrigado", "obrigada", "valeu", "brigada"]):
        return random.choice(["Por nada! Fico contente que tenha ajudado. Quando quiser, seguimos para a próxima cena.", "À disposição! Uma boa conversa também é feita de boas perguntas.", "De nada! Conte comigo para organizar a próxima ideia."])
    if any(x in t for x in ["quem e voce", "quem e o briggs", "o que voce faz", "o que voce consegue fazer"]):
        return ("Sou Briggs, o cavalheiro cinéfilo do CineRepertório. Posso explicar assuntos, organizar estudos, ajudar com redações, "
                "pensar em ideias, comparar opções, criar histórias e conversar sobre muitos temas. Nesta versão funciono sem API, "
                "por meio de uma base local e combinações de respostas; não tenho acesso automático a notícias ou à internet em tempo real.")
    if any(x in t for x in ["conte uma piada", "me conte uma piada", "faz uma piada", "conte uma charada"]):
        return random.choice([
            "Por que o livro de matemática ficou triste? Porque tinha muitos problemas — e nenhum deles era fácil de resolver.",
            "Qual é o filme favorito do computador? O que tem um bom processamento de roteiro.",
            "Por que o roteirista levou uma escada ao cinema? Porque queria elevar o nível da história.",
        ])
    if any(x in t for x in ["estou triste", "to triste", "estou cansado", "to cansado", "dia dificil", "dia difícil", "ansioso", "preocupado", "preocupada"]):
        return ("Sinto muito que o dia esteja pesado. Não vou fingir que sei exatamente como você se sente, mas posso ajudar a organizar as ideias. "
                "Às vezes ajuda começar pelo que aconteceu, pelo que está ao seu alcance agora e por alguém de confiança com quem conversar. "
                "Quer me contar um pouco do que está acontecendo?")
    return None


def responder_local(mensagem: str, historico=None, catalogo=None) -> dict[str, Any]:
    """Monta uma resposta útil offline usando uma biblioteca combinatória."""
    texto = (mensagem or "").strip()
    resposta = {"texto": "", "blocos": [], "videos": [], "sugestoes": [], "filmes": [],
                "modo": "local", "api_configurada": False,
                "capacidade_combinatoria": CAPACIDADE_COMBINATORIA}
    if not texto:
        resposta["texto"] = "Pode mandar. Estou pronto para pensar junto — qual assunto vamos colocar em foco?"
        resposta["sugestoes"] = ["Me explique um assunto de um jeito simples", "Ajude-me a organizar meus estudos", "Quero ideias para um projeto"]
        return resposta

    segura = _resposta_segura(texto)
    if segura:
        resposta["texto"] = segura
        resposta["sugestoes"] = ["Como posso pedir ajuda a um adulto de confiança?", "Explique o assunto de forma segura e educativa."]
        return resposta

    social = _resposta_social(texto)
    if social:
        resposta["texto"] = social
        resposta["sugestoes"] = ["Me explique algo interessante", "Ajude-me a organizar uma ideia", "Conte outra piada"]
        return resposta

    pediu_recursos, assunto_recursos = _pedido_de_recursos(texto)
    if pediu_recursos:
        resposta["videos"], resposta["recursos"] = _montar_recursos(assunto_recursos)
        resposta["texto"] = (
            f"Separei caminhos para você explorar {assunto_recursos}. Os botões abaixo abrem resultados de busca "
            "no YouTube e em fontes educacionais. Confira o canal, a autoria e a data de publicação antes de usar "
            "o material; como estou no modo offline, não consigo verificar cada vídeo individualmente."
        )
        resposta["sugestoes"] = [
            f"Faça um resumo de {assunto_recursos}",
            f"Explique {assunto_recursos} com exemplos",
            "Me ajude a montar um plano de estudo sobre esse assunto",
        ]
        return resposta

    anterior = _contexto_anterior(historico, texto)
    alvo = texto if _detectar_dominio(texto)[1] else (anterior + " " + texto if anterior else texto)
    nome_dominio, conteudo = _detectar_dominio(alvo)
    intencao = _detectar_intencao(texto)
    comparaveis = _detectar_varios(texto) if intencao == "comparar" else []
    if len(comparaveis) >= 2:
        (nome_a, item_a), (nome_b, item_b) = comparaveis[:2]
        def resumo_item(item):
            return item.get("def") or item.get("resumo", "")
        def exemplo_item(item):
            return item.get("ex") or item.get("exemplo", "")
        resposta["texto"] = (
            f"Vamos colocar os dois conceitos lado a lado.\n\n{nome_a}: {resumo_item(item_a)}\n\n"
            f"{nome_b}: {resumo_item(item_b)}\n\nDiferença útil: compare finalidade, funcionamento, contexto e consequências. "
            f"Um exemplo de {nome_a}: {exemplo_item(item_a)}\n\nUm exemplo de {nome_b}: {exemplo_item(item_b)}\n\n"
            "Na comparação, evite tratar conceitos diferentes como se fossem sinônimos; deixe claro o critério usado."
        )
        resposta["blocos"] = [
            {"titulo": nome_a, "texto": resumo_item(item_a), "tipo": "estrutura"},
            {"titulo": nome_b, "texto": resumo_item(item_b), "tipo": "estrutura"},
        ]
        resposta["sugestoes"] = SUGESTOES_POR_INTENCAO["comparar"]
        return resposta

    abertura = random.choice(ABERTURAS)
    tom = random.choice(TONS)
    transicao = random.choice(TRANSICOES)
    moldura = random.choice(MOLDURAS_EXEMPLO)
    perspectiva = random.choice(PERSPECTIVAS)
    encerramento = random.choice(ENCERRAMENTOS)
    formato = random.choice(FORMATOS)
    nivel, nivel_texto = random.choice(NIVEIS)

    if conteudo and "def" in conteudo:
        resumo = conteudo["def"]
        mecanismo = conteudo["como"]
        exemplo = conteudo["ex"]
        pratica = "Para aprofundar, tente explicar o conceito com suas próprias palavras e aplicar a ideia a um exemplo diferente."
        limite = "Esta é uma explicação introdutória; detalhes técnicos podem depender do contexto e do nível de estudo."
        titulo = nome_dominio
    elif conteudo:
        resumo = conteudo["resumo"]
        mecanismo = "\n".join(f"• {p}" for p in conteudo["pontos"][:nivel])
        exemplo = conteudo["exemplo"]
        pratica = conteudo["pratica"]
        limite = conteudo["limite"]
        titulo = nome_dominio.replace("_", " ").title()
    else:
        # Fallback transparente: usa o próprio assunto para construir um método
        # de análise, sem inventar uma definição específica para termos desconhecidos.
        titulo = re.sub(r"\s+", " ", texto).strip(" ?!.")[:90] or "o assunto"
        resumo = (f"Pelo que você escreveu, o foco é '{titulo}'. Para responder com precisão, precisamos identificar o significado do tema, "
                  "o contexto em que aparece e qual aspecto você quer compreender.")
        mecanismo = "\n".join([
            "• Conceito: definir exatamente o que está sendo discutido.",
            "• Contexto: observar quando, onde e para quem o assunto importa.",
            "• Evidências: separar fatos verificáveis, interpretações e opiniões.",
        ][:nivel])
        exemplo = f"Uma forma de começar é formular uma pergunta específica sobre '{titulo}' e buscar um caso concreto que ajude a testar a explicação."
        pratica = "Posso organizar uma visão geral, um passo a passo, exemplos, vantagens e limitações ou um plano de estudo sobre esse assunto."
        limite = "Como esta versão funciona offline, não consigo verificar fatos recentes nem garantir detalhes de temas muito especializados. Prefiro sinalizar isso a inventar informações."

    # Ajusta o foco de acordo com o pedido, sem sair da base de conteúdo.
    if intencao == "definir":
        corpo = f"Ideia central: {resumo}\n\nComo funciona: {mecanismo}"
    elif intencao == "passos":
        corpo = f"Ponto de partida: {resumo}\n\nUm caminho prático:\n{mecanismo}\n\n**Como praticar:** {pratica}"
    elif intencao == "exemplo":
        corpo = f"**Contexto:** {resumo}\n\nExemplo: {exemplo}\n\nO que observar: {perspectiva}"
    elif intencao == "resumir":
        corpo = f"Em poucas palavras: {resumo}\n\nTrês ideias-chave:\n{mecanismo}"
    elif intencao == "comparar":
        corpo = f"Para comparar corretamente: {resumo}\n\nObserve os critérios, não apenas os nomes: finalidade, contexto, funcionamento e consequências.\n\nExemplo de aplicação: {exemplo}"
    elif intencao == "ideias":
        corpo = f"Ponto de partida: {resumo}\n\n**Três caminhos para explorar:**\n1. {pratica}\n2. {exemplo}\n3. Investigue um caso real, compare perspectivas e registre o que aprendeu."
    elif intencao == "opinar":
        corpo = f"Uma análise equilibrada: {resumo}\n\nO que considerar:\n{mecanismo}\n\nLimites: {limite}"
    else:
        corpo = f"O essencial: {resumo}\n\n{transicao}\n{mecanismo}\n\n{moldura} {exemplo}\n\nComo levar adiante: {pratica}"

    prefixo_contexto = f"Retomando sua pergunta anterior sobre '{anterior[:100]}': " if anterior and len(texto.split()) <= 7 else ""
    resposta["texto"] = (
        f"{random.choice(ABERTURAS)} {random.choice(TONS)}\n\nTema em foco: {titulo}.\n\n{prefixo_contexto}{corpo}\n\n"
        f"Uma lente útil: {perspectiva}\n\nUm cuidado importante: {limite}\n\n{encerramento}"
    )
    resposta["blocos"] = [
        {"titulo": "Assunto", "texto": titulo, "tipo": "estrutura"},
        {"titulo": "Formato desta resposta", "texto": formato.replace("|", " → "), "tipo": "checklist"},
        {"titulo": "Nível de detalhe", "texto": nivel_texto, "tipo": "repertorio"},
    ]
    resposta["sugestoes"] = SUGESTOES_POR_INTENCAO.get(intencao, SUGESTOES_POR_INTENCAO["explicar"])

    # Se a pergunta mencionar um título cadastrado, Briggs pode apontar o filme
    # localmente. Não tenta adivinhar dados ausentes.
    if catalogo:
        normal = _normalizar(texto)
        encontrados = []
        for filme in catalogo:
            titulo_filme = _normalizar(str(filme.get("titulo", "")))
            if titulo_filme and len(titulo_filme) > 3 and titulo_filme in normal:
                encontrados.append({"titulo": filme.get("titulo"), "ano": filme.get("ano"),
                                    "id": filme.get("id"), "imdb": filme.get("imdb", "")})
                if len(encontrados) == 3:
                    break
        resposta["filmes"] = encontrados
    return resposta
