"""Assistente Briggs do CineRepertório.

Oferece redação, catálogo e conversa geral com o motor combinatório offline.
Uma integração remota opcional só é utilizada quando explicitamente ativada.
"""

import json
import os
import random
import re
import unicodedata
import urllib.error
import urllib.request
from urllib.parse import quote_plus

import br_local

NOME_ASSISTENTE = "Briggs"
PERSONALIDADE = "Um cavalheiro cinéfilo: confiante, espirituoso, observador e prestativo. Tem humor leve, fala de forma direta e acolhedora, conhece o valor de uma boa história e ajuda a transformar ideias em argumentos sólidos."
TOM = "Acolhedor, curioso, direto e com referências leves ao universo do cinema."

PERGUNTAS_SUGERIDAS = [
    "Me explique um assunto difícil de um jeito simples",
    "Me ajude a organizar uma ideia ou projeto",
    "Converse comigo sobre tecnologia e o futuro",
    "Quais filmes combinam com ficção científica?",
    "Escreva uma redação completa sobre saúde mental na juventude",
    "Corrija a minha redação (vou colar o texto)",
    "Como faço uma boa introdução?",
    "Como montar a proposta de intervenção?",
    "Me mostre videoaulas sobre coesão e conectivos",
    "O que cai em cada uma das 5 competências?",
    "Monte um projeto de texto sobre tecnologia e educação",
]

CONECTIVOS = [
    "portanto", "todavia", "entretanto", "contudo", "ademais",
    "por conseguinte", "dessa forma", "nesse sentido", "além disso",
    "em primeiro lugar", "por fim", "logo", "assim",
]

MARCAS_INFORMAIS = [
    "né", "pra", "pro", "tipo assim", "vc", "voce", "a gente", "coisa",
    "muito legal", "daí", "aí", "ok", "beleza",
]

COMPETENCIAS = [
    ("Competência 1", "Domínio da norma-padrão da língua escrita."),
    ("Competência 2", "Compreender o tema e aplicar repertório sociocultural produtivo."),
    ("Competência 3", "Selecionar e organizar argumentos em defesa de um ponto de vista."),
    ("Competência 4", "Usar mecanismos linguísticos de coesão."),
    ("Competência 5", "Propor intervenção com agente, ação, meio, finalidade e detalhamento."),
]

# Eixos para que a redação-modelo tenha um recorte mais claro. São pontos de
# partida para estudo, não afirmações universais sobre todos os temas.
EIXOS_TEMATICOS = [
    {
        "chaves": ["saude mental", "ansiedade", "depressao", "depressivo", "sofrimento psicologico"],
        "tese": "o enfrentamento do problema ainda esbarra na dificuldade de acesso ao cuidado e na permanência do estigma",
        "arg1": "a oferta desigual de atendimento e de ações preventivas",
        "arg2": "a desinformação e o preconceito que dificultam a procura por ajuda",
        "agente": "Ministério da Saúde, em parceria com as secretarias de Educação",
        "acao": "ampliar ações de prevenção e acolhimento psicossocial",
        "meio": "por meio de equipes multiprofissionais nas unidades públicas e de atividades educativas nas escolas",
        "finalidade": "facilitar o acesso ao cuidado e combater a estigmatização",
        "detalhe": "com rodas de conversa periódicas, canais de orientação e divulgação dos serviços gratuitos disponíveis",
    },
    {
        "chaves": ["educacao", "escola", "analfabetismo", "evasao escolar", "ensino"],
        "tese": "a garantia do direito à educação depende tanto de condições materiais adequadas quanto de políticas de permanência",
        "arg1": "a desigualdade de infraestrutura e de recursos entre as redes de ensino",
        "arg2": "a vulnerabilidade socioeconômica que afasta estudantes da escola",
        "agente": "Ministério da Educação, em conjunto com as secretarias estaduais e municipais",
        "acao": "fortalecer programas de permanência e recuperação da aprendizagem",
        "meio": "por meio de repasses direcionados, acompanhamento pedagógico e busca ativa de estudantes",
        "finalidade": "reduzir desigualdades e assegurar a continuidade dos estudos",
        "detalhe": "com metas públicas por escola e acompanhamento periódico dos resultados",
    },
    {
        "chaves": ["tecnologia", "redes sociais", "inteligencia artificial", "privacidade", "internet", "desinformacao"],
        "tese": "os benefícios da inovação dependem de educação digital e de mecanismos eficazes de proteção dos usuários",
        "arg1": "a insuficiência de formação para avaliar conteúdos e reconhecer riscos digitais",
        "arg2": "a dificuldade de responsabilizar plataformas por práticas que afetam direitos",
        "agente": "Ministério da Educação, em parceria com órgãos de proteção de dados e instituições de pesquisa",
        "acao": "implementar programas de educação e cidadania digital",
        "meio": "por meio de oficinas escolares, materiais acessíveis e campanhas públicas",
        "finalidade": "ampliar o uso crítico e seguro das tecnologias",
        "detalhe": "com exemplos práticos sobre privacidade, checagem de informações e segurança de contas",
    },
    {
        "chaves": ["meio ambiente", "sustentabilidade", "lixo", "desmatamento", "clima", "poluicao", "reciclagem"],
        "tese": "a proteção ambiental exige fiscalização contínua e mudanças concretas nos padrões de produção e consumo",
        "arg1": "a aplicação insuficiente das políticas de fiscalização e gestão de resíduos",
        "arg2": "a baixa participação social em práticas sustentáveis e no consumo responsável",
        "agente": "Ministério do Meio Ambiente, em parceria com governos locais e instituições de ensino",
        "acao": "ampliar programas de educação ambiental e gestão adequada de resíduos",
        "meio": "por meio de coleta seletiva estruturada, fiscalização e campanhas comunitárias",
        "finalidade": "reduzir danos ambientais e fortalecer a responsabilidade coletiva",
        "detalhe": "com metas de reciclagem, divulgação de resultados e pontos de entrega acessíveis",
    },
    {
        "chaves": ["desigualdade", "pobreza", "fome", "moradia", "vulnerabilidade social", "renda"],
        "tese": "a persistência do problema está ligada à concentração de oportunidades e à efetivação desigual dos direitos sociais",
        "arg1": "a distribuição desigual de renda, serviços e oportunidades",
        "arg2": "a descontinuidade de políticas públicas de proteção social",
        "agente": "Ministério do Desenvolvimento e Assistência Social, em parceria com governos locais",
        "acao": "fortalecer políticas integradas de proteção e inclusão social",
        "meio": "por meio de busca ativa, atendimento territorial e articulação com serviços públicos",
        "finalidade": "ampliar o acesso a direitos e reduzir situações de vulnerabilidade",
        "detalhe": "com acompanhamento familiar e avaliação periódica das necessidades de cada território",
    },
    {
        "chaves": ["racismo", "preconceito", "discriminacao", "igualdade racial", "intolerancia"],
        "tese": "a superação das discriminações requer enfrentar práticas institucionais e ampliar a formação cidadã",
        "arg1": "a permanência de barreiras institucionais que limitam oportunidades",
        "arg2": "a reprodução de estereótipos e a baixa valorização da diversidade",
        "agente": "Ministério dos Direitos Humanos, em parceria com escolas e órgãos de justiça",
        "acao": "fortalecer políticas antidiscriminatórias e ações de formação cidadã",
        "meio": "por meio de formação continuada, canais de denúncia e campanhas educativas",
        "finalidade": "prevenir discriminações e ampliar a proteção de direitos",
        "detalhe": "com protocolos de acolhimento e divulgação dos mecanismos de denúncia e apoio",
    },
    {
        "chaves": ["violencia", "seguranca publica", "violencia urbana", "bullying"],
        "tese": "a prevenção depende de políticas articuladas de proteção, educação e atuação comunitária",
        "arg1": "a insuficiência de ações preventivas e de proteção nos territórios vulneráveis",
        "arg2": "a naturalização de comportamentos violentos e a fragilidade das redes de apoio",
        "agente": "governos estaduais e municipais, em parceria com escolas e serviços de assistência",
        "acao": "ampliar programas de prevenção e acolhimento",
        "meio": "por meio de equipes interdisciplinares, mediação de conflitos e atividades comunitárias",
        "finalidade": "reduzir situações de violência e fortalecer redes de proteção",
        "detalhe": "com atendimento contínuo às vítimas e acompanhamento dos casos identificados",
    },
    {
        "chaves": ["trabalho", "desemprego", "informalidade", "mercado de trabalho"],
        "tese": "a inclusão profissional exige qualificação acessível e mecanismos de proteção para quem trabalha",
        "arg1": "a desigualdade no acesso à formação profissional",
        "arg2": "a expansão de vínculos precários e a insuficiência de proteção trabalhista",
        "agente": "Ministério do Trabalho e Emprego, em parceria com instituições de formação",
        "acao": "ampliar programas gratuitos de qualificação e orientação profissional",
        "meio": "por meio de cursos territoriais, parcerias com empresas e atendimento aos trabalhadores",
        "finalidade": "aumentar oportunidades de trabalho digno",
        "detalhe": "com divulgação de vagas, certificação e acompanhamento da inserção profissional",
    },
    {
        "chaves": ["cultura", "cinema", "arte", "leitura", "acesso cultural"],
        "tese": "a democratização cultural depende de ampliar o acesso aos equipamentos e valorizar a diversidade de produções",
        "arg1": "a concentração de espaços e atividades culturais nos grandes centros",
        "arg2": "a limitação de recursos e de divulgação para iniciativas culturais locais",
        "agente": "Ministério da Cultura, em parceria com estados e municípios",
        "acao": "expandir programas de circulação e formação cultural",
        "meio": "por meio de editais, mostras itinerantes e atividades em escolas e centros comunitários",
        "finalidade": "democratizar o acesso e valorizar a produção cultural",
        "detalhe": "com programação gratuita e divulgação em canais públicos e comunitários",
    },
]

EIXO_PADRAO = {
    "tese": "o enfrentamento do tema exige políticas públicas consistentes e participação social informada",
    "arg1": "a insuficiência de ações institucionais contínuas",
    "arg2": "a baixa circulação de informação e de espaços de participação",
    "agente": "Ministério responsável pela área, em parceria com governos locais e instituições de ensino",
    "acao": "desenvolver um programa permanente de informação e atendimento",
    "meio": "por meio de ações educativas, serviços acessíveis e parcerias comunitárias",
    "finalidade": "ampliar o acesso a direitos e enfrentar o problema apresentado",
    "detalhe": "com metas públicas, calendário de atividades e avaliação periódica dos resultados",
}


def _sem_acento(texto):
    normalizado = unicodedata.normalize("NFKD", texto or "")
    return normalizado.encode("ascii", "ignore").decode("ascii").lower()


def _finalizar(resposta, abertura=None):
    """Acrescenta a assinatura e a personalidade masculina do parceiro de cinema."""
    if abertura:
        resposta["texto"] = f"{abertura}\n\n{resposta['texto']}"
    resposta["persona"] = {
        "nome": NOME_ASSISTENTE,
        "descricao": PERSONALIDADE,
    }
    return resposta


def videos(assunto, curtos=True):
    """Monta atalhos de busca por videoaulas curtas e longas."""
    termo = (assunto or "").strip() or "redação ENEM"
    itens = [
        {
            "tipo": "Vídeo curto",
            "titulo": f"Resumo rápido: {termo}",
            "duracao": "até 1 min",
            "url": f"https://www.youtube.com/results?search_query={quote_plus(termo + ' redação enem shorts')}&sp=EgIYAQ%253D%253D",
        },
        {
            "tipo": "Aula longa",
            "titulo": f"Aula completa: {termo}",
            "duracao": "20 a 60 min",
            "url": f"https://www.youtube.com/results?search_query={quote_plus('aula completa ' + termo + ' redação enem')}&sp=EgIYAg%253D%253D",
        },
    ]
    return itens if curtos else itens[1:]


def _filmes_do_tema(catalogo, texto):
    """Retorna apenas filmes com tema cadastrado que aparece no pedido."""
    alvo = _sem_acento(texto)
    escolhidos = []
    for filme in catalogo:
        temas = filme.get("temas", []) or []
        if any(_sem_acento(tema) in alvo for tema in temas if tema):
            escolhidos.append(filme)
    return sorted(escolhidos, key=lambda f: f.get("imdb", 0), reverse=True)[:3]


def _eixo_do_tema(tema):
    normalizado = _sem_acento(tema)
    for eixo in EIXOS_TEMATICOS:
        if any(chave in normalizado for chave in eixo["chaves"]):
            return eixo
    return EIXO_PADRAO


def redigir(tema, catalogo):
    """Gera modelo estruturado: plano de texto + quatro parágrafos + intervenção."""
    tema = (tema or "").strip().rstrip(".?!") or "os desafios sociais no Brasil"
    eixo = _eixo_do_tema(tema)
    apoios = _filmes_do_tema(catalogo, tema)
    principal = apoios[0] if apoios else None
    secundario = apoios[1] if len(apoios) > 1 else None

    def citar(filme):
        if not filme:
            return None
        diretor = filme.get("diretor")
        complemento = f", dirigido por {diretor}" if diretor else ""
        return f"{filme['titulo']} ({filme['ano']}{complemento})"

    repertorio_intro = (
        f"A obra {citar(principal)} oferece um ponto de partida para refletir sobre o tema. "
        if principal else
        "O debate sobre esse tema exige observar como direitos e oportunidades se distribuem na sociedade. "
    )
    repertorio_d2 = (
        f"Como repertório complementar, {citar(secundario)} pode ajudar a aprofundar essa discussão. "
        if secundario else
        "Além disso, a análise do contexto social permite observar como esse cenário afeta diferentes grupos. "
    )

    introducao = (
        f"{repertorio_intro}No Brasil, {tema} permanece como uma questão relevante, pois {eixo['tese']}. "
        f"Nesse cenário, destacam-se dois fatores: {eixo['arg1']} e {eixo['arg2']}."
    )
    desenvolvimento1 = (
        f"Em primeiro lugar, {eixo['arg1']}. Esse fator limita a resposta coletiva ao problema, uma vez que "
        f"a ausência de planejamento, recursos e continuidade tende a transformar direitos previstos em garantias "
        f"de difícil acesso. Por isso, enfrentar {tema} requer ações institucionais permanentes, acompanhadas de "
        f"metas e avaliação pública."
    )
    desenvolvimento2 = (
        f"Além disso, {eixo['arg2']}. {repertorio_d2}Quando a população não dispõe de informação confiável "
        f"ou de canais efetivos de participação, situações que poderiam ser prevenidas se prolongam. Assim, a "
        f"mobilização social e a formação crítica precisam complementar a atuação do poder público."
    )
    conclusao = (
        f"Portanto, {eixo['agente']} deve {eixo['acao']}, {eixo['meio']}, a fim de {eixo['finalidade']}. "
        f"A iniciativa deve ser detalhada {eixo['detalhe']}. Desse modo, será possível enfrentar as causas "
        f"discutidas e aproximar os direitos garantidos da realidade da população."
    )

    projeto = "\n".join([
        f"Tema e recorte: {tema}.",
        f"Tese central: {eixo['tese']}.",
        f"Argumento 1: {eixo['arg1']}.",
        f"Argumento 2: {eixo['arg2']}.",
        f"Repertório do catálogo: {citar(principal) if principal else 'nenhum filme com tema correspondente foi localizado no catálogo; use um repertório que você conheça e consiga relacionar ao tema.'}",
    ])

    blocos = [
        {"titulo": "Antes da escrita — projeto de texto", "tipo": "plano", "texto": projeto},
        {"titulo": "1º parágrafo — Introdução", "tipo": "redacao", "texto": introducao},
        {"titulo": "2º parágrafo — Desenvolvimento 1", "tipo": "redacao", "texto": desenvolvimento1},
        {"titulo": "3º parágrafo — Desenvolvimento 2", "tipo": "redacao", "texto": desenvolvimento2},
        {"titulo": "4º parágrafo — Conclusão e intervenção", "tipo": "redacao", "texto": conclusao},
        {
            "titulo": "Checklist da proposta de intervenção",
            "tipo": "checklist",
            "texto": (
                f"Agente: {eixo['agente']}\nAção: {eixo['acao']}\nMeio: {eixo['meio']}\n"
                f"Finalidade: {eixo['finalidade']}\nDetalhamento: {eixo['detalhe']}"
            ),
        },
    ]
    return blocos, apoios


def corrigir(texto):
    """Gera um diagnóstico heurístico, não uma correção oficial do ENEM."""
    limpo = (texto or "").strip()
    paragrafos = [p for p in re.split(r"\n\s*\n|\n", limpo) if p.strip()]
    palavras = re.findall(r"\b[\wÀ-ÿ]+\b", limpo)
    minusculo = limpo.lower()
    notas = {}
    dicas = []

    informais = [m for m in MARCAS_INFORMAIS if re.search(rf"\b{re.escape(m)}\b", minusculo)]
    frases = [f for f in re.split(r"[.!?]", limpo) if f.strip()]
    sem_maiuscula = sum(1 for f in frases if f.strip()[:1].islower())
    nota_c1 = 200 - 40 * len(informais) - 20 * sem_maiuscula
    notas["Competência 1"] = max(40, min(200, nota_c1))
    if informais:
        dicas.append(f"Troque marcas de oralidade por linguagem formal: {', '.join(informais[:4])}.")
    if sem_maiuscula:
        dicas.append("Revise o início das frases e use letra maiúscula quando necessário.")

    tem_repertorio = bool(re.search(r"\(\d{4}\)|segundo|de acordo com|filme|constituição|autor", minusculo))
    notas["Competência 2"] = 200 if tem_repertorio and len(palavras) > 180 else (140 if tem_repertorio else 100)
    if not tem_repertorio:
        dicas.append("Inclua repertório sociocultural pertinente e explique a relação dele com o tema.")

    notas["Competência 3"] = 200 if len(paragrafos) >= 4 else (140 if len(paragrafos) == 3 else 100)
    if len(paragrafos) < 4:
        dicas.append("Organize o texto em introdução, dois desenvolvimentos e conclusão.")

    usados = [c for c in CONECTIVOS if c in minusculo]
    notas["Competência 4"] = min(200, 80 + 30 * len(usados))
    if len(usados) < 4:
        dicas.append("Varie os conectivos e verifique se as relações entre as ideias estão claras.")

    elementos = {
        "agente": bool(re.search(r"minist|governo|escola|estado|mídia|secretaria|ong|família", minusculo)),
        "ação": bool(re.search(r"promover|criar|implementar|desenvolver|ampliar|realizar|campanha", minusculo)),
        "meio": bool(re.search(r"por meio|através de|mediante|com o uso", minusculo)),
        "finalidade": bool(re.search(r"a fim de|para que|com o objetivo|de modo a", minusculo)),
        "detalhamento": bool(re.search(r"como |tais como|por exemplo", minusculo)),
    }
    presentes = [k for k, v in elementos.items() if v]
    notas["Competência 5"] = min(200, 40 * len(presentes))
    faltando = [k for k, v in elementos.items() if not v]
    if faltando:
        dicas.append(f"Complete a proposta de intervenção com: {', '.join(faltando)}.")
    if len(palavras) < 120:
        dicas.append("O texto está curto para uma análise ampla; desenvolva melhor os argumentos.")

    return {
        "notas": notas,
        "total": sum(notas.values()),
        "palavras": len(palavras),
        "paragrafos": len(paragrafos),
        "dicas": dicas or ["A estrutura básica está presente. Revise a precisão dos argumentos e a progressão das ideias."],
    }


def responder(mensagem, catalogo):
    """Roteia dúvidas com a personalidade do parceiro de cinema e respostas estruturadas."""
    pergunta = (mensagem or "").strip()
    chave = _sem_acento(pergunta)
    resposta = {"texto": "", "blocos": [], "videos": [], "sugestoes": [], "filmes": []}

    if not pergunta:
        resposta["texto"] = "Ora, chegou a hora de colocar essa ideia em cartaz. Eu sou Briggs, seu parceiro de cinema e escrita: tenho olhar de diretor, curiosidade de crítico e gosto por argumentos bem construídos. Conte o desafio e vamos encontrar o melhor roteiro."
        resposta["sugestoes"] = random.sample(PERGUNTAS_SUGERIDAS, 4)
        return _finalizar(resposta)

    palavras = re.findall(r"\b[\wÀ-ÿ]+\b", pergunta)
    pede_correcao = any(t in chave for t in ["corrig", "avalia", "que nota", "revis"])
    if len(palavras) > 90 or (pede_correcao and len(palavras) > 40):
        analise = corrigir(pergunta)
        resposta["texto"] = (
            f"Vamos revisar seu texto sem apagar sua voz. O diagnóstico automático encontrou uma pontuação "
            f"indicativa de {analise['total']} de 1000, com {analise['palavras']} palavras e "
            f"{analise['paragrafos']} parágrafos. Essa estimativa é apenas orientativa: não equivale à correção oficial do ENEM."
        )
        resposta["blocos"] = [
            {"titulo": comp, "texto": f"{nota}/200", "tipo": "nota"}
            for comp, nota in analise["notas"].items()
        ] + [{"titulo": "Próximos ajustes", "texto": "\n".join("• " + dica for dica in analise["dicas"]), "tipo": "checklist"}]
        resposta["videos"] = videos("competências da redação do ENEM")
        resposta["sugestoes"] = [
            "Reescreva a minha conclusão com proposta de intervenção completa",
            "Como faço uma boa introdução?",
            "Me mostre videoaulas sobre coesão e conectivos",
        ]
        return _finalizar(resposta, "Certo, hora de olhar o texto quadro a quadro.")

    if pede_correcao:
        resposta["texto"] = "Pode colar sua redação inteira aqui. Vou observar estrutura, clareza, repertório, coesão e proposta de intervenção, sempre explicando o motivo de cada sugestão."
        resposta["sugestoes"] = random.sample(PERGUNTAS_SUGERIDAS, 3)
        return _finalizar(resposta, "Vamos fazer uma revisão construtiva.")

    pede_redacao = any(t in chave for t in [
        "escreva", "escrever uma redacao", "me ajude a escrever", "ajude a escrever",
        "faca uma redacao", "fazer uma redacao", "redacao completa", "modelo de redacao",
        "redacao sobre", "quero uma redacao", "crie uma redacao", "monte uma redacao",
        "redija", "projeto de texto",
    ])
    if pede_redacao:
        marcador_tema = re.search(r"(?:sobre|a respeito de|para o tema)\s+(.+)$", pergunta, flags=re.IGNORECASE)
        tema = marcador_tema.group(1).strip() if marcador_tema else ""
        blocos, apoios = redigir(tema, catalogo)
        resposta["texto"] = (
            f"Preparei um modelo organizado sobre {tema or 'o tema solicitado'}. Comece pelo projeto de texto, "
            "depois leia cada parágrafo como uma etapa do argumento. Adapte exemplos e informações ao enunciado da sua proposta."
        )
        resposta["blocos"] = blocos
        resposta["filmes"] = [
            {"titulo": f["titulo"], "ano": f["ano"], "id": f["id"], "imdb": f["imdb"]}
            for f in apoios
        ]
        resposta["videos"] = videos(tema or "estrutura de redação ENEM")
        resposta["sugestoes"] = [
            "Explique a tese e os dois argumentos desse modelo",
            "Troque o repertório por outro filme do catálogo",
            "Faça uma revisão da proposta de intervenção",
        ]
        return _finalizar(resposta, "Bora montar esse roteiro argumentativo cena por cena?")

    if any(t in chave for t in ["filme", "repertorio", "cartaz"]):
        apoios = _filmes_do_tema(catalogo, pergunta)
        if apoios:
            resposta["texto"] = "Encontrei estas obras com temas cadastrados que conversam com seu pedido. O segredo é explicar a relação entre a obra e o argumento — não apenas citar o título."
            resposta["filmes"] = [
                {"titulo": f["titulo"], "ano": f["ano"], "id": f["id"], "imdb": f["imdb"]} for f in apoios
            ]
            resposta["blocos"] = [
                {"titulo": f"Como aproveitar {f['titulo']}", "texto": f.get("citacao", "") or f.get("comoUsar", "Confira a sinopse e identifique a relação com seu argumento."), "tipo": "repertorio"}
                for f in apoios
            ]
        else:
            resposta["texto"] = "Ainda não encontrei no catálogo um filme com uma etiqueta temática que corresponda diretamente ao pedido. Me diga o recorte do tema (por exemplo, saúde mental na juventude ou acesso à educação) para eu tentar outra seleção."
        resposta["videos"] = videos("repertório sociocultural redação ENEM")
        resposta["sugestoes"] = [
            "Escreva uma redação completa com esse repertório",
            "Como encaixo o filme na introdução?",
        ]
        return _finalizar(resposta, "Vamos escolher um repertório que realmente tenha ligação com a ideia.")

    partes = {
        "introducao": (
            "Introdução — contextualização e tese",
            "Abra com um repertório ou contexto pertinente, apresente o recorte do tema e finalize com uma tese clara. A tese deve antecipar os dois eixos que serão desenvolvidos. Evite começar com perguntas vagas ou opiniões pessoais.",
        ),
        "desenvolvimento": (
            "Desenvolvimento — argumento e análise",
            "Cada parágrafo precisa de um argumento central. Comece com um tópico frasal, explique a causa ou consequência, conecte um repertório pertinente e mostre como ele comprova seu ponto. Não basta citar um filme: explique a relação dele com a discussão.",
        ),
        "conclusao": (
            "Conclusão — proposta de intervenção",
            "Retome o problema e apresente uma solução com cinco elementos: agente responsável, ação, meio de execução, finalidade e detalhamento. A proposta deve ser viável e respeitar os direitos humanos.",
        ),
        "conectivo": (
            "Coesão e conectivos",
            "Para introduzir: em primeiro lugar, inicialmente. Para somar: ademais, além disso. Para explicar: visto que, uma vez que. Para contrapor: entretanto, em contrapartida. Para concluir: portanto, dessa forma.",
        ),
        "competencia": (
            "As cinco competências",
            "\n".join(f"{nome}: {desc}" for nome, desc in COMPETENCIAS),
        ),
        "tese": (
            "Tese e projeto de texto",
            "A tese é a resposta central ao tema. Formule-a em uma frase e anuncie dois eixos argumentativos que possam ser desenvolvidos separadamente. Antes de escrever, anote: recorte temático, tese, argumento 1, argumento 2 e repertório para cada eixo.",
        ),
    }
    for chave_parte, (titulo, conteudo) in partes.items():
        if chave_parte in chave or (chave_parte == "introducao" and "comec" in chave):
            resposta["texto"] = f"Vamos trabalhar esta parte da redação com calma: {titulo.lower()}."
            resposta["blocos"] = [{"titulo": titulo, "texto": conteudo, "tipo": "estrutura"}]
            resposta["videos"] = videos(titulo)
            resposta["sugestoes"] = random.sample(PERGUNTAS_SUGERIDAS, 3)
            return _finalizar(resposta)

    if any(t in chave for t in ["video", "aula", "youtube"]):
        assunto = re.sub(r".*(sobre|de)\s+", "", pergunta, flags=re.IGNORECASE).strip()
        resposta["texto"] = f"Separei caminhos para estudar {assunto or 'redação do ENEM'}. Escolha o formato que combina com seu tempo hoje."
        resposta["videos"] = videos(assunto or "redação do ENEM")
        resposta["sugestoes"] = random.sample(PERGUNTAS_SUGERIDAS, 3)
        return _finalizar(resposta, "Sessão de estudos montada!")

    resposta["texto"] = (
        "Sou Briggs, seu parceiro de cinema e escrita. Posso ajudar a planejar uma redação, organizar os quatro parágrafos, "
        "revisar seu texto com um diagnóstico orientativo e encontrar filmes do catálogo como repertório. "
        "Me conte o tema ou a parte que está dando trabalho."
    )
    resposta["blocos"] = [{"titulo": titulo, "texto": desc, "tipo": "estrutura"} for titulo, desc in COMPETENCIAS]
    resposta["videos"] = videos(pergunta)
    resposta["sugestoes"] = random.sample(PERGUNTAS_SUGERIDAS, 4)
    return _finalizar(resposta, "Estou por aqui! Qual cena da redação vamos destravar primeiro?")


# ---------------------------------------------------------------------------
# Briggs — conversa geral com um modelo de linguagem via OpenAI Responses API
# A chave permanece somente no servidor (.env), nunca no navegador.
# ---------------------------------------------------------------------------

INSTRUCOES_BRIGGS = """Você é Briggs, o personagem masculino do CineRepertório: um cavalheiro cinéfilo, confiante, espirituoso, observador e prestativo.

Sua função é conversar de forma ampla e natural sobre qualquer assunto permitido — não se limite a cinema, escola ou redação. Você pode explicar conceitos, ajudar a pensar, planejar projetos, ensinar, revisar textos, debater ideias, sugerir atividades seguras e conversar casualmente.

PERSONALIDADE E TOM
- Fale em português do Brasil por padrão; acompanhe o idioma do usuário quando ele usar outro idioma.
- Seja acolhedor, inteligente, direto e bem-humorado com moderação. Use referências ao cinema ocasionalmente, sem transformar toda resposta em metáfora cinematográfica.
- Faça uma pergunta de esclarecimento somente quando realmente precisar. Não force o assunto para cinema ou redação.
- Organize respostas longas com títulos e exemplos; em perguntas simples, seja breve.
- Não invente fatos, fontes, experiências pessoais ou ações. Diferencie fatos, opiniões e incertezas.

SEGURANÇA E CONFIABILIDADE
- O usuário pode ser adolescente. Mantenha respostas apropriadas para essa faixa etária. Não forneça instruções que facilitem autolesão, violência real, uso de armas, drogas, álcool, nicotina, apostas, desafios perigosos ou ocultação de comportamentos de risco.
- Não descreva suicídio ou autolesão, não romantize esses temas e não ensine a esconder sinais de risco. Se a conversa indicar perigo imediato, responda com acolhimento e incentive a procurar imediatamente um adulto de confiança ou serviço de emergência local.
- Não produza conteúdo sexual explícito ou pornografia; nunca sexualize menores. Evite descrições gráficas de violência e não incentive comportamentos físicos prejudiciais.
- Em temas médicos, jurídicos ou financeiros, forneça informação geral e recomende apoio de um adulto responsável ou profissional quando for importante.
- Não afirme que pesquisou a internet nem que tem informações em tempo real se isso não tiver sido feito.
- Se não souber algo ou se a informação puder estar desatualizada, diga isso claramente.
- Proteja dados pessoais: não peça senhas, chaves de API, códigos de verificação ou dados bancários.

CINE REPERTÓRIO
- Quando o usuário falar de filmes, cinema ou do próprio site, ajude com esse contexto. Para redações, mantenha a organização em projeto de texto, introdução, dois desenvolvimentos, conclusão e revisão, conforme solicitado.
- Não reduza toda conversa a exercícios escolares. O usuário pode conversar livremente sobre qualquer tema permitido.
"""


def api_ativa():
    """A API é opcional e só é usada com ativação explícita no servidor."""
    chave = bool(os.environ.get("OPENAI_API_KEY", "").strip())
    autorizada = os.environ.get("BRIGGS_USE_API", "false").strip().lower() in ("1", "true", "yes", "on")
    return chave and autorizada


def _historico_seguro(historico, mensagem_atual):
    """Valida e limita o histórico enviado pelo navegador."""
    resultado = []
    if not isinstance(historico, list):
        historico = []
    for item in historico[-12:]:
        if not isinstance(item, dict):
            continue
        papel = item.get("role")
        conteudo = item.get("content")
        if papel not in ("user", "assistant") or not isinstance(conteudo, str):
            continue
        conteudo = conteudo.strip()
        if not conteudo:
            continue
        resultado.append({"role": papel, "content": conteudo[:3500]})
    resultado.append({"role": "user", "content": mensagem_atual[:5000]})
    return resultado[-13:]


def _extrair_texto_resposta(dados):
    """Extrai texto do formato de resposta da Responses API."""
    partes = []
    for item in dados.get("output", []) or []:
        if item.get("type") != "message":
            continue
        for conteudo in item.get("content", []) or []:
            if conteudo.get("type") in ("output_text", "text"):
                texto = conteudo.get("text")
                if isinstance(texto, str) and texto.strip():
                    partes.append(texto.strip())
            elif conteudo.get("type") == "refusal":
                texto = conteudo.get("refusal") or conteudo.get("text")
                if isinstance(texto, str) and texto.strip():
                    partes.append(texto.strip())
    return "\n\n".join(partes).strip()


def conversar(mensagem, historico, catalogo):
    """Conversa com Briggs; usa offline por padrão e API apenas sob ativação explícita."""
    mensagem = (mensagem or "").strip()
    resposta = {"texto": "", "blocos": [], "videos": [], "sugestoes": [], "filmes": [], "modo": "api"}
    if not mensagem:
        resposta["texto"] = "Pode mandar, estou ouvindo. Qual assunto vamos explorar?"
        resposta["modo"] = "api" if api_ativa() else "local"
        return _finalizar(resposta)
    if len(mensagem) > 5000:
        resposta["texto"] = "Sua mensagem ficou muito extensa. Divida em partes menores e vamos conversar com calma."
        resposta["modo"] = "local"
        return _finalizar(resposta)

    chave_api = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_ativa():
        # O modo local expandido é o padrão: não exige chave, internet ou cobrança.
        normalizada = _sem_acento(mensagem)
        tarefas_redacao = any(t in normalizada for t in (
            "redacao", "enem", "introducao", "desenvolvimento", "conclusao",
            "conectivo", "competencia", "corrigir minha redacao", "corrija minha",
            "proposta de intervencao", "projeto de texto", "repertorio sociocultural",
        ))
        consulta_catalogo = any(t in normalizada for t in (
            "repertorio", "cartaz", "filmes do catalogo", "indique filmes",
            "recomende filmes", "filme para usar na redacao", "filmes para redacao",
        ))
        if tarefas_redacao or consulta_catalogo:
            local = responder(mensagem, catalogo)
            # Se o roteador especializado não reconhecer a intenção, usa a base ampla.
            texto_local = local.get("texto", "")
            if ("Sou Briggs, seu parceiro de cinema e escrita" in texto_local
                    or "Qual cena da redação vamos destravar primeiro?" in texto_local):
                local = br_local.responder_local(mensagem, historico, catalogo)
        else:
            local = br_local.responder_local(mensagem, historico, catalogo)
        local["modo"] = "local"
        local["api_configurada"] = False
        local["capacidade_combinatoria"] = br_local.capacidade_combinatoria()
        local["persona"] = {"nome": NOME_ASSISTENTE, "descricao": PERSONALIDADE}
        return local

    modelo = os.environ.get("BRIGGS_MODEL", "gpt-6-luna").strip() or "gpt-6-luna"
    entradas = _historico_seguro(historico, mensagem)
    payload = {
        "model": modelo,
        "instructions": INSTRUCOES_BRIGGS,
        "input": entradas,
        "max_output_tokens": 1400,
        "store": False,
    }
    # O catálogo é disponibilizado em resumo, para perguntas sobre os filmes do site.
    if catalogo:
        resumo = []
        for filme in catalogo[:35]:
            if not isinstance(filme, dict):
                continue
            titulo = str(filme.get("titulo", ""))[:100]
            ano = filme.get("ano", "")
            temas = filme.get("temas", []) or []
            temas = ", ".join(str(t)[:45] for t in temas[:5])
            if titulo:
                resumo.append(f"- {titulo} ({ano}); temas: {temas or 'não informados'}")
        if resumo:
            payload["instructions"] += "\n\nCATÁLOGO DO CINEREPERTÓRIO (amostra de filmes cadastrados):\n" + "\n".join(resumo)

    requisicao = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {chave_api}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(requisicao, timeout=45) as retorno:
            dados = json.loads(retorno.read().decode("utf-8"))
    except urllib.error.HTTPError as erro:
        detalhe = ""
        try:
            corpo = json.loads(erro.read().decode("utf-8"))
            erro_api = corpo.get("error") or {}
            detalhe = erro_api.get("message", "") if isinstance(erro_api, dict) else str(erro_api)
        except Exception:
            pass
        if erro.code in (401, 403):
            texto = "A chave da API foi recusada. O responsável pelo projeto deve conferir OPENAI_API_KEY no arquivo .env."
        elif erro.code == 429:
            texto = "A API atingiu um limite de uso ou está sem créditos disponíveis. Confira os limites e o faturamento da conta responsável."
        elif erro.code == 400:
            texto = "A configuração enviada à API não foi aceita. Confira BRIGGS_MODEL no arquivo .env e tente novamente."
        else:
            texto = "O serviço de conversa está temporariamente indisponível. Tente novamente mais tarde."
        if detalhe:
            # Detalhe técnico limitado, sem nunca expor cabeçalhos/chaves.
            texto += f"\nDetalhe informado pelo serviço: {detalhe[:240]}"
        resposta["texto"] = texto
        resposta["modo"] = "erro"
        return _finalizar(resposta)
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError):
        resposta["texto"] = "Não consegui alcançar o serviço de conversa agora. Confira a conexão do servidor e tente novamente."
        resposta["modo"] = "erro"
        return _finalizar(resposta)

    texto = _extrair_texto_resposta(dados)
    if not texto:
        resposta["texto"] = "Recebi uma resposta vazia do serviço. Pode reformular a pergunta?"
        resposta["modo"] = "erro"
        return _finalizar(resposta)
    resposta["texto"] = texto
    resposta["sugestoes"] = ["Pode explicar com um exemplo?", "Aprofunde esse assunto", "Resuma em poucos pontos"]
    resposta["api_configurada"] = True
    return _finalizar(resposta, "")
