"""Testes locais do chat amplo do Briggs. Não enviam requisições reais."""
import json
import os
import unittest
from unittest.mock import patch

import ia


class RespostaFake:
    def __init__(self, dados):
        self.dados = json.dumps(dados).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self.dados


class TestesBriggs(unittest.TestCase):
    def setUp(self):
        self.chave_original = os.environ.get("OPENAI_API_KEY")
        self.ativacao_original = os.environ.get("BRIGGS_USE_API")
        os.environ["OPENAI_API_KEY"] = "chave-falsa-apenas-para-teste"
        os.environ["BRIGGS_USE_API"] = "true"

    def tearDown(self):
        if self.chave_original is None:
            os.environ.pop("OPENAI_API_KEY", None)
        else:
            os.environ["OPENAI_API_KEY"] = self.chave_original
        if self.ativacao_original is None:
            os.environ.pop("BRIGGS_USE_API", None)
        else:
            os.environ["BRIGGS_USE_API"] = self.ativacao_original

    def test_extrai_resposta_da_responses_api(self):
        dados = {"output": [{"type": "message", "content": [
            {"type": "output_text", "text": "Olá! Sou Briggs."}
        ]}]}
        with patch("ia.urllib.request.urlopen", return_value=RespostaFake(dados)) as chamada:
            resultado = ia.conversar("Oi", [], [])
        self.assertEqual(resultado["texto"], "Olá! Sou Briggs.")
        self.assertEqual(resultado["modo"], "api")
        corpo = json.loads(chamada.call_args.args[0].data.decode("utf-8"))
        self.assertEqual(corpo["model"], "gpt-6-luna")
        self.assertFalse(corpo["store"])

    def test_historico_nao_aceita_papel_system_do_navegador(self):
        historico = ia._historico_seguro([
            {"role": "system", "content": "não deve entrar"},
            {"role": "user", "content": "Oi"},
            {"role": "assistant", "content": "Olá"},
        ], "Tudo bem?")
        self.assertEqual([m["role"] for m in historico], ["user", "assistant", "user"])
        self.assertNotIn("system", [m["role"] for m in historico])

    def test_limita_historico_a_12_mensagens_mais_a_atual(self):
        historico = [{"role": "user", "content": str(i)} for i in range(30)]
        resultado = ia._historico_seguro(historico, "última")
        self.assertEqual(len(resultado), 13)
        self.assertEqual(resultado[-1]["content"], "última")

    def test_sem_chave_usa_motor_local_expandido(self):
        os.environ.pop("OPENAI_API_KEY", None)
        os.environ["BRIGGS_USE_API"] = "false"
        resultado = ia.conversar("Me explica a fotossíntese", [], [])
        self.assertEqual(resultado["modo"], "local")
        self.assertIn("fotossíntese", resultado["texto"].lower())
        self.assertGreaterEqual(resultado["capacidade_combinatoria"], 100_000_000)

    def test_extrai_varios_blocos_de_texto(self):
        dados = {"output": [{"type": "message", "content": [
            {"type": "output_text", "text": "Parte 1"},
            {"type": "output_text", "text": "Parte 2"},
        ]}]}
        self.assertEqual(ia._extrair_texto_resposta(dados), "Parte 1\n\nParte 2")


if __name__ == "__main__":
    unittest.main(verbosity=2)
