# Testes das regras de pontuação usadas no piloto (posição do acerto, Top-N e MRR).
# Uso, na pasta raiz do repositório:  python -m unittest discover testes
import importlib.util, os, unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location('piloto', os.path.join(RAIZ, 'piloto', 'piloto.py'))
piloto = importlib.util.module_from_spec(spec); spec.loader.exec_module(piloto)
DEF = {d['id']: d for d in piloto.DEF}


def top_n(posicoes, n):
    """Percentual de defeitos com o trecho certo entre as n primeiras posições (mesma conta de modo_resultados)."""
    return 100 * sum(1 for p in posicoes if p and p <= n) / len(posicoes)


def mrr(posicoes):
    """Média de 1/posição, com zero quando o trecho certo não apareceu (mesma conta de modo_resultados)."""
    return sum(1 / p for p in posicoes if p) / len(posicoes)


class TestTopNeMRR(unittest.TestCase):
    def test_exemplo_da_secao_2_3(self):
        # Quatro defeitos: acerto em 1º, 3º, 2º e um sem acerto (exemplo do Cap. 2).
        pos = [1, 3, 2, None]
        self.assertEqual(top_n(pos, 1), 25)
        self.assertEqual(top_n(pos, 3), 75)
        self.assertAlmostEqual(mrr(pos), (1 + 1/3 + 1/2 + 0) / 4)

    def test_mrr_vai_de_zero_a_um(self):
        self.assertEqual(mrr([1, 1, 1]), 1)
        self.assertEqual(mrr([None, None]), 0)


class TestPosicaoArquivo(unittest.TestCase):
    d = DEF['nop-8409']
    certo = 'src/Plugins/Nop.Plugin.Feed.ChatGptShopping/Services/ChatGptShoppingService.cs'

    def test_acerto_na_primeira_posicao(self):
        self.assertEqual(piloto.posicao_arquivo(self.d, [self.certo, 'a.cs', 'b.cs']), 1)

    def test_acerto_na_terceira_posicao(self):
        self.assertEqual(piloto.posicao_arquivo(self.d, ['a.cs', 'b.cs', self.certo]), 3)

    def test_fora_das_cinco_primeiras_nao_conta(self):
        self.assertIsNone(piloto.posicao_arquivo(self.d, ['a.cs'] * 5 + [self.certo]))

    def test_caminho_encurtado_unico_e_aceito(self):
        # Regra da seção 3.3: caminho sem "src/" é aceito se corresponder a um único arquivo do repositório.
        curto = self.certo[len('src/'):]
        self.assertEqual(piloto.posicao_arquivo(self.d, [curto]), 1)

    def test_barra_invertida_do_windows_e_aceita(self):
        self.assertEqual(piloto.posicao_arquivo(self.d, [self.certo.replace('/', '\\')]), 1)

    def test_nome_de_arquivo_ambiguo_nao_e_aceito(self):
        # Um nome que existe em mais de uma pasta não pode ser resolvido; não conta como acerto.
        arqs = piloto.arquivos_repo(self.d)
        nomes = [a.rsplit('/', 1)[-1] for a in arqs]
        repetido = next(n for n in nomes if nomes.count(n) > 1)
        self.assertEqual(piloto.resolver(self.d, repetido), repetido)


class TestPosicaoMetodo(unittest.TestCase):
    d = DEF['nop-8409']
    arq = 'src/Plugins/Nop.Plugin.Feed.ChatGptShopping/Services/ChatGptShoppingService.cs'

    def test_metodo_certo(self):
        self.assertEqual(piloto.posicao_metodo(self.d, [{'file': self.arq, 'method': 'BuildProductAsync'}]), 1)

    def test_nome_com_classe_e_parenteses(self):
        m = {'file': self.arq, 'method': 'ChatGptShoppingService.BuildProductAsync(Product product)'}
        self.assertEqual(piloto.posicao_metodo(self.d, [{'file': self.arq, 'method': 'X'}, m]), 2)

    def test_metodo_certo_em_arquivo_errado_nao_conta(self):
        self.assertIsNone(piloto.posicao_metodo(self.d, [{'file': 'outro/Arquivo.cs', 'method': 'BuildProductAsync'}]))


class TestExtrairJson(unittest.TestCase):
    def test_bloco_de_codigo(self):
        self.assertEqual(piloto.extrair_json('```json\n{"files": ["a.cs"]}\n```'), {'files': ['a.cs']})

    def test_raciocinio_antes_da_resposta_e_ignorado(self):
        self.assertEqual(piloto.extrair_json('<think>{"x": 1} talvez</think>{"files": []}'), {'files': []})

    def test_json_invalido_vira_none(self):
        self.assertIsNone(piloto.extrair_json('{"method: "A"}'))


if __name__ == '__main__':
    unittest.main()
