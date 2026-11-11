"""Testes locais da rota de contato e da integração SMTP (sem enviar e-mails reais).

Execute com: python testes_email.py
"""
import os
import shutil
import tempfile
import unittest
from unittest.mock import patch

BASE = os.path.dirname(os.path.abspath(__file__))
TEMP_DIR = tempfile.mkdtemp(prefix="cinerepertorio-email-")
DB_TESTE = os.path.join(TEMP_DIR, "banco_email_teste.db")
shutil.copy(os.path.join(BASE, "banco.db"), DB_TESTE)
os.environ["DATABASE"] = DB_TESTE

import app as aplicacao  # noqa: E402


class SMTPFalso:
    """Servidor SMTP de teste: registra chamadas, mas nunca acessa a rede."""
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.tls_chamado = False
        self.login_args = None
        self.mensagem = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def ehlo(self):
        return (250, b"OK")

    def starttls(self, context=None):
        self.tls_chamado = context is not None
        return (220, b"Ready for TLS")

    def login(self, usuario, senha):
        self.login_args = (usuario, senha)
        return (235, b"Authenticated")

    def send_message(self, mensagem):
        self.mensagem = mensagem
        return {}


class TestesNotificacoes(unittest.TestCase):
    def setUp(self):
        self.cliente = aplicacao.app.test_client()
        self.variaveis_anteriores = {
            chave: os.environ.get(chave)
            for chave in ("SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD", "SMTP_FROM", "SMTP_USE_SSL", "SMTP_TIMEOUT")
        }
        for chave in self.variaveis_anteriores:
            os.environ.pop(chave, None)

    def tearDown(self):
        for chave, valor in self.variaveis_anteriores.items():
            if valor is None:
                os.environ.pop(chave, None)
            else:
                os.environ[chave] = valor

    def dados(self, **extras):
        dados = {
            "nome": "Pessoa Teste",
            "email": "pessoa@example.com",
            "assunto": "Sugestão para o catálogo",
            "mensagem": "Gostaria de sugerir um filme para a página.",
        }
        dados.update(extras)
        return dados

    def configurar_smtp(self, porta="587"):
        os.environ.update({
            "SMTP_HOST": "smtp.example.test",
            "SMTP_PORT": porta,
            "SMTP_USER": "cinerepertorio@gmail.com",
            "SMTP_PASSWORD": "segredo-falso-so-para-teste",
            "SMTP_FROM": "cinerepertorio@gmail.com",
        })

    def test_pagina_notificacoes_abre_e_mostra_destinatario(self):
        resposta = self.cliente.get("/notificacoes")
        self.assertEqual(resposta.status_code, 200)
        self.assertIn(b"cinerepertorio@gmail.com", resposta.data)

    def test_post_sem_configuracao_nao_tenta_conectar(self):
        with patch.object(aplicacao.smtplib, "SMTP") as smtp:
            resposta = self.cliente.post("/notificacoes", data=self.dados(), follow_redirects=True)
        self.assertEqual(resposta.status_code, 200)
        self.assertIn("precisa ser ativado".encode(), resposta.data)
        smtp.assert_not_called()

    def test_validacao_e_campo_armadilha_bloqueiam_envio(self):
        self.configurar_smtp()
        with patch.object(aplicacao.smtplib, "SMTP") as smtp:
            resposta_invalida = self.cliente.post(
                "/notificacoes", data=self.dados(email="email-invalido"), follow_redirects=True
            )
            resposta_armadilha = self.cliente.post(
                "/notificacoes", data=self.dados(website="bot"), follow_redirects=True
            )
        self.assertIn("Confira os campos".encode(), resposta_invalida.data)
        self.assertIn("Não foi possível enviar".encode(), resposta_armadilha.data)
        smtp.assert_not_called()

    def test_envio_starttls_587_monta_email_corretamente(self):
        self.configurar_smtp("587")
        servidor = SMTPFalso()
        with patch.object(aplicacao.smtplib, "SMTP", return_value=servidor) as smtp:
            resposta = self.cliente.post("/notificacoes", data=self.dados(), follow_redirects=True)
        self.assertEqual(resposta.status_code, 200)
        self.assertIn("Mensagem enviada".encode(), resposta.data)
        smtp.assert_called_once_with("smtp.example.test", 587, timeout=20)
        self.assertTrue(servidor.tls_chamado)
        self.assertEqual(servidor.login_args, ("cinerepertorio@gmail.com", "segredo-falso-so-para-teste"))
        self.assertEqual(servidor.mensagem["To"], "cinerepertorio@gmail.com")
        self.assertEqual(servidor.mensagem["Reply-To"], "pessoa@example.com")
        self.assertIn("Gostaria de sugerir um filme", servidor.mensagem.get_content())

    def test_envio_ssl_465_usa_conexao_ssl(self):
        self.configurar_smtp("465")
        servidor = SMTPFalso()
        with patch.object(aplicacao.smtplib, "SMTP_SSL", return_value=servidor) as smtp_ssl:
            resposta = self.cliente.post("/notificacoes", data=self.dados(), follow_redirects=True)
        self.assertEqual(resposta.status_code, 200)
        self.assertIn("Mensagem enviada".encode(), resposta.data)
        smtp_ssl.assert_called_once()
        self.assertEqual(servidor.mensagem["To"], "cinerepertorio@gmail.com")

    def test_falha_de_autenticacao_nao_exibe_sucesso(self):
        import smtplib
        self.configurar_smtp("587")
        with patch.object(aplicacao.smtplib, "SMTP", side_effect=smtplib.SMTPAuthenticationError(535, b"bad credentials")):
            resposta = self.cliente.post("/notificacoes", data=self.dados(), follow_redirects=True)
        self.assertIn("Não foi possível enviar agora".encode(), resposta.data)
        self.assertNotIn("Mensagem enviada!".encode(), resposta.data)


if __name__ == "__main__":
    try:
        unittest.main(verbosity=2)
    finally:
        shutil.rmtree(TEMP_DIR, ignore_errors=True)
