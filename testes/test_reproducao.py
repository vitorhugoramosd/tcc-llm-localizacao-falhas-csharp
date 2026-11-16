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
