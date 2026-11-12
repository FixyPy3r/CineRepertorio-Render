/* CineRepertório — interações da interface */
document.addEventListener("DOMContentLoaded", function () {
  // Botão "copiar parágrafo-modelo" ------------------------------------------
  document.querySelectorAll("[data-citacao]").forEach(function (botao) {
    botao.addEventListener("click", function () {
      var texto = botao.getAttribute("data-citacao") || "";
      var rotulo = botao.textContent;
      function feedback() {
        botao.textContent = "Copiado!";
        setTimeout(function () { botao.textContent = rotulo; }, 1600);
      }
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(texto).then(feedback);
      } else {
        var area = document.createElement("textarea");
        area.value = texto;
        document.body.appendChild(area);
        area.select();
        document.execCommand("copy");
        document.body.removeChild(area);
        feedback();
      }
    });
  });

  // Botão "copiar citação" -------------------------------------------------
  document.querySelectorAll("[data-copiar]").forEach(function (botao) {
    botao.addEventListener("click", function () {
      var alvo = document.querySelector(botao.dataset.copiar);
      if (!alvo) return;
      var texto = alvo.textContent.trim();
      var rotuloOriginal = botao.textContent;

      function confirmar() {
        botao.textContent = "Citação copiada!";
        setTimeout(function () {
          botao.textContent = rotuloOriginal;
        }, 2000);
      }

      if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(texto).then(confirmar);
      } else {
        var campo = document.createElement("textarea");
        campo.value = texto;
        document.body.appendChild(campo);
        campo.select();
        document.execCommand("copy");
        document.body.removeChild(campo);
        confirmar();
      }
    });
  });

  // Carrosséis infinitos: a animação acontece na faixa de cartazes,
  // não nas setas. O trilho desliza com curva suave e reencaixe invisível.
  document.querySelectorAll("[data-carrossel]").forEach(function (car) {
    var trilha = car.querySelector(".carrossel-trilha");
    var setas = car.querySelectorAll("[data-seta]");
    if (!trilha || !setas.length) return;

    var originais = Array.from(trilha.children).filter(function (item) {
      return !item.classList.contains("cartaz-clone");
    });
    if (!originais.length) return;

    function criarClone(elemento) {
      var clone = elemento.cloneNode(true);
      clone.classList.add("cartaz-clone");
      clone.setAttribute("aria-hidden", "true");
      clone.querySelectorAll("a, button, input, select, textarea, [tabindex]").forEach(function (item) {
        item.setAttribute("tabindex", "-1");
      });
      return clone;
    }

    var antes = document.createDocumentFragment();
    var depois = document.createDocumentFragment();
    originais.forEach(function (item) { antes.appendChild(criarClone(item)); });
    originais.forEach(function (item) { depois.appendChild(criarClone(item)); });
    trilha.insertBefore(antes, trilha.firstChild);
    trilha.appendChild(depois);

    var larguraSerie = 0;
    var bloqueandoRebase = false;
    var temporizadorLoop = null;
    var animacaoAtual = 0;
    var movimentoReduzido = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    function medirSerie() {
      var estilo = window.getComputedStyle(trilha);
      var gap = parseFloat(estilo.columnGap || estilo.gap) || 0;
      larguraSerie = originais.reduce(function (soma, item) {
        return soma + item.getBoundingClientRect().width;
      }, 0) + gap * originais.length;
      return larguraSerie;
    }

    function posicionarNoOriginal() {
      medirSerie();
      if (!larguraSerie) return;
      bloqueandoRebase = true;
      trilha.classList.add("carrossel-sem-snap");
      trilha.scrollLeft = larguraSerie;
      requestAnimationFrame(function () {
        trilha.classList.remove("carrossel-sem-snap");
        bloqueandoRebase = false;
      });
    }

    function manterLoop() {
      if (bloqueandoRebase || animacaoAtual || !larguraSerie) return;
      var atual = trilha.scrollLeft;
      if (atual < larguraSerie - 2) {
        bloqueandoRebase = true;
        trilha.classList.add("carrossel-sem-snap");
        trilha.scrollLeft = atual + larguraSerie;
      } else if (atual >= (larguraSerie * 2) - 2) {
        bloqueandoRebase = true;
        trilha.classList.add("carrossel-sem-snap");
        trilha.scrollLeft = atual - larguraSerie;
      } else {
        return;
      }
      requestAnimationFrame(function () {
        trilha.classList.remove("carrossel-sem-snap");
        bloqueandoRebase = false;
      });
    }

    function animarTrilho(destino, distancia) {
      if (animacaoAtual) cancelAnimationFrame(animacaoAtual);
      if (movimentoReduzido) {
        trilha.scrollLeft = destino;
        manterLoop();
        return;
      }

      var inicio = trilha.scrollLeft;
      var deslocamento = destino - inicio;
      if (Math.abs(deslocamento) < 1) return;
      var inicioTempo = null;
      // Um deslocamento maior recebe um pouco mais de tempo, sem ficar arrastado.
      var duracao = Math.min(1400, Math.max(950, 900 + (distancia / 500) * 160));
      trilha.classList.remove("carrossel-indo-direita", "carrossel-indo-esquerda");
      trilha.classList.add("carrossel-animando", deslocamento > 0 ? "carrossel-indo-direita" : "carrossel-indo-esquerda");

      function quadro(tempo) {
        if (inicioTempo === null) inicioTempo = tempo;
        var progresso = Math.min(1, (tempo - inicioTempo) / duracao);
        // Ease-in-out cúbica: começa suave, ganha ritmo no meio e desacelera no fim.
        // Ease-in-out senoidal: aceleração e freada bem suaves, sem trancos.
        var curva = -(Math.cos(Math.PI * progresso) - 1) / 2;
        trilha.scrollLeft = inicio + deslocamento * curva;

        if (progresso < 1) {
          animacaoAtual = requestAnimationFrame(quadro);
        } else {
          animacaoAtual = 0;
          trilha.classList.remove("carrossel-animando", "carrossel-indo-direita", "carrossel-indo-esquerda");
          trilha.scrollLeft = destino;
          manterLoop();
        }
      }
      animacaoAtual = requestAnimationFrame(quadro);
    }

    setas.forEach(function (seta) {
      seta.disabled = false;
      seta.removeAttribute("aria-disabled");
      seta.addEventListener("click", function () {
        var direcao = Number(seta.dataset.seta) || 1;
        seta.classList.remove("seta-clicada");
        void seta.offsetWidth;
        seta.classList.add("seta-clicada");
        window.setTimeout(function () { seta.classList.remove("seta-clicada"); }, 600);
        var primeiro = originais[0];
        var larguraCartaz = primeiro ? primeiro.getBoundingClientRect().width : 160;
        var estilo = window.getComputedStyle(trilha);
        var gap = parseFloat(estilo.columnGap || estilo.gap) || 14;
        var passo = larguraCartaz + gap;
        var visiveis = Math.max(1, Math.floor(trilha.clientWidth / passo));
        var quantidade = Math.max(1, Math.min(4, visiveis - 1));
        var distancia = passo * quantidade;
        animarTrilho(trilha.scrollLeft + direcao * distancia, distancia);
      });
    });

    function agendarVerificacaoDoLoop() {
      if (animacaoAtual || bloqueandoRebase) return;
      window.clearTimeout(temporizadorLoop);
      temporizadorLoop = window.setTimeout(manterLoop, 220);
    }

    trilha.addEventListener("scroll", agendarVerificacaoDoLoop, { passive: true });
    trilha.addEventListener("scrollend", manterLoop);
    window.addEventListener("resize", function () {
      if (animacaoAtual) cancelAnimationFrame(animacaoAtual);
      animacaoAtual = 0;
      trilha.classList.remove("carrossel-animando", "carrossel-indo-direita", "carrossel-indo-esquerda");
      posicionarNoOriginal();
    });
    requestAnimationFrame(posicionarNoOriginal);
    window.addEventListener("load", posicionarNoOriginal, { once: true });
  });

  // Botão flutuante do assistente para acima do rodapé ----
  var rodape = document.querySelector(".rodape");
  if (rodape) {
    var ajustarBotoes = function () {
      var sobe = Math.max(0, window.innerHeight - rodape.getBoundingClientRect().top);
      document.documentElement.style.setProperty("--sobe-rodape", sobe + "px");
    };
    window.addEventListener("scroll", ajustarBotoes, { passive: true });
    window.addEventListener("resize", ajustarBotoes);
    ajustarBotoes();
  }

  // Envio automático dos filtros ao trocar de opção -------------------------
  var formFiltros = document.querySelector(".filtros");
  if (formFiltros) {
    formFiltros.querySelectorAll("select").forEach(function (campo) {
      campo.addEventListener("change", function () {
        formFiltros.submit();
      });
    });
  }
});

/* =========================================================================
   Acessibilidade — daltonismo, contraste, fonte, movimento, Libras e voz
   ========================================================================= */
(function () {
  const html = document.documentElement;
  const salvar = (chave, valor) => localStorage.setItem("acess-" + chave, valor);
  const ler = (chave) => localStorage.getItem("acess-" + chave);

  const abrir = document.getElementById("acess-abrir");
  const painel = document.getElementById("acess-painel");
  if (abrir && painel) {
    abrir.addEventListener("click", () => {
      const aberto = !painel.hidden;
      painel.hidden = aberto;
      abrir.setAttribute("aria-expanded", String(!aberto));
    });
    // Esc fecha o painel e devolve o foco ao botão de acessibilidade
    document.addEventListener("keydown", (evento) => {
      if (evento.key !== "Escape" || painel.hidden) return;
      painel.hidden = true;
      abrir.setAttribute("aria-expanded", "false");
      abrir.focus();
    });
  }

  const daltonismo = document.getElementById("acess-daltonismo");
  function aplicarDaltonismo(valor) {
    ["protanopia", "deuteranopia", "tritanopia", "monocromatico"].forEach((m) =>
      html.classList.remove("daltonismo-" + m)
    );
    if (valor && valor !== "nenhum") html.classList.add("daltonismo-" + valor);
    salvar("daltonismo", valor);
  }
  if (daltonismo) {
    daltonismo.value = ler("daltonismo") || "nenhum";
    aplicarDaltonismo(daltonismo.value);
    daltonismo.addEventListener("change", () => aplicarDaltonismo(daltonismo.value));
  }

  const alternadores = [
    ["acess-contraste", "alto-contraste"],
    ["acess-fonte", "fonte-ampliada"],
    ["acess-movimento", "sem-movimento"],
  ];
  alternadores.forEach(([id, classe]) => {
    const campo = document.getElementById(id);
    if (!campo) return;
    const ativo = ler(classe) === "1";
    campo.checked = ativo;
    html.classList.toggle(classe, ativo);
    campo.addEventListener("change", () => {
      html.classList.toggle(classe, campo.checked);
      salvar(classe, campo.checked ? "1" : "0");
    });
  });

  // VLibras (tradutor oficial de Libras do Governo Federal)
  const libras = document.getElementById("acess-libras");
  function ligarVLibras() {
    if (document.getElementById("vlibras-wrapper")) return;
    const wrapper = document.createElement("div");
    wrapper.id = "vlibras-wrapper";
    wrapper.setAttribute("vw", "");
    wrapper.className = "enabled";
    wrapper.innerHTML =
      '<div vw-access-button class="active"></div><div vw-plugin-wrapper><div class="vw-plugin-top-wrapper"></div></div>';
    document.body.appendChild(wrapper);
    const script = document.createElement("script");
    script.src = "https://vlibras.gov.br/app/vlibras-plugin.js";
    script.onload = () => {
      try { new window.VLibras.Widget("https://vlibras.gov.br/app"); } catch (e) { console.warn(e); }
    };
    document.body.appendChild(script);
  }
  if (libras) {
    libras.checked = ler("libras") === "1";
    if (libras.checked) ligarVLibras();
    libras.addEventListener("change", () => {
      salvar("libras", libras.checked ? "1" : "0");
      if (libras.checked) ligarVLibras();
      else location.reload();
    });
  }

  const ler_voz = document.getElementById("acess-ler");
  if (ler_voz) {
    ler_voz.addEventListener("click", () => {
      if (!("speechSynthesis" in window)) return alert("Seu navegador não tem síntese de voz.");
      const principal = document.getElementById("conteudo");
      if (speechSynthesis.speaking) { speechSynthesis.cancel(); return; }
      const fala = new SpeechSynthesisUtterance(principal.innerText.slice(0, 4000));
      fala.lang = "pt-BR";
      speechSynthesis.speak(fala);
    });
  }

  const limpar = document.getElementById("acess-limpar");
  if (limpar) {
    limpar.addEventListener("click", () => {
      ["daltonismo", "alto-contraste", "fonte-ampliada", "sem-movimento", "libras"].forEach((c) =>
        localStorage.removeItem("acess-" + c)
      );
      location.reload();
    });
  }
})();

/* =========================================================================
   Assistente de redação (IA) — abre ao passar o mouse, voz e câmera
   ========================================================================= */
(function () {
  const caixa = document.getElementById("ia-caixa");
  const painel = document.getElementById("ia-painel");
  const abrir = document.getElementById("ia-abrir");
  const fechar = document.getElementById("ia-fechar");
  const expandir = document.getElementById("ia-expandir");
  const identificacao = document.getElementById("ia-identificacao");
  const presenca = document.getElementById("ia-presenca");
  const form = document.getElementById("ia-form");
  const entrada = document.getElementById("ia-entrada");
  const lista = document.getElementById("ia-mensagens");
  if (!caixa || !painel) return;

  let fixado = false;
  const CHAVE_HISTORICO = "cineRepertorioBriggsHistoricoV1";
  const LIMITE_HISTORICO = 12;
  let historico = [];
  try {
    const salvo = JSON.parse(sessionStorage.getItem(CHAVE_HISTORICO) || "[]");
    if (Array.isArray(salvo)) {
      historico = salvo.filter((item) => item && ["user", "assistant"].includes(item.role)
        && typeof item.content === "string").slice(-LIMITE_HISTORICO);
    }
  } catch (e) { historico = []; }

  function salvarHistorico() {
    historico = historico.slice(-LIMITE_HISTORICO);
    try { sessionStorage.setItem(CHAVE_HISTORICO, JSON.stringify(historico)); } catch (e) { /* armazenamento pode estar bloqueado */ }
  }

  function definirStatus(respondendo) {
    if (identificacao) identificacao.textContent = respondendo ? "Briggs respondendo..." : "Briggs";
    if (presenca) {
      presenca.replaceChildren();
      const ponto = document.createElement("span");
      ponto.className = "ia-status-ponto" + (respondendo ? " ia-status-ativo" : "");
      ponto.setAttribute("aria-hidden", "true");
      presenca.append(ponto, document.createTextNode(respondendo ? "Preparando sua resposta" : "Pronto para conversar"));
    }
  }

  function definirExpandido(estado) {
    painel.classList.toggle("ia-painel-expandido", estado);
    caixa.classList.toggle("ia-caixa-expandida", estado);
    document.body.classList.toggle("ia-sem-rolagem", estado);
    if (expandir) {
      expandir.setAttribute("aria-pressed", String(estado));
      expandir.setAttribute("aria-label", estado ? "Restaurar tamanho da conversa" : "Ampliar a janela do Briggs");
      expandir.setAttribute("title", estado ? "Restaurar tamanho" : "Ampliar conversa");
      const icone = expandir.querySelector("span");
      if (icone) icone.textContent = estado ? "↙" : "⛶";
    }
  }

  function mostrar(estado) {
    painel.hidden = !estado;
    abrir.setAttribute("aria-expanded", String(estado));
    if (!estado) definirExpandido(false);
  }
  caixa.addEventListener("mouseenter", () => mostrar(true));
  caixa.addEventListener("mouseleave", () => { if (!fixado && !painel.classList.contains("ia-painel-expandido")) mostrar(false); });
  caixa.addEventListener("focusin", () => mostrar(true));
  abrir.addEventListener("click", () => { fixado = !fixado; mostrar(true); entrada.focus(); });
  if (expandir) {
    expandir.addEventListener("click", () => {
      fixado = true;
      const vaiExpandir = !painel.classList.contains("ia-painel-expandido");
      definirExpandido(vaiExpandir);
      if (vaiExpandir) lista.scrollTop = lista.scrollHeight;
    });
  }
  fechar.addEventListener("click", () => { fixado = false; definirExpandido(false); mostrar(false); });
  document.querySelectorAll("[data-abrir-ia]").forEach((b) =>
    b.addEventListener("click", () => { fixado = true; mostrar(true); entrada.focus(); })
  );

  function bolha(texto, quem) {
    const div = document.createElement("div");
    div.className = "ia-msg " + quem;
    div.textContent = texto;
    lista.appendChild(div);
    lista.scrollTop = lista.scrollHeight;
    return div;
  }

  function renderizar(dados) {
    const div = bolha(dados.texto, "bot");
    const assinatura = document.createElement("span");
    assinatura.className = "ia-assinatura";
    assinatura.textContent = "Briggs:";
    div.insertBefore(assinatura, div.firstChild);
    (dados.blocos || []).forEach((b) => {
      const bloco = document.createElement("div");
      const tiposPermitidos = ["plano", "redacao", "checklist", "nota", "repertorio", "estrutura"];
      bloco.className = "ia-bloco" + (tiposPermitidos.includes(b.tipo) ? ` ia-bloco-${b.tipo}` : "");
      bloco.innerHTML = "<strong></strong><p class='mb-0'></p>";
      bloco.querySelector("strong").textContent = b.titulo;
      bloco.querySelector("p").textContent = b.texto;
      div.appendChild(bloco);
    });
    (dados.filmes || []).forEach((f) => {
      const link = document.createElement("a");
      link.className = "ia-chip d-inline-block mt-2 me-1";
      link.href = "/filmes/" + f.id;
      link.textContent = `${f.titulo} (${f.ano}) · IMDb ${f.imdb}`;
      div.appendChild(link);
    });
    const recursos = [
      ...(dados.videos || []).map((v) => ({ ...v, categoria: "Vídeo" })),
      ...(dados.recursos || []).map((r) => ({ ...r, categoria: r.tipo || "Material" })),
    ];
    if (recursos.length) {
      const areaRecursos = document.createElement("div");
      areaRecursos.className = "ia-recursos";
      const tituloRecursos = document.createElement("strong");
      tituloRecursos.className = "ia-recursos-titulo";
      tituloRecursos.textContent = "Materiais para continuar";
      areaRecursos.appendChild(tituloRecursos);
      recursos.forEach((r) => {
        let destino;
        try { destino = new URL(r.url, window.location.origin); } catch (e) { return; }
        if (destino.protocol !== "https:" || !["youtube.com", "www.youtube.com", "google.com", "www.google.com"].includes(destino.hostname)) return;
        const link = document.createElement("a");
        link.className = "ia-recurso-link";
        link.href = destino.href;
        link.target = "_blank";
        link.rel = "noopener noreferrer";
        const icone = document.createElement("span");
        icone.className = "ia-recurso-icone";
        icone.textContent = r.categoria === "Vídeo" ? "▶" : "↗";
        const textoLink = document.createElement("span");
        const tituloLink = document.createElement("strong");
        tituloLink.textContent = r.titulo || "Abrir material";
        const subtituloLink = document.createElement("small");
        subtituloLink.textContent = r.tipo || r.duracao || "Abrir em nova aba";
        textoLink.append(tituloLink, subtituloLink);
        const seta = document.createElement("span");
        seta.className = "ia-recurso-seta";
        seta.textContent = "↗";
        link.append(icone, textoLink, seta);
        areaRecursos.appendChild(link);
      });
      if (areaRecursos.querySelector(".ia-recurso-link")) div.appendChild(areaRecursos);
    }
    const chips = document.getElementById("ia-sugestoes");
    if (dados.sugestoes && dados.sugestoes.length) {
      chips.innerHTML = "";
      dados.sugestoes.forEach((s) => {
        const botao = document.createElement("button");
        botao.type = "button";
        botao.className = "ia-chip";
        botao.textContent = s;
        chips.appendChild(botao);
      });
    }
    lista.scrollTop = lista.scrollHeight;
  }

  async function perguntar(mensagem) {
    mensagem = (mensagem || "").trim();
    if (!mensagem) return;
    bolha(mensagem, "eu");
    entrada.value = "";
    historico.push({ role: "user", content: mensagem });
    salvarHistorico();
    const carregando = bolha("Briggs respondendo...", "bot");
    carregando.classList.add("ia-digitando");
    definirStatus(true);
    const enviar = form.querySelector('button[type="submit"]');
    if (enviar) enviar.disabled = true;
    try {
      const resposta = await fetch("/api/assistente", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mensagem, historico: historico.slice(0, -1) }),
      });
      const dados = await resposta.json();
      carregando.remove();
      if (!resposta.ok) throw new Error(dados.texto || "Não consegui responder agora.");
      renderizar(dados);
      historico.push({ role: "assistant", content: dados.texto || "" });
      salvarHistorico();
    } catch (erro) {
      carregando.textContent = erro.message || "Não consegui responder agora. Tente novamente.";
    } finally {
      definirStatus(false);
      if (enviar) enviar.disabled = false;
      entrada.focus();
    }
  }

  form.addEventListener("submit", (e) => { e.preventDefault(); perguntar(entrada.value); });
  document.addEventListener("click", (e) => {
    const chip = e.target.closest(".ia-chip");
    if (!chip || chip.tagName === "A") return;
    const texto = chip.dataset.pergunta || chip.textContent;
    fixado = true; mostrar(true);
    perguntar(texto);
  });

  // Comando de voz (pede permissão do microfone)
  const botaoVoz = document.getElementById("ia-voz");
  botaoVoz.addEventListener("click", async () => {
    const Reconhecimento = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!Reconhecimento) return alert("Seu navegador não suporta reconhecimento de voz.");
    try {
      await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (e) {
      return alert("Precisamos da sua permissão para usar o microfone.");
    }
    const rec = new Reconhecimento();
    rec.lang = "pt-BR";
    rec.interimResults = false;
    botaoVoz.textContent = "🎙️ Ouvindo...";
    rec.onresult = (evento) => { entrada.value = evento.results[0][0].transcript; };
    rec.onend = () => { botaoVoz.textContent = "🎤 Voz"; };
    rec.onerror = () => { botaoVoz.textContent = "🎤 Voz"; };
    rec.start();
  });

  // Câmera (pede permissão antes de ligar)
  const camera = document.getElementById("ia-camera");
  const video = document.getElementById("ia-video");
  const canvas = document.getElementById("ia-canvas");
  let fluxo = null;

  document.getElementById("ia-foto").addEventListener("click", async () => {
    try {
      fluxo = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } });
      video.srcObject = fluxo;
      camera.hidden = false;
    } catch (e) {
      alert("Precisamos da sua permissão para usar a câmera.");
    }
  });

  function pararCamera() {
    if (fluxo) fluxo.getTracks().forEach((t) => t.stop());
    fluxo = null;
    camera.hidden = true;
  }
  document.getElementById("ia-cancelar-camera").addEventListener("click", pararCamera);
  document.getElementById("ia-capturar").addEventListener("click", () => {
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext("2d").drawImage(video, 0, 0);
    const img = document.createElement("img");
    img.src = canvas.toDataURL("image/png");
    img.alt = "Foto da redação capturada pela câmera";
    img.className = "img-fluid rounded mt-2";
    const div = bolha("Foto da minha redação:", "eu");
    div.appendChild(img);
    pararCamera();
    perguntar("Tirei uma foto da minha redação. Como faço para melhorar a estrutura e a proposta de intervenção?");
  });

  if (historico.length) {
    definirStatus(false);
    historico.forEach((item) => {
      const div = bolha(item.content, item.role === "user" ? "eu" : "bot");
      if (item.role === "assistant") {
        const assinatura = document.createElement("span");
        assinatura.className = "ia-assinatura";
        assinatura.textContent = "Briggs:";
        div.insertBefore(assinatura, div.firstChild);
      }
    });
  } else {
    definirStatus(false);
    const boasVindas = bolha("Muito prazer, eu sou Briggs. Podemos conversar sobre praticamente qualquer assunto: estudos, tecnologia, ideias, filmes, criatividade ou o que estiver passando pela sua cabeça. Sou direto, curioso e tenho uma queda por boas histórias — mas a conversa é sua. Por onde começamos?", "bot");
    const assinaturaInicial = document.createElement("span");
    assinaturaInicial.className = "ia-assinatura";
    assinaturaInicial.textContent = "Briggs:";
    boasVindas.insertBefore(assinaturaInicial, boasVindas.firstChild);
    historico.push({ role: "assistant", content: boasVindas.textContent.replace("Briggs:", "").trim() });
    salvarHistorico();
  }

  const limpar = document.getElementById("ia-limpar");
  if (limpar) limpar.addEventListener("click", () => {
    historico = [];
    try { sessionStorage.removeItem(CHAVE_HISTORICO); } catch (e) { /* ignorar */ }
    lista.innerHTML = "";
    const boasVindas = bolha("Conversa limpa. A lousa está em branco — qual assunto vamos explorar agora?", "bot");
    const assinatura = document.createElement("span");
    assinatura.className = "ia-assinatura";
    assinatura.textContent = "Briggs:";
    boasVindas.insertBefore(assinatura, boasVindas.firstChild);
    historico.push({ role: "assistant", content: "Conversa limpa. A lousa está em branco — qual assunto vamos explorar agora?" });
    salvarHistorico();
  });
})();
