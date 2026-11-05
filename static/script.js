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

  // Esteiras: pausa também ao tocar na tela (dispositivos móveis) -----------
  document.querySelectorAll("[data-esteira]").forEach(function (esteira) {
    var trilha = esteira.querySelector(".esteira-trilha");
    if (!trilha) return;
    esteira.addEventListener("touchstart", function () {
      trilha.style.animationPlayState = "paused";
    });
    esteira.addEventListener("touchend", function () {
      trilha.style.animationPlayState = "running";
    });
  });

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
