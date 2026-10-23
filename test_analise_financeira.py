"""Testes da análise financeira (sem dependências externas)."""

import unittest

from analise_financeira import analisar_viabilidade


class TestAnaliseFinanceira(unittest.TestCase):
    def test_sem_milhas(self):
        self.assertEqual(analisar_viabilidade(0), "Destino recomendado: ficar em casa.")

    def test_poucas_milhas(self):
        self.assertEqual(analisar_viabilidade(9999), "Destino recomendado: rodoviária mais próxima.")

    def test_milhas_suficientes_para_sonhar(self):
        self.assertEqual(analisar_viabilidade(10000), "Parabéns! Agora só falta o dinheiro para o hotel.")

    def test_saldo_negativo(self):
        with self.assertRaises(ValueError):
            analisar_viabilidade(-1)


if __name__ == "__main__":
    unittest.main()
