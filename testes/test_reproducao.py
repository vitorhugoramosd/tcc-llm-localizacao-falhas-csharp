# Testes de reprodução: conferem que os números publicados no TCC saem dos arquivos deste repositório.
# Uso, na pasta raiz do repositório:  python -m unittest discover testes
import csv, importlib.util, json, os, random, unittest


def ler_json(*partes):
    with open(os.path.join(*partes), encoding='utf-8') as f:
        return json.load(f)


RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location('piloto', os.path.join(RAIZ, 'piloto', 'piloto.py'))
piloto = importlib.util.module_from_spec(spec); spec.loader.exec_module(piloto)

# Tabela 2 do Cap. 4 (nível de arquivo): (Top-1, Top-3, Top-5, MRR) por modelo e perfil
TABELA_2 = {('claude', 'com testes'): (75, 75, 75, 0.75), ('claude', 'legado (sem testes)'): (67, 100, 100, 0.83),
            ('gemini', 'com testes'): (75, 75, 75, 0.75), ('gemini', 'legado (sem testes)'): (33, 33, 100, 0.50),
            ('nemotron', 'com testes'): (50, 75, 75, 0.62), ('nemotron', 'legado (sem testes)'): (0, 33, 67, 0.23),
            ('cohere', 'com testes'): (50, 75, 75, 0.62), ('cohere', 'legado (sem testes)'): (0, 33, 67, 0.19)}
# Tabela 3 do Cap. 4 (nível de método)
TABELA_3 = {('claude', 'com testes'): (50, 75, 75, 0.58), ('claude', 'legado (sem testes)'): (67, 100, 100, 0.78),
            ('gemini', 'com testes'): (50, 75, 75, 0.62), ('gemini', 'legado (sem testes)'): (67, 67, 67, 0.67),
            ('nemotron', 'com testes'): (50, 50, 50, 0.50), ('nemotron', 'legado (sem testes)'): (33, 33, 67, 0.42),
            ('cohere', 'com testes'): (50, 50, 50, 0.50), ('cohere', 'legado (sem testes)'): (0, 0, 0, 0.00)}

# Tabela 4 do Cap. 4: posição do arquivo e do método certos em cada defeito (None = fora das cinco posições)
TABELA_4 = {
    'nop-8409':    {'claude': (1, 1), 'gemini': (1, 1), 'nemotron': (1, 1), 'cohere': (1, 1)},
    'nop-8369':    {'claude': (1, 1), 'gemini': (1, 1), 'nemotron': (1, 1), 'cohere': (1, 1)},
    'nop-7587':    {'claude': (1, 3), 'gemini': (1, 2), 'nemotron': (2, None), 'cohere': (2, None)},
    'nop-8299':    {'claude': (None, None), 'gemini': (None, None), 'nemotron': (None, None), 'cohere': (None, None)},
    'sharex-8699': {'claude': (1, 1), 'gemini': (1, 1), 'nemotron': (5, 1), 'cohere': (None, None)},
    'sharex-8568': {'claude': (2, 3), 'gemini': (4, None), 'nemotron': (2, 4), 'cohere': (4, None)},
    'sharex-8091': {'claude': (1, 1), 'gemini': (4, 1), 'nemotron': (None, None), 'cohere': (3, None)},
}
# Tabela 5 do Cap. 4: consultas, tokens enviados, tokens recebidos, tempo médio por defeito (s) e acertos na memorização
TABELA_5 = {'claude': (21, 808860, 7110, 11.1, 1), 'gemini': (22, 495389, 3012, 51.5, 3),
            'nemotron': (21, 381898, 38751, 89.5, 0), 'cohere': (32, 392558, 450981, 317.0, 0)}
# Preço oficial do Claude Sonnet 5.5 na API da Anthropic (US$ por milhão de tokens), usado para estimar o custo do piloto
PRECO_CLAUDE = {'entrada': 2.00, 'saida': 10.00}


def posicoes(modelo, perfil, nivel):
    out = []
    for d in piloto.DEF:
        if d['perfil'] != perfil: continue
        r = ler_json(RAIZ, 'piloto', 'respostas', modelo, f"{d['id']}.json")
        out.append(piloto.posicao_arquivo(d, r['arquivos']) if nivel == 'arquivo' else piloto.posicao_metodo(d, r['metodos']))
    return out


def metricas(ps):
    top = lambda n: round(100 * sum(1 for p in ps if p and p <= n) / len(ps))
    return top(1), top(3), top(5), round(sum(1 / p for p in ps if p) / len(ps), 2)


class TestTabelasDoCapitulo4(unittest.TestCase):
    def test_tabela_2_nivel_de_arquivo(self):
        for (m, perfil), esperado in TABELA_2.items():
            with self.subTest(modelo=m, perfil=perfil):
                self.assertEqual(metricas(posicoes(m, perfil, 'arquivo')), esperado)

    def test_tabela_3_nivel_de_metodo(self):
        for (m, perfil), esperado in TABELA_3.items():
            with self.subTest(modelo=m, perfil=perfil):
                self.assertEqual(metricas(posicoes(m, perfil, 'metodo')), esperado)

    def test_resultados_csv_bate_com_as_respostas(self):
        with open(os.path.join(RAIZ, 'piloto', 'resultados.csv'), encoding='utf-8') as f:
            linhas = list(csv.DictReader(f, delimiter=';'))
        self.assertEqual(len(linhas), 28)  # 7 defeitos x 4 modelos
        for l in linhas:
            d = next(x for x in piloto.DEF if x['id'] == l['defeito'])
            r = ler_json(RAIZ, 'piloto', 'respostas', l['rotulo'], f"{d['id']}.json")
            with self.subTest(modelo=l['rotulo'], defeito=l['defeito']):
                self.assertEqual(l['pos_arquivo'], str(piloto.posicao_arquivo(d, r['arquivos']) or ''))
                self.assertEqual(l['pos_metodo'], str(piloto.posicao_metodo(d, r['metodos']) or ''))

    def test_tabela_4_posicoes_por_defeito(self):
        for did, por_modelo in TABELA_4.items():
            d = next(x for x in piloto.DEF if x['id'] == did)
            for m, esperado in por_modelo.items():
                r = ler_json(RAIZ, 'piloto', 'respostas', m, f"{did}.json")
                with self.subTest(defeito=did, modelo=m):
                    self.assertEqual((piloto.posicao_arquivo(d, r['arquivos']), piloto.posicao_metodo(d, r['metodos'])), esperado)

    def test_tabela_5_esforco_e_memorizacao(self):
        with open(os.path.join(RAIZ, 'piloto', 'resultados.csv'), encoding='utf-8') as f:
            linhas = list(csv.DictReader(f, delimiter=';'))
        for m, esperado in TABELA_5.items():
            ls = [l for l in linhas if l['rotulo'] == m]
            obtido = (sum(int(l['consultas']) for l in ls), sum(int(l['tokens_entrada']) for l in ls),
                      sum(int(l['tokens_saida']) for l in ls), round(sum(float(l['segundos']) for l in ls) / len(ls), 1),
                      sum(l['memorizacao_acertou'] == 'True' for l in ls))
            with self.subTest(modelo=m):
                self.assertEqual(obtido, esperado)

    def test_custo_do_claude(self):
        # Cap. 4: cerca de US$ 1,70 no total e US$ 0,24 por defeito, estimados a partir dos tokens registrados
        _, entrada, saida, _, _ = TABELA_5['claude']
        custo = entrada / 1e6 * PRECO_CLAUDE['entrada'] + saida / 1e6 * PRECO_CLAUDE['saida']
        self.assertAlmostEqual(custo, 1.70, delta=0.02)
        self.assertEqual(round(custo / 7, 2), 0.24)


class TestSorteio(unittest.TestCase):
    def test_semente_reproduz_a_ordem_do_sorteio(self):
        pasta = os.path.join(RAIZ, 'preparacao')
        eleg = ler_json(pasta, 'elegiveis_pre.json')
        ordem = ler_json(pasta, 'ordem_sorteio.json')
        random.seed(20261107)
        for r in ('nop', 'sharex'):
            lista = list(eleg[r]); random.shuffle(lista)
            self.assertEqual(lista, ordem[r])


class TestReferenciaDeAcerto(unittest.TestCase):
    def test_arquivo_certo_existe_na_lista_enviada_ao_modelo(self):
        # Garante que a resposta certa estava disponível para o modelo na consulta de arquivo.
        for d in piloto.DEF:
            with self.subTest(d['id']):
                arqs = set(piloto.arquivos_repo(d))
                self.assertTrue(set(d['referencia']['arquivos']) & arqs)
                self.assertEqual(len(arqs), d['arquivos_cs_no_repositorio'])


if __name__ == '__main__':
    unittest.main()
